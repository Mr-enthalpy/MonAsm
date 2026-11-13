//! Command-line front end.
//!
//! ```text
//! fmp materialize <plan.json> --definitions <dir>
//! ```
//!
//! Two behaviours are deliberate:
//!
//! - The definition directory is an explicit option, never an implicit lookup
//!   next to the plan or in the current directory. Where the table came from is
//!   an input; it must not be a hidden one (`INV-05`).
//! - A rejected plan prints the complete diagnostic array to stderr and writes
//!   nothing to stdout, so a caller can never mistake a partial artifact for a
//!   result.
//!
//! Exit codes: `0` artifact emitted, `1` plan or definition rejected (including a
//! post-encode assertion), `2` a host, implementation, usage or I/O fault. An
//! internal invariant break is printed after an `internal fault:` marker on
//! stderr and never shares the rejection code (`ADR-0127` §3.4).

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use fmp_materialize::MaterializationFailure;
use fmp_model::diagnostic::Diagnostic;
use fmp_model::json::{self, Json};
use fmp_model::Registry;

const USAGE: &str = "usage: fmp materialize <plan.json> --definitions <dir>";

fn main() -> ExitCode {
    match run(std::env::args().skip(1).collect()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(failure) => {
            report(&failure);
            ExitCode::from(exit_code(&failure))
        }
    }
}

/// Exit 1 is a rejected plan; exit 2 is the host or the implementation.
///
/// `Internal` must not share the rejection path: `E-INTERNAL-001` means an
/// implementation invariant broke, never that the caller's plan is illegal.
fn exit_code(failure: &Failure) -> u8 {
    match failure {
        Failure::Rejected(_) => 1,
        Failure::Internal(_) | Failure::Host(_) | Failure::Usage(_) | Failure::Io(_) => 2,
    }
}

fn report(failure: &Failure) {
    match failure {
        Failure::Rejected(diagnostics) => print_diagnostics(diagnostics),
        Failure::Internal(diagnostic) => {
            eprintln!("internal fault:");
            print_diagnostics(std::slice::from_ref(diagnostic));
        }
        Failure::Host(message) => eprintln!("fmp: host failure: {message}"),
        Failure::Usage(message) => {
            eprintln!("fmp: {message}");
            eprintln!("{USAGE}");
        }
        Failure::Io(message) => eprintln!("fmp: {message}"),
    }
}

fn print_diagnostics(diagnostics: &[Diagnostic]) {
    let mut out = Vec::with_capacity(diagnostics.len());
    for diagnostic in diagnostics {
        out.push(diagnostic.to_json());
    }
    eprintln!("{}", json::pretty(&Json::Array(out)));
}

enum Failure {
    Rejected(Vec<Diagnostic>),
    Internal(Diagnostic),
    Host(String),
    Usage(String),
    Io(String),
}

/// Map an execution failure to the channel that owns it (`ADR-0127` §3.4).
fn classify(failure: MaterializationFailure) -> Failure {
    match failure {
        MaterializationFailure::PostEncodeAssertion(diagnostics) => Failure::Rejected(diagnostics),
        MaterializationFailure::Internal(diagnostic) => Failure::Internal(diagnostic),
        MaterializationFailure::HostFailure(fault) => Failure::Host(fault.message()),
    }
}

fn run(args: Vec<String>) -> Result<(), Failure> {
    let mut args = args.into_iter();
    let command = args.next().unwrap_or_default();
    if command != "materialize" {
        return Err(Failure::Usage(if command.is_empty() {
            "missing command".to_string()
        } else {
            format!("unknown command `{command}`")
        }));
    }

    let mut plan_path: Option<PathBuf> = None;
    let mut definitions: Option<PathBuf> = None;
    while let Some(argument) = args.next() {
        match argument.as_str() {
            "--definitions" => {
                let value = args
                    .next()
                    .ok_or_else(|| Failure::Usage("--definitions needs a directory".to_string()))?;
                if definitions.replace(PathBuf::from(value)).is_some() {
                    return Err(Failure::Usage(
                        "--definitions given more than once".to_string(),
                    ));
                }
            }
            other if other.starts_with("--") => {
                return Err(Failure::Usage(format!("unknown option `{other}`")));
            }
            other => {
                if plan_path.replace(PathBuf::from(other)).is_some() {
                    return Err(Failure::Usage(
                        "exactly one plan path is allowed".to_string(),
                    ));
                }
            }
        }
    }

    let plan_path = plan_path.ok_or_else(|| Failure::Usage("missing plan path".to_string()))?;
    let definitions =
        definitions.ok_or_else(|| Failure::Usage("missing --definitions <dir>".to_string()))?;

    let registry =
        Registry::load_dir(&definitions).map_err(|error| Failure::Rejected(vec![error]))?;
    let plan_bytes = read(&plan_path)?;
    let plan =
        fmp_model::plan::read(&plan_bytes).map_err(|error| Failure::Rejected(vec![error]))?;
    let definition = registry
        .find(&plan.definition.namespace, &plan.definition.version)
        .map_err(|error| Failure::Rejected(vec![error]))?;
    let validated = fmp_validate::bind(plan, definition).map_err(Failure::Rejected)?;
    let materialization = fmp_materialize::materialize(&validated).map_err(classify)?;
    println!("{}", json::pretty(&materialization.artifact.to_json()));
    Ok(())
}

fn read(path: &Path) -> Result<Vec<u8>, Failure> {
    std::fs::read(path).map_err(|error| Failure::Io(format!("{}: {error}", path.display())))
}

#[cfg(test)]
mod tests {
    use super::*;
    use fmp_model::codes;

    #[test]
    fn the_exit_code_separates_rejection_from_internal_fault() {
        assert_eq!(exit_code(&Failure::Rejected(Vec::new())), 1);
        assert_eq!(
            exit_code(&Failure::Internal(Diagnostic::new(
                codes::E_INTERNAL_001,
                ""
            ))),
            2,
            "an implementation fault is not a rejected plan"
        );
        assert_eq!(exit_code(&Failure::Host("no memory".to_string())), 2);
        assert_eq!(exit_code(&Failure::Usage("bad".to_string())), 2);
        assert_eq!(exit_code(&Failure::Io("missing".to_string())), 2);
    }

    #[test]
    fn a_post_encode_assertion_stays_on_the_plan_channel() {
        let rejected = classify(MaterializationFailure::PostEncodeAssertion(Vec::new()));
        assert_eq!(exit_code(&rejected), 1);
        let internal = classify(MaterializationFailure::Internal(Diagnostic::new(
            codes::E_INTERNAL_001,
            "",
        )));
        assert_eq!(exit_code(&internal), 2);
    }
}
