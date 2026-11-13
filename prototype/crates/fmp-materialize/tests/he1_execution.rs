//! H1b (`ADR-0127` D3/D4/D9/D11/D12/D15): one execution credential, one receipt.
//!
//! These tests are the H1b half of the identity table in
//! `docs/architecture/he1-h1-plan.md` §5. Each one pairs a positive property with
//! the concrete distinction it must keep:
//!
//! - `BindIdentity` names the parsed facts and the bound table, **not** the
//!   legacy envelope, so a `source_trace`-only edit binds identically while the
//!   payload digest moves;
//! - a parsed-operand edit changes the plan identity while the legacy
//!   fingerprint stays put, because that fingerprint hashes the raw document;
//! - `payload_digest` is the `payload/0.1` projection, so the envelope version is
//!   outside it and the bytes are inside it;
//! - a failed image reservation is a host limit, never `Internal` and never a
//!   plan rejection (`ADR-0127` §8.3);
//! - the deprecated facade routes through `bind`, so it cannot skip either the
//!   definition identity comparison or the stage classification.
//!
//! Every plan here is a shipped fixture or the same fixture with one field
//! changed in memory; no new fixture or definition is introduced.

#![allow(deprecated)]

use std::path::PathBuf;
use std::sync::Arc;

use fmp_materialize::legacy::{self, LegacyFailure};
use fmp_materialize::{payload_digest, HostFault, ImplementationIdentity, MaterializationFailure};
use fmp_model::codes;
use fmp_model::definition::Definition;
use fmp_model::json::{self, Json};
use fmp_model::plan::{self, Payload, Plan, Provenance};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn definition_bytes(isa: &str, version: &str) -> Vec<u8> {
    let path = root().join(format!("definitions/{isa}/{version}.json"));
    std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()))
}

fn definition(isa: &str, version: &str) -> Arc<Definition> {
    Arc::new(
        fmp_model::definition::read(&definition_bytes(isa, version))
            .expect("the shipped table loads"),
    )
}

fn fixture(isa: &str, phase: &str, name: &str) -> Vec<u8> {
    let path = root().join(format!("fixtures/{isa}/{phase}/{name}.fmp.json"));
    std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()))
}

fn positive(isa: &str, name: &str) -> Plan {
    let bytes = fixture(isa, "positive", name);
    plan::read(&bytes).unwrap_or_else(|error| panic!("{name}: {}", error.message()))
}

fn bind(
    plan: Plan,
    definition: Arc<Definition>,
) -> Result<fmp_validate::ValidatedPlan, Vec<fmp_model::Diagnostic>> {
    fmp_validate::bind(plan, definition)
}

/// The same parsed plan, plus a document field the reader accepts and drops.
///
/// `source_trace` is legal on an instruction and is not retained by the DTO, so
/// the two plans differ only in `legacy_document`. Re-reading the edited document
/// keeps the fixture honest: the parser is the one that accepts `source_trace`,
/// not this test poking at the legacy copy.
fn with_source_trace(bytes: &[u8]) -> Plan {
    let mut document = json::parse(bytes).expect("the fixture parses as JSON");
    let Json::Object(root) = &mut document else {
        panic!("a plan is an object");
    };
    let instructions = root
        .iter_mut()
        .find(|(key, _)| key == "instructions")
        .map(|(_, value)| value)
        .expect("the fixture has instructions");
    let Json::Array(items) = instructions else {
        panic!("instructions is an array");
    };
    let Json::Object(first) = &mut items[0] else {
        panic!("an instruction is an object");
    };
    first.push((
        "source_trace".to_string(),
        Json::Object(vec![
            ("file".to_string(), Json::Str("planner.fmp".to_string())),
            ("line".to_string(), Json::Int(12)),
            ("node".to_string(), Json::Int(7)),
        ]),
    ));
    plan::bind(&document).expect("source_trace is accepted at the instruction level")
}

