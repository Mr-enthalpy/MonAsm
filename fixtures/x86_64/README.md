# x86-64 fixtures

Vectors: `X86-P1` … `X86-P52` in `docs/fmp-v0/06_validation_matrix.md`.

## Positive vectors present

| ID | Fixture | Oracle |
|---|---|---|
| X86-P1 | `X86-P1-mov-r64-both-directions` | `EXP-0005` (`manual+disassembly` for the `8B /r` half) |
| X86-P2 | `X86-P2-add-imm8-and-imm32` | `EXP-0005` |
| X86-P3 | `X86-P3-two-legal-encodings` | `EXP-0005` (`81 /0` measured on `%rbx`; decode-verified on `%rax`) |
| X86-P7 | `X86-P7-short-and-near-branch` | `EXP-0005` |
| X86-P8 | `X86-P8-local-and-external-branch` | `EXP-0005`, record count from `llvm-readobj` |
| X86-P6 | `X86-P6-rip-relative` | `EXP-0005` + `EXP-0029`, record count from `llvm-readobj` |
| X86-P4 | `X86-P4-base-disp` | `EXP-0005` + `EXP-0030` (`manual+disassembly` for the small-value `disp32`) |
| X86-P5 | `X86-P5-prefixes` | `EXP-0005` + `EXP-0031` (`manual+disassembly` for the 16-bit `8B` half) |
| X86-P9 | `X86-P9-sse-vex-evex` | `EXP-0005` + `EXP-0032` (`manual+disassembly` for the EVEX.128 row) |
| X86-P10 | `X86-P10-gpr-extended` | `EXP-0035` |
| X86-P11 | `X86-P11-base-extended` | `EXP-0036` |
| X86-P12 | `X86-P12-base-index-scale` | `EXP-0037` |
| X86-P13 | `X86-P13-sse-memory` | `EXP-0038` (`{evex}` forces the EVEX family) |
| X86-P14 | `X86-P14-sse-base-ext` | `EXP-0039` (`{evex}` forces the EVEX family) |
| X86-P15 | `X86-P15-sse-xmm-ext` | `EXP-0040` (`{evex}` forces the EVEX family) |
| X86-P16 | `X86-P16-sse-no-disp` | `EXP-0041` (`{evex}` forces the EVEX family) |
| X86-P17 | `X86-P17-sse-xmm16-31` | `EXP-0042` (the operand selects EVEX; no `{evex}` needed) |
| X86-P18 | `X86-P18-sse-ymm-zmm` | `EXP-0043` (`{evex}` forces the EVEX.256 row; `ymm`/`zmm` otherwise select the family) |
| X86-P19 | `X86-P19-sse-ymm-zmm-memory` | `EXP-0044` (`{evex}` forces the EVEX.256 memory rows; `zmm` needs no directive) |
| X86-P20 | `X86-P20-vex-ymm-memory` | `EXP-0045` (the `ymm` operand selects VEX.256; no directive needed) |
| X86-P21 | `X86-P21-mov-mem-8-16` | `EXP-0046` (the `movw`/`movb` mnemonic selects the width; no directive needed) |
| X86-P22 | `X86-P22-mov-mem-base-ext` | `EXP-0047` (the same mnemonic rule; `r8`–`r15` bases force the `-base-ext` rows) |
| X86-P23 | `X86-P23-mov-mem-sib` | `EXP-0048` (the same mnemonic rule; `%rsp`/`%r12` bases force the fixed-base `SIB` rows) |
| X86-P24 | `X86-P24-sse-mem-sib` | `EXP-0049` (`movaps`/`vmovaps` select the family; `%rsp`/`%r12` bases force the fixed-base `SIB` rows) |
| X86-P25 | `X86-P25-evex-mem-sib` | `EXP-0050` (`{evex}` forces the EVEX family; `%rsp`/`%r12` bases force the fixed-base `SIB` rows at all three widths) |
| X86-P26 | `X86-P26-evex-mem-sib-nodisp` | `EXP-0051` (the same family rule; `(%rsp)`/`(%r12)` with no displacement force the `mod = 00` fixed-base `SIB` rows at all three widths) |
| X86-P27 | `X86-P27-evex-mem-sib-index` | `EXP-0052` (the same family rule; an index plus a scale selects the operand-owned `SIB` rows at all three widths and all three displacement shapes) |
| X86-P28 | `X86-P28-evex-mem-sib-nobase-index` | `EXP-0053` (the same family rule; `SIB.base = 101` at `mod = 00` drops the base and forces `disp32`, so the rows are eleven bytes at all three widths) |
| X86-P29 | `X86-P29-evex-mem-sib-absolute` | `EXP-0054` (the same family rule; `SIB = 25` at `mod = 00` drops both the base and the index and makes the four-byte address the only operand, so the rows are eleven bytes at all three widths) |
| X86-P30 | `X86-P30-gpr-mov-abs32` | `EXP-0055` (the same shape under the 64-bit GPR `mov` opcodes: `ModRM = 04`, `SIB = 25`, a four-bit raw register slot and a four-byte address, so both directions are eight bytes; `moffs` is a second legal encoding and has no row) |
| X86-P31 | `X86-P31-gpr32-mov-abs32` | `EXP-0056` (the same shape at 32-bit width, split by register window: the low rows have no `REX` byte and are seven bytes, the `-ext` rows carry `REX = 44` and are eight bytes, and both keep `ModRM = 04`, `SIB = 25` and a four-byte signed address) |
| X86-P32 | `X86-P32-gpr16-mov-abs32` | `EXP-0057` (the same shape at 16-bit width behind the `66` prefix: the low rows are eight bytes with no `REX` byte, the `-ext` rows insert `REX = 44` and are nine, and the address stays a signed 32-bit field, so `-32768` is `00 80 ff ff` and `0x80000000` leaves the row for `movabsw`) |
| X86-P33 | `X86-P33-gpr8-mov-abs32` | `EXP-0058` (the same shape at 8-bit width in four register windows: the low `%al`–`%bl` and high `%ah`–`%bh` rows are seven bytes with no `REX` byte, the `REX = 40` `%spl`–`%dil` and `REX = 44` `%r8b`–`%r15b` rows are eight, and the address stays a signed 32-bit field) |
| X86-P34 | `X86-P34-gpr8-ext-mem` | `EXP-0059` (the same fourth window in the memory rows: `REX.R` at `[2,1]` and `REX.B` at `[0,1]` share one prefix byte, so the plain-base rows are four bytes at disp8 and seven at disp32 whether the base is low or extended, while `%rsp` and `%r12` add the `SIB` byte `24` and are five and eight; the register slot is four bits and excludes `0`–`7`) |
| X86-P35 | `X86-P35-gpr8-mov-mem-nodisp` | `EXP-0060` (the same four windows at `mod = 00`, where the row is opcode plus `ModRM` and nothing else: the `REX`-less windows are two bytes, the `REX = 40` and `REX.R` windows three, and the base slot excludes four values — `%rbp`/`%r13` because `r/m = 101` there is RIP-relative, `%rsp`/`%r12` because they need a `SIB` byte) |
| X86-P36 | `X86-P36-gpr8-mov-mem-sib-nodisp` | `EXP-0061` (the two `SIB` bases on that shape: `SIB = 24` and the base are template constants, so `(%rsp), %al` is three bytes and `(%r12), %al` is the same three after a `REX` byte whose `B` bit alone picks the base; the high-byte window has only the `%rsp` half because `REX.B` renames `%ah`) |
| X86-P37 | `X86-P37-gpr64-mov-mem-nodisp` | `EXP-0062` (the same shape at 64-bit width: `REX.W` is in the template and both register fields are four bits, so one row covers every register and base; the base slot excludes `%rsp`/`%rbp`/`%r12`/`%r13`, and `llvm-mc` normalises an explicit zero displacement on a plain base to this short form) |
| X86-P38 | `X86-P38-gpr64-mov-mem-sib-nodisp` | `EXP-0063` (the `mod = 00` `SIB` shape: four bytes with `ModRM = 04` and `SIB = 24`, the base and its `REX.B` fixed in the template, so `(%rsp), %rax` and `(%r12), %rax` differ only in that byte and one row per base and direction covers every register) |
| X86-P39 | `X86-P39-gpr32-mov-mem-nodisp` | `EXP-0064` (the 32-bit plain-base shape at two and three bytes: the legacy row has no `REX` byte, so the reach is three disjoint rows per direction — `8b 00`, `44 8b 00`, `41 8b 00` — and the fixture runs each twice across both window edges) |
| X86-P40 | `X86-P40-gpr32-mov-mem-sib-nodisp` | `EXP-0065` (the 32-bit `SIB` shape at three and four bytes: `ModRM = 04` and `SIB = 24`, the base and its `REX.B` fixed in the template, so `(%rsp), %eax` and `(%r12), %eax` differ only in that byte and each base, direction and register window is a row) |
| X86-P41 | `X86-P41-gpr32-mov-mem-disp8` | `EXP-0066` (the 32-bit `mod = 01` shape at three and four bytes: `8(%rax), %eax` is `8b 40 08` with the displacement at `[16,8]`, the three reach windows still split, and `%rbp`/`%r13` legal here while `%rsp`/`%r12` stay on `SIB` rows) |
| X86-P42 | `X86-P42-gpr32-mov-mem-disp32` | `EXP-0067` (the 32-bit `mod = 10` shape at six and seven bytes: `200(%rax), %eax` is `8b 80 c8 00 00 00` with a signed 32-bit displacement at `[16,32]`, the three reach windows still split, `%rbp`/`%r13` ordinary bases and only `%rsp`/`%r12` on `SIB` rows) |
| X86-P43 | `X86-P43-gpr32-mov-mem-sib-disp8` | `EXP-0068` (the 32-bit `mod = 01` `SIB` shape at four and five bytes: `8(%rsp), %eax` is `8b 44 24 08` with `SIB = 24` and the displacement at `[24,8]`, `%r12` differing only in `REX.B`, and the register window still split) |
| X86-P44 | `X86-P44-gpr32-mov-mem-sib-disp32` | `EXP-0069` (the 32-bit `mod = 10` `SIB` shape at seven and eight bytes: `200(%rsp), %eax` is `8b 84 24 c8 00 00 00` with `SIB = 24` and a signed 32-bit displacement at `[24,32]`, `%r12` differing only in `REX.B`, and the register window still split) |
| X86-P45 | `X86-P45-gpr16-mov-mem-nodisp` | `EXP-0070` (the 16-bit `mod = 00` shape at three to five bytes: `(%rax), %ax` is `66 8b 00` with the base at `[16,3]`, `(%r8), %ax` is `66 41 8b 00` with the register at `[27,3]`, and `%rsp`/`%r12` are `66 8b 04 24`/`66 41 8b 04 24` with `SIB = 24`) |
| X86-P46 | `X86-P46-gpr16-mov-mem-nodisp-rex-r` | `EXP-0071` (the `REX.R` register window at four to five bytes: `(%rax), %r8w` is `66 44 8b 00` with `R` at `[10,1]`, `(%r8), %r8w` is `66 45 8b 00` with one byte carrying both `R` and `B`, and `%rsp`/`%r12` are `66 44 8b 04 24`/`66 45 8b 04 24`) |
| X86-P47 | `X86-P47-gpr16-mov-mem-disp8-rex-r` | `EXP-0072` (the same `REX.R` register window on the `disp8` rows at five to six bytes: `8(%rax), %r8w` is `66 44 8b 40 08` with the displacement at `[32,8]`, `8(%r8), %r8w` is `66 45 8b 40 08`, and `8(%rsp)`/`8(%r12)` are `66 44 8b 44 24 08`/`66 45 8b 44 24 08` with the displacement at `[40,8]`; at `mod = 01`, `8(%rbp), %r8w` is `66 44 8b 45 08`) |
| X86-P48 | `X86-P48-gpr16-mov-mem-disp32-rex-r` | `EXP-0073` (the same `REX.R` register window on the `disp32` rows at eight to nine bytes: `200(%rax), %r8w` is `66 44 8b 80 c8 00 00 00` with the displacement at `[32,32]`, `200(%r8), %r8w` is `66 45 8b 80 c8 00 00 00`, and `200(%rsp)`/`200(%r12)` are `66 44 8b 84 24 c8 00 00 00`/`66 45 8b 84 24 c8 00 00 00` with the displacement at `[40,32]`; at `mod = 10`, `200(%rbp), %r8w` is `66 44 8b 85 c8 00 00 00`) |
| X86-P49 | `X86-P49-gpr16-mov-index-rex-rx` | `EXP-0074` (the same 16-bit rows with a `SIB` index and scale: `8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08` with `SIB = 08` and the displacement at `[40,8]`, `8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08` with `R`, `X` and `B` in one byte, and `200(%rax,%rcx,1), %r8w` is `66 44 8b 84 08 c8 00 00 00` with four displacement bytes at `[40,32]`) |
| X86-P50 | `X86-P50-gpr16-mov-index-low` | `EXP-0075` (the same index/scale shape without `REX`: `8(%rax,%rcx,1), %ax` is `66 8b 44 08 08` with `ModRM = 44`, `SIB = 08` and the displacement at `[32,8]`, `8(%rdi,%rsi,4), %di` is `66 8b 7c b7 08`, and `200(%rax,%rcx,1), %ax` is `66 8b 84 08 c8 00 00 00` with four displacement bytes at `[32,32]`) |
| X86-P51 | `X86-P51-gpr16-mov-index-ext-window` | `EXP-0076` (the base and index windows with the register still low: `8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08` with `REX.B`, `8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08` with `REX.X`, and `200(%r8,%rcx,1), %ax` is `66 41 8b 84 08 c8 00 00 00` with four displacement bytes at `[40,32]`) |
| X86-P52 | `X86-P52-gpr16-mov-index-rex-bx-window` | `EXP-0077` (both memory operands extended at once: `8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08` with `REX = 43`, `8(%r12,%r12,1), %ax` is `66 43 8b 44 24 08`, and `200(%r8,%r9,1), %ax` is `66 43 8b 84 08 c8 00 00 00` with four displacement bytes at `[40,32]`) |

