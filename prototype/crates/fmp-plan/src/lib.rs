//! Planner-side plan builder for FMP v0.
//!
//! The contract is `docs/fmp-v0/01_contract.md` §3–§12 and the boundary design
//! is `docs/fmp-v0/09_planner_api.md` (`ADR-0097`).
//!
//! This crate is a typed writer, not a second contract. It serializes exactly
//! the facts a caller passes and does nothing else: no instruction selection,
//! no encoding-form selection, no expansion, no layout, no padding, no
//! relaxation, no reordering, no range check, no symbol resolution, no
//! synthesis, no defaulting and no validation. The only authority remains
//! `fmp_model::plan::read` followed by `fmp_validate` and `fmp_materialize`.
//!
//! It depends only on `fmp-model`. The materializer must never link it.

#![forbid(unsafe_code)]

use fmp_model::canonical;
use fmp_model::codes;
use fmp_model::json::Json;
use fmp_model::plan as model;

/// Why a bound plan cannot be re-emitted through this builder.
///
/// The builder is a closed typed writer, so a value outside its closed sets has
/// no slot. `from_model` reports that instead of inventing a catch-all variant
/// (`ADR-0031`, `ADR-0097`).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Unrepresentable {
    /// The JSON Pointer of the offending value.
    pub path: String,
    /// The value the closed builder cannot express.
    pub value: String,
}

impl Unrepresentable {
    fn new(path: impl Into<String>, value: impl Into<String>) -> Self {
        Self {
            path: path.into(),
            value: value.into(),
        }
    }
}

impl std::fmt::Display for Unrepresentable {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: `{}` is not representable", self.path, self.value)
    }
}

impl std::error::Error for Unrepresentable {}

