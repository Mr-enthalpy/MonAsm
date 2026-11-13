//! Determinism experiments `EXP-R1`, `EXP-R2`, `EXP-R3`, `EXP-R4`, `EXP-R5`
//! and `EXP-R6` (`06_validation_matrix.md` §2).
//!
//! `EXP-R3` is the cross-host half: the test below pins the canonical artifact
//! digest of one plan per ISA to the value recorded on the primary Windows
//! host. The same constants must hold on every host, which is what
//! `.github/workflows/determinism.yml` checks on Linux and macOS; the evidence
//! record names the run instead of turning "same host" into "cross-platform".
//!
//! The comparisons are on the artifact's canonical JSON, not on a formatted
//! printout, so a change in diagnostic prose cannot mask a byte difference and a
//! change in key order cannot invent one.

use std::path::{Path, PathBuf};
use std::process::Command;

use fmp_model::canonical;
use fmp_model::json::{self, Json};
use fmp_model::plan::Plan;
use fmp_model::Registry;

mod support;

const REPEATS: usize = 100;
const PROCESS_REPEATS: usize = 4;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn registry() -> Registry {
    Registry::load_dir(&root().join("definitions")).expect("definitions/ must load")
}

fn read_plan(path: &Path) -> Plan {
    let bytes = std::fs::read(path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    fmp_model::plan::read(&bytes)
        .unwrap_or_else(|error| panic!("{}: {}", path.display(), error.message()))
}

fn fixture_files(kind: &str) -> Vec<PathBuf> {
    let fixtures = root().join("fixtures");
    let mut paths = Vec::new();
    for isa in std::fs::read_dir(&fixtures).expect("fixtures/ must exist") {
        let isa = isa.expect("readable entry").path();
        let dir = isa.join(kind);
        if !dir.is_dir() {
            continue;
        }
        for entry in std::fs::read_dir(&dir).expect("readable fixture directory") {
            let path = entry.expect("readable entry").path();
            if path
                .file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.ends_with(".fmp.json"))
            {
                paths.push(path);
            }
        }
    }
    paths.sort();
    paths
}

fn artifact_identity(artifact: &fmp_materialize::Artifact) -> Vec<u8> {
    canonical::canonical_bytes(&artifact.to_json())
}

/// Materialize one fixture and return either the canonical artifact or the
/// sorted diagnostic identities. This is the unit all five experiments compare.
fn outcome(path: &Path, registry: &Registry) -> Result<Vec<u8>, Vec<String>> {
    let plan = read_plan(path);
    let definition = registry
        .find(&plan.definition.namespace, &plan.definition.version)
        .unwrap_or_else(|error| panic!("{}: {}", path.display(), error.message()));
    match support::execute(plan, definition) {
        Ok(artifact) => Ok(artifact_identity(&artifact)),
        Err(errors) => Err(errors.iter().map(|error| error.identity()).collect()),
    }
}

fn example(kind: &str, isa: &str, stem: &str) -> PathBuf {
    root().join("fixtures").join(isa).join(kind).join(stem)
}

/// `EXP-R1`: the same plan materialized repeatedly in one process yields one
/// canonical artifact.
#[test]
fn exp_r1_repeated_execution_is_identical() {
    let registry = registry();
    for path in fixture_files("positive") {
        let first = outcome(&path, &registry).expect("positive fixture must materialize");
        for run in 1..REPEATS {
            let again = outcome(&path, &registry).expect("positive fixture must materialize");
            assert_eq!(
                first,
                again,
                "{}: run {run} differs from run 0",
                path.display()
            );
        }
    }
}

/// `EXP-R2`: independent CLI processes produce the same artifact as the
/// in-process call, byte for byte.
#[test]
fn exp_r2_cross_process_agrees_with_in_process() {
    let registry = registry();
    let plans = [
        example("positive", "x86_64", "X86-P9-sse-vex-evex.fmp.json"),
        example("positive", "aarch64", "A64-P14-cmp-cmn-family.fmp.json"),
        example("positive", "rv64", "RV-P8-pcrel-pair.fmp.json"),
    ];
    let definitions = root().join("definitions");
    let fmp = env!("CARGO_BIN_EXE_fmp");

    for plan_path in plans {
        let direct = outcome(&plan_path, &registry).expect("positive fixture must materialize");
        let mut outputs: Vec<Vec<u8>> = Vec::new();
        for _ in 0..PROCESS_REPEATS {
            let output = Command::new(fmp)
                .arg("materialize")
                .arg(&plan_path)
                .arg("--definitions")
                .arg(&definitions)
                .output()
                .expect("the CLI must start");
            assert!(
                output.status.success(),
                "{}: CLI exited with {:?}: {}",
                plan_path.display(),
                output.status.code(),
                String::from_utf8_lossy(&output.stderr)
            );
            let artifact = json::parse(&output.stdout).expect("CLI stdout must be JSON");
            outputs.push(canonical::canonical_bytes(&artifact));
        }
        for (run, artifact) in outputs.iter().enumerate() {
            assert_eq!(
                &direct,
                artifact,
                "{}: process {run} differs from the in-process artifact",
                plan_path.display()
            );
        }
    }
}

