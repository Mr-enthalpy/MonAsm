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
//! Exit codes: `0` artifact emitted, `1` plan rejected, `2` usage or I/O fault.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use fmp_model::diagnostic::Diagnostic;
use fmp_model::json;
use fmp_model::Registry;

const USAGE: &str = "usage: fmp materialize <plan.json> --definitions <dir>";

fn main() -> ExitCode {
    match run(std::env::args().skip(1).collect()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(Failure::Rejected(diagnostics)) => {
            let mut out = Vec::with_capacity(diagnostics.len());
            for diagnostic in &diagnostics {
                out.push(diagnostic.to_json());
            }
            eprintln!("{}", json::pretty(&json::Json::Array(out)));
            ExitCode::from(1)
        }
        Err(Failure::Usage(message)) => {
            eprintln!("fmp: {message}");
            eprintln!("{USAGE}");
            ExitCode::from(2)
        }
        Err(Failure::Io(message)) => {
            eprintln!("fmp: {message}");
            ExitCode::from(2)
        }
    }
}

enum Failure {
    Rejected(Vec<Diagnostic>),
    Usage(String),
    Io(String),
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
    let artifact = fmp_materialize::materialize(&plan, &definition).map_err(Failure::Rejected)?;
    println!("{}", json::pretty(&artifact.to_json()));
    Ok(())
}

fn read(path: &Path) -> Result<Vec<u8>, Failure> {
    std::fs::read(path).map_err(|error| Failure::Io(format!("{}: {error}", path.display())))
}