/// `ParsedPlanIdentity` covers the facts, not the provenance block.
#[test]
fn plan_identity_ignores_provenance() {
    let plan = positive("x86_64", "X86-P1-mov-r64-both-directions");
    assert!(plan.provenance.is_none(), "the fixture has no provenance");
    let mut with_provenance = plan.clone();
    with_provenance.provenance = Some(Provenance {
        materializer_version: "0.0.0".to_string(),
        build_profile: Some("debug".to_string()),
        generated_by: Some("planner".to_string()),
        notes: Some("a note".to_string()),
        path: "/provenance".to_string(),
    });

    assert_eq!(
        fmp_model::identity::ParsedPlanIdentity::of(&plan),
        fmp_model::identity::ParsedPlanIdentity::of(&with_provenance),
        "provenance is not a plan fact"
    );
}

/// `ParsedPlanIdentity` also ignores the raw document; the legacy fingerprint
/// does not. This is the constraint `D12` keeps alive.
#[test]
fn plan_identity_ignores_the_legacy_document() {
    let plain = positive("x86_64", "X86-P1-mov-r64-both-directions");
    let traced = with_source_trace(&fixture(
        "x86_64",
        "positive",
        "X86-P1-mov-r64-both-directions",
    ));
    assert_eq!(
        fmp_model::identity::ParsedPlanIdentity::of(&plain),
        fmp_model::identity::ParsedPlanIdentity::of(&traced),
        "source_trace is not a parsed plan fact"
    );
}

/// D3: the parsed facts are what execution reads, so changing an operand must
/// change the plan identity. The legacy fingerprint stays put because it hashes
/// the document, which still names the old operand.
#[test]
fn a_mutated_operand_changes_the_plan_identity() {
    let definition = definition("x86_64", "0.1.0");
    let mut plan = positive("x86_64", "X86-P1-mov-r64-both-directions");
    let fingerprint = fmp_materialize::fingerprint(&plan, &definition);
    let first = bind(plan.clone(), Arc::clone(&definition)).expect("the fixture binds");
    let first_identity = first.identity().plan().digest().to_string();

    match &mut plan.instructions[0].operands[1].payload {
        Payload::Register(reg) => *reg = 1,
        other => panic!("X86-P1's second operand is a register, found {other:?}"),
    }
    let second = bind(plan, Arc::clone(&definition)).expect("register 1 is legal here");

    assert_ne!(
        second.identity().plan().digest(),
        first_identity,
        "an operand edit must change the plan identity"
    );
    assert_eq!(
        fmp_materialize::fingerprint(second.plan(), &definition),
        fingerprint,
        "the legacy fingerprint hashes `legacy_document`, not the parsed operands"
    );

    let before = fmp_materialize::materialize(&first)
        .expect("the fixture executes")
        .artifact;
    let after = fmp_materialize::materialize(&second)
        .expect("the edited plan executes")
        .artifact;
    assert_ne!(
        before.bytes, after.bytes,
        "the executed facts changed, so the bytes must too"
    );
    assert_ne!(payload_digest(&before), payload_digest(&after));
}

/// D3/D12: the fingerprint is a legacy envelope value, not a trusted cache key.
/// Two executions can share it and still be different executions.
#[test]
fn a_legacy_fingerprint_is_not_a_trusted_cache_key() {
    let definition = definition("x86_64", "0.1.0");
    let mut plan = positive("x86_64", "X86-P1-mov-r64-both-directions");
    let fingerprint = fmp_materialize::fingerprint(&plan, &definition);
    let first = fmp_materialize::materialize(
        &bind(plan.clone(), Arc::clone(&definition)).expect("the fixture binds"),
    )
    .expect("the fixture executes");

    match &mut plan.instructions[0].operands[1].payload {
        Payload::Register(reg) => *reg = 1,
        other => panic!("X86-P1's second operand is a register, found {other:?}"),
    }
    let second = fmp_materialize::materialize(
        &bind(plan, Arc::clone(&definition)).expect("register 1 is legal here"),
    )
    .expect("the edited plan executes");

    assert_eq!(
        second.artifact.fingerprint, fingerprint,
        "the fingerprint did not move"
    );
    assert_ne!(
        first.receipt, second.receipt,
        "the execution receipt did move"
    );
}

