//! Static checks: `01_contract.md` §13 steps 2–7.
//!
//! Nothing here emits a byte. The functions collect diagnostics and return the
//! complete set, because §13 and `04_errors.md` §4 require the whole error set
//! before emission starts. Each function corresponds to one step so the order in
//! the contract can be read off the call site.

use fmp_model::codes;
use fmp_model::definition::{Definition, Form, Slot, SlotFrom};
use fmp_model::diagnostic::{self, Diagnostic};
use fmp_model::plan::{
    Artifact, Binding, Fixup, FixupTarget, FragmentBody, Mode, Payload, PcRule, Plan, Section,
    SectionKind, Symbol, SymbolKind, Transform,
};

/// The largest image `fmp/0.1` will build. The plan states a size; it does not
/// get to make the materializer allocate an arbitrary amount of memory.
const MAX_IMAGE_BYTES: u64 = 64 * 1024 * 1024;

/// A plan plus the definition it names, with ordered lookups.
///
/// Lookups are linear scans over `Vec`. A plan is small and a `HashMap` on a
/// byte-affecting path would make iteration order a hidden input (`INV-05`).
pub struct Model<'a> {
    pub plan: &'a Plan,
    pub definition: &'a Definition,
}

impl<'a> Model<'a> {
    pub fn new(plan: &'a Plan, definition: &'a Definition) -> Self {
        Model { plan, definition }
    }

    pub fn section(&self, section_id: &str) -> Option<&'a Section> {
        self.plan
            .sections
            .iter()
            .find(|section| section.section_id == section_id)
    }

    pub fn symbol(&self, symbol_id: &str) -> Option<&'a Symbol> {
        self.plan
            .symbols
            .iter()
            .find(|symbol| symbol.symbol_id == symbol_id)
    }

    pub fn instruction(
        &self,
        section_id: &str,
        offset: u64,
    ) -> Option<&'a fmp_model::plan::Instruction> {
        self.plan.instructions.iter().find(|instruction| {
            instruction.section_id == section_id && instruction.offset == offset
        })
    }

    pub fn form(&self, form_id: &str) -> Option<&'a Form> {
        self.definition
            .forms()
            .iter()
            .find(|form| form.form_id == form_id)
    }

    /// Fixups whose site is this instruction's first byte.
    pub fn fixups_at(&self, section_id: &str, offset: u64) -> Vec<&'a Fixup> {
        self.plan
            .fixups
            .iter()
            .filter(|fixup| fixup.section_id == section_id && fixup.offset == offset)
            .collect()
    }
}

/// Run steps 2–7 and return every diagnostic, sorted by `(path, code)`.
pub fn check(plan: &Plan, definition: &Definition) -> Vec<Diagnostic> {
    let model = Model::new(plan, definition);
    let mut errors = Vec::new();
    check_target(&model, &mut errors);
    check_output(&model, &mut errors);
    check_provenance(&model, &mut errors);
    check_layout(&model, &mut errors);
    check_symbols(&model, &mut errors);
    check_instructions(&model, &mut errors);
    check_fixups(&model, &mut errors);
    diagnostic::sort(&mut errors);
    errors
}

// ---------------------------------------------------------------------------
// Step 2: target identity
// ---------------------------------------------------------------------------

fn check_target(model: &Model, errors: &mut Vec<Diagnostic>) {
    let plan = &model.plan.target;
    let definition = model.definition.target();
    if !plan.feature_constraints.is_empty() {
        errors.push(
            Diagnostic::new(
                codes::E_VERSION_001,
                plan.path.clone() + "/feature_constraints",
            )
            .with("feature", plan.feature_constraints.join(","))
            .with("format_version", codes::FORMAT_VERSION),
        );
    }
    if plan.isa_family != definition.isa_family {
        errors.push(
            Diagnostic::new(codes::E_TARGET_001, plan.path.clone() + "/isa_family")
                .with("found", plan.isa_family.as_str()),
        );
    }
    if plan.isa_variant != definition.isa_variant {
        errors.push(
            Diagnostic::new(codes::E_TARGET_001, plan.path.clone() + "/isa_variant")
                .with("found", plan.isa_variant.as_str()),
        );
    }
    // `fmp-def/0.1` compares the sets for equality; `fmp-def/0.2` treats the
    // table's set as the ceiling and requires the plan's set to be a subset
    // (`07_definition_format.md` §2). A per-form requirement is checked later,
    // once the plan names a form (`E-TARGET-003`, step 6).
    let subset_rule = model.definition.definition_format() == codes::DEFINITION_FORMAT_V0_2;
    let plan_extensions: std::collections::BTreeSet<&str> =
        plan.enabled_extensions.iter().map(String::as_str).collect();
    let definition_extensions: std::collections::BTreeSet<&str> = definition
        .enabled_extensions
        .iter()
        .map(String::as_str)
        .collect();
    let extensions_mismatch = if subset_rule {
        !plan_extensions.is_subset(&definition_extensions)
    } else {
        plan_extensions != definition_extensions
    };
    if extensions_mismatch {
        errors.push(
            Diagnostic::new(
                codes::E_TARGET_001,
                plan.path.clone() + "/enabled_extensions",
            )
            .with("found", plan.enabled_extensions.join(",")),
        );
    }
    if plan.execution_mode != definition.execution_mode {
        errors.push(
            Diagnostic::new(codes::E_TARGET_002, plan.path.clone() + "/execution_mode")
                .with("found", plan.execution_mode.as_str())
                .with("required", definition.execution_mode.as_str()),
        );
    }
    if plan.byte_order != definition.byte_order {
        errors.push(
            Diagnostic::new(codes::E_TARGET_004, plan.path.clone() + "/byte_order")
                .with("found", plan.byte_order.as_str()),
        );
    }
    if plan.address_width != definition.address_width {
        errors.push(
            Diagnostic::new(codes::E_TARGET_004, plan.path.clone() + "/address_width")
                .with("found", plan.address_width),
        );
    }
}

// ---------------------------------------------------------------------------
// Output contract gates (ADR-0096: Level 0 and Level 1)
// ---------------------------------------------------------------------------

fn check_output(model: &Model, errors: &mut Vec<Diagnostic>) {
    let output = &model.plan.output;
    if let Artifact::Unknown(name) = &output.artifact {
        errors.push(
            Diagnostic::new(codes::E_VERSION_001, output.path.clone() + "/artifact")
                .with("feature", format!("artifact:{name}"))
                .with("format_version", codes::FORMAT_VERSION),
        );
    }
    // `include_symbol_table` selects the Level 1 `symbols[]`; at Level 0 there
    // is no table to select, so asking for one is a version error rather than a
    // field that is silently ignored (`ADR-0096`).
    if output.include_symbol_table && output.artifact != Artifact::Sections {
        errors.push(
            Diagnostic::new(
                codes::E_VERSION_001,
                output.path.clone() + "/include_symbol_table",
            )
            .with("feature", "include_symbol_table")
            .with("format_version", codes::FORMAT_VERSION),
        );
    }
    if !output.emit_fixups {
        errors.push(
            Diagnostic::new(codes::E_VERSION_001, output.path.clone() + "/emit_fixups")
                .with("feature", "emit_fixups")
                .with("format_version", codes::FORMAT_VERSION),
        );
    }
    if output.fixup_record_order != "section_id,offset,fixup_id" {
        errors.push(
            Diagnostic::new(
                codes::E_VERSION_001,
                output.path.clone() + "/fixup_record_order",
            )
            .with("feature", output.fixup_record_order.as_str())
            .with("format_version", codes::FORMAT_VERSION),
        );
    }
}

