# Definition Format

Status: **frozen for `x86-64` `0.1.0` and `aarch64` `0.1.0`**; the same format
is intended for the other targets, whose tables wait on source data, not on an
open decision (`OD-07` is settled by ADR-0005 and pinned by ADR-0006). This
document defines the artifact a pinned `definition_identity` names. It is the
operational form of `OD-10`: the table *is* the feature surface, and a `form_id`
the table does not contain is `E-FORM-001`.

A definition is **data**. It is not a library, a plugin, or a table of callbacks
(`INV-06`). The materializer reads it, checks it, and encodes from it.

## 1. What a definition answers

Two questions, and only two:

1. Does this `form_id` exist, and what is its operand signature?
2. For each operand, which bits of the output does that operand own?

Everything else stays out: fixup descriptors (the plan owns them), layout (the
plan owns it), defaults, aliases, feature flags, and any instruction the plan did
not name. A definition that tries to answer a third question has crossed back
into selection (`INV-01`, `INV-02`).

## 2. Document shape

```json
{
  "definition_format": "fmp-def/0.1",
  "namespace": "monasm.isa.x86",
  "version": "0.1.0",
  "target_identity": { "isa_family": "x86", "isa_variant": "x86-64",
                       "execution_mode": "64", "enabled_extensions": [],
                       "byte_order": "little", "address_width": 64 },
  "forms": [ { "form_id": "...", "template": "...", "slots": [ ... ] } ]
}
```

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `definition_format` | yes | Format version of this document | A newer document is read by an older loader with different rules and accepted. |
| `namespace`, `version` | yes | Identity the plan must name | Two rule sets are loadable under one name; the plan cannot say which it was built for. |
| `target_identity` | yes | The target the table is valid for | An x86 table is applied to an `x86-32` plan, and `REX.W` is emitted for a 32-bit mode. |
| `forms` | yes | The closed form set | An empty table would accept nothing but claim to be a definition. |

`target_identity` is compared field by field with the plan's, excluding
`feature_constraints` (which the contract already requires to be empty). A
difference in `isa_family`, `isa_variant,` or `enabled_extensions` is
`E-TARGET-001`, in `execution_mode` `E-TARGET-002`, and in `byte_order` or
`address_width` `E-TARGET-004`. `E-TARGET-003` has no trigger here because a row
carries no extension requirement of its own: the table declares one
`enabled_extensions` set for the whole document. The table is never filtered per
plan: a definition covers exactly one target.

A table whose forms need an extension above the baseline declares it in
`enabled_extensions`: `0.5.0` lists `avx`, `avx512f` and `avx512vl` because its
EVEX row is `EVEX.128`, which AVX-512VL enables. This is still one set for the
whole table — no row carries a requirement of its own, so `E-TARGET-003` stays
unreachable (`04_errors.md` §2.3) and the plan/definition equality check is
`E-TARGET-001`.

There is **no digest field inside the definition**. The digest is computed over
the document and compared with `definition_identity.digest` (`E-DEF-001`); a
field that contained its own hash would have to exclude itself from its own
input, which is the kind of special case that drifts.

## 3. Forms

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `form_id` | yes | The identity a plan must name, exactly | Resolution becomes a search, and a search is a decision. |
| `template` | yes | One hex byte string; its length is the form's size, with every operand-owned bit at its base value | Without a base the loader would have to invent zeros for bits no operand writes. |
| `slots` | yes | Ordered operand signature, one entry per operand | The plan could supply operands in any order and a length check would be the only guard. |

Rules:

- `form_id` MUST follow `01_contract.md` §7. For `x86` it MUST end in
  `/legacy`, `/vex` or `/evex`; v0 carries `/legacy` in `0.1.0`–`0.4.0` and adds
  `/vex` and `/evex` in `0.5.0`.
- `size` is **not** a field: it is `len(template) / 2`. A redundant size field
  can disagree with the template, and the disagreement has no correct resolution.
- Two rows MUST NOT share a `form_id` (`E-DEF-001` at load; the plan's failure
  is `E-FORM-001`).
- A row MUST NOT be reachable from another row's signature. `rm-r64` and
  `r64-rm` are two rows; neither is a fallback for the other.
- The template's operand-owned bits are the base value the operand overwrites in
  full. For a fixup-covered field the base value MUST be zero
  (`03_fixup_model.md` §3), so the emitted byte is the fixup's alone.

## 4. Slots

```json
{ "role": "dest", "kind": "x86.gpr64", "target_type": "rm64",
  "from": "reg_number", "modifiers": [],
  "placements": [ { "bit_offset": 16, "width": 3 } ] }
```

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `role` | yes | Same closed set as the plan operand `role` | Two operands of one form become interchangeable and `src`/`dest` can swap silently. |
| `kind` | yes | Target-namespaced payload type, e.g. `x86.gpr64`, `x86.imm`, `x86.rel` | A `{"reg": 1}` payload is read as a value `1`. |
| `target_type` | yes | The slot constraint the plan operand must name | A `r64` operand fills a `rm64` slot; the check has nothing to compare. |
| `from` | yes | `reg_number` \| `operand_value` | The loader would have to guess whether `payload.reg` or `payload.value` is the number. |
| `range` | only for `operand_value` | `{signed, bits, align_bits}` | `imm8 = 300` is truncated to `0x2c` and becomes `44`. |
| `excluded` | no | Closed, strictly increasing list of exact values the slot may not carry; absent means no exclusion | `c.addi a0, 0` is inside `[-32, 31]` and encodes as `01 05`, which `llvm-objdump` calls a HINT, not the addition the plan names. |
| `placements` | yes | Ordered bit ranges, most significant operand bits first | The bit order of a split field would be a convention, not data. |
| `modifiers` | yes | The closed set of `{name, value}` pairs this slot permits; `[]` means none | An ignored `lock` emits `0xf0`-less bytes with different semantics and no error. |

`from` is a closed two-member set:

- `reg_number` — the operand's `payload.reg`, unsigned. The slot's placements
  must hold `sum(width)` bits; a register number that needs more is
  `E-OPERAND-004`. **It is never truncated**, because `r9` truncated to 3 bits is
  register 1 (`rcx`), and `48 89 c8` is a perfectly legal `movq %rcx, %rax`
  (`04_errors.md`, `E-OPERAND-004` counterexample).
- `operand_value` — the operand's `payload.value`, signed, checked against
  `range` before any bit is written.

`range_kind` is not a field: the error code follows from `role`, which is already
in the table.

| Slot role | Range violation |
|---|---|
| `target` | `E-RANGE-002` (displacement/branch offset) |
| `imm`, `disp` | `E-RANGE-001` (immediate) |

`align_bits` is checked on the value as planned: `align_bits = 0` means no check,
and a non-zero value that is not a multiple is `E-RANGE-003`. No v0 x86 slot
declares a non-zero `align_bits`, because x86 branch displacements are
byte-granular; the field exists for scaled branch fixups — AArch64 `bl`
(`align_bits = 2`) and RV64 `beq`/`jal` (`align_bits = 1`) — where the
pre-transform displacement must be instruction-aligned. The slot itself keeps
`align_bits = 0`, because it holds field content (§8.3).

`excluded` is the one place a slot may be **non-convex**, and it is data, not a
predicate (`ADR-0009`, `OD-14`). It is a closed list of exact integers, strictly
increasing, each inside the slot's representable domain: `range` for
`operand_value`, and the placements' summed width for `reg_number`. A value in
the list is rejected with `E-RANGE-004` even though `range` accepts it; an
absent key means no value is excluded, and an empty list is a definition error
because it is not a statement. The check is a lookup, never an expression
(`INV-06`), so "legal" remains decidable by inspection. No AArch64 slot declares
one; on x86 the base slots of the non-SIB rows exclude `%rsp` (`ADR-0028`) and
the three 8-bit rows use the list to keep the high-byte, REX-less low-byte and
REX low-byte number sets disjoint (`ADR-0029`);
`riscv:c.addi/rd-imm6` was the first user, excluding `0` on both slots (§8.5).

### 4.1 Placements

A placement is a bit range inside the template:

```json
{ "bit_offset": 16, "width": 3 }
```

- `bit_offset` counts from the **least significant bit of template byte 0**. Bit
  `k` therefore lives in byte `k / 8` at bit `k % 8`, and a multi-byte field is
  written little-endian, which is the only byte order v0 definitions declare
  (`byte_order: "big"` is `E-TARGET-004` against a little-endian definition).
- Placements of one slot are in **value order**: the first placement receives the
  most significant bits of the operand value. This mirrors
  `03_fixup_model.md` §3 and, like it, has no separate order field.
- The widths of one slot MUST sum to the number of bits the slot encodes: `bits`
  from `range` for `operand_value`, and the form's own register field width for
  `reg_number`.
- Placements of different slots MUST NOT overlap, and a placement MUST stay
  inside the template. Both are `E-DEF-001` at load time: a definition that
  overlaps itself has no correct output, so it is never a plan error.
- A slot MUST have at least one placement.
- A placement MAY carry `"invert": true` (default `false`), which writes its
  chunk complemented: `chunk ^= (1 << width) - 1`. This exists because EVEX and
  VEX name their extension bits inverted (`B̄`/`R̄`): `{evex} vmovaps 16(%r8),
  %xmm0` is `62 d1 7c 08 28 40 01`, with the base's fourth bit written as `0`
  into `B̄` at bit 13; a raw write would leave `P0 = f1` and encode
  `16(%rax)` (`EXP-0039`). The polarity is a fact of the encoding, so it is
  declared per placement rather than decided by the materializer
  (`ADR-0037`, `EC-40`). Inversion applies to each placement's own chunk and
  does not change the value order.

## 5. What is deliberately absent

- **No fixup descriptors.** The plan names the field descriptor, its PC rule and
  its transform; a definition that also described them would be a second source
  of truth for the same bits (`OD-02`).
- **No `encoding_choices`, no defaults, no optional bytes.** `ADR-0004` and
  `OD-11` removed the plan-side selector; a definition-side selector would
  reintroduce it one layer down.
- **No alias rows.** A `form_id` that is not in the table is rejected even if a
  near neighbour exists (`N01`).
- **No wildcard or "any register" rows.** Every row names its template.
- **No comments.** The file is JSON; the digest is computed over the canonical
  form (§6), so a comment would not survive canonicalization anyway.

## 6. Digest

`definition_identity.digest` is

```text
sha256(canonical_json(definition_document))
```

with canonical JSON exactly as `01_contract.md` §12 defines it: keys sorted by
code point, no insignificant whitespace, UTF-8 without BOM, no duplicate keys,
integers only, no trailing newline. Nothing is excluded: the document contains
nothing but the fields in §2 and §3, so every byte of it participates.

Consequences, which are the test `OD-06` asks for:

- A change to any rule — a template byte, a width, a range, a slot order —
  changes the digest and the old plan fails `E-DEF-001`.
- Reindenting the file, reordering keys, or writing it with CRLF does not change
  the digest, because canonicalization happens before hashing.
- A comment cannot exist. The "comment-only change" half of `OD-06` is therefore
  unrepresentable rather than merely ignored.

The materializer MUST refuse a definition whose declared `namespace`/`version` it
does not ship (`E-DEF-002`) before hashing, so a plan cannot pull in an arbitrary
table by digest alone.

## 7. Lookup

1. `form_id` MUST be present in `forms` (`E-FORM-001`). No normalisation, no
   case folding, no suffix repair.
2. The plan's operand list MUST match `slots` in length and role sequence
   (`E-OPERAND-002`).
3. Each operand's `kind` and `target_type` MUST equal the slot's
   (`E-OPERAND-001`).
4. Each operand's `modifiers` MUST be a subset of the slot's permitted set
   (`E-OPERAND-003`, reason `modifier not permitted`).
5. Each operand's payload shape MUST match `from` (`E-OPERAND-003`).
6. Each operand's value MUST be inside the slot's domain (`E-RANGE-001`/`002`/
   `003`/`004`); an `excluded` entry is rejected even when `range` contains it.

Only after these pass is a byte written.

## 8. v0 definition tables

Each table below is a reading aid; `definitions/<isa>/<version>.json` is
canonical, and `tools/check_definition.py` fails if a row and the JSON disagree.

