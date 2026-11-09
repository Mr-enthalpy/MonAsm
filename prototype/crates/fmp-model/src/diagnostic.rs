//! The error envelope from `docs/fmp-v0/04_errors.md` §1.
//!
//! Identity is `(code, path, sorted detail keys)`. The free-text `message` is
//! excluded from identity on purpose: `EXP-R6` requires two runs to agree on
//! identity even if the prose improves.

use std::collections::BTreeMap;

use crate::canonical;
use crate::json::Json;

/// A detail value. Details are informational; only their *keys* enter identity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Detail {
    Int(i128),
    Text(String),
    Bool(bool),
}

impl Detail {
    pub fn render(&self) -> String {
        match self {
            Detail::Int(value) => value.to_string(),
            Detail::Text(value) => value.clone(),
            Detail::Bool(value) => value.to_string(),
        }
    }
}

impl From<i64> for Detail {
    fn from(value: i64) -> Self {
        Detail::Int(value as i128)
    }
}

impl From<u64> for Detail {
    fn from(value: u64) -> Self {
        Detail::Int(value as i128)
    }
}

impl From<u32> for Detail {
    fn from(value: u32) -> Self {
        Detail::Int(value as i128)
    }
}

impl From<usize> for Detail {
    fn from(value: usize) -> Self {
        Detail::Int(value as i128)
    }
}

impl From<i128> for Detail {
    fn from(value: i128) -> Self {
        Detail::Int(value)
    }
}

impl From<bool> for Detail {
    fn from(value: bool) -> Self {
        Detail::Bool(value)
    }
}

impl From<&str> for Detail {
    fn from(value: &str) -> Self {
        Detail::Text(value.to_string())
    }
}

impl From<String> for Detail {
    fn from(value: String) -> Self {
        Detail::Text(value)
    }
}

/// One rejection: a stable code, a JSON Pointer into the plan, and fixed keys.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Diagnostic {
    code: &'static str,
    path: String,
    details: BTreeMap<&'static str, Detail>,
}

impl Diagnostic {
    pub fn new(code: &'static str, path: impl Into<String>) -> Self {
        Diagnostic {
            code,
            path: path.into(),
            details: BTreeMap::new(),
        }
    }

    /// Add a detail. Keys are `&'static str` so a typo cannot reach identity.
    pub fn with(mut self, key: &'static str, value: impl Into<Detail>) -> Self {
        self.details.insert(key, value.into());
        self
    }

    pub fn code(&self) -> &'static str {
        self.code
    }

    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn details(&self) -> &BTreeMap<&'static str, Detail> {
        &self.details
    }

    /// `sha256(code || "\0" || path || "\0" || join(sorted(detail_keys), ","))`.
    pub fn identity(&self) -> String {
        let keys: Vec<&str> = self.details.keys().copied().collect();
        canonical::sha256_prefixed(&[
            self.code.as_bytes(),
            b"\0",
            self.path.as_bytes(),
            b"\0",
            keys.join(",").as_bytes(),
        ])
    }

    /// The §1 envelope: `{ code, path, details, message }`.
    pub fn to_json(&self) -> Json {
        let details = self
            .details
            .iter()
            .map(|(key, value)| {
                (
                    (*key).to_string(),
                    match value {
                        Detail::Int(number) => Json::Int(*number),
                        Detail::Text(text) => Json::Str(text.clone()),
                        Detail::Bool(flag) => Json::Bool(*flag),
                    },
                )
            })
            .collect();
        Json::Object(vec![
            ("code".to_string(), Json::Str(self.code.to_string())),
            ("path".to_string(), Json::Str(self.path.clone())),
            ("details".to_string(), Json::Object(details)),
            ("message".to_string(), Json::Str(self.message())),
        ])
    }

    /// Free text. Never used for identity.
    pub fn message(&self) -> String {
        let mut out = format!("{}: {}", self.code, describe(self.code));
        if !self.path.is_empty() {
            out.push_str(" at ");
            out.push_str(&self.path);
        }
        if !self.details.is_empty() {
            out.push(' ');
            let rendered: Vec<String> = self
                .details
                .iter()
                .map(|(key, value)| format!("{key}={}", value.render()))
                .collect();
            out.push('(');
            out.push_str(&rendered.join(", "));
            out.push(')');
        }
        out
    }
}

