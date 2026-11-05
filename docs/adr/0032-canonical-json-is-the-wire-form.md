# ADR-0032: Canonical JSON is the v0 wire form

- Status: accepted
- Date: 2026-11-05
- Settles: `OD-08` (canonical wire form)
- Supersedes: none
- Superseded by: none

## Context

`OD-08` asked whether the replayable wire form is canonical JSON, a deterministic
binary encoding, or both. The contract already needs one byte representation for
two jobs: the definition digest (`OD-06`) and the plan fingerprint
(`01_contract.md` §12). `canonical.rs` implements one canonical form — keys
sorted by code point, no insignificant whitespace, UTF-8 without BOM, integers
only, no duplicate keys — and its test cross-checks the escaping against Python's
`json.dumps(..., sort_keys=True, separators=(",", ":"))`.

The evidence needed was plan size and round-trip determinism for the three
slices. `EXP-R4` (`EXP-0033` §3) measures the round trip on all 38 positive
fixtures, once through canonical JSON and once through the pretty form.

## Decision

**A. Canonical JSON is the one v0 wire form.**

- Replay records, fingerprints and definition digests are computed over the
  canonical bytes of the parsed value. Two documents with the same value have the
  same canonical bytes; a formatting change moves nothing.
- The reader accepts any valid JSON spelling of a plan value. A plan written with
  two-space indentation and a plan written with no whitespace materialize to the
  same artifact (`EXP-R4`), so requiring canonical bytes on input would add a
  rejection that changes no emitted byte.
- The wire form is a *value* form, not a byte form: key order in the source
  document is irrelevant, duplicate keys are rejected (`E-PLAN-004`) rather than
  resolved last-wins, and a BOM is `E-PLAN-005`.
- A deterministic binary transport is out of scope for `fmp/0.1`. If one is added
  later it is a new `format_version` with its own reader, never a second
  accepted spelling of the same version.

The measured reference is the x86 `X86-P9-sse-vex-evex` artifact: 13 bytes, no
records, fingerprint
`sha256:5e6bc559fc0356ef325018ffcc7e0a2a7c0cfb42bf3fd2c79420ccd177880a37`,
canonical artifact SHA-256
`da97dcaad805b973984a92d2ffb933a82a407b1a4cc9a1aa87bfc8a9c715c660`, equal for the
direct, canonical-round-trip and pretty-round-trip runs.

## Consequences

- `01_contract.md` §12 gains the wire-form statement; §14 no longer lists
  `OD-08`.
- `AC-07` cites `EXP-R4`; `EXP-R3` remains `unverified`, so this ADR does not
  claim cross-host determinism.
- No code change: the reader and canonicalizer already separate the value from
  its spelling.