/// D3/D12: `BindIdentity` is the parsed plan plus the bound table. A document
/// change the parser drops binds identically, yet changes the payload digest.
#[test]
fn a_bind_identity_does_not_identify_the_legacy_artifact() {
    let definition = definition("x86_64", "0.1.0");
    let bytes = fixture("x86_64", "positive", "X86-P1-mov-r64-both-directions");
    let plain = plan::read(&bytes).expect("the fixture parses");
    let traced = with_source_trace(&bytes);

    let first = fmp_materialize::materialize(
        &bind(plain, Arc::clone(&definition)).expect("the fixture binds"),
    )
    .expect("the fixture executes");
    let second = fmp_materialize::materialize(
        &bind(traced, Arc::clone(&definition)).expect("the traced plan binds"),
    )
    .expect("the traced plan executes");

    assert_eq!(
        first.receipt.bind(),
        second.receipt.bind(),
        "source_trace is not part of the binding identity"
    );
    assert_eq!(
        first.artifact.bytes, second.artifact.bytes,
        "the traced plan encodes the same machine code"
    );
    assert_ne!(
        first.artifact.fingerprint, second.artifact.fingerprint,
        "the legacy fingerprint covers the raw document"
    );
    assert_ne!(
        first.receipt.payload(),
        second.receipt.payload(),
        "only the receipt can tell the two executions apart"
    );
}

/// `payload_digest` is the `payload/0.1` projection: the envelope's
/// `materializer_version` is outside it, the bytes are inside it.
#[test]
fn payload_digest_follows_the_bytes() {
    let definition = definition("x86_64", "0.1.0");
    let materialization = fmp_materialize::materialize(
        &bind(
            positive("x86_64", "X86-P1-mov-r64-both-directions"),
            definition,
        )
        .expect("the fixture binds"),
    )
    .expect("the fixture executes");

    let digest = payload_digest(&materialization.artifact);
    let mut projection = materialization.artifact.to_json();
    if let Json::Object(entries) = &mut projection {
        entries.retain(|(key, _)| key != "materializer_version");
    }
    let expected =
        fmp_model::canonical::sha256_prefixed(&[&fmp_model::canonical::canonical_bytes(
            &projection,
        )]);
    assert_eq!(digest, expected, "the projection is the receipt's digest");
    assert_eq!(materialization.receipt.payload().digest(), digest);

    let mut changed = materialization.artifact.clone();
    changed.bytes[0] ^= 0xFF;
    assert_ne!(
        payload_digest(&changed),
        digest,
        "a byte change must move the payload identity"
    );

    let envelope = fmp_model::canonical::canonical_digest(&materialization.artifact.to_json());
    assert_ne!(
        envelope, digest,
        "the envelope digest and the payload digest answer different questions"
    );

    // The plan's second half: changing the envelope's version changes the
    // envelope but must leave the payload identity alone. The version is a
    // compile-time constant, so the edit is made on the JSON projection.
    let mut other_version = materialization.artifact.to_json();
    match &mut other_version {
        Json::Object(entries) => {
            let version = entries
                .iter_mut()
                .find(|(key, _)| key == "materializer_version")
                .map(|(_, value)| value)
                .expect("the envelope records materializer_version");
            *version = Json::Str("9.9.9".to_string());
        }
        other => panic!("the artifact envelope is an object, found {other:?}"),
    }
    assert_ne!(
        fmp_model::canonical::canonical_digest(&other_version),
        envelope,
        "the version is inside the envelope"
    );
    if let Json::Object(entries) = &mut other_version {
        entries.retain(|(key, _)| key != "materializer_version");
    }
    assert_eq!(
        fmp_model::canonical::sha256_prefixed(&[&fmp_model::canonical::canonical_bytes(
            &other_version
        )]),
        digest,
        "the version is outside the payload identity"
    );
}