// ---------------------------------------------------------------------------
// Closed enums of the contract
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Artifact {
    Bytes,
    Sections,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FixupRecordOrder {
    SectionIdOffsetFixupId,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SectionKind {
    Code,
    Data,
    Rodata,
    Bss,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FragmentBody {
    Instruction(String),
    Data(Vec<u8>),
    Fill(u8),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SymbolKind {
    Defined,
    Undefined,
    External,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Binding {
    Local,
    Global,
    Weak,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Payload {
    Register(u64),
    Value(i128),
    Symbol(String),
    Empty,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ModifierValue {
    Int(i128),
    Text(String),
    Bool(bool),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FixupTarget {
    Symbol(String),
    Absolute(u64),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PcRule {
    None,
    PcrelBegin,
    PcrelEnd,
    PcrelPage,
    PcrelHi,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Transform {
    Identity,
    Scale,
    Page,
    Hi20,
    Lo12I,
    Lo12S,
    PcrelHi20,
    PcrelLo12,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ResolutionMode {
    ResolveInPlace,
    EmitRelocation,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PairRole {
    Hi,
    Lo,
}

// ---------------------------------------------------------------------------
// Contract objects
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TargetIdentity {
    pub isa_family: String,
    pub isa_variant: String,
    pub execution_mode: String,
    pub enabled_extensions: Vec<String>,
    pub feature_constraints: Vec<String>,
    pub byte_order: String,
    pub address_width: u32,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DefinitionIdentity {
    pub namespace: String,
    pub version: String,
    pub digest: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OutputContract {
    pub artifact: Artifact,
    pub section_order: Vec<String>,
    pub symbol_order: Option<Vec<String>>,
    pub fixup_record_order: FixupRecordOrder,
    pub include_symbol_table: bool,
    pub emit_fixups: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Section {
    pub section_id: String,
    pub section_kind: SectionKind,
    pub image_backed: bool,
    pub base_address: Option<u64>,
    pub declared_size: u64,
    pub fragments: Vec<Fragment>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Fragment {
    pub offset: u64,
    pub size: u64,
    pub body: FragmentBody,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Symbol {
    pub symbol_id: String,
    pub name: String,
    pub kind: SymbolKind,
    pub binding: Binding,
    pub section_id: Option<String>,
    pub offset: Option<u64>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Instruction {
    pub instruction_id: String,
    pub section_id: String,
    pub offset: u64,
    pub form_id: String,
    pub operands: Vec<Operand>,
    pub expected_size: u64,
    pub expected_digest: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Operand {
    pub role: String,
    pub kind: String,
    pub target_type: String,
    pub payload: Payload,
    pub modifiers: Vec<Modifier>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Modifier {
    pub name: String,
    pub value: ModifierValue,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Fixup {
    pub fixup_id: String,
    pub section_id: String,
    pub offset: u64,
    pub field_descriptor: Vec<FieldRange>,
    pub target: FixupTarget,
    pub addend: i64,
    pub pc_reference_rule: PcRule,
    pub value_transform: Transform,
    pub transform_shift: Option<u32>,
    pub range_constraint: RangeConstraint,
    pub resolution_mode: ResolutionMode,
    pub pair_group: Option<String>,
    pub pair_role: Option<PairRole>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FieldRange {
    pub lsb: u32,
    pub width: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RangeConstraint {
    pub signed: bool,
    pub bits: u32,
    pub align_bits: u32,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Provenance {
    pub materializer_version: String,
    pub build_profile: Option<String>,
    pub generated_by: Option<String>,
    pub notes: Option<String>,
}

// ---------------------------------------------------------------------------
// The builder
// ---------------------------------------------------------------------------

/// A total plan document. Every required root member is set by `new`; there is
/// no partial state and `build` cannot fail.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlanBuilder {
    target: TargetIdentity,
    definition: DefinitionIdentity,
    output: OutputContract,
    sections: Vec<Section>,
    symbols: Vec<Symbol>,
    instructions: Vec<Instruction>,
    fixups: Vec<Fixup>,
    provenance: Option<Provenance>,
}

impl PlanBuilder {
    /// The seven required root members. `format_version` is pinned by the crate.
    pub fn new(
        target: TargetIdentity,
        definition: DefinitionIdentity,
        output: OutputContract,
        sections: Vec<Section>,
        symbols: Vec<Symbol>,
        instructions: Vec<Instruction>,
        fixups: Vec<Fixup>,
    ) -> Self {
        Self {
            target,
            definition,
            output,
            sections,
            symbols,
            instructions,
            fixups,
            provenance: None,
        }
    }

    /// Set the single optional root member.
    pub fn provenance(mut self, provenance: Provenance) -> Self {
        self.provenance = Some(provenance);
        self
    }

    /// Serialize in caller order. No validation, no repair, no default.
    pub fn build(self) -> Json {
        let mut entries = vec![
            (
                "format_version".to_string(),
                Json::Str(codes::FORMAT_VERSION.to_string()),
            ),
            ("target_identity".to_string(), self.target.to_json()),
            ("definition_identity".to_string(), self.definition.to_json()),
            ("output_contract".to_string(), self.output.to_json()),
            (
                "sections".to_string(),
                Json::Array(self.sections.into_iter().map(Section::to_json).collect()),
            ),
            (
                "symbols".to_string(),
                Json::Array(self.symbols.into_iter().map(Symbol::to_json).collect()),
            ),
            (
                "instructions".to_string(),
                Json::Array(
                    self.instructions
                        .into_iter()
                        .map(Instruction::to_json)
                        .collect(),
                ),
            ),
            (
                "fixups".to_string(),
                Json::Array(self.fixups.into_iter().map(Fixup::to_json).collect()),
            ),
        ];
        if let Some(provenance) = self.provenance {
            entries.push(("provenance".to_string(), provenance.to_json()));
        }
        Json::Object(entries)
    }

    /// Canonical spelling of `build`: sorted keys, no insignificant whitespace,
    /// integers only. Array order is unchanged; §12's ordering is what the
    /// caller passes and the validator checks.
    pub fn build_canonical(self) -> Vec<u8> {
        canonical::canonical_bytes(&self.build())
    }

    /// Re-emit a bound plan, lossless over the frozen v0 surface.
    ///
    /// Fields outside that surface are dropped deliberately: the three `draft`
    /// fields, the schema-only `symbol.size`, and values the closed builder has
    /// no slot for (reported as [`Unrepresentable`]).
    pub fn from_model(plan: &model::Plan) -> Result<Self, Unrepresentable> {
        let target = TargetIdentity {
            isa_family: plan.target.isa_family.clone(),
            isa_variant: plan.target.isa_variant.clone(),
            execution_mode: plan.target.execution_mode.clone(),
            enabled_extensions: plan.target.enabled_extensions.clone(),
            feature_constraints: plan.target.feature_constraints.clone(),
            byte_order: plan.target.byte_order.clone(),
            address_width: plan.target.address_width,
        };
        let definition = DefinitionIdentity {
            namespace: plan.definition.namespace.clone(),
            version: plan.definition.version.clone(),
            digest: plan.definition.digest.clone(),
        };
        let output = OutputContract {
            artifact: match &plan.output.artifact {
                model::Artifact::Bytes => Artifact::Bytes,
                model::Artifact::Sections => Artifact::Sections,
                model::Artifact::Unknown(value) => {
                    return Err(Unrepresentable::new(
                        plan.output.path.clone() + "/artifact",
                        value.as_str(),
                    ))
                }
            },
            section_order: plan.output.section_order.clone(),
            symbol_order: plan.output.symbol_order.clone(),
            fixup_record_order: match plan.output.fixup_record_order.as_str() {
                "section_id,offset,fixup_id" => FixupRecordOrder::SectionIdOffsetFixupId,
                other => {
                    return Err(Unrepresentable::new(
                        plan.output.path.clone() + "/fixup_record_order",
                        other,
                    ))
                }
            },
            include_symbol_table: plan.output.include_symbol_table,
            emit_fixups: plan.output.emit_fixups,
        };

        let sections = plan
            .sections
            .iter()
            .map(|section| {
                let fragments = section
                    .fragments
                    .iter()
                    .map(|fragment| {
                        let body = match &fragment.body {
                            model::FragmentBody::Instruction(id) => {
                                FragmentBody::Instruction(id.clone())
                            }
                            model::FragmentBody::Data(hex) => {
                                FragmentBody::Data(decode_hex(hex).ok_or_else(|| {
                                    Unrepresentable::new(
                                        fragment.path.clone() + "/payload_hex",
                                        hex,
                                    )
                                })?)
                            }
                            model::FragmentBody::Fill(byte) => FragmentBody::Fill(*byte),
                        };
                        Ok(Fragment {
                            offset: fragment.offset,
                            size: fragment.size,
                            body,
                        })
                    })
                    .collect::<Result<Vec<_>, Unrepresentable>>()?;
                Ok(Section {
                    section_id: section.section_id.clone(),
                    section_kind: match &section.section_kind {
                        model::SectionKind::Code => SectionKind::Code,
                        model::SectionKind::Data => SectionKind::Data,
                        model::SectionKind::Rodata => SectionKind::Rodata,
                        model::SectionKind::Bss => SectionKind::Bss,
                        model::SectionKind::Unknown(value) => {
                            return Err(Unrepresentable::new(
                                section.path.clone() + "/section_kind",
                                value.as_str(),
                            ))
                        }
                    },
                    image_backed: section.image_backed,
                    base_address: section.base_address,
                    declared_size: section.declared_size,
                    fragments,
                })
            })
            .collect::<Result<Vec<_>, Unrepresentable>>()?;

        let symbols = plan
            .symbols
            .iter()
            .map(|symbol| {
                Ok(Symbol {
                    symbol_id: symbol.symbol_id.clone(),
                    name: symbol.name.clone(),
                    kind: match &symbol.kind {
                        model::SymbolKind::Defined => SymbolKind::Defined,
                        model::SymbolKind::Undefined => SymbolKind::Undefined,
                        model::SymbolKind::External => SymbolKind::External,
                        model::SymbolKind::Unknown(value) => {
                            return Err(Unrepresentable::new(
                                symbol.path.clone() + "/kind",
                                value.as_str(),
                            ))
                        }
                    },
                    binding: match &symbol.binding {
                        model::Binding::Local => Binding::Local,
                        model::Binding::Global => Binding::Global,
                        model::Binding::Weak => Binding::Weak,
                        model::Binding::Unknown(value) => {
                            return Err(Unrepresentable::new(
                                symbol.path.clone() + "/binding",
                                value.as_str(),
                            ))
                        }
                    },
                    section_id: symbol.section_id.clone(),
                    offset: symbol.offset,
                })
            })
            .collect::<Result<Vec<_>, Unrepresentable>>()?;

        let instructions = plan
            .instructions
            .iter()
            .map(|instruction| {
                let operands = instruction
                    .operands
                    .iter()
                    .map(|operand| Operand {
                        role: operand.role.clone(),
                        kind: operand.kind.clone(),
                        target_type: operand.target_type.clone(),
                        payload: match &operand.payload {
                            model::Payload::Register(register) => Payload::Register(*register),
                            model::Payload::Value(value) => Payload::Value(*value),
                            model::Payload::Symbol(symbol) => Payload::Symbol(symbol.clone()),
                            model::Payload::Empty => Payload::Empty,
                        },
                        modifiers: operand
                            .modifiers
                            .iter()
                            .map(|modifier| Modifier {
                                name: modifier.name.clone(),
                                value: match &modifier.value {
                                    model::ModifierValue::Int(value) => ModifierValue::Int(*value),
                                    model::ModifierValue::Text(value) => {
                                        ModifierValue::Text(value.clone())
                                    }
                                    model::ModifierValue::Bool(value) => {
                                        ModifierValue::Bool(*value)
                                    }
                                },
                            })
                            .collect(),
                    })
                    .collect();
                Ok(Instruction {
                    instruction_id: instruction.instruction_id.clone(),
                    section_id: instruction.section_id.clone(),
                    offset: instruction.offset,
                    form_id: instruction.form_id.clone(),
                    operands,
                    expected_size: instruction.expected_size,
                    expected_digest: instruction.expected_digest.clone(),
                })
            })
            .collect::<Result<Vec<_>, Unrepresentable>>()?;

        let fixups = plan
            .fixups
            .iter()
            .map(|fixup| {
                Ok(Fixup {
                    fixup_id: fixup.fixup_id.clone(),
                    section_id: fixup.section_id.clone(),
                    offset: fixup.offset,
                    field_descriptor: fixup
                        .field_descriptor
                        .iter()
                        .map(|range| FieldRange {
                            lsb: range.lsb,
                            width: range.width,
                        })
                        .collect(),
                    target: match &fixup.target {
                        model::FixupTarget::Symbol(symbol) => FixupTarget::Symbol(symbol.clone()),
                        model::FixupTarget::Absolute(address) => FixupTarget::Absolute(*address),
                        model::FixupTarget::SectionRelative(_) => {
                            return Err(Unrepresentable::new(
                                fixup.path.clone() + "/target/kind",
                                "section_relative",
                            ))
                        }
                        model::FixupTarget::Unknown(value) => {
                            return Err(Unrepresentable::new(
                                fixup.path.clone() + "/target/kind",
                                value.as_str(),
                            ))
                        }
                    },
                    addend: fixup.addend,
                    pc_reference_rule: match &fixup.pc_reference_rule {
                        model::PcRule::None => PcRule::None,
                        model::PcRule::PcrelBegin => PcRule::PcrelBegin,
                        model::PcRule::PcrelEnd => PcRule::PcrelEnd,
                        model::PcRule::PcrelPage => PcRule::PcrelPage,
                        model::PcRule::PcrelHi => PcRule::PcrelHi,
                        model::PcRule::Unknown(value) => {
                            return Err(Unrepresentable::new(
                                fixup.path.clone() + "/pc_reference_rule",
                                value.as_str(),
                            ))
                        }
                    },
                    value_transform: match &fixup.value_transform {
                        model::Transform::Identity => Transform::Identity,
                        model::Transform::Scale => Transform::Scale,
                        model::Transform::Page => Transform::Page,
                        model::Transform::Hi20 => Transform::Hi20,
                        model::Transform::Lo12I => Transform::Lo12I,
                        model::Transform::Lo12S => Transform::Lo12S,
                        model::Transform::PcrelHi20 => Transform::PcrelHi20,
                        model::Transform::PcrelLo12 => Transform::PcrelLo12,
                        model::Transform::Unknown(value) => {
                            return Err(Unrepresentable::new(
                                fixup.path.clone() + "/value_transform",
                                value.as_str(),
                            ))
                        }
                    },
                    transform_shift: fixup.transform_shift,
                    range_constraint: RangeConstraint {
                        signed: fixup.range_constraint.signed,
                        bits: fixup.range_constraint.bits,
                        align_bits: fixup.range_constraint.align_bits,
                    },
                    resolution_mode: match &fixup.resolution_mode {
                        model::Mode::ResolveInPlace => ResolutionMode::ResolveInPlace,
                        model::Mode::EmitRelocation => ResolutionMode::EmitRelocation,
                        model::Mode::Unknown(value) => {
                            return Err(Unrepresentable::new(
                                fixup.path.clone() + "/resolution_mode",
                                value.as_str(),
                            ))
                        }
                    },
                    pair_group: fixup.pair_group.clone(),
                    pair_role: match &fixup.pair_role {
                        None => None,
                        Some(model::PairRole::Hi) => Some(PairRole::Hi),
                        Some(model::PairRole::Lo) => Some(PairRole::Lo),
                        Some(model::PairRole::Unknown(value)) => {
                            return Err(Unrepresentable::new(
                                fixup.path.clone() + "/pair_role",
                                value.as_str(),
                            ))
                        }
                    },
                })
            })
            .collect::<Result<Vec<_>, Unrepresentable>>()?;

        let provenance = plan.provenance.as_ref().map(|provenance| Provenance {
            materializer_version: provenance.materializer_version.clone(),
            build_profile: provenance.build_profile.clone(),
            generated_by: provenance.generated_by.clone(),
            notes: provenance.notes.clone(),
        });

        Ok(Self {
            target,
            definition,
            output,
            sections,
            symbols,
            instructions,
            fixups,
            provenance,
        })
    }
}

// ---------------------------------------------------------------------------
// Serialization
// ---------------------------------------------------------------------------

impl TargetIdentity {
    fn to_json(&self) -> Json {
        object(vec![
            ("isa_family", string(&self.isa_family)),
            ("isa_variant", string(&self.isa_variant)),
            ("execution_mode", string(&self.execution_mode)),
            ("enabled_extensions", strings(&self.enabled_extensions)),
            ("feature_constraints", strings(&self.feature_constraints)),
            ("byte_order", string(&self.byte_order)),
            ("address_width", unsigned(self.address_width as u64)),
        ])
    }
}

impl DefinitionIdentity {
    fn to_json(&self) -> Json {
        object(vec![
            ("namespace", string(&self.namespace)),
            ("version", string(&self.version)),
            ("digest", string(&self.digest)),
        ])
    }
}

impl OutputContract {
    fn to_json(&self) -> Json {
        let mut entries = vec![
            (
                "artifact",
                string(match self.artifact {
                    Artifact::Bytes => "bytes",
                    Artifact::Sections => "sections",
                }),
            ),
            ("section_order", strings(&self.section_order)),
        ];
        if let Some(symbol_order) = &self.symbol_order {
            entries.push(("symbol_order", strings(symbol_order)));
        }
        entries.push((
            "fixup_record_order",
            string(match self.fixup_record_order {
                FixupRecordOrder::SectionIdOffsetFixupId => "section_id,offset,fixup_id",
            }),
        ));
        entries.push(("include_symbol_table", boolean(self.include_symbol_table)));
        entries.push(("emit_fixups", boolean(self.emit_fixups)));
        object(entries)
    }
}

impl Section {
    fn to_json(self) -> Json {
        let mut entries = vec![
            ("section_id", string(&self.section_id)),
            (
                "section_kind",
                string(match self.section_kind {
                    SectionKind::Code => "code",
                    SectionKind::Data => "data",
                    SectionKind::Rodata => "rodata",
                    SectionKind::Bss => "bss",
                }),
            ),
            ("image_backed", boolean(self.image_backed)),
        ];
        if let Some(base_address) = self.base_address {
            entries.push(("base_address", unsigned(base_address)));
        }
        entries.push(("declared_size", unsigned(self.declared_size)));
        entries.push((
            "fragments",
            Json::Array(self.fragments.into_iter().map(Fragment::to_json).collect()),
        ));
        object(entries)
    }
}

impl Fragment {
    fn to_json(self) -> Json {
        let mut entries = vec![
            ("offset", unsigned(self.offset)),
            ("size", unsigned(self.size)),
        ];
        match self.body {
            FragmentBody::Instruction(id) => {
                entries.push(("kind", string("instruction")));
                entries.push(("instruction_id", string(&id)));
            }
            FragmentBody::Data(bytes) => {
                entries.push(("kind", string("data")));
                entries.push(("payload_hex", string(&encode_hex(&bytes))));
            }
            FragmentBody::Fill(byte) => {
                entries.push(("kind", string("fill")));
                entries.push(("fill_byte", unsigned(byte as u64)));
            }
        }
        object(entries)
    }
}

impl Symbol {
    fn to_json(self) -> Json {
        let mut entries = vec![
            ("symbol_id", string(&self.symbol_id)),
            ("name", string(&self.name)),
            (
                "kind",
                string(match self.kind {
                    SymbolKind::Defined => "defined",
                    SymbolKind::Undefined => "undefined",
                    SymbolKind::External => "external",
                }),
            ),
            (
                "binding",
                string(match self.binding {
                    Binding::Local => "local",
                    Binding::Global => "global",
                    Binding::Weak => "weak",
                }),
            ),
        ];
        if let Some(section_id) = &self.section_id {
            entries.push(("section_id", string(section_id)));
        }
        if let Some(offset) = self.offset {
            entries.push(("offset", unsigned(offset)));
        }
        object(entries)
    }
}

impl Instruction {
    fn to_json(self) -> Json {
        let mut entries = vec![
            ("instruction_id", string(&self.instruction_id)),
            ("section_id", string(&self.section_id)),
            ("offset", unsigned(self.offset)),
            ("form_id", string(&self.form_id)),
            (
                "operands",
                Json::Array(self.operands.into_iter().map(Operand::to_json).collect()),
            ),
            ("expected_size", unsigned(self.expected_size)),
        ];
        if let Some(digest) = &self.expected_digest {
            entries.push(("expected_digest", string(digest)));
        }
        object(entries)
    }
}

impl Operand {
    fn to_json(self) -> Json {
        object(vec![
            ("role", string(&self.role)),
            ("kind", string(&self.kind)),
            ("target_type", string(&self.target_type)),
            ("payload", self.payload.to_json()),
            (
                "modifiers",
                Json::Array(self.modifiers.into_iter().map(Modifier::to_json).collect()),
            ),
        ])
    }
}

impl Payload {
    fn to_json(self) -> Json {
        match self {
            Payload::Register(register) => object(vec![("reg", unsigned(register))]),
            Payload::Value(value) => object(vec![("value", signed(value))]),
            Payload::Symbol(symbol) => object(vec![("symbol_id", string(&symbol))]),
            Payload::Empty => Json::Object(Vec::new()),
        }
    }
}

impl Modifier {
    fn to_json(self) -> Json {
        object(vec![
            ("name", string(&self.name)),
            (
                "value",
                match self.value {
                    ModifierValue::Int(value) => signed(value),
                    ModifierValue::Text(text) => string(&text),
                    ModifierValue::Bool(flag) => boolean(flag),
                },
            ),
        ])
    }
}

impl Fixup {
    fn to_json(self) -> Json {
        let mut entries = vec![
            ("fixup_id", string(&self.fixup_id)),
            ("section_id", string(&self.section_id)),
            ("offset", unsigned(self.offset)),
            (
                "field_descriptor",
                Json::Array(
                    self.field_descriptor
                        .into_iter()
                        .map(FieldRange::to_json)
                        .collect(),
                ),
            ),
            ("target", self.target.to_json()),
            ("addend", signed(self.addend as i128)),
            (
                "pc_reference_rule",
                string(match self.pc_reference_rule {
                    PcRule::None => "none",
                    PcRule::PcrelBegin => "pcrel_begin",
                    PcRule::PcrelEnd => "pcrel_end",
                    PcRule::PcrelPage => "pcrel_page",
                    PcRule::PcrelHi => "pcrel_hi",
                }),
            ),
            (
                "value_transform",
                string(match self.value_transform {
                    Transform::Identity => "identity",
                    Transform::Scale => "scale",
                    Transform::Page => "page",
                    Transform::Hi20 => "hi20",
                    Transform::Lo12I => "lo12_i",
                    Transform::Lo12S => "lo12_s",
                    Transform::PcrelHi20 => "pcrel_hi20",
                    Transform::PcrelLo12 => "pcrel_lo12",
                }),
            ),
        ];
        if let Some(shift) = self.transform_shift {
            entries.push(("transform_shift", unsigned(shift as u64)));
        }
        entries.push(("range_constraint", self.range_constraint.to_json()));
        entries.push((
            "resolution_mode",
            string(match self.resolution_mode {
                ResolutionMode::ResolveInPlace => "resolve_in_place",
                ResolutionMode::EmitRelocation => "emit_relocation",
            }),
        ));
        if let Some(group) = &self.pair_group {
            entries.push(("pair_group", string(group)));
        }
        if let Some(role) = self.pair_role {
            entries.push((
                "pair_role",
                string(match role {
                    PairRole::Hi => "hi",
                    PairRole::Lo => "lo",
                }),
            ));
        }
        object(entries)
    }
}

impl FieldRange {
    fn to_json(self) -> Json {
        object(vec![
            ("lsb", unsigned(self.lsb as u64)),
            ("width", unsigned(self.width as u64)),
        ])
    }
}

impl RangeConstraint {
    fn to_json(self) -> Json {
        object(vec![
            ("signed", boolean(self.signed)),
            ("bits", unsigned(self.bits as u64)),
            ("align_bits", unsigned(self.align_bits as u64)),
        ])
    }
}

impl FixupTarget {
    fn to_json(self) -> Json {
        match self {
            FixupTarget::Symbol(symbol) => object(vec![
                ("kind", string("symbol")),
                ("symbol_id", string(&symbol)),
            ]),
            FixupTarget::Absolute(address) => object(vec![
                ("kind", string("absolute")),
                ("address", unsigned(address)),
            ]),
        }
    }
}

impl Provenance {
    fn to_json(self) -> Json {
        let mut entries = vec![("materializer_version", string(&self.materializer_version))];
        if let Some(build_profile) = &self.build_profile {
            entries.push(("build_profile", string(build_profile)));
        }
        if let Some(generated_by) = &self.generated_by {
            entries.push(("generated_by", string(generated_by)));
        }
        if let Some(notes) = &self.notes {
            entries.push(("notes", string(notes)));
        }
        object(entries)
    }
}

// ---------------------------------------------------------------------------
// Small constructors
// ---------------------------------------------------------------------------

fn object(entries: Vec<(&str, Json)>) -> Json {
    Json::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.to_string(), value))
            .collect(),
    )
}

fn string(text: &str) -> Json {
    Json::Str(text.to_string())
}

fn strings(items: &[String]) -> Json {
    Json::Array(items.iter().map(|item| string(item)).collect())
}

fn unsigned(value: u64) -> Json {
    Json::Int(value as i128)
}

fn signed(value: i128) -> Json {
    Json::Int(value)
}

fn boolean(value: bool) -> Json {
    Json::Bool(value)
}

fn encode_hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(DIGITS[(byte >> 4) as usize] as char);
        out.push(DIGITS[(byte & 0x0F) as usize] as char);
    }
    out
}

fn decode_hex(text: &str) -> Option<Vec<u8>> {
    if text.len() % 2 != 0 {
        return None;
    }
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len() / 2);
    let mut index = 0;
    while index < bytes.len() {
        let high = hex_digit(bytes[index])?;
        let low = hex_digit(bytes[index + 1])?;
        out.push((high << 4) | low);
        index += 2;
    }
    Some(out)
}

fn hex_digit(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal() -> PlanBuilder {
        PlanBuilder::new(
            TargetIdentity {
                isa_family: "x86".to_string(),
                isa_variant: "x86-64".to_string(),
                execution_mode: "64".to_string(),
                enabled_extensions: Vec::new(),
                feature_constraints: Vec::new(),
                byte_order: "little".to_string(),
                address_width: 64,
            },
            DefinitionIdentity {
                namespace: "monasm.isa.x86".to_string(),
                version: "0.1.0".to_string(),
                digest: "sha256:00".to_string(),
            },
            OutputContract {
                artifact: Artifact::Bytes,
                section_order: vec![".text".to_string()],
                symbol_order: None,
                fixup_record_order: FixupRecordOrder::SectionIdOffsetFixupId,
                include_symbol_table: false,
                emit_fixups: true,
            },
            Vec::new(),
            Vec::new(),
            Vec::new(),
            Vec::new(),
        )
    }

    #[test]
    fn format_version_is_pinned() {
        let json = minimal().build();
        assert_eq!(
            json.get("format_version").and_then(Json::as_str),
            Some(codes::FORMAT_VERSION)
        );
    }

    #[test]
    fn absent_optional_fields_are_none_and_only_none_are_omitted() {
        let json = minimal().build();
        assert!(json.get("provenance").is_none());
        let output = json.get("output_contract").unwrap();
        assert!(output.get("symbol_order").is_none());
        assert_eq!(
            output.get("include_symbol_table").and_then(Json::as_bool),
            Some(false)
        );
    }

    #[test]
    fn build_is_deterministic() {
        assert_eq!(minimal().build_canonical(), minimal().build_canonical());
    }

    #[test]
    fn hex_round_trips_and_rejects_uppercase() {
        assert_eq!(encode_hex(&[0xaa, 0xbb, 0xcc, 0xdd]), "aabbccdd");
        assert_eq!(decode_hex("aabbccdd"), Some(vec![0xaa, 0xbb, 0xcc, 0xdd]));
        assert_eq!(decode_hex("AABB"), None);
        assert_eq!(decode_hex("abc"), None);
    }

    #[test]
    fn empty_payload_is_an_empty_object() {
        assert_eq!(Payload::Empty.to_json(), Json::Object(Vec::new()));
    }
}