| Table | Namespace | Digest |
|---|---|---|
| `definitions/x86_64/0.1.0.json` | `monasm.isa.x86` | `sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad` |
| `definitions/x86_64/0.2.0.json` | `monasm.isa.x86` | `sha256:d9c088cacb9d20dcf8b801cbdb978996ed31d2e70b631897a905d179207991ac` |
| `definitions/x86_64/0.3.0.json` | `monasm.isa.x86` | `sha256:02500bf74d5c3db7816a30aca6c9c4d8fc7c5097306bc742f51284636c487c10` |
| `definitions/x86_64/0.4.0.json` | `monasm.isa.x86` | `sha256:ee2141cbb17f338c5b4a9de0302076bb2416838c09f7c44e2ca097cb142a2682` |
| `definitions/x86_64/0.5.0.json` | `monasm.isa.x86` | `sha256:24256f0c427447ee8db5506d7b395e3682dbb3b0317f0effa1ed3c4f75cc0aeb` |
| `definitions/x86_64/0.6.0.json` | `monasm.isa.x86` | `sha256:79952b5dc726d18378651498ee35452645d08a4f7a66a133679bc86efa5839f5` |
| `definitions/x86_64/0.7.0.json` | `monasm.isa.x86` | `sha256:8c40c948a3a103b7d0668a4539f5cc8bc95e3cdba12b62c0c6a00bbc2ee92f1c` |
| `definitions/x86_64/0.8.0.json` | `monasm.isa.x86` | `sha256:e55f694ae29e90854c8352aba60202cbd060d6333aff2a69b2e54978910155f5` |
| `definitions/x86_64/0.9.0.json` | `monasm.isa.x86` | `sha256:cc538253ba2d8a111ee16a8d5a8db1aa6efaaed75270889eed20f0f2f5ed6eb8` |
| `definitions/x86_64/0.10.0.json` | `monasm.isa.x86` | `sha256:0c10ff1c373eea2fe6098e67da3047081b34a5779d9ec492c47069ac73613442` |
| `definitions/x86_64/0.11.0.json` | `monasm.isa.x86` | `sha256:d9669be62267ecd90d69dc9f936bcb947948b8c1ec7c7ba0670eb63f32de0570` |
| `definitions/x86_64/0.12.0.json` | `monasm.isa.x86` | `sha256:a74ae09e3f9d2596f2e99edde80d6a487e8596efc05d87e59d6409f82ebf35ae` |
| `definitions/x86_64/0.13.0.json` | `monasm.isa.x86` | `sha256:79eabc2d19a7cf3cac84c857afd6a11b4f15063c7526f17f8782ace0b5ea3431` |
| `definitions/x86_64/0.14.0.json` | `monasm.isa.x86` | `sha256:3126af72d83ec4ee8e0e34abfde924a73e7b41866fb2c3b8fc3152821d691a5b` |
| `definitions/x86_64/0.15.0.json` | `monasm.isa.x86` | `sha256:305e96047cf870f963c7115ec1ecb205cdb48d83e629b67d5eb8db7720a014a4` |
| `definitions/x86_64/0.16.0.json` | `monasm.isa.x86` | `sha256:64ea1acf467afb2f858a5cb2967839445a5ffecac164a5f1b61931cb8fb3b99e` |
| `definitions/x86_64/0.17.0.json` | `monasm.isa.x86` | `sha256:eb8370255811a2364550bf98ae106f8f972c9a3e54e94d1aeb98ddde921fbcd0` |
| `definitions/x86_64/0.18.0.json` | `monasm.isa.x86` | `sha256:e1281b0c11d7e2bed9bd1ec7fa5404dadca2c82959376cbe3edfd9ff56b9e33d` |
| `definitions/x86_64/0.19.0.json` | `monasm.isa.x86` | `sha256:dddc678fe0abc6fa03c2e61c8fcafef2570b496775a11a25e1ab29e01bfe5130` |
| `definitions/x86_64/0.20.0.json` | `monasm.isa.x86` | `sha256:b8bd1ed3ed38d71f6b19cc1854c9252df13850127c4e9433981a3a45f49d0f99` |
| `definitions/x86_64/0.21.0.json` | `monasm.isa.x86` | `sha256:30af3fec5c2f50e3ab30fb30d32e6b2e71f4520dbdb2660c6c9de1767b7b1160` |
| `definitions/x86_64/0.22.0.json` | `monasm.isa.x86` | `sha256:61c7cd1c940a7b22838a2c3418ba54031a20c6b227203fb9b4a57875f1c36b58` |
| `definitions/x86_64/0.23.0.json` | `monasm.isa.x86` | `sha256:507e55c84cc80cf8bd9be10a6c6e4f7cff4999084fb41b3138df60b68a283962` |
| `definitions/x86_64/0.24.0.json` | `monasm.isa.x86` | `sha256:2521f2dcc9636c1e3a671bbfbf224dcaecb741014bf65b0660ae5cc1c8c4aca3` |
| `definitions/aarch64/0.1.0.json` | `monasm.isa.aarch64` | `sha256:96f87aa2fbac9f27261b99a0ed2d72a4f3e8b8c9be3bc1e11ba72201a9afc15e` |
| `definitions/aarch64/0.2.0.json` | `monasm.isa.aarch64` | `sha256:169e4bf6d45d83a74be3d185d7394b9ed042dbf52f27ec58d975ca5a1be354ed` |
| `definitions/aarch64/0.3.0.json` | `monasm.isa.aarch64` | `sha256:71af93c0a1b91d67cb97af1d27dda249c3ce7bb2b6c8ca13a10154891b7728cb` |
| `definitions/aarch64/0.4.0.json` | `monasm.isa.aarch64` | `sha256:14d6c2b66669ff45401b8b69d5ce111c13ce6e8ef44f04440b961b8f2133bc78` |
| `definitions/aarch64/0.5.0.json` | `monasm.isa.aarch64` | `sha256:9cec1688b5b9d1a9bd9299e6d0a155885053e7b228ff6eee88f40cef6f34e23e` |
| `definitions/aarch64/0.6.0.json` | `monasm.isa.aarch64` | `sha256:1151944e5855c08bd3d96074ace3ca787be6b7284c5d3e84654a257ab2055964` |
| `definitions/aarch64/0.7.0.json` | `monasm.isa.aarch64` | `sha256:1bb920356476cea20688b2d6596d787f3cf99aedebe7240b1af8227f64d29053` |
| `definitions/aarch64/0.8.0.json` | `monasm.isa.aarch64` | `sha256:9f82b566af004aaa9f0471151497d65acb45c3a7b46e4240345d21f4e330bc35` |
| `definitions/aarch64/0.9.0.json` | `monasm.isa.aarch64` | `sha256:99728cd9bd85b8b0768e700e15dd6263171d6261c385ac15ceeb5df6d2cafcff` |
| `definitions/aarch64/0.10.0.json` | `monasm.isa.aarch64` | `sha256:e958d69b4ba93222e7621a1f5c3ebd056ce929e2974a961a03abb7b66f0b247b` |
| `definitions/aarch64/0.11.0.json` | `monasm.isa.aarch64` | `sha256:c5a9aec943f9b195c400380b8416bf63cba944da3fdf0203f90de5baff295002` |
| `definitions/aarch64/0.12.0.json` | `monasm.isa.aarch64` | `sha256:8a428926568b99f0674785cc674bc066adc452216131706d458b9e3390da03b6` |
| `definitions/aarch64/0.13.0.json` | `monasm.isa.aarch64` | `sha256:d3876dd37a8441057b586312b3bee410e39594c64806b2c5c59960c06f9c7a5f` |
| `definitions/aarch64/0.14.0.json` | `monasm.isa.aarch64` | `sha256:a90ceac19824fbb00731e040346daa191973652e58522fab72336e24f769a5ba` |
| `definitions/aarch64/0.15.0.json` | `monasm.isa.aarch64` | `sha256:422ebb83b897b18e010da37539796b0b97cfc9018a47209fc4a6ddc5b14af5d3` |
| `definitions/aarch64/0.16.0.json` | `monasm.isa.aarch64` | `sha256:1e83c6cad91594e8315500f39d0bcffa235edc90c5f47c012555c077a8dbc457` |
| `definitions/aarch64/0.17.0.json` | `monasm.isa.aarch64` | `sha256:de2c53e1871f5c24f6af73082dcc402729786d2e6e2495f84e3ed553adb4e4ed` |
| `definitions/rv64/0.1.0.json` | `monasm.isa.riscv` | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` |
| `definitions/rv64/0.2.0.json` | `monasm.isa.riscv` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |

A plan names its `namespace`, `version` and digest in `definition_identity`.

### 8.1 `x86-64` `0.1.0` … `0.24.0`

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `x86:mov/rm-r64/legacy` | `4889c0` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 3 | `EC-06`, `EC-27` — 4-bit slots from `0.6.0` |
| `x86:mov/r64-rm/legacy` | `488bc0` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; src: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` | 3 | `EC-06`, `EC-27` — 4-bit slots from `0.6.0` |
| `x86:add/rm64-imm8/legacy` | `4883c000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | `EC-01`, `EC-06` — 4-bit dest from `0.6.0` |
| `x86:add/rm64-imm32/legacy` | `4881c000000000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | `EC-01`, `EC-04`, `EC-06` — 4-bit dest from `0.6.0` |
| `x86:add/rax-imm32/legacy` | `480500000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | `EC-04` |
| `x86:jmp/rel8/legacy` | `eb00` | target: `x86.rel`/`rel8` → `[8,8]` | 2 | `EC-03` |
| `x86:jmp/rel32/legacy` | `e900000000` | target: `x86.rel`/`rel32` → `[8,32]` | 5 | `EC-03` |
| `x86:mov/r64-riprel32/legacy` | `488b0500000000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `EC-06`, `EC-34`, `X86-P6` — 4-bit dest from `0.6.0` |
| `x86:mov/riprel32-r64/legacy` | `48890500000000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `EC-06`, `EC-34`, `X86-P6` — 4-bit src from `0.6.0` |
| `x86:mov/r64-base-disp8/legacy` | `488b4000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit from `0.7.0` |
| `x86:mov/r64-base-disp32/legacy` | `488b8000000000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit from `0.7.0` |
| `x86:mov/r64-rsp-disp8/legacy` | `488b442400` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit dest from `0.7.0` |
| `x86:mov/r64-r12-disp8/legacy` | `498b442400` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-06`, `EC-35`, `X86-P11` — `0.7.0`+ |
| `x86:mov/r64-rsp-disp32/legacy` | `488b842400000000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit dest from `0.7.0` |
| `x86:mov/r64-r12-disp32/legacy` | `498b842400000000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-06`, `EC-35`, `X86-P11` — `0.7.0`+ |
| `x86:mov/base-disp8-r64/legacy` | `48894000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit from `0.7.0` |
| `x86:mov/base-disp32-r64/legacy` | `48898000000000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit from `0.7.0` |
| `x86:mov/rsp-disp8-r64/legacy` | `4889442400` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit src from `0.7.0` |
| `x86:mov/r12-disp8-r64/legacy` | `4989442400` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-06`, `EC-35`, `X86-P11` — `0.7.0`+ |
| `x86:mov/rsp-disp32-r64/legacy` | `4889842400000000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-35`, `X86-P4` — 4-bit src from `0.7.0` |
| `x86:mov/r12-disp32-r64/legacy` | `4989842400000000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-06`, `EC-35`, `X86-P11` — `0.7.0`+ |
| `x86:mov/rm16-r16/legacy` | `6689c0` | dest: `x86.gpr16`/`rm16` → `[16,3]`; src: `x86.gpr16`/`r16` → `[19,3]` | 3 | `EC-36`, `X86-P5` — `0.4.0`+ |
| `x86:mov/r16-rm16/legacy` | `668bc0` | dest: `x86.gpr16`/`r16` → `[19,3]`; src: `x86.gpr16`/`rm16` → `[16,3]` | 3 | `EC-36`, `X86-P5` — `0.4.0`+ |
| `x86:mov/rm8h-r8h/legacy` | `88e4` | dest: `x86.gpr8h`/`rm8h` → `[8,3]` (excl 0, 1, 2, 3); src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3) | 2 | `EC-36`, `X86-P5` — `0.4.0`+ |
| `x86:mov/rm8-r8/legacy` | `88c0` | dest: `x86.gpr8`/`rm8` → `[8,3]` (excl 4, 5, 6, 7); src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7) | 2 | `EC-36`, `X86-P5` — `0.4.0`+ |
| `x86:mov/rm8-r8-rex/legacy` | `4088e0` | dest: `x86.gpr8`/`rm8` → `[16,3]` (excl 0, 1, 2, 3); src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3) | 3 | `EC-36`, `X86-P5` — `0.4.0`+ |
| `x86:movaps/xmm-xmm/legacy` | `0f28c0` | dest: `x86.xmm`/`xmm` → `[19,3]`; src: `x86.xmm`/`xmm` → `[16,3]` | 3 | `EC-09`, `X86-P9` — `0.5.0`+ |
| `x86:vmovaps/xmm-xmm/vex` | `c5f828c0` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; src: `x86.xmm`/`xmm` → `[24,3]` | 4 | `EC-09`, `X86-P15` — dest 4-bit from `0.11.0`; src stays 3-bit |
| `x86:vmovaps/xmm-xmm/evex` | `62f17c0828c0` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; src: `x86.xmm`/`xmm` → `[14,1]` inverted, `[13,1]` inverted, `[40,3]` | 6 | `EC-06`, `EC-09`, `EC-40`, `X86-P15`, `X86-P17` — 4-bit from `0.11.0`, 5-bit from `0.13.0` |
| `x86:mov/r64-base-index-disp8/legacy` | `488b440000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-35`, `EC-37`, `X86-P12` — `0.8.0`+ |
| `x86:mov/r64-base-index-disp32/legacy` | `488b840000000000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-35`, `EC-37`, `X86-P12` — `0.8.0`+ |
| `x86:mov/base-index-disp8-r64/legacy` | `4889440000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-35`, `EC-37`, `X86-P12` — `0.8.0`+ |
| `x86:mov/base-index-disp32-r64/legacy` | `4889840000000000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-35`, `EC-37`, `X86-P12` — `0.8.0`+ |
| `x86:movaps/xmm-base-disp8/legacy` | `0f284000` | dest: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-09`, `EC-35`, `EC-38`, `X86-P13` — `0.9.0`+ |
| `x86:movaps/xmm-base-disp32/legacy` | `0f288000000000` | dest: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-09`, `EC-35`, `EC-38`, `X86-P13` — `0.9.0`+ |
| `x86:movaps/base-disp8-xmm/legacy` | `0f294000` | src: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P13` — `0.9.0`+ |
| `x86:movaps/base-disp32-xmm/legacy` | `0f298000000000` | src: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P13` — `0.9.0`+ |
| `x86:vmovaps/xmm-base-disp8/vex` | `c5f8284000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-09`, `EC-35`, `EC-38`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:vmovaps/xmm-base-disp32/vex` | `c5f8288000000000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-09`, `EC-35`, `EC-38`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:vmovaps/base-disp8-xmm/vex` | `c5f8294000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:vmovaps/base-disp32-xmm/vex` | `c5f8298000000000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:vmovaps/xmm-base-disp8x16/evex` | `62f17c08284000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp8x16` → `[48,8]` | 7 | `EC-09`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P15`, `X86-P17` — `xmm` 4-bit from `0.11.0`, 5-bit from `0.13.0`; base 4-bit from `0.10.0` |
| `x86:vmovaps/xmm-base-disp32/evex` | `62f17c08288000000000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-09`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P15`, `X86-P17` — `xmm` 4-bit from `0.11.0`, 5-bit from `0.13.0`; base 4-bit from `0.10.0` |
| `x86:vmovaps/base-disp8x16-xmm/evex` | `62f17c08294000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp8x16` → `[48,8]` | 7 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P15`, `X86-P17` — `xmm` 4-bit from `0.11.0`, 5-bit from `0.13.0`; base 4-bit from `0.10.0` |
| `x86:vmovaps/base-disp32-xmm/evex` | `62f17c08298000000000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P15`, `X86-P17` — `xmm` 4-bit from `0.11.0`, 5-bit from `0.13.0`; base 4-bit from `0.10.0` |
| `x86:movaps/xmm-base-ext-disp8/legacy` | `400f284000` | dest: `x86.xmm`/`xmm` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-09`, `EC-35`, `EC-38`, `X86-P14` — `0.10.0`+ |
| `x86:movaps/xmm-base-ext-disp32/legacy` | `400f288000000000` | dest: `x86.xmm`/`xmm` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-09`, `EC-35`, `EC-38`, `X86-P14` — `0.10.0`+ |
| `x86:movaps/base-ext-disp8-xmm/legacy` | `400f294000` | src: `x86.xmm`/`xmm` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-06`, `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P14` — `0.10.0`+ |
| `x86:movaps/base-ext-disp32-xmm/legacy` | `400f298000000000` | src: `x86.xmm`/`xmm` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-06`, `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P14` — `0.10.0`+ |
| `x86:vmovaps/xmm-base-ext-disp8/vex` | `c4c178284000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-09`, `EC-35`, `EC-38`, `EC-40`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:vmovaps/xmm-base-ext-disp32/vex` | `c4c178288000000000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-09`, `EC-35`, `EC-38`, `EC-40`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:vmovaps/base-ext-disp8-xmm/vex` | `c4c178294000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-40`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:vmovaps/base-ext-disp32-xmm/vex` | `c4c178298000000000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-40`, `X86-P15` — `xmm` 4-bit from `0.11.0` |
| `x86:movaps/xmm-ext-xmm/legacy` | `400f28c0` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); src: `x86.xmm`/`xmm` → `[24,3]` | 4 | `EC-06`, `EC-09`, `X86-P15` — dest `REX.R` from `0.11.0` |
| `x86:movaps/xmm-xmm-ext/legacy` | `400f28c0` | dest: `x86.xmm`/`xmm` → `[27,3]`; src: `x86.xmm`/`xmm` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-06`, `EC-09`, `X86-P15` — src `REX.B` from `0.11.0` |
| `x86:movaps/xmm-ext-xmm-ext/legacy` | `400f28c0` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); src: `x86.xmm`/`xmm` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-06`, `EC-09`, `X86-P15` — both `REX` bits from `0.11.0` |
| `x86:vmovaps/xmm-xmm-src-ext/vex` | `c5f829c0` | dest: `x86.xmm`/`xmm` → `[24,3]`; src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-09`, `EC-40`, `X86-P15` — `R̄` + opcode 29 from `0.11.0` |
| `x86:vmovaps/xmm-xmm-both-ext/vex` | `c4e17828c0` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); src: `x86.xmm`/`xmm` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 5 | `EC-09`, `EC-40`, `X86-P15` — `R̄`/`B̄` from `0.11.0` |
| `x86:movaps/xmm-ext-base-disp8/legacy` | `400f284000` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-09`, `EC-35`, `EC-38`, `X86-P15` — dest `REX.R` + 4-bit base from `0.11.0` |
| `x86:movaps/xmm-ext-base-disp32/legacy` | `400f288000000000` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-09`, `EC-35`, `EC-38`, `X86-P15` — dest `REX.R` + 4-bit base from `0.11.0` |
| `x86:movaps/base-disp8-xmm-ext/legacy` | `400f294000` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-06`, `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P15` — src `REX.R` + 4-bit base from `0.11.0` |
| `x86:movaps/base-disp32-xmm-ext/legacy` | `400f298000000000` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-06`, `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P15` — src `REX.R` + 4-bit base from `0.11.0` |
| `x86:movaps/xmm-base/legacy` | `0f2800` | dest: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4, 5) | 3 | `EC-02`, `EC-09`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:movaps/base-xmm/legacy` | `0f2900` | src: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4, 5) | 3 | `EC-02`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:movaps/xmm-ext-base/legacy` | `440f2800` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 4, 5, 12, 13) | 4 | `EC-02`, `EC-06`, `EC-09`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:movaps/base-xmm-ext/legacy` | `440f2900` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 4, 5, 12, 13) | 4 | `EC-02`, `EC-06`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:movaps/xmm-base-ext/legacy` | `410f2800` | dest: `x86.xmm`/`xmm` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 4 | `EC-02`, `EC-06`, `EC-09`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:movaps/base-ext-xmm/legacy` | `410f2900` | src: `x86.xmm`/`xmm` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 4 | `EC-02`, `EC-06`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:vmovaps/xmm-base/vex` | `c5f82800` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) | 4 | `EC-02`, `EC-09`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:vmovaps/base-xmm/vex` | `c5f82900` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) | 4 | `EC-02`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:vmovaps/xmm-base-ext/vex` | `c4c1782800` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 12, 13) | 5 | `EC-02`, `EC-09`, `EC-35`, `EC-40`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:vmovaps/base-ext-xmm/vex` | `c4c1782900` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 12, 13) | 5 | `EC-02`, `EC-09`, `EC-27`, `EC-35`, `EC-40`, `X86-P16` — `mod = 00` from `0.12.0` |
| `x86:vmovaps/xmm-base/evex` | `62f17c082800` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 5, 12, 13) | 6 | `EC-02`, `EC-09`, `EC-34`, `EC-35`, `EC-40`, `X86-P16`, `X86-P17` — `mod = 00` from `0.12.0`; `xmm` 5-bit from `0.13.0` |
| `x86:vmovaps/base-xmm/evex` | `62f17c082900` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 5, 12, 13) | 6 | `EC-02`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `EC-40`, `X86-P16`, `X86-P17` — `mod = 00` from `0.12.0`; `xmm` 5-bit from `0.13.0` |
| `x86:vmovaps/ymm-ymm/vex` | `c5fc28c0` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]`; src: `x86.ymm`/`ymm` → `[24,3]` | 4 | `EC-09`, `X86-P18` — `L = 1` from `0.14.0`; dest 4-bit, src 3-bit |
| `x86:vmovaps/ymm-ymm-src-ext/vex` | `c57c29c0` | dest: `x86.ymm`/`ymm` → `[24,3]`; src: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-09`, `EC-40`, `X86-P18` — high source via opcode 29 |
| `x86:vmovaps/ymm-ymm-both-ext/vex` | `c4417c28c0` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); src: `x86.ymm`/`ymm` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 5 | `EC-09`, `EC-40`, `X86-P18` — three-byte `C4` when both are high |
| `x86:vmovaps/ymm-ymm/evex` | `62f17c2828c0` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; src: `x86.ymm`/`ymm` → `[14,1]` inverted, `[13,1]` inverted, `[40,3]` | 6 | `EC-06`, `EC-09`, `EC-40`, `X86-P18` — `L'L = 10` from `0.14.0` |
| `x86:vmovaps/zmm-zmm/evex` | `62f17c4828c0` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; src: `x86.zmm`/`zmm` → `[14,1]` inverted, `[13,1]` inverted, `[40,3]` | 6 | `EC-06`, `EC-09`, `EC-40`, `X86-P18` — `L'L = 11` from `0.14.0`; no VEX or legacy `zmm` |
| `x86:vmovaps/ymm-base-disp8x32/evex` | `62f17c28284000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp8x32` → `[48,8]` | 7 | `EC-09`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/ymm-base-disp32/evex` | `62f17c28288000000000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-09`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/base-disp8x32-ymm/evex` | `62f17c28294000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp8x32` → `[48,8]` | 7 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/base-disp32-ymm/evex` | `62f17c28298000000000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/ymm-base/evex` | `62f17c282800` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 5, 12, 13) | 6 | `EC-02`, `EC-09`, `EC-34`, `EC-35`, `EC-40`, `X86-P19` |
| `x86:vmovaps/base-ymm/evex` | `62f17c282900` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 5, 12, 13) | 6 | `EC-02`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `EC-40`, `X86-P19` |
| `x86:vmovaps/zmm-base-disp8x64/evex` | `62f17c48284000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp8x64` → `[48,8]` | 7 | `EC-09`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/zmm-base-disp32/evex` | `62f17c48288000000000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-09`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/base-disp8x64-zmm/evex` | `62f17c48294000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp8x64` → `[48,8]` | 7 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/base-disp32-zmm/evex` | `62f17c48298000000000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-39`, `EC-40`, `X86-P19` |
| `x86:vmovaps/zmm-base/evex` | `62f17c482800` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 5, 12, 13) | 6 | `EC-02`, `EC-09`, `EC-34`, `EC-35`, `EC-40`, `X86-P19` |
| `x86:vmovaps/base-zmm/evex` | `62f17c482900` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[40,3]` (excl 4, 5, 12, 13) | 6 | `EC-02`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `EC-40`, `X86-P19` |
| `x86:vmovaps/ymm-base-disp8/vex` | `c5fc284000` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-09`, `EC-35`, `EC-38`, `X86-P20` |
| `x86:vmovaps/ymm-base-disp32/vex` | `c5fc288000000000` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-09`, `EC-35`, `EC-38`, `X86-P20` |
| `x86:vmovaps/base-disp8-ymm/vex` | `c5fc294000` | src: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P20` |
| `x86:vmovaps/base-disp32-ymm/vex` | `c5fc298000000000` | src: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `X86-P20` |
| `x86:vmovaps/ymm-base-ext-disp8/vex` | `c4c17c284000` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-09`, `EC-35`, `EC-38`, `EC-40`, `X86-P20` |
| `x86:vmovaps/ymm-base-ext-disp32/vex` | `c4c17c288000000000` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-09`, `EC-35`, `EC-38`, `EC-40`, `X86-P20` |
| `x86:vmovaps/base-ext-disp8-ymm/vex` | `c4c17c294000` | src: `x86.ymm`/`ymm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-40`, `X86-P20` |
| `x86:vmovaps/base-ext-disp32-ymm/vex` | `c4c17c298000000000` | src: `x86.ymm`/`ymm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-09`, `EC-27`, `EC-35`, `EC-38`, `EC-40`, `X86-P20` |
| `x86:vmovaps/ymm-base/vex` | `c5fc2800` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) | 4 | `EC-02`, `EC-09`, `EC-34`, `EC-35`, `X86-P20` |
| `x86:vmovaps/base-ymm/vex` | `c5fc2900` | src: `x86.ymm`/`ymm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) | 4 | `EC-02`, `EC-09`, `EC-27`, `EC-34`, `EC-35`, `X86-P20` |
| `x86:vmovaps/ymm-base-ext/vex` | `c4c17c2800` | dest: `x86.ymm`/`ymm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 12, 13) | 5 | `EC-02`, `EC-09`, `EC-35`, `EC-40`, `X86-P20` |
| `x86:vmovaps/base-ext-ymm/vex` | `c4c17c2900` | src: `x86.ymm`/`ymm` → `[15,1]` inverted, `[35,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[32,3]` (excl 12, 13) | 5 | `EC-02`, `EC-09`, `EC-27`, `EC-35`, `EC-40`, `X86-P20` |
| `x86:mov/r16-base-disp8/legacy` | `668b4000` | dest: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/r16-base-disp32/legacy` | `668b8000000000` | dest: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/base-disp8-r16/legacy` | `66894000` | src: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/base-disp32-r16/legacy` | `66898000000000` | src: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-36, X86-P21 |
| `x86:mov/r8-base-disp8/legacy` | `8a4000` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8-base-disp32/legacy` | `8a8000000000` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp8-r8/legacy` | `884000` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp32-r8/legacy` | `888000000000` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8h-base-disp8/legacy` | `8a6000` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8h-base-disp32/legacy` | `8aa000000000` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp8-r8h/legacy` | `886000` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/base-disp32-r8h/legacy` | `88a000000000` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | EC-02, EC-27, EC-28, EC-36, X86-P21 |
| `x86:mov/r8-base-disp8-rex/legacy` | `408a6000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 — 4-bit base from 0.18.0 |
| `x86:mov/r8-base-disp32-rex/legacy` | `408aa000000000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 — 4-bit base from 0.18.0 |
| `x86:mov/base-disp8-r8-rex/legacy` | `40886000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 — 4-bit base from 0.18.0 |
| `x86:mov/base-disp32-r8-rex/legacy` | `4088a000000000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-28, EC-36, X86-P21, X86-P22 — 4-bit base from 0.18.0 |
| `x86:mov/r16-base-ext-disp8/legacy` | `66418b4000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r16-base-ext-disp32/legacy` | `66418b8000000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp8-r16/legacy` | `6641894000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp32-r16/legacy` | `6641898000000000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-06, EC-27, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r8-base-ext-disp8/legacy` | `418a4000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r8-base-ext-disp32/legacy` | `418a8000000000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp8-r8/legacy` | `41884000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/base-ext-disp32-r8/legacy` | `41888000000000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-06, EC-27, EC-28, EC-35, EC-36, EC-38, X86-P22 |
| `x86:mov/r16-rsp-disp8/legacy` | `668b442400` | dest: `x86.gpr16`/`r16` → `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r16-rsp-disp32/legacy` | `668b842400000000` | dest: `x86.gpr16`/`r16` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r16-r12-disp8/legacy` | `66418b442400` | dest: `x86.gpr16`/`r16` → `[27,3]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r16-r12-disp32/legacy` | `66418b842400000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r16/legacy` | `6689442400` | src: `x86.gpr16`/`r16` → `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r16/legacy` | `6689842400000000` | src: `x86.gpr16`/`r16` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp8-r16/legacy` | `664189442400` | src: `x86.gpr16`/`r16` → `[27,3]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp32-r16/legacy` | `664189842400000000` | src: `x86.gpr16`/`r16` → `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-27, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp8/legacy` | `8a442400` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp32/legacy` | `8a842400000000` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp8/legacy` | `418a442400` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp32/legacy` | `418a842400000000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r8/legacy` | `88442400` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r8/legacy` | `88842400000000` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp8-r8/legacy` | `4188442400` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp32-r8/legacy` | `4188842400000000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8h-rsp-disp8/legacy` | `8a642400` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8h-rsp-disp32/legacy` | `8aa42400000000` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r8h/legacy` | `88642400` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r8h/legacy` | `88a42400000000` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp8-rex/legacy` | `408a642400` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-rsp-disp32-rex/legacy` | `408aa42400000000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp8-rex/legacy` | `418a642400` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r8-r12-disp32-rex/legacy` | `418aa42400000000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp8-r8-rex/legacy` | `4088642400` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/rsp-disp32-r8-rex/legacy` | `4088a42400000000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp8-r8-rex/legacy` | `4188642400` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:mov/r12-disp32-r8-rex/legacy` | `4188a42400000000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-27, EC-28, EC-35, EC-36, X86-P23 |
| `x86:movaps/xmm-rsp-disp8/legacy` | `0f28442400` | dest: `x86.xmm`/`xmm` → `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/xmm-rsp-disp32/legacy` | `0f28842400000000` | dest: `x86.xmm`/`xmm` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/xmm-r12-disp8/legacy` | `410f28442400` | dest: `x86.xmm`/`xmm` → `[27,3]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/xmm-r12-disp32/legacy` | `410f28842400000000` | dest: `x86.xmm`/`xmm` → `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P24 |
| `x86:movaps/rsp-disp8-xmm/legacy` | `0f29442400` | src: `x86.xmm`/`xmm` → `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:movaps/rsp-disp32-xmm/legacy` | `0f29842400000000` | src: `x86.xmm`/`xmm` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:movaps/r12-disp8-xmm/legacy` | `410f29442400` | src: `x86.xmm`/`xmm` → `[27,3]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-06, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:movaps/r12-disp32-xmm/legacy` | `410f29842400000000` | src: `x86.xmm`/`xmm` → `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-06, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-rsp-disp8/vex` | `c5f828442400` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-rsp-disp32/vex` | `c5f828842400000000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-r12-disp8/vex` | `c4c17828442400` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-r12-disp32/vex` | `c4c17828842400000000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | EC-02, EC-06, EC-09, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/rsp-disp8-xmm/vex` | `c5f829442400` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/rsp-disp32-xmm/vex` | `c5f829842400000000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/r12-disp8-xmm/vex` | `c4c17829442400` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | EC-02, EC-06, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/r12-disp32-xmm/vex` | `c4c17829842400000000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[35,3]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | EC-02, EC-06, EC-09, EC-27, EC-35, EC-38, X86-P24 |
| `x86:vmovaps/xmm-rsp-disp8x16/evex` | `62f17c0828442400` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x16` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-rsp-disp32/evex` | `62f17c0828842400000000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-r12-disp8x16/evex` | `62d17c0828442400` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x16` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-r12-disp32/evex` | `62d17c0828842400000000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp8x16-xmm/evex` | `62f17c0829442400` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x16` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp32-xmm/evex` | `62f17c0829842400000000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp8x16-xmm/evex` | `62d17c0829442400` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x16` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp32-xmm/evex` | `62d17c0829842400000000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-rsp-disp8x32/evex` | `62f17c2828442400` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x32` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-rsp-disp32/evex` | `62f17c2828842400000000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-r12-disp8x32/evex` | `62d17c2828442400` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x32` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/ymm-r12-disp32/evex` | `62d17c2828842400000000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp8x32-ymm/evex` | `62f17c2829442400` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x32` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp32-ymm/evex` | `62f17c2829842400000000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp8x32-ymm/evex` | `62d17c2829442400` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x32` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp32-ymm/evex` | `62d17c2829842400000000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-rsp-disp8x64/evex` | `62f17c4828442400` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x64` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-rsp-disp32/evex` | `62f17c4828842400000000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-r12-disp8x64/evex` | `62d17c4828442400` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x64` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/zmm-r12-disp32/evex` | `62d17c4828842400000000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp8x64-zmm/evex` | `62f17c4829442400` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x64` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/rsp-disp32-zmm/evex` | `62f17c4829842400000000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp8x64-zmm/evex` | `62d17c4829442400` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp8x64` → `[56,8]` | 8 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/r12-disp32-zmm/evex` | `62d17c4829842400000000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | EC-09, EC-35, EC-38, EC-39, X86-P25 |
| `x86:vmovaps/xmm-rsp/evex` | `62f17c08280424` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/xmm-r12/evex` | `62d17c08280424` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/rsp-xmm/evex` | `62f17c08290424` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/r12-xmm/evex` | `62d17c08290424` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/ymm-rsp/evex` | `62f17c28280424` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/ymm-r12/evex` | `62d17c28280424` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/rsp-ymm/evex` | `62f17c28290424` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/r12-ymm/evex` | `62d17c28290424` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/zmm-rsp/evex` | `62f17c48280424` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/zmm-r12/evex` | `62d17c48280424` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/rsp-zmm/evex` | `62f17c48290424` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/r12-zmm/evex` | `62d17c48290424` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]` | 7 | EC-09, EC-35, EC-38, X86-P26 |
| `x86:vmovaps/xmm-base-index/evex` | `62f17c08280400` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]` (excl 5, 13); index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]` | 7 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/xmm-base-index-disp8x16/evex` | `62f17c0828440000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp8x16` → `[56,8]` | 8 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-39`, `EC-40`, `X86-P27` |
| `x86:vmovaps/xmm-base-index-disp32/evex` | `62f17c0828840000000000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-xmm/evex` | `62f17c08290400` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]` (excl 5, 13); index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]` | 7 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-disp8x16-xmm/evex` | `62f17c0829440000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp8x16` → `[56,8]` | 8 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-39`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-disp32-xmm/evex` | `62f17c0829840000000000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/ymm-base-index/evex` | `62f17c28280400` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]` (excl 5, 13); index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]` | 7 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/ymm-base-index-disp8x32/evex` | `62f17c2828440000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp8x32` → `[56,8]` | 8 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-39`, `EC-40`, `X86-P27` |
| `x86:vmovaps/ymm-base-index-disp32/evex` | `62f17c2828840000000000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-ymm/evex` | `62f17c28290400` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]` (excl 5, 13); index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]` | 7 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-disp8x32-ymm/evex` | `62f17c2829440000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp8x32` → `[56,8]` | 8 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-39`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-disp32-ymm/evex` | `62f17c2829840000000000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/zmm-base-index/evex` | `62f17c48280400` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]` (excl 5, 13); index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]` | 7 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/zmm-base-index-disp8x64/evex` | `62f17c4828440000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp8x64` → `[56,8]` | 8 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-39`, `EC-40`, `X86-P27` |
| `x86:vmovaps/zmm-base-index-disp32/evex` | `62f17c4828840000000000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-zmm/evex` | `62f17c48290400` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]` (excl 5, 13); index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]` | 7 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-disp8x64-zmm/evex` | `62f17c4829440000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp8x64` → `[56,8]` | 8 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-39`, `EC-40`, `X86-P27` |
| `x86:vmovaps/base-index-disp32-zmm/evex` | `62f17c4829840000000000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; base: `x86.gpr64`/`rm64` → `[13,1]` inverted, `[48,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P27` |
| `x86:vmovaps/xmm-index-disp32/evex` | `62f17c0828040500000000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P28` |
| `x86:vmovaps/index-disp32-xmm/evex` | `62f17c0829040500000000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P28` |
| `x86:vmovaps/ymm-index-disp32/evex` | `62f17c2828040500000000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P28` |
| `x86:vmovaps/index-disp32-ymm/evex` | `62f17c2829040500000000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P28` |
| `x86:vmovaps/zmm-index-disp32/evex` | `62f17c4828040500000000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P28` |
| `x86:vmovaps/index-disp32-zmm/evex` | `62f17c4829040500000000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; index: `x86.gpr64`/`sib_index` → `[14,1]` inverted, `[51,3]` (excl 4); imm: `x86.scale`/`scale2` → `[54,2]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P28` |

Placements are written `[bit_offset, width]`, with ` inverted` appended when the
chunk is complemented. In the legacy SSE row
`[16,3]` is the low three bits of byte 2, which is `ModRM.rm`, and `[19,3]`
is `ModRM.reg`; the VEX and EVEX rows are the same two fields at `[24,3]`/
`[27,3]` and `[40,3]`/`[43,3]`, because the prefix length moves `ModRM`.
`[24,8]` is byte 3. The `0.10.0` extension rows move `ModRM` one byte further
(`[24,3]`/`[27,3]` after `40 0F 28`, `[32,3]`/`[35,3]` after `C4 C1 78`), and
the base's fourth bit sits at `[0,1]` (legacy `REX.B`) or `[13,1]` inverted
(VEX and EVEX `B̄`). The `0.11.0` rows put the `xmm` register's fourth bit in
`REX.R` at `[2,1]` or `REX.B` at `[0,1]` (legacy), or in the inverted `R̄` at
`[15,1]` when the register is `ModRM.reg` and the inverted `B̄` at `[13,1]`
when it is `ModRM.rm` (EVEX register-direct source, and every VEX/EVEX base).
`0.13.0` adds the fifth bit to the EVEX `xmm` slot: the inverted `R̄'` at
`[12,1]` for `ModRM.reg`, and, for the register-direct source, the inverted
`X̄` at `[14,1]` before the `B̄`. A memory row has no `SIB` field, so `X̄`
there is unused and keeps its template value.
In the register-to-register rows the two `ModRM` bits
above them (`bits 6–7` of `ModRM`) are `mod = 0b11`, part of the template and
not owned by any operand; the memory rows fix `mod = 0b00`/`0b01`/`0b10` the
same way.

