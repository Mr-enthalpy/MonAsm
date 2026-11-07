//! Deterministic encoding and fixup execution for FMP v0.
//!
//! The order of operations is `01_contract.md` §13: every static check runs
//! first, and a byte is written only when the plan has no diagnostics. Within
//! emission each instruction is encoded from `form_id` + operands, then compared
//! with `expected_size` and `expected_digest`, and only then patched — so a
//! rejected plan never produces a partial artifact.
//!
//! Nothing here selects, relaxes, expands, pads or reorders. The bytes of an
//! instruction are the definition's template with the declared fields replaced;
//! the bytes of a section are its fragments in `offset` order; the image is the
//! sections in `section_order`.

#![forbid(unsafe_code)]

use fmp_model::codes;
use fmp_model::definition::{Definition, Form, Slot, SlotFrom};
use fmp_model::diagnostic::{self, Diagnostic};
use fmp_model::json::Json;
use fmp_model::plan::{
    Fixup, FixupTarget, FragmentBody, Mode, Payload, PcRule, Plan, RangeConstraint, Section,
    Transform,
};

/// The version recorded in the artifact envelope. Audit only.
pub const MATERIALIZER_VERSION: &str = env!("CARGO_PKG_VERSION");

/// The materialized result: `01_contract.md` §11.1 and §11.2.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Artifact {
    /// The Level 0 image: image-backed sections concatenated in `section_order`.
    pub bytes: Vec<u8>,
    /// `0` or `1`; Level 1 is `artifact: sections`.
    pub level: u8,
    /// One entry per `section_order` id, in that order (Level 1 payload).
    pub sections: Vec<SectionImage>,
    /// `Some` only when `include_symbol_table` asked for a table.
    pub symbols: Option<Vec<SymbolEntry>>,
    /// Records in `fixup_record_order`, one per `emit_relocation` fixup.
    pub fixups: Vec<Record>,
    pub fingerprint: String,
}

/// One laid-out section in the Level 1 artifact (`01_contract.md` §11.2).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SectionImage {
    pub section_id: String,
    pub section_kind: String,
    pub image_backed: bool,
    pub base_address: Option<u64>,
    /// The plan's `declared_size`; for an image-backed section this equals
    /// `bytes.len()` (validation enforces exact fragment coverage).
    pub size: u64,
    pub bytes: Vec<u8>,
}

/// One declared symbol in the Level 1 artifact; no symbol is synthesized.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SymbolEntry {
    pub symbol_id: String,
    pub name: String,
    pub kind: String,
    pub binding: String,
    pub section_id: Option<String>,
    pub offset: Option<u64>,
}

impl Artifact {
    pub fn bytes_hex(&self) -> String {
        hex(&self.bytes)
    }

    /// The artifact envelope as a JSON value. Level 0 follows §11.1 exactly;
    /// Level 1 follows §11.2 and never reuses the Level 0 field order.
    pub fn to_json(&self) -> Json {
        if self.level == 0 {
            return self.level_zero_json();
        }
        let mut sections = Vec::with_capacity(self.sections.len());
        for section in &self.sections {
            let mut fields = vec![
                (
                    "section_id".to_string(),
                    Json::Str(section.section_id.clone()),
                ),
                (
                    "section_kind".to_string(),
                    Json::Str(section.section_kind.clone()),
                ),
                ("image_backed".to_string(), Json::Bool(section.image_backed)),
            ];
            if let Some(address) = section.base_address {
                fields.push(("base_address".to_string(), Json::Int(address as i128)));
            }
            fields.push(("size".to_string(), Json::Int(section.size as i128)));
            fields.push(("bytes_hex".to_string(), Json::Str(hex(&section.bytes))));
            sections.push(Json::Object(fields));
        }

        let mut entries = vec![
            ("format_version".to_string(), text(codes::FORMAT_VERSION)),
            ("level".to_string(), Json::Int(1)),
            ("sections".to_string(), Json::Array(sections)),
        ];
        if let Some(symbols) = &self.symbols {
            let mut list = Vec::with_capacity(symbols.len());
            for symbol in symbols {
                list.push(symbol.to_json());
            }
            entries.push(("symbols".to_string(), Json::Array(list)));
        }
        entries.push(("fixups".to_string(), self.fixups_json()));
        entries.push((
            "fingerprint".to_string(),
            Json::Str(self.fingerprint.clone()),
        ));
        entries.push((
            "materializer_version".to_string(),
            Json::Str(MATERIALIZER_VERSION.to_string()),
        ));
        Json::Object(entries)
    }

    fn level_zero_json(&self) -> Json {
        Json::Object(vec![
            ("format_version".to_string(), text(codes::FORMAT_VERSION)),
            ("level".to_string(), Json::Int(0)),
            ("bytes_hex".to_string(), Json::Str(self.bytes_hex())),
            ("size".to_string(), Json::Int(self.bytes.len() as i128)),
            ("fixups".to_string(), self.fixups_json()),
            (
                "fingerprint".to_string(),
                Json::Str(self.fingerprint.clone()),
            ),
            (
                "materializer_version".to_string(),
                Json::Str(MATERIALIZER_VERSION.to_string()),
            ),
        ])
    }

