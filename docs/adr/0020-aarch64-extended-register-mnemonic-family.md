# ADR-0020: the extended-register `sub`/`adds`/`subs` rows reuse the `add` shapes, and 31 in `Rd` is `sp` only where the node says so

- Status: accepted
- Date: 2026-11-04
- Settles: `A64-P13` (the extended-register mnemonic family), and the boundary
  between `SUB_64_addsub_ext` and its `S = 1` siblings
- Supersedes: none
- Superseded by: none

## Context

`ADR-0016` closed the extend keyword on `ADD_64_addsub_ext` and recorded the
`op = 1` and `S = 1` twins as later slices. `ADR-0017` and `ADR-0018` closed the
same two bits on the shifted and immediate layouts. The MRS makes this step the
same shape as those: `SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and
`SUBS_64S_addsub_ext` are `ADD_64_addsub_ext` with `op` at 30+1 and/or `S` at
29+1 fixed, and every other field — `opt` (22+2) = `00`, bit 21 = `1`, `Rm`
(16+5), `option` (13+3), `imm3` (10+3), `Rn` (5+5), `Rd` (0+5) — is in the same
place (`EXP-0022` §1).

Five measured facts decide the boundaries.

1. **The words are the existing extended words with `op`/`S` set.** `sub x0, x1,
   w2, uxtb #0` is `0xcb220020` against `add x0, x1, w2, uxtb #0`'s
   `0x8b220020`; `adds` is `0xab220020`, `subs` `0xeb220020`, and all four have
   identical bits 28–0 for every keyword and every `imm3` measured
   (`EXP-0022` §2). The three nodes fix one or two bits; nothing in the operand
   list moves them.
2. **The extend keyword chooses the `src2` width, exactly as on `add`.** The six
   `[su]xt[bhw]` keywords take a `w` source and the two `[su]xtx` keywords take
   an `x` source; `llvm-mc` rejects both cross pairings and rejects `wsp` and
   `sp` in that slot (`EXP-0022` §2), and the MRS encodes the field through its
   single `<m>` placeholder (`EXP-0022` §1). `ADR-0016`'s rule therefore
   transfers unchanged.
3. **Register 31 is legal in every slot, but `Rd` means `sp` only on `sub`.**
   `sub sp, x1, w2, uxtb #3` is `0xcb220c3f` and `sub x0, sp, w1, uxtb #3` is
   `0xcb210fe0`, while `adds sp, ...` and `subs sp, ...` are rejected as invalid
   operands; `adds x0, sp, ...` is accepted, so 31 is `sp` in that `Rn`
   (`0xab2103e0`). The MRS assembly grammar names the slots directly: `SUB` uses
   `XdSP_option` for `Rd`, and both S nodes use `XdOrXZR__6`, while all three
   use `XnSP_option` for `Rn` and `Rm_option` for `Rm` (`EXP-0022` §1). So 31 in
   `Rd` is `sp` on the `sub` rows and `xzr` on the `adds`/`subs` rows — where
   `subs xzr, x1, w2, uxtb #0` is the `cmp x1, w2, uxtb` word
   `0xeb22003f` (`EXP-0022` §2).
4. **`imm3` is `0…4` again.** `#5`, `#6`, `#7` are inside the three-bit field but
   unallocated, and `#8` is outside it; the assembler rejects both, and
   omitting the amount means 0 (`EXP-0022` §2). The slot is the `imm3` slot
   `ADR-0009`/`ADR-0016` already define, with `excluded: [5, 6, 7]`.
5. **`lsl` and `uxtx` are different words on an `x` source, and `lsl` on an
   `sp` source is the extended node.** `sub x0, x1, x2, lsl #2` is the
   shifted-register word `0xcb020820` and `sub x0, x1, x2, uxtx #2` is the
   extended word `0xcb226820` — bit 21 is the only difference, so the two rows
   are distinguishable in bytes. With `sp` as `Rn` there is no shifted row at
   all: `sub x0, sp, x1, lsl #2` assembles to `0xcb216be0`, i.e. the extended
   node, and `llvm-mc -disassemble` prints that word back as `lsl #2` while it
   prints `0xcb226820` back as `uxtx #2` (`EXP-0022` §2). The spelling is not a
   reliable carrier in either direction; the `form_id` names the word.

## Decision

1. **Twenty-four forms in `definitions/aarch64/0.11.0.json`**, the eight
   `option` rows for each of the three nodes, named after the `add` rows of the
   same keyword:
   - `aarch64:sub/x64-x64-w32-imm3-uxtb` … and the six other `w`-source rows,
     plus `aarch64:sub/x64-x64-x64-imm3-uxtx` and `…-sxtx`, from
     `SUB_64_addsub_ext`;
   - the same eight under `aarch64:adds/…` from `ADDS_64S_addsub_ext`;
   - the same eight under `aarch64:subs/…` from `SUBS_64S_addsub_ext`.

   `0.11.0` repeats the sixty-eight `0.10.0` forms unchanged and adds these
   twenty-four; `0.1.0` … `0.10.0` stay frozen at their digests. The new digest
   is the one `EXP-0022` §5 records.