// ---------------------------------------------------------------------------
// Step 3: conditional provenance
// ---------------------------------------------------------------------------

/// Contract §7: when any `expected_digest` is present, its derivation source
/// must be named. The digest is a check against an independent oracle, and a
/// digest of unknown origin may be the encoder's own output, which would make the
/// check circular. `E-PLAN-006` reports the absence because the field is required
/// *in that case*, not optional with a default.
fn check_provenance(model: &Model, errors: &mut Vec<Diagnostic>) {
    let carries_digest = model
        .plan
        .instructions
        .iter()
        .any(|instruction| instruction.expected_digest.is_some());
    if !carries_digest {
        return;
    }
    let generated_by = model
        .plan
        .provenance
        .as_ref()
        .and_then(|provenance| provenance.generated_by.as_ref());
    if generated_by.is_none() {
        errors.push(
            Diagnostic::new(codes::E_PLAN_006, "/provenance")
                .with("field", "generated_by")
                .with("object", "provenance"),
        );
    }
}

// ---------------------------------------------------------------------------
// Step 4: sections, fragments, layout
// ---------------------------------------------------------------------------

fn check_layout(model: &Model, errors: &mut Vec<Diagnostic>) {
    let plan = model.plan;

    // `section_order` must be a permutation of `sections[]`: a section it omits
    // would vanish from the image with no diagnostic.
    let mut declared: Vec<&str> = plan
        .sections
        .iter()
        .map(|section| section.section_id.as_str())
        .collect();
    declared.sort_unstable();
    let mut ordered: Vec<&str> = plan
        .output
        .section_order
        .iter()
        .map(String::as_str)
        .collect();
    ordered.sort_unstable();
    if declared != ordered {
        errors.push(
            Diagnostic::new(
                codes::E_LAYOUT_006,
                plan.output.path.clone() + "/section_order",
            )
            .with("section_id", plan.output.section_order.join(","))
            .with("problem", "not a permutation of sections[]"),
        );
    }

    // The declared image is the sum over `section_order`. A plan cannot ask the
    // materializer to allocate an unbounded amount of memory; the limit is a
    // fixed property of this format version, not an environment input.
    let mut total: u128 = 0;
    for section_id in &plan.output.section_order {
        if let Some(section) = model.section(section_id) {
            total = total.saturating_add(u128::from(section.declared_size));
        }
    }
    if total > u128::from(MAX_IMAGE_BYTES) {
        errors.push(
            Diagnostic::new(
                codes::E_LIMIT_001,
                plan.output.path.clone() + "/section_order",
            )
            .with("limit", MAX_IMAGE_BYTES)
            .with("actual", total.to_string()),
        );
    }

    // Duplicate section ids make every reference to them ambiguous.
    for (index, section) in plan.sections.iter().enumerate() {
        if plan.sections[..index]
            .iter()
            .any(|other| other.section_id == section.section_id)
        {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_006, section.path.clone() + "/section_id")
                    .with("section_id", section.section_id.as_str())
                    .with("problem", "duplicate"),
            );
        }
        if let SectionKind::Unknown(name) = &section.section_kind {
            errors.push(
                Diagnostic::new(codes::E_VERSION_001, section.path.clone() + "/section_kind")
                    .with("feature", format!("section_kind:{name}"))
                    .with("format_version", codes::FORMAT_VERSION),
            );
        }
        check_fragments(model, section, errors);
    }

    // Every instruction must be owned by exactly one fragment.
    for instruction in &plan.instructions {
        let owned = plan.sections.iter().any(|section| {
            section.fragments.iter().any(|fragment| {
                matches!(&fragment.body, FragmentBody::Instruction(id)
                    if id == &instruction.instruction_id)
            })
        });
        if !owned {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_003, instruction.path.clone())
                    .with("instruction_id", instruction.instruction_id.as_str())
                    .with("fragment", ""),
            );
        }
    }

    // List order is part of the contract; it is never repaired (§3, §12).
    for (index, window) in plan.instructions.windows(2).enumerate() {
        let previous = (&window[0].section_id, window[0].offset);
        let current = (&window[1].section_id, window[1].offset);
        if current < previous {
            errors.push(
                Diagnostic::new(
                    codes::E_LAYOUT_004,
                    plan.instructions[index + 1].path.clone(),
                )
                .with("list", "instructions")
                .with("index", index + 1),
            );
        }
    }
    for (index, window) in plan.fixups.windows(2).enumerate() {
        let previous = (&window[0].section_id, window[0].offset, &window[0].fixup_id);
        let current = (&window[1].section_id, window[1].offset, &window[1].fixup_id);
        if current < previous {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_004, plan.fixups[index + 1].path.clone())
                    .with("list", "fixups")
                    .with("index", index + 1),
            );
        }
    }
    if let Some(order) = &plan.output.symbol_order {
        // §12: `symbols` are serialized by `symbol_order` when it is present, so
        // both the order list and the list it orders must agree.
        let mut declared: Vec<&str> = plan
            .symbols
            .iter()
            .map(|symbol| symbol.symbol_id.as_str())
            .collect();
        declared.sort_unstable();
        let mut ordered: Vec<&str> = order.iter().map(String::as_str).collect();
        ordered.sort_unstable();
        let actual: Vec<&str> = plan
            .symbols
            .iter()
            .map(|symbol| symbol.symbol_id.as_str())
            .collect();
        let expected: Vec<&str> = order.iter().map(String::as_str).collect();
        let problem = if declared != ordered {
            Some("symbol_order")
        } else if actual != expected {
            Some("symbols")
        } else {
            None
        };
        if let Some(list) = problem {
            errors.push(
                Diagnostic::new(
                    codes::E_LAYOUT_004,
                    plan.output.path.clone() + "/symbol_order",
                )
                .with("list", list)
                .with("index", 0usize),
            );
        }
    } else {
        for (index, window) in plan.symbols.windows(2).enumerate() {
            if window[0].symbol_id > window[1].symbol_id {
                errors.push(
                    Diagnostic::new(codes::E_LAYOUT_004, plan.symbols[index + 1].path.clone())
                        .with("list", "symbols")
                        .with("index", index + 1),
                );
            }
        }
    }
}

