//! H1a (`ADR-0127`, D14/D16): arithmetic bounds inside `check`, and the
//! `page` PC-reference precondition.
//!
//! These inputs are already-typed plans whose numbers are legal as types but
//! illegal as plan facts. H1a calls `check` directly, because `bind` does not
//! exist until H1b; H1b replays them end to end. The point of each test is that
//! `check` returns in bounded time instead of panicking or looping over a `u32`
//! range of bits.

use std::path::PathBuf;
use std::sync::Arc;

use fmp_model::codes;
use fmp_model::definition::Definition;
use fmp_model::json::{self, Json};
use fmp_model::plan::{self, FieldRange, PcRule, Plan};
use fmp_model::Registry;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn registry() -> Registry {
    Registry::load_dir(&root().join("definitions")).expect("definitions/ must load")
}

fn read_bytes(isa: &str, name: &str) -> Vec<u8> {
    let path = root().join(format!("fixtures/{isa}/positive/{name}.fmp.json"));
    std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()))
}

fn positive(isa: &str, name: &str) -> (Plan, Arc<Definition>) {
    let bytes = read_bytes(isa, name);
    let plan = plan::read(&bytes).expect("the fixture parses");
    let definition = registry()
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the fixture's definition exists");
    (plan, definition)
}

fn codes_of(errors: &[fmp_model::Diagnostic]) -> Vec<&'static str> {
    errors.iter().map(|error| error.code()).collect()
}

/// D14: `field.width` is a `u32`, so two `u32::MAX` widths used to overflow the
/// `u32` sum and `field.lsb + field.width`, and a 4-billion-bit loop followed.
/// `check` is the second line of defence (H1b rejects the same input earlier in
/// `check_structure`), so it must return diagnostics, not panic.
#[test]
fn a_descriptor_width_sum_cannot_overflow() {
    let (mut plan, definition) = positive("aarch64", "A64-P4-b-cond");
    plan.fixups[0].field_descriptor = vec![
        FieldRange {
            lsb: 0,
            width: u32::MAX,
        },
        FieldRange {
            lsb: 1,
            width: u32::MAX,
        },
    ];

    let errors = fmp_validate::check(&plan, &definition);
    assert!(
        codes_of(&errors).contains(&codes::E_FIXUP_001)
            && codes_of(&errors).contains(&codes::E_FIXUP_005),
        "{errors:#?}"
    );
}

/// D14: a site near `u64::MAX` makes `offset * 8` overflow. The two fixups are
/// injected into the **JSON** and re-read, so the parser's domain (a `u64`) is
/// respected and only the arithmetic is under test.
#[test]
fn two_huge_fixup_offsets_do_not_overflow() {
    let bytes = read_bytes("aarch64", "A64-P4-b-cond");
    let mut document = json::parse(&bytes).expect("the fixture parses as JSON");
    set_fixup_offset(&mut document, 0, u64::MAX);
    set_fixup_offset(&mut document, 1, u64::MAX - 8);
    let plan = plan::read(&fmp_model::canonical::canonical_bytes(&document))
        .expect("u64::MAX is a legal offset");
    let definition = registry()
        .find(&plan.definition.namespace, &plan.definition.version)
        .expect("the fixture's definition exists");

    let errors = fmp_validate::check(&plan, &definition);
    let paths: Vec<&str> = errors.iter().map(|error| error.path()).collect();
    assert!(paths.contains(&"/fixups/0/offset"), "{errors:#?}");
    assert!(paths.contains(&"/fixups/1/offset"), "{errors:#?}");
    assert!(
        errors
            .iter()
            .all(|error| error.code() != codes::E_INTERNAL_001),
        "{errors:#?}"
    );
}

/// D16: `page` is `page(S + A) - page(P)`, so it needs a `P`. Before H1a the
/// only rejection was the `internal(...)` arm in `apply`, reached after the
/// plan had been accepted. The kind is now rejected statically.
#[test]
fn a_page_transform_without_a_page_pc_rule_is_rejected() {
    let (mut plan, definition) = positive("aarch64", "A64-P6-adrp-lo12-pair");
    assert!(matches!(
        &plan.fixups[0].pc_reference_rule,
        PcRule::PcrelPage
    ));
    plan.fixups[0].pc_reference_rule = PcRule::None;

    let errors = fmp_validate::check(&plan, &definition);
    let error = errors
        .iter()
        .find(|error| error.path() == "/fixups/0/pc_reference_rule")
        .unwrap_or_else(|| panic!("no pc_reference_rule diagnostic: {errors:#?}"));
    assert_eq!(error.code(), codes::E_FIXUP_001);
    assert_eq!(
        error
            .details()
            .get("kind")
            .map(fmp_model::diagnostic::Detail::render),
        Some("value_transform:page".to_string())
    );
    assert!(
        codes_of(&errors)
            .iter()
            .all(|code| *code != codes::E_INTERNAL_001),
        "{errors:#?}"
    );
}