`X86-P6` ships in `definitions/x86_64/0.2.0.json` as two forms with
`mod = 00`, `r/m = 101` and `disp32` as the last field (`ADR-0027`). `X86-P4`
ships in `0.3.0` as eight forms, load/store × `disp8`/`disp32` ×
base-in-`r/m`/`%rsp`-fixed (`ADR-0028`). `X86-P5` ships in `0.4.0` as five
forms: two 16-bit directions whose template starts with `0x66`, the high-byte
row, and the low-byte pair split by a REX prefix (`ADR-0029`).
`X86-P9` ships in `0.5.0` as three `movaps` rows at `xmm` width, one per
encoding family: `/legacy` (`0f 28 /r`), two-byte `/vex` (`c5 f8 28 /r`) and
EVEX.128 `/evex` (`62 f1 7c 08 28 /r`), with the prefix as template and the
`ModRM` slots moving with it (`ADR-0030`). `X86-P10` ships in `0.6.0` as the
six 64-bit register-direct rows widened to a 4-bit `x86.gpr64` (`ADR-0033`),
`X86-P11` in `0.7.0` as the twelve base+disp rows at a 4-bit base plus four
fixed-base `%r12` rows (`ADR-0034`), `X86-P12` in `0.8.0` as four
`base + index*scale + disp` rows (`ADR-0035`), `X86-P13` in `0.9.0` as
twelve SSE memory rows across the three families, with the EVEX `disp8` as
compressed field content (`ADR-0036`), and `X86-P14` in `0.10.0` as the SSE
base window: the four EVEX rows widen in place and eight `-base-ext` rows carry
the legacy `REX` and three-byte-VEX reach, with `placement.invert` writing the
inverted `B̄` (`ADR-0037`). `X86-P15` ships in `0.11.0` as the register window:
the VEX and EVEX memory `xmm` slots and the EVEX register-direct pair widen in
place, three legacy `REX.R`/`REX.B` register rows and two VEX register rows join
(`C5 78 29` for a high source, `C4 41 78 28` for both high), and four legacy
memory rows carry a 4-bit `xmm` with a 4-bit base (`ADR-0038`). `X86-P16` ships
in `0.12.0` as the no-displacement shape: six legacy, four VEX and two EVEX rows
with `mod = 00` and no `disp` slot, because `0f 28 00` (three bytes) and
`0f 28 40 00` (four bytes, `disp8 = 0`) decode as the same instruction; `%rsp`/
`%r12` (a `SIB` byte) and `%rbp`/`%r13` (`r/m = 101` is RIP) stay outside and
name the `disp8` row with displacement `0` (`ADR-0039`). `X86-P17` ships in
`0.13.0` as the fifth EVEX register bit: the same seven EVEX rows get a 5-bit
`xmm` slot in place, with the inverted `R̄'` at bit 12 for `ModRM.reg` and the
inverted `X̄` at bit 14 for a register-direct `ModRM.rm`, so `vmovaps %xmm31,
%xmm30` is `62 01 7c 08 28 f7` with no new row and no length change (`ADR-0040`).
`X86-P18` ships in `0.14.0` as the other two widths: five register-direct rows —
three VEX.256 windows (`C5 FC 28`, `C5 7C 29` for a high source, `C4 41 7C 28` for
both high), one EVEX.256 row (`62 F1 7C 28 28`) and one EVEX.512 row
(`62 F1 7C 48 28`) — with `x86.ymm` and `x86.zmm` as distinct kinds (`ADR-0041`).
`X86-P19` ships in `0.15.0` as the memory counterpart: twelve EVEX rows repeat
the six `0.13.0` `xmm` memory shapes at `ymm` (`62 F1 7C 28 …`) and `zmm`
(`62 F1 7C 48 …`), and `EC-39` gains the per-form unit — `disp8x32` and
`disp8x64` sit at `[48,8]` with the payload as field content, exactly like
`disp8x16`, so `4064` is content `127` at `ymm`, `−4096` is `−128`, and `28`/
`4096`/`60`/`8192` are `disp32` rows (`ADR-0042`). `X86-P20` ships in `0.16.0` as
the same coverage at VEX width: twelve VEX.256 memory rows mirror the `0.11.0`/
`0.12.0` `xmm` rows at `L = 1`, the two-byte low-base window (`C5 FC …`) and the
three-byte `r8`–`r15` window (`C4 C1 7C …`), each with the `disp8`, `disp32` and
`mod = 00` pairs. VEX has no compressed unit, so `32(%rax)` is the plain signed
byte `20` and `128` names the `disp32` row; no `EC` row is added or revised
(`ADR-0043`). `X86-P21` ships in `0.17.0` as the 8/16-bit memory rows: four word
(`66 8B`/`66 89`) and twelve byte rows in the three `0.4.0` register sets — the
REX-less low set (`88`/`8A`, numbers 0–3), the high set (`88`/`8A`, numbers 4–7)
and the `spl`–`dil` set (`40 88`/`40 8A`, numbers 4–7) — each with `disp8` and
`disp32`. The `0x66` byte is template byte 0 ahead of any REX byte, so `ModRM`
sits at bit 16 on the word and `40`-byte rows and at bit 8 on the REX-less byte
rows; every base stays the three-bit window 0–7 minus `%rsp`, and no `EC` row is
added or revised (`ADR-0044`). `X86-P22` ships in `0.18.0` as the base window:
eight `-base-ext` rows (word and REX-less low-byte, load/store × `disp8`/
`disp32`) put `REX.B` at bit 8 after the `66` byte or at bit 0, and the four
`40`-prefixed byte rows widen from three to four base bits in place. The byte
registers split 0–3 on the new rows and 4–7 on the widened ones, so one
`(register, base)` pair names one row; `%rsp`/`%r12` stay out of both windows
and the high-byte rows cannot extend, because the `REX` byte renames `ah`–`bh`
(`ADR-0045`). `X86-P23` ships in `0.19.0` as the two bases that slice left
out: twenty-eight fixed-base `SIB` rows — word, REX-less low byte, high
byte and `40`-prefixed byte, load/store × `disp8`/`disp32`, at `%rsp` and
`%r12` — because `%rsp` spends a `SIB` byte and `%r12` spends `REX.B` on
top, so the base is a template fact and the row carries only the register and
the displacement. The high-byte family gets `%rsp` only, since
`movb %ah, 8(%r12)` has no encoding, and `ModRM` plus the displacement move
one byte later with the `SIB` (`ADR-0046`). `X86-P24` ships in `0.20.0` as the
same `SIB` pair inside the SSE families: sixteen fixed-base rows — legacy
`movaps` and VEX `vmovaps`, load/store × `disp8`/`disp32`, at `%rsp` and
`%r12` — because `%rsp` spends the `SIB` byte, the legacy `%r12` spends
`REX.B`, and the VEX `%r12` must use the three-byte prefix. Each family keeps
its existing register window: the legacy field stays three bits, while the VEX
`R̄` bit already reaches `xmm8`–`xmm15` (`ADR-0047`). `X86-P25` ships in `0.21.0` as the same
pair in the EVEX family: twenty-four fixed-base rows — `xmm`/`ymm`/`zmm`,
load/store, `disp8*N`/`disp32`, at `%rsp` and `%r12`. The base costs no
prefix byte here, because its fourth bit is already the inverted
`B̄` in `P0` (`62 f1 …` vs `62 d1 …`), so the two bases
are the same length; the prefix does not grow, the vector slot stays at
`[43,3]`, and only the displacement moves, from `[48,…]` to
`[56,…]`. `disp8*N` content stays `disp / N` and `8(%rsp)` promotes to
`disp32` rather than truncating (`ADR-0048`). `X86-P26` closes the `mod = 00`
half of that axis in `0.22.0`: twelve fixed-base rows — `xmm`/`ymm`/`zmm`,
load/store, at `%rsp` and `%r12` — where `r/m = 100` puts the base in the
`SIB` byte and the displacement slot disappears. `(%rsp)` is
`62 f1 7c 08 28 04 24` and `(%r12)` is `62 d1 7c 08 28 04 24`, seven bytes,
still differing only in `P0`; `%rbp`/`%r13` keep the `disp8 = 0` form because
`mod = 00` with `r/m = 101` is RIP-relative (`ADR-0049`). `X86-P27` opens that
byte in `0.23.0`: eighteen rows — `xmm`/`ymm`/`zmm`, load/store,
none/`disp8*N`/`disp32` — with the base an operand again. `r/m = 100` announces
the `SIB` byte, base is `[48,3]` plus the inverted `B̄`, index `[51,3]` plus the
inverted `X̄`, and scale `[54,2]`; `(%rsp,%rax,1)` is
`62 f1 7c 08 28 04 04` and `(%rsp,%r12,1)` is `62 b1 7c 08 28 04 24`, so `X̄`
carries the index's fourth bit. Index `4` is the "no index" encoding, and on
the `mod = 00` rows `SIB.base = 101` means "no base, `disp32`", so
`%rbp`/`%r13` stay on the `disp8*N = 0` row (`ADR-0050`). `X86-P28` takes that
last `SIB` base choice in `0.24.0`: six rows — three widths, load/store,
`disp32` only — with no `base` role at all. `mod = 00` with `SIB.base = 101`
*is* the displacement request, so the template carries `05` and four
displacement bytes and every row is eleven bytes: `(,%rax,4)` is
`62 f1 7c 08 28 0c 85 00 00 00 00` and `-4096(,%r12,8), %xmm3` is
`62 b1 7c 08 28 1c e5 00 f0 ff ff`. The index and scale fields do not move
(`ADR-0051`). `X86-P29` spends the byte's last combination in `0.25.0`: six
rows — three widths, load/store, `disp32` only — with neither a base nor an
index role. `SIB = 25` is scale `00`, index `100` ("no index") and base `101`
("no base, `disp32`"), so `0x1234, %xmm0` is
`62 f1 7c 08 28 04 25 34 12 00 00`, eleven bytes; the address is always four
bytes, even for `0` or `0x7fff`, and the indexed neighbour
`62 f1 7c 08 28 04 85 34 12 00 00` differs in three `SIB` bits (`ADR-0052`).
`X86-P30` carries the shape into the 64-bit GPR `mov` family in `0.26.0`: two
rows — load and store, `disp32` only — with the same `ModRM = 04` and
`SIB = 25`. `0x1234, %rax` is `48 8b 04 25 34 12 00 00` and `%r15, 0x1234` is
`4c 89 3c 25 34 12 00 00`: `REX.W` is a template bit, the register is four bits
written raw (`[19,3]` plus `REX.R`), and the address is four bytes even for
`0` (`ADR-0053`). `moffs` (`A0`–`A3`) is the second legal encoding at ten bytes
and has no row, so `EC-05` is frozen (`N01bf`).