`x86:add/rax-imm32/legacy` has no `dest` slot: the register is fixed by the
opcode (`REX.W 05 id`), which is exactly why `rax-imm32` and `rm64-imm32` are two
`form_id`s and not two choices (`01_contract.md` §7).

The register field of the six register-direct `0.1.0`–`0.5.0` rows is 3 bits wide,
so `r8`–`r15` are not encodable there: the template's `REX` byte is `0x48`, and
no extension bit is declared for those registers. A plan that names
`mov rax, r9` against `0.5.0` is rejected `E-OPERAND-004`; it is not emitted as
`48 89 c8`, which decodes as `movq %rcx, %rax`. `0.6.0` widens those slots to
four bits (`ADR-0033`); a plan that names `0.5.0` keeps the 3-bit table. `0.7.0`
does the same for the base+displacement rows (`ADR-0034`): the register operand
is `[2,1]` + `[19,3]`, and the base is `[0,1]` + `[16,3]`; `0.6.0` and earlier
keep the 3-bit reading.

Every row is verified against `llvm-mc` 23.1.2 in `EXP-0004`: each template byte
string is decoded, and each `ModRM` and immediate/branch field is exercised
across its whole encoded range.

`0.2.0` adds the two RIP-relative rows. `mod = 00` and `r/m = 101` are template,
the destination/source is `ModRM.reg`, and `disp32` is the instruction's last
field. The displacement is a `target` operand with `kind: x86.rel`, not a `disp`,
because the form has no base register: RIP is not in `x86.gpr64` and no slot
carries it (`ADR-0027`). A symbol reference uses `pcrel_end` with `addend = 0`;
the measured `L1` at `0x20` with the instruction at offset `7` gives
`12 00 00 00` (`EXP-0029` §4).