/// The receipt names **this** build, not `fmp-model`'s workspace version.
#[test]
fn receipt_names_the_build_that_ran() {
    let definition = definition("x86_64", "0.1.0");
    let materialization = fmp_materialize::materialize(
        &bind(
            positive("x86_64", "X86-P1-mov-r64-both-directions"),
            definition,
        )
        .expect("the fixture binds"),
    )
    .expect("the fixture executes");

    let implementation = materialization.receipt.implementation();
    assert_eq!(implementation, &ImplementationIdentity::current());
    assert_eq!(implementation.name(), "fmp-materialize");
    assert_eq!(
        implementation.version(),
        fmp_materialize::MATERIALIZER_VERSION
    );
    assert_eq!(implementation.build(), option_env!("FMP_BUILD_ID"));

    // A compile-time label can disappear without any compiler error: a local
    // build legitimately has none, and a CI build that stopped passing the
    // variable would look the same. CI sets the variable for the test process
    // as well, so a run-time value the receipt does not carry means the label
    // was not compiled in, and the job's own non-empty check catches a workflow
    // that drops the variable entirely.
    match std::env::var("FMP_BUILD_ID") {
        Ok(runtime) => assert_eq!(
            implementation.build(),
            Some(runtime.as_str()),
            "the receipt did not record the build label this process was given"
        ),
        // No build label: the receipt must not claim `HE-T20` coverage.
        Err(_) => assert_eq!(implementation.build(), None),
    }
}

/// D4/§8.3: an allocator failure is a host limit, not `Internal` and not a plan
/// rejection; the same plan still succeeds with a functioning allocator.
#[test]
fn an_image_reservation_failure_is_a_host_failure() {
    let definition = definition("x86_64", "0.1.0");
    let validated = bind(
        positive("x86_64", "X86-P1-mov-r64-both-directions"),
        definition,
    )
    .expect("the fixture binds");
    let declared = validated.plan().sections[0].declared_size;

    // The same plan on a working allocator: a reservation failure is not a
    // property of this input.
    fmp_materialize::materialize(&validated).expect("the host can allocate six bytes here");

    let requested = std::cell::Cell::new(None);
    let failure = fmp_materialize::materialize_with_allocator(&validated, |size| {
        requested.set(Some(size));
        Err(HostFault::ImageReservation { requested: size })
    })
    .expect_err("the injected allocator fails");

    match failure {
        MaterializationFailure::HostFailure(HostFault::ImageReservation { requested: value }) => {
            assert_eq!(value, declared);
        }
        other => panic!("expected a host failure, got {other:?}"),
    }
    assert_eq!(
        requested.get(),
        Some(declared),
        "the allocator saw the section's declared size"
    );
}

/// A short image must be a host failure, not a panic on the first fragment
/// write. The allocator contract is exact-length, and a violated contract says
/// nothing about the plan.
#[test]
fn a_short_image_is_a_host_failure() {
    let definition = definition("x86_64", "0.1.0");
    let validated = bind(
        positive("x86_64", "X86-P1-mov-r64-both-directions"),
        definition,
    )
    .expect("the fixture binds");
    let declared = validated.plan().sections[0].declared_size;
    assert!(declared > 0, "the fixture has an image-backed section");

    let failure = fmp_materialize::materialize_with_allocator(&validated, |size| {
        Ok(vec![0u8; size.saturating_sub(1) as usize])
    })
    .expect_err("a short image is rejected");

    match failure {
        MaterializationFailure::HostFailure(HostFault::ImageLength { requested, actual }) => {
            assert_eq!(requested, declared);
            assert_eq!(actual, declared - 1);
        }
        other => panic!("expected a host length failure, got {other:?}"),
    }
}

