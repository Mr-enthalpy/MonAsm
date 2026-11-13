//! The parsed-plan identity of `ADR-0127`.
//!
//! `ParsedPlanIdentity` answers one question: *were these the parsed facts?* It
//! covers every field of [`Plan`] except `legacy_document` and `provenance`.
//! It deliberately includes `path`, because a pointer is a deterministic part of
//! the plan and covering one extra deterministic field cannot create ambiguity;
//! excluding `provenance` matches the legacy fingerprint, which never hashed it.
//!
//! Two properties are structural, not tested by convention:
//!
//! - every covered struct is destructured exhaustively (no `..`), so adding a
//!   field stops the build until the identity says what it means;
//! - every enum is matched with all variants and no `_` arm, so adding a variant
//!   does the same.
//!
//! The byte encoding is a protocol, not an implementation detail: the tag table,
//! the field order and the enum variant numbers are frozen in `ADR-0127` §3.2.
//! Changing any of them is an algorithm change and needs a new
//! `plan-identity/<version>` literal, because the domain separator and the
//! algorithm name are the same string.
//!
//! This module is in `fmp-model` because the facts are model facts. It does not
//! know the build that will execute the plan; that belongs to the materializer
//! (`ExecutionReceipt`, H1b).

use crate::canonical;
use crate::plan::{
    Artifact, Binding, DefinitionIdentity, FieldRange, Fixup, FixupTarget, Fragment, FragmentBody,
    Instruction, Mode, Modifier, ModifierValue, OutputContract, PairRole, Payload, PcRule, Plan,
    RangeConstraint, Section, SectionKind, Symbol, SymbolKind, TargetIdentity, Transform,
};

/// The algorithm name and the hash domain separator.
pub const PLAN_IDENTITY_ALGORITHM: &str = "plan-identity/0.1";

const DOMAIN: &[u8] = b"plan-identity/0.1\0";

/// `sha256` over the parsed facts, prefixed with the algorithm name.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ParsedPlanIdentity {
    digest: String,
}

impl ParsedPlanIdentity {
    pub fn of(plan: &Plan) -> Self {
        let facts = plan_facts(plan);
        ParsedPlanIdentity {
            digest: canonical::sha256_prefixed(&[DOMAIN, &facts]),
        }
    }

    /// `sha256:<64 lowercase hex>`.
    pub fn digest(&self) -> &str {
        &self.digest
    }

    pub fn algorithm(&self) -> &'static str {
        PLAN_IDENTITY_ALGORITHM
    }
}

/// The canonical fact bytes, without the domain separator or the digest.
///
/// Exposed for the independent (Python) implementation and for the fixed
/// vectors in `ADR-0127`; callers normally want [`ParsedPlanIdentity::of`].
pub fn plan_facts(plan: &Plan) -> Vec<u8> {
    let mut out = Vec::new();
    let Plan {
        legacy_document: _,
        provenance: _,
        format_version,
        target,
        definition,
        output,
        sections,
        symbols,
        instructions,
        fixups,
    } = plan;

    structure(&mut out, |out| {
        string(out, format_version);
        target_identity(out, target);
        definition_identity(out, definition);
        output_contract(out, output);
        vector(out, sections, section);
        vector(out, symbols, symbol);
        vector(out, instructions, instruction);
        vector(out, fixups, fixup);
    });
    out
}

fn target_identity(out: &mut Vec<u8>, value: &TargetIdentity) {
    let TargetIdentity {
        isa_family,
        isa_variant,
        execution_mode,
        enabled_extensions,
        feature_constraints,
        byte_order,
        address_width,
        path,
    } = value;
    structure(out, |out| {
        string(out, isa_family);
        string(out, isa_variant);
        string(out, execution_mode);
        vector(out, enabled_extensions, |out, item| string(out, item));
        vector(out, feature_constraints, |out, item| string(out, item));
        string(out, byte_order);
        u64_value(out, u64::from(*address_width));
        string(out, path);
    });
}