`0.3.0` adds the eight base+displacement rows: load and store × `disp8`/`disp32`
× base-in-`r/m`/`%rsp`-fixed. The general rows put the base in `ModRM.rm` at
`[16,3]` and exclude register 4 (`%rsp`) with `E-RANGE-004`, because `%rsp`
forces a SIB byte; the `%rsp` rows fix `r/m = 100`, `SIB = 24` and the base
inside the template, so their `disp` starts at bit 32. `disp8` is signed 8 bits
and `disp32` signed 32 bits, and a value outside the named row's field is
`E-RANGE-001` rather than a re-formed instruction (`ADR-0028`, `EC-35`). Index
and scale, `mod = 00`, the `0x67` address-size prefix and `moffs` remain absent.

`0.7.0` widens the family to four bits (`ADR-0034`): the four general rows get a
4-bit base and a 4-bit register operand, and the four `%rsp` rows get the wider
register operand. `r8`–`r11`, `r13`–`r15` need only `REX.B` at `[0,1]`, so they
use the general rows, which now exclude both SIB-forcing values: `4` (`%rsp`) and
`12` (`%r12`). `%r12` has the same low three bits as `%rsp`, so it is four
fixed-base rows of its own with `REX = 0x49` instead of `0x48`; the `%rsp` rows
are unchanged. `REX.X` stays unexercised in `0.7.0`: it extends a `SIB` index,
and no row before `0.8.0` has an index operand.

`0.4.0` adds the five prefix rows: two 16-bit directions with `0x66` as
template byte 0, the high-byte row, and the low-byte pair split by REX. The
3-byte templates are 24 bits and the 2-byte templates are 16 bits, so the
`ModRM` byte starts at bit 16 and bit 8 respectively; `[8,3]` is `ModRM.rm` and
`[11,3]` is `ModRM.reg` in the short rows. `x86.gpr16` and `x86.gpr8h`/`x86.gpr8` are
separate kinds, because the same `ModRM` number is a different register in each
set; `%sp` is encodable in a 16-bit register-direct field (`66 89 e0`), so the
16-bit rows exclude nothing. The exclusion lists keep the three 8-bit rows
disjoint: `0–3` are the REX-less low bytes, `4–7` in `gpr8h` are
`ah`/`ch`/`dh`/`bh`, and `4–7` in a REX row are `spl`/`bpl`/`sil`/`dil`
(`ADR-0029`, `EC-36`). The `8A` direction, memory operands at these widths,
`0x67`, and `r8`–`r15` remain absent.

`0.5.0` adds the three encoding-family rows for one operation, `movaps` at
`xmm` width: `0F 28 /r` with no prefix, `C5 F8 28 /r` (two-byte VEX), and
`62 F1 7C 08 28 /r` (EVEX). The `ModRM` byte is the last byte in each, so the
`dest` and `src` slots move with the prefix length: `[19,3]`/`[16,3]`,
`[27,3]`/`[24,3]`, `[43,3]`/`[40,3]`. `x86.xmm` is one kind for all three
because the register set does not change with the family; the family is the
`/legacy`, `/vex` or `/evex` component of the `form_id`, never an operand
(`EC-09`, `ADR-0030`). The VEX `vvvv` field and the EVEX `R/X/B/R'`/`vvvv`/`V'`
extension bits are fixed `1` in the templates, so these rows reach `xmm0`–`xmm7`
only: `xmm8`–`xmm15` need a REX/VEX/EVEX extension bit and are rejected with
`E-OPERAND-004`. The three rows are the only forms that need an extension above
the x86-64 baseline, so `0.5.0` is the first x86 table whose `enabled_extensions` is
not empty (`avx`, `avx512f`, `avx512vl`); the plan must declare the same set
(`E-TARGET-001`), and the table is still not filtered per form. Memory operands,
masking, `ymm`/`zmm`, the `0x66` form of `movapd` and the three-byte VEX
`C4` form remain absent (`EXP-0032`).

`0.6.0` widens the six register-direct 64-bit rows — `mov` in both directions,
`add`'s two immediate rows, and the two `RIP`-relative rows — from 3-bit to 4-bit
register slots. The fourth bit is not a new operand and not a new `form_id`: it
is a placement into the `REX` byte the template already contains. `REX.B` (bit 0)
extends `ModRM.r/m`, so a `dest`/`src`/`base` slot in that field becomes
`[0,1], [16,3]`; `REX.R` (bit 2) extends `ModRM.reg`, so a slot in that field
becomes `[2,1], [19,3]`. The first placement is the most significant bit, so
`mov %r8, %r9` writes `r8`'s bit 3 into `REX.R`, its low three bits into
`ModRM.reg`, `r9`'s bit 3 into `REX.B` and its low three bits into `ModRM.r/m`,
giving `4d 89 c1` (`EXP-0035`). For a register below 8 the same placements write
zero into the prefix bit, which is why the old rows' bytes do not change.
`reg = 16` is `E-OPERAND-004` with `field_bits = 4`; `reg = 8` against `0.5.0`
stays `E-OPERAND-004` with `field_bits = 3` (`N14c`/`N14d`). The 8-bit and 16-bit
rows, the high-byte row, the base+disp rows (`SIB`/`mod` interaction) and the
SSE/VEX/EVEX rows keep their narrower fields; each needs its own decision
(`ADR-0033`). `REX.X` stays unused by these rows: no v0 row before `0.8.0` has an
index operand.

`0.8.0` adds the index/scale shape (`ADR-0035`): four rows whose template fixes
`r/m = 100` and therefore the `SIB` byte's presence, so an index/form choice is
never read from an operand value. The `SIB` fields are operands: `base` is
`[0,1]`/`[24,3]` (`REX.B` + `SIB.base`), `index` is `[1,1]`/`[27,3]` (`REX.X` +
`SIB.index`), and the scale is the two-bit field content at `[30,2]` (0 = ×1,
1 = ×2, 2 = ×4, 3 = ×8), carried as `role: imm`, `kind: x86.scale`,
`target_type: scale2`, because the contract's `role` set is closed and the
field's position is already fixed by the `SIB` byte plus the `target_type` guard;
the multiplier is not the operand value. `disp` stays per row (`[32,8]` /
`[32,32]`).

The two new slots are not symmetric. `base` excludes nothing: `r/m = 100` has
already announced the `SIB` byte, so `4` (`%rsp`) and `12` (`%r12`) are ordinary
bases here, unlike the rows above. `index` excludes `4`: `SIB.index = 100` with
`REX.X = 0` means "no index" and the register silently disappears (measured:
`48 8b 54 20 08` decodes as `movq 8(%rax,%riz), %rdx`), while `12` stays legal
because `REX.X = 1` makes `SIB.index = 100` mean `%r12` (`4b 8b 54 e5 08` is
`movq 8(%r13,%r12,8), %rdx`). `%rsp` cannot be an index at all: `llvm-mc` rejects
`8(%rax,%rsp,1)` as an invalid base+index expression. A scale operand outside
`0…3` is `E-RANGE-001` (`N03c` passes the multiplier `8`, whose content is `3`)
rather than a truncation or a third bit that would spill into `disp`
(`EC-37`, `EXP-0037`). `mod = 00` (a SIB row with no displacement), a
base-only `SIB` row (`index = 4` as a value), the `0x67` address-size prefix and
the 8/16-bit memory rows remain absent, as do the SSE memory rows until `0.9.0`.

`0.9.0` adds the SSE family's memory shape (`ADR-0036`). The direction is the
opcode (`0F 28` load, `0F 29` store), the family is the `/legacy`, `/vex` or
`/evex` component, and each needs a `disp8` and a `disp32` row: twelve rows.
`ModRM.reg` carries the `dest`/`src` `xmm` at `[19,3]`, `[27,3]` or `[43,3]`,
`ModRM.rm` carries the `base` at `[16,3]`, `[24,3]` or `[40,3]`, and `disp`
starts at bit 24, 32 or 48. In `0.9.0` the `xmm` slot and the `base` slot are
three bits in all three families, and the base excludes `4` (`%rsp` forces a
`SIB` byte, `E-RANGE-004`); `xmm8` and `r8` are `E-OPERAND-004`. The families
differ in how a fourth bit would be carried: the legacy templates have no `REX`
byte, two-byte VEX has no `B` bit, and EVEX's `B̄`/`R̄` are inverted, so a raw
placement would encode a different register (`EC-38`). Widening takes its own
decision: `0.10.0` widens the base, and the `xmm` slot stays three bits
(`ADR-0037`).

The EVEX `disp8` field is compressed: `N = 16` for `xmm`, so the plan carries
the field content under `target_type: disp8x16` (`1` is `16`, `-1` is `-16`,
`127` is `2032`) and the `disp32` row carries the byte offset. The materializer
writes the content and never multiplies; a plan that needs `8(%rax)` must name
the `disp32` row, because `8` is not a multiple of `16` and `llvm-mc` promotes
it (`62 f1 7c 08 28 98 08 00 00 00`) (`EC-39`, `EXP-0038`). EVEX `8(%rsp)`
confirms the `SIB` exclusion (`62 f1 7c 08 28 84 24 08 00 00 00`), and EVEX
`8(%r8)` confirms the inversion (`62 d1 7c 08 28 40 01`, `P0 = d1`, not `f1`).

`0.10.0` widens the SSE base to `r8`–`r15` (`ADR-0037`). The EVEX rows widen in
place: the base becomes `[13,1]` inverted + `[40,3]`, `%r12` joins `%rsp` in
`excluded`, and the template keeps `P0 = f1` for a low base. The legacy and VEX
families cannot widen in place, because reaching the high base changes the
instruction length: legacy gains a `REX` byte (`41 0f 28 40 08` versus
`0f 28 40 08`) and VEX moves from two-byte `C5 F8` to three-byte `C4 C1 78`
(`c4 c1 78 28 40 08` versus `c5 f8 28 40 08`). Each therefore gets eight new
`-base-ext` rows whose template carries the longer prefix: legacy `40 0F 28 /r`
with `REX.B` at `[0,1]`, VEX `C4 C1 78 28 /r` with the inverted `B̄` at `[13,1]`.
The two windows are disjoint by `excluded`: the low rows exclude `8`–`15` and
the extension rows exclude `0`–`7` (plus `12`, which still forces a `SIB` byte),
so no plan can name a base and get two encodings. `xmm8` remains
`E-OPERAND-004` on those rows; `0.11.0` takes the register next.

