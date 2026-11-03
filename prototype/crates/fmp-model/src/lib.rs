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

#![forbid(unsafe_code)]

pub mod bind;
pub mod canonical;
pub mod codes;
pub mod definition;
pub mod diagnostic;
pub mod json;
pub mod plan;

pub use definition::{Definition, Form, Registry, Slot, SlotFrom};
pub use diagnostic::Diagnostic;
pub use plan::Plan;