fn check_fragments(model: &Model, section: &Section, errors: &mut Vec<Diagnostic>) {
    if !section.image_backed {
        // `image_backed: false` means the section occupies no file bytes, so a
        // fragment there would ask for bytes that are never emitted, while
        // `declared_size` stays virtual. The two cannot both be true.
        for fragment in &section.fragments {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_002, fragment.path.clone())
                    .with("declared", 0u64)
                    .with("covered", fragment.size),
            );
        }
        return;
    }
    let mut cursor: u64 = 0;
    for (index, fragment) in section.fragments.iter().enumerate() {
        if fragment.offset < cursor {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_001, fragment.path.clone())
                    .with("first", fragment.offset)
                    .with("second", cursor),
            );
        } else if fragment.offset > cursor {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_002, fragment.path.clone())
                    .with("declared", section.declared_size)
                    .with("covered", cursor),
            );
        }
        if fragment.offset < cursor || fragment.offset > cursor {
            // A gap or overlap breaks the chain; keep going from the fragment's
            // own end so later diagnostics stay meaningful.
            cursor = fragment.offset;
        }
        cursor = cursor.saturating_add(fragment.size);
        if index == section.fragments.len() - 1 && cursor != section.declared_size {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_002, fragment.path.clone())
                    .with("declared", section.declared_size)
                    .with("covered", cursor),
            );
        }
        match &fragment.body {
            FragmentBody::Data(hex) => {
                let actual = (hex.len() / 2) as u64;
                if actual != fragment.size {
                    errors.push(
                        Diagnostic::new(
                            codes::E_LAYOUT_002,
                            fragment.path.clone() + "/payload_hex",
                        )
                        .with("declared", fragment.size)
                        .with("covered", actual),
                    );
                }
            }
            FragmentBody::Instruction(instruction_id) => {
                match model
                    .plan
                    .instructions
                    .iter()
                    .find(|instruction| &instruction.instruction_id == instruction_id)
                {
                    None => errors.push(
                        Diagnostic::new(codes::E_LAYOUT_003, fragment.path.clone())
                            .with("instruction_id", instruction_id.as_str())
                            .with("fragment", fragment.path.as_str()),
                    ),
                    Some(instruction) => {
                        if instruction.section_id != section.section_id
                            || instruction.offset != fragment.offset
                            || instruction.expected_size != fragment.size
                        {
                            errors.push(
                                Diagnostic::new(codes::E_LAYOUT_003, instruction.path.clone())
                                    .with("instruction_id", instruction.instruction_id.as_str())
                                    .with("fragment", fragment.path.as_str()),
                            );
                        }
                    }
                }
            }
            FragmentBody::Fill(_) => {}
        }
    }
    if section.fragments.is_empty() && section.declared_size != 0 {
        errors.push(
            Diagnostic::new(codes::E_LAYOUT_002, section.path.clone())
                .with("declared", section.declared_size)
                .with("covered", 0u64),
        );
    }
}

// ---------------------------------------------------------------------------
// Step 5: symbols
// ---------------------------------------------------------------------------