`0.11.0` widens the SSE register to `xmm8`–`xmm15` (`ADR-0038`). The EVEX
register-direct rows widen in place: `dest` gains `[15,1]` inverted and `src`
gains `[13,1]` inverted, because in a register-direct EVEX instruction the
destination is `ModRM.reg` and the source is `ModRM.rm`. Every VEX and EVEX
memory row widens its `xmm` slot in place at `[15,1]` inverted (`ModRM.reg`),
so a high register does not change the instruction length. The legacy family
cannot widen in place, because reaching a high register adds the `REX` byte
the low row does not have: three `40 0F 28 /r` windows cover dest-high
(`44 0f 28 c1`, `REX.R` at `[2,1]`), src-high (`41 0f 28 c1`, `REX.B` at
`[0,1]`) and both-high (`45 0f 28 c1`), and each excludes the low values of
the slot it extends. Per-slot `excluded` cannot express the cross product
"(dest low and src low)", so the all-low corner stays with the 3-byte
`0f28c0` row. Four `40 0F 28/29 /r` memory rows combine a 4-bit `xmm` at
`[2,1]` + `[27,3]` with a 4-bit base at `[0,1]` + `[24,3]`: the `REX` byte is
present for `REX.R`, so `REX.B` comes for free and one row covers base `0`–`15`
minus `%rsp`/`%r12` (`excluded: [4, 12]`). The VEX register-direct shape splits
by which operand is high: the existing two-byte row keeps its 3-bit source,
`c5 78 29 /r` (`xmm-xmm-src-ext`) puts a high source in `ModRM.reg` with a
3-bit destination in `rm`, and `c4 41 78 28 /r` (`xmm-xmm-both-ext`) carries
both fourth bits in `R̄`/`B̄`. `llvm-mc` measures both `c5 78 29 c0` (4 bytes)
and `c4 c1 78 28 c0` (5 bytes) for `vmovaps %xmm8, %xmm0`; the table pins the
four-byte opcode-29 form, because choosing by width or by family would make two
honest implementations emit different lengths (`INV-02`). `xmm16` is
`E-OPERAND-004` (`N14i`), `xmm8` on the 3-bit legacy register-direct row is
`E-OPERAND-004` (`N14j`/`N14k`), and a low `xmm` on an extension row is
`E-RANGE-004` (`N16m`, `N16n`).

`0.12.0` adds the no-displacement shape, `mod = 00` (`ADR-0039`). Twelve rows:
legacy low/low (`0f 28 00`, `0f 29 00`), legacy high `xmm` with any legal base
(`44 0f 28 00`, whose `REX` byte already exists for `REX.R`, so it carries
`REX.B` too), legacy low `xmm` with a high base (`41 0f 28 00`), the two-byte
VEX low-base pair (`c5 f8 28 00`), the three-byte VEX high-base pair
(`c4 c1 78 28 00`), and the EVEX pair (`62 f1 7c 08 28 00`). No row has a `disp`
slot: the shape ends at the `ModRM` byte, and the materializer never reads the
base to choose a `mod`. Two base values are outside the shape rather than
silently repaired. `%rsp`/`%r12` force a `SIB` byte (`0f 28 04 24`,
`41 0f 28 04 24`) and stay excluded; `%rbp`/`%r13` collide with
`mod = 00, r/m = 101`, which is `RIP + disp32`, so `llvm-mc` emits the `disp8`
shape with a zero displacement (`0f 28 45 00`, `41 0f 28 45 00`). Both are
`E-RANGE-004` on the new rows (`N16o`, `N16p`) and a plan that wants those bases
names the existing `disp8` row with `disp = 0`. A zero displacement and no
displacement are different encodings (`0f 28 40 00` versus `0f 28 00`), which
is why the width stays a form (`EC-02`). A base `16` is `E-OPERAND-004`
(`N14l`), a low base on `41 0F 28 /r` is `E-RANGE-004` (`N16q`), and `0.11.0`
has no such row at all (`N01ah`, `E-FORM-001`). Still absent: a base-only `SIB`
row under these opcodes, an SSE RIP-relative row, `mod = 00` for the GPR rows,
`0x67`, 8/16-bit memory widths, EVEX masking, `ymm`/`zmm`, `movapd` and
`xmm16`–`xmm31`.

`0.13.0` widens the EVEX `xmm` slot to five bits in place (`ADR-0040`), so
`xmm16`–`xmm31` become reachable without a new row and without a longer
instruction. The seven EVEX rows keep their templates: the six memory rows move
the register slot to `[12,1]` inverted (`R̄'`) + `[15,1]` inverted (`R̄`) +
`[43,3]`, and the register-direct row moves its source to `[14,1]` inverted
(`X̄`) + `[13,1]` inverted (`B̄`) + `[40,3]` as well. `R̄'` is a second inverted
extension bit, and the register-direct source's fifth bit is `X̄`, the same
prefix bit that would extend a `SIB` index; the memory rows have no `SIB` field,
so there it stays set and its meaning never has to be inferred. Legacy and VEX
have no second extension bit at all, so their `xmm` slots stay at three and four
bits: `xmm16` is `E-OPERAND-004` on a `0.13.0` VEX row (`N14o`) and on a
`0.12.0` EVEX row (`N14m`), and `xmm32` is `E-OPERAND-004` at five bits
(`N14n`). EVEX masking and broadcast, `movapd`'s `0x66` form, `ymm`/`zmm` and
the memory shapes and prefixes the `0.12.0` paragraph lists are still absent at
this version.

`0.14.0` adds the other two vector widths as form families (`ADR-0041`). The
mnemonic does not change; the width is the `L` bit in VEX or the `L'L` field in
EVEX, which the template pins, so an operand value never selects a width. Five
register-direct rows are added: three VEX.256 windows, mirroring the `0.11.0`
`xmm` windows with `L = 1` (`c5 fc 28 /r` low/low with the destination's fourth
bit in `R̄`, `c5 7c 29 /r` for a high source with a low destination, and the
three-byte `c4 41 7c 28 /r` when both are high), one EVEX.256 row
(`62 f1 7c 28 28 /r`) and one EVEX.512 row (`62 f1 7c 48 28 /r`). The EVEX rows
keep the `0.13.0` five-bit placements, so `ymm16`–`ymm31` and `zmm16`–`zmm31`
are reachable; `x86.ymm` and `x86.zmm` are distinct kinds from `x86.xmm`,
because the same register number names a different-width register and a plan
that mixes them is `E-OPERAND-001`. Legacy `movaps` and VEX have no `zmm` form
at all, and VEX `ymm` has only four bits, so `ymm16` is `E-OPERAND-004`
(`N14p`) and `zmm32` is outside the five-bit field (`N14q`). Memory forms at
these widths are a separate slice: they need `disp8*32`/`disp8*64` compression
(`EC-39`) and `0.15.0` supplies them (`ADR-0042`), so naming one against
`0.14.0` is `E-FORM-001` (`N01ak`).

`0.15.0` carries that slot shape into memory and makes the compressed unit a
form fact (`ADR-0042`). Twelve rows repeat the six `0.13.0` `xmm` memory shapes
at each width: the `disp8*N` pair (`62 f1 7c 28 28 40 00` / `… 29 40 00` for
`ymm`, `… 48 …` for `zmm`), the `disp32` pair, and the `mod = 00` pair. Only
`P2` changes between the two widths — every placement is the `0.13.0` one, so
the vector slot stays `[12,1]` inverted + `[15,1]` inverted + `[43,3]` and the
base stays `[13,1]` inverted + `[40,3]`. The displacement slot is the new
statement: `disp8x32` and `disp8x64` sit at `[48,8]` with
`{ "signed": true, "bits": 8, "align_bits": 0 }`, exactly like `disp8x16`,
because the payload is the field content and the unit is the row's. The base
exclusions are unchanged — `%rsp`/`%r12` on the displacement rows, plus
`%rbp`/`%r13` on the `mod = 00` rows (`EC-02`, `EC-35`). Naming `disp8x16` on a
`disp8x32` row is `E-OPERAND-001` (`N02p`), content `128` is `E-RANGE-001`
(`N03e`), `ymm32` is outside the five-bit field (`N14r`), and VEX.256 memory
stays out of `0.15.0` because it needs no new fact: `vmovaps 32(%rax),
%ymm0` is `c5 fc 28 40 20`, a plain unscaled byte (`N01al`).

`0.16.0` adds that VEX.256 memory coverage without adding a fact (`ADR-0043`).
Twelve rows mirror the VEX memory rows of `0.11.0`/`0.12.0` at `L = 1`: the two
base windows (`c5 fc …` for a low base, `c4 c1 7c …` for `r8`–`r15`), each with
the `disp8` pair, the `disp32` pair and the `mod = 00` pair. Every placement is
the VEX.128 one — `R̄` at `[15,1]` inverted plus `[27,3]`/`[35,3]`, the base at
`[24,3]` or `[13,1]` inverted plus `[32,3]`, and the displacement at
`[32,8]`/`[32,32]` or `[40,8]`/`[40,32]` — and only the vector kind/target_type
change from `xmm` to `ymm`. VEX has no compressed unit, so `32(%rax)` is the
plain signed byte `20` and `128` promotes to `disp32` rather than a scaled
content (`EC-02`, `EC-35`). The base windows are unchanged: `%rsp` is excluded
on the two-byte rows, `%r12` on the three-byte rows, and `%rbp`/`%r13` join on
the no-displacement rows. A `zmm` operand is `E-OPERAND-001` (`N02q`), `ymm16`
is `E-OPERAND-004` (`N14s`), `%rbp` and `%r12` are `E-RANGE-004` (`N16r`,
`N16s`), content `128` is `E-RANGE-001` (`N03f`), and naming either window
against `0.15.0` is `E-FORM-001` (`N01al`, `N01am`).

`0.17.0` carries the prefix and byte-register facts into memory at 8 and 16 bits
(`ADR-0044`). Sixteen rows: four word rows (`66 89`/`66 8b` with a `x86.gpr16`
at `[19,3]`, base `[16,3]`, displacement `[24,8]`/`[24,32]`) and twelve byte
rows in the three sets `0.4.0` already separated. The REX-less low set
(`88`/`8a`, numbers 0–3, excluding 4–7) and the high set (`88`/`8a`, numbers
4–7, excluding 0–3) put `ModRM` at byte 1, so the register is `[11,3]`, the base
`[8,3]` and the displacement `[16,8]`/`[16,32]`; the `spl`–`dil` set is the
same row shape behind a template `40` byte (`40 88`/`40 8a`), which moves the
fields back to `[19,3]`, `[16,3]` and `[24,8]`/`[24,32]`. The `0x66` byte stays
the row's, ahead of any REX byte, so no operand selects a width (`EC-36`), and
the byte sets stay disjoint (`EC-28`). Every base is the three-bit window 0–7
minus `%rsp`, because `mod = 01`/`10` with `r/m = 100` spends a `SIB` byte
(`EC-02`); `%r8`–`%r15` need a `REX.B` that the no-REX and `40` rows leave
unused, so they are `E-OPERAND-004` (`N14t`) until the `-base-ext` rows land.
`x86.gpr32` on a word row is `E-OPERAND-001` (`N02r`), `x86.gpr8h` on the
`-rex` row is `E-OPERAND-001` (`N02s`), number 4 on the REX-less low row is
`E-RANGE-004` (`N16t`), `%rsp` is `E-RANGE-004` (`N16u`), content `128` on a
`disp8` slot is `E-RANGE-001` (`N03g`), and naming any new row against `0.16.0`
is `E-FORM-001` (`N01an`).

`0.18.0` extends those bases to `r8`–`r15` (`ADR-0045`). The word rows put
`REX.B` at `[8,1]` because the `66` byte stays template byte 0, so the eight
`-base-ext` rows carry the base as `[8,1]` + `[24,3]` and move the displacement
to `[32,8]`/`[32,32]`; the REX-less low-byte rows put the same bit at `[0,1]`
with the base at `[16,3]` and the displacement at `[24,8]`/`[24,32]`. Every
extension row excludes the low bases `0`–`7` and `%r12`, so the two windows are
disjoint. The four `40`-prefixed byte rows already carry a `REX` byte, so they
widen from `[16,3]` to `[0,1]` + `[16,3]` in place and their `excluded` list
grows from `[4]` to `[4, 12]`; bases 0–7 keep their bytes. The byte register
set is the other half of the partition: the new rows carry numbers 0–3 and
exclude 4–7, the widened rows carry 4–7, and the high-byte set has no extension
row because `movb %ah, 8(%r8)` cannot be encoded. A low base on an extension
row is `E-RANGE-004` (`N16v`), `%r12` on either window is the same code
(`N16w`, `N16x`), base `16` is `E-OPERAND-004` (`N14u`), `x86.gpr8h` on a new
byte row is `E-OPERAND-001` plus `E-RANGE-004` (`N02t`), and naming a new row
against `0.17.0` is `E-FORM-001` (`N01ao`). Still deferred on this axis: `mod
= 00` for the GPR rows and the four-bit `r8b`–`r15b`/`r8w`–`r15w` registers.

`0.19.0` adds the two bases `0.18.0` left out (`ADR-0046`). `%rsp` forces
`r/m = 100` and spends a `SIB` byte (`24`), and `%r12` spends the same byte
plus `REX.B`, so the base leaves the operand list and enters the template:
twenty-eight fixed-base rows carry only the register and the displacement, the
shape `0.3.0`/`0.7.0` gave `movq`. The prefixes are template bytes, so `ModRM`
and the displacement move one byte later than on the `-base-disp*` rows — the
word `%rsp` pair keeps `[19,3]`/`[32,8]`, the word `%r12` pair reads
`[27,3]`/`[40,8]`, the REX-less byte `%rsp` pair `[11,3]`/`[24,8]`, and every
row whose template carries a `REX` byte `[19,3]`/`[32,8]`. The register
windows do not move: the low-byte rows still carry 0–3, the `40` rows 4–7, and
the high-byte rows 4–7 with `%rsp` only, because `movb %ah, 8(%r12)` has no
encoding — the `REX.B` byte that names `%r12` renames `ah` to `spl`. Naming a
row against `0.18.0` is `E-FORM-001` (`N01ap`), the absent high-byte `%r12` row
is the same code (`N01aq`), a `x86.gpr16` operand on a byte row is two
`E-OPERAND-001` (`N02u`), content `128` on a `disp8` slot is `E-RANGE-001`
(`N03h`), register `8` is `E-OPERAND-004` (`N14v`), and number `0` on a `40`
row is `E-RANGE-004` (`N16y`). Still deferred on this axis: `mod = 00` for the
GPR rows, index/scale under these opcodes, the `0x67` address-size prefix, and
the four-bit `r8b`–`r15b`/`r8w`–`r15w` registers.