`X86-P31` takes the shape to 32-bit width in `0.27.0`, where the same
instruction has two legal lengths: `0x1234, %eax` is
`8b 04 25 34 12 00 00` (seven bytes, no `REX` byte, the register in the
three-bit `ModRM.reg`), while `0x1234, %r8d` is
`44 8b 04 25 34 12 00 00` (eight bytes, `REX.R` at `[2,1]` with `0`–`7`
excluded). Both directions are mirrored, and the address stays four bytes
even for `0` (`ADR-0054`). Register `0` on an `-ext` row is `E-RANGE-004`
(`N16ad`), because the template's `REX.R = 1` already means `%r8d`.

`X86-P32` takes the shape to 16-bit width in `0.28.0`, where the
operand-size prefix `66` comes first: `0x1234, %ax` is
`66 8b 04 25 34 12 00 00` (eight bytes, no `REX` byte, the register in
the three-bit `ModRM.reg`), while `0x1234, %r8w` is
`66 44 8b 04 25 34 12 00 00` (nine bytes, `REX.R` at `[10,1]` with `0`–`7`
excluded). Both directions are mirrored, and the address does not narrow
with the operand: `-32768` is `00 80 ff ff` and `0x80000000` switches
`llvm-mc` to `movabsw` (`ADR-0055`). Register `0` on an `-ext` row is
`E-RANGE-004` (`N16ae`), because the template's `REX.R = 1` already
means `%r8w`.

`X86-P33` closes the width axis at 8 bits in `0.29.0`, where one three-bit field
names two register sets: `0x1234, %al` is `8a 04 25 34 12 00 00` and
`0x1234, %ah` is `8a 24 25 34 12 00 00` (seven bytes each, the register in the
three-bit `ModRM.reg`), while `0x1234, %spl` is
`40 8a 24 25 34 12 00 00` and `0x1234, %r8b` is `44 8a 04 25 34 12 00 00`
(eight bytes; `REX.R` is at `[2,1]` in the extended row with `0`–`7`
excluded). All four windows are mirrored in both directions, and the address
does not narrow with the operand: `-128` is `80 ff ff ff` and `0x80000000`
switches `llvm-mc` to `movabsb` for the low rows (`ADR-0056`). Register `0` on
the `REX = 40` row is `E-RANGE-004` (`N16af`), because that byte is what
renames `%ah` to `%spl`.