    fn fixups_json(&self) -> Json {
        let mut fixups = Vec::with_capacity(self.fixups.len());
        for record in &self.fixups {
            fixups.push(record.to_json());
        }
        Json::Array(fixups)
    }
}

impl SymbolEntry {
    fn to_json(&self) -> Json {
        let mut fields = vec![
            ("symbol_id".to_string(), Json::Str(self.symbol_id.clone())),
            ("name".to_string(), Json::Str(self.name.clone())),
            ("kind".to_string(), Json::Str(self.kind.clone())),
            ("binding".to_string(), Json::Str(self.binding.clone())),
        ];
        if let Some(section_id) = &self.section_id {
            fields.push(("section_id".to_string(), Json::Str(section_id.clone())));
        }
        if let Some(offset) = self.offset {
            fields.push(("offset".to_string(), Json::Int(offset as i128)));
        }
        Json::Object(fields)
    }
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(nibble(byte >> 4));
        out.push(nibble(byte & 0x0F));
    }
    out
}

/// One RELA-shaped fixup record (`03_fixup_model.md` §8).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Record {
    pub fixup_id: String,
    pub section_id: String,
    pub offset: u64,
    pub field_descriptor: Vec<(u32, u32)>,
    pub target: FixupTarget,
    pub addend: i64,
    pub pc_reference_rule: PcRule,
    pub value_transform: Transform,
    pub transform_shift: Option<u32>,
    pub range_constraint: RangeConstraint,
    pub pair_group: Option<String>,
    pub pair_role: Option<String>,
}

impl Record {
    fn of(fixup: &Fixup) -> Self {
        Record {
            fixup_id: fixup.fixup_id.clone(),
            section_id: fixup.section_id.clone(),
            offset: fixup.offset,
            field_descriptor: fixup
                .field_descriptor
                .iter()
                .map(|field| (field.lsb, field.width))
                .collect(),
            target: fixup.target.clone(),
            addend: fixup.addend,
            pc_reference_rule: fixup.pc_reference_rule.clone(),
            value_transform: fixup.value_transform.clone(),
            transform_shift: fixup.transform_shift,
            range_constraint: fixup.range_constraint.clone(),
            pair_group: fixup.pair_group.clone(),
            pair_role: fixup.pair_role.as_ref().map(pair_role_name),
        }
    }

    fn to_json(&self) -> Json {
        let descriptor = self
            .field_descriptor
            .iter()
            .map(|(lsb, width)| {
                Json::Object(vec![
                    ("lsb".to_string(), Json::Int(*lsb as i128)),
                    ("width".to_string(), Json::Int(*width as i128)),
                ])
            })
            .collect();
        let mut entries = vec![
            ("fixup_id".to_string(), Json::Str(self.fixup_id.clone())),
            ("section_id".to_string(), Json::Str(self.section_id.clone())),
            ("offset".to_string(), Json::Int(self.offset as i128)),
            ("field_descriptor".to_string(), Json::Array(descriptor)),
            ("target".to_string(), target_json(&self.target)),
            ("addend".to_string(), Json::Int(self.addend as i128)),
            (
                "pc_reference_rule".to_string(),
                Json::Str(pc_rule_name(&self.pc_reference_rule).to_string()),
            ),
            (
                "value_transform".to_string(),
                Json::Str(transform_name(&self.value_transform).to_string()),
            ),
        ];
        if let Some(shift) = self.transform_shift {
            entries.push(("transform_shift".to_string(), Json::Int(shift as i128)));
        }
        entries.push((
            "range_constraint".to_string(),
            Json::Object(vec![
                (
                    "signed".to_string(),
                    Json::Bool(self.range_constraint.signed),
                ),
                (
                    "bits".to_string(),
                    Json::Int(self.range_constraint.bits as i128),
                ),
                (
                    "align_bits".to_string(),
                    Json::Int(self.range_constraint.align_bits as i128),
                ),
            ]),
        ));
        if let Some(group) = &self.pair_group {
            entries.push(("pair_group".to_string(), Json::Str(group.clone())));
        }
        if let Some(role) = &self.pair_role {
            entries.push(("pair_role".to_string(), Json::Str(role.clone())));
        }
        Json::Object(entries)
    }
}

fn text(value: &str) -> Json {
    Json::Str(value.to_string())
}

fn target_json(target: &FixupTarget) -> Json {
    match target {
        FixupTarget::Symbol(symbol_id) => Json::Object(vec![
            ("kind".to_string(), text("symbol")),
            ("symbol_id".to_string(), Json::Str(symbol_id.clone())),
        ]),
        FixupTarget::Absolute(address) => Json::Object(vec![
            ("kind".to_string(), text("absolute")),
            ("address".to_string(), Json::Int(*address as i128)),
        ]),
        FixupTarget::SectionRelative(section_id) => Json::Object(vec![
            ("kind".to_string(), text("section_relative")),
            ("section_id".to_string(), Json::Str(section_id.clone())),
        ]),
        FixupTarget::Unknown(kind) => {
            Json::Object(vec![("kind".to_string(), Json::Str(kind.clone()))])
        }
    }
}