/// Sort by `(path, code)`, the order §1 requires for reporting.
pub fn sort(diagnostics: &mut [Diagnostic]) {
    diagnostics.sort_by(|a, b| a.path.cmp(&b.path).then_with(|| a.code.cmp(b.code)));
}

/// A short phrase per code. Prose only; the registry owns the meaning.
fn describe(code: &str) -> &'static str {
    match code {
        crate::codes::E_PLAN_001 => "unsupported format_version",
        crate::codes::E_PLAN_002 => "value has the wrong type or domain",
        crate::codes::E_PLAN_003 => "unknown field in a strict object",
        crate::codes::E_PLAN_004 => "document is not parseable",
        crate::codes::E_PLAN_005 => "canonical-form violation",
        crate::codes::E_PLAN_006 => "required field is absent",
        crate::codes::E_TARGET_001 => "target identity mismatch",
        crate::codes::E_TARGET_002 => "execution_mode mismatch",
        crate::codes::E_TARGET_003 => "extension is not enabled",
        crate::codes::E_TARGET_004 => "byte_order or address_width mismatch",
        crate::codes::E_DEF_001 => "definition cannot be loaded or does not match",
        crate::codes::E_DEF_002 => "definition namespace or version is not shipped",
        crate::codes::E_FORM_001 => "form_id is not in the pinned definition",
        crate::codes::E_OPERAND_001 => "operand kind or target_type does not match the form",
        crate::codes::E_OPERAND_002 => "operand count or role sequence mismatch",
        crate::codes::E_OPERAND_003 => "operand payload malformed for its kind",
        crate::codes::E_OPERAND_004 => "operand value does not fit the encoded field",
        crate::codes::E_RANGE_001 => "immediate outside the legal range",
        crate::codes::E_RANGE_002 => "displacement outside the legal range",
        crate::codes::E_RANGE_003 => "alignment requirement not met",
        crate::codes::E_RANGE_004 => "operand value is excluded by the slot's domain",
        crate::codes::E_LAYOUT_001 => "fragments overlap",
        crate::codes::E_LAYOUT_002 => "fragment gap or declared_size mismatch",
        crate::codes::E_LAYOUT_003 => "instruction does not match its fragment",
        crate::codes::E_LAYOUT_004 => "list order violates the contract",
        crate::codes::E_LAYOUT_005 => "layout needs computed padding",
        crate::codes::E_LAYOUT_006 => "section set is inconsistent",
        crate::codes::E_LAYOUT_007 => "instruction identity collides",
        crate::codes::E_LIMIT_001 => "declared image exceeds the resource limit",
        crate::codes::E_SYMBOL_001 => "symbol reference is undeclared",
        crate::codes::E_SYMBOL_002 => "symbol identity collides",
        crate::codes::E_SYMBOL_003 => "defined symbol has no resolvable location",
        crate::codes::E_FIXUP_001 => "fixup is incompatible with its context",
        crate::codes::E_FIXUP_002 => "fixup target has no address",
        crate::codes::E_FIXUP_003 => "computed fixup value is out of range",
        crate::codes::E_FIXUP_005 => "field descriptor is invalid",
        crate::codes::E_FIXUP_006 => "two writers patch the same bits",
        crate::codes::E_FIXUP_007 => "fixup pair is incomplete or inconsistent",
        crate::codes::E_FIXUP_008 => "fixup identity collides",
        crate::codes::E_FIXUP_009 => "fixup addend is not allowed by its kind",
        crate::codes::E_SIZE_001 => "encoded length differs from expected_size",
        crate::codes::E_BYTE_001 => "emitted bytes differ from expected_digest",
        crate::codes::E_VERSION_001 => "the format version cannot honour this feature",
        crate::codes::E_INTERNAL_001 => "internal invariant violated",
        _ => "unregistered code",
    }
}