`0.20.0` gives the SSE `movaps`/`vmovaps` memory rows the same two bases
(`ADR-0047`). The shape is the one `0.19.0` used: `%rsp` forces `r/m = 100` and
spends the `SIB` byte `24`, `%r12` spends the same byte plus `REX.B` in the
legacy family, and the VEX family cannot hold `%r12` in the two-byte prefix at
all, so it spends `c4 78`. Sixteen fixed-base rows carry only the register and
the displacement. The prefixes are template bytes, so `ModRM` and the
displacement move one byte later than on the `-base-disp*` rows: legacy
`%rsp` reads `[19,3]`/`[32,8]`, legacy `%r12` `[27,3]`/`[40,8]`, VEX `%rsp`
`[27,3]`/`[40,8]` and VEX `%r12` `[35,3]`/`[48,8]`. The register windows are
inherited, not widened: the legacy rows keep the three-bit field, so `xmm8` is
`E-OPERAND-004` (`N14w`), while the VEX rows keep the inverted `R` bit and
already reach `xmm8`–`xmm15`. Naming a row against `0.19.0` is `E-FORM-001`
(`N01ar`), the absent no-displacement shape is the same code (`N01as`), a
`x86.gpr64` operand on an `xmm` row is two `E-OPERAND-001` (`N02v`), a third
`base` operand on a fixed-base row is `E-OPERAND-002` (`N02w`), and content
`128` on a `disp8` slot is `E-RANGE-001` (`N03i`). Still deferred on this axis:
the EVEX `SIB` base, the `ymm`/`zmm` memory rows, the legacy `REX.R` window,
`mod = 00`, index/scale under these opcodes, and the SSE RIP-relative row.

`0.21.0` gives the EVEX `vmovaps` memory rows the same two bases
(`ADR-0048`). Here the base costs no prefix byte: `B̄` is already in
`P0`, so `%rsp` and `%r12` are the same length and differ only in that byte
(`62 f1 ...` vs `62 d1 ...`). Twenty-four fixed-base rows carry the register
and the displacement; the prefix does not grow, so the vector slot stays
`[12,1]` inverted + `[15,1]` inverted + `[43,3]` and only the displacement
moves, from `[48,...]` to `[56,...]`. The `disp8*N` content is the `disp / N`
the general rows use, so `16`/`32`/`64` are content `1` at the three widths,
and `8(%rsp)` promotes to `disp32` rather than truncating. The five-bit
field already reaches `xmm16`–`xmm31`, and a high register only clears
`R̄`/`R̄'` in `P0`. Naming a row against `0.20.0` is `E-FORM-001`
(`N01at`), the absent `mod = 00` shape is the same code (`N01au`), a
`x86.gpr64` operand on an `xmm` row is two `E-OPERAND-001` (`N02x`), a third
`base` operand is `E-OPERAND-002` (`N02y`), content `128` on a `disp8x16`
slot is `E-RANGE-001` (`N03j`), and register `32` is `E-OPERAND-004`
(`N14x`). Still deferred on this axis: `mod = 00` with a `SIB` base,
index/scale under these opcodes, the other EVEX SSE memory mnemonics, and
EVEX masking.

`0.22.0` adds the `mod = 00` half of the same EVEX axis (`ADR-0049`). The row
has no displacement slot at all: `ModRM` is `04` (`mod = 00`, `reg = 000`,
`r/m = 100`), the `SIB` byte is `24`, and the instruction stops after it, so
`(%rsp)` is `62 f1 7c 08 28 04 24` and `(%r12)` is `62 d1 7c 08 28 04 24`.
`%r12` still differs only in `P0` (`f1` → `d1`), so both bases cost the same
seven bytes, and the vector slot stays `[12,1]` inverted + `[15,1]` inverted +
`[43,3]` because the prefix does not grow. `%rbp` and `%r13` cannot use the
shape: `mod = 00` with `r/m = 101` is RIP-relative, so `(%rbp)` keeps a zero
displacement (`62 f1 7c 08 28 45 00`, the `-base` row at `mod = 01`) and stays
out. `llvm-mc` canonicalizes `0(%rsp)` to `(%rsp)`, so the no-displacement row
is the only encoding of a zero offset. Naming a row against `0.21.0` is
`E-FORM-001` (`N01av`), the absent `%rbp` shape is the same code (`N01aw`), a
`x86.gpr64` operand on an `xmm` row is two `E-OPERAND-001` (`N02z`), a `disp`
operand on a row with no `disp` slot is `E-OPERAND-002` (`N02aa`), register
`32` is `E-OPERAND-004` (`N14y`), and `%rsp` on the general `xmm-base` row is
`E-RANGE-004` (`N16z`). Still deferred on this axis: index/scale under these
opcodes, the other EVEX SSE memory mnemonics, and EVEX masking.

`0.23.0` opens the `SIB` byte of the same EVEX family (`ADR-0050`). Eighteen
rows replace the fixed base with operands: `ModRM` is `04`/`44`/`84`
(`mod = 00`/`01`/`10`, `r/m = 100`), the `SIB` byte sits at bits 48–55 with the
base at `[48,3]` plus the inverted `B̄` at `[13,1]`, the index at `[51,3]` plus
the inverted `X̄` at `[14,1]`, and the scale at `[54,2]`; the displacement,
when present, is at `[56,8]`/`[56,32]`. `(%rsp,%rax,1)` is
`62 f1 7c 08 28 04 04` and `(%rsp,%r12,1)` is `62 b1 7c 08 28 04 24`, so the
index's fourth bit is `X̄`. The index excludes `4` (`E-RANGE-004`, `N16aa`),
and the no-displacement rows exclude base `5`/`13` because `SIB.base = 101` at
`mod = 00` is the no-base form (`N16ab`); `(%rbp,%rax,1)` is the `disp8*N = 0`
row, `62 f1 7c 08 28 44 05 00`. Naming a row against `0.22.0` is `E-FORM-001`
(`N01ax`/`N01ay`), carrying the scale as `x86.imm` is `E-OPERAND-001` (`N02ab`),
and a `disp` operand on the no-displacement row is `E-OPERAND-002` (`N02ac`).
Still deferred on this axis: the no-base indexed shape, the other EVEX SSE
memory mnemonics, EVEX masking, and the `0x67` prefix.

`0.24.0` takes that no-base shape (`ADR-0051`). Six rows drop the `base` slot
and keep `ModRM` at `04`: with `mod = 00` and `SIB.base = 101` the encoding has
no base register and demands a `disp32`, so the template is
`62 f1 7c <L'L> <28|29> 04 05 00 00 00 00` and every row is eleven bytes. The
index (`[51,3]` plus `X̄` at `[14,1]`, excluding `4`) and the scale (`[54,2]`)
are unchanged, and the displacement sits at `[56,32]`. `(,%rax,4)` is
`62 f1 7c 08 28 0c 85 00 00 00 00` and `-4096(,%r12,8), %xmm3` is
`62 b1 7c 08 28 1c e5 00 f0 ff ff`. The operand sequence is `dest`/`src`,
`index`, `imm`, `disp`: a supplied base is `E-OPERAND-002` (`N02ad`), the scale
as `x86.imm` is `E-OPERAND-001` (`N02ae`), index `4` is `E-RANGE-004`
(`N16ac`), and `disp32` content `2147483648` is `E-RANGE-001` (`N03k`). Naming
a row against `0.23.0` is `E-FORM-001` (`N01az`/`N01ba`). Still deferred on
this axis: the absolute `SIB = 25` shape, the other EVEX SSE memory mnemonics,
EVEX masking, and the `0x67` prefix.

### 8.2 `aarch64` `0.1.0` … `0.17.0`

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `aarch64:add/x64-x64-x64-lsl0` | `0000008b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P1` |
| `aarch64:add/x64-imm12-lsl0` | `00000091` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P2` |
| `aarch64:add/x64-imm12-lsl12` | `00004091` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P2` — `0.2.0`+ |
| `aarch64:bl/imm26` | `00000094` | target: `aarch64.rel`/`imm26` → `[0,26]` | 4 | `A64-P5` |
| `aarch64:adrp/x64-imm21` | `00000090` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; target: `aarch64.rel`/`imm21` → `[5,19]`, `[29,2]` | 4 | `EC-15`, `EC-17`, `A64-P6` |
| `aarch64:b.cond/imm19` | `00000054` | imm: `aarch64.cond`/`cond4` → `[0,4]`; target: `aarch64.rel`/`imm19` → `[5,19]` | 4 | `EC-29`, `A64-P4` — `0.3.0` only |
| `aarch64:ldr/x64-base-imm12` | `000040f9` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:ldr/x64-base-imm9-pre` | `000c40f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:ldr/x64-base-imm9-post` | `000440f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:ldur/x64-base-imm9` | `000040f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:str/x64-base-imm12` | `000000f9` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-14`, `A64-P3` — `0.4.0` only |
| `aarch64:str/x64-base-imm9-pre` | `000c00f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P15` |
| `aarch64:str/x64-base-imm9-post` | `000400f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P15` |
| `aarch64:stur/x64-base-imm9` | `000000f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; disp: `aarch64.imm`/`imm9` → `[12,9]` | 4 | `EC-14`, `A64-P15` |
| `aarch64:ldr/x64-imm19` | `00000058` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; target: `aarch64.rel`/`imm19` → `[5,19]` | 4 | `EC-15`, `A64-P16` |
| `aarch64:movz/x64-imm16-lsl0` | `000080d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl16` | `0000a0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl32` | `0000c0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movz/x64-imm16-lsl48` | `0000e0d2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `A64-P7` — `0.5.0` only |
| `aarch64:movk/x64-imm16-lsl0` | `000080f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movk/x64-imm16-lsl16` | `0000a0f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movk/x64-imm16-lsl32` | `0000c0f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movk/x64-imm16-lsl48` | `0000e0f2` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl0` | `00008092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl16` | `0000a092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl32` | `0000c092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:movn/x64-imm16-lsl48` | `0000e092` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; imm: `aarch64.imm`/`imm16` → `[5,16]` | 4 | `EC-30`, `EC-16`, `A64-P19` — `0.17.0` only |
| `aarch64:add/x64-x64-x64-imm6-lsl` | `0000008b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P8` — `0.6.0` only |
| `aarch64:add/x64-x64-x64-imm6-lsr` | `0000408b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P8` — `0.6.0` only |
| `aarch64:add/x64-x64-x64-imm6-asr` | `0000808b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P8` — `0.6.0` only |
| `aarch64:add/x64-x64-w32-imm3-uxtb` | `0000208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-uxth` | `0020208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-uxtw` | `0040208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-x64-imm3-uxtx` | `0060208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-sxtb` | `0080208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-sxth` | `00a0208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-w32-imm3-sxtw` | `00c0208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:add/x64-x64-x64-imm3-sxtx` | `00e0208b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P9` — `0.7.0` only |
| `aarch64:sub/x64-x64-x64-lsl0` | `000000cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-imm12-lsl0` | `000000d1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-imm12-lsl12` | `000040d1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-x64-x64-imm6-lsl` | `000000cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-x64-x64-imm6-lsr` | `000040cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P10` — `0.8.0` only |
| `aarch64:sub/x64-x64-x64-imm6-asr` | `000080cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P10` — `0.8.0` only |
| `aarch64:adds/x64-x64-x64-lsl0` | `000000ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-imm12-lsl0` | `000000b1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-imm12-lsl12` | `000040b1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-x64-x64-imm6-lsl` | `000000ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-x64-x64-imm6-lsr` | `000040ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:adds/x64-x64-x64-imm6-asr` | `000080ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-lsl0` | `000000eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-imm12-lsl0` | `000000f1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-imm12-lsl12` | `000040f1` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-12`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-imm6-lsl` | `000000eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-imm6-lsr` | `000040eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:subs/x64-x64-x64-imm6-asr` | `000080eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-31`, `A64-P11` — `0.9.0` only |
| `aarch64:add/w32-w32-w32-lsl0` | `0000000b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:add/w32-w32-w32-imm6-lsl` | `0000000b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:add/w32-w32-w32-imm6-lsr` | `0000400b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:add/w32-w32-w32-imm6-asr` | `0000800b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:add/w32-imm12-lsl0` | `00000011` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:add/w32-imm12-lsl12` | `00004011` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-lsl0` | `0000004b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-imm6-lsl` | `0000004b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-imm6-lsr` | `0000404b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:sub/w32-w32-w32-imm6-asr` | `0000804b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:sub/w32-imm12-lsl0` | `00000051` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:sub/w32-imm12-lsl12` | `00004051` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-lsl0` | `0000002b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-imm6-lsl` | `0000002b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-imm6-lsr` | `0000402b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:adds/w32-w32-w32-imm6-asr` | `0000802b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:adds/w32-imm12-lsl0` | `00000031` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:adds/w32-imm12-lsl12` | `00004031` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-lsl0` | `0000006b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-11`, `EC-13`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-imm6-lsl` | `0000006b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-imm6-lsr` | `0000406b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:subs/w32-w32-w32-imm6-asr` | `0000806b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-11`, `EC-31`, `A64-P12` |
| `aarch64:subs/w32-imm12-lsl0` | `00000071` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:subs/w32-imm12-lsl12` | `00004071` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-11`, `EC-12`, `A64-P12` |
| `aarch64:sub/x64-x64-w32-imm3-uxtb` | `000020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-uxth` | `002020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-uxtw` | `004020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-x64-imm3-uxtx` | `006020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-sxtb` | `008020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-sxth` | `00a020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-w32-imm3-sxtw` | `00c020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:sub/x64-x64-x64-imm3-sxtx` | `00e020cb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-uxtb` | `000020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-uxth` | `002020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-uxtw` | `004020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-x64-imm3-uxtx` | `006020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-sxtb` | `008020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-sxth` | `00a020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-w32-imm3-sxtw` | `00c020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:adds/x64-x64-x64-imm3-sxtx` | `00e020ab` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-uxtb` | `000020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-uxth` | `002020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-uxtw` | `004020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-x64-imm3-uxtx` | `006020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-sxtb` | `008020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-sxth` | `00a020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-w32-imm3-sxtw` | `00c020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:subs/x64-x64-x64-imm3-sxtx` | `00e020eb` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-13`, `EC-32`, `A64-P13` |
| `aarch64:cmp/x64-x64-lsl0` | `1f0000eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-imm6-lsl` | `1f0000eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-imm6-lsr` | `1f0040eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-imm6-asr` | `1f0080eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-imm12-lsl0` | `1f0000f1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-imm12-lsl12` | `1f0040f1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-lsl0` | `1f00006b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-imm6-lsl` | `1f00006b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-imm6-lsr` | `1f00406b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-w32-imm6-asr` | `1f00806b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-imm12-lsl0` | `1f000071` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/w32-imm12-lsl12` | `1f004071` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtb` | `1f0020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-uxth` | `1f2020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-uxtw` | `1f4020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-x64-imm3-uxtx` | `1f6020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtb` | `1f8020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-sxth` | `1fa020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-w32-imm3-sxtw` | `1fc020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmp/x64-x64-x64-imm3-sxtx` | `1fe020eb` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-lsl0` | `1f0000ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-imm6-lsl` | `1f0000ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-imm6-lsr` | `1f0040ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-imm6-asr` | `1f0080ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-imm12-lsl0` | `1f0000b1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-imm12-lsl12` | `1f0040b1` | src: `aarch64.gpr64`/`x64` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-lsl0` | `1f00002b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-imm6-lsl` | `1f00002b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-imm6-lsr` | `1f00402b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-w32-imm6-asr` | `1f00802b` | src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm6` → `[10,6]` (excl 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-imm12-lsl0` | `1f000031` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/w32-imm12-lsl12` | `1f004031` | src: `aarch64.gpr32`/`w32` → `[5,5]`; imm: `aarch64.imm`/`imm12` → `[10,12]` | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtb` | `1f0020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-uxth` | `1f2020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-uxtw` | `1f4020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-x64-imm3-uxtx` | `1f6020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtb` | `1f8020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-sxth` | `1fa020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-w32-imm3-sxtw` | `1fc020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:cmn/x64-x64-x64-imm3-sxtx` | `1fe020ab` | src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.imm`/`imm3` → `[10,3]` (excl 5, 6, 7) | 4 | `EC-33`, `A64-P14` |
| `aarch64:ldr/x64-base-regoff-lsl0` | `006860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-lsl3` | `007860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-uxtw0` | `004860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-uxtw3` | `005860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtw0` | `00c860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtw3` | `00d860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtx0` | `00e860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/x64-base-regoff-sxtx3` | `00f860f8` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-lsl0` | `006820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-lsl3` | `007820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-uxtw0` | `004820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-uxtw3` | `005820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtw0` | `00c820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtw3` | `00d820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtx0` | `00e820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:str/x64-base-regoff-sxtx3` | `00f820f8` | src: `aarch64.gpr64`/`x64` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P17` |
| `aarch64:ldr/w32-base-regoff-lsl0` | `006860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-lsl2` | `007860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-uxtw0` | `004860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-uxtw2` | `005860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtw0` | `00c860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtw2` | `00d860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtx0` | `00e860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:ldr/w32-base-regoff-sxtx2` | `00f860b8` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-lsl0` | `006820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-lsl2` | `007820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-uxtw0` | `004820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-uxtw2` | `005820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtw0` | `00c820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtw2` | `00d820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtx0` | `00e820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |
| `aarch64:str/w32-base-regoff-sxtx2` | `00f820b8` | src: `aarch64.gpr32`/`w32` → `[0,5]`; base: `aarch64.gpr64`/`x64` → `[5,5]`; index: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-14`, `A64-P18` |