fn definition_identity(out: &mut Vec<u8>, value: &DefinitionIdentity) {
    let DefinitionIdentity {
        namespace,
        version,
        digest,
        source_ref,
        path,
    } = value;
    structure(out, |out| {
        string(out, namespace);
        string(out, version);
        string(out, digest);
        option(out, source_ref, |out, item| string(out, item));
        string(out, path);
    });
}

fn output_contract(out: &mut Vec<u8>, value: &OutputContract) {
    let OutputContract {
        artifact,
        section_order,
        symbol_order,
        fixup_record_order,
        include_symbol_table,
        emit_fixups,
        path,
    } = value;
    structure(out, |out| {
        self::artifact(out, artifact);
        vector(out, section_order, |out, item| string(out, item));
        option(out, symbol_order, |out, items| {
            vector(out, items, |out, item| string(out, item))
        });
        string(out, fixup_record_order);
        boolean(out, *include_symbol_table);
        boolean(out, *emit_fixups);
        string(out, path);
    });
}

fn artifact(out: &mut Vec<u8>, value: &Artifact) {
    match value {
        Artifact::Bytes => enumerated(out, 0, |_| {}),
        Artifact::Sections => enumerated(out, 1, |_| {}),
        Artifact::Unknown(name) => enumerated(out, 2, |out| string(out, name)),
    }
}

fn section(out: &mut Vec<u8>, value: &Section) {
    let Section {
        section_id,
        section_kind,
        image_backed,
        base_address,
        declared_size,
        fragments,
        path,
    } = value;
    structure(out, |out| {
        string(out, section_id);
        self::section_kind(out, section_kind);
        boolean(out, *image_backed);
        option(out, base_address, |out, item| u64_value(out, *item));
        u64_value(out, *declared_size);
        vector(out, fragments, fragment);
        string(out, path);
    });
}

fn section_kind(out: &mut Vec<u8>, value: &SectionKind) {
    match value {
        SectionKind::Code => enumerated(out, 0, |_| {}),
        SectionKind::Data => enumerated(out, 1, |_| {}),
        SectionKind::Rodata => enumerated(out, 2, |_| {}),
        SectionKind::Bss => enumerated(out, 3, |_| {}),
        SectionKind::Unknown(name) => enumerated(out, 4, |out| string(out, name)),
    }
}

fn fragment(out: &mut Vec<u8>, value: &Fragment) {
    let Fragment {
        offset,
        size,
        body,
        path,
    } = value;
    structure(out, |out| {
        u64_value(out, *offset);
        u64_value(out, *size);
        match body {
            FragmentBody::Instruction(id) => enumerated(out, 0, |out| string(out, id)),
            FragmentBody::Data(payload) => enumerated(out, 1, |out| string(out, payload)),
            FragmentBody::Fill(byte) => enumerated(out, 2, |out| u8_value(out, *byte)),
        }
        string(out, path);
    });
}

fn symbol(out: &mut Vec<u8>, value: &Symbol) {
    let Symbol {
        symbol_id,
        name,
        kind,
        binding,
        section_id,
        offset,
        path,
    } = value;
    structure(out, |out| {
        string(out, symbol_id);
        string(out, name);
        symbol_kind(out, kind);
        binding_value(out, binding);
        option(out, section_id, |out, item| string(out, item));
        option(out, offset, |out, item| u64_value(out, *item));
        string(out, path);
    });
}

fn symbol_kind(out: &mut Vec<u8>, value: &SymbolKind) {
    match value {
        SymbolKind::Defined => enumerated(out, 0, |_| {}),
        SymbolKind::Undefined => enumerated(out, 1, |_| {}),
        SymbolKind::External => enumerated(out, 2, |_| {}),
        SymbolKind::Unknown(name) => enumerated(out, 3, |out| string(out, name)),
    }
}

fn binding_value(out: &mut Vec<u8>, value: &Binding) {
    match value {
        Binding::Local => enumerated(out, 0, |_| {}),
        Binding::Global => enumerated(out, 1, |_| {}),
        Binding::Weak => enumerated(out, 2, |_| {}),
        Binding::Unknown(name) => enumerated(out, 3, |out| string(out, name)),
    }
}