fn check_symbols(model: &Model, errors: &mut Vec<Diagnostic>) {
    let plan = model.plan;
    for (index, symbol) in plan.symbols.iter().enumerate() {
        if plan.symbols[..index]
            .iter()
            .any(|other| other.symbol_id == symbol.symbol_id)
        {
            errors.push(
                Diagnostic::new(codes::E_SYMBOL_002, symbol.path.clone() + "/symbol_id")
                    .with("symbol_id", symbol.symbol_id.as_str()),
            );
        }
        if let SymbolKind::Unknown(name) = &symbol.kind {
            errors.push(
                Diagnostic::new(codes::E_VERSION_001, symbol.path.clone() + "/kind")
                    .with("feature", format!("symbol.kind:{name}"))
                    .with("format_version", codes::FORMAT_VERSION),
            );
        }
        if let Binding::Unknown(name) = &symbol.binding {
            errors.push(
                Diagnostic::new(codes::E_VERSION_001, symbol.path.clone() + "/binding")
                    .with("feature", format!("symbol.binding:{name}"))
                    .with("format_version", codes::FORMAT_VERSION),
            );
        }
        match symbol.kind {
            SymbolKind::Defined => {
                // Equality is legal: a symbol at `declared_size` is the
                // one-past-the-end label the v0 vectors already use.
                let located = match (&symbol.section_id, symbol.offset) {
                    (Some(section_id), Some(offset)) => model
                        .section(section_id)
                        .is_some_and(|section| offset <= section.declared_size),
                    _ => false,
                };
                if !located {
                    errors.push(
                        Diagnostic::new(codes::E_SYMBOL_003, symbol.path.clone())
                            .with("symbol_id", symbol.symbol_id.as_str()),
                    );
                }
            }
            SymbolKind::Undefined | SymbolKind::External => {
                if symbol.section_id.is_some() || symbol.offset.is_some() {
                    errors.push(
                        Diagnostic::new(codes::E_SYMBOL_003, symbol.path.clone())
                            .with("symbol_id", symbol.symbol_id.as_str()),
                    );
                }
            }
            SymbolKind::Unknown(_) => {}
        }
    }

    // A duplicate emitted name with a different binding makes the object symbol
    // table ambiguous.
    for (index, symbol) in plan.symbols.iter().enumerate() {
        if plan.symbols[..index]
            .iter()
            .any(|other| other.name == symbol.name && other.binding != symbol.binding)
        {
            errors.push(
                Diagnostic::new(codes::E_SYMBOL_002, symbol.path.clone() + "/name")
                    .with("symbol_id", symbol.symbol_id.as_str()),
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Step 6: static instruction checks
// ---------------------------------------------------------------------------

fn check_instructions(model: &Model, errors: &mut Vec<Diagnostic>) {
    let plan_extensions: std::collections::BTreeSet<&str> = model
        .plan
        .target
        .enabled_extensions
        .iter()
        .map(String::as_str)
        .collect();
    for (index, instruction) in model.plan.instructions.iter().enumerate() {
        // §7: the id is unique within the plan, and §12 orders instructions by
        // `(section_id, offset)`. A repeated id leaves a fragment reference
        // ambiguous; a repeated site leaves the emission order as the tie-break.
        let earlier = &model.plan.instructions[..index];
        if earlier
            .iter()
            .any(|other| other.instruction_id == instruction.instruction_id)
        {
            errors.push(
                Diagnostic::new(
                    codes::E_LAYOUT_007,
                    instruction.path.clone() + "/instruction_id",
                )
                .with("instruction_id", instruction.instruction_id.as_str())
                .with("section_id", instruction.section_id.as_str())
                .with("offset", instruction.offset),
            );
        } else if earlier.iter().any(|other| {
            other.section_id == instruction.section_id && other.offset == instruction.offset
        }) {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_007, instruction.path.clone() + "/offset")
                    .with("instruction_id", instruction.instruction_id.as_str())
                    .with("section_id", instruction.section_id.as_str())
                    .with("offset", instruction.offset),
            );
        }

        if model.section(&instruction.section_id).is_none() {
            errors.push(
                Diagnostic::new(codes::E_LAYOUT_003, instruction.path.clone())
                    .with("instruction_id", instruction.instruction_id.as_str())
                    .with("fragment", ""),
            );
            continue;
        }
        let form = match model.form(&instruction.form_id) {
            Some(form) => form,
            None => {
                errors.push(
                    Diagnostic::new(codes::E_FORM_001, instruction.path.clone() + "/form_id")
                        .with("form_id", instruction.form_id.as_str())
                        .with("namespace", model.definition.namespace())
                        .with("version", model.definition.version()),
                );
                continue;
            }
        };
        // `fmp-def/0.2`: a named form states what it needs, so the plan's set
        // must cover it. The first missing name in the row's (sorted) order is
        // reported; the gate skips the operand checks so one instruction yields
        // one diagnostic (`07_definition_format.md` §2, `ADR-0103`).
        if model.definition.definition_format() == codes::DEFINITION_FORMAT_V0_2 {
            if let Some(missing) = form
                .requires_extensions
                .iter()
                .find(|extension| !plan_extensions.contains(extension.as_str()))
            {
                errors.push(
                    Diagnostic::new(codes::E_TARGET_003, instruction.path.clone() + "/form_id")
                        .with("extension", missing.as_str())
                        .with("form_id", instruction.form_id.as_str()),
                );
                continue;
            }
        }
        // The size is a property of the form; a plan that states a different
        // number is asking the materializer to reserve bytes the encoder cannot
        // fill. Check it before any `expected_size * 8` arithmetic.
        if instruction.expected_size != form.size() {
            errors.push(
                Diagnostic::new(
                    codes::E_SIZE_001,
                    instruction.path.clone() + "/expected_size",
                )
                .with("instruction_id", instruction.instruction_id.as_str())
                .with("expected", instruction.expected_size)
                .with("actual", form.size()),
            );
        }
        if instruction.operands.len() != form.slots.len() {
            errors.push(
                Diagnostic::new(codes::E_OPERAND_002, instruction.path.clone() + "/operands")
                    .with("expected", form.slots.len())
                    .with("found", instruction.operands.len()),
            );
            continue;
        }
        let expected_roles: Vec<&str> = form.slots.iter().map(|slot| slot.role.as_str()).collect();
        let found_roles: Vec<&str> = instruction
            .operands
            .iter()
            .map(|operand| operand.role.as_str())
            .collect();
        if expected_roles != found_roles {
            errors.push(
                Diagnostic::new(codes::E_OPERAND_002, instruction.path.clone() + "/operands")
                    .with("expected", expected_roles.join(","))
                    .with("found", found_roles.join(",")),
            );
            continue;
        }
        let covers = model.fixups_at(&instruction.section_id, instruction.offset);
        for (slot, operand) in form.slots.iter().zip(&instruction.operands) {
            check_operand(model, form, slot, operand, &covers, errors);
        }
    }
}

/// `E-RANGE-004`: the slot's domain is an interval minus a closed list of exact
/// values (ADR-0009). This is a lookup, never a predicate, and the path names the
/// payload leaf that carried the value.
fn excluded_diagnostic(
    operand: &fmp_model::plan::Operand,
    slot: &Slot,
    value: i128,
    leaf: &str,
) -> Diagnostic {
    let list = slot
        .excluded
        .iter()
        .map(|item| item.to_string())
        .collect::<Vec<_>>()
        .join(",");
    Diagnostic::new(codes::E_RANGE_004, operand.path.clone() + leaf)
        .with("target_type", slot.target_type.as_str())
        .with("value", value)
        .with("excluded", list)
}

fn check_operand(
    _model: &Model,
    form: &Form,
    slot: &Slot,
    operand: &fmp_model::plan::Operand,
    covers: &[&Fixup],
    errors: &mut Vec<Diagnostic>,
) {
    if operand.kind != slot.kind {
        errors.push(
            Diagnostic::new(codes::E_OPERAND_001, operand.path.clone() + "/kind")
                .with("expected", slot.kind.as_str())
                .with("found", operand.kind.as_str()),
        );
    }
    if operand.target_type != slot.target_type {
        errors.push(
            Diagnostic::new(codes::E_OPERAND_001, operand.path.clone() + "/target_type")
                .with("expected", slot.target_type.as_str())
                .with("found", operand.target_type.as_str()),
        );
    }
    for (index, window) in operand.modifiers.windows(2).enumerate() {
        if window[0].name > window[1].name {
            errors.push(
                Diagnostic::new(
                    codes::E_OPERAND_003,
                    operand.path.clone() + "/modifiers/" + &(index + 1).to_string(),
                )
                .with("kind", operand.kind.as_str())
                .with("reason", "modifiers are not sorted by name"),
            );
        }
    }
    for modifier in &operand.modifiers {
        let permitted = slot
            .modifiers
            .iter()
            .any(|allowed| allowed.name == modifier.name && allowed.value == modifier.value);
        if !permitted {
            errors.push(
                Diagnostic::new(codes::E_OPERAND_003, operand.path.clone() + "/modifiers")
                    .with("kind", operand.kind.as_str())
                    .with(
                        "reason",
                        format!("modifier `{}` is not permitted", modifier.name),
                    ),
            );
        }
    }

    let cover = cover_state(slot, covers);
    match slot.from {
        SlotFrom::RegNumber => match &operand.payload {
            Payload::Register(register) => {
                let field_bits = slot.width_bits;
                // `u128` so a 64-bit register still fits `1 << 64`, and
                // `checked_shl` so a definition that widens a slot past 127
                // bits cannot make the validator panic (H1a, D14).
                if 1u128
                    .checked_shl(field_bits)
                    .is_some_and(|modulus| u128::from(*register) >= modulus)
                {
                    errors.push(
                        Diagnostic::new(
                            codes::E_OPERAND_004,
                            operand.path.clone() + "/payload/reg",
                        )
                        .with("target_type", slot.target_type.as_str())
                        .with("value", *register)
                        .with("field_bits", field_bits),
                    );
                }
                // `E-RANGE-004`: the slot may exclude exact register numbers even
                // though they fit the field (`c.addi`'s `rd != 0`).
                let register_number = i128::from(*register);
                if slot.excluded.iter().any(|item| *item == register_number) {
                    errors.push(excluded_diagnostic(
                        operand,
                        slot,
                        register_number,
                        "/payload/reg",
                    ));
                }
            }
            other => errors.push(
                Diagnostic::new(codes::E_OPERAND_003, operand.path.clone() + "/payload")
                    .with("kind", operand.kind.as_str())
                    .with(
                        "reason",
                        format!(
                            "a reg_number slot needs {{reg}}, found {}",
                            payload_name(other)
                        ),
                    ),
            ),
        },
        SlotFrom::OperandValue => match &operand.payload {
            Payload::Value(value) => {
                if let Some(fixup) = cover.any() {
                    errors.push(
                        Diagnostic::new(codes::E_FIXUP_006, operand.path.clone() + "/payload")
                            .with("first", operand.path.as_str())
                            .with("second", fixup),
                    );
                }
                if let Some(range) = slot.range {
                    if range.align_bits > 0 {
                        // A shift of 128 or more is not a multiple of anything
                        // except zero; `checked_shl` keeps the panic out of a
                        // path a hand-edited definition can reach (H1a, D14).
                        let unit = 1i128.checked_shl(range.align_bits);
                        let misaligned = match unit {
                            Some(unit) => *value % unit != 0,
                            None => *value != 0,
                        };
                        if misaligned {
                            errors.push(
                                Diagnostic::new(
                                    codes::E_RANGE_003,
                                    operand.path.clone() + "/payload/value",
                                )
                                .with("required_align", range.align_bits)
                                .with("value", *value),
                            );
                        }
                    }
                    let (min, max) = if range.signed {
                        match 1i128.checked_shl(range.bits.saturating_sub(1)) {
                            Some(half) => (-half, half - 1),
                            None => (i128::MIN, i128::MAX),
                        }
                    } else {
                        match 1i128.checked_shl(range.bits) {
                            Some(limit) => (0, limit - 1),
                            None => (0, i128::MAX),
                        }
                    };
                    if *value < min || *value > max {
                        let code = if slot.role == "target" {
                            codes::E_RANGE_002
                        } else {
                            codes::E_RANGE_001
                        };
                        let mut diagnostic =
                            Diagnostic::new(code, operand.path.clone() + "/payload/value")
                                .with("min", min)
                                .with("max", max)
                                .with("value", *value);
                        if slot.role == "target" {
                            diagnostic = diagnostic
                                .with("bits", range.bits)
                                .with("align_bits", range.align_bits);
                        } else {
                            diagnostic = diagnostic.with("target_type", slot.target_type.as_str());
                        }
                        errors.push(diagnostic);
                    }
                }
                // `E-RANGE-004`: inside the interval, outside the legal set.
                if slot.excluded.iter().any(|item| *item == *value) {
                    errors.push(excluded_diagnostic(operand, slot, *value, "/payload/value"));
                }
            }
            Payload::Empty => {
                if cover.none() {
                    errors.push(
                        Diagnostic::new(codes::E_OPERAND_003, operand.path.clone() + "/payload")
                            .with("kind", operand.kind.as_str())
                            .with(
                                "reason",
                                "an operand_value slot has no value and no fixup covers it",
                            ),
                    );
                }
            }
            Payload::Symbol(symbol_id) => {
                if slot.role != "target" {
                    errors.push(
                        Diagnostic::new(codes::E_OPERAND_003, operand.path.clone() + "/payload")
                            .with("kind", operand.kind.as_str())
                            .with(
                                "reason",
                                "a symbol_id payload is only legal on a target operand",
                            ),
                    );
                } else if !cover.any().is_some_and(|fixup_id| {
                    covers
                        .iter()
                        .find(|candidate| candidate.fixup_id == fixup_id)
                        .is_some_and(|fixup| {
                            matches!(&fixup.target, FixupTarget::Symbol(id) if id == symbol_id)
                        })
                }) {
                    errors.push(
                        Diagnostic::new(codes::E_FIXUP_001, operand.path.clone() + "/payload")
                            .with("kind", "target")
                            .with("form_id", form.form_id.as_str())
                            .with("field", "target operand vs fixup.target"),
                    );
                }
            }
            Payload::Register(_) => errors.push(
                Diagnostic::new(codes::E_OPERAND_003, operand.path.clone() + "/payload")
                    .with("kind", operand.kind.as_str())
                    .with("reason", "an operand_value slot cannot take {reg}"),
            ),
        },
    }

    if let CoverState::Partial = cover {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_001, operand.path.clone())
                .with("kind", "field_descriptor")
                .with("form_id", form.form_id.as_str())
                .with("field", "fixup covers part of an operand field"),
        );
    }
}