`X86-P34` carries that fourth window into the memory rows in `0.30.0`
(`ADR-0057`), where one `REX` byte holds both extension bits.
`8(%rax), %r8b` is `44 8a 40 08` and `8(%r8), %r8b` is `45 8a 40 08`: four
bytes either way, with `REX.R` at `[2,1]`, `REX.B` at `[0,1]`, the
register at `[19,3]` and the base at `[16,3]`. `8(%rsp), %r8b` is
`44 8a 44 24 08` and `8(%r12), %r8b` is `45 8a 44 24 08` (five bytes: the
same `SIB` byte `24`, read as two bases by `REX.B`), and their disp32
halves are eight. `%rbp` and `%r13` need no row of their own because
`mod = 01` is the family's floor (`8(%rbp), %r15b` is `44 8a 7d 08`), and
the high-byte window cannot join: `8(%r8), %ah` is rejected while
`8(%rax), %ah` is `8a 60 08`. Register `0` on an extended row is
`E-RANGE-004` (`N16ag`), and `%rsp` or `%r12` as the base of a plain-base
row is the same code (`N16ah`/`N16ai`).

`X86-P35` adds the third displacement shape in `0.31.0` (`ADR-0058`):
`(%rax), %al` is `8a 00` and `%cl, (%rcx)` is `88 09` (two bytes, the
opcode at `[0,8]`, `ModRM` at `[8,8]`, the register at `[11,3]` and the
base at `[8,3]`), while `(%rsi), %dil` is `40 8a 3e` and
`%r15b, (%r9)` is `45 88 39` (three bytes, register `[19,3]` with
`REX.R` at `[2,1]` and base `[16,3]` with `REX.B` at `[0,1]`). `%rbp`
and `%r13` cannot inhabit the rows — `r/m = 101` at `mod = 00` is
RIP-relative `disp32`, and `llvm-mc` writes `(%rbp), %al` as
`8a 45 00` — while `%rsp` and `%r12` need the `SIB` byte
(`8a 04 24`, `41 8a 04 24`) that a later slice carries. `%rbp`/`%r13`
as base are `E-RANGE-004` (`N16aj`/`N16ak`) and `%rsp`/`%r12` are the
same code (`N16al`/`N16am`).

`X86-P36` takes those two bases in `0.32.0` (`ADR-0059`): `(%rsp), %al` is
`8a 04 24` and `(%r12), %al` is `41 8a 04 24` — the same three bytes after
a `REX` byte whose `B` bit alone picks the base — with `SIB = 24` at
`[16,8]` (or `[24,8]` behind the prefix) and the register at `[11,3]` (or
`[19,3]`). The high-byte window has only the `%rsp` half because `REX.B`
renames `%ah` to `%spl`, so `(%r12), %ah` is rejected and the slice has
fourteen rows, not sixteen. The base is fixed in the template, so a `base`
or `disp` operand is `E-OPERAND-002` (`N02ay`/`N02az`), the absent
high-byte `%r12` row is `E-FORM-001` (`N01bs`), register `16`/`8` is
`E-OPERAND-004` (`N14af`/`N14ag`), and register `0` on the `REX = 40` row
is `E-RANGE-004` (`N16an`).

`X86-P37` gives the 64-bit family the same shape in `0.33.0` (`ADR-0060`):
`(%rax), %rax` is `48 8b 00` and `%rax, (%rax)` is `48 89 00` — three
bytes with `REX.W` in the template, `REX.R`/`REX.B` at `[2,1]`/`[0,1]` and
one row for every register and base, so `(%r8), %r8` is `4d 8b 00` and
`(%r9), %r15` is `4d 8b 39`. The base slot excludes `%rsp`/`%rbp`/`%r12`/
`%r13`: `%rbp`/`%r13` because `r/m = 101` at `mod = 00` is the RIP-relative
shape (`48 8b 45 00` at `mod = 01`), and `%rsp`/`%r12` because they need the
`SIB` byte. There is no displacement slot, so a `disp` operand is
`E-OPERAND-002` (`N02ba`), register `16` is `E-OPERAND-004` (`N14ah`), and
the four bases are `E-RANGE-004` (`N16ao`–`N16ar`).

`X86-P38` takes those two `SIB` bases onto the shape in `0.34.0`
(`ADR-0061`): `(%rsp), %rax` is `48 8b 04 24` and `(%r12), %rax` is
`49 8b 04 24` — four bytes with `ModRM = 04` and `SIB = 24`, the base and
its `REX.B` in the template, so one row per base and direction covers every
register (`(%rsp), %r8` is `4c 8b 04 24`). The base is not an operand, so a
`base` or `disp` operand is `E-OPERAND-002` (`N02bb`/`N02bc`) and register
`16` is `E-OPERAND-004` (`N14ai`).

`X86-P39` gives the 32-bit family its first base rows in `0.35.0`
(`ADR-0062`): `(%rax), %eax` is `8b 00` and `%eax, (%rax)` is `89 00` — two
bytes, `mod = 00`, no displacement. The legacy row has no `REX` byte, so a
high register or base grows the instruction and the reach is the form:
`(%rax), %r8d` is `44 8b 00` (`REX.R`), `(%r8), %eax` is `41 8b 00`
(`REX.B`), and `(%r9), %r15d` is `45 8b 39`; the three windows are disjoint.
Every row excludes `%rsp`/`%r12` (`SIB`) and `%rbp`/`%r13` (RIP-relative), a
`disp` operand is `E-OPERAND-002` (`N02bd`), the field ends are
`E-OPERAND-004` (`N14aj`/`N14ak`) and the exclusions are `E-RANGE-004`
(`N16as`–`N16av`).

`X86-P40` takes the `%rsp`/`%r12` `SIB` bases onto that family in `0.36.0`
(`ADR-0063`): `(%rsp), %eax` is `8b 04 24` and `(%r12), %eax` is
`41 8b 04 24` — `ModRM = 04` plus `SIB = 24`, the base and its `REX.B` in the
template. The two bases share the low three bits `100`, so each needs its own
row; the register window still splits, so `%rsp` is three bytes in the low
window and four in the `REX.R` window (`44 8b 04 24`), while every `%r12` row
is four (`41`/`45`, `45 8b 3c 24`). `%rbp`/`%r13` stay RIP-relative, a
`base`/`disp` operand is `E-OPERAND-002` (`N02be`/`N02bf`), the field ends are
`E-OPERAND-004` (`N14al`/`N14am`) and the `-ext` floor is `E-RANGE-004`
(`N16aw`).

`X86-P41` adds the plain-base `disp8` shape in `0.37.0` (`ADR-0064`):
`8(%rax), %eax` is `8b 40 08` and `%eax, 8(%rax)` is `89 40 08` — three
bytes, `mod = 01`, the base in `ModRM.r/m` and a signed byte at `[16,8]`
(`-128…127`). The reach is still three rows (`44 8b 40 08`, `41 8b 40 08`,
`45 8b 79 08`), with the displacement at `[24,8]` behind a `REX` byte. At
`mod = 01` `%rbp`/`%r13` are ordinary bases (`8b 45 08`), so only
`%rsp`/`%r12` stay excluded (`N16ax`/`N16ay`); the `REX.B` row also keeps
the low bases out, because one would clear the fixed bit (`N16ba`). A
missing `disp` is `E-OPERAND-002` (`N02bg`), `128` is `E-RANGE-001` (`N03r`),
the field ends are `E-OPERAND-004` (`N14an`/`N14ao`) and the `REX.R` floor
is `E-RANGE-004` (`N16az`).

`X86-P42` completes the displacement axis in `0.38.0` (`ADR-0065`):
`200(%rax), %eax` is `8b 80 c8 00 00 00` and `%eax, 200(%rax)` is
`89 80 c8 00 00 00` — six bytes, `mod = 10`, the base in `ModRM.r/m` and a
signed 32-bit displacement at `[16,32]` (`-2147483648…2147483647`). The
reach is still three rows, seven bytes each (`44 8b 80 c8 00 00 00`,
`41 8b 80 c8 00 00 00`, `45 8b b9 c8 00 00 00`), with the displacement at
`[24,32]` behind a `REX` byte. `%rbp`/`%r13` remain ordinary bases
(`8b 85 c8 00 00 00`), so only `%rsp`/`%r12` stay excluded
(`N16bb`/`N16bc`); the `REX.B` row again keeps the low bases out
(`N16be`). A missing `disp` is `E-OPERAND-002` (`N02bh`), `2147483648` is
`E-RANGE-001` (`N03s`), the field ends are `E-OPERAND-004`
(`N14ap`/`N14aq`) and the `REX.R` floor is `E-RANGE-004` (`N16bd`).

`X86-P43` combines the `SIB` bases with `disp8` in `0.39.0` (`ADR-0066`):
`8(%rsp), %eax` is `8b 44 24 08` and `%eax, 8(%rsp)` is `89 44 24 08` —
four bytes, `mod = 01`, `SIB = 24` and a signed byte at `[24,8]`
(`-128…127`). `8(%r12), %eax` is `41 8b 44 24 08`, the same three bytes
behind `REX.B`, so the base stays a form name; the register window still
splits (`44 8b 44 24 08`, `41 8b 44 24 08`, `45 8b 44 24 08`) with the
displacement at `[32,8]`. A missing `disp` is `E-OPERAND-002` (`N02bi`),
`128` is `E-RANGE-001` (`N03t`), the field ends are `E-OPERAND-004`
(`N14ar`/`N14as`) and the `REX.R` floor is `E-RANGE-004` (`N16bf`).

