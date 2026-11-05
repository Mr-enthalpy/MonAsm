# ADR-0058: the byte `mov` rows gain the no-displacement memory shape

- Status: accepted
- Date: 2026-11-06
- Settles: `X86-P35` (the `mod = 00` byte-memory rows for one
  register-only base, in all four byte-register windows)
- Supersedes: none
- Superseded by: none
- Revises: `ADR-0057` §Review triggers (its first item, the `mod = 00` byte
  rows); `EC-02` (the third displacement shape now reaches the byte rows)

## Context

`EC-02` freezes three displacement shapes — none (`mod = 00`), `disp8`
(`mod = 01`) and `disp32` (`mod = 10`) — and says the no-displacement shape is
a *third legal encoding*, not a zero value. Every other reachable family
carries all three: the SSE rows took `mod = 00` in `0.12.0` (`ADR-0039`), the
EVEX rows in `0.22.0` (`ADR-0049`), and the word/byte `mov` rows only ever
took `disp8`/`disp32` (`0.3.0`, `0.17.0`, `0.19.0`, `0.30.0`). No version has
`movb (%rax), %al`, which `llvm-mc` encodes as two bytes.

`EXP-0060` measures the shape and four facts come out:

1. **The shape is two bytes, one shorter than either displacement row.**
   `movb (%rax), %al` is `8a 00`: the opcode at `[0,8]` and `ModRM` at
   `[8,8]` with `mod = 00`, `reg = 000` and `r/m = 000`. The existing
   `disp8` row beside it is three bytes (`8a 40 00`), so a plan that wants
   the shorter encoding must name a different row (`INV-02`).
2. **`r/m = 101` is not a base at this `mod`.** `movb (%rbp), %al` is
   `8a 45 00` — `llvm-mc` writes `mod = 01` with a zero displacement byte,
   because at `mod = 00` the value `101` means RIP-relative `disp32`. So
   `%rbp` and `%r13` cannot inhabit these rows and the base slot excludes
   `5` and `13` (`E-RANGE-004`).
3. **`r/m = 100` would need a `SIB` byte the row does not have.**
   `movb (%rsp), %al` is `8a 04 24` and `movb (%r12), %al` is
   `41 8a 04 24`; both carry a `SIB` byte, so the plain-base rows exclude
   `4` and `12` as well. Their rows are a later slice.
4. **The four register windows and their prefixes are unchanged.** The low
   window has no `REX` byte (`8a 00`, two bytes); the high window puts
   `reg = 100`–`111` in the same field (`8a 20`, two bytes); the `REX = 40`
   window relabels `4`–`7` and is three bytes (`40 8a 20`); the extended
   window sets `REX.R` and reaches `%r8b`–`%r15b` (`44 8a 00`, three bytes),
   growing to `45` when the base is `%r8`–`%r15` (`movb (%r8), %r8b` is
   `45 8a 00`). `movb (%r15), %r15b` is `45 8a 3f` and `movb (%rax), %dil` is
   `40 8a 38`, so the four-bit register field is exercised at both ends.

The high-byte window also cannot take `%r12`: `movb (%r12), %ah` needs the
`REX.B` byte that renames `%ah` to `%spl`, and `llvm-mc` rejects the source
outright — the same `EC-36` rule the `disp8`/`disp32` rows already obey.

## Decision

**`0.31.0` appends eight rows: load and store at `mod = 00`, one per
byte-register window, over the plain four-bit base window minus `%rsp`,
`%rbp`, `%r12` and `%r13`.**

| Register window | `form_id` (load) | `form_id` (store) | Template | Length |
|---|---|---|---|---|
| `%al`–`%bl` | `x86:mov/r8-base/legacy` | `x86:mov/base-r8/legacy` | `8a 00` / `88 00` | 2 |
| `%ah`–`%bh` | `x86:mov/r8h-base/legacy` | `x86:mov/base-r8h/legacy` | `8a 20` / `88 20` | 2 |
| `%spl`–`%dil` | `x86:mov/r8-base-rex/legacy` | `x86:mov/base-r8-rex/legacy` | `40 8a 20` / `40 88 20` | 3 |
| `%r8b`–`%r15b` | `x86:mov/r8-ext-base/legacy` | `x86:mov/base-r8-ext/legacy` | `44 8a 00` / `44 88 00` | 3 |

Four properties follow:

- **The register slot keeps each window's existing width and exclusion.** The
  low and high rows use the three-bit field at `[11,3]`, excluding `4`–`7` and
  `0`–`3` respectively — the same disjoint split `0.17.0` pinned
  (`ADR-0045`). The `REX = 40` row moves the field to `[19,3]` and keeps the
  `0`–`3` exclusion; the extended row is `[2,1]` plus `[19,3]` with `0`–`7`
  excluded.
