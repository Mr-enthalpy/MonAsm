# ADR-0122: numeric and resource limits fail before arithmetic, not after

- Status: accepted
- Date: 2026-11-10
- Settles: where `fmp/0.1` bounds a number, an allocation and a domain
- Supersedes: none
- Superseded by: none
- Revises: `04_errors.md` §2 (`E-LIMIT-001`, `E-PLAN-002`, `E-SIZE-001`,
  `E-DEF-001` rows and §2.4 counts), `01_contract.md` §6, §7 and §13,
  `03_fixup_model.md` §3, `06_validation_matrix.md` (`N05`, `N25`); adds
  `N05b`, `N25a` and `N25b`

## Context

Four plan-supplied numbers reached arithmetic that assumed a value the contract
never enforced. Each one is a *plan* field, so each one is an input boundary.

1. **`field_descriptor[].width` and `range_constraint.bits` admitted 0.** The
   binder accepted `0` for both because both are `u31`-style domains with only an
   upper bound. A zero-width range is a range that writes nothing; a zero-bit
   constraint is a range whose bounds are `-(1 << -1)` … `1 << -1`. On `47a383b`
   a fixup on a register-only form with an empty descriptor and `bits: 0`
   panicked in `fmp-materialize` (`attempt to subtract with overflow` at
   `constraint.bits - 1`). The same plan is why the check has to be at read time:
   by the time a validator could see it, the arithmetic is the next statement.
2. **The definition binder summed template bits in `u32`.** `form.size()` is
   `len(template) as u64`, but `bind_form` computed `(template.len() as u32) * 8`
   and each placement end as `offset + width` in `u32`. A definition with a
   template large enough to wrap, or a placement at `bit_offset: u32::MAX`, would
   compute a small "end" and pass the bounds check. Definitions are trusted
   inputs only in the sense that they are pinned; a pin does not make an
   overflow benign, and the loader is the only place that can refuse them.
3. **`expected_size` was used as a bit bound before it was compared.** The
   descriptor check computed `instruction.expected_size * 8`. On `47a383b`, a
   plan with `expected_size: 2305843009213693952` (2^61) panicked there
   (`attempt to multiply with overflow`), because 2^61 × 8 = 2^64. The value was
   never constrained to the form's size before the multiplication, and
   `01_contract.md` §13 says steps 1–7 are static checks that emit no bytes — a
   static check that panics is not a check.
4. **`declared_size` chose an allocation.** `emit` called
   `bytes.resize(section.declared_size as usize, 0)` with no bound. On `47a383b`
   a plan with a single `fill` fragment of 2^63 bytes panicked in `raw_vec`
   (`capacity overflow`). A smaller but still enormous value would have asked the
   host for it and failed there, which is worse: the plan's failure would depend
   on the machine.

## Decision

1. **A descriptor width and a range width are at least 1.** `field_descriptor[i]
   .width` is `1…64` and `range_constraint.bits` is `1…64`; `0` is
   `E-PLAN-002` at the field's path with `path_type = u7`,
   `found_kind = integer 0`. The binder gains a lower bound instead of a second
   check, so the rule is the type and cannot be skipped by a later path.
2. **Definition arithmetic is wide and explicit.** The template bit count is
   computed in `u64`, a template wider than `u32::MAX` bits is `E-DEF-001`
   (`template has more bits than the slot model can address`), and each
   placement end is `u64`, so a placement can never wrap. The error is the
   loader's (`E-DEF-001`), because the definition is the input.
3. **`expected_size` equals the form's encoded size, statically.** Step 6 emits
   `E-SIZE-001` at `/instructions/<i>/expected_size` with
   `instruction_id`, `expected`, `actual` when they differ, and the descriptor
   bound uses `form.size() * 8` rather than `expected_size * 8`. The diagnostic
   identity is unchanged from the emission-time check it replaces, so `N05`
   still records the same code, path and keys; only the phase moves.