/// `EXP-R3`: one fixed plan per ISA has the same canonical artifact digest on
/// every host. The constants are the values recorded on the primary Windows
/// host (`EXP-0033` §6); a second host must reproduce them exactly.
#[test]
fn exp_r3_artifact_digests_match_the_recorded_values() {
    let registry = registry();
    let cases = [
        (
            "x86_64",
            "X86-P9-sse-vex-evex.fmp.json",
            "sha256:da97dcaad805b973984a92d2ffb933a82a407b1a4cc9a1aa87bfc8a9c715c660",
        ),
        (
            "aarch64",
            "A64-P14-cmp-cmn-family.fmp.json",
            "sha256:638e769fb8fe17ab3ed6d2259d1eab3f503ca9b25ca2133745076e7f64bf5a65",
        ),
        (
            "rv64",
            "RV-P8-pcrel-pair.fmp.json",
            "sha256:19bae975204dbe62ff46cf11a2fd70114356ff9656687c8fefc1aa459d032f7c",
        ),
    ];

    let mut mismatches = Vec::new();
    for (isa, fixture, expected) in cases {
        let path = example("positive", isa, fixture);
        let bytes = outcome(&path, &registry).expect("positive fixture must materialize");
        let document = json::parse(&bytes).expect("canonical artifact is JSON");
        let digest = canonical::canonical_digest(&document);
        if digest != expected {
            mismatches.push(format!("{isa}/{fixture}: {digest}"));
        }
    }
    assert!(
        mismatches.is_empty(),
        "artifact digests differ from the recorded values:\n{}",
        mismatches.join("\n")
    );
}

/// `EXP-R4`: serializing and re-reading the plan does not change the artifact,
/// whether the serialization is canonical or pretty.
#[test]
fn exp_r4_serialization_round_trip_is_identical() {
    let registry = registry();
    for path in fixture_files("positive") {
        let direct = outcome(&path, &registry).expect("positive fixture must materialize");
        let bytes = std::fs::read(&path).expect("fixture is readable");
        let document = json::parse(&bytes).expect("fixture is JSON");

        let canonical_bytes = canonical::canonical_bytes(&document);
        let canonical_document = json::parse(&canonical_bytes).expect("canonical bytes are JSON");
        let canonical_plan = fmp_model::plan::read(&canonical_bytes).expect("canonical plan reads");
        let definition = registry
            .find(
                &canonical_plan.definition.namespace,
                &canonical_plan.definition.version,
            )
            .expect("definition is present");
        let canonical_artifact = support::artifact(canonical_plan, definition);
        assert_eq!(
            direct,
            artifact_identity(&canonical_artifact),
            "{}: canonical round trip changed the artifact",
            path.display()
        );
        assert_eq!(
            canonical::canonical_digest(&document),
            canonical::canonical_digest(&canonical_document),
            "{}: canonical round trip changed the document",
            path.display()
        );

        let pretty = json::pretty(&document);
        let pretty_plan = fmp_model::plan::read(pretty.as_bytes()).expect("pretty plan reads");
        let definition = registry
            .find(
                &pretty_plan.definition.namespace,
                &pretty_plan.definition.version,
            )
            .expect("definition is present");
        let pretty_artifact = support::artifact(pretty_plan, definition);
        assert_eq!(
            direct,
            artifact_identity(&pretty_artifact),
            "{}: pretty round trip changed the artifact",
            path.display()
        );
    }
}