`0.1.0` holds the first, second, fourth and fifth rows; `0.2.0` adds
`aarch64:add/x64-imm12-lsl12` (ADR-0011); `0.3.0` repeats all five and adds
`aarch64:b.cond/imm19` (ADR-0012); `0.4.0` repeats all six and adds the five
load/store rows (ADR-0013); `0.5.0` repeats all eleven and adds the four `movz`
rows (ADR-0014); `0.6.0` repeats all fifteen and adds the three shift rows
(ADR-0015); `0.7.0` repeats all eighteen and adds the eight extend rows
(ADR-0016); `0.8.0` repeats all twenty-six and adds the six `sub` rows (ADR-0017);
`0.9.0` repeats all thirty-two and adds the twelve `adds`/`subs` rows (ADR-0018);
`0.10.0` repeats all forty-four and adds the twenty-four `w` rows (ADR-0019);
`0.11.0` repeats all sixty-eight and adds the twenty-four extended
`sub`/`adds`/`subs` rows (ADR-0020); `0.12.0` repeats all ninety-two and adds the
forty `cmp`/`cmn` alias rows (ADR-0021); `0.13.0` repeats all one hundred and
thirty-two and adds the three store `imm9` rows (ADR-0022); `0.14.0` repeats all
one hundred and thirty-five and adds the literal load row (ADR-0023); `0.15.0`
repeats all one hundred and thirty-six and adds the sixteen register-offset rows
(ADR-0024); `0.16.0` repeats all one hundred and fifty-two and adds the sixteen
32-bit register-offset rows (ADR-0025); `0.17.0` repeats all one hundred and
sixty-eight and adds the eight `movk`/`movn` rows (ADR-0026).
Each document therefore shares its earlier rows
unchanged and differs only in the rows its version introduced, so a plan bound to
an older version cannot reach a newer form (`E-FORM-001`, `N01`) even though the
newest document has it.

The templates are little-endian file order, so `0000008b` is the word
`0x8b000000` in a disassembler. The generator
(`research/evidence/experiments/EXP-0008/generate_aarch64.py`) derives every
bit from the MRS node, requires the MRS node name to exist, and refuses to emit
unless all 32 bits are covered exactly once by a fixed bit or a slot placement;
`EXP-0008` §2–§3 records the nodes and the coverage check. The one hundred and
seventy-six forms come
from thirty-nine encode nodes: `ADD_64_addsub_shift` is read four times, once with `imm6`
pinned to 0 and once per shift keyword, `ADD_64_addsub_ext` eight times, once per
`option` value, `ADD_64_addsub_imm` twice, once with
`sh = 0` and once with `sh = 1`, `MOVZ_64_movewide` four times, once per `hw`
value, `MOVK_64_movewide` and `MOVN_64_movewide` four times each, once per `hw`
value (`ADR-0026`), `SUB_64_addsub_shift` four times and `SUB_64_addsub_imm` twice, each once
per row it shares with the `add` half (`ADR-0017`), `ADDS_64_addsub_shift` and
`SUBS_64_addsub_shift` four times each, `ADDS_64S_addsub_imm` and
`SUBS_64S_addsub_imm` twice each (`ADR-0018`), the eight `*_32*` nodes four times
(shifted) or twice (immediate) each on the same pattern (`ADR-0019`),
`SUB_64_addsub_ext`, `ADDS_64S_addsub_ext` and `SUBS_64S_addsub_ext` eight times
each, once per `option` value (`ADR-0020`),
`B_only_condbranch` contributes one row with both of its variable
fields as operands, and each of the eight load/store rows reads one node whose
addressing-kind bits are fixed and whose `imm12`/`imm9` is the single variable
field (`ADR-0022` adds the three store `imm9` nodes); `LDR_64_loadlit` is the one
node with no base register, and its `imm19` is the single variable field
(`ADR-0023`); `LDR_64_ldst_regoff` and `STR_64_ldst_regoff` are each read eight
times, once per `option`/`S` pair (`ADR-0024`), and the 32-bit pair
`LDR_32_ldst_regoff`/`STR_32_ldst_regoff` eight times each on the same pattern
(`ADR-0025`); the ten `CMP`/`CMN` alias
nodes are read for verification only, because
they carry no `encoding` and the bytes stay the base node's (`ADR-0021`). The
generator states each pinned value explicitly and asserts that `0.1.0` … `0.15.0`
still hash to their frozen digests.

The literal row's `imm19` follows §8.3's rule, not a slot transform: the slot is
the field, so `{ "value": 1 }` loads from `PC + 4`, and a byte displacement is
the `pcrel_begin` + `scale(2)` fixup with `align_bits: 2`. That is the same
shape as `bl`'s `imm26` and `b.cond`'s `imm19`, and it is why the row's only
difference from a branch row is that the destination is a register and the
target is not a branch: `aarch64:ldr/x64-imm19` has no `base` slot because the
MRS node has no `Rn`.

The `-lsl0`/`-lsl12` suffix on the `add`, `sub`, `adds` and `subs` rows carries a
decision the operand list does not state, and the name states it instead
(`01_contract.md` §7, `ADR-0004`, ADR-0017, ADR-0018):
the MRS leaves AArch64 `shift` (2 bits) and `imm6` (6 bits) variable in the
shifted-register node, and `sh` (1 bit) variable in the immediate node. This
table pins `shift` to `LSL` and `imm6` to 0 in the plain register row, and pins
`sh` to `0` or `1` in the two immediate rows. The shift *keyword* is a decision;
the shift *amount* is not: `-imm6-lsl`/`-imm6-lsr`/`-imm6-asr` pin `shift` and
leave `imm6` open as a `0…63` operand on the `x64-…` rows (`0…31` on the
`w32-…` ones, below), so `add x0, x1, x2, lsl #4` is
`aarch64:add/x64-x64-x64-imm6-lsl` with `imm = 4`, and nothing shifts implicitly
(`INV-02`, `INV-03`, `EC-31`, ADR-0015). `lsl #0` is expressible both ways —
`-lsl0` and `-imm6-lsl` with `imm6 = 0` are the same word `0x8b020020` — because
the assembly language itself treats the two spellings as one instruction, and
excluding `0` would make an operand's value choose the form.

The two immediate rows hold the *same* operand value type, and only the form
differs: `{ "value": n }` must be in `[0, 4095]` for both, and the instruction
does the `<< 12` on the `-lsl12` one. Writing `add x0, x1, #0x1000` as
`-lsl0` is therefore `E-RANGE-001` (`N18a`), not a silent switch to `-lsl12` —
which is exactly what `llvm-mc` does with the plain literal (`EV-26`,
`EXP-0013` §2). Writing `0x123000` as `-lsl12` is `E-RANGE-001` too (`N18b`),
because the operand is field content, not the shifted literal. The six `sub` rows
repeat both rules with `op = 1` (`ADR-0017`): `-lsl0`/`-lsl12` behave exactly as
`add`'s two rows do, and a literal outside the named half is `E-RANGE-001`
(`N18d`), even though `llvm-mc` re-encodes `sub x0, x1, #0x1000` without a
diagnostic (`EXP-0019` §2). The twelve `adds`/`subs` rows repeat it once more
with `S = 1` (`ADR-0018`): the same two `sh` halves and the same three keywords,
and `0x1000` on `adds/x64-imm12-lsl0` is `E-RANGE-001` (`N18e`) even though
`llvm-mc` re-encodes it (`EXP-0020` §2).

The twenty-four `w` rows repeat all of those rules on the `sf = 0` nodes
(`ADR-0019`), with one slot-level difference. Every register slot is
`aarch64.gpr32`/`w32`, so an `x64` operand is `E-OPERAND-001` on `kind` and
`target_type` (`N02c`); register 31 stays a plain `reg_number` whose meaning is
the node's role, and no `sp` operand kind exists. `sh`, the shift keyword and
`imm12` behave exactly as on the `x64` rows, so `4096` on
`adds/w32-imm12-lsl0` is `E-RANGE-001` (`N18f`). The `imm6` slot is the
difference: the field is six bits wide but the 32-bit instruction allocates only
`0…31` (`lsl #32` is rejected, the `imm6 = 32` word does not decode), so the
slot declares `bits: 6` and `excluded: [32 … 63]`; `imm6 = 32` is
`E-RANGE-004` (`N16d`), never a truncated shift (`EXP-0021` §2).

The twenty-four `sub`/`adds`/`subs` extended rows repeat the `0.7.0` extend rows
on the three nodes that fix `op` at bit 30 and/or `S` at bit 29 (`ADR-0020`).
The slots are identical to `add`'s: the keyword pins `option` at 13+3 and fixes
`src2`'s width, and `imm3` is `[10,3]` with `excluded: [5, 6, 7]`. Register 31 is
again a plain `reg_number` — `sp` in `sub`'s `Rd`, `xzr` in `adds`/`subs` `Rd` —
because the node's role supplies the meaning, not the slot (`EXP-0022` §2). The
four `sf = 0` extended nodes have no row, so `sub w0, w1, w2, uxtb` is
`E-FORM-001` (`N01l`).

The forty `cmp`/`cmn` alias rows are the same words as the `subs`/`adds` rows with
`Rd` at 31 and the destination dropped (`ADR-0021`). Each is the base row with
`dest` removed and `Rd` pinned, so its slots are `src`, `src2` or `imm`, and the
inherited `imm6`/`imm3`/`imm12` shapes; the shift and immediate rules transfer per
width, and the `w32` `imm6` rows carry the `32…63` tail. The alias node is the
check, not the source: it has no `encoding`, its `operation_id` names the base
node, and its `condition` is `Rd == '11111'`. A plan that names a `cmp`/`cmn` row
and also passes `dest` is `E-OPERAND-002` (`N02e`); the 32-bit extended alias rows
stay out while their base rows do (`N01l`).

`aarch64:b.cond/imm19` is the one row whose *condition* is an operand. `cond` is a
4-bit field, all sixteen values are architecture-defined, and the sixteen rows it
would otherwise need differ only in that nibble, so `role: imm`,
`kind: aarch64.cond`, `target_type: cond4` carries it with a `range` of
`0..15` and no `excluded` list (`EC-29`, ADR-0012). A `cond` of 16 is
`E-RANGE-001`, not a masked `0`: the low four bits of 16 are `eq`, a different
branch. The target is `imm19` field content, exactly as `bl`'s `imm26` is, so a
byte displacement is a `pcrel_begin` + `scale` fixup (`EXP-0014`).

The eight offset rows fix their addressing-kind bits in the template (bit 24
for the unsigned-offset rows, bits 11–10 for pre/post/unscaled) and leave one
`imm12` or `imm9` slot open, so the kind is the `form_id` and never an operand
value (`EC-14`, ADR-0013, ADR-0022). `disp` is again the field, not the byte
offset: the two `imm12` rows count 8-byte units for these `size = 11` rows
(`#16` is `disp = 2`, `#32760` is `4095`) and the six `imm9` rows count signed
bytes (`-256 … 255`). The three store `imm9` rows are the load rows' layouts
with `opc = 00` and `Rt` as the stored register, so the family is symmetric:
every addressing kind the MRS drop carries now has a row, with register offset
the last one added (`ADR-0024`, below). `LDR_64_loadlit` is the ninth member and
the only one with no `Rn`: bits 11–10 and bit 21 are not fields there, so no
kind question arises, and its single variable field is `imm19` in 4-byte units
(`ADR-0023`). A plan that states a byte offset on
an `imm12` row therefore
addresses eight times too far without any error; `expected_digest` (`OD-01`) is
what catches that class of same-length defect, which is why the unit is stated
here rather than inferred. `align_bits` is `0` on both because the range check
applies to the field value (§4), not to a byte offset that was divided first.

The sixteen register-offset rows are the only form-variant case whose variant is
two bit fields rather than a keyword, and they close the load/store family.
`option` (bits 15–13) fixes which register the row consumes as the index and how
it extends it: `011`
`lsl` and `111` `sxtx` take an `x` register, `010` `uxtw` and `110` `sxtw` take a
`w`, and the assembler rejects the cross pairings (`ldr x0, [x1, x2, uxtw]`,
`ldr x0, [x1, w2, lsl #3]`), so `index` is `aarch64.gpr64`/`x64` on four rows and
`aarch64.gpr32`/`w32` on four. `S` (bit 12) is whether the index is scaled by the
access size: `0` is the bare spelling or `#0`, `1` is `#3` on these `size = 11`
rows, so the scale is a form bit and never an operand (`INV-02`, `EC-14`,
ADR-0024). `Rm` is the `index` slot at `[16,5]`; `Rn` and `Rt` keep the
`base`/`dest`/`src` roles of the offset rows, and register 31 is again a plain
`reg_number` — `sp` in `Rn`, `xzr`/`wzr` in `Rm`. `lsl #1` and `lsl #4` have no
row: only `#0` and `#3` are encodable on a 64-bit access, and `N01q` names the
`#1` spelling. The other four `option` values (`000`, `001`, `100`, `101`) are
unallocated, so no spelling reaches them and no row needs to exclude them. Bit
21 is `1` in both templates, which is why `ldur x0, [x1, x2]` is not this kind:
the assembler reads it as an unscaled offset and demands an integer. Register
offset has no writeback variant either: `ldr x0, [x1, x2, lsl #3]!` is rejected
(`EXP-0026` §2), so there is no pre/post row to add here.

The sixteen 32-bit register-offset rows (`ADR-0025`) are the same decision one
`size` down: `LDR_32_ldst_regoff`/`STR_32_ldst_regoff` fix `size = 10` and
`opc = 01`/`00`, so the template's top bits change and `S = 1` now means `#2` on
these 4-byte accesses. `option` keeps its keyword/width pairing from the 64-bit
rows, and only `Rt` changes class: `dest`/`src` are `aarch64.gpr32`/`w32` while
`base` and the two `x` index rows stay `aarch64.gpr64`/`x64`. The suffix states
the amount (`-lsl0` … `-sxtx2`), so `-lsl1` and `-lsl3` are names for nothing at
this width (`E-FORM-001`, `N01s`), and the same modifier rule holds: `lsl #2` as
a `modifiers` entry on the `index` is `E-OPERAND-003` (`N19c`).