fn pc_rule_name(rule: &PcRule) -> &str {
    match rule {
        PcRule::None => "none",
        PcRule::PcrelBegin => "pcrel_begin",
        PcRule::PcrelEnd => "pcrel_end",
        PcRule::PcrelPage => "pcrel_page",
        PcRule::PcrelHi => "pcrel_hi",
        PcRule::Unknown(name) => name,
    }
}

fn transform_name(transform: &Transform) -> &str {
    match transform {
        Transform::Identity => "identity",
        Transform::Scale => "scale",
        Transform::Page => "page",
        Transform::Hi20 => "hi20",
        Transform::Lo12I => "lo12_i",
        Transform::Lo12S => "lo12_s",
        Transform::PcrelHi20 => "pcrel_hi20",
        Transform::PcrelLo12 => "pcrel_lo12",
        Transform::Unknown(name) => name,
    }
}

fn pair_role_name(role: &fmp_model::plan::PairRole) -> String {
    match role {
        fmp_model::plan::PairRole::Hi => "hi".to_string(),
        fmp_model::plan::PairRole::Lo => "lo".to_string(),
        fmp_model::plan::PairRole::Unknown(name) => name.clone(),
    }
}

/// The `target` detail of `E-FIXUP-002`: the same identifier the validator
/// reports for the same target, so the two layers produce one identity.
fn target_name(target: &FixupTarget) -> String {
    match target {
        FixupTarget::Symbol(symbol_id) => symbol_id.clone(),
        FixupTarget::Absolute(address) => format!("{address}"),
        FixupTarget::SectionRelative(section_id) => section_id.clone(),
        FixupTarget::Unknown(kind) => kind.clone(),
    }
}

/// Validate, then emit. `Err` is the complete diagnostic set and no artifact.
pub fn materialize(plan: &Plan, definition: &Definition) -> Result<Artifact, Vec<Diagnostic>> {
    let mut errors = Vec::new();

    // Step 3: the plan's digest must name this definition exactly. A digest
    // mismatch is checked before any rule is applied, because the rules below
    // are the ones the digest vouches for.
    if plan.definition.digest != definition.digest {
        errors.push(
            Diagnostic::new(codes::E_DEF_001, "/definition_identity/digest")
                .with("declared", plan.definition.digest.as_str())
                .with("actual", definition.digest.as_str())
                .with(
                    "reason",
                    "definition digest does not match the loaded definition",
                ),
        );
    }

    // Steps 2, 4, 5, 6, 7 and the output gates.
    errors.extend(fmp_validate::check(plan, definition));
    diagnostic::sort(&mut errors);
    if !errors.is_empty() {
        return Err(errors);
    }

    emit(plan, definition)
}

fn emit(plan: &Plan, definition: &Definition) -> Result<Artifact, Vec<Diagnostic>> {
    let mut errors = Vec::new();
    let mut sections: Vec<SectionImage> = Vec::new();
    let mut records: Vec<Record> = Vec::new();

    for section_id in &plan.output.section_order {
        let section = match plan
            .sections
            .iter()
            .find(|section| &section.section_id == section_id)
        {
            Some(section) => section,
            None => {
                errors.push(internal("section_order names an unvalidated section"));
                continue;
            }
        };
        let mut bytes: Vec<u8> = Vec::new();
        if section.image_backed {
            bytes.resize(section.declared_size as usize, 0);
            for fragment in &section.fragments {
                let at = fragment.offset as usize;
                match &fragment.body {
                    FragmentBody::Fill(byte) => {
                        for offset in 0..fragment.size as usize {
                            bytes[at + offset] = *byte;
                        }
                    }
                    FragmentBody::Data(hex) => {
                        let payload = decode_hex(hex);
                        bytes[at..at + payload.len()].copy_from_slice(&payload);
                    }
                    FragmentBody::Instruction(instruction_id) => {
                        let instruction = match plan
                            .instructions
                            .iter()
                            .find(|instruction| &instruction.instruction_id == instruction_id)
                        {
                            Some(instruction) => instruction,
                            None => {
                                errors.push(internal("fragment names an unvalidated instruction"));
                                continue;
                            }
                        };
                        match encode_instruction(plan, definition, section, instruction) {
                            Ok(encoded) => {
                                bytes[at..at + encoded.len()].copy_from_slice(&encoded);
                            }
                            Err(found) => errors.extend(found),
                        }
                    }
                }
            }
        }
        // A non-image-backed section keeps its virtual size and has no bytes.
        sections.push(SectionImage {
            section_id: section.section_id.clone(),
            section_kind: section_kind_name(&section.section_kind).to_string(),
            image_backed: section.image_backed,
            base_address: section.base_address,
            size: section.declared_size,
            bytes,
        });
    }

    // Records are collected from the plan, not from the fragment walk, so the
    // order is `(section_id, offset, fixup_id)` regardless of layout order.
    for fixup in &plan.fixups {
        if matches!(fixup.resolution_mode, Mode::EmitRelocation) {
            records.push(Record::of(fixup));
        }
    }

    let symbols = if plan.output.include_symbol_table {
        let mut entries = Vec::with_capacity(plan.symbols.len());
        if let Some(order) = &plan.output.symbol_order {
            // §12: the declared order is the emitted order; the validator has
            // already required `symbols[]` to match it exactly.
            for symbol_id in order {
                match plan
                    .symbols
                    .iter()
                    .find(|symbol| &symbol.symbol_id == symbol_id)
                {
                    Some(symbol) => entries.push(SymbolEntry::of(symbol)),
                    None => errors.push(internal("symbol_order names an unvalidated symbol")),
                }
            }
        } else {
            let mut ordered: Vec<&fmp_model::plan::Symbol> = plan.symbols.iter().collect();
            ordered.sort_by(|left, right| left.symbol_id.cmp(&right.symbol_id));
            for symbol in ordered {
                entries.push(SymbolEntry::of(symbol));
            }
        }
        Some(entries)
    } else {
        None
    };

    if !errors.is_empty() {
        diagnostic::sort(&mut errors);
        return Err(errors);
    }

    // The Level 0 image is exactly the image-backed section bytes in
    // `section_order`, so a Level 1 plan is still checked by the oracle bytes.
    let image: Vec<u8> = sections
        .iter()
        .flat_map(|section| section.bytes.iter().copied())
        .collect();
    let level = match plan.output.artifact {
        fmp_model::plan::Artifact::Bytes => 0,
        fmp_model::plan::Artifact::Sections => 1,
        fmp_model::plan::Artifact::Unknown(_) => {
            return Err(vec![internal(
                "an unvalidated artifact value reached emission",
            )])
        }
    };

    Ok(Artifact {
        bytes: image,
        level,
        sections,
        symbols,
        fixups: records,
        fingerprint: fingerprint(plan, definition),
    })
}