/// `EXP-R5`: a definition whose rules changed under the same identity stops the
/// plan at `E-DEF-001`; a definition whose version moved stops it at `E-DEF-002`.
/// Neither case may emit bytes.
#[test]
fn exp_r5_definition_perturbation_is_loud() {
    let plan_path = example("positive", "x86_64", "X86-P9-sse-vex-evex.fmp.json");
    let plan = read_plan(&plan_path);

    let digest_dir = fresh_dir("exp-r5-digest");
    copy_tree(&root().join("definitions"), &digest_dir);
    let table = digest_dir.join("x86_64").join("0.5.0.json");
    mutate(&table, |document| {
        let template = form_field(document);
        let Json::Str(hex) = template else {
            panic!("template is a string");
        };
        let last = hex.pop().expect("a template has at least one digit");
        let replacement = if last == '0' { '1' } else { '0' };
        hex.push(replacement);
    });
    let perturbed = Registry::load_dir(&digest_dir).expect("the perturbed table still loads");
    let definition = perturbed
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the version is unchanged");
    let errors = support::diagnostics(plan.clone(), definition);
    let expected = fmp_model::codes::E_DEF_001;
    assert_eq!(
        errors.iter().map(|error| error.code()).collect::<Vec<_>>(),
        vec![expected],
        "EXP-R5: a rule change must surface as {expected}, found {:?}",
        errors
            .iter()
            .map(|error| error.message())
            .collect::<Vec<_>>()
    );
    assert_eq!(errors[0].path(), "/definition_identity/digest");
    std::fs::remove_dir_all(&digest_dir).expect("temporary copy is removable");

    let version_dir = fresh_dir("exp-r5-version");
    copy_tree(&root().join("definitions"), &version_dir);
    let table = version_dir.join("x86_64").join("0.5.0.json");
    mutate(&table, |document| {
        *form_field_at(document, &["version"]) = Json::Str("0.5.0-perturbed".to_string());
    });
    let renamed = Registry::load_dir(&version_dir).expect("the renamed table still loads");
    let error = renamed
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect_err("a renamed version must not resolve");
    assert_eq!(error.code(), fmp_model::codes::E_DEF_002);
    assert_eq!(error.path(), "/definition_identity");
    std::fs::remove_dir_all(&version_dir).expect("temporary copy is removable");
}

/// `EXP-R6`: repeating an invalid plan yields the same diagnostic identity
/// `(code, path, sorted detail keys)`. The free-text message is deliberately not
/// part of the comparison.
#[test]
fn exp_r6_negative_identity_is_stable() {
    let registry = registry();
    let negatives: Vec<(PathBuf, String)> = fixture_files("negative")
        .into_iter()
        .map(|path| {
            let expected_path = path.with_file_name(
                path.file_name()
                    .and_then(|name| name.to_str())
                    .expect("fixture file name")
                    .trim_end_matches(".fmp.json")
                    .to_string()
                    + ".expected-error.json",
            );
            let bytes = std::fs::read(&expected_path).expect("expected-error.json is readable");
            let document = json::parse(&bytes).expect("expected-error.json is JSON");
            let phase = document
                .get("phase")
                .and_then(Json::as_str)
                .unwrap_or("materialize")
                .to_string();
            (path, phase)
        })
        .collect();

    for (path, phase) in negatives {
        let first = repeated_outcome(&path, &phase, &registry);
        for run in 1..REPEATS {
            let again = repeated_outcome(&path, &phase, &registry);
            assert_eq!(
                first,
                again,
                "{}: run {run} has a different diagnostic identity",
                path.display()
            );
        }
    }
}

fn repeated_outcome(path: &Path, phase: &str, registry: &Registry) -> Result<Vec<u8>, Vec<String>> {
    if phase == "read" {
        let bytes = std::fs::read(path).expect("fixture is readable");
        match fmp_model::plan::read(&bytes) {
            Ok(_) => panic!("{} was read and should have been rejected", path.display()),
            Err(error) => Err(vec![error.identity()]),
        }
    } else {
        outcome(path, registry)
    }
}

fn fresh_dir(name: &str) -> PathBuf {
    let dir = root().join("prototype").join("target").join(name);
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).expect("temporary directory is creatable");
    dir
}

fn copy_tree(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).expect("destination is creatable");
    for entry in std::fs::read_dir(from).expect("source is readable") {
        let entry = entry.expect("readable entry");
        let target = to.join(entry.file_name());
        if entry.path().is_dir() {
            copy_tree(&entry.path(), &target);
        } else {
            std::fs::copy(entry.path(), target).expect("file is copyable");
        }
    }
}

fn mutate(path: &Path, edit: impl FnOnce(&mut Json)) {
    let bytes = std::fs::read(path).expect("definition is readable");
    let mut document = json::parse(&bytes).expect("definition is JSON");
    edit(&mut document);
    std::fs::write(path, json::pretty(&document)).expect("definition is writable");
}

/// The first `template` of the first form, as a mutable reference.
fn form_field(document: &mut Json) -> &mut Json {
    form_field_at(document, &["forms", "0", "template"])
}

/// Resolve `keys` through objects and array indices. `"0"` names the first item.
fn form_field_at<'a>(document: &'a mut Json, keys: &[&str]) -> &'a mut Json {
    let mut current = document;
    for key in keys {
        current = match current {
            Json::Object(entries) => entries
                .iter_mut()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value)
                .unwrap_or_else(|| panic!("missing object key {key}")),
            Json::Array(items) => items
                .get_mut(key.parse::<usize>().expect("array index"))
                .unwrap_or_else(|| panic!("missing array index {key}")),
            other => panic!("cannot descend into {}", other.kind()),
        };
    }
    current
}
