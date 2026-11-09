//! Planner-boundary parity gate (`docs/fmp-v0/09_planner_api.md`, `ADR-0097`).
//!
//! The point is not that the builder has its own rules. It has none: every
//! rebuilt document is serialized and handed back to the shipped reader,
//! validator and emitter. If a builder field is dropped, renamed or defaulted,
//! the fixture's bytes or its exact diagnostic set changes, and the test fails.
//!
//! Covered here:
//!
//! - all 114 positive fixtures, via `from_model`, including the Level 1
//!   envelope and the fingerprint;
//! - all 559 `materialize`-phase negative fixtures, via `from_model`, comparing
//!   code, JSON Pointer and detail-key set;
//! - from-scratch authoring for one positive per ISA plus `X86-P71`;
//! - the exact closed key set of every emitted object;
//! - the six `read`-phase negatives that never produce a bound `Plan`;
//! - determinism and the typed `Unrepresentable` failures.

use std::path::{Path, PathBuf};

use fmp_model::json::Json;
use fmp_model::plan as model;
use fmp_model::Registry;
use fmp_plan::{
    Artifact, Binding, DefinitionIdentity, FieldRange, Fixup, FixupRecordOrder, FixupTarget,
    Fragment, FragmentBody, Instruction, Modifier, ModifierValue, Operand, OutputContract,
    PairRole, Payload, PcRule, PlanBuilder, Provenance, RangeConstraint, ResolutionMode, Section,
    SectionKind, Symbol, SymbolKind, TargetIdentity, Transform,
};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn registry() -> Registry {
    Registry::load_dir(&root().join("definitions")).expect("definitions/ must load")
}