impl SymbolEntry {
    fn of(symbol: &fmp_model::plan::Symbol) -> Self {
        SymbolEntry {
            symbol_id: symbol.symbol_id.clone(),
            name: symbol.name.clone(),
            kind: symbol_kind_name(&symbol.kind).to_string(),
            binding: binding_name(&symbol.binding).to_string(),
            section_id: symbol.section_id.clone(),
            offset: symbol.offset,
        }
    }
}

fn section_kind_name(kind: &fmp_model::plan::SectionKind) -> &str {
    match kind {
        fmp_model::plan::SectionKind::Code => "code",
        fmp_model::plan::SectionKind::Data => "data",
        fmp_model::plan::SectionKind::Rodata => "rodata",
        fmp_model::plan::SectionKind::Bss => "bss",
        fmp_model::plan::SectionKind::Unknown(name) => name,
    }
}

fn symbol_kind_name(kind: &fmp_model::plan::SymbolKind) -> &str {
    match kind {
        fmp_model::plan::SymbolKind::Defined => "defined",
        fmp_model::plan::SymbolKind::Undefined => "undefined",
        fmp_model::plan::SymbolKind::External => "external",
        fmp_model::plan::SymbolKind::Unknown(name) => name,
    }
}

fn binding_name(binding: &fmp_model::plan::Binding) -> &str {
    match binding {
        fmp_model::plan::Binding::Local => "local",
        fmp_model::plan::Binding::Global => "global",
        fmp_model::plan::Binding::Weak => "weak",
        fmp_model::plan::Binding::Unknown(name) => name,
    }
}

fn encode_instruction(
    plan: &Plan,
    definition: &Definition,
    section: &Section,
    instruction: &fmp_model::plan::Instruction,
) -> Result<Vec<u8>, Vec<Diagnostic>> {
    let mut errors = Vec::new();
    let form = match lookup(definition, &instruction.form_id) {
        Some(form) => form,
        None => return Err(vec![internal("validated form disappeared")]),
    };
    let mut bytes = form.template.clone();

    for (slot, operand) in form.slots.iter().zip(&instruction.operands) {
        let value = match (&slot.from, &operand.payload) {
            (SlotFrom::RegNumber, Payload::Register(register)) => Some(*register as i128),
            (SlotFrom::OperandValue, Payload::Value(value)) => Some(*value),
            // A fixup is the only writer for these bits; `check_operand` already
            // rejected every other combination.
            _ => None,
        };
        if let Some(value) = value {
            write_field(&mut bytes, slot, value);
        }
    }

    if bytes.len() as u64 != instruction.expected_size {
        errors.push(
            Diagnostic::new(
                codes::E_SIZE_001,
                instruction.path.clone() + "/expected_size",
            )
            .with("instruction_id", instruction.instruction_id.as_str())
            .with("expected", instruction.expected_size)
            .with("actual", bytes.len() as u64),
        );
        return Err(errors);
    }

    // The digest is a check on the encoded bytes, never an input to them.
    if let Some(declared) = &instruction.expected_digest {
        let actual = fmp_model::canonical::sha256_prefixed(&[&bytes]);
        if &actual != declared {
            errors.push(
                Diagnostic::new(
                    codes::E_BYTE_001,
                    instruction.path.clone() + "/expected_digest",
                )
                .with("instruction_id", instruction.instruction_id.as_str())
                .with("declared", declared.as_str())
                .with("actual", actual),
            );
            return Err(errors);
        }
    }

    for fixup in plan.fixups.iter().filter(|fixup| {
        fixup.section_id == section.section_id && fixup.offset == instruction.offset
    }) {
        match apply(fixup, plan, section, instruction, &mut bytes) {
            Ok(()) => {}
            Err(found) => errors.push(found),
        }
    }

    if errors.is_empty() {
        Ok(bytes)
    } else {
        Err(errors)
    }
}