/// A long image must be a host failure too: accepting it would return more
/// bytes than the frozen plan declares. The check runs before encoding, so no
/// fragment is written into the surplus.
#[test]
fn a_long_image_is_a_host_failure() {
    let definition = definition("x86_64", "0.1.0");
    let validated = bind(
        positive("x86_64", "X86-P1-mov-r64-both-directions"),
        definition,
    )
    .expect("the fixture binds");
    let declared = validated.plan().sections[0].declared_size;

    let failure = fmp_materialize::materialize_with_allocator(&validated, |size| {
        Ok(vec![0u8; size as usize + 1])
    })
    .expect_err("a long image is rejected");

    match failure {
        MaterializationFailure::HostFailure(HostFault::ImageLength { requested, actual }) => {
            assert_eq!(requested, declared);
            assert_eq!(actual, declared + 1);
        }
        other => panic!("expected a host length failure, got {other:?}"),
    }
}

/// The artifact stays mutable, so the receipt can go stale; `verify_receipt`
/// is the documented way to notice before persisting a pair that no longer
/// describes the bytes.
#[test]
fn verify_receipt_notices_an_edited_artifact() {
    let definition = definition("x86_64", "0.1.0");
    let mut materialization = fmp_materialize::materialize(
        &bind(
            positive("x86_64", "X86-P1-mov-r64-both-directions"),
            definition,
        )
        .expect("the fixture binds"),
    )
    .expect("the fixture executes");

    assert!(materialization.verify_receipt(), "a fresh pair must verify");
    assert!(!materialization.artifact.bytes.is_empty());
    materialization.artifact.bytes[0] ^= 0xff;
    assert!(
        !materialization.verify_receipt(),
        "the recorded digest no longer names these bytes"
    );
}

/// The historical `materialize(&Plan, &Definition)` shape now routes through
/// `bind`; a digest mismatch is a binding rejection, exactly as before.
#[test]
fn legacy_facade_rejects_a_digest_mismatch() {
    let definition = definition("x86_64", "0.1.0");
    let bytes = fixture("x86_64", "negative", "N10-definition-digest-mismatch");
    let plan = plan::read(&bytes).expect("the fixture parses");

    let direct =
        bind(plan.clone(), Arc::clone(&definition)).expect_err("the digest does not match");
    let facade = legacy::materialize(&plan, definition).expect_err("the digest does not match");

    match facade {
        LegacyFailure::Rejected(errors) => {
            assert_eq!(errors, direct);
            assert_eq!(errors.len(), 1, "{errors:#?}");
            assert_eq!(errors[0].code(), codes::E_DEF_001);
            assert_eq!(errors[0].path(), "/definition_identity/digest");
        }
        other => panic!("expected a binding rejection, got {other:?}"),
    }
}

/// D15: the facade cannot skip the namespace/version comparison either; it
/// returns the same Pointer the direct binding does.
#[test]
fn a_definition_identity_mismatch_is_rejected_by_the_legacy_facade() {
    let definition = definition("x86_64", "0.1.0");
    let mut plan = positive("x86_64", "X86-P1-mov-r64-both-directions");
    plan.definition.namespace = "monasm.isa.probe".to_string();

    let direct = bind(plan.clone(), Arc::clone(&definition))
        .expect_err("the namespace does not match the bound definition");
    let facade = legacy::materialize(&plan, definition).expect_err("the namespace does not match");

    match facade {
        LegacyFailure::Rejected(errors) => {
            assert_eq!(
                errors
                    .iter()
                    .map(fmp_model::Diagnostic::identity)
                    .collect::<Vec<_>>(),
                direct
                    .iter()
                    .map(fmp_model::Diagnostic::identity)
                    .collect::<Vec<_>>(),
                "the facade reports the same diagnostics as `bind`"
            );
            assert_eq!(errors.len(), 1, "{errors:#?}");
            assert_eq!(errors[0].path(), "/definition_identity/namespace");
        }
        other => panic!("expected a binding rejection, got {other:?}"),
    }
}
