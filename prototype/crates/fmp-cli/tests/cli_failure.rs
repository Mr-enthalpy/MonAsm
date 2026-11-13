//! End-to-end exit channels (`ADR-0127` §3.4).
//!
//! `exit_code` is unit-tested inside `main.rs`; these two tests prove the real
//! process uses it. A `bind` rejection prints the complete diagnostic array on
//! stderr, writes nothing to stdout and exits 1. A usage fault never prints a
//! diagnostic array and exits 2.
//!
//! An actual `Internal` fault is deliberately **not** injected here: forcing one
//! would mean corrupting a validated plan or adding a test-only switch, and the
//! plan says the pure function plus the classification unit test is the coverage
//! for that branch. Host faults depend on this host's memory and are likewise not
//! a corpus property.

use std::path::PathBuf;
use std::process::Command;

use fmp_model::codes;
use fmp_model::json::{self, Json};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn fmp() -> &'static str {
    env!("CARGO_BIN_EXE_fmp")
}

/// A definition digest mismatch is a `bind` rejection: exit 1, complete
/// diagnostic array on stderr, empty stdout.
#[test]
fn a_binding_rejection_exits_one_with_the_diagnostic_array() {
    let plan = root().join("fixtures/x86_64/negative/N10-definition-digest-mismatch.fmp.json");
    let output = Command::new(fmp())
        .arg("materialize")
        .arg(&plan)
        .arg("--definitions")
        .arg(root().join("definitions"))
        .output()
        .expect("the CLI must start");

    assert_eq!(
        output.status.code(),
        Some(1),
        "a rejected plan is not a host/usage fault: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        output.stdout.is_empty(),
        "a rejected plan must not emit a partial artifact: {}",
        String::from_utf8_lossy(&output.stdout)
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    let Json::Array(diagnostics) = json::parse(stderr.as_bytes())
        .unwrap_or_else(|error| panic!("stderr is not JSON: {error:?}; got {stderr}"))
    else {
        panic!("the diagnostic channel is a JSON array, got {stderr}");
    };
    assert_eq!(diagnostics.len(), 1, "{stderr}");
    let Json::Object(fields) = &diagnostics[0] else {
        panic!("a diagnostic is an object: {stderr}");
    };
    let field = |name: &str| {
        fields
            .iter()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value)
    };
    assert_eq!(field("code").and_then(Json::as_str), Some(codes::E_DEF_001));
    assert_eq!(
        field("path").and_then(Json::as_str),
        Some("/definition_identity/digest")
    );
}

/// Calling the CLI without a command is a usage fault: exit 2, a prose channel,
/// and no JSON diagnostic array.
#[test]
fn a_usage_fault_exits_two_without_a_diagnostic_array() {
    let output = Command::new(fmp()).output().expect("the CLI must start");

    assert_eq!(
        output.status.code(),
        Some(2),
        "usage is not a plan rejection: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.is_empty());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("usage: fmp materialize"),
        "the usage text is on stderr: {stderr}"
    );
    assert!(
        json::parse(stderr.as_bytes()).is_err(),
        "a usage fault is not a diagnostic array: {stderr}"
    );
}