2. **The mnemonic bit is the node's, as on the other two layouts.** The
   generator reads a different MRS node per family, and those nodes fix
   `op = 1` and/or `S = 1`; no plan field names either bit, and no row pins
   them by hand. This is `ADR-0017`/`ADR-0018` applied to the third layout.
3. **The extend keyword is the form and fixes the `src2` width.** The eight
   `option` values are eight rows per mnemonic, each pinning `option` at 13+3;
   the six `[su]xt[bhw]` rows have an `aarch64.gpr32`/`w32` `src2` slot and the
   two `[su]xtx` rows an `aarch64.gpr64`/`x64` one. A cross pairing is
   `E-OPERAND-001` on `kind` and `target_type` (`N02d`).
4. **`imm3` is field content over `0…4` with the `5…7` tail excluded.** The slot
   is `aarch64.imm`/`imm3` at `[10,3]`, `align_bits = 0`, `bits = 3`,
   `excluded: [5, 6, 7]`; `5` is `E-RANGE-004` (`N16e`) and `8` is
   `E-RANGE-001`, never a truncated or re-encoded amount.
5. **Register 31 stays a plain `reg_number` in every slot; the node's role says
   what it denotes.** `Rd` on the `sub` rows is `sp`, `Rd` on the
   `adds`/`subs` rows and `src2` are `xzr`/`wzr`, and `Rn` is `sp`. No `sp`
   operand kind and no plan field are added: the encoding stores one 5-bit
   number, and splitting it would let the same word be reached two ways
   (`ADR-0019` decision 4).
6. **`cmp`/`cmn` stay out.** They fix `Rd = 31` and drop the destination, so the
   `subs`/`adds` extended rows already reach their words but the alias family
   is still a separate two-operand shape (`ADR-0018`, `N01i`).
7. **The 32-bit extended nodes stay out.** `ADD_32_addsub_ext`,
   `SUB_32_addsub_ext`, `ADDS_32S_addsub_ext` and `SUBS_32S_addsub_ext` fix
   `sf = 0` as well; naming one is `E-FORM-001` (`N01l`), and `add w0, wsp, w1`
   (`0x0b2143e0`) remains unreachable, as `ADR-0019` decision 8 recorded.
8. **No new error code, no schema change, no Rust change.** The slot shapes come
   from `ADR-0016`, the rejection codes already have fixtures, and the
   materializer only resolves the `form_id`.

## Consequences

- `A64-P13` passes: `A64-P13-ext-family` is twenty-seven instructions (108 B) —
  one per new row, plus one row per register-31 role (`sub sp, …`,
  `adds x0, sp, …`, `subs xzr, …`) — and its bytes match `llvm-mc` 23.1.2
  (`EXP-0022` §3), with no relocations.
- The AArch64 table is 92 forms across eleven documents, from twenty-nine MRS
  nodes. The new rows add three node names to the generator and no new slot
  shape.
- `N01f` (`aarch64:sub/x64-x64-w32-imm3-uxtb` against `0.8.0`) stays valid but
  narrows to a version boundary, like `N01h`/`N01j`/`N01k`.
- The negative set is 33 fixtures: `N01l`, `N02d` and `N16e` join the thirty.
- `A64-P9`'s extend rows gain their `sub`/`adds`/`subs` twins; `EC-32` now
  covers all four mnemonics on the extended layout.

## Alternatives considered

- **Keep the three nodes out and call the extend family complete.** Rejected:
  the slice is one `op` bit and one `S` bit on a node already read, and leaving
  them out would let `sub x0, x1, w2, uxtb` be `E-FORM-001` while
  `add`'s identical shape is in the table — a coverage hole with no contract
  reason behind it.
- **Add an `sp` operand kind for `Rd` on the `sub` rows.** Rejected for the
  reason `ADR-0019` gives: 31 is one number in one field, the role is the
  node's, and a second kind would restate the instruction in the plan.
- **One row per keyword for all three mnemonics with `op`/`S` as operands.**
  Rejected: neither bit has an assembly spelling, and a free bit would let a
  plan ask for `add`'s bytes under `sub`'s mnemonic (`INV-07`).
- **Include the 32-bit extended nodes here.** Deferred, not refused: they fix
  `sf = 0` and their `Rm` width rule is the same one, but the 32-bit shift
  amount and the `w`-source pairing need their own counterexamples, as
  `ADR-0019` did for the other two layouts.
