//! H1b (`ADR-0127`, D13/D15): the binding entry point rejects at the stage the
//! input's boundary requires.
//!
//! H1a called `check_structure`/`check` directly, because `bind` did not exist.
//! This file is the same input set through the public entry: structural damage
//! stops at `check_structure`, type-legal but semantically illegal plans reach
//! `check`, and a declared definition identity must match the bound object.
//! "The materializer was not called" is structural here: no `ValidatedPlan`
//! exists, and `fmp_materialize::materialize` accepts nothing else.

use std::path::PathBuf;
use std::sync::Arc;

use fmp_model::codes;
use fmp_model::definition::Definition;
use fmp_model::diagnostic::{Detail, Diagnostic};
use fmp_model::json::{self, Json};
use fmp_model::plan::{self, FragmentBody, PcRule, Plan};
use fmp_model::Registry;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn registry() -> Registry {
    Registry::load_dir(&root().join("definitions")).expect("definitions/ must load")
}

fn read_bytes(isa: &str, name: &str) -> Vec<u8> {
    let path = root().join(format!("fixtures/{isa}/positive/{name}.fmp.json"));
    std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()))
}

fn positive(isa: &str, name: &str) -> (Plan, Arc<Definition>) {
    let bytes = read_bytes(isa, name);
    let plan = plan::read(&bytes).expect("the fixture parses");
    let definition = registry()
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the fixture's definition exists");
    (plan, definition)
}

fn detail(error: &Diagnostic, key: &'static str) -> Option<String> {
    error.details().get(key).map(Detail::render)
}

fn assert_domain(error: &Diagnostic, path: &str, domain: &str, found: &str) {
    assert_eq!(error.code(), codes::E_PLAN_002);
    assert_eq!(error.path(), path);
    assert_eq!(detail(error, "path_type").as_deref(), Some(domain));
    assert_eq!(detail(error, "found_kind").as_deref(), Some(found));
}

/// Replace the first data fragment's payload and return its JSON Pointer.
fn replace_data_payload(plan: &mut Plan, payload: &str) -> String {
    for section in &mut plan.sections {
        for fragment in &mut section.fragments {
            if matches!(fragment.body, FragmentBody::Data(_)) {
                fragment.body = FragmentBody::Data(payload.to_string());
                return fragment.path.clone();
            }
        }
    }
    panic!("X86-P71 has a data fragment");
}

/// Bind must return exactly the `check_structure` set, which is what "the
/// structure gate ran first and `check` never saw the DTO" means operationally.
fn assert_stops_at_structure(plan: Plan, definition: Arc<Definition>) {
    let structure = plan::check_structure(&plan);
    assert!(!structure.is_empty(), "the input is structurally illegal");
    let expected: Vec<(&str, &str)> = structure
        .iter()
        .map(|error| (error.code(), error.path()))
        .collect();

    let errors = fmp_validate::bind(plan, definition).expect_err("structure damage is rejected");
    let found: Vec<(&str, &str)> = errors
        .iter()
        .map(|error| (error.code(), error.path()))
        .collect();
    assert_eq!(
        found, expected,
        "bind must stop at `check_structure`, not add validator diagnostics"
    );
    assert!(
        errors
            .iter()
            .all(|error| error.code() != codes::E_INTERNAL_001),
        "{errors:#?}"
    );
}