/// Write one operand value into a form's slot, most significant placement first.
///
/// `placement.inverted` complements the chunk it carries (`ADR-0037`): EVEX and
/// VEX name their extension bits `B̄`/`R̄`, so a set extension bit is written as
/// zero. The complement is a constant, not a choice.
fn write_field(bytes: &mut [u8], slot: &Slot, value: i128) {
    let total = slot.width_bits;
    let masked = value & mask(total);
    let mut remaining = total;
    for placement in &slot.placements {
        remaining -= placement.width;
        let mut chunk = (masked >> remaining) & mask(placement.width);
        if placement.inverted {
            chunk ^= mask(placement.width);
        }
        write_bits(bytes, placement.bit_offset, placement.width, chunk);
    }
}

/// Apply one fixup to one instruction's bytes, exactly one mode.
fn apply(
    fixup: &Fixup,
    plan: &Plan,
    section: &Section,
    instruction: &fmp_model::plan::Instruction,
    bytes: &mut [u8],
) -> Result<(), Diagnostic> {
    match fixup.resolution_mode {
        Mode::EmitRelocation => {
            // Zero the covered bits and emit a record; never compute a value.
            for field in &fixup.field_descriptor {
                write_bits(bytes, field.lsb, field.width, 0);
            }
            Ok(())
        }
        Mode::ResolveInPlace => {
            let (source, absolute) = source(fixup, plan, section)?;
            let reference = match fixup.pc_reference_rule {
                PcRule::None => None,
                PcRule::PcrelBegin | PcRule::PcrelPage => Some(fixup.offset as i128),
                PcRule::PcrelEnd => Some(fixup.offset as i128 + instruction.expected_size as i128),
                // ADR-0010: the low half measures from the paired `hi`'s site.
                // The validator required that member to exist and to sit in this
                // same section, so the offset is on the same origin as `S`.
                PcRule::PcrelHi => match paired_hi_offset(fixup, plan) {
                    Some(offset) => Some(offset),
                    None => return Err(internal("validated pcrel_hi pair disappeared")),
                },
                PcRule::Unknown(_) => None,
            };
            // `S` and `P` must be measured from the same origin. A relative `S`
            // is only produced for a same-section PC-relative reference, so the
            // site offset is the right origin there. An absolute `S` needs the
            // site's base address; a missing base is never read as zero.
            let reference = match (reference, absolute) {
                (None, _) => None,
                (Some(offset), false) => Some(offset),
                (Some(offset), true) => match section.base_address {
                    Some(base) => Some(base as i128 + offset),
                    None => {
                        return Err(Diagnostic::new(
                            codes::E_FIXUP_002,
                            fixup.path.clone() + "/target",
                        )
                        .with("fixup_id", fixup.fixup_id.as_str())
                        .with("target", target_name(&fixup.target)))
                    }
                },
            };

            let value = source + fixup.addend as i128;
            let displaced = match reference {
                Some(reference) => value - reference,
                None => value,
            };

            // OD-09: alignment is checked on the pre-transform value, range on
            // the post-transform value. Intermediates are never checked.
            if fixup.range_constraint.align_bits > 0 {
                let unit = 1i128 << fixup.range_constraint.align_bits;
                if displaced % unit != 0 {
                    return Err(Diagnostic::new(
                        codes::E_RANGE_003,
                        fixup.path.clone() + "/value_transform",
                    )
                    .with("required_align", fixup.range_constraint.align_bits)
                    .with("value", displaced));
                }
            }

            let transformed = match &fixup.value_transform {
                Transform::Identity => displaced,
                Transform::Scale => {
                    let shift = fixup.transform_shift.unwrap_or(0);
                    displaced >> shift
                }
                Transform::Page => {
                    let reference = match reference {
                        Some(reference) => reference,
                        None => {
                            return Err(internal(
                                "value_transform `page` needs a pc_reference_rule",
                            ))
                        }
                    };
                    (page(value) - page(reference)) >> 12
                }
                Transform::Lo12I => value & 0xFFF,
                Transform::PcrelHi20 => (displaced + 0x800) >> 12,
                // A mask, never range-checked — the same class as `lo12_i`,
                // applied to the displaced value (ADR-0010).
                Transform::PcrelLo12 => displaced & 0xFFF,
                // `fmp/0.1` has no semantics for these; `check_fixup_kind`
                // rejected the plan before emission.
                Transform::Hi20 | Transform::Lo12S | Transform::Unknown(_) => {
                    return Err(internal("validated transform disappeared"))
                }
            };

            if !matches!(
                fixup.value_transform,
                Transform::Lo12I | Transform::PcrelLo12
            ) {
                let constraint = &fixup.range_constraint;
                let (min, max) = if constraint.signed {
                    (
                        -(1i128 << (constraint.bits - 1)),
                        (1i128 << (constraint.bits - 1)) - 1,
                    )
                } else {
                    (0, (1i128 << constraint.bits) - 1)
                };
                if transformed < min || transformed > max {
                    return Err(Diagnostic::new(codes::E_FIXUP_003, fixup.path.clone())
                        .with("fixup_id", fixup.fixup_id.as_str())
                        .with("min", min)
                        .with("max", max)
                        .with("value", transformed));
                }
            }

            write_descriptor(bytes, fixup, transformed);
            Ok(())
        }
        Mode::Unknown(_) => Err(internal("validated resolution_mode disappeared")),
    }
}