fn instruction(out: &mut Vec<u8>, value: &Instruction) {
    let Instruction {
        instruction_id,
        section_id,
        offset,
        form_id,
        operands,
        expected_size,
        expected_digest,
        path,
    } = value;
    structure(out, |out| {
        string(out, instruction_id);
        string(out, section_id);
        u64_value(out, *offset);
        string(out, form_id);
        vector(out, operands, operand);
        u64_value(out, *expected_size);
        option(out, expected_digest, |out, item| string(out, item));
        string(out, path);
    });
}

fn operand(out: &mut Vec<u8>, value: &crate::plan::Operand) {
    let crate::plan::Operand {
        role,
        kind,
        target_type,
        payload,
        modifiers,
        path,
    } = value;
    structure(out, |out| {
        string(out, role);
        string(out, kind);
        string(out, target_type);
        payload_value(out, payload);
        vector(out, modifiers, modifier);
        string(out, path);
    });
}

fn payload_value(out: &mut Vec<u8>, value: &Payload) {
    match value {
        Payload::Register(register) => enumerated(out, 0, |out| u64_value(out, *register)),
        Payload::Value(value) => enumerated(out, 1, |out| i128_value(out, *value)),
        Payload::Symbol(symbol_id) => enumerated(out, 2, |out| string(out, symbol_id)),
        Payload::Empty => enumerated(out, 3, |_| {}),
    }
}

fn modifier(out: &mut Vec<u8>, value: &Modifier) {
    let Modifier { name, value } = value;
    structure(out, |out| {
        string(out, name);
        match value {
            ModifierValue::Int(value) => enumerated(out, 0, |out| i128_value(out, *value)),
            ModifierValue::Text(text) => enumerated(out, 1, |out| string(out, text)),
            ModifierValue::Bool(flag) => enumerated(out, 2, |out| boolean(out, *flag)),
        }
    });
}

fn fixup(out: &mut Vec<u8>, value: &Fixup) {
    let Fixup {
        fixup_id,
        section_id,
        offset,
        field_descriptor,
        target,
        addend,
        pc_reference_rule,
        value_transform,
        transform_shift,
        range_constraint,
        resolution_mode,
        pair_group,
        pair_role,
        path,
    } = value;
    structure(out, |out| {
        string(out, fixup_id);
        string(out, section_id);
        u64_value(out, *offset);
        vector(out, field_descriptor, field_range);
        match target {
            FixupTarget::Symbol(symbol_id) => enumerated(out, 0, |out| string(out, symbol_id)),
            FixupTarget::Absolute(address) => enumerated(out, 1, |out| u64_value(out, *address)),
            FixupTarget::SectionRelative(section_id) => {
                enumerated(out, 2, |out| string(out, section_id))
            }
            FixupTarget::Unknown(name) => enumerated(out, 3, |out| string(out, name)),
        }
        i128_value(out, i128::from(*addend));
        pc_rule(out, pc_reference_rule);
        transform(out, value_transform);
        option(out, transform_shift, |out, item| {
            u64_value(out, u64::from(*item))
        });
        self::range_constraint(out, range_constraint);
        self::resolution_mode(out, resolution_mode);
        option(out, pair_group, |out, item| string(out, item));
        option(out, pair_role, |out, item| self::pair_role(out, item));
        string(out, path);
    });
}

fn field_range(out: &mut Vec<u8>, value: &FieldRange) {
    let FieldRange { lsb, width } = value;
    structure(out, |out| {
        u64_value(out, u64::from(*lsb));
        u64_value(out, u64::from(*width));
    });
}

fn pc_rule(out: &mut Vec<u8>, value: &PcRule) {
    match value {
        PcRule::None => enumerated(out, 0, |_| {}),
        PcRule::PcrelBegin => enumerated(out, 1, |_| {}),
        PcRule::PcrelEnd => enumerated(out, 2, |_| {}),
        PcRule::PcrelPage => enumerated(out, 3, |_| {}),
        PcRule::PcrelHi => enumerated(out, 4, |_| {}),
        PcRule::Unknown(name) => enumerated(out, 5, |out| string(out, name)),
    }
}

