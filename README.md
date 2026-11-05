# MonAsm

A deterministic materializer for a **Frozen Machine Plan (FMP)**.

FMP is the contract between an upstream planner and this repository. The planner
is responsible for instruction selection, operand legalization, encoding-form
selection, layout, and fixup planning. The materializer validates a frozen plan
and executes it: it emits bytes and fixup records, and rejects anything it cannot
execute exactly as written.

The materializer has no planning authority. That is the whole point.

## Status

**Phase 3 in progress on x86-64, AArch64 and RV64.** Gate G0 (oracle toolchain) and
G1 (encoder boundary audit) passed. The audit found that XirAsm's x86 path makes
four independent encoding decisions the caller cannot address, that its RISC-V
path is the only form-addressable entry point, and that AArch64 exists solely as a
40.9 MB interpreted Meta-language tree. Thirteen contract-level decisions are
settled (OD-01, OD-02, OD-03, OD-04, OD-06, OD-07, OD-09, OD-10, OD-11, OD-12,
OD-13, OD-14, OD-15); ADR-0004 makes `form_id` the only encoding selector, ADR-0005
takes AArch64 knowledge from the Arm MRS, ADR-0006 pins the MRS packaging by hash
and licence, ADR-0007 takes RV64 knowledge from the UDB resolved spec, ADR-0008
makes a memory operand one operand per encoded field, ADR-0009 gives a slot a
closed `excluded` list, ADR-0010 makes an RV64 low half name its high half,
ADR-0011 makes AArch64 `add ..., lsl #12` a form rather than a slot scale,
ADR-0012 makes an AArch64 condition a typed operand rather than sixteen forms,
ADR-0013 makes AArch64 addressing kinds forms and the offset field content,
ADR-0014 makes an AArch64 `movz` lane a form with `imm16` as field content,
ADR-0015 makes an AArch64 shift keyword a form with the amount as field content,
ADR-0016 makes an AArch64 extend keyword a form with the amount as field
content and a closed excluded tail, ADR-0017 makes an AArch64 mnemonic a
form family (`sub` repeats the `add` shapes with the node's `op = 1`), and
ADR-0018 makes the flag-setting mnemonic a form family too (`adds`/`subs`
repeat the shapes with the node's `S = 1`), and ADR-0019 makes the 32-bit width
a form family (`add`/`sub`/`adds`/`subs` repeat the shapes on the `sf = 0`
nodes, with every register slot `w32`), ADR-0020 makes the extended-register
mnemonic a form family too (`sub`/`adds`/`subs` repeat the eight `add` extend
rows with the node's `op`/`S` fixed), ADR-0021 makes `cmp`/`cmn` a separate
two-operand alias family (the `subs`/`adds` row with `Rd` pinned to 31 and the
destination dropped), ADR-0022 completes the store half of the addressing
kinds (the load `imm9` layouts with `opc = 00` and the stored register as `src`),
ADR-0023 makes the literal load a row with `dest`/`target` and no base register,
and ADR-0024 makes register offset a form family (`option` fixes the index width
and keyword, `S` is the only scale carrier), ADR-0025 repeats it at `size =
10` where `S = 1` is `#2`, and ADR-0026 repeats the `movz` lane family for
`movk`/`movn`, whose `opc` is fixed by the node and whose `imm16` operand is the
raw field, and ADR-0027 makes an x86 RIP-relative memory operand a form with no
base register (`mod = 00`, `r/m = 101`, `disp32` as a `target` operand), and
ADR-0028 makes x86 base+displacement eight rows across four shapes (load/store ×
`disp8`/`disp32` × base-in-`r/m`/`%rsp`-fixed), with the SIB byte and `mod`
fixed by the form, ADR-0029 makes the operand-size prefix and the high-byte
register set form facts (five rows: two 16-bit directions, the high-byte row and
the low-byte pair split by REX), and ADR-0030 makes the x86 encoding family a
form fact (one `movaps` shape in `/legacy`, `/vex` and `/evex`, with the prefix
as template and `xmm` registers 0–7 only), ADR-0033 makes a GPR operand four
bits with the high bit placed in the form's `REX.R`/`REX.B` (the six 64-bit
register-direct rows reach `r8`–`r15` from `0.6.0`), ADR-0034 does the same
for a memory base and gives `%r12` its own SIB rows (the base+disp rows reach
`r8`–`r15` from `0.7.0`), and ADR-0035 makes the SIB index and scale operands
(`REX.X` extends the index, `4` is the "no index" value, and the scale is the
two-bit field content `0…3` from `0.8.0`), and ADR-0036 makes the SSE memory
operand one family: `movaps`/`vmovaps` load/store as twelve rows across
`legacy`/`vex`/`evex`, with the base and the `xmm` register at three bits in
all three (the legacy templates have no `REX`, `C5` has no `B`, and EVEX
inverts `B̄`/`R̄`), and the EVEX `disp8` carrying the compressed field content
(`disp8x16`, unit 16) rather than a byte offset, and ADR-0037 takes the SSE base
to `r8`–`r15` through a window per family: the four EVEX rows widen in place
(their prefix already carries `B̄`), while legacy and VEX add eight
`-base-ext` rows because reaching the high base adds a `REX` byte or a third
VEX byte, and a placement's new `invert` flag writes `B̄` complemented. ADR-0038
takes the SSE register to `xmm8`–`xmm15` through a window per family: the EVEX
register-direct pair and the VEX/EVEX memory rows widen in place (`R̄` at bit 15,
`B̄` at bit 13 for the EVEX source), while legacy adds three `REX.R`/`REX.B`
register windows and four memory rows, and VEX adds a `C5 78 29` source window
and a `C4 41 78 28` both-high window; the two legal VEX spellings of a high
source make the opcode-29 row a pinned `EC-09` decision. ADR-0039 adds the
memory shape with no displacement: `0.12.0` carries twelve `mod = 00` rows
across the three families, because `0f 28 00` (three bytes) and `0f 28 40 00`
(four bytes, `disp8 = 0`) decode as the same instruction and the assembler
canonicalizes a zero displacement to the short form; `%rsp`/`%r12` (a `SIB`
byte) and `%rbp`/`%r13` (`r/m = 101` is RIP) stay outside and must name the
`disp8` row with `0`. ADR-0040 takes the EVEX register to `xmm16`–`xmm31` by
widening the `xmm` slot of the seven EVEX rows from four bits to five in place:
bit 4 is the inverted `R̄'` for `ModRM.reg` and, in register form, the inverted
`X̄` for `ModRM.rm` (`vmovaps %xmm31, %xmm30` is `62 01 7c 08 28 f7`). No row is
added and no length changes; the memory rows have no `SIB` field, so `X̄` keeps
its template value there, and legacy/VEX have no second extension bit at all.
ADR-0041 makes width a form fact: `0.14.0` adds five register-direct `ymm`/`zmm`
rows and the kinds `x86.ymm`/`ymm` and `x86.zmm`/`zmm`. The mnemonic is the same
at every width, so only the prefix field changes (`L` in VEX, `L'L` in EVEX), and
the three VEX.256 windows repeat the `xmm` windows: a high destination in `R̄`, a
high source through opcode 29, both-high through the three-byte `C4`.
ADR-0042 turns the EVEX compressed-displacement unit into a form fact: `0.15.0`
adds twelve memory rows — the six `0.13.0` `xmm` memory shapes at `ymm` and
`zmm` — and revises `EC-39` so `N` is the row's `target_type`
(`disp8x32`/`disp8x64`), never a division. The same field content is `16`, `32`
or `64` bytes under `P2 = 08`/`28`/`48`, so `4064` is content `127` at `ymm`
and `4096` promotes to `disp32` instead of truncating.
ADR-0043 closes the VEX width axis as pure coverage: `0.16.0` adds twelve
VEX.256 memory rows at `L = 1`, the two base windows (`c5 fc …` for a low base,
`c4 c1 7c …` for `r8`–`r15`) each with the `disp8`, `disp32` and `mod = 00`
pairs. VEX has no compression, so `32(%rax)` is the plain signed byte `20` and
`128` names the `disp32` row; no `EC` row is added or revised.
ADR-0044 carries the prefix and byte-register facts into memory at 8 and 16
bits: `0.17.0` adds sixteen `mov` rows — four word (`66 8b`/`66 89`) and twelve
byte in the three `0.4.0` register sets (REX-less low `88`/`8a`, high byte, and
`40`-prefixed `spl`–`dil`), each with `disp8` and `disp32`. The `0x66` byte is
template byte 0 ahead of any REX byte, every base stays the three-bit window 0–7
minus `%rsp`, and no `EC` row is added or revised.
Thirty-six definition documents are frozen and oracle-verified; the materializer
and its fixture gate are implemented.

| Area | State |
|---|---|
| Contract (`docs/fmp-v0/01_contract.md`) | draft, fields marked `TBD` where unproven |
| Schema (`schema/fmp-v0.schema.json`) | draft, examples validate |
| Definitions (`definitions/`) | x86-64 `0.1.0` (7 forms), `0.2.0` (9 forms), `0.3.0` (17 forms), `0.4.0` (22 forms), `0.5.0` (25 forms), `0.6.0` (25 forms), `0.7.0` (29 forms), `0.8.0` (33 forms), `0.9.0` (45 forms), `0.10.0` (53 forms), `0.11.0` (62 forms), `0.12.0` (74 forms), `0.13.0` (74 forms), `0.14.0` (79 forms), `0.15.0` (91 forms), `0.16.0` (103 forms) and `0.17.0` (119 forms), aarch64 `0.1.0` (4 forms), `0.2.0` (5 forms), `0.3.0` (6 forms), `0.4.0` (11 forms), `0.5.0` (15 forms), `0.6.0` (18 forms), `0.7.0` (26 forms), `0.8.0` (32 forms), `0.9.0` (44 forms), `0.10.0` (68 forms), `0.11.0` (92 forms), `0.12.0` (132 forms), `0.13.0` (135 forms), `0.14.0` (136 forms), `0.15.0` (152 forms), `0.16.0` (168 forms) and `0.17.0` (176 forms), rv64 `0.1.0` (7 forms) and `0.2.0` (8 forms) frozen, digests pinned |
| Prototype (`prototype/`) | workspace compiled; all three slices materialize from the plan |
| Oracles (`tools/oracle/`) | planned; `llvm-mc` (± `ld.lld`) drives the experiments |
| Evidence (`research/evidence/`) | index, XirAsm snapshot, EXP-0001…EXP-0046 |

Read `docs/STATUS.md` for the current phase, gate status, and next action.

## Reading order

1. `AGENTS.md` — working constraints and the eight invariants.
2. `docs/fmp-v0/00_directive.md` — immutable research directive (source of truth).
3. `docs/fmp-v0/01_contract.md` — the FMP v0 contract.
4. `docs/STATUS.md` — where the work stands.

## Repository layout

```text
docs/
  STATUS.md                  phase, gates, next action, open decisions
  glossary.md                terms used across the contract set
  fmp-v0/                    contract, encoding choices, fixups, errors, matrix
  adr/                       architecture decision records
schema/                      JSON Schema for FMP v0 (draft)
definitions/{x86_64,aarch64,rv64}/  pinned encoding tables, one target each
fixtures/{x86_64,aarch64,rv64}/ plan + expected bytes + oracle metadata
research/evidence/           source index, pinned revisions, experiment records
research/external/           disposable snapshots (gitignored, pinned by SHA)
prototype/                   Rust workspace (materializer, Phase 3)
tools/oracle/                temporary oracle wrappers (llvm-mc, binutils)
tools/check_ids.py           documentation consistency check
tools/check_definition.py    definition table <-> document consistency check
tools/check_mrs.py           verifies the pinned Arm MRS drop (ADR-0006)
tools/check_rv64_source.py   verifies the pinned UDB drop (ADR-0007)
```

## Invariants at a glance

INV-01 no implicit instruction selection · INV-02 no implicit encoding-form
selection · INV-03 no implicit expansion · INV-04 no implicit layout change ·
INV-05 no hidden environment dependency · INV-06 no metaprogramming ·
INV-07 strict rejection · INV-08 replayable and traceable.

Each invariant has a registry row in `docs/fmp-v0/01_contract.md` and must map to
an executable test before it can be marked verified.

## Checking the docs

```bash
python tools/check_ids.py
```

The check verifies that IDs (`INV-*`, `N*`, `EXP-R*`, `AC-*`, `EC-*`, `OD-*`,
`E-*`) are declared exactly once in their registry document, that references
resolve, and that every declared negative test appears in the validation matrix.

## Dependency posture

XirAsm and LLVM are **temporary**: oracles, knowledge sources, and audit targets
(see `docs/adr/0001-route-c-self-owned-core.md`). The product path must build and
run with both directories deleted.

## License

Apache License 2.0. See `LICENSE`.
