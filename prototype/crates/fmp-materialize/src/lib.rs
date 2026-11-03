//! Deterministic encoding and fixup execution for FMP v0.
//!
//! Encodes only forms named by a frozen plan, then compares the emitted length
//! with `expected_size`. No selection, relaxation, expansion, or padding.

#![forbid(unsafe_code)]
