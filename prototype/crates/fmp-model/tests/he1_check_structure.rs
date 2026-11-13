//! H1a (`ADR-0127`, D13): the parser's numeric and payload domains, re-checked
//! on the mutable DTO.
//!
//! `plan::read` enforces these domains, but `Plan` is a public DTO: the planner
//! API and the negative tests build illegal states by editing fields after the
//! reader returned. `check_structure` is the second gate for exactly the rules
//! the types cannot hold. These tests call it directly (H1a's stage boundary);
//! H1b repeats the same inputs through `bind`.

use std::path::PathBuf;

use fmp_model::codes;
use fmp_model::diagnostic::Detail;
use fmp_model::plan::{self, check_structure, FragmentBody, Plan};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn positive(isa: &str, name: &str) -> Plan {
    let path = root().join(format!("fixtures/{isa}/positive/{name}.fmp.json"));
    let bytes = std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    plan::read(&bytes).unwrap_or_else(|error| panic!("{}: {}", path.display(), error.message()))
}

fn detail(error: &fmp_model::Diagnostic, key: &'static str) -> Option<String> {
    error.details().get(key).map(Detail::render)
}

fn only(errors: &[fmp_model::Diagnostic]) -> &fmp_model::Diagnostic {
    assert_eq!(errors.len(), 1, "expected one diagnostic, got {errors:#?}");
    &errors[0]
}

fn assert_domain(error: &fmp_model::Diagnostic, path: &str, domain: &str, found: &str) {
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

/// D13: `payload_hex` is even-length lowercase hex. The old encoder checks the
/// length as `hex.len() / 2`, so an odd-length string with a whole number of
/// bytes (`9 / 2 == 4`) reached `decode_hex` and its last nibble was dropped.
#[test]
fn a_data_fragment_with_odd_length_hex_is_rejected_by_check_structure() {
    let mut plan = positive("x86_64", "X86-P71-level-one-sections");
    let pointer = replace_data_payload(&mut plan, "aabbccdd0");

    let errors = check_structure(&plan);
    let error = only(&errors);
    assert_eq!(error.code(), codes::E_PLAN_002);
    assert_eq!(error.path(), format!("{pointer}/payload_hex"));
    assert_eq!(
        detail(error, "path_type").as_deref(),
        Some("lowercase hex bytes")
    );
}

/// D13: `decode_hex`'s `digit()` maps every non-hex byte to `0`, so `"zzzzzzzz"`
/// used to emit four zero bytes instead of rejecting the plan.
#[test]
fn a_data_fragment_with_non_hex_payload_is_rejected_by_check_structure() {
    let mut plan = positive("x86_64", "X86-P71-level-one-sections");
    let pointer = replace_data_payload(&mut plan, "zzzzzzzz");

    let errors = check_structure(&plan);
    let error = only(&errors);
    assert_eq!(error.code(), codes::E_PLAN_002);
    assert_eq!(error.path(), format!("{pointer}/payload_hex"));
}

/// D13: `align_bits` is bounded to 12 by the reader. Without the bound,
/// `1i128 << align_bits` panics at 128 in debug.
#[test]
fn an_alignment_outside_the_parser_bound_is_rejected_by_check_structure() {
    let mut plan = positive("aarch64", "A64-P4-b-cond");
    plan.fixups[0].range_constraint.align_bits = 128;

    let errors = check_structure(&plan);
    let error = only(&errors);
    assert_domain(
        error,
        "/fixups/0/range_constraint/align_bits",
        "u4",
        "integer 128",
    );
}

/// D13: `transform_shift` is bounded to 63 by the reader.
#[test]
fn a_transform_shift_outside_the_parser_bound_is_rejected_by_check_structure() {
    let mut plan = positive("aarch64", "A64-P4-b-cond");
    plan.fixups[0].transform_shift = Some(128);

    let errors = check_structure(&plan);
    let error = only(&errors);
    assert_domain(error, "/fixups/0/transform_shift", "u6", "integer 128");
}

/// D13: the five remaining numeric domains (`lsb`, `width`, `bits`). Each miss
/// has to be rejected before `check`'s sums and bit loops see the value.
#[test]
fn a_field_range_outside_the_parser_bound_is_rejected_by_check_structure() {
    let cases: &[(&str, fn(&mut Plan), &str, &str)] = &[
        (
            "lsb > 127",
            |plan| plan.fixups[0].field_descriptor[0].lsb = 128,
            "/fixups/0/field_descriptor/0/lsb",
            "integer 128",
        ),
        (
            "width = 0",
            |plan| plan.fixups[0].field_descriptor[0].width = 0,
            "/fixups/0/field_descriptor/0/width",
            "integer 0",
        ),
        (
            "width > 64",
            |plan| plan.fixups[0].field_descriptor[0].width = 65,
            "/fixups/0/field_descriptor/0/width",
            "integer 65",
        ),
        (
            "bits = 0",
            |plan| plan.fixups[0].range_constraint.bits = 0,
            "/fixups/0/range_constraint/bits",
            "integer 0",
        ),
        (
            "bits > 64",
            |plan| plan.fixups[0].range_constraint.bits = 65,
            "/fixups/0/range_constraint/bits",
            "integer 65",
        ),
    ];

    for (name, mutate, path, found) in cases {
        let mut plan = positive("aarch64", "A64-P4-b-cond");
        mutate(&mut plan);
        let errors = check_structure(&plan);
        let error = only(&errors);
        assert_domain(error, path, "u7", found);
        assert!(detail(error, "path_type").is_some(), "{name}");
    }
}
