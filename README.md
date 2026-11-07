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
ADR-0045 extends those bases to `r8`–`r15`: `0.18.0` adds eight `-base-ext` rows
(word and REX-less low-byte, load/store × `disp8`/`disp32`) because those
templates carry no `REX` byte and a high base adds one, and widens the four
`40`-prefixed byte rows in place because their `REX` byte already exists.
`REX.B` is bit 8 after the `66` byte on the word rows and bit 0 on the byte
rows; the byte register set is a partition (0–3 on the new rows, 4–7 on the
widened ones), and the high-byte rows cannot extend at all because the `REX`
byte renames `ah`–`bh` to `spl`–`dil`.
ADR-0046 then adds the two bases P22 left out: `0.19.0` appends twenty-eight
fixed-base `SIB` rows, because `%rsp` spends a `SIB` byte and `%r12` spends
`REX.B` on top, so the base is a template fact and the row carries only the
register and the displacement. The high-byte family gets `%rsp` only, since
`movb %ah, 8(%r12)` has no encoding, and `ModRM` plus the displacement move one
byte later with the `SIB`.
ADR-0047 repeats the `SIB` decision inside the SSE families: `0.20.0` appends
sixteen fixed-base rows for legacy `movaps` and VEX `vmovaps`, because `%rsp`
spends the `SIB` byte, the legacy `%r12` spends `REX.B`, and the VEX `%r12` must
spend the three-byte prefix. Each family keeps the register window it already
had — the legacy field stays three bits, while the VEX `R̄` bit reaches
`xmm8`–`xmm15` at no length cost.
ADR-0048 repeats it once more in the EVEX family: `0.21.0` appends
twenty-four fixed-base rows (× `xmm`/`ymm`/`zmm`, load/store,
`disp8*N`/`disp32`, `%rsp`/`%r12`). There the base costs no prefix byte, because
its fourth bit is already the inverted `B̄` in `P0`; `62 f1 …`
and `62 d1 …` are the same length, so the prefix does not grow, the vector
slot stays at `[43,3]`, and only the displacement moves (from bit 48 to 56).
`disp8*N` content is still `disp / N`, and `8(%rsp)` promotes to `disp32`
rather than truncating.
ADR-0049 closes the `mod = 00` half of that axis: `0.22.0` appends twelve
fixed-base rows (× `xmm`/`ymm`/`zmm`, load/store, `%rsp`/`%r12`) where
`r/m = 100` puts the base in the `SIB` byte and drops the displacement slot
entirely. `(%rsp)` is `62 f1 7c 08 28 04 24` and `(%r12)` is
`62 d1 7c 08 28 04 24` — seven bytes, still differing only in `P0` — while
`%rbp`/`%r13` cannot use the shape because `r/m = 101` at `mod = 00` is
RIP-relative.
ADR-0050 opens that byte to an index and a scale: `0.23.0` appends eighteen rows
(× `xmm`/`ymm`/`zmm`, load/store, none/`disp8*N`/`disp32`) with the base an
operand again. `r/m = 100` announces the `SIB` byte, so `ModRM` is `04`/`44`/`84`;
base is `[48,3]` plus the inverted `B̄`, index `[51,3]` plus the inverted `X̄`,
and scale `[54,2]`. `(%rsp,%rax,1)` is `62 f1 7c 08 28 04 04` and
`(%rsp,%r12,1)` is `62 b1 7c 08 28 04 24`, so `X̄` is the index's fourth bit;
index `4` is the "no index" encoding, and `%rbp`/`%r13` are excluded from the
no-displacement rows only, where `SIB.base = 101` means "no base, `disp32`".
ADR-0051 takes that last `SIB` base choice: `0.24.0` appends six rows
(× `xmm`/`ymm`/`zmm`, load/store, `disp32` only) with no `base` role at all.
`mod = 00` with `SIB.base = 101` *is* the displacement request, so every row is
eleven bytes and `(,%rax,4)` is `62 f1 7c 08 28 0c 85 00 00 00 00`, while the
index (`[51,3]` + `X̄`) and the scale (`[54,2]`) stay where they were.
ADR-0052 spends the byte's last combination: `0.25.0` appends six rows
(× `xmm`/`ymm`/`zmm`, load/store, `disp32` only) with neither a base nor an
index role. `SIB = 25` is index `100` ("no index") and base `101` ("no base,
`disp32`"), so `0x1234, %xmm0` is `62 f1 7c 08 28 04 25 34 12 00 00` — eleven
bytes, with the address always four bytes, even for `0x0` or `0x7fff`.
ADR-0053 carries the same shape into the 64-bit GPR `mov` family: `0.26.0`
appends two rows (load and store, `disp32` only) whose `ModRM` is `04` and whose
`SIB` byte is `25`, so `0x1234, %rax` is `48 8b 04 25 34 12 00 00` — eight
bytes, with the register four bits written raw (`[19,3]` plus `REX.R`).
`moffs` (`A0`–`A3`) is the second legal encoding at ten bytes and has no row,
so `EC-05` is frozen with the `form variant` carrier.
ADR-0054 takes the same address into the 32-bit GPR `mov` rows, which need
one row per register window: the low rows have no `REX` byte, so
`0x1234, %eax` is `8b 04 25 34 12 00 00` (seven bytes) with the register in
the three-bit `ModRM.reg`, while `0x1234, %r8d` is
`44 8b 04 25 34 12 00 00` (eight bytes) with `REX.R` at `[2,1]` and `0`–`7`
excluded. The length difference is the prefix, never the address.
ADR-0055 moves the shape down to 16-bit width, where the operand-size
prefix `66` comes first: `0x1234, %ax` is
`66 8b 04 25 34 12 00 00` (eight bytes) while `0x1234, %r8w` is
`66 44 8b 04 25 34 12 00 00` (nine), with `REX.R` at `[10,1]` and `0`–`7`
excluded. The address stays a signed 32-bit field (`-32768` is
`00 80 ff ff`) and `0x80000000` leaves the row for `movabsw`.
ADR-0056 closes the width axis at eight bits, where one three-bit field
names two register sets: `0x1234, %al` is `8a 04 25 34 12 00 00` and
`0x1234, %ah` is `8a 24 25 34 12 00 00` (seven bytes each), while
`0x1234, %spl` is `40 8a 24 25 34 12 00 00` and `0x1234, %r8b` is
`44 8a 04 25 34 12 00 00` (eight), so the byte width has four windows.
ADR-0058 adds the no-displacement shape to those same rows: `(%rax), %al`
is `8a 00` and `%cl, (%rcx)` is `88 09` (two bytes), while `(%rsi), %dil`
is `40 8a 3e` and `%r15b, (%r9)` is `45 88 39` (three). `%rbp` and `%r13`
stay on their `disp8 = 0` rows (`8a 45 00`) because `r/m = 101` at
`mod = 00` is RIP-relative, and `%rsp`/`%r12` still need the `SIB` byte.
The address is still signed 32-bit content (`-128` is `80 ff ff ff`).
ADR-0059 takes those two bases onto the shape: `(%rsp), %al` is `8a 04 24`
and `(%r12), %al` is `41 8a 04 24` (three bytes, or four behind a `REX` byte
whose `B` bit alone picks the base), with `SIB = 24` fixed in the template;
the high-byte window has only the `%rsp` half, because `REX.B` renames `%ah`.
ADR-0060 gives the same third shape to the 64-bit rows: `movq (%rax), %rax`
is `48 8b 00` and `movq %rax, (%rax)` is `48 89 00` (three bytes, `REX.W`
in the template, both register fields four bits so one row covers all
sixteen registers and bases), while `%rsp`/`%r12` keep their `SIB` rows and
`%rbp`/`%r13` their RIP-relative rows. `llvm-mc` normalises `0(%rax)` to the
short form, so the plan names the row.
ADR-0061 gives `%rsp`/`%r12` that `mod = 00` shape: `(%rsp), %rax` is
`48 8b 04 24` and `(%r12), %rax` is `49 8b 04 24` (four bytes, `ModRM = 04`
and `SIB = 24`), with the base's `REX.B` fixed in the template so only the
register's `REX.R` is a slot and one row per base and direction covers all
sixteen registers; `%rbp`/`%r13` stay RIP-relative.
ADR-0062 gives the 32-bit rows their first bases: `(%rax), %eax` is `8b 00`
(two bytes, `mod = 00`), but the legacy row has no `REX` byte, so the reach is
three disjoint rows per direction — `(%rax), %r8d` is `44 8b 00`,
`(%r8), %eax` is `41 8b 00`, and `(%r9), %r15d` is `45 8b 39` — with
`%rsp`/`%r12` and `%rbp`/`%r13` excluded.
ADR-0063 takes the `SIB` pair onto that family: `(%rsp), %eax` is `8b 04 24`
and `(%r12), %eax` is `41 8b 04 24` — `ModRM = 04` plus `SIB = 24`, the base
and its `REX.B` fixed in the template — so each base, direction and register
window is a row and `%rsp` costs three bytes in the low window against four
in every other row (`(%rsp), %r8d` is `44 8b 04 24`).
ADR-0064 adds the `disp8` shape to the same family: `8(%rax), %eax` is `8b 40 08`
three bytes with `mod = 01` and a signed byte, while `%rbp`/`%r13` become
ordinary bases (`8(%rbp)` is `8b 45 08`) and only `%rsp`/`%r12` stay on `SIB`
rows; `128` leaves the row for the four-byte `disp32` form.
ADR-0065 completes that axis: `200(%rax), %eax` is `8b 80 c8 00 00 00`, six
bytes with `mod = 10` and a signed 32-bit displacement, and the same three
reach windows reappear at seven bytes (`44`/`41`/`45`), with `%rbp`/`%r13`
still ordinary bases and only `%rsp`/`%r12` on `SIB` rows.
ADR-0066 combines the two: `8(%rsp), %eax` is `8b 44 24 08`, four bytes with
`SIB = 24` and a signed byte, while `8(%r12), %eax` is the same three bytes
behind `REX.B` — so the base stays a form name rather than an operand.
ADR-0067 completes that axis: `200(%rsp), %eax` is `8b 84 24 c8 00 00 00`, seven
bytes with `mod = 10` and a signed 32-bit displacement, and `200(%r12), %eax`
is the same three bytes behind `REX.B`.
ADR-0068 repeats the `mod = 00` shape one width down: `(%rax), %ax` is `66 8b 00`,
three bytes with no displacement, and `(%r8), %ax` is `66 41 8b 00`, where the
`REX` byte also moves the register field to `[27,3]`. `%rsp`/`%r12` are
`66 8b 04 24`/`66 41 8b 04 24`, the same `SIB = 24` with the base fixed in the
form.
ADR-0069 widens the register field of those rows: `(%rax), %r8w` is `66 44 8b 00`,
four bytes with `REX = 44`, and `(%r8), %r8w` is `66 45 8b 00`, where one byte
carries both `R` and `B`; the `%rsp`/`%r12` rows become `66 44 8b 04 24` and
`66 45 8b 04 24`.
ADR-0070 repeats that window on the `disp8` rows: `8(%rax), %r8w` is
`66 44 8b 40 08` (five bytes, displacement at `[32,8]`) and `8(%r8), %r8w` is
`66 45 8b 40 08`; the `SIB` rows are `66 44 8b 44 24 08`/`66 45 8b 44 24 08`,
with the displacement at `[40,8]`. At `mod = 01`, `%rbp`/`%r13` are legal
bases (`66 44 8b 45 08`).
ADR-0071 repeats it on the `disp32` rows: `200(%rax), %r8w` is
`66 44 8b 80 c8 00 00 00` (eight bytes, displacement at `[32,32]`) and
`200(%r8), %r8w` is `66 45 8b 80 c8 00 00 00`; the `SIB` rows are
`66 44 8b 84 24 c8 00 00 00`/`66 45 8b 84 24 c8 00 00 00`, with the
displacement at `[40,32]`. At `mod = 10`, `%rbp`/`%r13` are legal bases
(`66 44 8b 85 c8 00 00 00`).
ADR-0072 adds the index and scale to those rows: `8(%rax,%rcx,1), %r8w` is
`66 44 8b 44 08 08` (six bytes, `SIB = 08`, displacement at `[40,8]`) and
`8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08`, where one `REX` byte carries
`R`, `X` and `B`. The base is one four-bit slot (`REX.B` + `SIB.base`), the
index one four-bit slot (`REX.X` + `SIB.index`, with `4` the "no index"
encoding), and the scale two bits of field content (`0…3` for ×1/×2/×4/×8).
ADR-0073 removes the `REX` byte from that shape: `8(%rax,%rcx,1), %ax` is
`66 8b 44 08 08` (five bytes, `ModRM` and `SIB` one byte earlier and the
displacement at `[32,8]`), while `8(%rdi,%rsi,4), %di` is `66 8b 7c b7 08`.
The register, base and index fields are three bits each, so register `8` and
base `8` are rejected, but `%rsp`/`%rbp` stay legal bases (`66 8b 44 0c 08` /
`66 8b 44 0d 08`).
ADR-0074 puts a `REX` byte back for the base or the index only: `8(%r8,%rcx,1),
%ax` is `66 41 8b 44 08 08` (`REX.B`, six bytes, displacement at `[40,8]`) and
`8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08` (`REX.X`), while the register stays
in `%ax`–`%di`.
ADR-0075 extends both memory operands at once: `8(%r8,%r9,1), %ax` is
`66 43 8b 44 08 08` (`REX = 43`, six bytes) and `8(%r12,%r12,1), %ax` is
`66 43 8b 44 24 08`, where `SIB.base = 100` and `SIB.index = 100` are both
meaningful; base or index below `8` is rejected rather than read as `REX.B`/
`REX.X = 0`.
ADR-0076 brings the index/scale shape to the 32-bit family, where there is no
prefix byte at all: `8(%rax,%rcx,1), %eax` is `8b 44 08 08` (four bytes,
`ModRM` at byte 1, `disp8` at `[24,8]`) and `8(%rdi,%rsi,4), %edi` is
`8b 7c b7 08`. The register, base and index are three bits each, so register
`8` and base `8` stay rejected (they are the pending `REX.R`/`REX.B` rows),
while `%rsp`/`%rbp` remain legal bases (`8b 44 0c 08` / `8b 44 35 08`) and
index `4` is rejected as the "no index" encoding.
ADR-0077 gives those 32-bit indexed rows their single `REX` windows, one
extension bit per row: `8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08` (`REX.R`,
five bytes), `8(%r8,%rcx,1), %eax` is `41 8b 44 08 08` (`REX.B`) and
`8(%rax,%r9,1), %eax` is `42 8b 44 08 08` (`REX.X`). The prefix pushes `ModRM`
to byte 2, so the displacement moves to `[32,8]`/`[32,32]`; each extended slot
lists its fixed bit as the most significant placement and rejects `0`–`7`,
while the operands the row keeps low stay three-bit fields.
ADR-0078 extends both memory operands at once: `8(%r8,%r9,1), %eax` is
`43 8b 44 08 08` (`REX = 43`, five bytes) and `8(%r12,%r12,1), %eax` is
`43 8b 44 24 08`, where `SIB.base = 100` and `SIB.index = 100` are both
meaningful; base or index below `8` is rejected rather than read as `REX.B`/
`REX.X = 0`, and the register stays low (`8(%r8,%r9,1), %r8d` is the deferred
`REX.RBX` row `47 8b 44 08 08`).
ADR-0079 closes the split by extending the register too: `8(%r8,%r9,1), %r8d`
is `47 8b 44 08 08` (five bytes, `REX = 47` with `R`, `X` and `B` set), and all
three register slots reject `0`–`7`. `%r12` is legal on all three operands
(`8(%r12,%r12,1), %r8d` is `47 8b 44 24 08`, `%r12d, 8(%r12,%r12,1)` is
`47 89 64 24 08`), and `%rsp` as an index is still rejected.
ADR-0080 adds the `0x67` address-size prefix to the `REX`-less rows:
`8(%eax,%ecx,1), %eax` is `67 8b 44 08 08` (five bytes), where `0x67` is byte 0
and the base/index name `%eax`/`%ecx` rather than `%rax`/`%rcx`. The prefix
precedes any `REX` byte (`67 47 8b 44 08 08`), so the `0x67`+`REX` windows are
separate forms; `%esp` remains rejected as an index while `%ebp` is legal
(`67 8b 44 28 08`).
ADR-0081 puts one `REX` byte between `0x67` and the opcode:
`8(%eax,%ecx,1), %r8d` is `67 44 8b 44 08 08` (six bytes, `REX.R`),
`8(%r8d,%ecx,1), %eax` is `67 41 8b 44 08 08` (`REX.B`) and
`8(%eax,%r9d,1), %eax` is `67 42 8b 44 08 08` (`REX.X`). Each extended slot
excludes `0`–`7`, so a low value on it is a different row; the two-bit windows
(`67 43`, `67 45`, `67 46`, `67 47`) stay deferred.
ADR-0057 carries that fourth window into the memory rows, where one `REX`
byte holds both extension bits: `8(%rax), %r8b` is `44 8a 40 08` and
`8(%r8), %r8b` is `45 8a 40 08` (four bytes each, `REX.R` at `[2,1]` and
`REX.B` at `[0,1]`), while `8(%rsp), %r8b` is `44 8a 44 24 08` and
`8(%r12), %r8b` is `45 8a 44 24 08`: five bytes, the same `SIB` byte `24`
read two ways. Both directions appear in all three base windows at disp8
and disp32, and the high-byte window cannot join (`8(%r8), %ah` is
rejected; `8(%rax), %ah` is `8a 60 08`).
Seventy-three definition documents are frozen and oracle-verified; the materializer
and its fixture gate are implemented.

| Area | State |
|---|---|
| Contract (`docs/fmp-v0/01_contract.md`) | draft, fields marked `TBD` where unproven |
| Schema (`schema/fmp-v0.schema.json`) | draft, examples validate |
| Definitions (`definitions/`) | x86-64 `0.1.0` (7 forms), `0.2.0` (9 forms), `0.3.0` (17 forms), `0.4.0` (22 forms), `0.5.0` (25 forms), `0.6.0` (25 forms), `0.7.0` (29 forms), `0.8.0` (33 forms), `0.9.0` (45 forms), `0.10.0` (53 forms), `0.11.0` (62 forms), `0.12.0` (74 forms), `0.13.0` (74 forms), `0.14.0` (79 forms), `0.15.0` (91 forms), `0.16.0` (103 forms), `0.17.0` (119 forms), `0.18.0` (127 forms), `0.19.0` (155 forms), `0.20.0` (171 forms), `0.21.0` (195 forms) and `0.22.0` (207 forms) and `0.23.0` (225 forms) and `0.24.0` (231 forms) and `0.25.0` (237 forms) and `0.26.0` (239 forms) and `0.27.0` (243 forms) and `0.28.0` (247 forms) and `0.29.0` (255 forms) and `0.30.0` (267 forms) and `0.31.0` (275 forms) and `0.32.0` (289 forms) and `0.33.0` (291 forms) and `0.34.0` (295 forms) and `0.35.0` (301 forms) and `0.36.0` (309 forms) and `0.37.0` (315 forms) and `0.38.0` (321 forms) and `0.39.0` (329 forms) and `0.40.0` (337 forms) and `0.41.0` (345 forms) and `0.42.0` (353 forms) and `0.43.0` (361 forms) and `0.44.0` (369 forms) and `0.45.0` (373 forms) and `0.46.0` (377 forms) and `0.47.0` (385 forms) and `0.48.0` (389 forms) and `0.49.0` (393 forms) and `0.50.0` (405 forms) and `0.51.0` (409 forms) and `0.52.0` (413 forms) and `0.53.0` (417 forms) and `0.54.0` (429 forms), aarch64 `0.1.0` (4 forms), `0.2.0` (5 forms), `0.3.0` (6 forms), `0.4.0` (11 forms), `0.5.0` (15 forms), `0.6.0` (18 forms), `0.7.0` (26 forms), `0.8.0` (32 forms), `0.9.0` (44 forms), `0.10.0` (68 forms), `0.11.0` (92 forms), `0.12.0` (132 forms), `0.13.0` (135 forms), `0.14.0` (136 forms), `0.15.0` (152 forms), `0.16.0` (168 forms) and `0.17.0` (176 forms), rv64 `0.1.0` (7 forms) and `0.2.0` (8 forms) frozen, digests pinned |
| Prototype (`prototype/`) | workspace compiled; all three slices materialize from the plan |
| Oracles (`tools/oracle/`) | planned; `llvm-mc` (± `ld.lld`) drives the experiments |
| Evidence (`research/evidence/`) | index, XirAsm snapshot, EXP-0001…EXP-0083 |

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