fn read_plan(path: &Path) -> fmp_model::Plan {
    let bytes = std::fs::read(path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    fmp_model::plan::read(&bytes)
        .unwrap_or_else(|error| panic!("{}: {}", path.display(), error.message()))
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

fn case_file(dir: &Path, stem: &str, suffix: &str) -> PathBuf {
    dir.join(format!("{stem}.{suffix}"))
}

fn fixture_files(kind: &str, suffix: &str) -> Vec<PathBuf> {
    let fixtures = root().join("fixtures");
    let mut isa_dirs: Vec<PathBuf> = std::fs::read_dir(&fixtures)
        .unwrap_or_else(|error| panic!("{}: {error}", fixtures.display()))
        .map(|entry| entry.expect("readable directory entry").path())
        .filter(|path| path.is_dir() && path.join(kind).is_dir())
        .collect();
    isa_dirs.sort();

    let mut paths: Vec<PathBuf> = Vec::new();
    for isa in &isa_dirs {
        let dir = isa.join(kind);
        paths.extend(
            std::fs::read_dir(&dir)
                .unwrap_or_else(|error| panic!("{}: {error}", dir.display()))
                .map(|entry| entry.expect("readable directory entry").path())
                .filter(|path| {
                    path.file_name()
                        .and_then(|name| name.to_str())
                        .is_some_and(|name| name.ends_with(suffix))
                }),
        );
    }
    paths.sort();
    paths
}

fn positives() -> Vec<PathBuf> {
    fixture_files("positive", ".fmp.json")
}

fn negatives() -> Vec<PathBuf> {
    fixture_files("negative", ".fmp.json")
}

fn stem(path: &Path) -> String {
    path.file_name()
        .and_then(|name| name.to_str())
        .expect("fixture file name")
        .trim_end_matches(".fmp.json")
        .to_string()
}

fn expected_error(path: &Path) -> Json {
    let name = stem(path);
    let dir = path.parent().expect("fixture directory");
    let expected_path = case_file(dir, &name, "expected-error.json");
    let bytes = std::fs::read(&expected_path)
        .unwrap_or_else(|error| panic!("{}: {error}", expected_path.display()));
    fmp_model::json::parse(&bytes).expect("expected-error.json must parse")
}

/// Rebuild a fixture through the builder, then hand the bytes back to the
/// shipped reader. Returns the bound plan and the definition it names.
fn rebuild(path: &Path) -> (fmp_model::Plan, String) {
    let name = stem(path);
    let plan = read_plan(path);
    let rebuilt = PlanBuilder::from_model(&plan).unwrap_or_else(|error| panic!("{name}: {error}"));
    let bytes = rebuilt.build_canonical();
    let plan = fmp_model::plan::read(&bytes).unwrap_or_else(|error| {
        panic!(
            "{name}: the builder's own bytes did not read: {}",
            error.message()
        )
    });
    (plan, name)
}

// ---------------------------------------------------------------------------
// Positive parity
// ---------------------------------------------------------------------------

#[test]
fn positives_reproduce_the_oracle_through_the_builder() {
    let registry = registry();
    let paths = positives();
    assert_eq!(paths.len(), 120, "the positive corpus is 120 plans");
    for path in paths {
        let (plan, name) = rebuild(&path);
        let definition = registry
            .find(&plan.definition.namespace, &plan.definition.version)
            .unwrap_or_else(|error| panic!("{name}: {}", error.message()));
        let artifact = match fmp_materialize::materialize(&plan, definition) {
            Ok(artifact) => artifact,
            Err(errors) => panic!(
                "{name} was rejected after rebuilding:\n{}",
                errors
                    .iter()
                    .map(|error| error.message())
                    .collect::<Vec<_>>()
                    .join("\n")
            ),
        };

        let dir = path.parent().expect("fixture directory");
        let expected_path = case_file(dir, &name, "expected.bin");
        let expected = std::fs::read(&expected_path)
            .unwrap_or_else(|error| panic!("{}: {error}", expected_path.display()));
        assert_eq!(
            artifact.bytes_hex(),
            hex(&expected),
            "{name}: rebuilt bytes differ from the oracle's"
        );

        let oracle_path = case_file(dir, &name, "oracle.json");
        let oracle = std::fs::read(&oracle_path)
            .unwrap_or_else(|error| panic!("{}: {error}", oracle_path.display()));
        let oracle = fmp_model::json::parse(&oracle).expect("oracle.json must parse");
        let records = oracle
            .get("records")
            .and_then(Json::as_i128)
            .unwrap_or_else(|| panic!("{name}: oracle.json has no `records`"));
        assert_eq!(
            artifact.fixups.len() as i128,
            records,
            "{name}: rebuilt record count differs from the oracle record"
        );

        let artifact_path = case_file(dir, &name, "expected-artifact.json");
        if artifact_path.is_file() {
            let expected = std::fs::read(&artifact_path)
                .unwrap_or_else(|error| panic!("{}: {error}", artifact_path.display()));
            let expected = fmp_model::json::parse(&expected)
                .unwrap_or_else(|error| panic!("{}: {}", artifact_path.display(), error.reason()));
            assert_eq!(
                artifact.to_json(),
                expected,
                "{name}: rebuilt Level 1 envelope differs from the recorded shape"
            );
        }

        // No corpus plan carries a draft field, so re-emission must be
        // fingerprint-identical, not merely byte-identical.
        let original = read_plan(&path);
        assert_eq!(
            fmp_materialize::fingerprint(&plan, definition),
            fmp_materialize::fingerprint(&original, definition),
            "{name}: rebuilding changed the plan fingerprint"
        );
    }
}

// ---------------------------------------------------------------------------
// Negative parity
// ---------------------------------------------------------------------------

#[test]
fn negatives_reject_at_the_same_code_path_and_detail_keys() {
    let registry = registry();
    let paths = negatives();
    assert_eq!(
        paths.len(),
        583,
        "the corpus is 577 materialize-phase plus 6 read-phase negatives"
    );
    let mut materialize_phase = 0usize;
    for path in paths {
        let expected = expected_error(&path);
        let phase = expected
            .get("phase")
            .and_then(Json::as_str)
            .unwrap_or("materialize");
        if phase == "read" {
            continue;
        }
        materialize_phase += 1;

        let (plan, name) = rebuild(&path);
        let definition = registry
            .find(&plan.definition.namespace, &plan.definition.version)
            .unwrap_or_else(|error| panic!("{name}: {}", error.message()));
        let errors = match fmp_materialize::materialize(&plan, definition) {
            Ok(artifact) => panic!(
                "{name} was accepted after rebuilding and emitted {}",
                artifact.bytes_hex()
            ),
            Err(errors) => errors,
        };

        let wanted = expected
            .get("errors")
            .and_then(Json::as_array)
            .unwrap_or_else(|| panic!("{name}: expected-error.json needs `errors`"));
        let mut wanted_set: Vec<(String, String, String)> = wanted
            .iter()
            .map(|entry| {
                let code = entry
                    .get("code")
                    .and_then(Json::as_str)
                    .expect("error code");
                let path = entry
                    .get("path")
                    .and_then(Json::as_str)
                    .expect("error path");
                let mut keys: Vec<&str> = entry
                    .get("detail_keys")
                    .and_then(Json::as_array)
                    .expect("detail_keys")
                    .iter()
                    .map(|key| key.as_str().expect("detail key"))
                    .collect();
                keys.sort_unstable();
                (code.to_string(), path.to_string(), keys.join(","))
            })
            .collect();
        wanted_set.sort();

        let mut found: Vec<(String, String, String)> = errors
            .iter()
            .map(|error| {
                let keys: Vec<&str> = error.details().keys().copied().collect();
                (
                    error.code().to_string(),
                    error.path().to_string(),
                    keys.join(","),
                )
            })
            .collect();
        found.sort();

        assert_eq!(
            found,
            wanted_set,
            "{name}: rebuilt diagnostics differ\nfound:\n{}\nexpected:\n{}",
            errors
                .iter()
                .map(|error| error.message())
                .collect::<Vec<_>>()
                .join("\n"),
            wanted
                .iter()
                .map(|entry| fmp_model::json::pretty(entry))
                .collect::<Vec<_>>()
                .join("\n")
        );
    }
    assert_eq!(
        materialize_phase, 577,
        "every materialize-phase negative must be rebuildable and compared"
    );
}

// ---------------------------------------------------------------------------
// From-scratch authoring
// ---------------------------------------------------------------------------

fn target(
    family: &str,
    variant: &str,
    mode: &str,
    extensions: &[&str],
    width: u32,
) -> TargetIdentity {
    TargetIdentity {
        isa_family: family.to_string(),
        isa_variant: variant.to_string(),
        execution_mode: mode.to_string(),
        enabled_extensions: extensions.iter().map(|item| item.to_string()).collect(),
        feature_constraints: Vec::new(),
        byte_order: "little".to_string(),
        address_width: width,
    }
}

fn definition(registry: &Registry, namespace: &str, version: &str) -> DefinitionIdentity {
    let definition = registry
        .find(namespace, version)
        .unwrap_or_else(|error| panic!("{namespace}/{version}: {}", error.message()));
    DefinitionIdentity {
        namespace: definition.namespace.clone(),
        version: definition.version.clone(),
        digest: definition.digest.clone(),
    }
}

fn output_bytes(sections: &[&str]) -> OutputContract {
    OutputContract {
        artifact: Artifact::Bytes,
        section_order: sections.iter().map(|item| item.to_string()).collect(),
        symbol_order: None,
        fixup_record_order: FixupRecordOrder::SectionIdOffsetFixupId,
        include_symbol_table: false,
        emit_fixups: true,
    }
}

fn output_level_one(sections: &[&str], symbol_order: &[&str]) -> OutputContract {
    OutputContract {
        artifact: Artifact::Sections,
        section_order: sections.iter().map(|item| item.to_string()).collect(),
        symbol_order: Some(symbol_order.iter().map(|item| item.to_string()).collect()),
        fixup_record_order: FixupRecordOrder::SectionIdOffsetFixupId,
        include_symbol_table: true,
        emit_fixups: true,
    }
}

fn reg(role: &str, kind: &str, target_type: &str, number: u64) -> Operand {
    Operand {
        role: role.to_string(),
        kind: kind.to_string(),
        target_type: target_type.to_string(),
        payload: Payload::Register(number),
        modifiers: Vec::new(),
    }
}

fn imm(role: &str, kind: &str, target_type: &str, value: i128) -> Operand {
    Operand {
        role: role.to_string(),
        kind: kind.to_string(),
        target_type: target_type.to_string(),
        payload: Payload::Value(value),
        modifiers: Vec::new(),
    }
}

fn symbol_operand(role: &str, kind: &str, target_type: &str, symbol_id: &str) -> Operand {
    Operand {
        role: role.to_string(),
        kind: kind.to_string(),
        target_type: target_type.to_string(),
        payload: Payload::Symbol(symbol_id.to_string()),
        modifiers: Vec::new(),
    }
}

fn ins(
    id: &str,
    section_id: &str,
    offset: u64,
    form_id: &str,
    operands: Vec<Operand>,
    expected_size: u64,
) -> Instruction {
    Instruction {
        instruction_id: id.to_string(),
        section_id: section_id.to_string(),
        offset,
        form_id: form_id.to_string(),
        operands,
        expected_size,
        expected_digest: None,
    }
}

fn section(
    id: &str,
    kind: SectionKind,
    image_backed: bool,
    base_address: Option<u64>,
    declared_size: u64,
    fragments: Vec<Fragment>,
) -> Section {
    Section {
        section_id: id.to_string(),
        section_kind: kind,
        image_backed,
        base_address,
        declared_size,
        fragments,
    }
}

fn frag_instruction(offset: u64, size: u64, id: &str) -> Fragment {
    Fragment {
        offset,
        size,
        body: FragmentBody::Instruction(id.to_string()),
    }
}

fn frag_data(offset: u64, bytes: &[u8]) -> Fragment {
    Fragment {
        offset,
        size: bytes.len() as u64,
        body: FragmentBody::Data(bytes.to_vec()),
    }
}

fn frag_fill(offset: u64, size: u64, byte: u8) -> Fragment {
    Fragment {
        offset,
        size,
        body: FragmentBody::Fill(byte),
    }
}

fn fixup(id: &str, offset: u64, target: FixupTarget, mode: ResolutionMode) -> Fixup {
    Fixup {
        fixup_id: id.to_string(),
        section_id: ".text".to_string(),
        offset,
        field_descriptor: vec![FieldRange { lsb: 24, width: 32 }],
        target,
        addend: 0,
        pc_reference_rule: PcRule::PcrelEnd,
        value_transform: Transform::Identity,
        transform_shift: None,
        range_constraint: RangeConstraint {
            signed: true,
            bits: 32,
            align_bits: 0,
        },
        resolution_mode: mode,
        pair_group: None,
        pair_role: None,
    }
}

fn x86_p1(registry: &Registry) -> PlanBuilder {
    PlanBuilder::new(
        target("x86", "x86-64", "64", &[], 64),
        definition(registry, "monasm.isa.x86", "0.1.0"),
        output_bytes(&[".text"]),
        vec![section(
            ".text",
            SectionKind::Code,
            true,
            None,
            6,
            vec![
                frag_instruction(0, 3, "I0001"),
                frag_instruction(3, 3, "I0002"),
            ],
        )],
        Vec::new(),
        vec![
            ins(
                "I0001",
                ".text",
                0,
                "x86:mov/rm-r64/legacy",
                vec![
                    reg("dest", "x86.gpr64", "rm64", 0),
                    reg("src", "x86.gpr64", "r64", 3),
                ],
                3,
            ),
            ins(
                "I0002",
                ".text",
                3,
                "x86:mov/r64-rm/legacy",
                vec![
                    reg("dest", "x86.gpr64", "r64", 0),
                    reg("src", "x86.gpr64", "rm64", 3),
                ],
                3,
            ),
        ],
        Vec::new(),
    )
}

fn a64_p2(registry: &Registry) -> PlanBuilder {
    PlanBuilder::new(
        target("aarch64", "aarch64", "n/a", &[], 64),
        definition(registry, "monasm.isa.aarch64", "0.1.0"),
        output_bytes(&[".text"]),
        vec![section(
            ".text",
            SectionKind::Code,
            true,
            None,
            8,
            vec![
                frag_instruction(0, 4, "I0001"),
                frag_instruction(4, 4, "I0002"),
            ],
        )],
        Vec::new(),
        vec![
            ins(
                "I0001",
                ".text",
                0,
                "aarch64:add/x64-imm12-lsl0",
                vec![
                    reg("dest", "aarch64.gpr64", "x64", 0),
                    reg("src", "aarch64.gpr64", "x64", 1),
                    imm("imm", "aarch64.imm", "imm12", 0),
                ],
                4,
            ),
            ins(
                "I0002",
                ".text",
                4,
                "aarch64:add/x64-imm12-lsl0",
                vec![
                    reg("dest", "aarch64.gpr64", "x64", 2),
                    reg("src", "aarch64.gpr64", "x64", 3),
                    imm("imm", "aarch64.imm", "imm12", 4095),
                ],
                4,
            ),
        ],
        Vec::new(),
    )
}

fn rv_p1(registry: &Registry) -> PlanBuilder {
    PlanBuilder::new(
        target("riscv", "rv64", "n/a", &["rv64i"], 64),
        definition(registry, "monasm.isa.riscv", "0.1.0"),
        output_bytes(&[".text"]),
        vec![section(
            ".text",
            SectionKind::Code,
            true,
            None,
            12,
            vec![
                frag_instruction(0, 4, "I0001"),
                frag_instruction(4, 4, "I0002"),
                frag_instruction(8, 4, "I0003"),
            ],
        )],
        Vec::new(),
        vec![
            ins(
                "I0001",
                ".text",
                0,
                "riscv:add/rd-rs1-rs2",
                vec![
                    reg("dest", "riscv.xreg", "xreg", 10),
                    reg("src", "riscv.xreg", "xreg", 11),
                    reg("src2", "riscv.xreg", "xreg", 12),
                ],
                4,
            ),
            ins(
                "I0002",
                ".text",
                4,
                "riscv:add/rd-rs1-rs2",
                vec![
                    reg("dest", "riscv.xreg", "xreg", 15),
                    reg("src", "riscv.xreg", "xreg", 16),
                    reg("src2", "riscv.xreg", "xreg", 17),
                ],
                4,
            ),
            ins(
                "I0003",
                ".text",
                8,
                "riscv:add/rd-rs1-rs2",
                vec![
                    reg("dest", "riscv.xreg", "xreg", 10),
                    reg("src", "riscv.xreg", "xreg", 0),
                    reg("src2", "riscv.xreg", "xreg", 11),
                ],
                4,
            ),
        ],
        Vec::new(),
    )
}

fn x86_p71(registry: &Registry) -> PlanBuilder {
    PlanBuilder::new(
        target("x86", "x86-64", "64", &[], 64),
        definition(registry, "monasm.isa.x86", "0.2.0"),
        output_level_one(&[".text", ".bss"], &["ext", "S2", "S1"]),
        vec![
            section(
                ".text",
                SectionKind::Code,
                true,
                None,
                43,
                vec![
                    frag_instruction(0, 7, "I0001"),
                    frag_instruction(7, 7, "I0002"),
                    frag_fill(14, 2, 0),
                    frag_instruction(16, 7, "I0003"),
                    frag_fill(23, 9, 0),
                    frag_data(32, &[0xaa, 0xbb, 0xcc, 0xdd]),
                    frag_instruction(36, 7, "I0004"),
                ],
            ),
            section(".bss", SectionKind::Bss, false, None, 8, Vec::new()),
        ],
        vec![
            Symbol {
                symbol_id: "ext".to_string(),
                name: "ext".to_string(),
                kind: SymbolKind::External,
                binding: Binding::Global,
                section_id: None,
                offset: None,
            },
            Symbol {
                symbol_id: "S2".to_string(),
                name: "S2".to_string(),
                kind: SymbolKind::Defined,
                binding: Binding::Local,
                section_id: Some(".bss".to_string()),
                offset: Some(0),
            },
            Symbol {
                symbol_id: "S1".to_string(),
                name: "L1".to_string(),
                kind: SymbolKind::Defined,
                binding: Binding::Local,
                section_id: Some(".text".to_string()),
                offset: Some(32),
            },
        ],
        vec![
            ins(
                "I0001",
                ".text",
                0,
                "x86:mov/r64-riprel32/legacy",
                vec![
                    reg("dest", "x86.gpr64", "r64", 0),
                    imm("target", "x86.rel", "riprel32", 16),
                ],
                7,
            ),
            ins(
                "I0002",
                ".text",
                7,
                "x86:mov/r64-riprel32/legacy",
                vec![
                    reg("dest", "x86.gpr64", "r64", 1),
                    symbol_operand("target", "x86.rel", "riprel32", "S1"),
                ],
                7,
            ),
            ins(
                "I0003",
                ".text",
                16,
                "x86:mov/riprel32-r64/legacy",
                vec![
                    reg("src", "x86.gpr64", "r64", 2),
                    symbol_operand("target", "x86.rel", "riprel32", "S1"),
                ],
                7,
            ),
            ins(
                "I0004",
                ".text",
                36,
                "x86:mov/r64-riprel32/legacy",
                vec![
                    reg("dest", "x86.gpr64", "r64", 3),
                    symbol_operand("target", "x86.rel", "riprel32", "ext"),
                ],
                7,
            ),
        ],
        vec![
            fixup(
                "F0001",
                7,
                FixupTarget::Symbol("S1".to_string()),
                ResolutionMode::ResolveInPlace,
            ),
            fixup(
                "F0002",
                16,
                FixupTarget::Symbol("S1".to_string()),
                ResolutionMode::ResolveInPlace,
            ),
            fixup(
                "F0003",
                36,
                FixupTarget::Symbol("ext".to_string()),
                ResolutionMode::EmitRelocation,
            ),
        ],
    )
}

#[test]
fn from_scratch_positives_materialize_to_the_oracle_bytes() {
    let registry = registry();
    let cases: Vec<(&str, &str, PlanBuilder)> = vec![
        (
            "x86_64",
            "X86-P1-mov-r64-both-directions",
            x86_p1(&registry),
        ),
        ("aarch64", "A64-P2-add-imm12", a64_p2(&registry)),
        ("rv64", "RV-P1-add-register", rv_p1(&registry)),
        ("x86_64", "X86-P71-level-one-sections", x86_p71(&registry)),
    ];

    for (isa, name, builder) in cases {
        let bytes = builder.build_canonical();
        let plan = fmp_model::plan::read(&bytes).unwrap_or_else(|error| {
            panic!("{name}: built document does not read: {}", error.message())
        });
        let definition = registry
            .find(&plan.definition.namespace, &plan.definition.version)
            .unwrap_or_else(|error| panic!("{name}: {}", error.message()));
        let artifact = match fmp_materialize::materialize(&plan, definition) {
            Ok(artifact) => artifact,
            Err(errors) => panic!(
                "{name} built from scratch was rejected:\n{}",
                errors
                    .iter()
                    .map(|error| error.message())
                    .collect::<Vec<_>>()
                    .join("\n")
            ),
        };

        let dir = root().join("fixtures").join(isa).join("positive");
        let expected_path = dir.join(format!("{name}.expected.bin"));
        let expected = std::fs::read(&expected_path)
            .unwrap_or_else(|error| panic!("{}: {error}", expected_path.display()));
        assert_eq!(
            artifact.bytes_hex(),
            hex(&expected),
            "{name}: from-scratch bytes differ from the oracle's"
        );

        let artifact_path = dir.join(format!("{name}.expected-artifact.json"));
        if artifact_path.is_file() {
            let expected = std::fs::read(&artifact_path)
                .unwrap_or_else(|error| panic!("{}: {error}", artifact_path.display()));
            let expected = fmp_model::json::parse(&expected)
                .unwrap_or_else(|error| panic!("{}: {}", artifact_path.display(), error.reason()));
            assert_eq!(
                artifact.to_json(),
                expected,
                "{name}: from-scratch Level 1 envelope differs"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Closed key sets and round trip
// ---------------------------------------------------------------------------

fn field<'a>(value: &'a Json, key: &str) -> &'a Json {
    value
        .get(key)
        .unwrap_or_else(|| panic!("object has no `{key}`"))
}

fn key_set(value: &Json) -> Vec<String> {
    let mut keys: Vec<String> = value
        .as_object()
        .unwrap_or_else(|| panic!("expected an object, found {}", value.kind()))
        .iter()
        .map(|(key, _)| key.clone())
        .collect();
    keys.sort();
    keys
}

fn expect_keys(value: &Json, expected: &[&str], what: &str) {
    let mut wanted: Vec<String> = expected.iter().map(|key| key.to_string()).collect();
    wanted.sort();
    assert_eq!(key_set(value), wanted, "{what}: wrong closed key set");
}

#[test]
fn emitted_objects_have_exactly_the_closed_key_sets() {
    let registry = registry();
    let bytes = x86_p71(&registry).build_canonical();
    let document = fmp_model::json::parse(&bytes).expect("built document parses");

    expect_keys(
        &document,
        &[
            "format_version",
            "target_identity",
            "definition_identity",
            "output_contract",
            "sections",
            "symbols",
            "instructions",
            "fixups",
        ],
        "root",
    );
    expect_keys(
        field(&document, "target_identity"),
        &[
            "isa_family",
            "isa_variant",
            "execution_mode",
            "enabled_extensions",
            "feature_constraints",
            "byte_order",
            "address_width",
        ],
        "target_identity",
    );
    expect_keys(
        field(&document, "definition_identity"),
        &["namespace", "version", "digest"],
        "definition_identity",
    );
    expect_keys(
        field(&document, "output_contract"),
        &[
            "artifact",
            "section_order",
            "symbol_order",
            "fixup_record_order",
            "include_symbol_table",
            "emit_fixups",
        ],
        "output_contract",
    );

    let sections = field(&document, "sections").as_array().expect("sections");
    expect_keys(
        &sections[0],
        &[
            "section_id",
            "section_kind",
            "image_backed",
            "declared_size",
            "fragments",
        ],
        "section",
    );
    let fragments = field(&sections[0], "fragments")
        .as_array()
        .expect("fragments");
    expect_keys(
        &fragments[0],
        &["offset", "size", "kind", "instruction_id"],
        "instruction fragment",
    );
    expect_keys(
        &fragments[2],
        &["offset", "size", "kind", "fill_byte"],
        "fill fragment",
    );
    expect_keys(
        &fragments[5],
        &["offset", "size", "kind", "payload_hex"],
        "data fragment",
    );

    let symbols = field(&document, "symbols").as_array().expect("symbols");
    expect_keys(
        &symbols[0],
        &["symbol_id", "name", "kind", "binding"],
        "external symbol",
    );
    expect_keys(
        &symbols[1],
        &[
            "symbol_id",
            "name",
            "kind",
            "binding",
            "section_id",
            "offset",
        ],
        "defined symbol",
    );

    let instructions = field(&document, "instructions")
        .as_array()
        .expect("instructions");
    expect_keys(
        &instructions[0],
        &[
            "instruction_id",
            "section_id",
            "offset",
            "form_id",
            "operands",
            "expected_size",
        ],
        "instruction",
    );
    let operands = field(&instructions[0], "operands")
        .as_array()
        .expect("operands");
    expect_keys(
        &operands[0],
        &["role", "kind", "target_type", "payload", "modifiers"],
        "operand",
    );

    let fixups = field(&document, "fixups").as_array().expect("fixups");
    expect_keys(
        &fixups[0],
        &[
            "fixup_id",
            "section_id",
            "offset",
            "field_descriptor",
            "target",
            "addend",
            "pc_reference_rule",
            "value_transform",
            "range_constraint",
            "resolution_mode",
        ],
        "fixup",
    );
    let descriptor = field(&fixups[0], "field_descriptor")
        .as_array()
        .expect("field_descriptor");
    expect_keys(&descriptor[0], &["lsb", "width"], "field_range");
    expect_keys(
        field(&fixups[0], "range_constraint"),
        &["signed", "bits", "align_bits"],
        "range_constraint",
    );
    expect_keys(
        field(&fixups[0], "target"),
        &["kind", "symbol_id"],
        "symbol target",
    );
}

#[test]
fn reemission_is_a_fixed_point() {
    let registry = registry();
    let bytes = x86_p71(&registry).build_canonical();
    let plan = fmp_model::plan::read(&bytes).expect("built document reads");
    let again = PlanBuilder::from_model(&plan)
        .expect("rebuilt plan is representable")
        .build_canonical();
    assert_eq!(again, bytes, "from_model -> build must not drift");
}

// ---------------------------------------------------------------------------
// Optional members and closed enum spellings
// ---------------------------------------------------------------------------

/// One document that sets every optional member the builder can emit. The
/// closed-key test uses `x86_p71`, which sets none of them, so this is what
/// proves an optional field is written under the name the reader expects.
fn maximal(registry: &Registry) -> PlanBuilder {
    PlanBuilder::new(
        target("aarch64", "aarch64", "n/a", &[], 64),
        definition(registry, "monasm.isa.aarch64", "0.1.0"),
        OutputContract {
            artifact: Artifact::Sections,
            section_order: vec![".text".to_string(), ".data".to_string()],
            symbol_order: Some(vec!["S1".to_string(), "S2".to_string(), "S3".to_string()]),
            fixup_record_order: FixupRecordOrder::SectionIdOffsetFixupId,
            include_symbol_table: true,
            emit_fixups: true,
        },
        vec![
            section(
                ".text",
                SectionKind::Code,
                true,
                Some(4096),
                8,
                vec![frag_instruction(0, 4, "I0001"), frag_fill(4, 4, 0x90)],
            ),
            section(
                ".data",
                SectionKind::Data,
                true,
                None,
                4,
                vec![frag_data(0, &[0x01, 0x02, 0x03, 0x04])],
            ),
        ],
        vec![
            Symbol {
                symbol_id: "S1".to_string(),
                name: "defined".to_string(),
                kind: SymbolKind::Defined,
                binding: Binding::Global,
                section_id: Some(".text".to_string()),
                offset: Some(0),
            },
            Symbol {
                symbol_id: "S2".to_string(),
                name: "undefined".to_string(),
                kind: SymbolKind::Undefined,
                binding: Binding::Weak,
                section_id: None,
                offset: None,
            },
            Symbol {
                symbol_id: "S3".to_string(),
                name: "external".to_string(),
                kind: SymbolKind::External,
                binding: Binding::Local,
                section_id: None,
                offset: None,
            },
        ],
        vec![Instruction {
            instruction_id: "I0001".to_string(),
            section_id: ".text".to_string(),
            offset: 0,
            form_id: "aarch64:add/x64-imm12-lsl0".to_string(),
            operands: vec![
                Operand {
                    role: "dest".to_string(),
                    kind: "aarch64.gpr64".to_string(),
                    target_type: "x64".to_string(),
                    payload: Payload::Empty,
                    modifiers: vec![
                        Modifier {
                            name: "lsl".to_string(),
                            value: ModifierValue::Int(3),
                        },
                        Modifier {
                            name: "note".to_string(),
                            value: ModifierValue::Text("x".to_string()),
                        },
                        Modifier {
                            name: "flag".to_string(),
                            value: ModifierValue::Bool(true),
                        },
                    ],
                },
                reg("src", "aarch64.gpr64", "x64", 1),
                imm("imm", "aarch64.imm", "imm12", 1),
            ],
            expected_size: 4,
            expected_digest: Some("sha256:00112233".to_string()),
        }],
        vec![Fixup {
            fixup_id: "F0001".to_string(),
            section_id: ".text".to_string(),
            offset: 0,
            field_descriptor: vec![
                FieldRange { lsb: 5, width: 19 },
                FieldRange { lsb: 29, width: 2 },
            ],
            target: FixupTarget::Absolute(4096),
            addend: -4,
            pc_reference_rule: PcRule::PcrelPage,
            value_transform: Transform::Page,
            transform_shift: Some(2),
            range_constraint: RangeConstraint {
                signed: true,
                bits: 21,
                align_bits: 0,
            },
            resolution_mode: ResolutionMode::EmitRelocation,
            pair_group: Some("P1".to_string()),
            pair_role: Some(PairRole::Hi),
        }],
    )
    .provenance(Provenance {
        materializer_version: "0.0.0".to_string(),
        build_profile: Some("release".to_string()),
        generated_by: Some("planner_api.rs".to_string()),
        notes: Some("maximal".to_string()),
    })
}

#[test]
fn optional_members_are_emitted_and_read_back_unchanged() {
    let registry = registry();
    let bytes = maximal(&registry).build_canonical();
    let document = fmp_model::json::parse(&bytes).expect("built document parses");

    expect_keys(
        &document,
        &[
            "format_version",
            "target_identity",
            "definition_identity",
            "output_contract",
            "sections",
            "symbols",
            "instructions",
            "fixups",
            "provenance",
        ],
        "root with provenance",
    );
    expect_keys(
        field(&document, "output_contract"),
        &[
            "artifact",
            "section_order",
            "symbol_order",
            "fixup_record_order",
            "include_symbol_table",
            "emit_fixups",
        ],
        "output_contract with symbol_order",
    );
    let sections = field(&document, "sections").as_array().expect("sections");
    expect_keys(
        &sections[0],
        &[
            "section_id",
            "section_kind",
            "image_backed",
            "base_address",
            "declared_size",
            "fragments",
        ],
        "section with base_address",
    );
    let instructions = field(&document, "instructions")
        .as_array()
        .expect("instructions");
    expect_keys(
        &instructions[0],
        &[
            "instruction_id",
            "section_id",
            "offset",
            "form_id",
            "operands",
            "expected_size",
            "expected_digest",
        ],
        "instruction with expected_digest",
    );
    let fixups = field(&document, "fixups").as_array().expect("fixups");
    expect_keys(
        &fixups[0],
        &[
            "fixup_id",
            "section_id",
            "offset",
            "field_descriptor",
            "target",
            "addend",
            "pc_reference_rule",
            "value_transform",
            "transform_shift",
            "range_constraint",
            "resolution_mode",
            "pair_group",
            "pair_role",
        ],
        "fixup with every optional",
    );
    expect_keys(
        field(&fixups[0], "target"),
        &["kind", "address"],
        "absolute target",
    );
    expect_keys(
        field(&document, "provenance"),
        &[
            "materializer_version",
            "build_profile",
            "generated_by",
            "notes",
        ],
        "provenance",
    );

    let plan = fmp_model::plan::read(&bytes).expect("built document reads");
    let provenance = plan.provenance.as_ref().expect("provenance survives");
    assert_eq!(provenance.materializer_version, "0.0.0");
    assert_eq!(provenance.build_profile.as_deref(), Some("release"));
    assert_eq!(provenance.generated_by.as_deref(), Some("planner_api.rs"));
    assert_eq!(provenance.notes.as_deref(), Some("maximal"));
    assert_eq!(
        plan.output.symbol_order,
        Some(vec!["S1".to_string(), "S2".to_string(), "S3".to_string()])
    );
    assert_eq!(plan.sections[0].base_address, Some(4096));
    assert_eq!(plan.sections[1].section_kind, model::SectionKind::Data);
    assert_eq!(
        plan.sections[1].fragments[0].body,
        model::FragmentBody::Data("01020304".to_string())
    );
    assert_eq!(plan.symbols[1].binding, model::Binding::Weak);
    assert_eq!(
        plan.instructions[0].expected_digest.as_deref(),
        Some("sha256:00112233")
    );
    assert_eq!(
        plan.instructions[0].operands[0].payload,
        model::Payload::Empty
    );
    assert_eq!(
        plan.instructions[0].operands[0].modifiers[2].value,
        model::ModifierValue::Bool(true)
    );
    assert_eq!(plan.fixups[0].target, model::FixupTarget::Absolute(4096));
    assert_eq!(plan.fixups[0].addend, -4);
    assert_eq!(plan.fixups[0].transform_shift, Some(2));
    assert_eq!(plan.fixups[0].pair_group.as_deref(), Some("P1"));
    assert_eq!(plan.fixups[0].pair_role, Some(model::PairRole::Hi));
}

/// Every closed enum member the builder exposes must be spelled exactly as the
/// reader spells it. A rename on either side turns the reader's value into
/// `Unknown(..)`, so comparing the variant name catches it.
#[test]
fn every_closed_enum_spelling_round_trips() {
    let registry = registry();

    let artifacts = [Artifact::Bytes, Artifact::Sections];
    for artifact in artifacts {
        let mut output = output_bytes(&[".text"]);
        output.artifact = artifact;
        if artifact == Artifact::Sections {
            output.include_symbol_table = true;
        }
        let bytes = PlanBuilder::new(
            target("x86", "x86-64", "64", &[], 64),
            definition(&registry, "monasm.isa.x86", "0.1.0"),
            output,
            Vec::new(),
            Vec::new(),
            Vec::new(),
            Vec::new(),
        )
        .build_canonical();
        let plan = fmp_model::plan::read(&bytes).expect("artifact spelling reads");
        assert_eq!(
            format!("{:?}", plan.output.artifact),
            format!("{artifact:?}")
        );
    }

    let kinds = [
        SectionKind::Code,
        SectionKind::Data,
        SectionKind::Rodata,
        SectionKind::Bss,
    ];
    let symbol_kinds = [
        SymbolKind::Defined,
        SymbolKind::Undefined,
        SymbolKind::External,
    ];
    let bindings = [Binding::Local, Binding::Global, Binding::Weak];

    let mut sections = Vec::new();
    for (index, kind) in kinds.iter().enumerate() {
        sections.push(section(
            &format!(".s{index}"),
            *kind,
            kind == &SectionKind::Code,
            None,
            0,
            Vec::new(),
        ));
    }
    let mut symbols = Vec::new();
    for (index, kind) in symbol_kinds.iter().enumerate() {
        for (inner, binding) in bindings.iter().enumerate() {
            symbols.push(Symbol {
                symbol_id: format!("S{index}{inner}"),
                name: format!("S{index}{inner}"),
                kind: *kind,
                binding: *binding,
                section_id: None,
                offset: None,
            });
        }
    }

    let rules = [
        PcRule::None,
        PcRule::PcrelBegin,
        PcRule::PcrelEnd,
        PcRule::PcrelPage,
        PcRule::PcrelHi,
    ];
    let transforms = [
        Transform::Identity,
        Transform::Scale,
        Transform::Page,
        Transform::Hi20,
        Transform::Lo12I,
        Transform::Lo12S,
        Transform::PcrelHi20,
        Transform::PcrelLo12,
    ];
    let modes = [
        ResolutionMode::ResolveInPlace,
        ResolutionMode::EmitRelocation,
    ];
    let roles = [PairRole::Hi, PairRole::Lo];

    let mut fixups = Vec::new();
    for rule in rules {
        let mut entry = plain_fixup(&format!("R{}", fixups.len()));
        entry.pc_reference_rule = rule;
        fixups.push(entry);
    }
    for transform in transforms {
        let mut entry = plain_fixup(&format!("T{}", fixups.len()));
        entry.value_transform = transform;
        fixups.push(entry);
    }
    for mode in modes {
        let mut entry = plain_fixup(&format!("M{}", fixups.len()));
        entry.resolution_mode = mode;
        fixups.push(entry);
    }
    for role in roles {
        let mut entry = plain_fixup(&format!("P{}", fixups.len()));
        entry.pair_role = Some(role);
        fixups.push(entry);
    }

    let bytes = PlanBuilder::new(
        target("x86", "x86-64", "64", &[], 64),
        definition(&registry, "monasm.isa.x86", "0.1.0"),
        output_bytes(&[".s0", ".s1", ".s2", ".s3"]),
        sections,
        symbols,
        Vec::new(),
        fixups,
    )
    .build_canonical();
    let plan = fmp_model::plan::read(&bytes).expect("enum spellings read");

    for (index, kind) in kinds.iter().enumerate() {
        assert_eq!(
            format!("{:?}", plan.sections[index].section_kind),
            format!("{kind:?}"),
            "section_kind {kind:?}"
        );
    }
    for (index, kind) in symbol_kinds.iter().enumerate() {
        for (inner, binding) in bindings.iter().enumerate() {
            let symbol = &plan.symbols[index * bindings.len() + inner];
            assert_eq!(format!("{:?}", symbol.kind), format!("{kind:?}"));
            assert_eq!(format!("{:?}", symbol.binding), format!("{binding:?}"));
        }
    }
    let mut position = 0;
    for rule in rules {
        assert_eq!(
            format!("{:?}", plan.fixups[position].pc_reference_rule),
            format!("{rule:?}")
        );
        position += 1;
    }
    for transform in transforms {
        assert_eq!(
            format!("{:?}", plan.fixups[position].value_transform),
            format!("{transform:?}")
        );
        position += 1;
    }
    for mode in modes {
        assert_eq!(
            format!("{:?}", plan.fixups[position].resolution_mode),
            format!("{mode:?}")
        );
        position += 1;
    }
    for role in roles {
        assert_eq!(
            plan.fixups[position]
                .pair_role
                .as_ref()
                .map(|value| format!("{value:?}")),
            Some(format!("{role:?}"))
        );
        position += 1;
    }
}

fn plain_fixup(id: &str) -> Fixup {
    Fixup {
        fixup_id: id.to_string(),
        section_id: ".s0".to_string(),
        offset: 0,
        field_descriptor: vec![FieldRange { lsb: 0, width: 8 }],
        target: FixupTarget::Symbol("S00".to_string()),
        addend: 0,
        pc_reference_rule: PcRule::None,
        value_transform: Transform::Identity,
        transform_shift: None,
        range_constraint: RangeConstraint {
            signed: false,
            bits: 8,
            align_bits: 0,
        },
        resolution_mode: ResolutionMode::ResolveInPlace,
        pair_group: None,
        pair_role: None,
    }
}

// ---------------------------------------------------------------------------
// Structural exclusion, determinism and typed failure
// ---------------------------------------------------------------------------

#[test]
fn read_phase_negatives_never_produce_a_bound_plan() {
    let mut found: Vec<String> = Vec::new();
    for path in negatives() {
        let expected = expected_error(&path);
        if expected.get("phase").and_then(Json::as_str) != Some("read") {
            continue;
        }
        let name = stem(&path);
        let bytes = std::fs::read(&path).expect("fixture file");
        assert!(
            fmp_model::plan::read(&bytes).is_err(),
            "{name}: a read-phase negative must not bind"
        );
        found.push(name);
    }
    found.sort();
    assert_eq!(
        found,
        vec![
            "N15-composite-memory-payload",
            "N21a-unknown-root-field",
            "N21b-unknown-instruction-field",
            "N23a-expression-shaped-value",
            "N24a-unsupported-format-version",
            "N24b-missing-required-field",
        ]
    );
}

#[test]
fn building_twice_is_byte_identical() {
    let registry = registry();
    let first = x86_p71(&registry).build_canonical();
    let second = x86_p71(&registry).build_canonical();
    assert_eq!(first, second);
}

#[test]
fn closed_sets_report_unrepresentable_values() {
    let registry = registry();
    let bytes = x86_p71(&registry).build_canonical();

    let mut plan = fmp_model::plan::read(&bytes).expect("built document reads");
    plan.output.artifact = fmp_model::plan::Artifact::Unknown("elf".to_string());
    let error = PlanBuilder::from_model(&plan).expect_err("an unknown artifact has no slot");
    assert_eq!(error.path, "/output_contract/artifact");
    assert_eq!(error.value, "elf");

    let mut plan = fmp_model::plan::read(&bytes).expect("built document reads");
    plan.fixups[0].target = fmp_model::plan::FixupTarget::SectionRelative(".text".to_string());
    let error = PlanBuilder::from_model(&plan).expect_err("section_relative is out of scope");
    assert_eq!(error.path, "/fixups/0/target/kind");
    assert_eq!(error.value, "section_relative");

    let mut plan = fmp_model::plan::read(&bytes).expect("built document reads");
    plan.output.fixup_record_order = "fixup_id".to_string();
    let error = PlanBuilder::from_model(&plan).expect_err("a non-default order is a version error");
    assert_eq!(error.path, "/output_contract/fixup_record_order");
    assert_eq!(error.value, "fixup_id");
}