/// `P` for `pcrel_hi`: the site offset of the group's single `hi` member.
///
/// `check_fixup_pairs` already required exactly one `hi` in the group and kept
/// it in the low half's section, so a `None` here is an internal inconsistency,
/// never a plan that should resolve some other way.
fn paired_hi_offset(fixup: &Fixup, plan: &Plan) -> Option<i128> {
    let group = fixup.pair_group.as_deref()?;
    plan.fixups
        .iter()
        .find(|other| {
            other.pair_group.as_deref() == Some(group)
                && matches!(other.pair_role, Some(fmp_model::plan::PairRole::Hi))
        })
        .map(|hi| hi.offset as i128)
}

/// `S`: the target's value, plus whether it is an absolute address.
fn source(fixup: &Fixup, plan: &Plan, site: &Section) -> Result<(i128, bool), Diagnostic> {
    match &fixup.target {
        FixupTarget::Absolute(address) => Ok((*address as i128, true)),
        FixupTarget::SectionRelative(section_id) => {
            let section = plan
                .sections
                .iter()
                .find(|section| &section.section_id == section_id)
                .ok_or_else(|| internal("validated target section disappeared"))?;
            match section.base_address {
                Some(base) => Ok((base as i128, true)),
                None => Err(
                    Diagnostic::new(codes::E_FIXUP_002, fixup.path.clone() + "/target")
                        .with("fixup_id", fixup.fixup_id.as_str())
                        .with("target", section_id.as_str()),
                ),
            }
        }
        FixupTarget::Symbol(symbol_id) => {
            let symbol = plan
                .symbols
                .iter()
                .find(|symbol| &symbol.symbol_id == symbol_id)
                .ok_or_else(|| internal("validated symbol disappeared"))?;
            let offset = symbol
                .offset
                .ok_or_else(|| internal("validated symbol has no location"))?
                as i128;
            // A same-section PC-relative reference is translation-invariant, so
            // offsets alone are exact; anything else needs the section base.
            let section = symbol.section_id.as_deref().and_then(|section_id| {
                plan.sections
                    .iter()
                    .find(|section| section.section_id == section_id)
            });
            let same_section = symbol.section_id.as_deref() == Some(site.section_id.as_str());
            // `pcrel_hi`'s reference point is in the same section by
            // construction (ADR-0010), so offsets alone stay exact.
            let offsets_are_enough = same_section
                && matches!(
                    fixup.pc_reference_rule,
                    PcRule::PcrelBegin | PcRule::PcrelEnd | PcRule::PcrelHi
                );
            match section.and_then(|section| section.base_address) {
                Some(base) if !offsets_are_enough => Ok((base as i128 + offset, true)),
                _ if offsets_are_enough => Ok((offset, false)),
                _ => Err(
                    Diagnostic::new(codes::E_FIXUP_002, fixup.path.clone() + "/target")
                        .with("fixup_id", fixup.fixup_id.as_str())
                        .with("target", symbol_id.as_str()),
                ),
            }
        }
        FixupTarget::Unknown(_) => Err(internal("validated target kind disappeared")),
    }
}

/// Place a masked value into the descriptor, first entry most significant.
fn write_descriptor(bytes: &mut [u8], fixup: &Fixup, value: i128) {
    let total = fixup.range_constraint.bits;
    let masked = value & mask(total);
    let mut remaining = total;
    for field in &fixup.field_descriptor {
        remaining -= field.width;
        let chunk = (masked >> remaining) & mask(field.width);
        write_bits(bytes, field.lsb, field.width, chunk);
    }
}

fn mask(width: u32) -> i128 {
    if width >= 128 {
        -1
    } else {
        (1i128 << width) - 1
    }
}