- **The base slot excludes four values, not two.** `4` (`%rsp`) and `12`
  (`%r12`) would force a `SIB` byte, and `5` (`%rbp`) and `13` (`%r13`)
  collide with the `r/m = 101` RIP-relative meaning of `mod = 00`. A plan
  naming any of the four is `E-RANGE-004`; those bases keep their
  `disp8 = 0` rows.
- **The three-bit rows keep the three-bit base.** The low and high windows
  have no `REX` byte, so their base slot is `[8,3]` with `4` and `5`
  excluded and cannot reach `%r8`–`%r15` at all. Base `8` there is
  `E-OPERAND-004`.
- **There is no `disp` slot.** The row has no displacement field, so a `disp`
  operand is `E-OPERAND-002` rather than a silently ignored zero — the same
  rule `ADR-0049` set for the EVEX no-displacement rows.

## Consequences

- `0.31.0` is a 275-form document, byte-reproducing every `0.30.0` row.
- Its positive fixture `X86-P35-gpr8-mov-mem-nodisp` has eight instructions
  and 20 bytes: one per row, two bytes each for the two `REX`-less windows
  and three for the two prefixed ones. The bases span the legal set (`%rax`,
  `%rcx`, `%rdx`, `%rbx`, `%rsi`, `%rdi`, `%r8`, `%r9`) and the registers
  span each window's ends (`%al`, `%cl`, `%ah`, `%bh`, `%dil`, `%sil`,
  `%r8b`, `%r15b`).
- Negatives pin the version boundary in both directions (`N01bo`, `N01bp`),
  the high-byte kind on a low-window row (`N02aw`), a `disp` operand on a row
  with no displacement slot (`N02ax`), base `8` on a three-bit row
  (`N14ae`), `%rbp` and `%r13` on the `mod = 00` rows (`N16aj`, `N16ak`), and
  `%rsp` and `%r12` there too (`N16al`, `N16am`).
- `EC-02` is revised in place: the byte `mov` family now carries all three
  displacement shapes. No new `EC` row appears and no row is renumbered.
- No schema, loader or materializer change: the rows are two- and three-slot
  forms of the shape `0.12.0` already used for the SSE no-displacement rows.

## Alternatives rejected

- **Let the `disp8` row accept a missing displacement operand and shorten
  itself.** The row's length would then depend on the presence of an operand,
  which is exactly the implicit form choice `INV-02` forbids; the two
  encodings differ by a byte and by the `mod` field, so they are two rows.
- **Fold `%rbp`/`%r13` into the `mod = 00` rows by clearing `mod`.** A base
  slot cannot rewrite `ModRM.mod`, because the materializer would then be
  choosing a length from a value (`INV-04`). `llvm-mc` itself writes
  `8a 45 00` and not `8a 05 …`, which shows the shape is not available.
- **Take the `%rsp`/`%r12` `SIB` rows in this slice.** They carry a fourth
  template byte and their own disjoint window (`4`/`12` against the plain
  rows' exclusion of the same two values), and the high-byte window cannot
  have the `%r12` half at all. One shape per ADR.
- **Add the 16-bit and 32/64-bit `mov` rows at the same time.** The width
  axis is already a separate set of ADRs (`ADR-0028`, `ADR-0045`), and the
  16-bit rows would put `66` in front of the same two bytes.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| `8a 00` / `88 00` at two bytes, `40 8a 20` / `44 8a 00` at three | `llvm-mc -show-encoding`, `EXP-0060` §1 | high |
| `%rbp` at `mod = 00` is written as `mod = 01` with a zero byte | `llvm-mc -show-encoding`, `EXP-0060` §2 | high |
| `%rsp`/`%r12` spend a `SIB` byte, so these rows exclude them | `llvm-mc -show-encoding`, `EXP-0060` §3 | high |
| the four register windows and their prefix lengths are unchanged | `llvm-mc -show-encoding`, `EXP-0060` §1, §4 | high |
| `%ah` is illegal with any `REX` prefix | `llvm-mc` rejection, `EXP-0060` §4 | high |

## Review triggers

- The `%rsp`/`%r12` `SIB` rows at `mod = 00` are attempted.
- A `SIB` index or scale is requested at byte width.
- The `0x67` address-size prefix is attempted.
- A symbol or relocation in the displacement is requested.
- `moffs` for the byte width is requested.
- The APX `d5` register window is attempted.
- A width other than eight bits takes the no-displacement shape.
