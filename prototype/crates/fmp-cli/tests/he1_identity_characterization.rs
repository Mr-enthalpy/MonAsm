//! H0 characterization tests: the gaps HE-1 had to close, measured rather than
//! asserted from source reading.
//!
//! This file is evidence, not a description of the current code. H1a/H1b changed
//! two of the original four gap tests; the rest stay as the boundary H1 did
//! **not** change:
//!
//! - the definition-mutation test became `a_definition_edit_reloads_to_a_new_digest`,
//!   which edits the document, reloads it and asserts the untouched plan is
//!   rejected (`H1a`);
//! - `a_parsed_operand_can_change_under_a_stable_fingerprint` is kept as the
//!   **legacy** half of a pair. The fingerprint still does not move; the H1b
//!   half in `fmp-materialize/tests/he1_execution.rs` asserts that
//!   `ParsedPlanIdentity` and `ExecutionReceipt` do;
//! - the unselected-file and synthetic-namespace tests still document loader
//!   behaviour that the package round (H2) owns, not H1.
//!
//! One test remains a **constraint**: the legacy fingerprint hashes the raw
//! document, so it sees fields the parser drops. Two are controls — a plan naming
//! another definition's digest, and a plan whose top level is not an object — and
//! assert the rejection that already happens. They exist so that:
//!
//! - H0 can report "reproduced" for the audit risks instead of "inferred"; and
//! - later rounds can flip each gap test into a rejection or identity test, at
//!   which point the test name and body change and this file shrinks.
//!
//! Do not read a green run here as a property of the system. For the remaining
//! gap tests the property is the opposite of what they assert. The constraint
//! test asserts a property H1 must **preserve**, and the two controls assert
//! rejections H1 must keep. The deep-JSON finding is **not** in this file: it is
//! the `deep-json` probe in `tools/he1_baseline.py`, because the crash is inside
//! the parser and cannot be observed safely in-process.

use std::path::PathBuf;
use std::sync::Arc;

use fmp_model::codes;
use fmp_model::plan::Payload;
use fmp_model::Registry;

mod support;

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

/// `HE-T03`: the digest is a function of the definition **document**, and a
/// reload after an edit produces a different digest. This replaces the H0
/// characterization that wrote `definition.forms[0].template` in memory: H1a
/// closes the fields (`compile_fail` doctest in `fmp-model`), so the same
/// property is measured the only way a caller can still express it — by editing
/// the bytes and loading them again.
///
/// The second half is the consequence: the untouched plan still names the old
/// digest, so the reloaded definition is rejected by the digest comparison that
/// runs before any rule.
#[test]
fn a_definition_edit_reloads_to_a_new_digest() {
    let bytes = definition_bytes("x86_64", "0.1.0");
    let original = fmp_model::definition::read(&bytes).expect("the shipped table loads");
    let plan = positive("X86-P1-mov-r64-both-directions");

    // A one-byte edit inside a template: same shape, same forms, different
    // content. `"4889c0"` is the legacy `mov r/m64, r64` template.
    let text = String::from_utf8(bytes).expect("definitions are UTF-8");
    assert!(
        text.contains("4889c0"),
        "the fixture's template is the one this test edits"
    );
    let edited = text.replacen("4889c0", "4889c1", 1);
    let reloaded =
        fmp_model::definition::read(edited.as_bytes()).expect("the edited table still loads");

    assert_ne!(
        original.digest(),
        reloaded.digest(),
        "the digest covers the document content"
    );

    let errors = support::diagnostics(plan.clone(), Arc::new(reloaded));
    assert!(
        errors.iter().any(|error| error.code() == codes::E_DEF_001
            && error.path() == "/definition_identity/digest"),
        "{errors:?}"
    );
    support::artifact(plan, Arc::new(original));
}

/// `HE-T04`: the fingerprint is built from the parsed plan *document*, so a
/// change to the parsed operands — the facts emission actually reads — leaves
/// both the fingerprint and the definition identity unchanged.
#[test]
fn a_parsed_operand_can_change_under_a_stable_fingerprint() {
    let definition = Arc::new(
        fmp_model::definition::read(&definition_bytes("x86_64", "0.1.0"))
            .expect("the shipped table loads"),
    );
    let mut plan = positive("X86-P1-mov-r64-both-directions");
    let fingerprint = fmp_materialize::fingerprint(&plan, &definition);
    let before = support::artifact(plan.clone(), Arc::clone(&definition)).bytes;

    match &mut plan.instructions[0].operands[1].payload {
        Payload::Register(reg) => *reg = 1,
        other => panic!("X86-P1's second operand is a register, found {other:?}"),
    }

    assert_eq!(
        fmp_materialize::fingerprint(&plan, &definition),
        fingerprint,
        "the fingerprint covers `plan.document`, not the parsed operands"
    );
    let after = support::artifact(plan, Arc::clone(&definition)).bytes;
    assert_ne!(before, after, "the executed facts changed");
}

/// Constraint, not a gap: the legacy fingerprint hashes the **raw document**, and
/// the parser deliberately drops fields that document allows — `source_trace` on
/// an instruction (`plan.rs:604-651`), `type`/`size` on a symbol
/// (`plan.rs:545-602`). So two plans can share every parsed field and still have
/// different fingerprints. H1 cannot delete `Plan.document` while promising
/// `fingerprint()` stays byte-identical; it has to keep the raw document as a
/// read-only, legacy-only input.
#[test]
fn a_legacy_fingerprint_covers_document_fields_the_parser_drops() {
    let definition = fmp_model::definition::read(&definition_bytes("x86_64", "0.1.0"))
        .expect("the shipped table loads");
    let path = root().join("fixtures/x86_64/positive/X86-P1-mov-r64-both-directions.fmp.json");
    let bytes = std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    let plain = fmp_model::plan::read(&bytes).expect("the fixture parses");

    // Add a field the reader accepts and does not retain, straight into the raw
    // document, so the parsed DTO is the only thing the two plans share.
    let mut document = fmp_model::json::parse(&bytes).expect("the fixture parses as JSON");
    let fmp_model::json::Json::Object(root) = &mut document else {
        panic!("a plan is an object");
    };
    let instructions = root
        .iter_mut()
        .find(|(key, _)| key == "instructions")
        .map(|(_, value)| value)
        .expect("the fixture has instructions");
    let fmp_model::json::Json::Array(items) = instructions else {
        panic!("instructions is an array");
    };
    let fmp_model::json::Json::Object(first) = &mut items[0] else {
        panic!("an instruction is an object");
    };
    first.push((
        "source_trace".to_string(),
        fmp_model::json::Json::Object(vec![
            (
                "file".to_string(),
                fmp_model::json::Json::Str("planner.fmp".to_string()),
            ),
            ("line".to_string(), fmp_model::json::Json::Int(12)),
            ("node".to_string(), fmp_model::json::Json::Int(7)),
        ]),
    ));
    let traced = fmp_model::plan::bind(&document).expect("source_trace is accepted");

    assert_eq!(
        format!("{:?}", plain.instructions),
        format!("{:?}", traced.instructions),
        "the parsed instruction has no field for source_trace"
    );
    assert_ne!(
        fmp_materialize::fingerprint(&plain, &definition),
        fmp_materialize::fingerprint(&traced, &definition),
        "the fingerprint hashes the raw document, so it sees source_trace"
    );
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
    let errors = support::diagnostics(plan, Arc::new(other));
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