The move-wide rows are the fourth form-variant case and the first whose pinned
field is multi-bit; `0.17.0` brings them to twelve. `hw` (bits 22–21) selects the 16-bit lane, the four values are
exactly the four `lsl #0/#16/#32/#48` spellings the assembler accepts, and the slot
holds `imm16` field content in `0…65535`: the value the instruction builds,
`imm16 << 16·hw`, belongs to the row (`EC-30`, ADR-0014). A pre-scaled literal such
as `0x12340000` on `-lsl16` is `E-RANGE-001` (`N18c`, `N18g`), and a lane the ISA
does not have (`-lsl8`) is `E-FORM-001` (`N01d`, `N01t`). `0.17.0` adds the same
four lanes for `movk` and `movn`, whose `MOVK_64_movewide`/`MOVN_64_movewide`
nodes fix `opc` to `11`/`00`, so the mnemonic is the node and never an operand
(`EC-16`, ADR-0026). `movn` stores the raw `imm16` field: the complement is the
instruction's operation, not a plan-side computation, so `movn x0, #0x1234` is
`0x92824680` with `imm16 = 0x1234`. The `w` (`sf = 0`) lanes and the `mov` alias
have no row: the first is a different node, and the alias picks its operation and
lane from the literal's value, which is `EC-16` (`N01w`).

The three shift rows are the fifth form-variant case, and the first where one
modifier spelling splits into a form and an operand. `shift` (bits 23–22) is the
keyword: three spellings, no numeric one, and `shift = 11` is unallocated in this
node. `imm6` (bits 15–10) is the amount: `0…63`, field content, one slot with
`align_bits = 0` because nothing is scaled. An amount of `64` is `E-RANGE-001`
(`N03-imm6`), and the same shift stated as a `modifiers` entry on `-lsl0` is
`E-OPERAND-003` (`N19`): a modifier is a guard and never writes a bit, so
accepting it would emit the unshifted word and report success.

The eight extend rows are the sixth form-variant case and the first where the
form fixes an operand's *width* as well as a field. `option` (bits 15–13) is the
keyword: six `[su]xt[bhw]` spellings consume a `w` register and two `[su]xtx`
spellings consume an `x` register, and the assembler rejects the cross pairings,
so the width has to be the row's (`src2` is `aarch64.gpr32`/`w32` on six rows and
`aarch64.gpr64`/`x64` on two). The encoded register is the same 5-bit number
either way, so a single row with a free `option` and a free register class would
emit a legal word for a plan the assembler refuses (`INV-07`, `EC-32`,
ADR-0016). `imm3` (bits 12–10) is the amount: the field is three bits, but
`add/sub` extended allocates only `0…4`, so the slot is `bits: 3` with
`excluded: [5, 6, 7]` (`ADR-0009`) — `8` is `E-RANGE-001` (`N03-imm3`) and `5` is
`E-RANGE-004` (`N16c`). `imm3 = 0` stays legal: the assembler prints `uxtb #0`
back as `uxtb`, the same word, so excluding it would make the value choose the
form. The extended `sub` node and the extended `adds`/`subs` nodes, the `sf = 0`
nodes and the `cmp`/`cmn` aliases have no row (`N01f`, `N01h`, `N01i`, `N01j`);
the shifted and immediate `sub` nodes are rows in `0.8.0` and their `S = 1` twins
are rows in `0.9.0` (§8.2, ADR-0017, ADR-0018). Register 31 in those rows is
`xzr`: `sub sp, …` and `adds x0, sp, x2` are the extended node, so they are not
reachable through these rows. `N01g` names `subs` against `0.8.0`, which predates
the rows.

`adrp`'s immediate is one value over two fields: `immhi` holds bits `[20:2]` and
`immlo` holds `[1:0]`, which is why the slot has two placements in that order
(§4.1: first placement, most significant bits).

`bl` and `adrp` are the two rows whose field is not a plain integer, and the
next subsection is the rule that follows from it.

### 8.3 Scaled branch fields: the slot is the field

`bl`'s `imm26` counts instructions, not bytes, and `adrp`'s `imm21` counts
4 KiB pages. A definition slot has no scaling transform, so the table cannot say
"divide by 4 first" and must not pretend to:

- `{ "value": n }` on those slots writes `n` into the field, exactly as the
  definition says. It is the field content, not a byte offset. This is the same
  rule as an x86 `rel32` slot; the difference is only that x86's scale is 1.
- A byte offset is expressed with a fixup, which does carry a transform:
  `scale` with `transform_shift: 2` for `bl`, `page` with `pcrel_page` for
  `adrp`. That is the only path where the division happens, and it is why both
  AArch64 branch fixtures use a symbol instead of a plain value.
- `align_bits` follows the value it is attached to: `0` on the slot (a field
  value need not be a multiple of 4), and `2` on the `bl` fixup, where the
  pre-transform displacement must be instruction-aligned (`E-RANGE-003`).
  `adrp`'s fixup uses `align_bits: 0` because the page delta is already divided;
  an `align_bits: 12` there would reject every symbol that is not page-aligned.
- An operand whose bits a fixup owns carries `{}`, not a `symbol_id`
  (`01_contract.md` §8.1): only a `target` slot may name a symbol. In
  `A64-P6` the `add`'s `imm12` is such a slot.

This keeps `INV-04` intact: nothing is relaxed, and a plan that omits the
transform emits the field value it stated, which is a wrong program rather than a
repaired one. The alternative — a slot that silently scales — was rejected
because the same number would then mean different things on `add` and `bl`.

`aarch64:add/x64-imm12-lsl12` is the same rule on an immediate: the slot holds
`imm12`, and the `sh = 1` the form fixes is what multiplies it by 4096. A
slot-level scale was rejected for the reason above — the same number would mean
different things on the `-lsl0` and `-lsl12` rows — and because it would be a
second carrier for a decision the `form_id` already names (`INV-02`, ADR-0011).

`movz`'s lane is the field-selected version of the same rule: `imm16` is the
field, `hw` is the exponent of the multiplier, and the four rows are the four
values of `hw`, so no slot has to carry `16 × hw` and no plan can state a lane the
instruction does not have (`EC-30`, ADR-0014, `EXP-0016` §2). `movk` and `movn`
reuse the same four lanes; their `opc` comes from the node, so the mnemonic adds
no field to the operand list (`ADR-0026`, `EXP-0028` §2).

The shift amount is the plainest case of the same rule, with no multiplier at all:
`imm6` is the amount the plan states, `shift` is the keyword the row pins, and the
instruction applies the field directly (`EC-31`, ADR-0015, `EXP-0017` §2). The
extend amount is the same rule with a non-convex domain: `imm3` is the field, and
the three values beyond `4` are unallocated rather than out of range, so they are
`excluded` (`EC-32`, ADR-0016, `EXP-0018` §2).

RV64 follows the same rule with different shift amounts (ADR-0007, `EXP-0009`):
the source states `left_shift: 1` for `beq`/`jal` and `left_shift: 12` for
`auipc`, so a byte offset is a `scale` fixup with `transform_shift` 1 or 12,
while the slot keeps `align_bits: 0` and holds field content. The B- and J-type
slots have several placements each (`beq`: `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]`;
`jal`: `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]`), which is the scattered-field
case directive §6.3 item 6 asks for. `c.addi` needs `imm != 0` and `xd != 0`;
that is the `excluded` rule of §4, not a scaling rule, and §8.5 records it. The
extend rows' `imm3` is the same rule in §8.2: values `5`–`7` fit the field but are
unallocated, so they are excluded rather than scaled or clamped.

### 8.4 `rv64` `0.1.0`

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `riscv:add/rd-rs1-rs2` | `33000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]` | 4 | `RV-P1` |
| `riscv:addi/rd-rs1-imm12` | `13000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; src: `riscv.xreg`/`xreg` → `[15,5]`; imm: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P2` |
| `riscv:beq/rs1-rs2-imm12` | `63000000` | src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]`; target: `riscv.rel`/`imm12` → `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` | 4 | `RV-P4`, `RV-P6` |
| `riscv:jal/rd-imm20` | `6f000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; target: `riscv.rel`/`imm20` → `[31,1]`, `[12,8]`, `[20,1]`, `[21,10]` | 4 | `RV-P5`, `RV-P6` |
| `riscv:auipc/rd-imm20` | `17000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; target: `riscv.rel`/`imm20` → `[12,20]` | 4 | `RV-P8` (field half) |
| `riscv:ld/rd-base-imm12` | `03300000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P3` |
| `riscv:sd/rs-base-imm12` | `23300000` | src: `riscv.xreg`/`xreg` → `[20,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[25,7]`, `[7,5]` | 4 | `RV-P3` |

The source is the pinned UDB resolved spec (ADR-0007), not a hand-written table.
`research/evidence/experiments/EXP-0010/generate_rv64.py` reads
`encoding.match` and each `encoding.variables[].location` from
`inst/I/{add,addi,beq,jal,auipc,ld,sd}.yaml`, turns every `location` into the
placements above, and refuses to emit unless every one of the 32 bits is covered
exactly once by a fixed bit or a slot placement and the bits `match` calls
variable are exactly the bits the placements own. `EXP-0009` §5 records the same
derivation; the table is its product.

`ld.yaml` and `sd.yaml` carry one `encoding:` block per xlen. The generator reads
the `RV64` block by name, because the `RV32` block states a `not:` list on `xd`
and `xs2` (the Zilsd pair rule) that the RV64 form does not have. Selecting the
block, rather than taking the first one, is what keeps a 32-bit legality rule out
of a 64-bit table.

The document declares `enabled_extensions: ["rv64i"]` because all seven nodes are
defined by the base `I` extension either unconditionally or under `xlen: 64`,
which the generator asserts per node. One set covers the whole document and is
compared exactly with the plan's (`01_contract.md` §4); the table is never
filtered per plan. A plan that enables a different set is `E-TARGET-001`, not
silently accepted.

That exact comparison is why `c.addi` is not a row here. Its node is
`definedBy: Zca`, and `ext/C.yaml` puts `Zca` in C's `requirements.allOf`, so it
needs `rv64c` enabled — which would change this document's extension set and
therefore its digest. `0.2.0` is that change (§8.5); `0.1.0` keeps its bytes and
its digest, and a plan that names `riscv:c.addi/rd-imm6` against `0.1.0` is
`E-FORM-001` (`N01c`).

The three immediate-bearing arithmetic forms are the scattered-field case:
`beq`'s 12-bit field is `imm[12]|imm[10:5]|imm[4:1]|imm[11]` over four
placements, `jal`'s 20-bit field is `imm[20]|imm[10:1]|imm[11]|imm[19:12]`, and
`auipc`'s field is contiguous. `sd` is scattered over two placements
(`[31,25]`, `[11,7]`), `ld` is contiguous. The placements are derived from the
source `location`, so no scatter is written by hand. The slots keep
`align_bits: 0` and hold field content; a byte offset is the fixup path with
`transform_shift` 1 (`beq`, `jal`) or 12 (`auipc`), as §8.3 requires. `RV-P8`'s
associated-reference half is deliberately absent: the psABI
`R_RISCV_PCREL_HI20`/`R_RISCV_PCREL_LO12_I` pairing is not in the encoding blocks
and is not yet pinned (ADR-0007 §Decision 9).

`ld`/`sd` are the memory slice, and they are decomposed into `base` + `disp`
rather than a composite payload (ADR-0008, `OD-13`): the base is a 5-bit
register field, the displacement is a 12-bit signed field, and a fixup covering
one does not cover the other. RV64 does not scale the load/store immediate, so
`disp` is the byte displacement and no transform is involved. `ld` has one form
because it has one encoding form; a later x86 or AArch64 memory slice will need
one `form_id` per addressing variant for the same reason.

`RV-P7` (`c.addi`) is not in this table for the extension-set reason above; it
is the first row of `0.2.0`.

### 8.5 `rv64` `0.2.0`

`0.2.0` contains every row of §8.4 unchanged, plus:

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `riscv:c.addi/rd-imm6` | `0100` | dest: `riscv.xreg`/`xreg` → `[7,5]` (excl 0); imm: `riscv.imm`/`imm6` → `[12,1]`, `[2,5]` (excl 0) | 2 | `RV-P7` |

The node is `inst/C/c.addi.yaml`; its `encoding.match` is `000-----------01`, so
the fixed word is `0x0001` and the file template is `0100` (little-endian). `imm`
is `location: "12|6-2"`, which is one bit at 12 plus five bits at 6–2, and `xd` is
`11-7`. Both variables carry `not: 0`, which the generator turns into the
`excluded: [0]` on each slot (ADR-0009). Encoding either zero would still produce
two bytes — `01 05` is `c.addi a0, 0x0` to `llvm-objdump`, and `05 00` is
`c.nop 0x1` — so the plan is rejected with `E-RANGE-004` (`N16a`, `N16b`) rather
than silently materialized as a HINT.

The document's `enabled_extensions` is `["rv64i","rv64c"]`. The generator asserts
the node's `definedBy.extension.name` (`Zca`) maps to a plan token through the
same table that produced §8.4's assertions; `ext/C.yaml` states the relation
(`C` requires `Zca`). A plan that pins `0.2.0` must declare exactly that set
(`E-TARGET-001` otherwise), and a plan that pins `0.1.0` never sees the form.

## 9. Load-time checks

| Check | Code |
|---|---|
| `definition_format` unsupported (only `fmp-def/0.1` is accepted) | `E-DEF-001` |
| `namespace`/`version` not shipped by this materializer | `E-DEF-002` |
| duplicate `form_id` | `E-DEF-001` |
| `template` empty, odd-length, or non-hex | `E-DEF-001` |
| placement outside the template, or two placements overlapping | `E-DEF-001` |
| placement key outside `bit_offset`/`width`/`invert`, or a non-boolean `invert` | `E-DEF-001` |
| slot with no placement | `E-DEF-001` |
| placement widths that do not sum to `range.bits` | `E-DEF-001` |
| `x86.gpr8h` slot in a REX-prefixed template, or a REX-less `x86.gpr8` slot that does not exclude `4…7` | `E-DEF-001` |
| plan digest does not match the loaded definition | `E-DEF-001` |

A definition that fails a load-time check is unusable, so the namespace/version
gate is `E-DEF-002` and everything else is `E-DEF-001`, and no plan is read from a
definition that fails either. This is the one place where `E-DEF-001` is raised
without a plan error: the input is the definition.

## 10. Open

- `OD-06` (digest coverage) is settled for this document shape by §6; the
  measurement that confirms both halves is the digest test in `EXP-0004` §4.
- `OD-07` (AArch64 knowledge source) is settled by ADR-0005 and pinned by
  ADR-0006: the facts come from the Arm MRS 2026-06 OPENSOURCE packaging, and
  the Arm notice ships with the generated table. The format did not need to
  change for it: `adrp`'s split `immhi:immlo` is two placements of one slot, as
  §4.1 anticipated. `definitions/aarch64/0.1.0.json` … `0.17.0.json` now exist
  (§8.2); each is a superset that adds its own rows without a format change
  (ADR-0011 to ADR-0026). What is
  missing is coverage, not design: the `b`/`h` load/store widths, the signed and
  extended load rows (`LDRSW`/`LDRSB`/`LDRSH`), `prfm`, the 32-bit
  extended `add`/`sub` nodes and their aliases, and the `mov` alias and the
  32-bit move-wide lanes have no row. Each is `E-FORM-001` until
  a slice adds it.
- The archive is still not vendored and the drop is not a build input: a
  regeneration reads `research/external/arm-mrs/` after `tools/check_mrs.py`
  passes, and the shipped artifact is the JSON plus its digest.
- A slot has no scaling transform (§8.3). If a future slice needs an operand
  value that is *not* the field content, that is a format change with its own
  ADR, not a convention added here. The `-lsl12` immediate did not need one: the
  operand is field content and the shift belongs to the form. The load/store
  `imm12` rows are the same statement: the operand is the field and the
  access-size multiplier belongs to the ISA field, so a byte offset would need
  the format change ADR-0013 declined.
- `EC-09` is frozen by `0.5.0`: the family is the `/legacy`, `/vex` or `/evex`
  component of the `form_id`, and the three rows share one operation and one
  operand shape. A family the table does not carry is still `E-FORM-001`.