/// The six structural inputs from `ADR-0127` §4.2, through `bind`.
#[test]
fn the_negatives_are_rejected_at_the_stage_their_boundary_requires() {
    let (mut plan, definition) = positive("x86_64", "X86-P71-level-one-sections");
    let pointer = replace_data_payload(&mut plan, "aabbccdd0");
    assert_stops_at_structure(plan, Arc::clone(&definition));

    let (mut plan, _) = positive("x86_64", "X86-P71-level-one-sections");
    let pointer_non_hex = replace_data_payload(&mut plan, "zzzzzzzz");
    assert_stops_at_structure(plan, Arc::clone(&definition));

    let (mut plan, _) = positive("aarch64", "A64-P4-b-cond");
    plan.fixups[0].range_constraint.align_bits = 128;
    assert_stops_at_structure(plan, Arc::clone(&definition));

    let (mut plan, _) = positive("aarch64", "A64-P4-b-cond");
    plan.fixups[0].transform_shift = Some(128);
    assert_stops_at_structure(plan, Arc::clone(&definition));

    for mutate in [
        (|plan: &mut Plan| plan.fixups[0].field_descriptor[0].lsb = 128) as fn(&mut Plan),
        |plan| plan.fixups[0].field_descriptor[0].width = 0,
        |plan| plan.fixups[0].field_descriptor[0].width = 65,
        |plan| plan.fixups[0].range_constraint.bits = 0,
        |plan| plan.fixups[0].range_constraint.bits = 65,
    ] {
        let (mut plan, _) = positive("aarch64", "A64-P4-b-cond");
        mutate(&mut plan);
        assert_stops_at_structure(plan, Arc::clone(&definition));
    }

    let (mut plan, _) = positive("aarch64", "A64-P4-b-cond");
    plan.fixups[0].field_descriptor = vec![
        fmp_model::plan::FieldRange {
            lsb: 0,
            width: u32::MAX,
        },
        fmp_model::plan::FieldRange {
            lsb: 1,
            width: u32::MAX,
        },
    ];
    assert_stops_at_structure(plan, Arc::clone(&definition));

    // The two pointers the structural cases landed on, so a future move of the
    // gate is visible even if the set comparison is loosened.
    let (mut data, _) = positive("x86_64", "X86-P71-level-one-sections");
    replace_data_payload(&mut data, "aabbccdd0");
    let errors =
        fmp_validate::bind(data, Arc::clone(&definition)).expect_err("odd-length hex is rejected");
    assert_domain(
        &errors[0],
        &format!("{pointer}/payload_hex"),
        "lowercase hex bytes",
        "aabbccdd0",
    );

    let (mut other, _) = positive("x86_64", "X86-P71-level-one-sections");
    let other_pointer = replace_data_payload(&mut other, "zzzzzzzz");
    let errors =
        fmp_validate::bind(other, Arc::clone(&definition)).expect_err("non-hex is rejected");
    assert_eq!(errors[0].path(), format!("{other_pointer}/payload_hex"));
    assert_eq!(errors[0].code(), codes::E_PLAN_002);
    let _ = pointer_non_hex;
}

/// Type-legal inputs (`offset: u64`) reach `check` and are rejected there.
#[test]
fn a_type_legal_offset_is_rejected_by_check_through_bind() {
    let bytes = read_bytes("aarch64", "A64-P4-b-cond");
    let mut document = json::parse(&bytes).expect("the fixture parses as JSON");
    set_fixup_offset(&mut document, 0, u64::MAX);
    set_fixup_offset(&mut document, 1, u64::MAX - 8);
    let plan = plan::read(&fmp_model::canonical::canonical_bytes(&document))
        .expect("u64::MAX is a legal offset");
    assert!(
        plan::check_structure(&plan).is_empty(),
        "the input is structurally legal, so only `check` may reject it"
    );
    let definition = registry()
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the fixture's definition exists");

    let errors = fmp_validate::bind(plan, definition).expect_err("the sites match no instruction");
    let paths: Vec<&str> = errors.iter().map(|error| error.path()).collect();
    assert!(paths.contains(&"/fixups/0/offset"), "{errors:#?}");
    assert!(paths.contains(&"/fixups/1/offset"), "{errors:#?}");
    assert!(
        errors
            .iter()
            .all(|error| error.code() != codes::E_INTERNAL_001),
        "{errors:#?}"
    );
}

/// D16: `page` needs a PC reference; the static rule now closes the branch the
/// encoder used to report as `E-INTERNAL-001`.
#[test]
fn a_page_transform_without_a_page_pc_rule_is_rejected_by_bind() {
    let (mut plan, definition) = positive("aarch64", "A64-P6-adrp-lo12-pair");
    assert!(matches!(
        &plan.fixups[0].pc_reference_rule,
        PcRule::PcrelPage
    ));
    plan.fixups[0].pc_reference_rule = PcRule::None;

    let errors = fmp_validate::bind(plan, definition).expect_err("`page` without `P` is illegal");
    let error = errors
        .iter()
        .find(|error| error.path() == "/fixups/0/pc_reference_rule")
        .unwrap_or_else(|| panic!("no pc_reference_rule diagnostic: {errors:#?}"));
    assert_eq!(error.code(), codes::E_FIXUP_001);
    assert_eq!(
        detail(error, "kind").as_deref(),
        Some("value_transform:page")
    );
    assert!(
        errors
            .iter()
            .all(|error| error.code() != codes::E_INTERNAL_001),
        "{errors:#?}"
    );
}

