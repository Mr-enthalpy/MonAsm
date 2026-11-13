//! H1a review, P1: a register field wider than one machine word must both
//! validate and **encode**.
//!
//! `ADR-0127` §7.1 keeps `slot.width_bits` a legal definition fact: the loader
//! bounds each *placement* to 64 bits but not their sum. H1a's validator fix
//! widened the range comparison to `u128`, so such a definition passes every
//! gate. This test therefore goes one step further than
//! `he1_validation_bounds.rs` and calls `materialize`, asserting the bytes.
//!
//! The values are non-zero on purpose: writing zero into every placement hides
//! a chunk-extraction bug, because the wrong chunk is also zero. The 127-bit
//! case puts a set bit in each half, and the 192-bit case would put the value
//! into the *first* placement if the shift wrapped.
//!
//! `definitions/**` is frozen and ships no slot this wide, so the table is
//! built here from `definition::read`, the same loader the registry uses.

use fmp_model::codes;
use fmp_model::definition::Definition;
use fmp_model::plan::{self, Plan};
use std::sync::Arc;

struct Case {
    label: &'static str,
    /// The form template: `total` zero bits, hex.
    template: &'static str,
    /// Most significant placement first; widths sum to the field width.
    placements: &'static str,
    register: u64,
    expected_hex: &'static str,
}

const CASES: &[Case] = &[
    Case {
        label: "64-bit field",
        template: "0000000000000000",
        placements: r#"[{"bit_offset":0,"width":32},{"bit_offset":32,"width":32}]"#,
        register: 0x1122_3344_5566_7788,
        // high half 0x11223344 at bit 0, low half 0x55667788 at bit 32
        expected_hex: "4433221188776655",
    },
    Case {
        label: "127-bit field",
        template: "00000000000000000000000000000000",
        placements: r#"[{"bit_offset":0,"width":64},{"bit_offset":64,"width":63}]"#,
        register: 0x8000_0000_0000_0001,
        expected_hex: "01000000000000000100000000000000",
    },
    Case {
        label: "128-bit field",
        template: "00000000000000000000000000000000",
        placements: r#"[{"bit_offset":0,"width":64},{"bit_offset":64,"width":64}]"#,
        register: 0x1122_3344_5566_7788,
        expected_hex: "00000000000000008877665544332211",
    },
    Case {
        label: "192-bit field",
        template: "000000000000000000000000000000000000000000000000",
        placements: r#"[{"bit_offset":0,"width":64},{"bit_offset":64,"width":64},{"bit_offset":128,"width":64}]"#,
        register: 0x1122_3344_5566_7788,
        // Only the last placement may carry the value: `1` must not appear at
        // bit 0 (the pre-fix release bug).
        expected_hex: "000000000000000000000000000000008877665544332211",
    },
];

#[test]
fn a_wide_register_field_encodes_the_same_bytes_in_every_build() {
    for case in CASES {
        let definition = read_definition(case);
        let plan = read_plan(&definition, case);

        let structure = plan::check_structure(&plan);
        assert!(structure.is_empty(), "{}: {structure:#?}", case.label);
        let validation = fmp_validate::check(&plan, &definition);
        assert!(validation.is_empty(), "{}: {validation:#?}", case.label);

        let validated = fmp_validate::bind(plan, Arc::new(definition))
            .unwrap_or_else(|errors| panic!("{}: {errors:#?}", case.label));
        let artifact = fmp_materialize::materialize(&validated)
            .unwrap_or_else(|failure| panic!("{}: {failure:#?}", case.label))
            .artifact;
        assert_eq!(
            artifact.bytes_hex(),
            case.expected_hex,
            "{}: register {:#x}",
            case.label,
            case.register
        );
    }
}

fn read_definition(case: &Case) -> Definition {
    let form = format!(
        r#"{{"form_id":"x86:wide/rm64/legacy","template":"{}","slots":[{{"role":"dest","kind":"x86.gpr64","target_type":"rm64","from":"reg_number","modifiers":[],"placements":{}}}]}}"#,
        case.template, case.placements
    );
    let text = [
        r#"{"definition_format":"fmp-def/0.1","namespace":"monasm.isa.x86","version":"test","#,
        r#""target_identity":{"isa_family":"x86","isa_variant":"x86-64","execution_mode":"64","#,
        r#""enabled_extensions":[],"byte_order":"little","address_width":64},"forms":["#,
        &form,
        "]}",
    ]
    .concat();
    fmp_model::definition::read(text.as_bytes()).unwrap_or_else(|error| {
        panic!(
            "{}: the synthetic table loads: {}",
            case.label,
            error.message()
        )
    })
}

fn read_plan(definition: &Definition, case: &Case) -> Plan {
    let size = case.template.len() / 2;
    let text = [
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
        &format!(r#""declared_size":{size},"fragments":[{{"offset":0,"size":{size},"#),
        r#""kind":"instruction","instruction_id":"I0001"}]}],"#,
        r#""symbols":[],"#,
        r#""instructions":[{"instruction_id":"I0001","section_id":".text","offset":0,"#,
        r#""form_id":"x86:wide/rm64/legacy","operands":[{"role":"dest","kind":"x86.gpr64","#,
        &format!(
            r#""target_type":"rm64","payload":{{"reg":{}}},"modifiers":[]}}],"#,
            case.register
        ),
        &format!(r#""expected_size":{size}}}],"#),
        r#""fixups":[]}"#,
    ]
    .concat();
    let plan = plan::read(text.as_bytes()).unwrap_or_else(|error| {
        panic!(
            "{}: the synthetic plan reads: {}",
            case.label,
            error.message()
        )
    });
    assert_eq!(
        plan.format_version,
        codes::FORMAT_VERSION,
        "{}: the synthetic plan uses the shipped format",
        case.label
    );
    plan
}
