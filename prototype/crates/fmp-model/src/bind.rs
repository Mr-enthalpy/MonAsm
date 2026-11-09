//! Binding helpers: strict objects, typed accessors, and the two error mappings.
//!
//! A [`Fault`] is a structural finding with no policy attached. The plan binder
//! maps it to `E-PLAN-002/003/006`; the definition loader maps every fault to
//! `E-DEF-001`, because `07_definition_format.md` §9 says the definition is the
//! input and its load failures have their own code.

use crate::codes;
use crate::diagnostic::Diagnostic;
use crate::json::Json;

/// A structural fault, before it becomes a registry code.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Fault {
    Missing {
        path: String,
        field: String,
        object: &'static str,
    },
    Unknown {
        path: String,
        field: String,
        object: &'static str,
    },
    Type {
        path: String,
        expected: &'static str,
        found: String,
    },
    Domain {
        path: String,
        required: &'static str,
        found: String,
    },
}

impl Fault {
    pub fn path(&self) -> &str {
        match self {
            Fault::Missing { path, .. }
            | Fault::Unknown { path, .. }
            | Fault::Type { path, .. }
            | Fault::Domain { path, .. } => path,
        }
    }

    /// Map to a plan code: `E-PLAN-006`, `E-PLAN-003`, or `E-PLAN-002`.
    pub fn plan(&self) -> Diagnostic {
        match self {
            Fault::Missing {
                path,
                field,
                object,
            } => Diagnostic::new(codes::E_PLAN_006, path.clone())
                .with("field", field.as_str())
                .with("object", *object),
            Fault::Unknown {
                path,
                field,
                object,
            } => Diagnostic::new(codes::E_PLAN_003, path.clone())
                .with("field", field.as_str())
                .with("object", *object),
            Fault::Type {
                path,
                expected,
                found,
            } => Diagnostic::new(codes::E_PLAN_002, path.clone())
                .with("path_type", *expected)
                .with("found_kind", found.as_str()),
            Fault::Domain {
                path,
                required,
                found,
            } => Diagnostic::new(codes::E_PLAN_002, path.clone())
                .with("path_type", *required)
                .with("found_kind", found.as_str()),
        }
    }

    /// Map to `E-DEF-001`. The definition is the input, so there is no plan path
    /// to report; the JSON Pointer rides along in `reason` instead. `declared`
    /// and `actual` carry the digest pair and stay empty for a structural fault,
    /// so the detail key set is the same whichever half failed.
    pub fn definition(&self) -> Diagnostic {
        let reason = match self {
            Fault::Missing {
                field,
                object,
                path,
            } => {
                format!("{object} at {path:?} is missing `{field}`")
            }
            Fault::Unknown {
                field,
                object,
                path,
            } => {
                format!("{object} at {path:?} has unknown field `{field}`")
            }
            Fault::Type {
                expected,
                found,
                path,
            } => {
                format!("at {path:?}: expected {expected}, found {found}")
            }
            Fault::Domain {
                required,
                found,
                path,
            } => {
                format!("at {path:?}: expected {required}, found {found}")
            }
        };
        Diagnostic::new(codes::E_DEF_001, String::new())
            .with("declared", "")
            .with("actual", "")
            .with("reason", reason)
    }
}

impl From<Fault> for Diagnostic {
    fn from(fault: Fault) -> Self {
        fault.plan()
    }
}

/// Append one JSON Pointer segment, escaping `~` and `/`.
pub fn pointer(base: &str, key: &str) -> String {
    let mut out = String::with_capacity(base.len() + key.len() + 1);
    out.push_str(base);
    out.push('/');
    for ch in key.chars() {
        match ch {
            '~' => out.push_str("~0"),
            '/' => out.push_str("~1"),
            other => out.push(other),
        }
    }
    out
}

/// Append an array index.
pub fn pointer_index(base: &str, index: usize) -> String {
    format!("{base}/{index}")
}

/// A strict object view: closed field set, required fields, typed children.
pub struct Obj<'a> {
    entries: &'a [(String, Json)],
    path: String,
    role: &'static str,
}

impl<'a> Obj<'a> {
    pub fn new(
        path: impl Into<String>,
        role: &'static str,
        value: &'a Json,
    ) -> Result<Self, Fault> {
        let path = path.into();
        match value {
            Json::Object(entries) => Ok(Obj {
                entries,
                path,
                role,
            }),
            other => Err(Fault::Type {
                path,
                expected: "object",
                found: other.kind().to_string(),
            }),
        }
    }