fn payload_name(payload: &Payload) -> &'static str {
    match payload {
        Payload::Register(_) => "{reg}",
        Payload::Value(_) => "{value}",
        Payload::Symbol(_) => "{symbol_id}",
        Payload::Empty => "{}",
    }
}

/// How a slot's bits relate to the fixups that cover them.
enum CoverState<'a> {
    None,
    One(&'a str),
    Partial,
    Many,
}

impl<'a> CoverState<'a> {
    fn none(&self) -> bool {
        matches!(self, CoverState::None)
    }

    fn any(&self) -> Option<&'a str> {
        match self {
            CoverState::One(id) => Some(id),
            _ => None,
        }
    }
}

fn cover_state<'a>(slot: &Slot, covers: &[&'a Fixup]) -> CoverState<'a> {
    let mut hits: Vec<&'a str> = Vec::new();
    let mut partial = false;
    for fixup in covers {
        let mut intersection = 0u64;
        for (offset, width) in slot.owned_bits() {
            // `u64` endpoints: a descriptor entry is plan data, so its
            // `lsb + width` must not be able to wrap `u32` (H1a, D14).
            let slot_start = u64::from(offset);
            let slot_end = slot_start + u64::from(width);
            for field in &fixup.field_descriptor {
                let start = u64::from(field.lsb).max(slot_start);
                let end = (u64::from(field.lsb) + u64::from(field.width)).min(slot_end);
                if start < end {
                    intersection += end - start;
                }
            }
        }
        if intersection > 0 {
            if intersection < u64::from(slot.width_bits) {
                partial = true;
            }
            if !hits.contains(&fixup.fixup_id.as_str()) {
                hits.push(fixup.fixup_id.as_str());
            }
        }
    }
    if hits.is_empty() {
        CoverState::None
    } else if partial {
        CoverState::Partial
    } else if hits.len() > 1 {
        CoverState::Many
    } else {
        CoverState::One(hits[0])
    }
}

// ---------------------------------------------------------------------------
// Step 7: fixup compatibility
// ---------------------------------------------------------------------------

fn check_fixups(model: &Model, errors: &mut Vec<Diagnostic>) {
    for (index, fixup) in model.plan.fixups.iter().enumerate() {
        if model.plan.fixups[..index]
            .iter()
            .any(|other| other.fixup_id == fixup.fixup_id)
        {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_008, fixup.path.clone() + "/fixup_id")
                    .with("fixup_id", fixup.fixup_id.as_str())
                    .with("offset", fixup.offset),
            );
        }
        check_fixup_site(model, fixup, errors);
        check_fixup_target(model, fixup, errors);
        check_fixup_kind(fixup, errors);
        check_fixup_descriptor(model, fixup, errors);
    }
    check_fixup_overlap(model, errors);
    check_fixup_pairs(model, errors);
    check_one_writer(model, errors);
    check_fixup_ownership(model, errors);
}

fn check_fixup_site(model: &Model, fixup: &Fixup, errors: &mut Vec<Diagnostic>) {
    if model.section(&fixup.section_id).is_none() {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_005, fixup.path.clone() + "/section_id")
                .with("fixup_id", fixup.fixup_id.as_str())
                .with("descriptor", "site is in an undeclared section"),
        );
        return;
    }
    if model.instruction(&fixup.section_id, fixup.offset).is_none() {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_005, fixup.path.clone() + "/offset")
                .with("fixup_id", fixup.fixup_id.as_str())
                .with(
                    "descriptor",
                    "site must be the first byte of an instruction",
                ),
        );
    }
}