`X86-P44` completes the displacement axis in `0.40.0` (`ADR-0067`):
`200(%rsp), %eax` is `8b 84 24 c8 00 00 00` and `%eax, 200(%rsp)` is
`89 84 24 c8 00 00 00` — seven bytes, `mod = 10`, `SIB = 24` and a signed
32-bit displacement at `[24,32]` (`-2147483648…2147483647`). `200(%r12), %eax`
is `41 8b 84 24 c8 00 00 00`, the same three bytes behind `REX.B`, so the
base stays a form name; the register window still splits
(`44 8b 84 24 c8 00 00 00`, `41 8b 84 24 c8 00 00 00`,
`45 8b 84 24 c8 00 00 00`) with the displacement at `[32,32]`. A missing
`disp` is `E-OPERAND-002` (`N02bj`), `2147483648` is `E-RANGE-001` (`N03u`),
the field ends are `E-OPERAND-004` (`N14at`/`N14au`) and the `REX.R` floor is
`E-RANGE-004` (`N16bg`).

`X86-P45` gives the 16-bit family its `mod = 00` rows in `0.41.0`
(`ADR-0068`): `(%rax), %ax` is `66 8b 00` and `%ax, (%rax)` is `66 89 00` —
three bytes, no displacement, base at `[16,3]`. `(%r8), %ax` is
`66 41 8b 00`, where the `REX` byte also moves the register field to `[27,3]`
and the base to `[24,3]`. At `mod = 00` `r/m = 101` is `rip`-relative, so
`%rbp`/`%r13` are not plain bases (`(%rbp), %ax` is `66 8b 45 00`), and
`%rsp`/`%r12` are the fixed `66 8b 04 24`/`66 41 8b 04 24` rows. A supplied
`disp` is `E-OPERAND-002` (`N02bk`), `%rsp`/`%r12` on a plain row and a low
base on the `-ext` row are `E-RANGE-004` (`N16bh`–`N16bj`), and
`%rbp`/`%r13` are `E-RANGE-004` (`N16bk`/`N16bl`).

`X86-P46` takes the `REX.R` register window on those rows in `0.42.0`
(`ADR-0069`): `(%rax), %r8w` is `66 44 8b 00`, four bytes with `REX = 44`
(`R` at `[10,1]`, register at `[27,3]`), and `(%r8), %r8w` is `66 45 8b 00`,
where one byte carries both `R` and `B`. The `SIB` bases compose unchanged:
`(%rsp), %r8w` is `66 44 8b 04 24` and `(%r12), %r8w` is `66 45 8b 04 24`.
A low register is `E-RANGE-004` (`N16bm`), `16` is `E-OPERAND-004` (`N14av`),
a supplied `disp` is `E-OPERAND-002` (`N02bl`), and `%rsp`/`%rbp` on the new
base rows are `E-RANGE-004` (`N16bn`/`N16bo`).

`X86-P47` carries that window onto the `disp8` rows in `0.43.0`
(`ADR-0070`): `8(%rax), %r8w` is `66 44 8b 40 08`, five bytes with the
displacement at `[32,8]`, and `8(%r8), %r8w` is `66 45 8b 40 08`, one byte
carrying both `R` and `B`. The `SIB` rows add the `SIB` byte and move the
displacement to `[40,8]`: `8(%rsp), %r8w` is `66 44 8b 44 24 08` and
`8(%r12), %r8w` is `66 45 8b 44 24 08`. At `mod = 01`, `%rbp`/`%r13` are
legal bases (`8(%rbp), %r8w` is `66 44 8b 45 08`). A missing `disp` is
`E-OPERAND-002` (`N02bm`), `128` is `E-RANGE-001` (`N03v`), a low register is
`E-RANGE-004` (`N16bp`), `16` is `E-OPERAND-004` (`N14aw`), and `%rsp` on the
plain row and `%rbp` on the `-ext` row are `E-RANGE-004`
(`N16bq`/`N16br`).

`X86-P48` carries that window onto the `disp32` rows in `0.44.0`
(`ADR-0071`): `200(%rax), %r8w` is `66 44 8b 80 c8 00 00 00`, eight bytes
with the displacement at `[32,32]`, and `200(%r8), %r8w` is
`66 45 8b 80 c8 00 00 00`, one byte carrying both `R` and `B`. The `SIB`
rows add the `SIB` byte and move the displacement to `[40,32]`:
`200(%rsp), %r8w` is `66 44 8b 84 24 c8 00 00 00` and `200(%r12), %r8w` is
`66 45 8b 84 24 c8 00 00 00`. At `mod = 10`, `%rbp`/`%r13` are legal bases
(`200(%rbp), %r8w` is `66 44 8b 85 c8 00 00 00`). A missing `disp` is
`E-OPERAND-002` (`N02bn`), `2147483648` is `E-RANGE-001` (`N03w`), a low
register is `E-RANGE-004` (`N16bs`), `16` is `E-OPERAND-004` (`N14ax`), and
`%rsp` on the plain row and `%rbp` on the `-ext` row are `E-RANGE-004`
(`N16bt`/`N16bu`).