/// D15: the declared namespace is compared with the **bound** definition, not
/// only used to select one.
#[test]
fn a_declared_namespace_must_match_the_bound_definition() {
    let (mut plan, definition) = positive("x86_64", "X86-P1-mov-r64-both-directions");
    let declared = plan.definition.namespace.clone();
    plan.definition.namespace = "monasm.isa.probe".to_string();

    let errors = fmp_validate::bind(plan, definition).expect_err("the namespace does not match");
    assert_eq!(errors.len(), 1, "{errors:#?}");
    assert_eq!(errors[0].code(), codes::E_DEF_001);
    assert_eq!(errors[0].path(), "/definition_identity/namespace");
    assert_eq!(
        detail(&errors[0], "declared").as_deref(),
        Some("monasm.isa.probe")
    );
    assert_eq!(
        detail(&errors[0], "actual").as_deref(),
        Some(declared.as_str())
    );
}

/// D15: the same for `version`, and the digest-only negative keeps its single
/// diagnostic and Pointer.
#[test]
fn a_declared_version_must_match_the_bound_definition() {
    let (mut plan, definition) = positive("x86_64", "X86-P1-mov-r64-both-directions");
    let declared = plan.definition.version.clone();
    plan.definition.version = "9.9.9".to_string();

    let errors = fmp_validate::bind(plan, definition).expect_err("the version does not match");
    assert_eq!(errors.len(), 1, "{errors:#?}");
    assert_eq!(errors[0].code(), codes::E_DEF_001);
    assert_eq!(errors[0].path(), "/definition_identity/version");
    assert_eq!(detail(&errors[0], "declared").as_deref(), Some("9.9.9"));
    assert_eq!(
        detail(&errors[0], "actual").as_deref(),
        Some(declared.as_str())
    );

    let path = root().join("fixtures/x86_64/negative/N10-definition-digest-mismatch.fmp.json");
    let bytes = std::fs::read(&path).expect("the fixture is readable");
    let plan = plan::read(&bytes).expect("the fixture parses");
    let definition = registry()
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the fixture's definition exists");
    let errors = fmp_validate::bind(plan, definition).expect_err("the digest does not match");
    assert_eq!(errors.len(), 1, "{errors:#?}");
    assert_eq!(errors[0].code(), codes::E_DEF_001);
    assert_eq!(errors[0].path(), "/definition_identity/digest");
}

/// The identity recorded on the credential comes from the object that will be
/// executed, not from the plan's declaration.
#[test]
fn bind_reports_the_definition_it_bound() {
    let (plan, definition) = positive("x86_64", "X86-P1-mov-r64-both-directions");
    let expected = definition.digest().to_string();
    let expected_namespace = definition.namespace().to_string();
    let expected_version = definition.version().to_string();

    let validated = fmp_validate::bind(plan, definition).expect("the fixture binds");
    let identity = validated.identity().definition();
    assert_eq!(identity.digest(), expected);
    assert_eq!(identity.namespace(), expected_namespace);
    assert_eq!(identity.version(), expected_version);
    assert_eq!(validated.identity().plan().algorithm(), "plan-identity/0.1");
    assert_eq!(validated.plan().instructions.len(), 2);
}

fn set_fixup_offset(document: &mut Json, index: usize, value: u64) {
    let Json::Object(root) = document else {
        panic!("a plan is an object");
    };
    let fixups = root
        .iter_mut()
        .find(|(key, _)| key == "fixups")
        .map(|(_, value)| value)
        .expect("the fixture declares fixups");
    let Json::Array(items) = fixups else {
        panic!("fixups is an array");
    };
    let Json::Object(fixup) = &mut items[index] else {
        panic!("a fixup is an object");
    };
    let slot = fixup
        .iter_mut()
        .find(|(key, _)| key == "offset")
        .map(|(_, value)| value)
        .expect("a fixup has an offset");
    *slot = Json::Int(value as i128);
}