/// Write `width` bits of `value` at `lsb`, in little-endian template numbering
/// (bit 0 is the least significant bit of byte 0) — the same convention
/// `definitions/` uses for placements.
fn write_bits(bytes: &mut [u8], lsb: u32, width: u32, value: i128) {
    for index in 0..width {
        let bit = lsb + index;
        let byte = (bit / 8) as usize;
        let offset = bit % 8;
        let set = (value >> index) & 1 == 1;
        if set {
            bytes[byte] |= 1 << offset;
        } else {
            bytes[byte] &= !(1 << offset);
        }
    }
}

fn lookup<'a>(definition: &'a Definition, form_id: &str) -> Option<&'a Form> {
    definition.forms.iter().find(|form| form.form_id == form_id)
}

fn decode_hex(text: &str) -> Vec<u8> {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len() / 2);
    for pair in bytes.chunks(2) {
        let high = digit(pair[0]);
        let low = digit(pair[1]);
        out.push(high * 16 + low);
    }
    out
}

fn digit(byte: u8) -> u8 {
    match byte {
        b'0'..=b'9' => byte - b'0',
        b'a'..=b'f' => byte - b'a' + 10,
        _ => 0,
    }
}

fn nibble(value: u8) -> char {
    match value {
        0..=9 => (b'0' + value) as char,
        _ => (b'a' + value - 10) as char,
    }
}

fn page(value: i128) -> i128 {
    value & !0xFFF
}

fn internal(invariant: &str) -> Diagnostic {
    Diagnostic::new(codes::E_INTERNAL_001, "").with("invariant", invariant)
}

