//! H1a (`ADR-0127`, §4.3) and H1b: measure where the post-encode negatives
//! actually fail, instead of reading the answer off function names.
//!
//! `fmp_validate::bind` runs `check_structure`, the definition identity
//! comparison and `check`; the materializer then encodes. H1b replays the same
//! fixtures through `bind`, so a failure that appears here is classified as
//! `MaterializationFailure::PostEncodeAssertion`, not as a static rejection.
//! `a_digest_mismatch_is_post_encode` and friends are the four fixtures whose
//! value-level detail snapshots `ADR-0127` §9 adds; the other 615 negatives keep
//! the code + Pointer + detail-key-set gate.

use std::path::PathBuf;
use std::sync::Arc;

use fmp_materialize::MaterializationFailure;
use fmp_model::codes;
use fmp_model::definition::Definition;
use fmp_model::plan::Plan;
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
    let plan = fmp_model::plan::read(&bytes)
        .unwrap_or_else(|error| panic!("{}: {}", path.display(), error.message()));
    let definition = registry()
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the fixture's definition exists");
    (plan, definition)
}

fn codes_of(errors: &[fmp_model::Diagnostic]) -> Vec<&'static str> {
    errors.iter().map(|error| error.code()).collect()
}

fn post_encode(isa: &str, name: &str) -> Vec<fmp_model::Diagnostic> {
    let (plan, definition) = load(isa, name);
    let static_errors = fmp_validate::check(&plan, &definition);
    assert!(
        static_errors.is_empty(),
        "{name} is already rejected by `check`, so it is not post-encode: {static_errors:#?}"
    );

    let validated =
        fmp_validate::bind(plan, definition).expect("bind accepts a post-encode negative");
    match fmp_materialize::materialize(&validated) {
        Err(MaterializationFailure::PostEncodeAssertion(errors)) => errors,
        other => panic!("{name} did not fail as a post-encode assertion: {other:?}"),
    }
}

fn rendered(error: &fmp_model::Diagnostic, key: &str) -> String {
    error
        .details()
        .get(key)
        .unwrap_or_else(|| panic!("{} has no `{key}`: {error:?}", error.code()))
        .render()
}

/// `expected_digest` is a check on the encoded bytes, so only encoding can see
/// it. The value snapshot pins what the assertion actually compared.
#[test]
fn a_digest_mismatch_is_post_encode() {
    let errors = post_encode("x86_64", "N13-expected-digest-mismatch");
    assert_eq!(codes_of(&errors), vec![codes::E_BYTE_001]);
    assert_eq!(
        rendered(&errors[0], "declared"),
        "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    );
    assert_eq!(
        rendered(&errors[0], "actual"),
        "sha256:d17f36bd44115fe593938b561817d7d2e86f7dfeecedf40827be4b9012a310a7"
    );
}

/// Pre-transform alignment is an `apply` rule, not a static one.
#[test]
fn a_fixup_alignment_failure_is_post_encode() {
    let errors = post_encode("aarch64", "N20-loadlit-fixup-misaligned");
    assert_eq!(codes_of(&errors), vec![codes::E_RANGE_003]);
    assert_eq!(rendered(&errors[0], "required_align"), "2");
    assert_eq!(rendered(&errors[0], "value"), "2");
}

/// Post-transform range is an `apply` rule.
#[test]
fn a_fixup_range_failure_is_post_encode() {
    for (isa, name, min, max, value) in [
        (
            "x86_64",
            "N04b-rel32-absolute-out-of-range",
            "-2147483648",
            "2147483647",
            "4294963195",
        ),
        (
            "x86_64",
            "N04f-absolute-address-in-imm8-field",
            "-128",
            "127",
            "4096",
        ),
    ] {
        let errors = post_encode(isa, name);
        assert_eq!(codes_of(&errors), vec![codes::E_FIXUP_003], "{name}");
        assert_eq!(rendered(&errors[0], "min"), min, "{name}");
        assert_eq!(rendered(&errors[0], "max"), max, "{name}");
        assert_eq!(rendered(&errors[0], "value"), value, "{name}");
    }
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
        let bound = fmp_validate::bind(plan, definition)
            .expect_err("the fixture is a recorded static negative");
        assert!(
            codes_of(&bound).contains(&codes::E_SIZE_001),
            "{name}: {bound:#?}"
        );
    }
}
