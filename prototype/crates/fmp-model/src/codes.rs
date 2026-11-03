//! Diagnostic codes from `docs/fmp-v0/04_errors.md` §2.
//!
//! One constant per registry row, spelled exactly as the registry spells it. A
//! new condition gets a new constant; a constant is never repurposed for a
//! different trigger (§3, "No code may be reused for a different condition").

/// Unknown or unsupported `format_version`.
pub const E_PLAN_001: &str = "E-PLAN-001";
/// Wrong type, non-integer literal, or out-of-domain value.
pub const E_PLAN_002: &str = "E-PLAN-002";
/// Unknown field in a strict object.
pub const E_PLAN_003: &str = "E-PLAN-003";
/// Document is not parseable, or has duplicate keys.
pub const E_PLAN_004: &str = "E-PLAN-004";
/// Canonical-form violation that changes bytes (BOM and friends).
pub const E_PLAN_005: &str = "E-PLAN-005";
/// Required field absent from a strict object.
pub const E_PLAN_006: &str = "E-PLAN-006";
/// Mismatched `isa_family`, `isa_variant`, or `enabled_extensions`.
pub const E_TARGET_001: &str = "E-TARGET-001";
/// Invalid or mismatched `execution_mode`.
pub const E_TARGET_002: &str = "E-TARGET-002";
/// Form requires an extension that is not enabled.
pub const E_TARGET_003: &str = "E-TARGET-003";
/// Unsupported or mismatched `byte_order` or `address_width`.
pub const E_TARGET_004: &str = "E-TARGET-004";
/// Definition cannot be loaded, or its digest does not match.
pub const E_DEF_001: &str = "E-DEF-001";
/// Namespace or version not shipped by this materializer.
pub const E_DEF_002: &str = "E-DEF-002";
/// `form_id` is not present in the pinned definition.
pub const E_FORM_001: &str = "E-FORM-001";
/// Operand kind or `target_type` does not match the form.
pub const E_OPERAND_001: &str = "E-OPERAND-001";
/// Operand count or role sequence mismatch.
pub const E_OPERAND_002: &str = "E-OPERAND-002";
/// Operand payload malformed for its kind.
pub const E_OPERAND_003: &str = "E-OPERAND-003";
/// Operand value does not fit the slot's encoded field.
pub const E_OPERAND_004: &str = "E-OPERAND-004";
/// Immediate outside the legal encoding range.
pub const E_RANGE_001: &str = "E-RANGE-001";
/// Displacement or branch offset outside the legal range.
pub const E_RANGE_002: &str = "E-RANGE-002";
/// Alignment requirement not met.
pub const E_RANGE_003: &str = "E-RANGE-003";
/// Operand value is excluded by the slot's declared domain.
pub const E_RANGE_004: &str = "E-RANGE-004";
/// Fragments overlap.
pub const E_LAYOUT_001: &str = "E-LAYOUT-001";
/// Fragment gap, or fragment sum != `declared_size`.
pub const E_LAYOUT_002: &str = "E-LAYOUT-002";
/// Instruction offset/size does not match its fragment.
pub const E_LAYOUT_003: &str = "E-LAYOUT-003";
/// List order violates the contract's declared order.
pub const E_LAYOUT_004: &str = "E-LAYOUT-004";
/// Layout requires the materializer to compute padding or alignment.
pub const E_LAYOUT_005: &str = "E-LAYOUT-005";
/// Duplicate `section_id`, or `section_order` is not a permutation.
pub const E_LAYOUT_006: &str = "E-LAYOUT-006";
/// Duplicate `instruction_id`, or two instructions at the same site.
pub const E_LAYOUT_007: &str = "E-LAYOUT-007";
/// A reference names a `symbol_id` that `symbols[]` does not declare.
pub const E_SYMBOL_001: &str = "E-SYMBOL-001";
/// Duplicate `symbol_id`, or duplicate emitted name with conflicting binding.
pub const E_SYMBOL_002: &str = "E-SYMBOL-002";
/// Defined symbol without a resolvable location.
pub const E_SYMBOL_003: &str = "E-SYMBOL-003";
/// Fixup is incompatible with the form, the descriptor, or the operands.
pub const E_FIXUP_001: &str = "E-FIXUP-001";
/// Target has no address in a `resolve_in_place` fixup.
pub const E_FIXUP_002: &str = "E-FIXUP-002";
/// Computed fixup value outside `range_constraint`.
pub const E_FIXUP_003: &str = "E-FIXUP-003";
/// Field descriptor out of bounds or self-overlapping.
pub const E_FIXUP_005: &str = "E-FIXUP-005";
/// Two writers patch overlapping bits.
pub const E_FIXUP_006: &str = "E-FIXUP-006";
/// Pair group incomplete, duplicated role, or target mismatch.
pub const E_FIXUP_007: &str = "E-FIXUP-007";
/// Duplicate `fixup_id`.
pub const E_FIXUP_008: &str = "E-FIXUP-008";
/// Encoded length != `expected_size`.
pub const E_SIZE_001: &str = "E-SIZE-001";
/// Emitted bytes do not match `expected_digest`.
pub const E_BYTE_001: &str = "E-BYTE-001";
/// Materializer cannot honor a declared plan feature.
pub const E_VERSION_001: &str = "E-VERSION-001";
/// Internal invariant violated (bug).
pub const E_INTERNAL_001: &str = "E-INTERNAL-001";

/// Every code the registry currently declares, in registry order.
///
/// `E-FIXUP-004`, `E-CHOICE-001..003` are absent on purpose: they are retired
/// (`04_errors.md` §2.2) and must not be produced.
pub const ALL: &[&str] = &[
    E_PLAN_001,
    E_PLAN_002,
    E_PLAN_003,
    E_PLAN_004,
    E_PLAN_005,
    E_PLAN_006,
    E_TARGET_001,
    E_TARGET_002,
    E_TARGET_003,
    E_TARGET_004,
    E_DEF_001,
    E_DEF_002,
    E_FORM_001,
    E_OPERAND_001,
    E_OPERAND_002,
    E_OPERAND_003,
    E_OPERAND_004,
    E_RANGE_001,
    E_RANGE_002,
    E_RANGE_003,
    E_RANGE_004,
    E_LAYOUT_001,
    E_LAYOUT_002,
    E_LAYOUT_003,
    E_LAYOUT_004,
    E_LAYOUT_005,
    E_LAYOUT_006,
    E_LAYOUT_007,
    E_SYMBOL_001,
    E_SYMBOL_002,
    E_SYMBOL_003,
    E_FIXUP_001,
    E_FIXUP_002,
    E_FIXUP_003,
    E_FIXUP_005,
    E_FIXUP_006,
    E_FIXUP_007,
    E_FIXUP_008,
    E_SIZE_001,
    E_BYTE_001,
    E_VERSION_001,
    E_INTERNAL_001,
];

/// The `format_version` this build implements.
pub const FORMAT_VERSION: &str = "fmp/0.1";
/// The definition document format this build implements.
pub const DEFINITION_FORMAT: &str = "fmp-def/0.1";