fn check_fixup_target(model: &Model, fixup: &Fixup, errors: &mut Vec<Diagnostic>) {
    match &fixup.target {
        FixupTarget::Symbol(symbol_id) => {
            let symbol = match model.symbol(symbol_id) {
                Some(symbol) => symbol,
                None => {
                    // Identity is checked in every mode: no resolution policy can
                    // supply a symbol the plan never declared (§5.1, N08).
                    errors.push(
                        Diagnostic::new(
                            codes::E_SYMBOL_001,
                            fixup.path.clone() + "/target/symbol_id",
                        )
                        .with("symbol_id", symbol_id.as_str())
                        .with("mode", mode_name(&fixup.resolution_mode)),
                    );
                    return;
                }
            };
            if !matches!(fixup.resolution_mode, Mode::ResolveInPlace) {
                // `emit_relocation` records the reference and never needs an
                // address, so an undefined or external symbol is legal here.
                return;
            }
            let located = matches!(symbol.kind, SymbolKind::Defined) && symbol.offset.is_some();
            if !located {
                errors.push(
                    Diagnostic::new(codes::E_FIXUP_002, fixup.path.clone() + "/target")
                        .with("fixup_id", fixup.fixup_id.as_str())
                        .with("target", symbol_id.as_str()),
                );
                return;
            }
            let same_section = symbol.section_id.as_deref() == Some(fixup.section_id.as_str());
            let offsets_are_enough = same_section
                && matches!(
                    fixup.pc_reference_rule,
                    PcRule::PcrelBegin | PcRule::PcrelEnd | PcRule::PcrelHi
                );
            if !offsets_are_enough {
                let bound = symbol
                    .section_id
                    .as_deref()
                    .and_then(|section_id| model.section(section_id))
                    .and_then(|section| section.base_address);
                if bound.is_none() {
                    // No base to compute `S` (or a page of `S`) from. A same-section
                    // PC-relative reference still resolves from offsets alone,
                    // which is why that case is excluded above.
                    errors.push(
                        Diagnostic::new(codes::E_FIXUP_002, fixup.path.clone() + "/target")
                            .with("fixup_id", fixup.fixup_id.as_str())
                            .with("target", symbol_id.as_str()),
                    );
                }
            }
        }
        FixupTarget::SectionRelative(_) => {
            // `03_fixup_model.md` §2.1: the kind is named by the schema but no
            // v0 fixture uses it, so `fmp/0.1` cannot honour it. Returning a
            // section's base address would invent semantics; the plan must name
            // a symbol instead.
            errors.push(
                Diagnostic::new(codes::E_VERSION_001, fixup.path.clone() + "/target/kind")
                    .with("feature", "target.kind:section_relative")
                    .with("format_version", codes::FORMAT_VERSION),
            );
        }
        FixupTarget::Absolute(address) => {
            // An absolute `S` shares a number line with `P`, and `P` is an
            // address. Without the site's base there is no origin to measure
            // either from; `none` needs no `P` and is exempt.
            if matches!(fixup.resolution_mode, Mode::ResolveInPlace)
                && !matches!(fixup.pc_reference_rule, PcRule::None)
            {
                let bound = model
                    .section(&fixup.section_id)
                    .and_then(|section| section.base_address);
                if bound.is_none() {
                    errors.push(
                        Diagnostic::new(codes::E_FIXUP_002, fixup.path.clone() + "/target")
                            .with("fixup_id", fixup.fixup_id.as_str())
                            .with("target", format!("{address}")),
                    );
                }
            }
        }
        FixupTarget::Unknown(kind) => errors.push(
            Diagnostic::new(codes::E_VERSION_001, fixup.path.clone() + "/target/kind")
                .with("feature", format!("target.kind:{kind}"))
                .with("format_version", codes::FORMAT_VERSION),
        ),
    }
}

fn check_fixup_kind(fixup: &Fixup, errors: &mut Vec<Diagnostic>) {
    if let PcRule::Unknown(name) = &fixup.pc_reference_rule {
        errors.push(
            Diagnostic::new(
                codes::E_VERSION_001,
                fixup.path.clone() + "/pc_reference_rule",
            )
            .with("feature", format!("pc_reference_rule:{name}"))
            .with("format_version", codes::FORMAT_VERSION),
        );
    }
    if let Mode::Unknown(name) = &fixup.resolution_mode {
        errors.push(
            Diagnostic::new(
                codes::E_VERSION_001,
                fixup.path.clone() + "/resolution_mode",
            )
            .with("feature", format!("resolution_mode:{name}"))
            .with("format_version", codes::FORMAT_VERSION),
        );
    }
    match &fixup.value_transform {
        Transform::Unknown(name) => errors.push(
            Diagnostic::new(
                codes::E_VERSION_001,
                fixup.path.clone() + "/value_transform",
            )
            .with("feature", format!("value_transform:{name}"))
            .with("format_version", codes::FORMAT_VERSION),
        ),
        Transform::Lo12S => errors.push(
            Diagnostic::new(
                codes::E_VERSION_001,
                fixup.path.clone() + "/value_transform",
            )
            .with("feature", "value_transform:lo12_s")
            .with("format_version", codes::FORMAT_VERSION),
        ),
        _ => {}
    }
    // ADR-0010: `pcrel_hi` and `pcrel_lo12` are one decision split across two
    // fields. A plan that names one without the other describes a displacement
    // whose reference point and mask disagree, so it is not a resolvable kind.
    if matches!(fixup.value_transform, Transform::PcrelLo12)
        && !matches!(fixup.pc_reference_rule, PcRule::PcrelHi)
    {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/value_transform")
                .with("kind", "value_transform:pcrel_lo12")
                .with("form_id", "")
                .with("field", "pcrel_lo12 requires pc_reference_rule pcrel_hi"),
        );
    }
    // `ADR-0127` / `03_fixup_model.md` §7: `page` is `page(S + A) - page(P)`.
    // Without `pcrel_page` there is no `P` to take the page of, and `apply`
    // would reach its `internal(...)` arm. Reject the kind here instead.
    if matches!(fixup.value_transform, Transform::Page)
        && !matches!(fixup.pc_reference_rule, PcRule::PcrelPage)
    {
        errors.push(
            Diagnostic::new(
                codes::E_FIXUP_001,
                fixup.path.clone() + "/pc_reference_rule",
            )
            .with("kind", "value_transform:page")
            .with("form_id", "")
            .with("field", "page requires pc_reference_rule pcrel_page"),
        );
    }
    if matches!(fixup.value_transform, Transform::Hi20)
        && !matches!(fixup.pc_reference_rule, PcRule::None)
    {
        // `03_fixup_model.md` §6: the absolute split is `hi20` over `S + A`;
        // the low half masks the absolute `S + A`, so a PC rule here would
        // subtract `P` from the high half only.
        errors.push(
            Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/value_transform")
                .with("kind", "value_transform:hi20")
                .with("form_id", "")
                .with("field", "hi20 requires pc_reference_rule none"),
        );
    }
    if matches!(fixup.pc_reference_rule, PcRule::PcrelHi)
        && !matches!(fixup.value_transform, Transform::PcrelLo12)
    {
        errors.push(
            Diagnostic::new(
                codes::E_FIXUP_001,
                fixup.path.clone() + "/pc_reference_rule",
            )
            .with("kind", "pc_reference_rule:pcrel_hi")
            .with("form_id", "")
            .with("field", "pcrel_hi requires value_transform pcrel_lo12"),
        );
    }
    // The high half already carried the addend into the shared displacement
    // (`03_fixup_model.md` §6.1), so a second one on the low half would be
    // added twice.
    if matches!(fixup.value_transform, Transform::PcrelLo12) && fixup.addend != 0 {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_009, fixup.path.clone() + "/addend")
                .with("fixup_id", fixup.fixup_id.as_str())
                .with("addend", fixup.addend)
                .with("value_transform", "pcrel_lo12"),
        );
    }
    let needs_shift = matches!(fixup.value_transform, Transform::Scale);
    if needs_shift && fixup.transform_shift.is_none() {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/transform_shift")
                .with("kind", "value_transform:scale")
                .with("form_id", "")
                .with("field", "scale needs transform_shift"),
        );
    }
    if !needs_shift && fixup.transform_shift.is_some() {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/transform_shift")
                .with("kind", "transform_shift")
                .with("form_id", "")
                .with("field", "transform_shift is only legal with scale"),
        );
    }
    if matches!(fixup.pair_role, Some(fmp_model::plan::PairRole::Unknown(_))) {
        errors.push(
            Diagnostic::new(codes::E_VERSION_001, fixup.path.clone() + "/pair_role")
                .with("feature", "pair_role:unknown")
                .with("format_version", codes::FORMAT_VERSION),
        );
    }
}