fn transform(out: &mut Vec<u8>, value: &Transform) {
    match value {
        Transform::Identity => enumerated(out, 0, |_| {}),
        Transform::Scale => enumerated(out, 1, |_| {}),
        Transform::Page => enumerated(out, 2, |_| {}),
        Transform::Hi20 => enumerated(out, 3, |_| {}),
        Transform::Lo12I => enumerated(out, 4, |_| {}),
        Transform::Lo12S => enumerated(out, 5, |_| {}),
        Transform::PcrelHi20 => enumerated(out, 6, |_| {}),
        Transform::PcrelLo12 => enumerated(out, 7, |_| {}),
        Transform::Unknown(name) => enumerated(out, 8, |out| string(out, name)),
    }
}

fn range_constraint(out: &mut Vec<u8>, value: &RangeConstraint) {
    let RangeConstraint {
        signed,
        bits,
        align_bits,
    } = value;
    structure(out, |out| {
        boolean(out, *signed);
        u64_value(out, u64::from(*bits));
        u64_value(out, u64::from(*align_bits));
    });
}

fn resolution_mode(out: &mut Vec<u8>, value: &Mode) {
    match value {
        Mode::ResolveInPlace => enumerated(out, 0, |_| {}),
        Mode::EmitRelocation => enumerated(out, 1, |_| {}),
        Mode::Unknown(name) => enumerated(out, 2, |out| string(out, name)),
    }
}

fn pair_role(out: &mut Vec<u8>, value: &PairRole) {
    match value {
        PairRole::Hi => enumerated(out, 0, |_| {}),
        PairRole::Lo => enumerated(out, 1, |_| {}),
        PairRole::Unknown(name) => enumerated(out, 2, |out| string(out, name)),
    }
}

// --- primitive encoders (the tag table of `ADR-0127` §3.2) -----------------

fn u8_value(out: &mut Vec<u8>, value: u8) {
    out.push(0x01);
    out.push(value);
}

fn boolean(out: &mut Vec<u8>, value: bool) {
    out.push(0x01);
    out.push(u8::from(value));
}

fn u64_value(out: &mut Vec<u8>, value: u64) {
    out.push(0x02);
    out.extend_from_slice(&value.to_le_bytes());
}

fn i128_value(out: &mut Vec<u8>, value: i128) {
    out.push(0x03);
    out.extend_from_slice(&value.to_le_bytes());
}

fn string(out: &mut Vec<u8>, value: &str) {
    out.push(0x04);
    out.extend_from_slice(&(value.len() as u64).to_le_bytes());
    out.extend_from_slice(value.as_bytes());
}

fn option<T>(out: &mut Vec<u8>, value: &Option<T>, write: impl FnOnce(&mut Vec<u8>, &T)) {
    match value {
        None => out.push(0x05),
        Some(item) => {
            out.push(0x06);
            write(out, item);
        }
    }
}

fn vector<T>(out: &mut Vec<u8>, items: &[T], write: impl Fn(&mut Vec<u8>, &T)) {
    out.push(0x07);
    out.extend_from_slice(&(items.len() as u64).to_le_bytes());
    for item in items {
        write(out, item);
    }
}

fn structure(out: &mut Vec<u8>, write: impl FnOnce(&mut Vec<u8>)) {
    out.push(0x08);
    write(out);
}