/// D14, register width: `slot.width_bits` is the **sum** of its placements, and
/// the loader bounds each placement to 64 bits, not the sum. A definition can
/// therefore declare a 64-bit register field, which made the old
/// `1u64 << field_bits` overflow (panic in debug) for exactly `width_bits == 64`.
/// The comparison now uses `u128` + `checked_shl`: a register is a `u64`, so it
/// always fits, and no diagnostic is expected.
///
/// `definitions/**` is frozen and no shipped slot is that wide, so the table is
/// built here. This is also why the fix is `u128` rather than a load-time
/// constraint on `width_bits`: the width is a legal definition fact, only the
/// comparison was unsafe.
#[test]
fn a_wide_register_field_does_not_overflow_the_width_check() {
    let cases = [
        (
            "64-bit field",
            "0000000000000000",
            r#"[{"bit_offset":0,"width":32},{"bit_offset":32,"width":32}]"#,
        ),
        (
            "128-bit field",
            "00000000000000000000000000000000",
            r#"[{"bit_offset":0,"width":64},{"bit_offset":64,"width":64}]"#,
        ),
    ];

    for (label, template, placements) in cases {
        let form = format!(
            r#"{{"form_id":"x86:wide/rm64/legacy","template":"{template}","slots":[{{"role":"dest","kind":"x86.gpr64","target_type":"rm64","from":"reg_number","modifiers":[],"placements":{placements}}}]}}"#
        );
        let definition_text = [
            r#"{"definition_format":"fmp-def/0.1","namespace":"monasm.isa.x86","version":"test","#,
            r#""target_identity":{"isa_family":"x86","isa_variant":"x86-64","execution_mode":"64","#,
            r#""enabled_extensions":[],"byte_order":"little","address_width":64},"forms":["#,
            &form,
            "]}",
        ]
        .concat();
        let definition =
            fmp_model::definition::read(definition_text.as_bytes()).unwrap_or_else(|error| {
                panic!("{label}: the synthetic table loads: {}", error.message())
            });

        let size = template.len() / 2;
        let plan_text = [
            r#"{"format_version":"fmp/0.1","#,
            r#""target_identity":{"isa_family":"x86","isa_variant":"x86-64","execution_mode":"64","#,
            r#""enabled_extensions":[],"feature_constraints":[],"byte_order":"little","address_width":64},"#,
            &format!(
                r#""definition_identity":{{"namespace":"monasm.isa.x86","version":"test","digest":"{}"}},"#,
                definition.digest()
            ),
            r#""output_contract":{"artifact":"bytes","section_order":[".text"],"#,
            r#""fixup_record_order":"section_id,offset,fixup_id","include_symbol_table":false,"emit_fixups":true},"#,
            r#""sections":[{"section_id":".text","section_kind":"code","image_backed":true,"#,
            &format!(
                r#""declared_size":{size},"fragments":[{{"offset":0,"size":{size},"#
            ),
            r#""kind":"instruction","instruction_id":"I0001"}]}],"#,
            r#""symbols":[],"#,
            r#""instructions":[{"instruction_id":"I0001","section_id":".text","offset":0,"#,
            r#""form_id":"x86:wide/rm64/legacy","operands":[{"role":"dest","kind":"x86.gpr64","#,
            r#""target_type":"rm64","payload":{"reg":0},"modifiers":[]}],"#,
            &format!(r#""expected_size":{size}}}],"#),
            r#""fixups":[]}"#,
        ]
        .concat();
        let plan = plan::read(plan_text.as_bytes()).unwrap_or_else(|error| {
            panic!("{label}: the synthetic plan reads: {}", error.message())
        });

        let errors = fmp_validate::check(&plan, &definition);
        assert!(
            !codes_of(&errors).contains(&codes::E_OPERAND_004),
            "{label}: a u64 register always fits the field: {errors:#?}"
        );
    }
}

fn set_fixup_offset(document: &mut Json, index: usize, value: u64) {
    let Json::Object(root) = document else {
        panic!("a plan is an object");
    };
    let fixups = root
        .iter_mut()
        .find(|(key, _)| key == "fixups")
        .map(|(_, value)| value)
        .expect("the fixture declares fixups");
    let Json::Array(items) = fixups else {
        panic!("fixups is an array");
    };
    let Json::Object(fixup) = &mut items[index] else {
        panic!("a fixup is an object");
    };
    let slot = fixup
        .iter_mut()
        .find(|(key, _)| key == "offset")
        .map(|(_, value)| value)
        .expect("a fixup has an offset");
    *slot = Json::Int(i128::from(value));
}