fn check_fixup_descriptor(model: &Model, fixup: &Fixup, errors: &mut Vec<Diagnostic>) {
    let instruction = match model.instruction(&fixup.section_id, fixup.offset) {
        Some(instruction) => instruction,
        None => return,
    };
    // The form, not `expected_size`, is the authority on how many bits exist.
    // §13 step 6 already rejected a plan whose `expected_size` disagrees.
    let form = match model.form(&instruction.form_id) {
        Some(form) => form,
        None => return,
    };
    let limit = form.size() * 8;
    let mut bits: Vec<(u32, u32)> = Vec::new();
    for field in &fixup.field_descriptor {
        let end = u64::from(field.lsb) + u64::from(field.width);
        if end > limit {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_005, fixup.path.clone() + "/field_descriptor")
                    .with("fixup_id", fixup.fixup_id.as_str())
                    .with(
                        "descriptor",
                        format!("[{}..{}] exceeds {limit} bits", field.lsb, end),
                    ),
            );
        }
        for (offset, width) in &bits {
            let prior_end = u64::from(*offset) + u64::from(*width);
            let field_end = u64::from(field.lsb) + u64::from(field.width);
            if u64::from(field.lsb) < prior_end && u64::from(*offset) < field_end {
                errors.push(
                    Diagnostic::new(codes::E_FIXUP_005, fixup.path.clone() + "/field_descriptor")
                        .with("fixup_id", fixup.fixup_id.as_str())
                        .with("descriptor", "descriptor entries overlap"),
                );
            }
        }
        bits.push((field.lsb, field.width));
    }
    // `u64` sum: two `u32::MAX` widths must yield a diagnostic, not a wrapped
    // total that happens to equal `range_constraint.bits` (H1a, D14).
    let total: u64 = fixup
        .field_descriptor
        .iter()
        .map(|field| u64::from(field.width))
        .sum();
    if total != u64::from(fixup.range_constraint.bits) {
        errors.push(
            Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/range_constraint")
                .with("kind", "field_descriptor")
                .with("form_id", instruction.form_id.as_str())
                .with(
                    "field",
                    format!(
                        "descriptor widths sum to {total}, range_constraint.bits is {}",
                        fixup.range_constraint.bits
                    ),
                ),
        );
    }
}

fn check_fixup_overlap(model: &Model, errors: &mut Vec<Diagnostic>) {
    for (index, fixup) in model.plan.fixups.iter().enumerate() {
        for other in &model.plan.fixups[..index] {
            if other.section_id != fixup.section_id {
                continue;
            }
            for a in &fixup.field_descriptor {
                for b in &other.field_descriptor {
                    // `u128`: `offset * 8` on a `u64::MAX` site would otherwise
                    // wrap and invent an overlap (H1a, D14).
                    let a_start = u128::from(fixup.offset) * 8 + u128::from(a.lsb);
                    let a_end = a_start + u128::from(a.width);
                    let b_start = u128::from(other.offset) * 8 + u128::from(b.lsb);
                    let b_end = b_start + u128::from(b.width);
                    if a_start < b_end && b_start < a_end {
                        errors.push(
                            Diagnostic::new(codes::E_FIXUP_006, fixup.path.clone())
                                .with("first", other.fixup_id.as_str())
                                .with("second", fixup.fixup_id.as_str()),
                        );
                    }
                }
            }
        }
    }
}

fn check_fixup_pairs(model: &Model, errors: &mut Vec<Diagnostic>) {
    let mut groups: Vec<(&str, Vec<&Fixup>)> = Vec::new();
    for fixup in model.fixup_groups() {
        groups.push(fixup);
    }
    for (group, members) in groups {
        let highs: Vec<&Fixup> = members
            .iter()
            .copied()
            .filter(|fixup| matches!(fixup.pair_role, Some(fmp_model::plan::PairRole::Hi)))
            .collect();
        let lows: Vec<&Fixup> = members
            .iter()
            .copied()
            .filter(|fixup| matches!(fixup.pair_role, Some(fmp_model::plan::PairRole::Lo)))
            .collect();
        // ADR-0010: one high part may serve several low parts (psABI
        // `riscv-elf.adoc:1580-1605`), so the count is 1:N, not 1:1.
        if highs.len() != 1 || lows.is_empty() {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_007, members[0].path.clone())
                    .with("pair_group", group)
                    .with("problem", "a pair needs exactly one hi and at least one lo"),
            );
            continue;
        }
        let hi = highs[0];
        if members
            .iter()
            .any(|fixup| !same_target(fixup.target.clone(), hi.target.clone()))
        {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_007, members[0].path.clone())
                    .with("pair_group", group)
                    .with("problem", "the group members reference different targets"),
            );
        }
        for lo in &lows {
            if matches!(lo.pc_reference_rule, PcRule::PcrelHi) && lo.section_id != hi.section_id {
                errors.push(
                    Diagnostic::new(codes::E_FIXUP_007, lo.path.clone() + "/pc_reference_rule")
                        .with("pair_group", group)
                        .with(
                            "problem",
                            "a pcrel_hi low half must be in its high half's section",
                        ),
                );
            }
        }
    }
    for fixup in &model.plan.fixups {
        if fixup.pair_group.is_none() && fixup.pair_role.is_some() {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_007, fixup.path.clone() + "/pair_role")
                    .with("pair_group", "")
                    .with("problem", "pair_role without pair_group"),
            );
        }
        if matches!(fixup.pc_reference_rule, PcRule::PcrelHi)
            && !matches!(fixup.pair_role, Some(fmp_model::plan::PairRole::Lo))
        {
            errors.push(
                Diagnostic::new(
                    codes::E_FIXUP_007,
                    fixup.path.clone() + "/pc_reference_rule",
                )
                .with("pair_group", fixup.pair_group.as_deref().unwrap_or(""))
                .with("problem", "pcrel_hi is only legal on a lo member"),
            );
        }
    }
}