`X86-P49` adds the index and scale to those rows in `0.45.0` (`ADR-0072`):
`8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08`, six bytes with `REX = 44`,
`ModRM = 44` (`mod = 01`, `r/m = 100`), `SIB = 08` (scale `0`, index `1`,
base `0`) and the displacement at `[40,8]`; all three extension bits share the
byte, so `8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08` at the same length.
The base is one four-bit slot (`REX.B` + `SIB.base`, so `8(%r8,%rdi,2), %r8w`
is `66 45 8b 44 78 08`), and the index is one four-bit slot (`REX.X` +
`SIB.index`, so `%r12` is legal through `REX.X = 1` while index `4` is the "no
index" encoding). The `disp32` rows put four bytes at `[40,32]`
(`200(%rax,%rcx,1), %r8w` is `66 44 8b 84 08 c8 00 00 00`). A missing index is
`E-OPERAND-002` (`N02bo`), scale `4` is `E-RANGE-001` (`N03x`), a low register
and index `4` are `E-RANGE-004` (`N16bw`/`N16bv`), `16`/base `16` are
`E-OPERAND-004` (`N14ay`/`N14az`), and naming a row against `0.44.0` is
`E-FORM-001` (`N01cr`/`N01cs`).

`X86-P50` takes the `REX` byte out of that shape in `0.46.0` (`ADR-0073`):
`8(%rax,%rcx,1), %ax` is `66 8b 44 08 08`, five bytes with `ModRM = 44`
(`mod = 01`, `r/m = 100`), `SIB = 08` and the displacement at `[32,8]`; every
field moves one byte earlier and only three bits wide, so `8(%rdi,%rsi,4), %di`
is `66 8b 7c b7 08`. `%rsp`/`%rbp` are legal bases (`66 8b 44 0c 08` /
`66 8b 44 0d 08`), while register `8` and base `8` are `E-OPERAND-004`
(`N14bb`/`N14bc`). The `disp32` rows put four bytes at `[32,32]`
(`200(%rax,%rcx,1), %ax` is `66 8b 84 08 c8 00 00 00`). A missing index is
`E-OPERAND-002` (`N02bp`), scale `4` is `E-RANGE-001` (`N03y`), index `4` is
`E-RANGE-004` (`N16bx`), `16` is `E-OPERAND-004` (`N14ba`), and naming a row
against `0.45.0` is `E-FORM-001` (`N01ct`/`N01cu`).

`X86-P51` keeps the register low and gives the base or the index a fourth bit in
`0.47.0` (`ADR-0074`): `8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08`, six bytes
with `REX.B`, `ModRM = 44`, `SIB = 08` and the displacement at `[40,8]`, while
`8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08` with `REX.X`. The register stays at
`[27,3]`, so register `8` is `E-OPERAND-004` (`N14bd`); the extended operand's
slot excludes the low window, so base `3` and index `3` are `E-RANGE-004`
(`N16bz`/`N16by`), and the other operand past `7` is `E-OPERAND-004`
(`N14be`). `%r12`/`%rsp`/`%rbp`/`%r13` are legal bases, and `%r12` is legal as
an index (`66 42 8b 44 20 08`). The `disp32` rows put four bytes at `[40,32]`
(`200(%r8,%rcx,1), %ax` is `66 41 8b 84 08 c8 00 00 00`). A missing index is
`E-OPERAND-002` (`N02bq`), scale `4` is `E-RANGE-001` (`N03z`), and naming a row
against `0.46.0` is `E-FORM-001` (`N01cv`/`N01cw`).

`X86-P52` extends both memory operands at once in `0.48.0` (`ADR-0075`):
`8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08`, six bytes with `REX = 43`
(`X = 1`, `B = 1`), `ModRM = 44`, `SIB = 08` and the displacement at `[40,8]`.
The register stays at `[27,3]`, so register `8` is `E-OPERAND-004` (`N14bf`);
both memory slots are four-bit slots (`[8,1]`+`[32,3]`, `[9,1]`+`[35,3]`) that
exclude `0`–`7`, so base `3` and index `3` are `E-RANGE-004`
(`N16ca`/`N16cb`) rather than a silent `REX.B`/`REX.X` clear. `%r12` is legal
as base and as index (`66 43 8b 44 24 08`), `%rsp`/`%rbp` are legal bases
(`66 42 8b 44 0c 08`), and `%rbp` is a legal index (`66 41 8b 44 2d 08`). The
`disp32` rows put four bytes at `[40,32]` (`200(%r8,%r9,1), %ax` is
`66 43 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02br`),
scale `4` is `E-RANGE-001` (`N03za`), and naming a row against `0.47.0` is
`E-FORM-001` (`N01cx`/`N01cy`).

## Negative fixtures present

| Vector | Fixture | Code |
|---|---|---|
| N01 | `negative/N01-absent-form`, `negative/N01x-absent-riprel-form`, `negative/N01y-absent-basedisp-form`, `negative/N01z-absent-16bit-form`, `negative/N01aa-absent-unfamilied-vmovaps-form`, `negative/N01ab-vex-form-absent-in-0.4.0`, `negative/N01ac-absent-r12-base-form`, `negative/N01ad-absent-index-scale-form`, `negative/N01ae-absent-sse-memory-form`, `negative/N01af-absent-base-ext-row-on-0.9.0`, `negative/N01ag-absent-xmm-ext-row-on-0.10.0`, `negative/N01ah-absent-no-disp-row-on-0.11.0`, `negative/N01ai-absent-ymm-row-on-0.13.0`, `negative/N01aj-legacy-has-no-ymm-width`, `negative/N01ak-absent-ymm-memory-row-on-0.14.0`, `negative/N01al-absent-vex256-memory-row`, `negative/N01am-absent-vex256-base-ext-row-on-0.15.0`, `negative/N01an-absent-mov-memory-r16-row-on-0.16.0`, `negative/N01ao-absent-mov-memory-base-ext-row-on-0.17.0`, `negative/N01ap-absent-mov-memory-sib-row-on-0.18.0`, `negative/N01aq-absent-high-byte-r12-row`, `negative/N01ar-absent-sse-mem-sib-row-on-0.19.0`, `negative/N01as-absent-no-displacement-sse-mem-sib-row`, `negative/N01at-absent-evex-mem-sib-row-on-0.20.0`, `negative/N01au-absent-no-displacement-evex-mem-sib-row`, `negative/N01av-absent-evex-mem-sib-nodisp-row-on-0.21.0`, `negative/N01aw-absent-rbp-no-displacement-evex-row`, `negative/N01ax-absent-evex-mem-sib-index-row-on-0.22.0`, `negative/N01ay-absent-evex-mem-sib-index-store-row-on-0.22.0`, `negative/N01az-absent-evex-mem-sib-nobase-load-row-on-0.23.0`, `negative/N01ba-absent-evex-mem-sib-nobase-store-row-on-0.23.0`, `negative/N01bb-absent-evex-mem-sib-absolute-load-row-on-0.24.0`, `negative/N01bc-absent-evex-mem-sib-absolute-store-row-on-0.24.0`, `negative/N01bd-absent-gpr-mov-abs32-load-row-on-0.25.0`, `negative/N01be-absent-gpr-mov-abs32-store-row-on-0.25.0`, `negative/N01bf-absent-gpr-mov-moffs-row`, `negative/N01bg-absent-gpr32-mov-abs32-load-row-on-0.26.0`, `negative/N01bh-absent-gpr32-mov-abs32-store-row-on-0.26.0`, `negative/N01bi-absent-gpr16-mov-abs32-load-row-on-0.27.0`, `negative/N01bj-absent-gpr16-mov-abs32-store-row-on-0.27.0`, `negative/N01bk-absent-gpr8-mov-abs32-load-row-on-0.28.0`, `negative/N01bl-absent-gpr8-mov-abs32-ext-store-row-on-0.28.0`, `negative/N01bm-absent-gpr8-ext-mov-mem-load-row-on-0.29.0`, `negative/N01bn-absent-gpr8-ext-mov-mem-store-row-on-0.29.0`, `negative/N01bo-absent-gpr8-mov-mem-load-row-on-0.30.0`, `negative/N01bp-absent-gpr8-mov-mem-store-row-on-0.30.0`, `negative/N01bq-absent-gpr8-mov-mem-sib-load-row-on-0.31.0`, `negative/N01br-absent-gpr8-mov-mem-sib-store-row-on-0.31.0`, `negative/N01bs-absent-gpr8h-r12-sib-row`, `negative/N01bt-absent-gpr64-mov-mem-load-row-on-0.32.0`, `negative/N01bu-absent-gpr64-mov-mem-store-row-on-0.32.0`, `negative/N01bv-absent-gpr64-mov-mem-sib-load-row-on-0.33.0`, `negative/N01bw-absent-gpr64-mov-mem-sib-store-row-on-0.33.0`, `negative/N01bx-absent-gpr32-mov-mem-load-row-on-0.34.0`, `negative/N01by-absent-gpr32-mov-mem-store-row-on-0.34.0`, `negative/N01bz-absent-gpr32-mov-mem-sib-load-row-on-0.35.0`, `negative/N01ca-absent-gpr32-mov-mem-sib-store-row-on-0.35.0`, `negative/N01cb-absent-gpr32-mov-mem-disp8-load-row-on-0.36.0`, `negative/N01cc-absent-gpr32-mov-mem-disp8-store-row-on-0.36.0`, `negative/N01cd-absent-gpr32-mov-mem-disp32-load-row-on-0.37.0`, `negative/N01ce-absent-gpr32-mov-mem-disp32-store-row-on-0.37.0`, `negative/N01cf-absent-gpr32-mov-mem-sib-disp8-load-row-on-0.38.0`, `negative/N01cg-absent-gpr32-mov-mem-sib-disp8-store-row-on-0.38.0`, `negative/N01ch-absent-gpr32-mov-mem-sib-disp32-load-row-on-0.39.0`, `negative/N01ci-absent-gpr32-mov-mem-sib-disp32-store-row-on-0.39.0`, `negative/N01cj-absent-gpr16-mov-mem-nodisp-load-row-on-0.40.0`, `negative/N01ck-absent-gpr16-mov-mem-nodisp-store-row-on-0.40.0`, `negative/N01cl-absent-gpr16-mov-mem-nodisp-rex-r-load-row-on-0.41.0`, `negative/N01cm-absent-gpr16-mov-mem-nodisp-rex-r-store-row-on-0.41.0`, `negative/N01cn-absent-gpr16-mov-mem-disp8-rex-r-load-row-on-0.42.0`, `negative/N01co-absent-gpr16-mov-mem-disp8-rex-r-store-row-on-0.42.0`, `negative/N01cp-absent-gpr16-mov-mem-disp32-rex-r-load-row-on-0.43.0`, `negative/N01cq-absent-gpr16-mov-mem-disp32-rex-r-store-row-on-0.43.0`, `negative/N01cr-absent-gpr16-mov-index-disp8-rex-rx-load-row-on-0.44.0`, `negative/N01cs-absent-gpr16-mov-index-disp8-rex-rx-store-row-on-0.44.0`, `negative/N01ct-absent-gpr16-mov-index-disp8-low-load-row-on-0.45.0`, `negative/N01cu-absent-gpr16-mov-index-disp8-low-store-row-on-0.45.0`, `negative/N01cv-absent-gpr16-mov-index-base-ext-load-row-on-0.46.0`, `negative/N01cw-absent-gpr16-mov-index-ext-store-row-on-0.46.0`, `negative/N01cx-absent-gpr16-mov-index-rex-bx-load-row-on-0.47.0`, `negative/N01cy-absent-gpr16-mov-index-rex-bx-store-row-on-0.47.0` | `E-FORM-001` |
| N02 | `negative/N02-operand-kind-mismatch`, `negative/N02j-base-on-riprel-form`, `negative/N02k-high-byte-operand-on-rex-form`, `negative/N02l-zmm-operand-on-xmm-evex-form`, `negative/N02m-dest-on-store-row`, `negative/N02n-zmm-operand-on-ymm-row`, `negative/N02o-zmm-operand-on-ymm-memory-row`, `negative/N02p-disp8x16-unit-on-disp8x32-row`, `negative/N02q-zmm-operand-on-vex256-memory-row`, `negative/N02r-gpr32-operand-on-mov-memory-r16-row`, `negative/N02s-r8h-operand-on-mov-memory-rex-row`, `negative/N02t-r8h-operand-on-mov-memory-base-ext-row`, `negative/N02u-gpr16-operand-on-mov-memory-sib-row`, `negative/N02v-gpr64-operand-on-sse-mem-sib-row`, `negative/N02w-extra-base-operand-on-fixed-base-row`, `negative/N02x-gpr64-operand-on-evex-mem-sib-row`, `negative/N02y-extra-base-operand-on-fixed-base-row`, `negative/N02z-gpr64-operand-on-evex-mem-sib-nodisp-row`, `negative/N02aa-extra-disp-operand-on-fixed-base-row`, `negative/N02ab-scale-spelled-x86-imm`, `negative/N02ac-extra-disp-operand-on-evex-mem-sib-index-row`, `negative/N02ad-extra-base-operand-on-evex-mem-sib-nobase-row`, `negative/N02ae-scale-spelled-x86-imm-on-evex-mem-sib-nobase-row`, `negative/N02af-extra-index-operand-on-evex-mem-sib-absolute-row`, `negative/N02ag-address-carried-as-disp8-on-evex-mem-sib-absolute-row`, `negative/N02ah-extra-base-operand-on-gpr-mov-abs32-row`, `negative/N02ai-address-carried-as-disp8-on-gpr-mov-abs32-row`, `negative/N02aj-extra-base-operand-on-gpr32-mov-abs32-row`, `negative/N02ak-address-carried-as-disp8-on-gpr32-mov-abs32-row`, `negative/N02al-gpr64-operand-on-gpr32-mov-abs32-row`, `negative/N02am-extra-base-operand-on-gpr16-mov-abs32-row`, `negative/N02an-address-carried-as-disp8-on-gpr16-mov-abs32-row`, `negative/N02ao-gpr32-operand-on-gpr16-mov-abs32-row`, `negative/N02ap-extra-base-operand-on-gpr8-mov-abs32-row`, `negative/N02aq-address-carried-as-disp8-on-gpr8-mov-abs32-row`, `negative/N02ar-gpr16-operand-on-gpr8-mov-abs32-row`, `negative/N02as-gpr8h-operand-on-gpr8-mov-abs32-row`, `negative/N02at-gpr8h-operand-on-gpr8-ext-mov-mem-row`, `negative/N02au-displacement-carried-as-disp8-on-gpr8-ext-mov-mem-disp32-row`, `negative/N02av-extra-base-operand-on-gpr8-ext-mov-mem-sib-row`, `negative/N02aw-gpr8h-operand-on-gpr8-mov-mem-nodisp-row`, `negative/N02ax-extra-disp-operand-on-gpr8-mov-mem-nodisp-row`, `negative/N02ay-extra-base-operand-on-gpr8-mov-mem-sib-row`, `negative/N02az-extra-disp-operand-on-gpr8-mov-mem-sib-row`, `negative/N02ba-extra-disp-operand-on-gpr64-mov-mem-nodisp-row`, `negative/N02bb-extra-base-operand-on-gpr64-mov-mem-sib-row`, `negative/N02bc-extra-disp-operand-on-gpr64-mov-mem-sib-row`, `negative/N02bd-extra-disp-operand-on-gpr32-mov-mem-nodisp-row`, `negative/N02be-extra-base-operand-on-gpr32-mov-mem-sib-row`, `negative/N02bf-extra-disp-operand-on-gpr32-mov-mem-sib-row`, `negative/N02bg-missing-disp-operand-on-gpr32-mov-mem-disp8-row`, `negative/N02bh-missing-disp-operand-on-gpr32-mov-mem-disp32-row`, `negative/N02bi-missing-disp-operand-on-gpr32-mov-mem-sib-disp8-row`, `negative/N02bj-missing-disp-operand-on-gpr32-mov-mem-sib-disp32-row`, `negative/N02bk-supplied-disp-operand-on-gpr16-mov-mem-nodisp-row`, `negative/N02bl-supplied-disp-operand-on-gpr16-mov-mem-nodisp-rex-r-row`, `negative/N02bm-missing-disp-operand-on-gpr16-mov-mem-disp8-rex-r-row`, `negative/N02bn-missing-disp-operand-on-gpr16-mov-mem-disp32-rex-r-row`, `negative/N02bo-missing-index-operand-on-gpr16-mov-index-disp8-rex-rx-row`, `negative/N02bp-missing-index-operand-on-gpr16-mov-index-disp8-low-row`, `negative/N02bq-missing-index-operand-on-gpr16-mov-index-base-ext-row`, `negative/N02br-missing-index-operand-on-gpr16-mov-index-rex-bx-row` | `E-OPERAND-001`, `E-OPERAND-002` |
| N03 | `negative/N03-imm8-out-of-range`, `negative/N03-disp8-out-of-range`, `negative/N03c-scale-is-field-content`, `negative/N03d-evex-disp8-content-out-of-range`, `negative/N03e-disp8x32-content-out-of-range`, `negative/N03f-disp8-content-out-of-range-vex256`, `negative/N03g-disp8-content-out-of-range-mov-memory`, `negative/N03h-disp8-content-out-of-range-mov-memory-sib`, `negative/N03i-disp8-content-out-of-range-sse-mem-sib`, `negative/N03j-disp8x16-content-out-of-range-evex-mem-sib`, `negative/N03k-disp32-past-end-on-evex-mem-sib-nobase-row`, `negative/N03l-disp32-past-end-on-evex-mem-sib-absolute-row`, `negative/N03m-disp32-past-end-on-gpr-mov-abs32-row`, `negative/N03n-disp32-past-end-on-gpr32-mov-abs32-row`, `negative/N03o-disp32-past-end-on-gpr16-mov-abs32-row`, `negative/N03p-disp32-past-end-on-gpr8-mov-abs32-row`, `negative/N03q-disp32-past-end-on-gpr8-ext-mov-mem-row`, `negative/N03r-disp8-out-of-range-on-gpr32-mov-mem-base-row`, `negative/N03s-disp32-out-of-range-on-gpr32-mov-mem-base-row`, `negative/N03t-disp8-out-of-range-on-gpr32-mov-mem-sib-row`, `negative/N03u-disp32-out-of-range-on-gpr32-mov-mem-sib-row`, `negative/N03v-disp8-128-on-gpr16-mov-mem-disp8-rex-r-row`, `negative/N03w-disp32-2147483648-on-gpr16-mov-mem-disp32-rex-r-row`, `negative/N03x-scale4-on-gpr16-mov-index-disp8-rex-rx-row`, `negative/N03y-scale4-on-gpr16-mov-index-disp8-low-row`, `negative/N03z-scale4-on-gpr16-mov-index-base-ext-row`, `negative/N03za-scale4-on-gpr16-mov-index-rex-bx-row` | `E-RANGE-001` |
| N04 | `negative/N04a-rel8-out-of-range`, `N04b-rel32-absolute-out-of-range`, `N04e-riprel32-literal-out-of-range` | `E-RANGE-002`, `E-FIXUP-003` |
| N05 | `negative/N05-expected-size-mismatch` | `E-SIZE-001` |
| N06 | `negative/N06-extension-list-mismatch` | `E-TARGET-001` |
| N07 | `negative/N07-fixup-partial-field`, `negative/N07b-riprel-operand-fixup-mismatch` | `E-FIXUP-001` |
| N08 | `negative/N08-undeclared-symbol`, `N08b-resolve-undefined-symbol`, `N08c-absolute-pcrel-without-base` | `E-SYMBOL-001`, `E-FIXUP-002` |
| N09 | `negative/N09-overlapping-fragments` | `E-LAYOUT-001` |
| N10 | `negative/N10-definition-digest-mismatch` | `E-DEF-001` |
| N11 | `negative/N11-fragment-gap` | `E-LAYOUT-002` |
| N13 | `negative/N13-expected-digest-mismatch` | `E-BYTE-001` |
| N14 | `negative/N14-register-wider-than-field`, `negative/N14b-xmm8-wider-than-field`, `negative/N14c-extended-register-on-old-table`, `negative/N14d-register-16-on-extended-table`, `negative/N14e-xmm8-on-sse-memory-row`, `negative/N14f-base8-on-vex-row`, `negative/N14g-base8-on-evex-row`, `negative/N14h-base16-on-base-ext-row`, `negative/N14i-xmm16-wider-than-field`, `negative/N14j-xmm8-on-3bit-legacy-row`, `negative/N14k-xmm8-source-on-2byte-vex-row`, `negative/N14l-base16-on-no-disp-row`, `negative/N14m-xmm16-on-0.12.0-evex-row`, `negative/N14n-xmm32-on-5bit-evex-row`, `negative/N14o-xmm16-on-4bit-vex-row`, `negative/N14p-ymm16-on-4bit-vex-row`, `negative/N14q-zmm32-on-5bit-evex-row`, `negative/N14r-ymm32-on-5bit-evex-memory-row`, `negative/N14s-ymm16-on-4bit-vex256-memory-row`, `negative/N14t-base8-on-3bit-mov-memory-row`, `negative/N14u-base16-on-4bit-mov-memory-base-row`, `negative/N14v-register8-on-mov-memory-sib-row`, `negative/N14w-register8-on-legacy-sse-mem-sib-row`, `negative/N14x-register32-on-evex-mem-sib-row`, `negative/N14y-register32-on-evex-mem-sib-nodisp-row`, `negative/N14z-register-16-on-gpr-mov-abs32-row`, `negative/N14aa-register-16-on-gpr32-mov-abs32-row`, `negative/N14ab-register-16-on-gpr16-mov-abs32-row`, `negative/N14ac-register-16-on-gpr8-mov-abs32-row`, `negative/N14ad-register-16-on-gpr8-ext-mov-mem-row`, `negative/N14ae-base-8-on-gpr8-mov-mem-nodisp-three-bit-row`, `negative/N14af-register16-on-gpr8-mov-mem-sib-three-bit-row`, `negative/N14ag-register8-on-gpr8-mov-mem-sib-three-bit-row`, `negative/N14ah-register16-on-gpr64-mov-mem-nodisp-row`, `negative/N14ai-register16-on-gpr64-mov-mem-sib-row`, `negative/N14aj-register16-on-gpr32-mov-mem-ext-row`, `negative/N14ak-register8-on-gpr32-mov-mem-low-row`, `negative/N14al-register16-on-gpr32-mov-mem-sib-ext-row`, `negative/N14am-register8-on-gpr32-mov-mem-sib-low-row`, `negative/N14an-register16-on-gpr32-mov-mem-ext-disp8-row`, `negative/N14ao-register8-on-gpr32-mov-mem-disp8-low-row`, `negative/N14ap-register16-on-gpr32-mov-mem-ext-disp32-row`, `negative/N14aq-register8-on-gpr32-mov-mem-disp32-low-row`, `negative/N14ar-register16-on-gpr32-mov-mem-sib-ext-disp8-row`, `negative/N14as-register8-on-gpr32-mov-mem-sib-disp8-low-row`, `negative/N14at-register16-on-gpr32-mov-mem-sib-ext-disp32-row`, `negative/N14au-register8-on-gpr32-mov-mem-sib-disp32-low-row`, `negative/N14av-register16-on-gpr16-mov-mem-nodisp-rex-r-row`, `negative/N14aw-register16-on-gpr16-mov-mem-disp8-rex-r-row`, `negative/N14ax-register16-on-gpr16-mov-mem-disp32-rex-r-row`, `negative/N14ay-register16-on-gpr16-mov-index-disp8-rex-rx-row`, `negative/N14az-base16-on-gpr16-mov-index-disp8-rex-rx-row`, `negative/N14ba-register16-on-gpr16-mov-index-disp8-low-row`, `negative/N14bb-register8-on-gpr16-mov-index-disp8-low-row`, `negative/N14bc-base8-on-gpr16-mov-index-disp8-low-row`, `negative/N14bd-register8-on-gpr16-mov-index-base-ext-row`, `negative/N14be-base8-on-gpr16-mov-index-ext-row`, `negative/N14bf-register8-on-gpr16-mov-index-rex-bx-row` | `E-OPERAND-004` |
| N16 | `negative/N16f-rsp-on-non-sib-form`, `negative/N16g-low-byte-number-four-without-rex`, `negative/N16h-r12-on-general-base-form`, `negative/N16i-index-rsp-excluded`, `negative/N16j-base-rsp-excluded`, `negative/N16k-low-base-on-base-ext-row`, `negative/N16l-r12-on-base-ext-row`, `negative/N16m-low-xmm-on-xmm-ext-row`, `negative/N16n-low-source-on-vex-src-ext-row`, `negative/N16o-rsp-on-no-disp-row`, `negative/N16p-rbp-on-no-disp-row`, `negative/N16q-low-base-on-no-disp-base-ext-row`, `negative/N16r-rbp-on-vex256-no-disp-row`, `negative/N16s-r12-on-vex256-base-ext-row`, `negative/N16t-high-byte-number-on-rexless-mov-memory-row`, `negative/N16u-rsp-on-mov-memory-r16-row`, `negative/N16v-low-base-on-mov-memory-base-ext-row`, `negative/N16w-r12-on-mov-memory-base-ext-row`, `negative/N16x-r12-on-widened-mov-memory-rex-row`, `negative/N16y-low-byte-number-on-mov-memory-sib-rex-row`, `negative/N16z-rsp-on-general-evex-no-displacement-row`, `negative/N16aa-index4-on-evex-mem-sib-index-row`, `negative/N16ab-base5-on-evex-no-displacement-index-row`, `negative/N16ac-index4-on-evex-mem-sib-nobase-row`, `negative/N16ad-register-0-on-gpr32-mov-abs32-ext-row`, `negative/N16ae-register-0-on-gpr16-mov-abs32-ext-row`, `negative/N16af-register-0-on-gpr8-mov-abs32-rex-row`, `negative/N16ag-register-0-on-gpr8-ext-mov-mem-row`, `negative/N16ah-base-rsp-on-gpr8-ext-mov-mem-plain-base-row`, `negative/N16ai-base-r12-on-gpr8-ext-mov-mem-plain-base-row`, `negative/N16aj-base-rbp-on-gpr8-mov-mem-nodisp-row`, `negative/N16ak-base-r13-on-gpr8-mov-mem-nodisp-ext-row`, `negative/N16al-base-rsp-on-gpr8-mov-mem-nodisp-row`, `negative/N16am-base-r12-on-gpr8-mov-mem-nodisp-ext-row`, `negative/N16an-register0-on-gpr8-mov-mem-sib-rex-row`, `negative/N16ao-base-rsp-on-gpr64-mov-mem-nodisp-row`, `negative/N16ap-base-rbp-on-gpr64-mov-mem-nodisp-row`, `negative/N16aq-base-r12-on-gpr64-mov-mem-nodisp-row`, `negative/N16ar-base-r13-on-gpr64-mov-mem-nodisp-row`, `negative/N16as-base-rsp-on-gpr32-mov-mem-low-row`, `negative/N16at-base-r12-on-gpr32-mov-mem-ext-row`, `negative/N16au-register0-on-gpr32-mov-mem-ext-row`, `negative/N16av-base0-on-gpr32-mov-mem-base-ext-row`, `negative/N16aw-register0-on-gpr32-mov-mem-sib-ext-row`, `negative/N16ax-base-rsp-on-gpr32-mov-mem-disp8-low-row`, `negative/N16ay-base-r12-on-gpr32-mov-mem-ext-disp8-row`, `negative/N16az-register0-on-gpr32-mov-mem-ext-disp8-row`, `negative/N16ba-base0-on-gpr32-mov-mem-base-ext-disp8-row`, `negative/N16bb-base-rsp-on-gpr32-mov-mem-disp32-low-row`, `negative/N16bc-base-r12-on-gpr32-mov-mem-ext-disp32-row`, `negative/N16bd-register0-on-gpr32-mov-mem-ext-disp32-row`, `negative/N16be-base0-on-gpr32-mov-mem-base-ext-disp32-row`, `negative/N16bf-register0-on-gpr32-mov-mem-sib-ext-disp8-row`, `negative/N16bg-register0-on-gpr32-mov-mem-sib-ext-disp32-row`, `negative/N16bh-rsp-on-gpr16-mov-mem-nodisp-row`, `negative/N16bi-r12-on-gpr16-mov-mem-nodisp-ext-row`, `negative/N16bj-low-base-on-gpr16-mov-mem-nodisp-ext-row`, `negative/N16bk-rbp-on-gpr16-mov-mem-nodisp-row`, `negative/N16bl-r13-on-gpr16-mov-mem-nodisp-ext-row`, `negative/N16bm-register0-on-gpr16-mov-mem-nodisp-rex-r-row`, `negative/N16bn-rsp-on-gpr16-mov-mem-nodisp-rex-r-row`, `negative/N16bo-rbp-on-gpr16-mov-mem-nodisp-rex-r-ext-row`, `negative/N16bp-register0-on-gpr16-mov-mem-disp8-rex-r-row`, `negative/N16bq-rsp-on-gpr16-mov-mem-disp8-rex-r-row`, `negative/N16br-rbp-on-gpr16-mov-mem-disp8-rex-r-ext-row`, `negative/N16bs-register0-on-gpr16-mov-mem-disp32-rex-r-row`, `negative/N16bt-rsp-on-gpr16-mov-mem-disp32-rex-r-row`, `negative/N16bu-rbp-on-gpr16-mov-mem-disp32-rex-r-ext-row`, `negative/N16bv-index4-on-gpr16-mov-index-disp8-rex-rx-row`, `negative/N16bw-register0-on-gpr16-mov-index-disp8-rex-rx-row`, `negative/N16bx-index4-on-gpr16-mov-index-disp8-low-row`, `negative/N16by-index3-on-gpr16-mov-index-ext-row`, `negative/N16bz-base3-on-gpr16-mov-index-base-ext-row`, `negative/N16ca-base3-on-gpr16-mov-index-rex-bx-row`, `negative/N16cb-index3-on-gpr16-mov-index-rex-bx-row` | `E-RANGE-004` |

`N06` (extension-list mismatch) now has an x86 case: `0.5.0` declares
`avx`/`avx512f`/`avx512vl` for its EVEX.128 row, and a plan that omits them is
`E-TARGET-001`. `N12` (relocation pair) still has no x86 case in v0: the slice
has only single-site `rel32` fixups. It is recorded as not applicable in
`06_validation_matrix.md`, not silently skipped.

See `../README.md` for naming and oracle rules.
