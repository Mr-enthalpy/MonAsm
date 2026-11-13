//! H1a (`ADR-0127`, §4.3): measure where the post-encode negatives actually
//! fail, instead of reading the answer off function names.
//!
//! `fmp_validate::check` is steps 2–7; `fmp_materialize::materialize` re-runs it
//! and then encodes. A case whose diagnostic appears only in the second column
//! is a **post-encode** failure: it must not be described as a static rejection.
//! The plan's stage table names these as the only rows H1 may have to snapshot
//! at value level; a mismatch between this test and that table means the table
//! is corrected, not this test.

use std::path::PathBuf;
use std::sync::Arc;

use fmp_model::codes;
use fmp_model::definition::Definition;
use fmp_model::plan::{self, Plan};
use fmp_model::Registry;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn registry() -> Registry {
    Registry::load_dir(&root().join("definitions")).expect("definitions/ must load")
}

fn load(isa: &str, name: &str) -> (Plan, Arc<Definition>) {
    let path = root().join(format!("fixtures/{isa}/negative/{name}.fmp.json"));
    let bytes = std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    let plan = plan::read(&bytes)
        .unwrap_or_else(|error| panic!("{}: {}", path.display(), error.message()));
    let definition = registry()
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the fixture's definition exists");
    (plan, definition)
}

fn codes_of(errors: &[fmp_model::Diagnostic]) -> Vec<&'static str> {
    errors.iter().map(|error| error.code()).collect()
}

fn assert_post_encode(isa: &str, name: &str, expected: &'static str) {
    let (plan, definition) = load(isa, name);
    let static_errors = fmp_validate::check(&plan, &definition);
    assert!(
        static_errors.is_empty(),
        "{name} is already rejected by `check`, so it is not post-encode: {static_errors:#?}"
    );

    let errors = fmp_materialize::materialize(&plan, &definition)
        .expect_err("the fixture is a recorded negative");
    assert_eq!(
        codes_of(&errors),
        vec![expected],
        "{name} failed at a different code"
    );
}

/// `expected_digest` is a check on the encoded bytes, so only `emit` can see it.
#[test]
fn a_digest_mismatch_is_post_encode() {
    assert_post_encode("x86_64", "N13-expected-digest-mismatch", codes::E_BYTE_001);
}

/// Pre-transform alignment is an `apply` rule, not a static one.
#[test]
fn a_fixup_alignment_failure_is_post_encode() {
    assert_post_encode(
        "aarch64",
        "N20-loadlit-fixup-misaligned",
        codes::E_RANGE_003,
    );
}

/// Post-transform range is an `apply` rule.
#[test]
fn a_fixup_range_failure_is_post_encode() {
    assert_post_encode(
        "x86_64",
        "N04b-rel32-absolute-out-of-range",
        codes::E_FIXUP_003,
    );
    assert_post_encode(
        "x86_64",
        "N04f-absolute-address-in-imm8-field",
        codes::E_FIXUP_003,
    );
}

/// `expected_size` is compared in `check_instructions`, so these two are
/// **static** rejections and must not be counted as post-encode snapshots.
#[test]
fn an_expected_size_mismatch_is_rejected_before_encoding() {
    for name in ["N05-expected-size-mismatch", "N05b-huge-expected-size"] {
        let (plan, definition) = load("x86_64", name);
        let errors = fmp_validate::check(&plan, &definition);
        assert!(
            codes_of(&errors).contains(&codes::E_SIZE_001),
            "{name}: {errors:#?}"
        );
        let materialized = fmp_materialize::materialize(&plan, &definition)
            .expect_err("the fixture is a recorded negative");
        assert!(
            codes_of(&materialized).contains(&codes::E_SIZE_001),
            "{name}: {materialized:#?}"
        );
    }
}