4. **The image has a fixed ceiling.** The sum of `declared_size` over
   `section_order` is computed in `u128` and compared with 64 MiB
   (67,108,864 bytes). Over the ceiling is `E-LIMIT-001` at
   `/output_contract/section_order` with `limit` (integer) and `actual` (text).
   `emit` uses `try_reserve_exact` and reports an internal failure instead of
   letting `resize` abort, so even a host that cannot provide 64 MiB gets a
   diagnostic rather than a process death.
5. **The ceiling is a format property, not an environment input.** 64 MiB is
   stated here and in `01_contract.md` §6; it is not read from the host, a flag
   or an environment variable, so two runs on two machines agree on accept or
   reject (`INV-05`).

## Consequences

- Three reachable panics become diagnostics: `bits: 0`, an overflowing
  `expected_size`, and an over-sized image.
- `N05b` is the `expected_size` fixture. It records two diagnostics —
  `E-LAYOUT-003` (the fragment size disagrees with the instruction's stated size)
  and `E-SIZE-001` — because a plan that states 2^61 bytes for a 5-byte form is
  inconsistent in both places. The complete set is recorded rather than
  suppressed.
- `N25a`/`N25b` are `read`-phase negatives: the reader refuses the plan before
  any definition is loaded, which is the strongest form of the rule.
- `N24l` is the limit fixture: a non-image-backed `.bss` of 67,108,865 bytes, so
  the only fault is the total and no fragment can explain it away.
- The error registry grows to 44 active codes and 39 fixture-covered codes
  (`04_errors.md` §2.4). `E-LIMIT-001` is the only addition.
- A future slice that needs a larger image must change the constant *and* the
  contract text; it cannot be relaxed by a plan option.

## Alternatives rejected

- **Check `width == 0` / `bits == 0` in the validator.** Rejected: the reader is
  the layer that owns the plan grammar, and a plan must not bind a value the
  model cannot represent. `01_contract.md` §13 step 1 is the parse-and-schema
  step; a domain rule belongs there.
- **Clamp `expected_size` to `form.size()`.** Rejected: that is a silent repair
  of a plan that states the wrong size, and `INV-07` forbids it. The mismatch is
  reported.
- **Keep the emission-time size check and clamp the bit bound.** Rejected: it
  leaves `expected_size * 8` running on an unvalidated number, which is the
  panic in the first place.
- **Make the image limit an environment variable or a CLI flag.** Rejected:
  acceptance would then depend on the host (`INV-05`), and two replays of one
  plan could disagree.
- **Use `resize` and let the allocator fail.** Rejected: the failure mode is a
  process abort with no diagnostic, which the replay requirement
  (`INV-08`) cannot record.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `bits: 0` + empty descriptor on a register-only row panics at `constraint.bits - 1` | `fmp materialize` built from `47a383b`: `thread 'main' panicked ... attempt to subtract with overflow` at `fmp-materialize/src/lib.rs:745` | high |
| `expected_size: 2^61` panics at `expected_size * 8` | the same build: `attempt to multiply with overflow` at `fmp-validate/src/lib.rs:1213` | high |
| A 2^63-byte `fill` section panics in `raw_vec` | the same build: `capacity overflow` in `alloc/raw_vec/mod.rs` | high |
| The same plan is now `E-LIMIT-001` with `actual = 9223372036854775808`, `limit = 67108864` | `fmp materialize` on the current tree | high |
| `N05` keeps its code, path and detail keys | `N05-expected-size-mismatch.expected-error.json` unchanged and green | high |
| `N05b` is two diagnostics | `fmp materialize` on the fixture; recorded in its expected set | high |
| The three fixes reject nothing that ships | `cargo test --workspace` green | high |

## Review triggers

- A definition needs a template wider than 2^29 bytes (the `u32::MAX`-bit
  guard), or a placement beyond `u32::MAX`.
- A positive vector declares an image over 64 MiB; the ceiling is then wrong for
  the corpus and must be re-decided, not raised silently.
- A new plan field is used in arithmetic before it is validated. That is the same
  defect as `expected_size * 8` and needs its own decision.
