//! H0 characterization tests: the gaps HE-1 has to close, measured rather than
//! asserted from source reading.
//!
//! Every test in this file **passes on the current code by documenting a hole**,
//! not by requiring correct behaviour. They exist so that:
//!
//! - H0 can report "reproduced" for the audit risks instead of "inferred"; and
//! - H1/H3 can flip each one into a rejection test, at which point the test name
//!   and body change and this file shrinks.
//!
//! Do not read a green run here as a property of the system. The property is the
//! opposite of what most of these assert.

use std::path::PathBuf;

use fmp_model::codes;
use fmp_model::plan::Payload;
use fmp_model::Registry;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn definition_bytes(isa: &str, version: &str) -> Vec<u8> {
    let path = root().join(format!("definitions/{isa}/{version}.json"));
    std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()))
}

fn positive(name: &str) -> fmp_model::Plan {
    let path = root().join(format!("fixtures/x86_64/positive/{name}.fmp.json"));
    let bytes = std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    fmp_model::plan::read(&bytes)
        .unwrap_or_else(|error| panic!("{}: {}", path.display(), error.message()))
}

fn expected_bytes(name: &str) -> Vec<u8> {
    let path = root().join(format!("fixtures/x86_64/positive/{name}.expected.bin"));
    std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()))
}

/// `HE-T03`/`HE-T04`: a loaded definition can be re-encoded in memory while the
/// digest string — the value a plan names and the materializer compares — stays
/// untouched. The emitted bytes then come from rules the digest does not cover.
#[test]
fn a_loaded_definition_can_be_re_encoded_under_its_original_digest() {
    let mut definition = fmp_model::definition::read(&definition_bytes("x86_64", "0.1.0"))
        .expect("the shipped table loads");
    let digest = definition.digest.clone();
    for form in &mut definition.forms {
        form.template = vec![0x90; form.template.len()];
    }
    assert_eq!(
        definition.digest, digest,
        "the digest is a stored string, not derived from `forms`"
    );

    let plan = positive("X86-P1-mov-r64-both-directions");
    let fingerprint = fmp_materialize::fingerprint(&plan, &definition);
    let artifact = fmp_materialize::materialize(&plan, &definition)
        .expect("the mutated table still validates: the shape did not change");
    assert_eq!(
        fmp_materialize::fingerprint(&plan, &definition),
        fingerprint,
        "the artifact identity is unchanged"
    );
    let expected = expected_bytes("X86-P1-mov-r64-both-directions");
    assert_eq!(
        artifact.bytes.len(),
        expected.len(),
        "the mutated templates kept their length"
    );
    assert_ne!(
        artifact.bytes,
        expected,
        "emission followed the mutated templates: {}",
        artifact.bytes_hex()
    );
}

/// `HE-T04`: the fingerprint is built from the parsed plan *document*, so a
/// change to the parsed operands — the facts emission actually reads — leaves
/// both the fingerprint and the definition identity unchanged.
#[test]
fn a_parsed_operand_can_change_under_a_stable_fingerprint() {
    let definition = fmp_model::definition::read(&definition_bytes("x86_64", "0.1.0"))
        .expect("the shipped table loads");
    let mut plan = positive("X86-P1-mov-r64-both-directions");
    let fingerprint = fmp_materialize::fingerprint(&plan, &definition);
    let before = fmp_materialize::materialize(&plan, &definition)
        .expect("the fixture materializes")
        .bytes;

    match &mut plan.instructions[0].operands[1].payload {
        Payload::Register(reg) => *reg = 1,
        other => panic!("X86-P1's second operand is a register, found {other:?}"),
    }

    assert_eq!(
        fmp_materialize::fingerprint(&plan, &definition),
        fingerprint,
        "the fingerprint covers `plan.document`, not the parsed operands"
    );
    let after = fmp_materialize::materialize(&plan, &definition)
        .expect("register 1 is legal in this slot")
        .bytes;
    assert_ne!(before, after, "the executed facts changed");
}

/// `HE-T06`: `Registry::load_dir` reads every `*.json` under the directory, so a
/// file no plan selects can still decide whether a plan materializes.
#[test]
fn an_unselected_file_in_the_definition_directory_breaks_loading() {
    let scratch =
        std::env::temp_dir().join(format!("monasm-he1-unselected-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&scratch);
    std::fs::create_dir_all(&scratch).expect("create the scratch directory");
    std::fs::write(
        scratch.join("0.1.0.json"),
        definition_bytes("x86_64", "0.1.0"),
    )
    .expect("copy the table");
    std::fs::write(
        scratch.join("notes.json"),
        br#"{"note":"not a definition"}"#,
    )
    .expect("write the stray file");

    let error =
        Registry::load_dir(&scratch).expect_err("an unrelated file still fails the whole load");
    assert_eq!(error.code(), codes::E_DEF_001);
    let _ = std::fs::remove_dir_all(&scratch);
}

/// `HE-T15`: the loader's form-id check names the three ISAs, so a new target
/// namespace cannot be added without editing the model crate.
#[test]
fn a_synthetic_namespace_is_rejected_by_the_loader() {
    let text = [
        r#"{"definition_format":"fmp-def/0.1","namespace":"monasm.isa.probe","version":"test","#,
        r#""target_identity":{"isa_family":"probe","isa_variant":"probe-1","execution_mode":"64","#,
        r#""enabled_extensions":[],"byte_order":"little","address_width":64},"forms":["#,
        r#"{"form_id":"probe:insn/x","template":"00","slots":[]}"#,
        "]}",
    ]
    .concat();
    let error = fmp_model::definition::read(text.as_bytes())
        .expect_err("the ISA allowlist refuses a new namespace");
    assert_eq!(error.code(), codes::E_DEF_001);
    assert!(
        error.message().contains("unknown ISA family"),
        "{}",
        error.message()
    );
}

/// Control, not a gap: the digest comparison itself exists and fires before any
/// rule is applied. H1 must keep this rejection while making the object that
/// carries the digest immutable.
#[test]
fn a_plan_naming_another_definition_digest_is_rejected() {
    let plan = positive("X86-P1-mov-r64-both-directions");
    let other = fmp_model::definition::read(&definition_bytes("x86_64", "0.2.0"))
        .expect("the shipped table loads");
    let errors =
        fmp_materialize::materialize(&plan, &other).expect_err("the plan names the 0.1.0 digest");
    assert!(
        errors.iter().any(|error| error.code() == codes::E_DEF_001
            && error.path() == "/definition_identity/digest"),
        "{errors:?}"
    );
}

/// `HE-T13`: the recorded deep-input probe (`tools/he1_baseline.py`) shows the
/// `fmp` process exits abnormally on 20 000 nested arrays. This test records the
/// boundary in-process where it can be observed safely: a plan whose top level
/// is not an object is a structured rejection, so the unbounded descent is the
/// parser's, not the plan reader's.
#[test]
fn the_plan_reader_rejects_a_non_object_top_level() {
    let error = fmp_model::plan::read(b"[]").expect_err("a plan is an object");
    assert_eq!(error.code(), codes::E_PLAN_002);
}