    pub fn role(&self) -> &'static str {
        self.role
    }

    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn child(&self, field: &str) -> String {
        pointer(&self.path, field)
    }

    /// Reject members outside `allowed` (`E-PLAN-003`).
    pub fn closed(&self, allowed: &[&str]) -> Result<(), Fault> {
        for (key, _) in self.entries {
            if !allowed.contains(&key.as_str()) {
                return Err(Fault::Unknown {
                    path: self.path.clone(),
                    field: key.clone(),
                    object: self.role,
                });
            }
        }
        Ok(())
    }

    pub fn get(&self, field: &str) -> Option<&'a Json> {
        self.entries
            .iter()
            .find(|(name, _)| name == field)
            .map(|(_, value)| value)
    }

    /// A required member (`E-PLAN-006` when absent).
    pub fn req(&self, field: &str) -> Result<&'a Json, Fault> {
        self.get(field).ok_or_else(|| Fault::Missing {
            path: self.path.clone(),
            field: field.to_string(),
            object: self.role,
        })
    }

    /// A required member with its own path, for the common `req` + accessor pair.
    pub fn required(&self, field: &str) -> Result<(&'a Json, String), Fault> {
        let value = self.req(field)?;
        Ok((value, self.child(field)))
    }

    /// An optional member with its path.
    pub fn optional(&self, field: &str) -> Option<(&'a Json, String)> {
        self.get(field).map(|value| (value, self.child(field)))
    }
}

pub fn describe(value: &Json) -> String {
    match value {
        Json::Int(number) => format!("integer {number}"),
        other => other.kind().to_string(),
    }
}

pub fn string(value: &Json, path: String) -> Result<&str, Fault> {
    match value {
        Json::Str(text) => Ok(text),
        other => Err(Fault::Type {
            path,
            expected: "string",
            found: other.kind().to_string(),
        }),
    }
}

pub fn owned_string(value: &Json, path: String) -> Result<String, Fault> {
    string(value, path).map(str::to_string)
}

pub fn boolean(value: &Json, path: String) -> Result<bool, Fault> {
    match value {
        Json::Bool(flag) => Ok(*flag),
        other => Err(Fault::Type {
            path,
            expected: "boolean",
            found: other.kind().to_string(),
        }),
    }
}

pub fn integer(value: &Json, path: String) -> Result<i128, Fault> {
    match value {
        Json::Int(number) => Ok(*number),
        other => Err(Fault::Type {
            path,
            expected: "integer",
            found: other.kind().to_string(),
        }),
    }
}

pub fn u64_in(value: &Json, path: String, domain: &'static str) -> Result<u64, Fault> {
    let number = integer(value, path.clone())?;
    if (0..=u64::MAX as i128).contains(&number) {
        Ok(number as u64)
    } else {
        Err(Fault::Domain {
            path,
            required: domain,
            found: format!("integer {number}"),
        })
    }
}

pub fn i64_in(value: &Json, path: String, domain: &'static str) -> Result<i64, Fault> {
    let number = integer(value, path.clone())?;
    if (i64::MIN as i128..=i64::MAX as i128).contains(&number) {
        Ok(number as i64)
    } else {
        Err(Fault::Domain {
            path,
            required: domain,
            found: format!("integer {number}"),
        })
    }
}

pub fn bounded_u32(
    value: &Json,
    path: String,
    max: u32,
    domain: &'static str,
) -> Result<u32, Fault> {
    bounded_u32_range(value, path, 0, max, domain)
}

/// The same check with an explicit inclusive lower bound. A zero is a valid
/// integer, so "must be at least 1" is a domain rule, not a type rule.
pub fn bounded_u32_range(
    value: &Json,
    path: String,
    min: u32,
    max: u32,
    domain: &'static str,
) -> Result<u32, Fault> {
    let number = integer(value, path.clone())?;
    if (min as i128..=max as i128).contains(&number) {
        Ok(number as u32)
    } else {
        Err(Fault::Domain {
            path,
            required: domain,
            found: format!("integer {number}"),
        })
    }
}

pub fn array<'a>(value: &'a Json, path: String) -> Result<&'a [Json], Fault> {
    match value {
        Json::Array(items) => Ok(items),
        other => Err(Fault::Type {
            path,
            expected: "array",
            found: other.kind().to_string(),
        }),
    }
}
