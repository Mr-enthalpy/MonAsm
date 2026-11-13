//! Shared binding helpers for the integration tests.
//!
//! Every test now goes through `bind` before it can reach the encoder; there is
//! no two-argument path left. `execute` keeps the split visible: a `bind`
//! rejection and a post-encode assertion are different stages, but both carry
//! the complete diagnostic set the negative gates compare.

#![allow(dead_code)]

use std::sync::Arc;

use fmp_materialize::{Artifact, MaterializationFailure};
use fmp_model::definition::Definition;
use fmp_model::diagnostic::Diagnostic;
use fmp_model::Plan;

/// Bind and execute, or return every diagnostic the plan produced.
///
/// A host failure is a panic: no corpus fixture depends on this host's memory,
/// and silently turning it into a diagnostic would misstate the classification.
pub fn execute(plan: Plan, definition: Arc<Definition>) -> Result<Artifact, Vec<Diagnostic>> {
    let validated = match fmp_validate::bind(plan, definition) {
        Ok(validated) => validated,
        Err(errors) => return Err(errors),
    };
    match fmp_materialize::materialize(&validated) {
        Ok(materialization) => Ok(materialization.artifact),
        Err(MaterializationFailure::PostEncodeAssertion(errors)) => Err(errors),
        Err(MaterializationFailure::Internal(error)) => Err(vec![error]),
        Err(MaterializationFailure::HostFailure(fault)) => {
            panic!("the host failed to satisfy the plan: {fault:?}")
        }
    }
}

/// The artifact of a plan that must be accepted.
pub fn artifact(plan: Plan, definition: Arc<Definition>) -> Artifact {
    execute(plan, definition)
        .unwrap_or_else(|errors| panic!("the plan binds:\n{}", messages(&errors)))
}

/// The complete diagnostic set of a plan that must be rejected.
pub fn diagnostics(plan: Plan, definition: Arc<Definition>) -> Vec<Diagnostic> {
    execute(plan, definition).expect_err("the plan should have been rejected")
}

pub fn messages(errors: &[Diagnostic]) -> String {
    errors
        .iter()
        .map(|error| error.message())
        .collect::<Vec<_>>()
        .join("\n")
}
