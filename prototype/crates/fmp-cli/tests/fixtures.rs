//! Fixture gate: positives must reproduce oracle bytes, negatives must produce
//! exactly the registered diagnostics.
//!
//! The expected bytes in `*.expected.bin` come from a tool other than this
//! materializer (`fixtures/README.md`), so a passing test is two independent
//! implementations agreeing. A negative fixture states the complete diagnostic
//! set — code, JSON Pointer and detail keys — and the test requires equality, not
//! "contains", so an unexpected extra error fails the fixture instead of being
//! tolerated.

use std::path::{Path, PathBuf};

use fmp_model::json::Json;
use fmp_model::Registry;

mod support;

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

fn positives() -> Vec<PathBuf> {
    fixture_files("positive", ".fmp.json")
}

fn negatives() -> Vec<PathBuf> {
    fixture_files("negative", ".fmp.json")
}

fn fixture_files(kind: &str, suffix: &str) -> Vec<PathBuf> {
    // Every ISA directory is scanned, not a hard-coded one: a new table's
    // fixtures are gated the moment they land, and an ISA directory without a
    // fixture set is skipped rather than failing the whole gate.
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
    assert!(
        !paths.is_empty(),
        "no fixtures under {}",
        fixtures.display()
    );
    paths
}

fn stem(path: &Path) -> String {
    path.file_name()
        .and_then(|name| name.to_str())
        .expect("fixture file name")
        .trim_end_matches(".fmp.json")
        .to_string()
}

#[test]
fn positives_reproduce_the_oracle_bytes() {
    let registry = registry();
    for path in positives() {
        let name = stem(&path);
        let dir = path.parent().expect("fixture directory");
        let plan = read_plan(&path);
        let definition = registry
            .find(&plan.definition.namespace, &plan.definition.version)
            .unwrap_or_else(|error| panic!("{name}: {}", error.message()));
        let artifact = match support::execute(plan.clone(), definition) {
            Ok(artifact) => artifact,
            Err(errors) => panic!(
                "{name} was rejected:\n{}",
                errors
                    .iter()
                    .map(|error| error.message())
                    .collect::<Vec<_>>()
                    .join("\n")
            ),
        };

        let expected_path = case_file(dir, &name, "expected.bin");
        let expected = std::fs::read(&expected_path)
            .unwrap_or_else(|error| panic!("{}: {error}", expected_path.display()));
        assert_eq!(
            artifact.bytes_hex(),
            hex(&expected),
            "{name}: emitted bytes differ from the oracle's"
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
            "{name}: record count differs from the oracle record"
        );

        // A Level 1 fixture states the complete envelope, not only the bytes:
        // section split, symbol table and the unchanged fixup records. The file
        // is authored from the plan and `*.expected.bin`; comparing the parsed
        // values also pins the documented field order (`Json` objects are
        // ordered).
        let artifact_path = case_file(dir, &name, "expected-artifact.json");
        if artifact_path.is_file() {
            let expected = std::fs::read(&artifact_path)
                .unwrap_or_else(|error| panic!("{}: {error}", artifact_path.display()));
            let expected = fmp_model::json::parse(&expected)
                .unwrap_or_else(|error| panic!("{}: {}", artifact_path.display(), error.reason()));
            assert_eq!(
                artifact.to_json(),
                expected,
                "{name}: artifact envelope differs from the recorded Level 1 shape"
            );
        }

        // Every positive fixture that carries a digest must name its source
        // (contract §7), and the materializer must have accepted it.
        if plan
            .instructions
            .iter()
            .any(|instruction| instruction.expected_digest.is_some())
        {
            assert!(
                plan.provenance
                    .as_ref()
                    .and_then(|provenance| provenance.generated_by.as_ref())
                    .is_some(),
                "{name}: a digest without a generated_by would be rejected"
            );
        }
    }
}

#[test]
fn negatives_produce_exactly_the_registered_diagnostics() {
    let registry = registry();
    for path in negatives() {
        let name = stem(&path);
        let dir = path.parent().expect("fixture directory");
        let expected_path = case_file(dir, &name, "expected-error.json");
        let expected = std::fs::read(&expected_path)
            .unwrap_or_else(|error| panic!("{}: {error}", expected_path.display()));
        let expected = fmp_model::json::parse(&expected).expect("expected-error.json must parse");

        // A negative fixture is either a plan the reader must reject (a schema
        // shape that is not in `fmp/0.1`) or a plan the materializer must
        // reject. `phase` says which, because the reader returns one diagnostic
        // and there is no definition to look up when the plan does not parse.
        let phase = expected
            .get("phase")
            .and_then(Json::as_str)
            .unwrap_or("materialize");
        if phase != "read" && phase != "materialize" {
            panic!("{name}: unknown `phase` {phase:?}");
        }

        let errors = if phase == "read" {
            let bytes =
                std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
            match fmp_model::plan::read(&bytes) {
                Ok(_) => panic!("{name} was read and should have been rejected"),
                Err(error) => vec![error],
            }
        } else {
            let plan = read_plan(&path);
            let definition = registry
                .find(&plan.definition.namespace, &plan.definition.version)
                .unwrap_or_else(|error| panic!("{name}: {}", error.message()));
            support::diagnostics(plan, definition)
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
            "{name}: diagnostics differ\nfound:\n{}\nexpected:\n{}",
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
}