fn enumerated(out: &mut Vec<u8>, variant: u32, write: impl FnOnce(&mut Vec<u8>)) {
    out.push(0x09);
    out.extend_from_slice(&variant.to_le_bytes());
    write(out);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::json;
    use crate::plan::*;

    fn sha_a() -> String {
        "sha256:".to_string() + &"a".repeat(64)
    }

    fn sha_b() -> String {
        "sha256:".to_string() + &"b".repeat(64)
    }

    fn target_with(extensions: &[&str]) -> TargetIdentity {
        TargetIdentity {
            isa_family: "x86".to_string(),
            isa_variant: "x86-64".to_string(),
            execution_mode: "64".to_string(),
            enabled_extensions: extensions.iter().map(|item| item.to_string()).collect(),
            feature_constraints: vec![],
            byte_order: "little".to_string(),
            address_width: 64,
            path: "/target_identity".to_string(),
        }
    }

    fn base_definition() -> DefinitionIdentity {
        DefinitionIdentity {
            namespace: "monasm.isa.x86".to_string(),
            version: "0.75.0".to_string(),
            digest: sha_a(),
            source_ref: None,
            path: "/definition_identity".to_string(),
        }
    }

    fn base_output() -> OutputContract {
        OutputContract {
            artifact: Artifact::Bytes,
            section_order: vec![],
            symbol_order: None,
            fixup_record_order: "section_offset".to_string(),
            include_symbol_table: false,
            emit_fixups: false,
            path: "/output_contract".to_string(),
        }
    }

    fn empty_plan() -> Plan {
        Plan {
            legacy_document: json::parse(b"{}").unwrap(),
            format_version: "fmp/0.1".to_string(),
            target: target_with(&[]),
            definition: base_definition(),
            output: base_output(),
            sections: vec![],
            symbols: vec![],
            instructions: vec![],
            fixups: vec![],
            provenance: None,
        }
    }

    /// Vector 2: one image-backed `.text` section with a one-byte data fragment.
    fn sample_plan() -> Plan {
        let mut plan = empty_plan();
        plan.legacy_document = json::parse(b"{\"source_trace\":\"legacy\"}").unwrap();
        plan.output.section_order = vec![".text".to_string()];
        plan.sections.push(Section {
            section_id: ".text".to_string(),
            section_kind: SectionKind::Code,
            image_backed: true,
            base_address: None,
            declared_size: 1,
            fragments: vec![Fragment {
                offset: 0,
                size: 1,
                body: FragmentBody::Data("90".to_string()),
                path: "/sections/0/fragments/0".to_string(),
            }],
            path: "/sections/0".to_string(),
        });
        plan.provenance = Some(Provenance {
            materializer_version: "0.0.0".to_string(),
            build_profile: None,
            generated_by: None,
            notes: None,
            path: "/provenance".to_string(),
        });
        plan
    }

    /// Vector 3: every `Unknown` variant, every `Some`, and all three modifier
    /// payload shapes. One instruction, one symbol and one fixup, so the
    /// per-field mutation table has an element of every covered type.
    fn unknown_variants_plan() -> Plan {
        Plan {
            legacy_document: json::parse(b"{}").unwrap(),
            format_version: "fmp/0.1".to_string(),
            target: target_with(&["avx"]),
            definition: base_definition(),
            output: OutputContract {
                artifact: Artifact::Unknown("future".to_string()),
                section_order: vec!["a".to_string(), "b".to_string()],
                symbol_order: Some(vec!["s".to_string()]),
                fixup_record_order: "declared".to_string(),
                include_symbol_table: true,
                emit_fixups: true,
                path: "/output_contract".to_string(),
            },
            sections: vec![Section {
                section_id: "s".to_string(),
                section_kind: SectionKind::Unknown("custom".to_string()),
                image_backed: false,
                base_address: Some(4096),
                declared_size: 0,
                fragments: vec![Fragment {
                    offset: 3,
                    size: 0,
                    body: FragmentBody::Fill(0xCC),
                    path: "/sections/0/fragments/0".to_string(),
                }],
                path: "/sections/0".to_string(),
            }],
            symbols: vec![Symbol {
                symbol_id: "s0".to_string(),
                name: "n".to_string(),
                kind: SymbolKind::Unknown("k".to_string()),
                binding: Binding::Unknown("b".to_string()),
                section_id: Some("s".to_string()),
                offset: Some(7),
                path: "/symbols/0".to_string(),
            }],
            instructions: vec![Instruction {
                instruction_id: "i0".to_string(),
                section_id: "s".to_string(),
                offset: 0,
                form_id: "f".to_string(),
                operands: vec![Operand {
                    role: "src".to_string(),
                    kind: "k".to_string(),
                    target_type: "t".to_string(),
                    payload: Payload::Value(-5),
                    modifiers: vec![
                        Modifier {
                            name: "m".to_string(),
                            value: ModifierValue::Int(-1),
                        },
                        Modifier {
                            name: "n".to_string(),
                            value: ModifierValue::Text("x".to_string()),
                        },
                        Modifier {
                            name: "o".to_string(),
                            value: ModifierValue::Bool(true),
                        },
                    ],
                    path: "/instructions/0/operands/0".to_string(),
                }],
                expected_size: 0,
                expected_digest: Some(sha_b()),
                path: "/instructions/0".to_string(),
            }],
            fixups: vec![Fixup {
                fixup_id: "f0".to_string(),
                section_id: "s".to_string(),
                offset: 9,
                field_descriptor: vec![FieldRange { lsb: 1, width: 2 }],
                target: FixupTarget::Unknown("t".to_string()),
                addend: -3,
                pc_reference_rule: PcRule::Unknown("r".to_string()),
                value_transform: Transform::Unknown("v".to_string()),
                transform_shift: Some(4),
                range_constraint: RangeConstraint {
                    signed: true,
                    bits: 2,
                    align_bits: 1,
                },
                resolution_mode: Mode::Unknown("m".to_string()),
                pair_group: Some("g".to_string()),
                pair_role: Some(PairRole::Unknown("u".to_string())),
                path: "/fixups/0".to_string(),
            }],
            provenance: None,
        }
    }

    fn digest_of(plan: &Plan) -> String {
        ParsedPlanIdentity::of(plan).digest().to_string()
    }

    /// `ADR-0127` §3.2's three protocol vectors. Each digest was produced by the
    /// independent Python encoder (`tools/plan_identity.py`, run with `--check`)
    /// from the same hand-built facts, so agreement is two implementations, not
    /// one implementation compared with itself.
    #[test]
    fn the_three_protocol_vectors_are_stable() {
        assert_eq!(
            digest_of(&empty_plan()),
            "sha256:a48faecec39dd1de38f13b4868559f307b575a95a0aa241a01caa325400422c4"
        );
        assert_eq!(
            digest_of(&sample_plan()),
            "sha256:9da5a3318e943bcbd5c9c32366708922b68a5e7e7c67a0b3d48a9c7b1a68eec2"
        );
        assert_eq!(
            digest_of(&unknown_variants_plan()),
            "sha256:1a07ae98cba50f7ee65b36bbe2bb1684eaa0885f728270b9baa39824a2a4632a"
        );
    }

    #[test]
    fn the_algorithm_name_is_the_domain_separator() {
        let identity = ParsedPlanIdentity::of(&sample_plan());
        assert_eq!(identity.algorithm(), "plan-identity/0.1");
        assert_eq!(identity.algorithm(), PLAN_IDENTITY_ALGORITHM);
        assert!(identity.digest().starts_with("sha256:"));
        assert_eq!(identity.digest().len(), 7 + 64);
    }

    #[test]
    fn provenance_is_not_part_of_the_identity() {
        let first = sample_plan();
        let mut second = sample_plan();
        second.provenance = None;
        assert_eq!(digest_of(&first), digest_of(&second));
    }

    #[test]
    fn the_legacy_document_is_not_part_of_the_identity() {
        let first = sample_plan();
        let mut second = sample_plan();
        second.legacy_document = json::parse(b"{\"source_trace\":\"different\"}").unwrap();
        assert_eq!(digest_of(&first), digest_of(&second));
    }

    #[test]
    fn a_changed_operand_changes_the_identity() {
        let mut first = sample_plan();
        let mut second = sample_plan();
        first.instructions = unknown_variants_plan().instructions;
        second.instructions = first.instructions.clone();
        second.instructions[0].operands[0].payload = Payload::Register(1);
        assert_ne!(digest_of(&first), digest_of(&second));
    }

    #[test]
    fn an_unknown_variant_is_payload_carrying_and_distinct() {
        let mut first = sample_plan();
        let mut second = sample_plan();
        first.output.artifact = Artifact::Unknown("future".to_string());
        second.output.artifact = Artifact::Unknown("other".to_string());
        assert_ne!(digest_of(&first), digest_of(&second));
        assert_ne!(digest_of(&first), digest_of(&sample_plan()));
    }

    /// Hard rule 2's per-field counterexample: every covered field must move the
    /// digest when it changes. The table names one mutation per field of every
    /// covered struct, so a field added to the encoder but forgotten here (or a
    /// field silently dropped from the encoder) is caught by a failing row.
    #[test]
    fn plan_identity_covers_every_parsed_field() {
        type Mutation = (&'static str, fn(&mut Plan));
        let cases: Vec<Mutation> = vec![
            ("format_version", |p| p.format_version = "fmp/0.2".into()),
            ("target.isa_family", |p| {
                p.target.isa_family = "aarch64".into()
            }),
            ("target.isa_variant", |p| {
                p.target.isa_variant = "x86-64-v3".into()
            }),
            ("target.execution_mode", |p| {
                p.target.execution_mode = "32".into()
            }),
            ("target.enabled_extensions", |p| {
                p.target.enabled_extensions.push("sse2".into())
            }),
            ("target.feature_constraints", |p| {
                p.target.feature_constraints.push("x".into())
            }),
            ("target.byte_order", |p| p.target.byte_order = "big".into()),
            ("target.address_width", |p| p.target.address_width = 32),
            ("target.path", |p| p.target.path = "/t".into()),
            ("definition.namespace", |p| {
                p.definition.namespace = "monasm.isa.aarch64".into()
            }),
            ("definition.version", |p| {
                p.definition.version = "0.0.0".into()
            }),
            ("definition.digest", |p| p.definition.digest = sha_b()),
            ("definition.source_ref", |p| {
                p.definition.source_ref = Some("ref".into())
            }),
            ("definition.path", |p| p.definition.path = "/d".into()),
            ("output.artifact", |p| {
                p.output.artifact = Artifact::Unknown("else".into())
            }),
            ("output.section_order", |p| {
                p.output.section_order.push("c".into())
            }),
            ("output.symbol_order", |p| p.output.symbol_order = None),
            ("output.fixup_record_order", |p| {
                p.output.fixup_record_order = "file_offset".into()
            }),
            ("output.include_symbol_table", |p| {
                p.output.include_symbol_table = false
            }),
            ("output.emit_fixups", |p| p.output.emit_fixups = false),
            ("output.path", |p| p.output.path = "/o".into()),
            ("section.section_id", |p| {
                p.sections[0].section_id = "x".into()
            }),
            ("section.section_kind", |p| {
                p.sections[0].section_kind = SectionKind::Unknown("other".into())
            }),
            ("section.image_backed", |p| {
                p.sections[0].image_backed = true
            }),
            ("section.base_address", |p| {
                p.sections[0].base_address = None
            }),
            ("section.declared_size", |p| p.sections[0].declared_size = 1),
            ("section.path", |p| p.sections[0].path = "/s".into()),
            ("fragment.offset", |p| p.sections[0].fragments[0].offset = 4),
            ("fragment.size", |p| p.sections[0].fragments[0].size = 1),
            ("fragment.body", |p| {
                p.sections[0].fragments[0].body = FragmentBody::Data("cc".into())
            }),
            ("fragment.path", |p| {
                p.sections[0].fragments[0].path = "/f".into()
            }),
            ("symbol.symbol_id", |p| p.symbols[0].symbol_id = "s1".into()),
            ("symbol.name", |p| p.symbols[0].name = "other".into()),
            ("symbol.kind", |p| {
                p.symbols[0].kind = SymbolKind::Unknown("k2".into())
            }),
            ("symbol.binding", |p| {
                p.symbols[0].binding = Binding::Unknown("b2".into())
            }),
            ("symbol.section_id", |p| p.symbols[0].section_id = None),
            ("symbol.offset", |p| p.symbols[0].offset = None),
            ("symbol.path", |p| p.symbols[0].path = "/y".into()),
            ("instruction.instruction_id", |p| {
                p.instructions[0].instruction_id = "i1".into()
            }),
            ("instruction.section_id", |p| {
                p.instructions[0].section_id = "x".into()
            }),
            ("instruction.offset", |p| p.instructions[0].offset = 1),
            ("instruction.form_id", |p| {
                p.instructions[0].form_id = "g".into()
            }),
            ("instruction.operands", |p| {
                p.instructions[0].operands[0].path = "/instructions/0/operands/1".into()
            }),
            ("instruction.expected_size", |p| {
                p.instructions[0].expected_size = 1
            }),
            ("instruction.expected_digest", |p| {
                p.instructions[0].expected_digest = Some(sha_a())
            }),
            ("instruction.path", |p| p.instructions[0].path = "/i".into()),
            ("operand.role", |p| {
                p.instructions[0].operands[0].role = "dest".into()
            }),
            ("operand.kind", |p| {
                p.instructions[0].operands[0].kind = "k2".into()
            }),
            ("operand.target_type", |p| {
                p.instructions[0].operands[0].target_type = "t2".into()
            }),
            ("operand.payload", |p| {
                p.instructions[0].operands[0].payload = Payload::Register(5)
            }),
            ("operand.modifiers", |p| {
                p.instructions[0].operands[0].modifiers[0].name = "m2".into()
            }),
            ("operand.path", |p| {
                p.instructions[0].operands[0].path = "/p".into()
            }),
            ("modifier.value.int", |p| {
                p.instructions[0].operands[0].modifiers[0].value = ModifierValue::Int(-2)
            }),
            ("modifier.value.text", |p| {
                p.instructions[0].operands[0].modifiers[1].value = ModifierValue::Text("y".into())
            }),
            ("modifier.value.bool", |p| {
                p.instructions[0].operands[0].modifiers[2].value = ModifierValue::Bool(false)
            }),
            ("fixup.fixup_id", |p| p.fixups[0].fixup_id = "f1".into()),
            ("fixup.section_id", |p| p.fixups[0].section_id = "x".into()),
            ("fixup.offset", |p| p.fixups[0].offset = 10),
            ("fixup.field_descriptor", |p| {
                p.fixups[0].field_descriptor = vec![FieldRange { lsb: 0, width: 1 }]
            }),
            ("fixup.target", |p| {
                p.fixups[0].target = FixupTarget::Unknown("t2".into())
            }),
            ("fixup.addend", |p| p.fixups[0].addend = -4),
            ("fixup.pc_reference_rule", |p| {
                p.fixups[0].pc_reference_rule = PcRule::Unknown("r2".into())
            }),
            ("fixup.value_transform", |p| {
                p.fixups[0].value_transform = Transform::Unknown("v2".into())
            }),
            ("fixup.transform_shift", |p| {
                p.fixups[0].transform_shift = None
            }),
            ("fixup.range_constraint.signed", |p| {
                p.fixups[0].range_constraint.signed = false
            }),
            ("fixup.range_constraint.bits", |p| {
                p.fixups[0].range_constraint.bits = 3
            }),
            ("fixup.range_constraint.align_bits", |p| {
                p.fixups[0].range_constraint.align_bits = 2
            }),
            ("fixup.resolution_mode", |p| {
                p.fixups[0].resolution_mode = Mode::Unknown("m2".into())
            }),
            ("fixup.pair_group", |p| p.fixups[0].pair_group = None),
            ("fixup.pair_role", |p| {
                p.fixups[0].pair_role = Some(PairRole::Unknown("u2".into()))
            }),
            ("fixup.path", |p| p.fixups[0].path = "/x".into()),
            ("field_range.lsb", |p| {
                p.fixups[0].field_descriptor[0].lsb = 0
            }),
            ("field_range.width", |p| {
                p.fixups[0].field_descriptor[0].width = 1
            }),
        ];

        let baseline = digest_of(&unknown_variants_plan());
        for (name, mutate) in cases {
            let mut plan = unknown_variants_plan();
            mutate(&mut plan);
            assert_ne!(
                digest_of(&plan),
                baseline,
                "{name} changed but the identity did not"
            );
        }
    }
}
