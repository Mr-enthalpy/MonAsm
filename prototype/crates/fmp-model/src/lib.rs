//! Plan and definition model for FMP v0.
//!
//! The contract is `docs/fmp-v0/01_contract.md` (plan), `03_fixup_model.md`
//! (patches) and `07_definition_format.md` (the definition artifact). This crate
//! owns parsing and structure; it never emits a byte and never chooses between
//! legal encodings.
//!
//! Three rules shape the code:
//!
//! - **No hidden state.** Objects keep document order, lists are never sorted
//!   implicitly, and no `HashMap` is on a path that can affect bytes or
//!   diagnostics.
//! - **Exact integers.** Numbers are `i128` after parsing; a float or an
//!   exponent is rejected rather than normalised.
//! - **Structure here, semantics elsewhere.** Membership in an enum of the
//!   *contract* (target identity, fixup kind, mode) is a semantic question and
//!   is answered in `fmp-validate` with the registry code that names it. Only the
//!   closed field sets and the types of the document live here.
//!
//! ## Closed execution objects (`ADR-0127`)
//!
//! A loaded [`definition::Definition`] is half of an execution credential, so
//! its fields are private and it has no public constructor and no `Clone`. The
//! only way to obtain one is [`definition::read`] or [`Registry::load_dir`]; the
//! registry hands out `Arc<Definition>`, so sharing cannot become mutation.
//!
//! The negative assertion is a `compile_fail` doctest, because the property is
//! "this program cannot be written", not "this call returns an error":
//!
//! ```compile_fail
//! use fmp_model::definition::read;
//!
//! let text = r#"{"definition_format":"fmp-def/0.1","namespace":"monasm.isa.x86","version":"0.1.0","target_identity":{"isa_family":"x86","isa_variant":"x86-64","execution_mode":"64","enabled_extensions":[],"byte_order":"little","address_width":64},"forms":[{"form_id":"x86:mov/rm64/legacy","template":"4889c0","slots":[{"role":"dest","kind":"x86.gpr64","target_type":"rm64","from":"reg_number","modifiers":[],"placements":[{"bit_offset":16,"width":3}]}]}]}"#;
//! let mut definition = read(text.as_bytes()).expect("the table loads");
//! definition.forms = Vec::new();
//! ```
//!
//! ```compile_fail
//! use fmp_model::definition::Definition;
//!
//! let _definition = Definition {
//!     definition_format: String::new(),
//!     namespace: String::new(),
//!     version: String::new(),
//!     target: unimplemented!(),
//!     forms: Vec::new(),
//!     digest: String::new(),
//! };
//! ```
//!
//! The literal names every field, so the only reason it can fail is the private
//! field access. An incomplete literal (`Definition { forms: Vec::new() }`)
//! would also fail with all fields public, which is why it was not evidence.
//!
//! The positive control uses the same import path and the public accessors, so
//! the two failures above cannot be "the import was wrong":
//!
//! ```
//! use fmp_model::definition::read;
//!
//! let text = r#"{"definition_format":"fmp-def/0.1","namespace":"monasm.isa.x86","version":"0.1.0","target_identity":{"isa_family":"x86","isa_variant":"x86-64","execution_mode":"64","enabled_extensions":[],"byte_order":"little","address_width":64},"forms":[{"form_id":"x86:mov/rm64/legacy","template":"4889c0","slots":[{"role":"dest","kind":"x86.gpr64","target_type":"rm64","from":"reg_number","modifiers":[],"placements":[{"bit_offset":16,"width":3}]}]}]}"#;
//! let definition = read(text.as_bytes()).expect("the table loads");
//! assert_eq!(definition.namespace(), "monasm.isa.x86");
//! assert_eq!(definition.version(), "0.1.0");
//! assert!(definition.digest().starts_with("sha256:"));
//! ```

#![forbid(unsafe_code)]

pub mod bind;
pub mod canonical;
pub mod codes;
pub mod definition;
pub mod diagnostic;
pub mod identity;
pub mod json;
pub mod plan;

pub use definition::{Definition, Form, Registry, Slot, SlotFrom};
pub use diagnostic::Diagnostic;
pub use identity::ParsedPlanIdentity;
pub use plan::Plan;