/// Contract §12's fingerprint, with `provenance` excluded as §12 requires.
pub fn fingerprint(plan: &Plan, definition: &Definition) -> String {
    let mut document = plan.document.clone();
    if let Json::Object(entries) = &mut document {
        entries.retain(|(key, _)| key != "provenance");
    }
    let canonical = fmp_model::canonical::canonical_bytes(&document);
    let identity = format!(
        "{}/{}\0{}",
        definition.namespace, definition.version, definition.digest
    );
    fmp_model::canonical::sha256_prefixed(&[
        codes::FORMAT_VERSION.as_bytes(),
        b"\0",
        &canonical,
        b"\0",
        identity.as_bytes(),
    ])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn plan_source() -> &'static str {
        include_str!("../../../../schema/examples/x86-mov-r64-r64.example.json")
    }

    fn definition_bytes() -> Vec<u8> {
        std::fs::read(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../definitions/x86_64/0.1.0.json"
        ))
        .expect("definition table is part of the repository")
    }

    #[test]
    fn encodes_the_example_plan() {
        let plan = fmp_model::plan::read(plan_source().as_bytes()).unwrap();
        let definition = fmp_model::definition::read(&definition_bytes()).unwrap();
        let artifact = materialize(&plan, &definition).unwrap();
        // dest = rax (rm), src = rcx (reg): `48 89 c8`, measured as
        // `movq %rcx, %rax` by llvm-mc (EXP-0004).
        assert_eq!(artifact.bytes_hex(), "4889c8");
        assert_eq!(artifact.fixups.len(), 0);
        assert!(artifact.fingerprint.starts_with("sha256:"));
    }

    #[test]
    fn write_field_is_most_significant_first() {
        let mut bytes = [0u8; 2];
        let slot = Slot {
            role: "x".to_string(),
            kind: "x".to_string(),
            target_type: "x".to_string(),
            from: SlotFrom::OperandValue,
            range: None,
            modifiers: Vec::new(),
            excluded: Vec::new(),
            placements: vec![
                fmp_model::definition::Placement {
                    bit_offset: 12,
                    width: 4,
                    inverted: false,
                },
                fmp_model::definition::Placement {
                    bit_offset: 0,
                    width: 8,
                    inverted: false,
                },
            ],
            width_bits: 12,
        };
        write_field(&mut bytes, &slot, 0xABC);
        // The high nibble goes to the high placement (byte 1, bits 4..8), the
        // low byte to the low placement.
        assert_eq!(bytes, [0xBC, 0xA0]);
    }

    #[test]
    fn write_field_inverts_a_marked_placement() {
        // `ADR-0037`: EVEX `B̄` carries the base's fourth bit complemented, so
        // base 8 writes 0 at bit 13. A raw write would emit `P0 = f1` and
        // encode `(%rax)` instead of `(%r8)` (`EXP-0039`).
        let mut bytes = [0u8; 2];
        let slot = Slot {
            role: "base".to_string(),
            kind: "x86.gpr64".to_string(),
            target_type: "rm64".to_string(),
            from: SlotFrom::RegNumber,
            range: None,
            modifiers: Vec::new(),
            excluded: Vec::new(),
            placements: vec![
                fmp_model::definition::Placement {
                    bit_offset: 13,
                    width: 1,
                    inverted: true,
                },
                fmp_model::definition::Placement {
                    bit_offset: 0,
                    width: 3,
                    inverted: false,
                },
            ],
            width_bits: 4,
        };
        write_field(&mut bytes, &slot, 8);
        // Low three bits of 8 are 0 (bits 0..3), bit 3 is 1, written as 0 at 13.
        assert_eq!(bytes, [0x00, 0x00]);
        write_field(&mut bytes, &slot, 0);
        // Base 0 writes 1 at 13 (the template's `f1` byte keeps bit 5 set).
        assert_eq!(bytes, [0x00, 0x20]);
    }

    #[test]
    fn negative_values_are_masked_not_wrapped() {
        let mut bytes = [0u8; 1];
        write_bits(&mut bytes, 0, 8, -1i128 & mask(8));
        assert_eq!(bytes, [0xFF]);
    }

    #[test]
    fn fingerprint_ignores_provenance() {
        let plan = fmp_model::plan::read(plan_source().as_bytes()).unwrap();
        let definition = fmp_model::definition::read(&definition_bytes()).unwrap();
        let first = fingerprint(&plan, &definition);
        let mut document = plan.document.clone();
        if let Json::Object(entries) = &mut document {
            entries.push((
                "provenance".to_string(),
                Json::Object(vec![(
                    "materializer_version".to_string(),
                    Json::Str("different".to_string()),
                )]),
            ));
        }
        let second_plan = fmp_model::plan::bind(&document).unwrap();
        assert_eq!(first, fingerprint(&second_plan, &definition));
    }

    fn level_one_plan() -> Plan {
        fmp_model::plan::read(
            include_str!(
                "../../../../fixtures/x86_64/positive/X86-P71-level-one-sections.fmp.json"
            )
            .as_bytes(),
        )
        .unwrap()
    }

    fn definition_for(relative: &str) -> Definition {
        let path = format!(
            "{}/../../../definitions/{}",
            env!("CARGO_MANIFEST_DIR"),
            relative
        );
        fmp_model::definition::read(&std::fs::read(path).unwrap()).unwrap()
    }

    #[test]
    fn level_one_splits_sections_and_keeps_the_level_zero_image() {
        let plan = level_one_plan();
        let definition = definition_for("x86_64/0.2.0.json");
        let artifact = materialize(&plan, &definition).unwrap();

        assert_eq!(artifact.level, 1);
        assert_eq!(artifact.sections.len(), 2);
        assert_eq!(artifact.sections[0].section_id, ".text");
        assert_eq!(artifact.sections[0].size, 43);
        assert_eq!(artifact.sections[0].bytes, artifact.bytes);
        assert_eq!(artifact.sections[1].section_id, ".bss");
        assert_eq!(artifact.sections[1].size, 8);
        assert!(!artifact.sections[1].image_backed);
        assert!(artifact.sections[1].bytes.is_empty());
    }

    #[test]
    fn level_one_symbols_follow_symbol_order() {
        let plan = level_one_plan();
        let definition = definition_for("x86_64/0.2.0.json");
        let artifact = materialize(&plan, &definition).unwrap();
        let symbols = artifact
            .symbols
            .as_ref()
            .expect("include_symbol_table is true");
        let ids: Vec<&str> = symbols
            .iter()
            .map(|symbol| symbol.symbol_id.as_str())
            .collect();
        // The plan declares `symbol_order` as ext, S2, S1; `symbol_id` order
        // would be S1, S2, ext, so this pins the declared order.
        assert_eq!(ids, ["ext", "S2", "S1"]);
        assert_eq!(symbols[2].name, "L1");
        assert_eq!(symbols[2].section_id.as_deref(), Some(".text"));
        assert_eq!(symbols[2].offset, Some(32));
    }

    #[test]
    fn level_one_without_symbol_table_omits_symbols() {
        let plan = level_one_plan();
        let mut document = plan.document.clone();
        if let Json::Object(entries) = &mut document {
            for (key, value) in entries {
                if key == "output_contract" {
                    if let Json::Object(fields) = value {
                        for (name, field) in fields {
                            if name == "include_symbol_table" {
                                *field = Json::Bool(false);
                            }
                        }
                    }
                }
            }
        }
        let plan = fmp_model::plan::bind(&document).unwrap();
        let definition = definition_for("x86_64/0.2.0.json");
        let artifact = materialize(&plan, &definition).unwrap();
        assert!(artifact.symbols.is_none());
        assert!(artifact.to_json().get("symbols").is_none());
    }

    #[test]
    fn level_zero_envelope_keeps_its_fields_and_order() {
        let plan = fmp_model::plan::read(plan_source().as_bytes()).unwrap();
        let definition = fmp_model::definition::read(&definition_bytes()).unwrap();
        let artifact = materialize(&plan, &definition).unwrap();
        let envelope = artifact.to_json();
        let keys: Vec<&str> = match &envelope {
            Json::Object(entries) => entries.iter().map(|(key, _)| key.as_str()).collect(),
            _ => panic!("an artifact envelope is an object"),
        };
        assert_eq!(
            keys,
            [
                "format_version",
                "level",
                "bytes_hex",
                "size",
                "fixups",
                "fingerprint",
                "materializer_version",
            ]
        );
        assert!(envelope.get("sections").is_none());
        assert!(envelope.get("symbols").is_none());
    }
}