fn same_target(a: FixupTarget, b: FixupTarget) -> bool {
    match (a, b) {
        (FixupTarget::Symbol(left), FixupTarget::Symbol(right)) => left == right,
        (FixupTarget::Absolute(left), FixupTarget::Absolute(right)) => left == right,
        (FixupTarget::SectionRelative(left), FixupTarget::SectionRelative(right)) => left == right,
        _ => false,
    }
}

/// A fixup-covered field must not also carry a base value in the template, and
/// two fixups must not share a bit. The operand half of this rule lives in
/// [`check_operand`] and [`check_fixup_ownership`], which are the places that
/// know the slot layout.
fn check_one_writer(model: &Model, errors: &mut Vec<Diagnostic>) {
    for fixup in &model.plan.fixups {
        let instruction = match model.instruction(&fixup.section_id, fixup.offset) {
            Some(instruction) => instruction,
            None => continue,
        };
        let form = match model.form(&instruction.form_id) {
            Some(form) => form,
            None => continue,
        };
        // One diagnostic per fixup, not one per set template bit: the failure is
        // "this fixup writes over a template value", and the bit count is an
        // artefact of how wide the field is.
        'fields: for field in &fixup.field_descriptor {
            // Clamp to the form: a descriptor wider than the instruction must
            // not turn a diagnostic into ~4e9 iterations (H1a, D14). Bits past
            // the template end are already `E-FIXUP-005`.
            let end = (u64::from(field.lsb) + u64::from(field.width)).min(u64::from(form.bits()));
            for bit in u64::from(field.lsb)..end {
                let byte = (bit / 8) as usize;
                if byte >= form.template.len() {
                    continue;
                }
                let set = form.template[byte] & (1 << (bit % 8)) != 0;
                if set {
                    errors.push(
                        Diagnostic::new(codes::E_FIXUP_006, fixup.path.clone())
                            .with("first", "template")
                            .with("second", fixup.fixup_id.as_str()),
                    );
                    break 'fields;
                }
            }
        }
    }
}

/// Every fixup must write exactly one operand-value field, and must write it in
/// the value order the slot declared.
///
/// The template check above sees static bits; this check sees the slot layout.
/// Without it a fixup could cover a `reg_number` slot (overwriting the register
/// the operand selected) or take bits from an opcode/modifier placement, and the
/// plan would be accepted while one of its statements is silently ignored.
fn check_fixup_ownership(model: &Model, errors: &mut Vec<Diagnostic>) {
    for fixup in &model.plan.fixups {
        let instruction = match model.instruction(&fixup.section_id, fixup.offset) {
            Some(instruction) => instruction,
            None => continue,
        };
        let form = match model.form(&instruction.form_id) {
            Some(form) => form,
            None => continue,
        };

        // A descriptor outside the instruction is `E-FIXUP-005`; do not add a
        // second diagnostic for the same bytes. Everything inside the
        // instruction must still be accounted for below.
        let limit = form.size() * 8;
        let mut outside_form = false;
        let mut covered: Vec<bool> = vec![false; form.bits() as usize];
        for field in &fixup.field_descriptor {
            let end = u64::from(field.lsb) + u64::from(field.width);
            if end > limit {
                outside_form = true;
                continue;
            }
            let end = end.min(u64::from(form.bits()));
            for bit in u64::from(field.lsb)..end {
                covered[bit as usize] = true;
            }
        }
        if outside_form {
            continue;
        }

        // Slots that own at least one of the covered bits.
        let owners: Vec<&Slot> = form
            .slots
            .iter()
            .filter(|slot| {
                slot.placements.iter().any(|placement| {
                    (placement.bit_offset..placement.bit_offset + placement.width)
                        .any(|bit| covered.get(bit as usize).copied().unwrap_or(false))
                })
            })
            .collect();

        // A register slot (or an inverted placement) is written by the operand
        // path. A fixup on the same bits is the two-writer case, not a field
        // patch.
        if owners.iter().any(|slot| {
            slot.from == SlotFrom::RegNumber
                || slot.placements.iter().any(|placement| placement.inverted)
        }) {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_006, fixup.path.clone())
                    .with("first", "operand")
                    .with("second", fixup.fixup_id.as_str()),
            );
            continue;
        }

        if owners.len() != 1 || owners[0].from != SlotFrom::OperandValue {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/field_descriptor")
                    .with("kind", "field_descriptor")
                    .with("form_id", form.form_id.as_str())
                    .with(
                        "field",
                        "descriptor does not cover exactly one operand_value slot",
                    ),
            );
            continue;
        }

        // Within the slot, each range must sit in exactly one placement, and the
        // placements must appear in the slot's declared order. That order is the
        // value order: swapping two of them silently reassigns the value bits.
        let placements = &owners[0].placements;
        let mut seen: Vec<usize> = Vec::new();
        let mut outside_placement = false;
        let mut out_of_order = false;
        for field in &fixup.field_descriptor {
            let start = field.lsb;
            let end = u64::from(start) + u64::from(field.width);
            let hit = placements.iter().position(|placement| {
                u64::from(start) >= u64::from(placement.bit_offset)
                    && end <= u64::from(placement.bit_offset) + u64::from(placement.width)
            });
            match hit {
                Some(index) => {
                    if seen.last().is_some_and(|previous| index < *previous) {
                        out_of_order = true;
                    }
                    if !seen.contains(&index) {
                        seen.push(index);
                    }
                }
                None => outside_placement = true,
            }
        }
        if outside_placement {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/field_descriptor")
                    .with("kind", "field_descriptor")
                    .with("form_id", form.form_id.as_str())
                    .with(
                        "field",
                        "descriptor range is not contained in one placement of the slot",
                    ),
            );
        } else if out_of_order {
            errors.push(
                Diagnostic::new(codes::E_FIXUP_001, fixup.path.clone() + "/field_descriptor")
                    .with("kind", "field_descriptor")
                    .with("form_id", form.form_id.as_str())
                    .with(
                        "field",
                        "descriptor order does not match the slot's placement order",
                    ),
            );
        }
    }
}

fn mode_name(mode: &Mode) -> &str {
    match mode {
        Mode::ResolveInPlace => "resolve_in_place",
        Mode::EmitRelocation => "emit_relocation",
        Mode::Unknown(name) => name,
    }
}

impl<'a> Model<'a> {
    /// Fixups grouped by `pair_group`, in first-appearance order.
    fn fixup_groups(&self) -> Vec<(&'a str, Vec<&'a Fixup>)> {
        let mut groups: Vec<(&'a str, Vec<&'a Fixup>)> = Vec::new();
        for fixup in &self.plan.fixups {
            if let Some(group) = &fixup.pair_group {
                match groups.iter_mut().find(|(name, _)| name == &group.as_str()) {
                    Some((_, members)) => members.push(fixup),
                    None => groups.push((group.as_str(), vec![fixup])),
                }
            }
        }
        groups
    }
}
