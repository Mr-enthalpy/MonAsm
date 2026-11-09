# Definition Format

Status: **frozen for the v0 scope** (`ADR-0095`): the format and the shipped
tables (`x86-64` `0.1.0` … `0.68.0`, `aarch64` `0.1.0` … `0.18.0`, `rv64`
`0.1.0`/`0.2.0`). Two document formats are accepted: `fmp-def/0.1` for every
table through `0.67.0`, and `fmp-def/0.2` from `0.68.0`. They differ only in the
per-form `requires_extensions` field and the matching subset rule (§2–§3). The
format is intended for the other targets, whose tables wait
on source data, not on an open decision (`OD-07` is settled by ADR-0005 and
pinned by ADR-0006). This document defines the artifact a pinned
`definition_identity` names. It is the operational form of `OD-10`: the table
*is* the feature surface, and a `form_id` the table does not contain is
`E-FORM-001`.

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

Under `fmp-def/0.2` the same object carries
`"definition_format": "fmp-def/0.2"` and each form is
`{ "form_id": "...", "requires_extensions": [...], "template": "...",
"slots": [ ... ] }`; nothing else changes.

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `definition_format` | yes | Format version of this document | A newer document is read by an older loader with different rules and accepted. |
| `namespace`, `version` | yes | Identity the plan must name | Two rule sets are loadable under one name; the plan cannot say which it was built for. |
| `target_identity` | yes | The target the table is valid for | An x86 table is applied to an `x86-32` plan, and `REX.W` is emitted for a 32-bit mode. |
| `forms` | yes | The closed form set | An empty table would accept nothing but claim to be a definition. |

`target_identity` is compared field by field with the plan's, excluding
`feature_constraints` (which the contract already requires to be empty). A
difference in `isa_family`, `isa_variant`, or `enabled_extensions` is
`E-TARGET-001`, in `execution_mode` `E-TARGET-002`, and in `byte_order` or
`address_width` `E-TARGET-004`.

`fmp-def/0.1` and `fmp-def/0.2` differ in how `enabled_extensions` and the
per-form requirement are read:

| Format | `target_identity.enabled_extensions` | Per-form `requires_extensions` |
|---|---|---|
| `fmp-def/0.1` | equality: the plan's set MUST equal the table's set (`E-TARGET-001`) | absent; a row carries no requirement of its own |
| `fmp-def/0.2` | upper bound: the plan's set MUST be a subset of the table's set (`E-TARGET-001`) | required on every row; a named row is legal only when its set is a subset of the plan's (`E-TARGET-003`) |

The table is never filtered per plan: a definition covers exactly one target. A
table whose forms need an extension above the baseline declares the full set it
can encode in `enabled_extensions`: `0.5.0` lists `avx`, `avx512f` and
`avx512vl` because its EVEX row is `EVEX.128`, which AVX-512VL enables. Under
`0.1` that set is the plan's set, so no row needs a requirement of its own and
`E-TARGET-003` is unreachable (`04_errors.md` §2.3). Under `0.2` the same set is
the ceiling and each row states what it actually needs; `0.68.0` is the first
such table (§8.1).

There is **no digest field inside the definition**. The digest is computed over
the document and compared with `definition_identity.digest` (`E-DEF-001`); a
field that contained its own hash would have to exclude itself from its own
input, which is the kind of special case that drifts.

## 3. Forms

| Field | Required | Meaning | Counterexample if absent |
|---|---|---|---|
| `form_id` | yes | The identity a plan must name, exactly | Resolution becomes a search, and a search is a decision. |
| `requires_extensions` | yes in `fmp-def/0.2`; rejected in `0.1` | Strictly increasing list of extension names the form needs; `[]` is the baseline | A VEX row with no annotation passes a plan that never enabled `avx`, because the table's set is only an upper bound in `0.2`. |
| `template` | yes | One hex byte string; its length is the form's size, with every operand-owned bit at its base value | Without a base the loader would have to invent zeros for bits no operand writes. |
| `slots` | yes | Ordered operand signature, one entry per operand | The plan could supply operands in any order and a length check would be the only guard. |

Rules:

- Under `fmp-def/0.2` every form MUST declare `requires_extensions`; an empty
  array is the baseline (the form needs nothing above the baseline), not an
  omission. Under `fmp-def/0.1` the key is unknown and therefore `E-DEF-001`
  (closed object, §9).
- Each name MUST be non-empty, unique, and strictly increasing. The order is
  the order the first missing name is reported in (`E-TARGET-003`), so two
  spellings of one set cannot produce two diagnostics.
- Every name MUST appear in the table's `target_identity.enabled_extensions`.
  A form that requires an extension the table does not declare is `E-DEF-001`
  at load: a plan matching the table could never name that form, and the dead
  requirement would silently disable the gate.
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
| `definitions/x86_64/0.25.0.json` | `monasm.isa.x86` | `sha256:b72c0b08d30e9bbfd0c5129e01e1cecf77abcde36e2928aab2f94bb80c06a51c` |
| `definitions/x86_64/0.26.0.json` | `monasm.isa.x86` | `sha256:e253e0506d89f16b4d23fe9e9341720c5e6ada53534c199cabe31cc1b2c94212` |
| `definitions/x86_64/0.27.0.json` | `monasm.isa.x86` | `sha256:c51a0a6b1fefd708a8f05303079fc4fd245462a3f4d4d59d4fe3a5d7063430b9` |
| `definitions/x86_64/0.28.0.json` | `monasm.isa.x86` | `sha256:1c1e66235356f959a7d7d01801aae4b76ba63c5571b4234d0dfa41fea4df1854` |
| `definitions/x86_64/0.29.0.json` | `monasm.isa.x86` | `sha256:cf78fac0b9c9b9828e74559bec9f612b609468ea2894c94c6e3e5b131c3951e6` |
| `definitions/x86_64/0.30.0.json` | `monasm.isa.x86` | `sha256:5dae4541162884f14dfbebd7aaf38a49d4212f0e24155137391e6e0bf93c3cf2` |
| `definitions/x86_64/0.31.0.json` | `monasm.isa.x86` | `sha256:cc01b72ceed0c77e5079b53ea8f3035ebf44b02fd156f1aae207044cb44327d5` |
| `definitions/x86_64/0.32.0.json` | `monasm.isa.x86` | `sha256:bad81d6655d9e612fa353814fa40ba9910ba3830ac954df2169365abd02563ac` |
| `definitions/x86_64/0.33.0.json` | `monasm.isa.x86` | `sha256:b6659c62116dab7bf79f6c9704844d0fd9a1ad27ac8780e2071a93cf28dd6d8e` |
| `definitions/x86_64/0.34.0.json` | `monasm.isa.x86` | `sha256:03368b63e89e40d4cc0c58f7b394110e6dcc2e69bd801d469fa8adc505ad117f` |
| `definitions/x86_64/0.35.0.json` | `monasm.isa.x86` | `sha256:d4fd01ad8f795ea595f77dc928ded8188a0e98e7b1c5e098c458bea46616780d` |
| `definitions/x86_64/0.36.0.json` | `monasm.isa.x86` | `sha256:c4a61297e71ed19a79c0f01fb7495832ee447a1448a3b9071e1477eaeb70892f` |
| `definitions/x86_64/0.37.0.json` | `monasm.isa.x86` | `sha256:1a29805f2f9e58f4d7ab749999c90fa415c29985dae9c5e45a9294ddf25102d6` |
| `definitions/x86_64/0.38.0.json` | `monasm.isa.x86` | `sha256:47355a151d981fdbf36942305b3cad5d1a29bf6d4b20eb60d8efb13e39e2c5b2` |
| `definitions/x86_64/0.39.0.json` | `monasm.isa.x86` | `sha256:08e2fb7afee30bc6bf63f3bd795f88f6dfb4ae100a41e72f2f6491b113a3b1a0` |
| `definitions/x86_64/0.40.0.json` | `monasm.isa.x86` | `sha256:ddeb4734cab0483c6f440106954233072d352910998c5680e28b6d33352eb468` |
| `definitions/x86_64/0.41.0.json` | `monasm.isa.x86` | `sha256:a2c5fa28122f43ce824ee637017dd6fdaef4e7455122b5cfa0e065c3400ffaef` |
| `definitions/x86_64/0.42.0.json` | `monasm.isa.x86` | `sha256:b45380cd781c4e2fd26da3218a2655b332ba7ab17680782d99aca5ed0bdc6c9b` |
| `definitions/x86_64/0.43.0.json` | `monasm.isa.x86` | `sha256:da40c8548f75b6dd0f509ff1b10e9b3e633c69a7a3a26d660d6bd87c58a1a54c` |
| `definitions/x86_64/0.44.0.json` | `monasm.isa.x86` | `sha256:4361f534bd04064d9ce0b89e8d5f6ad077ceb4a8c890b103efc16899e887c922` |
| `definitions/x86_64/0.45.0.json` | `monasm.isa.x86` | `sha256:9adaf50a6798c7b4bd5f0090f9860de30e360994c45138f017a3c1298e5fc2d8` |
| `definitions/x86_64/0.46.0.json` | `monasm.isa.x86` | `sha256:44a396f348cc940bdf247c21e4752358d929df952ea0c7f2e5b5be14a63e2e9e` |
| `definitions/x86_64/0.47.0.json` | `monasm.isa.x86` | `sha256:0894646319c6f42071b0fd9d24417e27246a49343144540c80d05e49da7045c3` |
| `definitions/x86_64/0.48.0.json` | `monasm.isa.x86` | `sha256:552b82733ac35ec9d6270dbab21bef8b19f3de800f25fc7f9c0654c4eb6189ff` |
| `definitions/x86_64/0.49.0.json` | `monasm.isa.x86` | `sha256:5a7ec114d02101465839a60645c4cfb8b4527dab766a6c90f801e0b38161ccd0` |
| `definitions/x86_64/0.50.0.json` | `monasm.isa.x86` | `sha256:6f38e272ef1464b5067053c7a10d744adee19699fbe4ecbc0928fb3c8f7da75a` |
| `definitions/x86_64/0.51.0.json` | `monasm.isa.x86` | `sha256:e73395dffc494d13d0b142cbba0e4c55a40d19bcd68a6b793025156bbcb41bc5` |
| `definitions/x86_64/0.52.0.json` | `monasm.isa.x86` | `sha256:4587b149e1119681ffefe011862343d8bccd0f52dbe7d278a0afb05517f7f7ae` |
| `definitions/x86_64/0.53.0.json` | `monasm.isa.x86` | `sha256:9c4c913f51e0e74710f416cd03d1547e6d4af4f2b678c1f1c4ae46f5722ff52b` |
| `definitions/x86_64/0.54.0.json` | `monasm.isa.x86` | `sha256:4513f6a9b15293f96bb79e46dbd477ea7cc051e3fb33a9a9ce3792e8ac6fa8cd` |
| `definitions/x86_64/0.55.0.json` | `monasm.isa.x86` | `sha256:e4fe01184a25274242c3eb9cf29b411d48d2d629cd2befbcbd274ef6384618fc` |
| `definitions/x86_64/0.56.0.json` | `monasm.isa.x86` | `sha256:d039c97253fbdefba9c68c4fdab0d3310d17b809b8ba29fc268e6d8458f2ef87` |
| `definitions/x86_64/0.57.0.json` | `monasm.isa.x86` | `sha256:4b41ac755862f46d9e9e8bd574c399d8aa6a771cf93358772e590fae11314ca7` |
| `definitions/x86_64/0.58.0.json` | `monasm.isa.x86` | `sha256:8e7fc7e799ede398cb5d560b2ca43991c11cba518cadae45f84222bbf93994bf` |
| `definitions/x86_64/0.59.0.json` | `monasm.isa.x86` | `sha256:bf7e54f512d27e83a3834b95ec4dc75767ee86d619ec833dee2a7cf13637826f` |
| `definitions/x86_64/0.60.0.json` | `monasm.isa.x86` | `sha256:f951de4cc1532c3df5a8f715343d8a9e7a4b3ba302df49c9fa3fa2f85a45d7b1` |
| `definitions/x86_64/0.61.0.json` | `monasm.isa.x86` | `sha256:e5a57fc7f72d810283980e1c059ff4195b77b1bc3c5ff30ff830798d7dd91983` |
| `definitions/x86_64/0.62.0.json` | `monasm.isa.x86` | `sha256:bbcd8062c84580e208c1cbf275254593a7d937fd7de28fde19e7dc5c5049e3b3` |
| `definitions/x86_64/0.63.0.json` | `monasm.isa.x86` | `sha256:72c7e8f2fcf4c73ad816d7de274d9b46edec7d9ef99b4834c27140d83d6c91e8` |
| `definitions/x86_64/0.64.0.json` | `monasm.isa.x86` | `sha256:fc98a834b7840d3f2383b05a5d2950966a81187234a080f24f7ad85ab6c07a4f` |
| `definitions/x86_64/0.65.0.json` | `monasm.isa.x86` | `sha256:9f5bc421a67688426dea259a7f5a9c4c5eb0746db0dd1c5b473a30ba3612b42a` |
| `definitions/x86_64/0.66.0.json` | `monasm.isa.x86` | `sha256:63b3b3a153aa0b5508f2055496efa1c56ac74e56b03d56f56f5c522b6d2e1904` |
| `definitions/x86_64/0.67.0.json` | `monasm.isa.x86` | `sha256:367d76ebf89ee9c1cf51f561b4798eeb0a2000ae3688ee9a52a4c4a9eaea5c9e` |
| `definitions/x86_64/0.68.0.json` | `monasm.isa.x86` | `sha256:4c9ff304b305ceb831fd99e22bf0a7c422cce4104d08de604a6509f58e1501d2` |
| `definitions/x86_64/0.69.0.json` | `monasm.isa.x86` | `sha256:94dee360550537cbefed798bcc4e7d790b9a879391e0b6a47ecf24a819a6b596` |
| `definitions/x86_64/0.70.0.json` | `monasm.isa.x86` | `sha256:02cbd866ce04b7584456bccf177c1aef7395a6b503240ddd1617be8e73f9eb2e` |
| `definitions/x86_64/0.71.0.json` | `monasm.isa.x86` | `sha256:2858c0f163b1239b37f7be9ba294d8d81748038987a154afac66c2b63b4d2c5b` |
| `definitions/x86_64/0.72.0.json` | `monasm.isa.x86` | `sha256:15fbacc2e014b9c135762f53a8b55b8c7d5dc21e9ff665ee5a0259437d70bf11` |
| `definitions/x86_64/0.73.0.json` | `monasm.isa.x86` | `sha256:dfe7c9385b5a6a8636d8a54252ba72e3630aee3573b7e71062c4d7f8777d4237` |
| `definitions/x86_64/0.74.0.json` | `monasm.isa.x86` | `sha256:27f337115cffe89c8d7028863e7748783247344ba4d8e622fa9c4345efdead58` |
| `definitions/x86_64/0.75.0.json` | `monasm.isa.x86` | `sha256:5b13b6b96a4061f354e7d0a371175936cb66c71dbfa80a7eabbf74bfe7eef40d` |
| `definitions/x86_64/0.76.0.json` | `monasm.isa.x86` | `sha256:7535ae0641806b1785096bd286ac62f90f7f02023fd5d47a92b4d4df6371e39a` |
| `definitions/x86_64/0.77.0.json` | `monasm.isa.x86` | `sha256:093d8f3c0abefc04b9c9b4ed421412a1f9a1fe54bf430951653fac0955d4c68b` |
| `definitions/x86_64/0.78.0.json` | `monasm.isa.x86` | `sha256:30cb9f13047ff742d8f53a20f93218a601302bd52814ad26364347cb85576a21` |
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
| `definitions/aarch64/0.18.0.json` | `monasm.isa.aarch64` | `sha256:c32e3674bf50140276d29fd01891bab20a86b849fa1503d2c9d02ae6aa503824` |
| `definitions/aarch64/0.19.0.json` | `monasm.isa.aarch64` | `sha256:f299d978b734a295fe111f6e03999d891d08a84e6d02c36ce83ee9a25c961546` |
| `definitions/aarch64/0.20.0.json` | `monasm.isa.aarch64` | `sha256:05033c9e1c5ca430d2922312cf7139c9bc4e8cc7c34364e24a455efa9a1df6cd` |
| `definitions/rv64/0.1.0.json` | `monasm.isa.riscv` | `sha256:6afb2bf48c3c8b7c8878868eb9afce9c10c219ff12b297b7e68843dbba7f7083` |
| `definitions/rv64/0.2.0.json` | `monasm.isa.riscv` | `sha256:8329a38faa964f9c69207a48e3bfb45c13fb0ddbaeb829ddcc0dbd1cffa8de10` |
| `definitions/rv64/0.3.0.json` | `monasm.isa.riscv` | `sha256:484eae4ba4c80c1ff4d91bc11a6fd9bd36bdc511a8271815d76c0883869ad2af` |
| `definitions/rv64/0.4.0.json` | `monasm.isa.riscv` | `sha256:e00dee01004ec9d927ac4e5494e8e6dabfcbb4ff0e123980190c9871624afa76` |
| `definitions/rv64/0.5.0.json` | `monasm.isa.riscv` | `sha256:571ab1ed93f4464d5ec8981df02dd0444005ababdaaf1e175d0ec489bb33a776` |
| `definitions/rv64/0.6.0.json` | `monasm.isa.riscv` | `sha256:0baf3b34804df12c5e73debf54cf70420ce436bec914258eb5216549972d9585` |

A plan names its `namespace`, `version` and digest in `definition_identity`.

### 8.1 `x86-64` `0.1.0` … `0.78.0`

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
| `x86:mov/r32-addr32-riprel32/legacy` | `678b0500000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `ADR-0107`, `X86-P77` — `0.71.0`+ |
| `x86:mov/addr32-riprel32-r32/legacy` | `67890500000000` | src: `x86.gpr32`/`r32` → `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `ADR-0107`, `X86-P77` — `0.71.0`+ |
| `x86:mov/r64-addr32-riprel32/legacy` | `67488b0500000000` | dest: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; target: `x86.rel`/`riprel32` → `[32,32]` | 8 | `ADR-0107`, `X86-P77` — `0.71.0`+ |
| `x86:mov/addr32-riprel32-r64/legacy` | `6748890500000000` | src: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; target: `x86.rel`/`riprel32` → `[32,32]` | 8 | `ADR-0107`, `X86-P77` — `0.71.0`+ |
| `x86:mov/r16-addr32-riprel32/legacy` | `67668b0500000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; target: `x86.rel`/`riprel32` → `[32,32]` | 8 | `ADR-0107`, `X86-P77` — `0.71.0`+ |
| `x86:mov/addr32-riprel32-r16/legacy` | `6766890500000000` | src: `x86.gpr16`/`r16` → `[27,3]`; target: `x86.rel`/`riprel32` → `[32,32]` | 8 | `ADR-0107`, `X86-P77` — `0.71.0`+ |
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
| `x86:movaps/xmm-ext-rsp-disp8/legacy` | `440f28442400` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/xmm-ext-rsp-disp32/legacy` | `440f28842400000000` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/xmm-ext-r12-disp8/legacy` | `450f28442400` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/xmm-ext-r12-disp32/legacy` | `450f28842400000000` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/rsp-disp8-xmm-ext/legacy` | `440f29442400` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/rsp-disp32-xmm-ext/legacy` | `440f29842400000000` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/r12-disp8-xmm-ext/legacy` | `450f29442400` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/r12-disp32-xmm-ext/legacy` | `450f29842400000000` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `ADR-0106`, `X86-P76` — `0.70.0`+ |
| `x86:movaps/xmm-base-index-disp8/legacy` | `0f28440000` | dest: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:movaps/base-index-disp8-xmm/legacy` | `0f29440000` | src: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:movaps/xmm-ext-base-index-disp8/legacy` | `440f28440000` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:movaps/base-index-disp8-xmm-ext/legacy` | `440f29440000` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:movaps/xmm-base-index-disp32/legacy` | `0f28840000000000` | dest: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:movaps/base-index-disp32-xmm/legacy` | `0f29840000000000` | src: `x86.xmm`/`xmm` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:movaps/xmm-ext-base-index-disp32/legacy` | `440f28840000000000` | dest: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:movaps/base-index-disp32-xmm-ext/legacy` | `440f29840000000000` | src: `x86.xmm`/`xmm` → `[2,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/xmm-base-index-disp8/vex` | `c5f828440000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/base-index-disp8-xmm/vex` | `c5f829440000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/xmm-ext-base-index-disp8/vex` | `c57828440000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/base-index-disp8-xmm-ext/vex` | `c57829440000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/xmm-base-index-disp32/vex` | `c5f828840000000000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/base-index-disp32-xmm/vex` | `c5f829840000000000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/xmm-ext-base-index-disp32/vex` | `c57828840000000000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:vmovaps/base-index-disp32-xmm-ext/vex` | `c57829840000000000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | EC-02, EC-09, EC-37, EC-38, `ADR-0108`, `X86-P78` — `0.72.0`+ |
| `x86:mov/r8-base-index-disp8/legacy` | `8a440000` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/base-index-disp8-r8/legacy` | `88440000` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/r8-base-index-disp32/legacy` | `8a840000000000` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/base-index-disp32-r8/legacy` | `88840000000000` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/r8h-base-index-disp8/legacy` | `8a440000` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/base-index-disp8-r8h/legacy` | `88440000` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/r8h-base-index-disp32/legacy` | `8a840000000000` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/base-index-disp32-r8h/legacy` | `88840000000000` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/r8-base-index-disp8-rex/legacy` | `408a440000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/base-index-disp8-r8-rex/legacy` | `4088440000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/r8-base-index-disp32-rex/legacy` | `408a840000000000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:mov/base-index-disp32-r8-rex/legacy` | `4088840000000000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | EC-02, EC-06, EC-36, EC-37, `ADR-0109`, `X86-P79` — `0.73.0`+ |
| `x86:sub/rm64-r64/legacy` | `4829c8` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0110`, `X86-P80` — `0.74.0`+ |
| `x86:sub/rm32-r32/legacy` | `29c8` | dest: `x86.gpr32`/`rm32` → `[8,3]`; src: `x86.gpr32`/`r32` → `[11,3]` | 2 | EC-01, EC-06, EC-07, EC-42, `ADR-0110`, `X86-P80` — `0.74.0`+ |
| `x86:sub/rm16-r16/legacy` | `6629c8` | dest: `x86.gpr16`/`rm16` → `[16,3]`; src: `x86.gpr16`/`r16` → `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0110`, `X86-P80` — `0.74.0`+ |
| `x86:add/rm64-r64/legacy` | `4801c0` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:add/rm32-r32/legacy` | `01c0` | dest: `x86.gpr32`/`rm32` → `[8,3]`; src: `x86.gpr32`/`r32` → `[11,3]` | 2 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:add/rm16-r16/legacy` | `6601c0` | dest: `x86.gpr16`/`rm16` → `[16,3]`; src: `x86.gpr16`/`r16` → `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:and/rm64-r64/legacy` | `4821c0` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:and/rm32-r32/legacy` | `21c0` | dest: `x86.gpr32`/`rm32` → `[8,3]`; src: `x86.gpr32`/`r32` → `[11,3]` | 2 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:and/rm16-r16/legacy` | `6621c0` | dest: `x86.gpr16`/`rm16` → `[16,3]`; src: `x86.gpr16`/`r16` → `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:or/rm64-r64/legacy` | `4809c0` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:or/rm32-r32/legacy` | `09c0` | dest: `x86.gpr32`/`rm32` → `[8,3]`; src: `x86.gpr32`/`r32` → `[11,3]` | 2 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:or/rm16-r16/legacy` | `6609c0` | dest: `x86.gpr16`/`rm16` → `[16,3]`; src: `x86.gpr16`/`r16` → `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:xor/rm64-r64/legacy` | `4831c0` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:xor/rm32-r32/legacy` | `31c0` | dest: `x86.gpr32`/`rm32` → `[8,3]`; src: `x86.gpr32`/`r32` → `[11,3]` | 2 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:xor/rm16-r16/legacy` | `6631c0` | dest: `x86.gpr16`/`rm16` → `[16,3]`; src: `x86.gpr16`/`r16` → `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:cmp/rm64-r64/legacy` | `4839c0` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:cmp/rm32-r32/legacy` | `39c0` | dest: `x86.gpr32`/`rm32` → `[8,3]`; src: `x86.gpr32`/`r32` → `[11,3]` | 2 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:cmp/rm16-r16/legacy` | `6639c0` | dest: `x86.gpr16`/`rm16` → `[16,3]`; src: `x86.gpr16`/`r16` → `[19,3]` | 3 | EC-01, EC-06, EC-07, EC-42, `ADR-0113`, `X86-P81` — `0.75.0`+ |
| `x86:add/rm32-imm8/legacy` | `83c000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm8` → `[16,8]` | 3 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:add/rm32-imm32/legacy` | `81c000000000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:add/rm16-imm8/legacy` | `6683c000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:add/rm16-imm16/legacy` | `6681c00000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm16` → `[24,16]` | 5 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:sub/rm32-imm8/legacy` | `83e800` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm8` → `[16,8]` | 3 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:sub/rm32-imm32/legacy` | `81e800000000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:sub/rm16-imm8/legacy` | `6683e800` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:sub/rm16-imm16/legacy` | `6681e80000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm16` → `[24,16]` | 5 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:and/rm64-imm8/legacy` | `4883e000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:and/rm64-imm32/legacy` | `4881e000000000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:and/rm32-imm8/legacy` | `83e000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm8` → `[16,8]` | 3 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:and/rm32-imm32/legacy` | `81e000000000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:and/rm16-imm8/legacy` | `6683e000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:and/rm16-imm16/legacy` | `6681e00000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm16` → `[24,16]` | 5 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:or/rm64-imm8/legacy` | `4883c800` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:or/rm64-imm32/legacy` | `4881c800000000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:or/rm32-imm8/legacy` | `83c800` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm8` → `[16,8]` | 3 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:or/rm32-imm32/legacy` | `81c800000000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:or/rm16-imm8/legacy` | `6683c800` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:or/rm16-imm16/legacy` | `6681c80000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm16` → `[24,16]` | 5 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:xor/rm64-imm8/legacy` | `4883f000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:xor/rm64-imm32/legacy` | `4881f000000000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:xor/rm32-imm8/legacy` | `83f000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm8` → `[16,8]` | 3 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:xor/rm32-imm32/legacy` | `81f000000000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:xor/rm16-imm8/legacy` | `6683f000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:xor/rm16-imm16/legacy` | `6681f00000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm16` → `[24,16]` | 5 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:cmp/rm64-imm8/legacy` | `4883f800` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:cmp/rm64-imm32/legacy` | `4881f800000000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:cmp/rm32-imm8/legacy` | `83f800` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm8` → `[16,8]` | 3 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:cmp/rm32-imm32/legacy` | `81f800000000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:cmp/rm16-imm8/legacy` | `6683f800` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:cmp/rm16-imm16/legacy` | `6681f80000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm16` → `[24,16]` | 5 | EC-01, EC-06, EC-07, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:and/rax-imm32/legacy` | `482500000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-04, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:or/rax-imm32/legacy` | `480d00000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-04, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:xor/rax-imm32/legacy` | `483500000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-04, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:cmp/rax-imm32/legacy` | `483d00000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-04, `ADR-0114`, `X86-P82` — `0.76.0`+ |
| `x86:mov/r16-imm16/legacy` | `66b80000` | dest: `x86.gpr16`/`r16` → `[8,3]`; imm: `x86.imm`/`imm16` → `[16,16]` | 4 | EC-04, `ADR-0115`, `X86-P83` — `0.77.0`+ |
| `x86:mov/r32-imm32/legacy` | `b800000000` | dest: `x86.gpr32`/`r32` → `[0,3]`; imm: `x86.imm`/`imm32` → `[8,32]` | 5 | EC-04, `ADR-0115`, `X86-P83` — `0.77.0`+ |
| `x86:mov/rm16-imm16/legacy` | `66c7c00000` | dest: `x86.gpr16`/`rm16` → `[16,3]`; imm: `x86.imm`/`imm16` → `[24,16]` | 5 | EC-04, `ADR-0115`, `X86-P83` — `0.77.0`+ |
| `x86:mov/rm32-imm32/legacy` | `c7c000000000` | dest: `x86.gpr32`/`rm32` → `[8,3]`; imm: `x86.imm`/`imm32` → `[16,32]` | 6 | EC-04, `ADR-0115`, `X86-P83` — `0.77.0`+ |
| `x86:mov/rm64-imm32/legacy` | `48c7c000000000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | EC-04, `ADR-0115`, `X86-P83` — `0.77.0`+ |
| `x86:sub/base-disp8-r64/legacy` | `48294000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/base-disp32-r64/legacy` | `48298000000000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/r64-base-disp8/legacy` | `482b4000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; src: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/r64-base-disp32/legacy` | `482b8000000000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; src: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/base-disp8-r32/legacy` | `294000` | src: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/base-disp32-r32/legacy` | `298000000000` | src: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/r32-base-disp8/legacy` | `2b4000` | dest: `x86.gpr32`/`r32` → `[11,3]`; src: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/r32-base-disp32/legacy` | `2b8000000000` | dest: `x86.gpr32`/`r32` → `[11,3]`; src: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/base-disp8-r16/legacy` | `66294000` | src: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/base-disp32-r16/legacy` | `66298000000000` | src: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/r16-base-disp8/legacy` | `662b4000` | dest: `x86.gpr16`/`r16` → `[19,3]`; src: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
| `x86:sub/r16-base-disp32/legacy` | `662b8000000000` | dest: `x86.gpr16`/`r16` → `[19,3]`; src: `x86.gpr64`/`rm64` → `[16,3]` (excl 4); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | EC-42, `ADR-0116`, `X86-P84` — `0.78.0`+ |
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
| `x86:vmovaps/xmm-abs32/evex` | `62f17c0828042500000000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P29` |
| `x86:vmovaps/abs32-xmm/evex` | `62f17c0829042500000000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P29` |
| `x86:vmovaps/ymm-abs32/evex` | `62f17c2828042500000000` | dest: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P29` |
| `x86:vmovaps/abs32-ymm/evex` | `62f17c2829042500000000` | src: `x86.ymm`/`ymm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P29` |
| `x86:vmovaps/zmm-abs32/evex` | `62f17c4828042500000000` | dest: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P29` |
| `x86:vmovaps/abs32-zmm/evex` | `62f17c4829042500000000` | src: `x86.zmm`/`zmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; disp: `x86.imm`/`disp32` → `[56,32]` | 11 | `EC-02`, `EC-09`, `EC-35`, `EC-37`, `EC-40`, `X86-P29` |
| `x86:mov/r64-abs32/legacy` | `488b042500000000` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-35`, `EC-37`, `X86-P30` |
| `x86:mov/abs32-r64/legacy` | `4889042500000000` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-35`, `EC-37`, `X86-P30` |
| `x86:mov/r32-abs32/legacy` | `8b042500000000` | dest: `x86.gpr32`/`r32` → `[11,3]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-05`, `EC-35`, `EC-37`, `EC-38`, `X86-P31` |
| `x86:mov/r32-ext-abs32/legacy` | `448b042500000000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-06`, `EC-35`, `EC-37`, `EC-38`, `X86-P31` |
| `x86:mov/abs32-r32/legacy` | `89042500000000` | src: `x86.gpr32`/`r32` → `[11,3]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-05`, `EC-35`, `EC-37`, `EC-38`, `X86-P31` |
| `x86:mov/abs32-r32-ext/legacy` | `4489042500000000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-06`, `EC-35`, `EC-37`, `EC-38`, `X86-P31` |
| `x86:mov/r16-abs32/legacy` | `668b042500000000` | dest: `x86.gpr16`/`r16` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P32` |
| `x86:mov/r16-ext-abs32/legacy` | `66448b042500000000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-05`, `EC-06`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P32` |
| `x86:mov/abs32-r16/legacy` | `6689042500000000` | src: `x86.gpr16`/`r16` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P32` |
| `x86:mov/abs32-r16-ext/legacy` | `664489042500000000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-05`, `EC-06`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P32` |
| `x86:mov/r8-abs32/legacy` | `8a042500000000` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/abs32-r8/legacy` | `88042500000000` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/r8h-abs32/legacy` | `8a242500000000` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/abs32-r8h/legacy` | `88242500000000` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/r8-rex-abs32/legacy` | `408a242500000000` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/abs32-r8-rex/legacy` | `4088242500000000` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/r8-ext-abs32/legacy` | `448a042500000000` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-06`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/abs32-r8-ext/legacy` | `4488042500000000` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-05`, `EC-06`, `EC-27`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P33` |
| `x86:mov/r8-ext-base-disp8/legacy` | `448a4000` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r8-ext-base-disp32/legacy` | `448a8000000000` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r8-ext-rsp-disp8/legacy` | `448a442400` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r8-ext-rsp-disp32/legacy` | `448a842400000000` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r8-ext-r12-disp8/legacy` | `458a442400` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r8-ext-r12-disp32/legacy` | `458a842400000000` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/base-disp8-r8-ext/legacy` | `44884000` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/base-disp32-r8-ext/legacy` | `44888000000000` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/rsp-disp8-r8-ext/legacy` | `4488442400` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/rsp-disp32-r8-ext/legacy` | `4488842400000000` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r12-disp8-r8-ext/legacy` | `4588442400` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r12-disp32-r8-ext/legacy` | `4588842400000000` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `EC-37`, `EC-38`, `X86-P34` |
| `x86:mov/r8-base/legacy` | `8a00` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) | 2 | `EC-02`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/base-r8/legacy` | `8800` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) | 2 | `EC-02`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/r8h-base/legacy` | `8a20` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) | 2 | `EC-02`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/base-r8h/legacy` | `8820` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) | 2 | `EC-02`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/r8-base-rex/legacy` | `408a20` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/base-r8-rex/legacy` | `408820` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/r8-ext-base/legacy` | `448a00` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/base-r8-ext/legacy` | `448800` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-36`, `X86-P35` |
| `x86:mov/r8-rsp/legacy` | `8a0424` | dest: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7) | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/rsp-r8/legacy` | `880424` | src: `x86.gpr8`/`r8` → `[11,3]` (excl 4, 5, 6, 7) | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r8-r12/legacy` | `418a0424` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7) | 4 | `EC-02`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r12-r8/legacy` | `41880424` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 4, 5, 6, 7) | 4 | `EC-02`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r8h-rsp/legacy` | `8a2424` | dest: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3) | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/rsp-r8h/legacy` | `882424` | src: `x86.gpr8h`/`r8h` → `[11,3]` (excl 0, 1, 2, 3) | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r8-rsp-rex/legacy` | `408a2424` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/rsp-r8-rex/legacy` | `40882424` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r8-r12-rex/legacy` | `418a2424` | dest: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r12-r8-rex/legacy` | `41882424` | src: `x86.gpr8`/`r8` → `[19,3]` (excl 0, 1, 2, 3) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r8-ext-rsp/legacy` | `448a0424` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/rsp-r8-ext/legacy` | `44880424` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r8-ext-r12/legacy` | `458a0424` | dest: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r12-r8-ext/legacy` | `45880424` | src: `x86.gpr8`/`r8` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-35`, `EC-36`, `X86-P36` |
| `x86:mov/r64-base/legacy` | `488b00` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-34`, `EC-35`, `X86-P37` |
| `x86:mov/base-r64/legacy` | `488900` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-34`, `EC-35`, `X86-P37` |
| `x86:mov/r64-rsp/legacy` | `488b0424` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 4 | `EC-02`, `EC-06`, `EC-35`, `X86-P38` |
| `x86:mov/rsp-r64/legacy` | `48890424` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 4 | `EC-02`, `EC-06`, `EC-35`, `X86-P38` |
| `x86:mov/r64-r12/legacy` | `498b0424` | dest: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 4 | `EC-02`, `EC-06`, `EC-35`, `X86-P38` |
| `x86:mov/r12-r64/legacy` | `49890424` | src: `x86.gpr64`/`r64` → `[2,1]`, `[19,3]` | 4 | `EC-02`, `EC-06`, `EC-35`, `X86-P38` |
| `x86:mov/r32-base/legacy` | `8b00` | dest: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) | 2 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P39` |
| `x86:mov/base-r32/legacy` | `8900` | src: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4, 5) | 2 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P39` |
| `x86:mov/r32-ext-base/legacy` | `448b00` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P39` |
| `x86:mov/base-r32-ext/legacy` | `448900` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 5, 12, 13) | 3 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P39` |
| `x86:mov/r32-base-ext/legacy` | `418b00` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 3 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P39` |
| `x86:mov/base-ext-r32/legacy` | `418900` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 3 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P39` |
| `x86:mov/r32-rsp/legacy` | `8b0424` | dest: `x86.gpr32`/`r32` → `[11,3]` | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/rsp-r32/legacy` | `890424` | src: `x86.gpr32`/`r32` → `[11,3]` | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/r32-r12/legacy` | `418b0424` | dest: `x86.gpr32`/`r32` → `[19,3]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/r12-r32/legacy` | `41890424` | src: `x86.gpr32`/`r32` → `[19,3]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/r32-ext-rsp/legacy` | `448b0424` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/rsp-r32-ext/legacy` | `44890424` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/r32-ext-r12/legacy` | `458b0424` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/r12-r32-ext/legacy` | `45890424` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `EC-38`, `X86-P40` |
| `x86:mov/r32-base-disp8/legacy` | `8b4000` | dest: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P41` |
| `x86:mov/base-disp8-r32/legacy` | `894000` | src: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp8` → `[16,8]` | 3 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P41` |
| `x86:mov/r32-ext-base-disp8/legacy` | `448b4000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P41` |
| `x86:mov/base-disp8-r32-ext/legacy` | `44894000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P41` |
| `x86:mov/r32-base-ext-disp8/legacy` | `418b4000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P41` |
| `x86:mov/base-ext-disp8-r32/legacy` | `41894000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P41` |
| `x86:mov/r32-base-disp32/legacy` | `8b8000000000` | dest: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P42` |
| `x86:mov/base-disp32-r32/legacy` | `898000000000` | src: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[8,3]` (excl 4); disp: `x86.imm`/`disp32` → `[16,32]` | 6 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P42` |
| `x86:mov/r32-ext-base-disp32/legacy` | `448b8000000000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P42` |
| `x86:mov/base-disp32-r32-ext/legacy` | `44898000000000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 4, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P42` |
| `x86:mov/r32-base-ext-disp32/legacy` | `418b8000000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P42` |
| `x86:mov/base-ext-disp32-r32/legacy` | `41898000000000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-38`, `X86-P42` |
| `x86:mov/r32-rsp-disp8/legacy` | `8b442400` | dest: `x86.gpr32`/`r32` → `[11,3]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/rsp-disp8-r32/legacy` | `89442400` | src: `x86.gpr32`/`r32` → `[11,3]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/r32-ext-rsp-disp8/legacy` | `448b442400` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/rsp-disp8-r32-ext/legacy` | `4489442400` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/r32-r12-disp8/legacy` | `418b442400` | dest: `x86.gpr32`/`r32` → `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/r12-disp8-r32/legacy` | `4189442400` | src: `x86.gpr32`/`r32` → `[19,3]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/r32-ext-r12-disp8/legacy` | `458b442400` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/r12-disp8-r32-ext/legacy` | `4589442400` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P43` |
| `x86:mov/r32-rsp-disp32/legacy` | `8b842400000000` | dest: `x86.gpr32`/`r32` → `[11,3]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/rsp-disp32-r32/legacy` | `89842400000000` | src: `x86.gpr32`/`r32` → `[11,3]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/r32-ext-rsp-disp32/legacy` | `448b842400000000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/rsp-disp32-r32-ext/legacy` | `4489842400000000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/r32-r12-disp32/legacy` | `418b842400000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/r12-disp32-r32/legacy` | `4189842400000000` | src: `x86.gpr32`/`r32` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/r32-ext-r12-disp32/legacy` | `458b842400000000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/r12-disp32-r32-ext/legacy` | `4589842400000000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-28`, `EC-34`, `EC-35`, `X86-P44` |
| `x86:mov/r16-base/legacy` | `668b00` | dest: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4, 5) | 3 | `EC-02`, `EC-27`, `EC-38`, `X86-P45` |
| `x86:mov/base-r16/legacy` | `668900` | src: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[16,3]` (excl 4, 5) | 3 | `EC-02`, `EC-27`, `EC-38`, `X86-P45` |
| `x86:mov/r16-base-ext/legacy` | `66418b00` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 4 | `EC-02`, `EC-27`, `EC-38`, `X86-P45` |
| `x86:mov/base-ext-r16/legacy` | `66418900` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 4 | `EC-02`, `EC-27`, `EC-38`, `X86-P45` |
| `x86:mov/r16-rsp/legacy` | `668b0424` | dest: `x86.gpr16`/`r16` → `[19,3]` | 4 | `EC-02`, `EC-27`, `EC-35`, `X86-P45` |
| `x86:mov/rsp-r16/legacy` | `66890424` | src: `x86.gpr16`/`r16` → `[19,3]` | 4 | `EC-02`, `EC-27`, `EC-35`, `X86-P45` |
| `x86:mov/r16-r12/legacy` | `66418b0424` | dest: `x86.gpr16`/`r16` → `[27,3]` | 5 | `EC-02`, `EC-27`, `EC-35`, `X86-P45` |
| `x86:mov/r12-r16/legacy` | `6641890424` | src: `x86.gpr16`/`r16` → `[27,3]` | 5 | `EC-02`, `EC-27`, `EC-35`, `X86-P45` |
| `x86:mov/r16-ext-base/legacy` | `66448b00` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P46` |
| `x86:mov/base-r16-ext/legacy` | `66448900` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4, 5) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P46` |
| `x86:mov/r16-ext-base-ext/legacy` | `66458b00` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P46` |
| `x86:mov/base-ext-r16-ext/legacy` | `66458900` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12, 13) | 4 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P46` |
| `x86:mov/r16-ext-rsp/legacy` | `66448b0424` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-35`, `X86-P46` |
| `x86:mov/rsp-r16-ext/legacy` | `6644890424` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-35`, `X86-P46` |
| `x86:mov/r16-ext-r12/legacy` | `66458b0424` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-35`, `X86-P46` |
| `x86:mov/r12-r16-ext/legacy` | `6645890424` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7) | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-35`, `X86-P46` |
| `x86:mov/r16-ext-base-disp8/legacy` | `66448b4000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/base-disp8-r16-ext/legacy` | `6644894000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/r16-ext-base-ext-disp8/legacy` | `66458b4000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/base-ext-disp8-r16-ext/legacy` | `6645894000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/r16-ext-rsp-disp8/legacy` | `66448b442400` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/rsp-disp8-r16-ext/legacy` | `664489442400` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/r16-ext-r12-disp8/legacy` | `66458b442400` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/r12-disp8-r16-ext/legacy` | `664589442400` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P47` |
| `x86:mov/r16-ext-base-disp32/legacy` | `66448b8000000000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/base-disp32-r16-ext/legacy` | `6644898000000000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]` (excl 4); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/r16-ext-base-ext-disp32/legacy` | `66458b8000000000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/base-ext-disp32-r16-ext/legacy` | `6645898000000000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7, 12); disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/r16-ext-rsp-disp32/legacy` | `66448b842400000000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/rsp-disp32-r16-ext/legacy` | `664489842400000000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/r16-ext-r12-disp32/legacy` | `66458b842400000000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/r12-disp32-r16-ext/legacy` | `664589842400000000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-38`, `X86-P48` |
| `x86:mov/r16-ext-base-index-disp8/legacy` | `66448b440000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P49` |
| `x86:mov/base-index-disp8-r16-ext/legacy` | `664489440000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P49` |
| `x86:mov/r16-ext-base-index-disp32/legacy` | `66448b840000000000` | dest: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P49` |
| `x86:mov/base-index-disp32-r16-ext/legacy` | `664489840000000000` | src: `x86.gpr16`/`r16` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P49` |
| `x86:mov/r16-base-index-disp8/legacy` | `668b440000` | dest: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P50` |
| `x86:mov/base-index-disp8-r16/legacy` | `6689440000` | src: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P50` |
| `x86:mov/r16-base-index-disp32/legacy` | `668b840000000000` | dest: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P50` |
| `x86:mov/base-index-disp32-r16/legacy` | `6689840000000000` | src: `x86.gpr16`/`r16` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P50` |
| `x86:mov/r16-base-ext-index-disp8/legacy` | `66418b440000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/base-ext-index-disp8-r16/legacy` | `664189440000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/r16-base-ext-index-disp32/legacy` | `66418b840000000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/base-ext-index-disp32-r16/legacy` | `664189840000000000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/r16-base-index-ext-disp8/legacy` | `66428b440000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/base-index-ext-disp8-r16/legacy` | `664289440000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/r16-base-index-ext-disp32/legacy` | `66428b840000000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/base-index-ext-disp32-r16/legacy` | `664289840000000000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[32,3]`; index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P51` |
| `x86:mov/r16-base-ext-index-ext-disp8/legacy` | `66438b440000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P52` |
| `x86:mov/base-ext-index-ext-disp8-r16/legacy` | `664389440000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P52` |
| `x86:mov/r16-base-ext-index-ext-disp32/legacy` | `66438b840000000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P52` |
| `x86:mov/base-ext-index-ext-disp32-r16/legacy` | `664389840000000000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr64`/`rm64` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P52` |
| `x86:mov/r32-base-index-disp8/legacy` | `8b440000` | dest: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-27`, `EC-37`, `EC-38`, `X86-P53` |
| `x86:mov/base-index-disp8-r32/legacy` | `89440000` | src: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp8` → `[24,8]` | 4 | `EC-02`, `EC-27`, `EC-37`, `EC-38`, `X86-P53` |
| `x86:mov/r32-base-index-disp32/legacy` | `8b840000000000` | dest: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-27`, `EC-37`, `EC-38`, `X86-P53` |
| `x86:mov/base-index-disp32-r32/legacy` | `89840000000000` | src: `x86.gpr32`/`r32` → `[11,3]`; base: `x86.gpr64`/`rm64` → `[16,3]`; index: `x86.gpr64`/`sib_index` → `[19,3]` (excl 4); imm: `x86.scale`/`scale2` → `[22,2]`; disp: `x86.imm`/`disp32` → `[24,32]` | 7 | `EC-02`, `EC-27`, `EC-37`, `EC-38`, `X86-P53` |
| `x86:mov/r32-ext-base-index-disp8/legacy` | `448b440000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/base-index-disp8-r32-ext/legacy` | `4489440000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/r32-ext-base-index-disp32/legacy` | `448b840000000000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/base-index-disp32-r32-ext/legacy` | `4489840000000000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/r32-base-ext-index-disp8/legacy` | `418b440000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/base-ext-index-disp8-r32/legacy` | `4189440000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/r32-base-ext-index-disp32/legacy` | `418b840000000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/base-ext-index-disp32-r32/legacy` | `4189840000000000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/r32-base-index-ext-disp8/legacy` | `428b440000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/base-index-ext-disp8-r32/legacy` | `4289440000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/r32-base-index-ext-disp32/legacy` | `428b840000000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/base-index-ext-disp32-r32/legacy` | `4289840000000000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[24,3]`; index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P54` |
| `x86:mov/r32-base-ext-index-ext-disp8/legacy` | `438b440000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P55` |
| `x86:mov/base-ext-index-ext-disp8-r32/legacy` | `4389440000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P55` |
| `x86:mov/r32-base-ext-index-ext-disp32/legacy` | `438b840000000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P55` |
| `x86:mov/base-ext-index-ext-disp32-r32/legacy` | `4389840000000000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P55` |
| `x86:mov/r32-ext-base-ext-index-ext-disp8/legacy` | `478b440000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P56` |
| `x86:mov/base-ext-index-ext-disp8-r32-ext/legacy` | `4789440000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P56` |
| `x86:mov/r32-ext-base-ext-index-ext-disp32/legacy` | `478b840000000000` | dest: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P56` |
| `x86:mov/base-ext-index-ext-disp32-r32-ext/legacy` | `4789840000000000` | src: `x86.gpr32`/`r32` → `[2,1]`, `[19,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr64`/`rm64` → `[0,1]`, `[24,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr64`/`sib_index` → `[1,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-27`, `EC-37`, `EC-38`, `X86-P56` |
| `x86:mov/r32-addr32-base-index-disp8/legacy` | `678b440000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr32`/`rm32` → `[24,3]`; index: `x86.gpr32`/`sib_index32` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P57` |
| `x86:mov/addr32-base-index-disp8-r32/legacy` | `6789440000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr32`/`rm32` → `[24,3]`; index: `x86.gpr32`/`sib_index32` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp8` → `[32,8]` | 5 | `EC-02`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P57` |
| `x86:mov/r32-addr32-base-index-disp32/legacy` | `678b840000000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr32`/`rm32` → `[24,3]`; index: `x86.gpr32`/`sib_index32` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P57` |
| `x86:mov/addr32-base-index-disp32-r32/legacy` | `6789840000000000` | src: `x86.gpr32`/`r32` → `[19,3]`; base: `x86.gpr32`/`rm32` → `[24,3]`; index: `x86.gpr32`/`sib_index32` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P57` |
| `x86:mov/r32-ext-addr32-base-index-disp8/legacy` | `67448b440000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/addr32-base-index-disp8-r32-ext/legacy` | `674489440000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/r32-ext-addr32-base-index-disp32/legacy` | `67448b840000000000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/addr32-base-index-disp32-r32-ext/legacy` | `674489840000000000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/r32-addr32-base-ext-index-disp8/legacy` | `67418b440000` | dest: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/addr32-base-ext-index-disp8-r32/legacy` | `674189440000` | src: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/r32-addr32-base-ext-index-disp32/legacy` | `67418b840000000000` | dest: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/addr32-base-ext-index-disp32-r32/legacy` | `674189840000000000` | src: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/r32-addr32-base-index-ext-disp8/legacy` | `67428b440000` | dest: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/addr32-base-index-ext-disp8-r32/legacy` | `674289440000` | src: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/r32-addr32-base-index-ext-disp32/legacy` | `67428b840000000000` | dest: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/addr32-base-index-ext-disp32-r32/legacy` | `674289840000000000` | src: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P58` |
| `x86:mov/r32-addr32-base-ext-index-ext-disp8/legacy` | `67438b440000` | dest: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-ext-index-ext-disp8-r32/legacy` | `674389440000` | src: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r32-addr32-base-ext-index-ext-disp32/legacy` | `67438b840000000000` | dest: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-ext-index-ext-disp32-r32/legacy` | `674389840000000000` | src: `x86.gpr32`/`r32` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r32-ext-addr32-base-ext-index-disp8/legacy` | `67458b440000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-ext-index-disp8-r32-ext/legacy` | `674589440000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r32-ext-addr32-base-ext-index-disp32/legacy` | `67458b840000000000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-ext-index-disp32-r32-ext/legacy` | `674589840000000000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r32-ext-addr32-base-index-ext-disp8/legacy` | `67468b440000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-index-ext-disp8-r32-ext/legacy` | `674689440000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r32-ext-addr32-base-index-ext-disp32/legacy` | `67468b840000000000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-index-ext-disp32-r32-ext/legacy` | `674689840000000000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r32-ext-addr32-base-ext-index-ext-disp8/legacy` | `67478b440000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-ext-index-ext-disp8-r32-ext/legacy` | `674789440000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r32-ext-addr32-base-ext-index-ext-disp32/legacy` | `67478b840000000000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/addr32-base-ext-index-ext-disp32-r32-ext/legacy` | `674789840000000000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P59` |
| `x86:mov/r64-addr32-base-index-disp8/legacy` | `67488b440000` | dest: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P60` |
| `x86:mov/addr32-base-index-disp8-r64/legacy` | `674889440000` | src: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P60` |
| `x86:mov/r64-addr32-base-index-disp32/legacy` | `67488b840000000000` | dest: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P60` |
| `x86:mov/addr32-base-index-disp32-r64/legacy` | `674889840000000000` | src: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; base: `x86.gpr32`/`rm32` → `[8,1]`, `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P60` |
| `x86:mov/r16-addr32-base-index-disp8/legacy` | `67668b440000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P61` |
| `x86:mov/addr32-base-index-disp8-r16/legacy` | `676689440000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp8` → `[40,8]` | 6 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P61` |
| `x86:mov/r16-addr32-base-index-disp32/legacy` | `67668b840000000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P61` |
| `x86:mov/addr32-base-index-disp32-r16/legacy` | `676689840000000000` | src: `x86.gpr16`/`r16` → `[27,3]`; base: `x86.gpr32`/`rm32` → `[32,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P61` |
| `x86:mov/r16-ext-addr32-base-index-disp8/legacy` | `6766448b440000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/addr32-base-index-disp8-r16-ext/legacy` | `67664489440000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/r16-ext-addr32-base-index-disp32/legacy` | `6766448b840000000000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/addr32-base-index-disp32-r16-ext/legacy` | `67664489840000000000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/r16-addr32-base-ext-index-disp8/legacy` | `6766418b440000` | dest: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/addr32-base-ext-index-disp8-r16/legacy` | `67664189440000` | src: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/r16-addr32-base-ext-index-disp32/legacy` | `6766418b840000000000` | dest: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/addr32-base-ext-index-disp32-r16/legacy` | `67664189840000000000` | src: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/r16-addr32-base-index-ext-disp8/legacy` | `6766428b440000` | dest: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/addr32-base-index-ext-disp8-r16/legacy` | `67664289440000` | src: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/r16-addr32-base-index-ext-disp32/legacy` | `6766428b840000000000` | dest: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/addr32-base-index-ext-disp32-r16/legacy` | `67664289840000000000` | src: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P62` |
| `x86:mov/r16-ext-addr32-base-ext-index-disp8/legacy` | `6766458b440000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-ext-addr32-base-ext-index-disp32/legacy` | `6766458b840000000000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-ext-index-disp8-r16-ext/legacy` | `67664589440000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-ext-index-disp32-r16-ext/legacy` | `67664589840000000000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-ext-addr32-base-index-ext-disp8/legacy` | `6766468b440000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-ext-addr32-base-index-ext-disp32/legacy` | `6766468b840000000000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-index-ext-disp8-r16-ext/legacy` | `67664689440000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-index-ext-disp32-r16-ext/legacy` | `67664689840000000000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[40,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-addr32-base-ext-index-ext-disp8/legacy` | `6766438b440000` | dest: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-addr32-base-ext-index-ext-disp32/legacy` | `6766438b840000000000` | dest: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-ext-index-ext-disp8-r16/legacy` | `67664389440000` | src: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-ext-index-ext-disp32-r16/legacy` | `67664389840000000000` | src: `x86.gpr16`/`r16` → `[35,3]`; base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-ext-addr32-base-ext-index-ext-disp8/legacy` | `6766478b440000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-ext-addr32-base-ext-index-ext-disp32/legacy` | `6766478b840000000000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-ext-index-ext-disp8-r16-ext/legacy` | `67664789440000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp8` → `[48,8]` | 7 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/addr32-base-ext-index-ext-disp32-r16-ext/legacy` | `67664789840000000000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); base: `x86.gpr32`/`rm32` → `[16,1]`, `[40,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-27`, `EC-36`, `EC-37`, `EC-38`, `X86-P63` |
| `x86:mov/r16-addr32-index-disp32/legacy` | `67668b040500000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/addr32-index-disp32-r16/legacy` | `676689040500000000` | src: `x86.gpr16`/`r16` → `[27,3]`; index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/r16-ext-addr32-index-disp32/legacy` | `6766448b040500000000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/addr32-index-disp32-r16-ext/legacy` | `67664489040500000000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[43,3]` (excl 4); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/r16-addr32-index-ext-disp32/legacy` | `6766428b040500000000` | dest: `x86.gpr16`/`r16` → `[35,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/addr32-index-ext-disp32-r16/legacy` | `67664289040500000000` | src: `x86.gpr16`/`r16` → `[35,3]`; index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/r16-ext-addr32-index-ext-disp32/legacy` | `6766468b040500000000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/addr32-index-ext-disp32-r16-ext/legacy` | `67664689040500000000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[17,1]`, `[43,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[46,2]`; disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-08`, `EC-27`, `EC-37`, `EC-38`, `X86-P64` |
| `x86:mov/r32-addr32-index-disp32/legacy` | `678b040500000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; index: `x86.gpr32`/`sib_index32` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/addr32-index-disp32-r32/legacy` | `6789040500000000` | src: `x86.gpr32`/`r32` → `[19,3]`; index: `x86.gpr32`/`sib_index32` → `[27,3]` (excl 4); imm: `x86.scale`/`scale2` → `[30,2]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/r32-ext-addr32-index-disp32/legacy` | `67448b040500000000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/addr32-index-disp32-r32-ext/legacy` | `674489040500000000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/r32-addr32-index-ext-disp32/legacy` | `67428b040500000000` | dest: `x86.gpr32`/`r32` → `[27,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/addr32-index-ext-disp32-r32/legacy` | `674289040500000000` | src: `x86.gpr32`/`r32` → `[27,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/r32-ext-addr32-index-ext-disp32/legacy` | `67468b040500000000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/addr32-index-ext-disp32-r32-ext/legacy` | `674689040500000000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P65` |
| `x86:mov/r64-addr32-index-disp32/legacy` | `67488b040500000000` | dest: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P66` |
| `x86:mov/addr32-index-disp32-r64/legacy` | `674889040500000000` | src: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; index: `x86.gpr32`/`sib_index32` → `[9,1]`, `[35,3]` (excl 4); imm: `x86.scale`/`scale2` → `[38,2]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P66` |
| `x86:mov/r32-addr32-abs32/legacy` | `678b042500000000` | dest: `x86.gpr32`/`r32` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P67` |
| `x86:mov/addr32-abs32-r32/legacy` | `6789042500000000` | src: `x86.gpr32`/`r32` → `[19,3]`; disp: `x86.imm`/`disp32` → `[32,32]` | 8 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P67` |
| `x86:mov/r32-ext-addr32-abs32/legacy` | `67448b042500000000` | dest: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P67` |
| `x86:mov/addr32-abs32-r32-ext/legacy` | `674489042500000000` | src: `x86.gpr32`/`r32` → `[10,1]`, `[27,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P67` |
| `x86:mov/r64-addr32-abs32/legacy` | `67488b042500000000` | dest: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P68` |
| `x86:mov/addr32-abs32-r64/legacy` | `674889042500000000` | src: `x86.gpr64`/`r64` → `[10,1]`, `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P68` |
| `x86:mov/r16-addr32-abs32/legacy` | `67668b042500000000` | dest: `x86.gpr16`/`r16` → `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P69` |
| `x86:mov/addr32-abs32-r16/legacy` | `676689042500000000` | src: `x86.gpr16`/`r16` → `[27,3]`; disp: `x86.imm`/`disp32` → `[40,32]` | 9 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P69` |
| `x86:mov/r16-ext-addr32-abs32/legacy` | `6766448b042500000000` | dest: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P69` |
| `x86:mov/addr32-abs32-r16-ext/legacy` | `67664489042500000000` | src: `x86.gpr16`/`r16` → `[18,1]`, `[35,3]` (excl 0, 1, 2, 3, 4, 5, 6, 7); disp: `x86.imm`/`disp32` → `[48,32]` | 10 | `EC-02`, `EC-06`, `EC-07`, `EC-08`, `EC-37`, `EC-38`, `X86-P69` |
| `x86:sub/rm64-imm8/legacy` | `4883e800` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm8` → `[24,8]` | 4 | `EC-01`, `EC-06` — 4-bit dest from `0.6.0`, `0.66.0`+ |
| `x86:sub/rm64-imm32/legacy` | `4881e800000000` | dest: `x86.gpr64`/`rm64` → `[0,1]`, `[16,3]`; imm: `x86.imm`/`imm32` → `[24,32]` | 7 | `EC-01`, `EC-04`, `EC-06` — 4-bit dest from `0.6.0`, `0.66.0`+ |
| `x86:sub/rax-imm32/legacy` | `482d00000000` | imm: `x86.imm`/`imm32` → `[16,32]` | 6 | `EC-04`, `0.66.0`+ |
| `x86:call/rel32/legacy` | `e800000000` | target: `x86.rel`/`rel32` → `[8,32]` | 5 | `EC-03`, `X86-P73` — `0.67.0`+ |
| `x86:movaps/xmm-riprel32/legacy` | `0f280500000000` | dest: `x86.xmm`/`xmm` → `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `ADR-0105`, `X86-P75` — `0.69.0`+ |
| `x86:movaps/riprel32-xmm/legacy` | `0f290500000000` | src: `x86.xmm`/`xmm` → `[19,3]`; target: `x86.rel`/`riprel32` → `[24,32]` | 7 | `ADR-0105`, `X86-P75` — `0.69.0`+ |
| `x86:vmovaps/xmm-riprel32/vex` | `c5f8280500000000` | dest: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; target: `x86.rel`/`riprel32` → `[32,32]` | 8 | `ADR-0105`, `X86-P75` — `0.69.0`+ |
| `x86:vmovaps/riprel32-xmm/vex` | `c5f8290500000000` | src: `x86.xmm`/`xmm` → `[15,1]` inverted, `[27,3]`; target: `x86.rel`/`riprel32` → `[32,32]` | 8 | `ADR-0105`, `X86-P75` — `0.69.0`+ |
| `x86:vmovaps/xmm-riprel32/evex` | `62f17c08280500000000` | dest: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; target: `x86.rel`/`riprel32` → `[48,32]` | 10 | `ADR-0105`, `X86-P75` — `0.69.0`+ |
| `x86:vmovaps/riprel32-xmm/evex` | `62f17c08290500000000` | src: `x86.xmm`/`xmm` → `[12,1]` inverted, `[15,1]` inverted, `[43,3]`; target: `x86.rel`/`riprel32` → `[48,32]` | 10 | `ADR-0105`, `X86-P75` — `0.69.0`+ |

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
Still deferred on this axis: the other EVEX SSE memory mnemonics, EVEX masking,
and the `0x67` prefix.

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
this axis: the other EVEX SSE memory mnemonics, EVEX masking, and the `0x67`
prefix.

`0.25.0` takes the last `SIB` combination (`ADR-0052`). Six rows put a 32-bit
absolute address where the base and index used to be: `ModRM` stays `04`, the
`SIB` byte is the constant `25` (scale `00`, index `100`, base `101`), and the
template is `62 f1 7c <L'L> <28|29> 04 25 00 00 00 00`, eleven bytes in every
row. The vector slot is the only field besides the address, which sits at
`[56,32]`: `0x1234` is `62 f1 7c 08 28 04 25 34 12 00 00` and
`-2147483648, %xmm21` is `62 e1 7c 08 29 2c 25 00 00 00 80`. The operand
sequence is `dest`/`src`, `disp`: an `index` operand is `E-OPERAND-002`
(`N02af`), the address carried as `disp8` is `E-OPERAND-001` (`N02ag`),
`disp32` content `2147483648` is `E-RANGE-001` (`N03l`), and naming a row
against `0.24.0` is `E-FORM-001` (`N01bb`/`N01bc`). Still deferred on this
axis: a symbol in the address, the other EVEX SSE memory mnemonics, EVEX
masking, the `0x67` prefix, and the same shape under the 8/16-bit `mov`
opcodes.

`0.26.0` carries the absolute address into the 64-bit GPR `mov` family
(`ADR-0053`). Two rows repeat the EVEX byte pattern one opcode family over:
`ModRM` is `04`, the `SIB` byte is the constant `25`, and the template is
`48 <8B|89> 04 25 00 00 00 00`, eight bytes in both rows. `REX.W` is template
bit 3, and the register is four bits written raw — `[19,3]` plus `REX.R` at
`[2,1]`, no invariant — so the address sits at `[32,32]`:
`movq 0x1234, %rax` is `48 8b 04 25 34 12 00 00`, `movq %r15, 0x1234` is
`4c 89 3c 25 34 12 00 00`, and `-2147483648, %rdi` is
`48 8b 3c 25 00 00 00 80`. The operand sequence is `dest`/`src`, `disp`: a
supplied `base` is `E-OPERAND-002` (`N02ah`), the address carried as `disp8`
is `E-OPERAND-001` (`N02ai`), `disp32` content `2147483648` is `E-RANGE-001`
(`N03m`), register `16` is `E-OPERAND-004` (`N14z`), and naming a row against
`0.25.0` is `E-FORM-001` (`N01bd`/`N01be`). `moffs` (`A0`–`A3`) is the second
legal encoding of the same source instruction and has no row: naming
`x86:mov/r64-moffs64/legacy` is `E-FORM-001` (`N01bf`), because the plan names
the eight-byte `abs32` form and never hands the ten-byte choice to the
materializer (`EC-05`). Still deferred on this axis: the 16- and 8-bit absolute
rows (`66 8b`, the three `movb` register sets), the `0x67` prefix, a symbol in
the address, and `moffs` for any other width.

`0.27.0` takes the same absolute address into the 32-bit rows, which need a row
per register window (`ADR-0054`). `movl 0x1234, %eax` is
`8b 04 25 34 12 00 00` — seven bytes, no `REX` byte, `ModRM` at `[8,8]`, `SIB`
at `[16,8]` and the address at `[24,32]`, with the register in the three-bit
`ModRM.reg` at `[11,3]`. `movl 0x1234, %r8d` is `44 8b 04 25 34 12 00 00` —
eight bytes, `REX = 44` (`REX.R = 1`, `REX.W = 0`), the same `04`/`25` bytes one
byte later and the address at `[32,32]`; its register slot is `[19,3]` plus
`REX.R` at `[2,1]` with `0`–`7` excluded, so `%eax` on that row is
`E-RANGE-004` (`N16ad`) and `%r16d` is `E-OPERAND-004` (`N14aa`). The operand
sequence is `dest`/`src`, `disp`: a supplied `base` is `E-OPERAND-002`
(`N02aj`), the address carried as `disp8` is `E-OPERAND-001` (`N02ak`), a
`gpr64`/`r64` operand on an `r32` row is `E-OPERAND-001` on both `kind` and
`target_type` (`N02al`), `disp32` content `2147483648` is `E-RANGE-001`
(`N03n`), and naming either row against `0.26.0` is `E-FORM-001`
(`N01bg`/`N01bh`). Still deferred on this axis: the 16- and 8-bit absolute
rows (`66 8b`, the three `movb` register sets), the `0x67` prefix, a symbol in
the address, `moffs` for the other widths, and the APX `d5` register window.

`0.28.0` moves the same address down to 16-bit width, where the `66` prefix
comes first (`ADR-0055`). `movw 0x1234, %ax` is `66 8b 04 25 34 12 00 00` —
eight bytes, no `REX` byte, with `66` at `[0,8]`, the opcode at `[8,8]`,
`ModRM` at `[16,8]`, `SIB` at `[24,8]` and the address at `[32,32]`, and the
register in the three-bit `ModRM.reg` at `[19,3]`. `movw 0x1234, %r8w` is
`66 44 8b 04 25 34 12 00 00` — nine bytes, `REX = 44` at `[8,8]`, the same
`04`/`25` bytes one byte later and the address at `[40,32]`; its register slot
is `[27,3]` plus `REX.R` at `[10,1]` with `0`–`7` excluded. The address stays a
signed 32-bit field: `-32768` is `00 80 ff ff`, and `0x80000000` leaves the
row for `movabsw` (`66 a1`, ten bytes, `EC-05`). A supplied `base` is
`E-OPERAND-002` (`N02am`), the address carried as `disp8` is `E-OPERAND-001`
(`N02an`), a `gpr32`/`r32` operand on an `r16` row is `E-OPERAND-001` on both
axes (`N02ao`), `disp32` content `2147483648` is `E-RANGE-001` (`N03o`),
register `16` is `E-OPERAND-004` (`N14ab`), register `0` on the `-ext` row is
`E-RANGE-004` (`N16ae`), and naming either row against `0.27.0` is
`E-FORM-001` (`N01bi`/`N01bj`).

`0.29.0` closes the width axis at eight bits, where one three-bit field names two
register sets (`ADR-0056`). `movb 0x1234, %al` is `8a 04 25 34 12 00 00` and
`movb 0x1234, %ah` is `8a 24 25 34 12 00 00` — seven bytes each, no `REX` byte,
with the opcode at `[0,8]`, `ModRM` at `[8,8]`, `SIB = 25` at `[16,8]` and the
address at `[24,32]`, and the register in the three-bit `ModRM.reg` at
`[11,3]`; the low window excludes `4`–`7` and the high window excludes `0`–`3`.
`movb 0x1234, %spl` is `40 8a 24 25 34 12 00 00` — eight bytes, `REX = 40`, the
same `24`/`25` bytes one byte later, the register at `[19,3]` and the address at
`[32,32]`; the `REX` byte is what relabels `4`–`7` to `%spl`–`%dil`, so the slot
excludes `0`–`3`. `movb 0x1234, %r8b` is `44 8a 04 25 34 12 00 00` — eight
bytes with `REX.R = 1` at `[2,1]` plus `[19,3]` and `0`–`7` excluded. The address
stays signed 32-bit content: `-128` is `80 ff ff ff`, `-32768` is `00 80 ff ff`,
and `0x80000000` sends the low rows to `movabsb` (`a0`/`a2`, nine bytes,
`EC-05`) while `%r8b` stays on the short row with the same four bytes. A
supplied `base` is `E-OPERAND-002` (`N02ap`), the address carried as `disp8` is
`E-OPERAND-001` (`N02aq`), a `gpr16`/`r16` operand on an `r8` row is
`E-OPERAND-001` on both axes (`N02ar`), a `gpr8h`/`r8h` operand on the low row
is `E-OPERAND-001` twice plus `E-RANGE-004` (`N02as`), `disp32` content
`2147483648` is `E-RANGE-001` (`N03p`), register `16` is `E-OPERAND-004`
(`N14ac`), register `0` on the `REX = 40` row is `E-RANGE-004` (`N16af`), and
naming a row against `0.28.0` is `E-FORM-001` (`N01bk`/`N01bl`).

`0.30.0` carries the fourth byte window into the memory rows
(`ADR-0057`), where the register and the base can both need an extension
and one `REX` byte carries both bits. `movb 8(%rax), %r8b` is
`44 8a 40 08` — four bytes, `REX.R = 1` at `[2,1]`, the opcode at
`[8,8]`, `ModRM` at `[16,8]` with `mod = 01`, the register at `[19,3]`
and the base at `[16,3]`, then the displacement at `[24,8]` — and
`movb 8(%r8), %r8b` is `45 8a 40 08`: the same length with `REX.B = 1`
at `[0,1]`, so the plain-base slot is four bits and excludes `4` and
`12`. `%rsp` needs `SIB = 24` (`44 8a 44 24 08`, five bytes, the
displacement at `[32,8]`) and `%r12` is the same `SIB` byte with
`REX.B = 1` (`45 8a 44 24 08`); `%rbp` and `%r13` need no row of their
own because `mod = 01` is the family's floor (`44 8a 7d 08` is
`movb 8(%rbp), %r15b`). The high-byte kind cannot reach any of these
rows: `movb 8(%rax), %ah` is `8a 60 08` while `movb 8(%r8), %ah` is
rejected. A `gpr8h`/`r8h` operand is `E-OPERAND-001` on both axes
(`N02at`), `disp8` on a `disp32` row is `E-OPERAND-001` (`N02au`), a
`base` operand on a `SIB` row is `E-OPERAND-002` (`N02av`), `disp32`
content `2147483648` is `E-RANGE-001` (`N03q`), register `16` is
`E-OPERAND-004` (`N14ad`), register `0` on an extended row is
`E-RANGE-004` (`N16ag`), and `%rsp` or `%r12` as the base of a
plain-base row is `E-RANGE-004` (`N16ah`/`N16ai`).

`0.31.0` adds the third displacement shape to that family (`ADR-0058`),
one row per register window and direction: `movb (%rax), %al` is `8a 00`,
two bytes with the opcode at `[0,8]` and `ModRM` at `[8,8]`, and
`movb (%r8), %r15b` is `45 8a 3f`. The `REX`-less rows keep the three-bit
base at `[8,3]` and the three-bit register at `[11,3]`; the prefixed rows
move both one byte along (`[16,3]` and `[19,3]`) and add the same
`REX.R`/`REX.B` extension bits. The base slot excludes four values rather
than two, because at `mod = 00` the `r/m` value `101` is RIP-relative
`disp32`: `llvm-mc` writes `movb (%rbp), %al` as `8a 45 00` (`mod = 01`,
`disp8 = 0`), and `%rsp`/`%r12` still need the `SIB` byte (`8a 04 24`,
`41 8a 04 24`). There is no displacement slot, so a `disp` operand is
`E-OPERAND-002` (`N02ax`) rather than an implied zero; `%rbp`, `%r13`,
`%rsp` and `%r12` are `E-RANGE-004` (`N16aj`/`N16ak`/`N16al`/`N16am`),
base `8` on a three-bit row is `E-OPERAND-004` (`N14ae`), the high-byte
kind on a low-window row is `E-OPERAND-001` twice (`N02aw`), and naming a
row against `0.30.0` is `E-FORM-001` (`N01bo`/`N01bp`).

`0.32.0` takes the last two bases on that shape (`ADR-0059`), one row per
base and direction: `movb (%rsp), %al` is `8a 04 24` and
`movb (%r12), %al` is `41 8a 04 24` — the same three bytes after a `REX`
byte whose `B` bit is the only difference. `SIB = 24` sits at `[16,8]` on
the `REX`-less row and at `[24,8]` on the prefixed row, so the three-bit
register field moves from `[11,3]` to `[19,3]`. The high-byte window has
only the `%rsp` half, because `REX.B` renames `%ah` to `%spl` and
`movb (%r12), %ah` is rejected. The base and its `REX.B` bit are fixed in
the template, so a `base` operand is `E-OPERAND-002` (`N02ay`) and a `disp`
operand is `E-OPERAND-002` too (`N02az`); naming the absent `%r12`
high-byte row is `E-FORM-001` (`N01bs`), register `16` or `8` on the
three-bit row is `E-OPERAND-004` (`N14af`/`N14ag`), register `0` on the
`REX = 40` row is `E-RANGE-004` (`N16an`), and naming a row against
`0.31.0` is `E-FORM-001` (`N01bq`/`N01br`). Still deferred on this axis:
`REX.X` at byte width, the `0x67` prefix, a symbol in the displacement,
`moffs` for the byte width, and the APX `d5` register window.

`0.33.0` gives the 64-bit family the same third shape (`ADR-0060`):
`movq (%rax), %rax` is `48 8b 00` and `movq %rax, (%rax)` is `48 89 00`,
three bytes with `REX.W` in the template and both register fields four
bits wide (`REX.R` at `[2,1]` plus `[19,3]`, `REX.B` at `[0,1]` plus
`[16,3]`), so one row covers every register and every base. The base
slot excludes four values: `%rbp`/`%r13` because `r/m = 101` at
`mod = 00` is the RIP-relative `disp32` row, and `%rsp`/`%r12` because
they need the `SIB` byte. `llvm-mc` normalises an explicit zero
displacement on a plain base (`movq 0(%rax), %rax` assembles to
`48 8b 00`), so the plan names the row rather than the assembler picking
one. A `disp` operand is `E-OPERAND-002` (`N02ba`), register `16` is
`E-OPERAND-004` (`N14ah`), the four bases are `E-RANGE-004`
(`N16ao`–`N16ar`), and naming either row against `0.32.0` is
`E-FORM-001` (`N01bt`/`N01bu`).

`0.34.0` takes the two `SIB` bases onto that shape (`ADR-0061`):
`movq (%rsp), %rax` is `48 8b 04 24` and `movq (%r12), %rax` is
`49 8b 04 24`, four bytes with `ModRM = 04` and `SIB = 24`; the base and
its `REX.B` are template content, so only `REX.R` is a slot and one row
per base and direction covers all sixteen registers (`movq (%rsp), %r8`
is `4c 8b 04 24`). The base is not an operand: a `base` or `disp`
operand is `E-OPERAND-002` (`N02bb`/`N02bc`), register `16` is
`E-OPERAND-004` (`N14ai`), and naming a row against `0.33.0` is
`E-FORM-001` (`N01bv`/`N01bw`). Still deferred in this family: `REX.X`
with an index and scale, the `0x67` prefix, a symbol in the displacement,
`moffs`, the APX `d5` window, and the same shape at 16 bits.

`0.35.0` gives the 32-bit family its first base rows (`ADR-0062`):
`movl (%rax), %eax` is `8b 00` and `movl %eax, (%rax)` is `89 00`, two
bytes with `mod = 00` and no displacement, but the legacy row has no
`REX` byte, so a high register or a high base changes the length. The
reach is three disjoint rows per direction: the low row keeps the 3-bit
`ModRM` fields, `movl (%rax), %r8d` is `44 8b 00` (`REX.R`), and
`movl (%r8), %eax` is `41 8b 00` (`REX.B`), so `movl (%r9), %r15d` is
`45 8b 39` and a `(register, base)` pair names exactly one row. The base
excludes `%rsp`/`%r12` (they need the `SIB` byte) and `%rbp`/`%r13`
(`r/m = 101` at `mod = 00` is RIP-relative). A `disp` operand is
`E-OPERAND-002` (`N02bd`), the 3-bit and 4-bit ends are `E-OPERAND-004`
(`N14ak`/`N14aj`), the excluded bases and windows are `E-RANGE-004`
(`N16as`/`N16at`/`N16au`/`N16av`), and naming a row against `0.34.0` is
`E-FORM-001` (`N01bx`/`N01by`). Still deferred in this family: the
`%rsp`/`%r12` `SIB` bases, the `disp8`/`disp32` base shapes, the `0x67`
prefix, a symbol in an address, and the APX `d5` window.

`0.36.0` takes the two `SIB` bases onto that family (`ADR-0063`):
`movl (%rsp), %eax` is `8b 04 24`, three bytes with `ModRM = 04` and
`SIB = 24` (`scale = 00`, `index = 100` none, `base = 100`).
`%r12` differs only in a fixed `REX.B` byte (`41 8b 04 24`), so each
base, direction and register window is a row: `%rsp` costs three bytes
in the low window and four in the `REX.R` window (`44 8b 04 24`,
`44 8b 3c 24`), while every `%r12` row is four (`41`/`45`). The base is
not an operand -- a `base` or `disp` operand is `E-OPERAND-002`
(`N02be`/`N02bf`) -- and the register window stays the form, so
register `8` on a low row is `E-OPERAND-004` (`N14am`) and register `0`
on an `-ext` row is `E-RANGE-004` (`N16aw`). Naming a row against
`0.35.0` is `E-FORM-001` (`N01bz`/`N01ca`). Still deferred in this
family: the `disp8`/`disp32` `SIB` shapes, an index or scale, the `0x67`
prefix, a symbol in an address, and the APX `d5` window.

`0.37.0` gives that family the plain-base `disp8` shape (`ADR-0064`):
`movl 8(%rax), %eax` is `8b 40 08`, three bytes with `mod = 01`, the
base in `ModRM.r/m` and the signed displacement at `[16,8]`. The reach
is again three rows per direction: `movl 8(%rax), %r8d` is
`44 8b 40 08` (`REX.R`), `movl 8(%r8), %eax` is `41 8b 40 08`
(`REX.B`), and both bits share one byte (`45 8b 79 08`). At `mod = 01`
`%rbp`/`%r13` are ordinary bases (`8b 45 08`), so only `%rsp`/`%r12`
stay excluded (`N16ax`/`N16ay`); the `REX.B` row also excludes `0`-`7`,
because a low base would clear the fixed `REX.B` bit and emit a
different instruction (`N16ba`). The displacement is a slot: a missing
one is `E-OPERAND-002` (`N02bg`), `128` is `E-RANGE-001` (`N03r`),
register `16` is `E-OPERAND-004` (`N14an`), and an `-ext` row's low
register is `E-RANGE-004` (`N16az`). Naming a row against `0.36.0` is
`E-FORM-001` (`N01cb`/`N01cc`). Still deferred in this family: the
`%rsp`/`%r12` `SIB` `disp8` rows, the `disp32` base rows, an index or
scale, the `0x67` prefix, a symbol in a displacement, and the APX `d5`
window.

`0.38.0` completes the displacement axis for that family (`ADR-0065`):
`movl 200(%rax), %eax` is `8b 80 c8 00 00 00`, six bytes with
`mod = 10`, the base in `ModRM.r/m` and the signed 32-bit displacement
at `[16,32]`; the range ends are `8b 80 ff ff ff 7f` and
`8b 80 00 00 00 80`. The reach is again three rows per direction, seven
bytes each (`44 8b 80 …`, `41 8b 80 …`, `45 8b b9 …`), with the
displacement at `[24,32]` behind a `REX` byte. `%rbp`/`%r13` are
ordinary bases here (`8b 85 …`), so only `%rsp`/`%r12` stay excluded
(`N16bb`/`N16bc`), and the `REX.B` row again keeps the low bases out
(`N16be`). A missing displacement is `E-OPERAND-002` (`N02bh`),
`2147483648` is `E-RANGE-001` (`N03s`), register `16` is
`E-OPERAND-004` (`N14ap`), and an `-ext` row's low register is
`E-RANGE-004` (`N16bd`). Naming a row against `0.37.0` is
`E-FORM-001` (`N01cd`/`N01ce`). Still deferred in this family: the
`%rsp`/`%r12` `SIB` `disp8`/`disp32` rows, an index or scale, the
`0x67` prefix, a symbol in a displacement, and the APX `d5` window.

`0.39.0` combines the `SIB` bases with the `disp8` shape (`ADR-0066`):
`movl 8(%rsp), %eax` is `8b 44 24 08`, four bytes with `mod = 01` and
`SIB = 24`, and `movl 8(%r12), %eax` is `41 8b 44 24 08`, the same
three bytes behind `REX.B`. The base is fixed in the form (the two bases
share the low three bits `100`), so each base, direction and register
window is a row; the legacy row again splits the register window, giving
`44 8b 44 24 08` (`REX.R`), `41 8b 44 24 08` (`REX.B`) and
`45 8b 44 24 08` (both), with the displacement at `[24,8]` and `[32,8]`.
The range is the signed byte (`8b 44 24 80`…`8b 44 24 7f`). A missing
displacement is `E-OPERAND-002` (`N02bi`), `128` is `E-RANGE-001`
(`N03t`), register `16` is `E-OPERAND-004` (`N14ar`), and an `-ext` row's
low register is `E-RANGE-004` (`N16bf`). Naming a row against `0.38.0` is
`E-FORM-001` (`N01cf`/`N01cg`). Still deferred in this family: the
`%rsp`/`%r12` `SIB` `disp32` rows, an index or scale, the `0x67` prefix,
a symbol in a displacement, and the APX `d5` window.

`0.40.0` completes the displacement axis for the `SIB` bases (`ADR-0067`):
`movl 200(%rsp), %eax` is `8b 84 24 c8 00 00 00`, seven bytes with
`mod = 10`, `SIB = 24` and the signed 32-bit displacement at `[24,32]`;
the range ends are `8b 84 24 ff ff ff 7f` and `8b 84 24 00 00 00 80`.
`movl 200(%r12), %eax` is `41 8b 84 24 c8 00 00 00`, the same three bytes
behind `REX.B`, and the register window still splits
(`44 8b 84 24 c8 00 00 00`, `41 8b 84 24 c8 00 00 00`,
`45 8b 84 24 c8 00 00 00`), with the displacement at `[32,32]`. A missing
displacement is `E-OPERAND-002` (`N02bj`), `2147483648` is `E-RANGE-001`
(`N03u`), register `16` is `E-OPERAND-004` (`N14at`), and an `-ext` row's
low register is `E-RANGE-004` (`N16bg`). Naming a row against `0.39.0` is
`E-FORM-001` (`N01ch`/`N01ci`). Still deferred in this family: an index or
scale, the `0x67` prefix, a symbol in a displacement, and the APX `d5`
window.

`0.41.0` gives the 16-bit `mov` family its `mod = 00` rows (`ADR-0068`):
`movw (%rax), %ax` is `66 8b 00`, three bytes with no displacement, and
`movw %ax, (%rax)` is `66 89 00`. A `REX.B` base still costs a byte
(`66 41 8b 00`, `66 41 8b 07`), and the field layout shifts with it: the
register is `[19,3]` and the plain base `[16,3]` in the unprefixed rows, but
`[27,3]` and `[24,3]` once `REX` is present. At `mod = 00` `r/m = 101` is
`rip`-relative, so `%rbp`/`%r13` cannot be plain bases (`movw (%rbp), %ax` is
`66 8b 45 00`, a `mod = 01` row), and `%rsp`/`%r12` need the fixed `SIB`
rows: `66 8b 04 24` and `66 41 8b 04 24`, the same `SIB = 24` with `REX.B`
as the only difference. A supplied displacement is `E-OPERAND-002`
(`N02bk`), `%rsp`/`%r12` on a plain row and a low base on the `-ext` row are
`E-RANGE-004` (`N16bh`–`N16bj`), and `%rbp`/`%r13` are `E-RANGE-004`
(`N16bk`/`N16bl`). Naming a row against `0.40.0` is `E-FORM-001`
(`N01cj`/`N01ck`). Still deferred in this family: the `REX.R` 16-bit register
window, an index or scale, the `0x67` prefix, a symbol in a displacement, and
the APX `d5` window.

`0.42.0` takes that register window (`ADR-0069`): `movw (%rax), %r8w` is
`66 44 8b 00`, four bytes with `REX = 44` (`R = 1`), so the register's fourth
bit sits at `[10,1]` and its low three bits at `[27,3]`. Both extension bits
share one byte, so `movw (%r8), %r8w` is `66 45 8b 00` and the length does not
grow. The `SIB` bases compose unchanged: `66 44 8b 04 24` (`%rsp`) and
`66 45 8b 04 24` (`%r12`), with `REX.B` still the only difference between the
two rows. The low register window is excluded from the `-ext` rows, because a
value `0`–`7` would clear the fixed `REX.R` bit (`E-RANGE-004`, `N16bm`), and
`16` is past the four-bit field (`E-OPERAND-004`, `N14av`). A supplied
displacement is `E-OPERAND-002` (`N02bl`), `%rsp` on the low-base row and
`%rbp` on the `-ext`-base row are `E-RANGE-004` (`N16bn`/`N16bo`), and naming
a row against `0.41.0` is `E-FORM-001` (`N01cl`/`N01cm`). Still deferred:
the `disp8`/`disp32` shapes with the same register window, an index or scale,
the `0x67` prefix, a symbol in a displacement, and the APX `d5` window.

`0.43.0` takes the `disp8` shape (`ADR-0070`): `movw 8(%rax), %r8w` is
`66 44 8b 40 08`, five bytes, with the register still at `[10,1]`/`[27,3]`
and the displacement byte at `[32,8]`. Both extension bits still share one
byte, so `movw 8(%r8), %r8w` is `66 45 8b 40 08`. The `SIB` rows add the
`SIB` byte, putting the displacement at `[40,8]`: `66 44 8b 44 24 08`
(`%rsp`) and `66 45 8b 44 24 08` (`%r12`). At `mod = 01` the base window is
looser than at `mod = 00`: `r/m = 101` is `%rbp`/`%r13` with a displacement,
so the plain low-base row excludes `%rsp` only (`[4]`) and the `-ext`-base
row excludes `0`–`7` and `%r12` (`E-RANGE-004`, `N16br`/`N16bq`). A missing
`disp` is `E-OPERAND-002` (`N02bm`), `128` is `E-RANGE-001` (`N03v`), a low
register on an `-ext` row is `E-RANGE-004` (`N16bp`), `16` is
`E-OPERAND-004` (`N14aw`), and naming a row against `0.42.0` is
`E-FORM-001` (`N01cn`/`N01co`). Still deferred: the `disp32` shape with the
same register window, an index or scale, the `0x67` prefix, a symbol in a
displacement, and the APX `d5` window.

`0.44.0` takes the `disp32` shape (`ADR-0071`): `movw 200(%rax), %r8w` is
`66 44 8b 80 c8 00 00 00`, eight bytes, with the register at
`[10,1]`/`[27,3]` and the four displacement bytes at `[32,32]`. Both
extension bits still share one byte, so `movw 200(%r8), %r8w` is
`66 45 8b 80 c8 00 00 00`. The `SIB` rows add the `SIB` byte, putting the
displacement at `[40,32]`: `66 44 8b 84 24 c8 00 00 00` (`%rsp`) and
`66 45 8b 84 24 c8 00 00 00` (`%r12`). At `mod = 10` the base window matches
`mod = 01`: `%rbp`/`%r13` are legal bases (`66 44 8b 85 c8 00 00 00`), so the
plain low-base row excludes `%rsp` only (`[4]`) and the `-ext`-base row
excludes `0`–`7` and `%r12`. A missing `disp` is `E-OPERAND-002` (`N02bn`),
`2147483648` is `E-RANGE-001` (`N03w`), a low register on an `-ext` row is
`E-RANGE-004` (`N16bs`), `16` is `E-OPERAND-004` (`N14ax`), `%rsp` on the
plain row and `%rbp` on the `-ext` row are `E-RANGE-004`
(`N16bt`/`N16bu`), and naming a row against `0.43.0` is `E-FORM-001`
(`N01cp`/`N01cq`). Still deferred: an index or scale, the `0x67` prefix, a
symbol in a displacement, the same shape at 8 and 64 bits where a window is
still missing, and the APX `d5` window.

`0.45.0` puts the `SIB` index and scale on those rows (`ADR-0072`): `movw
8(%rax,%rcx,1), %r8w` is `66 44 8b 44 08 08`, six bytes, with `REX = 44`
(`R = 1`), `SIB = 08` (scale `0`, index `1`, base `0`) and the displacement at
`[40,8]`; `movw 8(%r15,%r13,8), %r15w` is `66 47 8b 7c ef 08`, where `REX =
47` carries `R`, `X` and `B` in one byte and the row stays six bytes. The base
is one four-bit slot (`REX.B` plus `SIB.base`, all sixteen values, with
`%rsp`/`%r12` legal because the `SIB` byte is present), and the index is one
four-bit slot (`REX.X` plus `SIB.index`, `4` excluded because `SIB.index =
100` with `REX.X = 0` means "no index"; `%r12` stays legal through `REX.X =
1`). The scale is two bits of field content (`0…3` for ×1/×2/×4/×8; `4` is
`E-RANGE-001`), never a multiplier. The `disp32` rows put four bytes at
`[40,32]`: `66 44 8b 84 08 c8 00 00 00`. A missing index is
`E-OPERAND-002` (`N02bo`), scale `4` is `E-RANGE-001` (`N03x`), a low
register on an `-ext` row is `E-RANGE-004` (`N16bw`), `16` is
`E-OPERAND-004` (`N14ay`/`N14az`), index `4` is `E-RANGE-004` (`N16bv`), and
naming a row against `0.44.0` is `E-FORM-001` (`N01cr`/`N01cs`). Still
deferred: the low-register indexed rows (they need a `REX`-less prefix
variant), the `0x67` prefix, a symbol in a displacement, and the APX `d5`
window.

`0.46.0` takes the `REX` byte out of that shape (`ADR-0073`): `movw
8(%rax,%rcx,1), %ax` is `66 8b 44 08 08`, five bytes, with `ModRM = 44` at
byte 2, `SIB = 08` at byte 3 (scale `0`, index `1`, base `0`) and the
displacement at `[32,8]`. Every field moves one byte earlier with the missing
prefix, and the row is one byte shorter. The register, base and index fields
are three bits each (`[19,3]`, `[24,3]`, `[27,3]`), so `movw 8(%rdi,%rsi,4),
%di` is `66 8b 7c b7 08` and register `8` / base `8` are `E-OPERAND-004`
(`N14bb`/`N14bc`): there is no `REX.R`/`REX.B` to carry a fourth bit, and
reaching `%r8`–`%r15` is the `0.45.0` form. `%rsp`/`%rbp` stay legal bases
because `r/m = 100` announces the `SIB` byte (`66 8b 44 0c 08` / `66 8b 44 0d
08`, `SIB.base = 100`/`101`). The index is three bits with `4` excluded, since
`SIB.index = 100` with no `REX.X` means "no index" (`E-RANGE-004`, `N16bx`);
`%r12` is not reachable from this row at all. The scale is again two bits of
field content (`4` is `E-RANGE-001`, `N03y`). The `disp32` rows put four bytes
at `[32,32]`: `66 8b 84 08 c8 00 00 00`. A missing index is `E-OPERAND-002`
(`N02bp`), `16` is `E-OPERAND-004` (`N14ba`), and naming a row against
`0.45.0` is `E-FORM-001` (`N01ct`/`N01cu`). Still deferred: the
`REX.B`/`REX.X`/`REX.BX` windows on the same indexed rows (they need a
`REX` byte), the `0x67` prefix, a symbol in a displacement, the no-base
indexed shape, and the APX `d5` window.

`0.47.0` keeps the register in the low window and gives the base or the index
its fourth bit (`ADR-0074`): `movw 8(%r8,%rcx,1), %ax` is `66 41 8b 44 08 08`,
six bytes, with `REX = 41` (`B = 1`), `ModRM = 44`, `SIB = 08` and the
displacement at `[40,8]`; `movw 8(%rax,%r9,1), %ax` is `66 42 8b 44 08 08`
(`REX.X`). The register is still three bits at `[27,3]`, so register `8`–`15`
is `E-OPERAND-004` (`N14bd`) and is the `0.45.0` form. The extended operand's
slot lists the `REX` bit as its most significant placement (`[8,1]` or
`[9,1]`) and excludes the low window, so base `3` on a `-base-ext` row
(`N16bz`) and index `3` on an `-index-ext` row (`N16by`) are `E-RANGE-004`;
the other operand stays three bits, so base `8` on an `-index-ext` row is
`E-OPERAND-004` (`N14be`). `%r12`/`%rsp`/`%rbp`/`%r13` are legal bases
(`66 41 8b 44 0c 08`, `66 42 8b 44 0c 08`, `66 42 8b 44 0d 08`), and `%r12`
is legal as an index through `REX.X` (`66 42 8b 44 20 08`). The `disp32` rows
put four bytes at `[40,32]` (`66 41 8b 84 08 c8 00 00 00`). Still deferred:
the `REX.BX` window (`66 43 8b 44 08 08`), the `0x67` prefix, a symbol in a
displacement, the no-base indexed shape, and the APX `d5` window.

`0.48.0` closes that family with both extension bits at once (`ADR-0075`):
`movw 8(%r8,%r9,1), %ax` is `66 43 8b 44 08 08`, six bytes, with `REX = 43`
(`X = 1`, `B = 1`), `ModRM = 44`, `SIB = 08` and the displacement at `[40,8]`.
The register is still `[27,3]`, so register `8`–`15` is `E-OPERAND-004`
(`N14bf`); the base and the index are four-bit slots (`[8,1]`, `[32,3]` and
`[9,1]`, `[35,3]`) that exclude `0`–`7`, so a low value is `E-RANGE-004`
(`N16ca`/`N16cb`). Both operands reach `%r12` here:
`movw 8(%r12,%r12,1), %ax` is `66 43 8b 44 24 08` and the store direction is
`66 43 89 44 24 08`; `movw 8(%r15,%r15,8), %di` is `66 43 8b 7c ff 08`. `%rbp`
is a legal index (`66 41 8b 44 2d 08` for `8(%r13,%rbp,1), %ax`), and `%rsp`
is still not (`E-RANGE-004` on the index slot). The `disp32` rows put four
bytes at `[40,32]` (`66 43 8b 84 08 c8 00 00 00`). A missing index is
`E-OPERAND-002` (`N02br`), scale `4` is `E-RANGE-001` (`N03za`), and naming a
row against `0.47.0` is `E-FORM-001` (`N01cx`/`N01cy`). Still deferred: the
`0x67` address-size prefix, a symbol in a displacement, the no-base indexed
shape, and the APX `d5` window.

`0.49.0` carries the same index/scale shape to the 32-bit family, where there
is no prefix byte at all (`ADR-0076`): `movl 8(%rax,%rcx,1), %eax` is
`8b 44 08 08`, four bytes, with `ModRM = 44` at byte 1, `SIB = 08` at byte 2
and the displacement at `[24,8]`. Every field sits one byte earlier than the
64-bit rows and the register, base and index are three bits
(`[11,3]`/`[16,3]`/`[19,3]`), so `movl 8(%rdi,%rsi,4), %edi` is
`8b 7c b7 08` and register `8`/base `8` are `E-OPERAND-004`
(`N14bg`/`N14bh`): `movl 8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08`, the
`REX.R` form. `%rsp`/`%rbp` stay legal bases (`8b 44 0c 08` / `8b 44 35 08`),
and `%r12` as a base is `41 8b 44 0c 08`, the `REX.B` form rather than
`%rsp`. The index is three bits with `4` excluded (`E-RANGE-004`, `N16cc`).
The `disp32` rows put four bytes at `[24,32]`: `8b 84 08 c8 00 00 00`. A
missing index is `E-OPERAND-002` (`N02bs`), scale `4` is `E-RANGE-001`
(`N03zb`), and naming a row against `0.48.0` is `E-FORM-001`
(`N01cz`/`N01da`). Still deferred: the 32-bit `REX` windows on these rows, the
`0x67` prefix, a symbol in a displacement, the no-base indexed shape, and the
APX `d5` window.

`0.50.0` adds the single `REX` windows to the same 32-bit indexed rows
(`ADR-0077`). Each row fixes one extension bit in a prefix byte at 0, so
`ModRM` moves to byte 2 and every field sits one byte later:
`movl 8(%rax,%rcx,1), %r8d` is `44 8b 44 08 08` (`REX.R`, five bytes),
`movl 8(%r8,%rcx,1), %eax` is `41 8b 44 08 08` (`REX.B`) and
`movl 8(%rax,%r9,1), %eax` is `42 8b 44 08 08` (`REX.X`). The register is
`[19,3]`, the base `[24,3]`, the index `[27,3]`, the scale `[30,2]` and the
displacement `[32,8]`; the extended operand's slot excludes `0`–`7` because
those values belong to the `REX`-less `0.49.0` row (`E-RANGE-004`,
`N16cd`/`N16ce`/`N16cf`). `%r12` is legal in both memory windows
(`41 8b 44 0c 08` as a base, `42 89 44 20 08` as an index), `%rsp` is a legal
base on the `REX.R` row (`44 8b 44 0c 08`), and `%rsp` as an index stays
rejected. The `disp32` rows put four bytes at `[32,32]`
(`44 8b 84 08 c8 00 00 00`). A missing index is `E-OPERAND-002` (`N02bt`),
scale `4` is `E-RANGE-001` (`N03zc`), register `8`/base `8` on the `REX`-less
row are `E-OPERAND-004` (`N14bi`/`N14bj`), and naming a row against `0.49.0` is
`E-FORM-001` (`N01db`/`N01dc`). Still deferred: the `REX.BX` window on these
rows (`43 8b 44 08 08`), the `0x67` prefix, a symbol in a displacement, the
no-base indexed shape, and the APX `d5` window.

`0.51.0` takes that last window (`ADR-0078`): both memory operands are extended
at once, so one prefix byte carries `REX.B` and `REX.X` together.
`movl 8(%r8,%r9,1), %eax` is `43 8b 44 08 08` (`REX = 43`, five bytes) and
`200(%r8,%r9,1), %eax` is `43 8b 84 08 c8 00 00 00` (eight). `ModRM` stays at
byte 2, so the register is `[19,3]`, the base `[0,1]`+`[24,3]`, the index
`[1,1]`+`[27,3]`, the scale `[30,2]` and the displacement `[32,8]`/`[32,32]`.
Both memory slots exclude `0`–`7`, so a low base or index is `E-RANGE-004`
(`N16cg`/`N16ch`), while the register stays three bits and `8` is
`E-OPERAND-004` (`N14bk`). `%r12` is legal as a base and as an index
(`43 8b 44 24 08`), and `%r15`/`%r15` at x8 is `43 8b 7c ff 08`; `%rsp` as an
index stays rejected. A missing index is `E-OPERAND-002` (`N02bu`), scale `4`
is `E-RANGE-001` (`N03zd`), and naming a row against `0.50.0` is `E-FORM-001`
(`N01dd`/`N01de`). Still deferred: the `0x67` prefix, a symbol in a
displacement, the no-base indexed shape, the APX `d5` window, and EVEX
masking/broadcast on these rows.

`0.52.0` completes the split (`ADR-0079`): all three registers carry an
extension bit, so one `REX` byte holds `R`, `X` and `B` together.
`movl 8(%r8,%r9,1), %r8d` is `47 8b 44 08 08` (`REX = 47`, five bytes) and
`movl 200(%r8,%r9,1), %r8d` is `47 8b 84 08 c8 00 00 00` (eight). `ModRM` is
still byte 2 and the geometry is unchanged, except that the register now
occupies four bits (`[2,1]`+`[19,3]`) and excludes `0`–`7` like the base and
index, so a low value on any of the three is `E-RANGE-004`
(`N16ci`/`N16cj`/`N16ck`). `%r12` is legal on all three operands
(`8(%r12,%r12,1), %r8d` is `47 8b 44 24 08`, `%r12d, 8(%r12,%r12,1)` is
`47 89 64 24 08`), `%r15`/`%r15` with `%r15d` at x8 is `47 8b 7c ff 08`, and
`%rsp` as an index stays rejected. A missing index is `E-OPERAND-002`
(`N02bv`), scale `4` is `E-RANGE-001` (`N03ze`), and naming a row against
`0.51.0` is `E-FORM-001` (`N01df`/`N01dg`). Still deferred: the `0x67`+`REX`
windows, a symbol in a displacement, the no-base indexed shape, the APX `d5`
window, and EVEX masking/broadcast on these rows.

`0.53.0` puts the address-size prefix in front of that shape (`ADR-0080`):
`0x67` is template byte 0 and the opcode moves to byte 1, so `ModRM` is byte 2
and `SIB` byte 3 exactly as in the `0.51.0` geometry. `movl 8(%eax,%ecx,1),
%eax` is `67 8b 44 08 08` (five bytes) and `movl 200(%eax,%ecx,1), %eax` is
`67 8b 84 08 c8 00 00 00` (eight). The register is still `x86.gpr32`/`r32` at
`[19,3]`, but the base and index are 32-bit address registers: `x86.gpr32`/
`rm32` at `[24,3]` and `x86.gpr32`/`sib_index32` at `[27,3]` (index `4`
excluded), with the scale at `[30,2]` and the displacement at
`[32,8]`/`[32,32]`. `%esp` is a legal base (`67 8b 44 0c 08`) and `%ebp` is a
legal index (`67 8b 44 28 08`), while `%esp` as an index is rejected. All three
address slots are three bits, so `8`–`15` is `E-OPERAND-004`; the `0x67`+`REX`
windows are the deferred forms (`67 47 8b 44 08 08`, `67 44 8b 44 08 08`). A
missing index is `E-OPERAND-002` (`N02bw`), scale `4` is `E-RANGE-001`
(`N03zf`), index `4` is `E-RANGE-004` (`N16cl`), and naming a row against
`0.52.0` is `E-FORM-001` (`N01dh`/`N01di`).

`0.54.0` puts one `REX` byte after the `0x67` byte (`ADR-0081`):
`movl 8(%eax,%ecx,1), %r8d` is `67 44 8b 44 08 08` (six bytes) and
`movl 200(%eax,%ecx,1), %r8d` is `67 44 8b 84 08 c8 00 00 00` (nine). `0x67`
stays byte 0 and `REX` byte 1, so the opcode is byte 2, `ModRM` byte 3 and
`SIB` byte 4: register `[27,3]` (with `REX.R` at `[10,1]`), base `[32,3]` (with
`REX.B` at `[8,1]`), index `[35,3]` (with `REX.X` at `[9,1]`), scale `[38,2]`
and displacement `[40,8]`/`[40,32]`. Each extended slot excludes `0`–`7`, so a
low value on it is `E-RANGE-004` (`N16cm`/`N16cn`/`N16co`), while the operands a
row keeps low stay three bits (`E-OPERAND-004`, `N14bn`/`N14bo`). `%r12d` is
legal as a base (`67 41 8b 44 0c 08`) and as an index (`67 42 8b 44 20 08`),
`%esp` as an index stays rejected, and `%ebp` is a legal base on the `REX.R` row
(`67 44 8b 44 0d 08`). A missing index is `E-OPERAND-002` (`N02by`), scale `4`
is `E-RANGE-001` (`N03zg`), and naming a row against `0.53.0` is `E-FORM-001`
(`N01dj`/`N01dk`). Still deferred: the two-bit `addr32` windows (`67 43`,
`67 45`, `67 46`, `67 47`), a symbol in a displacement, the no-base indexed
shape, the `moffs` form, the APX `d5` window and EVEX masking/broadcast.

`0.55.0` adds the four two-bit windows (`ADR-0082`):
`movl 8(%r8d,%r9d,1), %eax` is `67 43 8b 44 08 08` (`REX.BX`, six bytes),
`movl 8(%r8d,%ecx,1), %r8d` is `67 45 8b 44 08 08` (`REX.RB`),
`movl 8(%eax,%r9d,1), %r8d` is `67 46 8b 44 08 08` (`REX.RX`) and
`movl 8(%r8d,%r9d,1), %r8d` is `67 47 8b 44 08 08` (`REX.RBX`); the `disp32`
siblings are nine bytes. The geometry is unchanged: `0x67` byte 0, `REX`
byte 1, opcode byte 2, `ModRM` byte 3, `SIB` byte 4, with the register
`[27,3]`, base `[32,3]`, index `[35,3]`, scale `[38,2]` and displacement
`[40,8]`/`[40,32]`. Each fixed bit sits at `[10,1]` (`R`), `[8,1]` (`B`) or
`[9,1]` (`X`) and its slot excludes `0`–`7` (`E-RANGE-004`,
`N16cp`/`N16cq`/`N16cr`), while the third operand stays three bits
(`E-OPERAND-004`, `N14bp`/`N14bq`). `%r12d` on all three operands is
`67 47 8b 64 24 08`, `%r13d` is `67 47 8b 6c 2d 08`, the x8 scale with `%r15d`
is `67 47 8b 7c c8 08`, and `%esp` as an index stays rejected. A missing index
is `E-OPERAND-002` (`N02bz`), scale `4` is `E-RANGE-001` (`N03zh`), and naming
a row against `0.54.0` is `E-FORM-001` (`N01dl`/`N01dm`). Still deferred: a
symbol in a displacement, the no-base indexed shape, the `moffs` form, the APX
`d5` window and EVEX masking/broadcast.

`0.56.0` adds the `0x67` `REX.W` `movq` shape as one wide row per direction and
displacement width (`ADR-0083`): `movq 8(%eax,%ecx,1), %rax` is
`67 48 8b 44 08 08` (six bytes) and `movq 200(%eax,%ecx,1), %rax` is
`67 48 8b 84 08 c8 00 00 00` (nine). `REX.W` is template content while `R`, `X`
and `B` come from the operands, so `67 48` widens to `67 4f`
(`movq 8(%r8d,%r9d,1), %r8`, `REX.RBX`), `67 49` (`REX.B`), `67 4a` (`REX.X`)
or `67 4c` (`REX.R`) without a new row. The geometry is unchanged (`0x67` byte
0, `REX` byte 1, opcode byte 2, `ModRM` byte 3, `SIB` byte 4; value
`[10,1]`+`[27,3]`, base `[8,1]`+`[32,3]`, index `[9,1]`+`[35,3]`, scale
`[38,2]`, displacement `[40,8]`/`[40,32]`). The value is `x86.gpr64`/`r64`,
while the base and index stay 32-bit address registers (`x86.gpr32`/`rm32` and
`x86.gpr32`/`sib_index32` with index `4` excluded): `%r12`/`%r13` on all three
operands are `67 4f 8b 64 24 08`/`67 4f 8b 6c 2d 08`, `%ebp` is a legal base,
and a 64-bit base is `E-OPERAND-001` (`N02cb`). A missing index is
`E-OPERAND-002` (`N02ca`), scale `4` is `E-RANGE-001` (`N03zi`), index `4` is
`E-RANGE-004` (`N16cs`), and a five-bit register is `E-OPERAND-004`
(`N14br`/`N14bs`); naming a row against `0.55.0` is `E-FORM-001`
(`N01dn`/`N01do`). Still deferred: a symbol in a displacement, the no-base
indexed shape, the `moffs` form, the APX `d5` window, EVEX masking/broadcast, a
16-bit address width with `0x67`, and a 64-bit address register with `0x67`.

`0.57.0` adds the `0x67 66` 16-bit value pair as one bare window per direction
and displacement width (`ADR-0084`): `0x67` stays byte 0 and `0x66` takes
byte 1, so `movw 8(%eax,%ecx,1), %ax` is `67 66 8b 44 08 08` (six bytes) and
`movw 200(%eax,%ecx,1), %ax` is `67 66 8b 84 08 c8 00 00 00` (nine). The
opcode is byte 2, `ModRM = 44` byte 3 and `SIB = 08` byte 4, with the value at
`[27,3]`, the base at `[32,3]`, the index at `[35,3]`, the scale at `[38,2]`
and the displacement at `[40,8]`/`[40,32]`. Because the bare pair has no `REX`
byte, the value is `x86.gpr16`/`r16` and the base and index are
`x86.gpr32`/`rm32` and `x86.gpr32`/`sib_index32` (index `4` excluded), each
three bits. `%ebp` is a legal base and index (`67 66 8b 44 0d 08`/
`67 66 8b 44 28 08`), `%esp` is a base but not an index, the x8 scale is
`67 66 8b 44 c8 08`, and a `%dx` value is `67 66 8b 54 08 08`. A value or base
above `7` is `E-OPERAND-004` (`N14bt`/`N14bu`), index `4` is `E-RANGE-004`
(`N16ct`), scale `4` is `E-RANGE-001` (`N03zj`), a missing index is
`E-OPERAND-002` (`N02cc`), a 64-bit base is `E-OPERAND-001` (`N02cd`), and
naming a row against `0.56.0` is `E-FORM-001` (`N01dp`/`N01dq`). Still
deferred: a symbol in a displacement, the no-base indexed shape, the `moffs`
form, the APX `d5` window, EVEX masking/broadcast and a 64-bit address register
with `0x67`.

`0.58.0` adds the three single-`REX` windows on the `0x67 66` pair
(`ADR-0085`). The `REX` byte sits at position 2, so `0x67` stays byte 0,
`0x66` byte 1, the opcode moves to byte 3, `ModRM` to byte 4 and `SIB` to
byte 5: `movw 8(%eax,%ecx,1), %r8w` is `67 66 44 8b 44 08 08` (seven bytes)
and `movw 200(%eax,%ecx,1), %r8w` is `67 66 44 8b 84 08 c8 00 00 00` (ten).
The value is `[35,3]`, the base `[40,3]`, the index `[43,3]`, the scale
`[46,2]` and the displacement `[48,8]`/`[48,32]`. One fixed bit opens one
window: `R` at `[18,1]` widens the value (`%r8w`–`%r15w`, `67 66 44 …`), `B`
at `[16,1]` the base (`67 66 41 8b 44 08 08`) and `X` at `[17,1]` the index
(`67 66 42 8b 44 08 08`); the widened slot excludes `0`–`7` (`E-RANGE-004`,
`N16cu`/`N16cv`/`N16cw`). The address registers stay 32-bit. A value past its
four-bit field is `E-OPERAND-004` (`N14bv`), scale `4` is `E-RANGE-001`
(`N03zk`), a missing index is `E-OPERAND-002` (`N02ce`), and naming a row
against `0.57.0` is `E-FORM-001` (`N01dr`/`N01ds`). `%r15w` with `%ebp` is
`67 66 44 8b 7c 0d 08`, `%r15d` as a base is `67 66 41 8b 54 2f 08`, `%r15d`
as an index is `67 66 42 8b 54 38 08`, and the x8 scale is
`67 66 44 8b 7c c8 08`.

`0.59.0` adds the four two-`REX`-bit windows on that pair (`ADR-0086`). The
`REX` byte keeps position 2, so the geometry is unchanged: value `[35,3]`,
base `[40,3]`, index `[43,3]`, scale `[46,2]` and displacement
`[48,8]`/`[48,32]`. `movw 8(%r8d,%ecx,1), %r8w` is `67 66 45 8b 44 08 08`
(`REX.RB`) and `movw 200(%r8d,%ecx,1), %r8w` is
`67 66 45 8b 84 08 c8 00 00 00` (ten). `RX` is `67 66 46 8b 44 08 08`, `BX`
`67 66 43 8b 44 08 08` and `RBX` `67 66 47 8b 44 08 08`; each extended slot
carries its fixed bit plus its three-bit field and excludes `0`–`7`
(`E-RANGE-004`, `N16cx`/`N16cy`/`N16cz`). The address registers stay 32-bit,
so index `4` with `REX.X = 1` names `%r12d` (`67 66 47 8b 64 24 08`). A value
past its four-bit field is `E-OPERAND-004` (`N14bw`), scale `4` is
`E-RANGE-001` (`N03zl`), a missing index is `E-OPERAND-002` (`N02cf`), and
naming a row against `0.58.0` is `E-FORM-001` (`N01dt`/`N01du`). `%r12d` with
`%r15w` is `67 66 45 8b 7c 0c 08`, `%r12d`/`%r15d` is
`67 66 43 8b 54 3c 08`, `%r12d`/`%r13d` is `67 66 47 8b 7c 2c 08`, and the
x8 scale is `67 66 47 8b 44 c8 08`. Still deferred: the `REX.W` siblings
(`67 66 48`–`67 66 4f`), a symbol in a displacement, the no-base indexed
shape, the `moffs` form, the APX `d5` window, EVEX masking/broadcast and a
64-bit address register with `0x67`.

`0.60.0` adds the no-base indexed shape on that pair (`ADR-0087`).
`SIB.base = 101` at `mod = 00` frees the base slot and forces a `disp32`, so
`movw 8(,%ecx,1), %ax` is `67 66 8b 04 0d 08 00 00 00` (nine): `0x67` at
byte 0, `0x66` at byte 1, the opcode at byte 2, `ModRM = 04` at byte 3,
`SIB = 0d` at byte 4 and the displacement at `[40,32]`. The row has no `base`
role and there is no `REX.B` bit; `R` at `[18,1]` and `X` at `[17,1]` insert
the `REX` byte at position 2 and move every later field eight bits, so
`movw 8(,%ecx,1), %r8w` is `67 66 44 8b 04 0d 08 00 00 00` with the value at
`[35,3]`, the index at `[43,3]`, the scale at `[46,2]` and the displacement
at `[48,32]`. The displacement is four bytes at every value, including zero
(`67 66 8b 04 0d 00 00 00 00`). `SIB.base = 101` carries the no-base meaning,
so index `4` with `REX.X = 1` names `%r12d`
(`67 66 42 8b 04 25 08 00 00 00`) while the bare row still rejects `4`
(`E-RANGE-004`, `N16da`) and the `RX` row rejects `0` (`N16db`). A missing
index and a supplied base are both `E-OPERAND-002` (`N02cg`/`N02ch`), scale
`4` is `E-RANGE-001` (`N03zm`), a value past its four-bit field is
`E-OPERAND-004` (`N14bx`), and naming a row against `0.59.0` is
`E-FORM-001` (`N01dv`/`N01dw`). `4660(,%r15d,8), %r15w` is
`67 66 46 8b 3c fd 34 12 00 00`. Still deferred: the `REX.W` siblings (`67 66
48`–`67 66 4f`, which no assembler emits), a symbol in a displacement, the
absolute `SIB = 25` shape with `0x67`, the `moffs` form, the APX `d5` window,
EVEX masking/broadcast and a 64-bit address register with `0x67`.

`0.61.0` adds the 32-bit value width of that shape (`ADR-0088`), where the
absent `0x66` removes one geometry: `movl 8(,%ecx,1), %eax` is
`67 8b 04 0d 08 00 00 00` (eight) with the opcode at byte 1, `ModRM = 04`
at byte 2, `SIB = 0d` at byte 3, the value at `[19,3]`, the index at
`[27,3]`, the scale at `[30,2]` and the displacement at `[32,32]`. `R` at
`[10,1]` and `X` at `[9,1]` insert the `REX` byte at position 1 and move
every later field eight bits, so `movl 8(,%r9d,1), %r8d` is
`67 46 8b 04 0d 08 00 00 00` (nine). Index `4` under `REX.X` names `%r12d`
(`67 42 8b 04 25 08 00 00 00`), the bare row rejects `4` (`E-RANGE-004`,
`N16dc`) and the `RX` row rejects `0` (`N16dd`); a missing index and a
supplied base are `E-OPERAND-002` (`N02ci`/`N02cj`), scale `4` is
`E-RANGE-001` (`N03zn`), a value past its four-bit field is `E-OPERAND-004`
(`N14by`), and naming a row against `0.60.0` is `E-FORM-001`
(`N01dx`/`N01dy`). `4660(,%r15d,8), %r15d` is `67 46 8b 3c fd 34 12 00 00`.
Still deferred: the `REX.W` `movq` shape (`67 48`/`67 4c`/`67 4a`/`67 4e`),
a symbol in a displacement, the absolute `SIB = 25` shape with `0x67`, the
`moffs` form, the APX `d5` window, EVEX masking/broadcast and a 64-bit
address register with `0x67`.

`0.62.0` adds the 64-bit value width of that shape (`ADR-0089`), where
`REX.W` is mandatory and therefore changes the row decomposition:
`movq 8(,%ecx,1), %rax` is `67 48 8b 04 0d 08 00 00 00` (nine), with
`0x67` at byte 0, `REX` at byte 1, the opcode at byte 2, `ModRM = 04` at
byte 3, `SIB = 0d` at byte 4 and the displacement at `[40,32]`. Because the
`REX` byte always exists, `R` at `[10,1]` and `X` at `[9,1]` are free bits
of one row rather than separate windows: `0x48` is the low pair, `0x4c`
(`%r8` value), `0x4a` (`%r9d` index) and `0x4e` (both) are the same form, so
one row per direction covers all sixteen value registers and indexes. Index
`4` with `REX.X = 0` is still the "no index" constant, so `%r12d` is legal
through `REX.X = 1` (`67 4a 8b 04 25 08 00 00 00`) and index `4` is
`E-RANGE-004` (`N16de`); a missing index and a supplied base are both
`E-OPERAND-002` (`N02ck`/`N02cl`), scale `4` is `E-RANGE-001` (`N03zo`), a
value or index past its four-bit field is `E-OPERAND-004`
(`N14bz`/`N14ca`), and naming a row against `0.61.0` is `E-FORM-001`
(`N01dz`/`N01ea`). `4660(,%r15d,8), %r15` is `67 4e 8b 3c fd 34 12 00 00`.
Still deferred: a symbol in a displacement, the absolute `SIB = 25` shape
with `0x67`, a 64-bit address register with `0x67`, the `moffs` form, the
APX `d5` window and EVEX masking/broadcast.

`0.63.0` takes the absolute `SIB = 25` shape behind `0x67` (`ADR-0090`):
`addr32 movl 4660, %eax` is `67 8b 04 25 34 12 00 00` (eight), with `0x67`
at byte 0, the opcode at byte 1, `ModRM = 04` at byte 2, `SIB = 25` at byte
3 and the displacement at `[32,32]`. The `SIB` byte is `scale = 00`,
`index = 100`, `base = 101`, so nothing in the address is operand-owned:
there is no `base`, `index` or `scale` slot and no `REX.B`/`REX.X` bit, and
a supplied base is `E-OPERAND-002` (`N02cm`). The `REX.R` rows put `REX` at
byte 1, the value at `[10,1]`+`[27,3]` and the displacement at `[40,32]`:
`addr32 movl 4660, %r8d` is `67 44 8b 04 25 34 12 00 00` (nine), while the
bare rows keep a three-bit value field at `[19,3]`, so `8` is
`E-OPERAND-004` there (`N14cc`) and `16` is `E-OPERAND-004` on the
extended row (`N14cb`). The displacement is four bytes at every value
(`67 8b 04 25 00 00 00 00`), its signed ends are
`67 8b 04 25 00 00 00 80` and `67 8b 04 25 ff ff ff 7f`, and `2147483648`
is `E-RANGE-001` (`N03zp`). `SIB = 25` never changes (`%r15d` is
`67 44 8b 3c 25 34 12 00 00`), value `0` on the `-ext` row is
`E-RANGE-004` (`N16df`), and naming a row against `0.62.0` is `E-FORM-001`
(`N01eb`/`N01ec`). Still deferred: the `REX.W` (`67 48`) and `0x67 66`
absolute siblings, `moffs` with `0x67`, the RIP-relative `67 8b 05` row, a
symbol in the displacement, APX `d5` and EVEX masking/broadcast.

`0.64.0` reaches the 64-bit width of the same shape (`ADR-0091`):
`addr32 movq 4660, %rax` is `67 48 8b 04 25 34 12 00 00` (nine), with
`0x67` at byte 0, `REX.W` at byte 1, the opcode at byte 2, `ModRM = 04` at
byte 3, `SIB = 25` at byte 4 and the displacement at `[40,32]`.
`REX.W` is mandatory, so there is no bare geometry and `R` (`[10,1]`)
plus `ModRM.reg` (`[27,3]`) covers all sixteen values:
`addr32 movq 4660, %r8` is `67 4c 8b 04 25 34 12 00 00`, one row per
direction. The value window has no exclusion, so `16` is
`E-OPERAND-004` (`N14cd`) and a 32-bit operand misses both the kind and
the target type (`N02cp`, two `E-OPERAND-001`). Supplying a base and
omitting the displacement are both `E-OPERAND-002` (`N02cn`/`N02co`), the
displacement is four bytes at every value
(`67 48 8b 04 25 00 00 00 00`) with signed ends
`67 48 8b 04 25 00 00 00 80` and `67 48 8b 04 25 ff ff ff 7f`, and
`2147483648` is `E-RANGE-001` (`N03zq`). `SIB = 25` never changes
(`%r15` is `67 4c 8b 3c 25 34 12 00 00`) and naming a row against
`0.63.0` is `E-FORM-001` (`N01ed`/`N01ee`). Still deferred: the
`0x67 66` absolute sibling, `moffs` with `0x67` (the measurement and a
manual derivation disagree about the offset width), the RIP-relative
`67 48 8b 05` row, a symbol in the displacement, APX `d5` and EVEX
masking/broadcast.

`0.65.0` adds the `0x67 66` absolute rows (`ADR-0092`):
`addr32 movw 4660, %ax` is `67 66 8b 04 25 34 12 00 00` (nine), with
`0x67` at byte 0, `0x66` at byte 1, the opcode at byte 2, `ModRM = 04` at
byte 3, `SIB = 25` at byte 4 and the displacement at `[40,32]`. The
`REX.R` rows put `REX` at byte 2, the value at `[18,1]`+`[35,3]`
(excluding `0`-`7`) and the displacement at `[48,32]`:
`addr32 movw 4660, %r8w` is `67 66 44 8b 04 25 34 12 00 00` (ten), while
the bare rows keep a three-bit value field at `[27,3]`, so `8` is
`E-OPERAND-004` there (`N14cf`) and `16` is `E-OPERAND-004` on the
extended row (`N14ce`). The displacement is four bytes at every value
(`67 66 8b 04 25 00 00 00 00`), its signed ends are
`67 66 8b 04 25 00 00 00 80` and `67 66 8b 04 25 ff ff ff 7f`, and
`2147483648` is `E-RANGE-001` (`N03zr`). `SIB = 25` never changes
(`%r15w` is `67 66 44 8b 3c 25 34 12 00 00`), a supplied base and a
missing displacement are both `E-OPERAND-002` (`N02cq`/`N02cr`), a 32-bit
operand misses both the kind and the target type (`N02cs`), value `0` on
the `-ext` row is `E-RANGE-004` (`N16dg`), and naming a row against
`0.64.0` is `E-FORM-001` (`N01ef`/`N01eg`). Still deferred: `moffs` with
`0x67 66` (the measurement and a manual derivation disagree about the
offset width), the `0x67 66` RIP-relative row, a symbol in the
displacement, APX `d5` and EVEX masking/broadcast.

`0.66.0` adds the three `sub` immediate rows (`ADR-0101`): `subq $1, %rax`
is `48 83 e8 01`, `subq $300, %rbx` is `48 81 eb 2c 01 00 00` and
`subq $300, %rax` is `48 2d 2c 01 00 00`. The only bytes that differ from
the `add` rows are `ModRM.reg` (`/5` instead of `/0`) and the accumulator
opcode (`2d` instead of `05`), so both are template content and no plan
field carries them. The destination slot keeps its four bits
(`REX.B` `[0,1]` + `ModRM.r/m` `[16,3]`): `subq $1, %r8` is
`49 83 e8 01`. `subq $300, %rax` also has the `48 81 e8 2c 01 00 00`
encoding, and `llvm-mc` picks the accumulator, which is `EC-04`'s
counterexample for `sub` too. `128` on the signed 8-bit immediate is
`E-RANGE-001` (`N03zs`), a `r32` destination on `rm64-imm32` misses both
the kind and the target type (`N02ct`), the register form (`29`/`2B`) is
absent (`N01ej`) and a `0.66.0` row against `0.65.0` is `E-FORM-001`
(`N01ek`). Still deferred: the register-register pair, the other widths, a
symbol in the immediate, APX `d5` and EVEX masking/broadcast.

`0.67.0` adds the direct `call rel32` row (`ADR-0102`): `callq L1` is
`e8 05 00 00 00` (the field is the displacement from the end of the
instruction, `pcrel_end`), `callq ext` is `e8 00 00 00 00` with one
`R_X86_64_PLT32 ext -4` record, and the same row takes a literal field
value (`call .+130` is `e8 7d 00 00 00`). `E8` is the only difference from
the `0.1.0` `jmp/rel32` row, so the row is `EC-03`'s rel32 half without a
rel8 sibling. `2147483648` on the signed displacement is `E-RANGE-002`
(`N04g`), a register operand misses both the kind and the target type
(`N02cu`), a missing target is `E-OPERAND-002` (`N02cv`), the indirect
`FF /2` family is absent (`N01el`) and a `0.67.0` row against `0.66.0` is
`E-FORM-001` (`N01em`). Still deferred: the indirect call, the 16/32-bit
operand sizes, APX `d5` and EVEX masking/broadcast.

`0.68.0` is the first `fmp-def/0.2` table (`ADR-0103`). It repeats the 513 forms
of `0.67.0` unchanged and adds `requires_extensions` to every form: the 388
`/legacy` rows `[]`, the 38 `/vex` rows `["avx"]`, the 29 `zmm` EVEX rows
`["avx","avx512f"]`, and the 58 `xmm`/`ymm` EVEX rows
`["avx","avx512f","avx512vl"]`. The split is the operand width, not the
mnemonic: `L'L` selects 128/256-bit EVEX (AVX-512VL) or 512-bit EVEX
(AVX-512F) (`EXP-0032` §1), and every gated row is a `vmovaps` row. A plan that
declares `["avx"]` may name a legacy or VEX row, but the first EVEX row it names
is `E-TARGET-003`; a plan that declares an extension outside the table's
three-name set is `E-TARGET-001`. `X86-P74` re-pins the 24 VEX instructions of
`X86-P20` to this table, `N06b` omits `avx` and `N06c` declares an extension the
table does not carry.

`0.69.0` adds six `%rip`-relative SSE rows (`ADR-0105`): the `movaps`/`vmovaps`
xmm load and store at the legacy, VEX and EVEX encodings. Each replaces the base
and `disp32` slots of the fixed-base row with the one `x86.rel`/`riprel32`
target slot that `x86:mov/r64-riprel32/legacy` already pins; the template is the
measured `16(%rip)` encoding with the displacement zeroed (`EXP-0106`). The
target placement is `[24,32]` for the legacy pair, `[32,32]` for the VEX pair
and `[48,32]` for the EVEX pair, because the displacement is the last 32 bits of
every one of these instructions. `X86-P75` resolves one local symbol at all
three placements through six `pcrel_end` fixups. The absent `ymm`/`zmm`
siblings are `E-FORM-001` (`N01eo`), a missing target operand is
`E-OPERAND-002` (`N02cx`), and a literal one past the signed 32-bit range is
`E-RANGE-002` (`N04i`).

`0.70.0` splits the legacy SSE fixed-base rows on the register's fourth bit
(`ADR-0106`). The four `%rsp`/`%r12` load/store rows hold only `xmm0`–`xmm7`
(`ModRM.reg` at `[19,3]`/`[27,3]`), so `movaps 8(%rsp), %xmm8` needs a `REX.R`
byte that the low row cannot carry: `44 0f 28 44 24 08` is six bytes where
`0f 28 44 24 08` is five, and emitting the longer byte from the operand value
would change the length with the register (`INV-04`). Eight `-ext` rows
therefore append the `xmm8`–`xmm15` window with `REX.R` at `[2,1]` and
`ModRM.reg` at `[27,3]`; `%r12` keeps the fixed `REX.B` byte (`45`), and the
displacement moves one byte to `[40,8]`/`[40,32]` behind the `REX` byte.
`X86-P76` is the 60-byte vector. The low rows keep their `xmm0`–`xmm7` window
(`N14w`), naming a `0.70.0` row against `0.69.0` is `E-FORM-001` (`N01ep`), a
missing `disp` is `E-OPERAND-002` (`N02cy`), and `disp8 = 128` is
`E-RANGE-001` (`N03zt`).

`0.71.0` puts the `0x67` prefix on the `%rip`-relative rows (`ADR-0107`). With
no base or index to rename, the prefix selects the 32-bit `%eip` reference, so
`addr32 movl 16(%rip), %eax` is `67 8b 05 10 00 00 00` and the displacement is
still the last 32 bits. The plan keeps `address_width: 64`: the prefix is a
form fact (`EC-08`), not a target-identity field. Six rows cover the three
value widths × load/store, with the target at `[24,32]` for `r32` and
`[32,32]` for `r64`/`r16`. `X86-P77` resolves one symbol at offset 62 through
six `pcrel_end` fixups. The `0.70.0` boundary is `E-FORM-001` (`N01eq`), a
missing target is `E-OPERAND-002` (`N02cz`), and a literal past the signed
32-bit range is `E-RANGE-002` (`N04j`).

`0.72.0` gives the legacy SSE and VEX families the general indexed shape
(`ADR-0108`). Sixteen rows cross {`movaps`, `vmovaps`} × {load, store} ×
{`disp8`, `disp32`} × {`xmm0`-`xmm7`, `xmm8`-`xmm15`}, with `%rax` as the low
base and `%rcx` as the low index in the measurement:
`movaps 8(%rax,%rcx,4), %xmm1` is `0f 28 4c 88 08` (5 B), `vmovaps` is
`c5 f8 28 44 88 08` (6 B), and the legacy high window pays the `44` `REX.R`
byte (`44 0f 28 44 88 08`). The base and index are the three-bit window, so
`REX.X`/`REX.B` stay at their template values; the high `xmm` window is a
separate row because `REX.R` (legacy) and `R̄` (VEX) are template bytes, not
inserted from an operand. Scale and index live in the `SIB` byte at `[30,2]`
and `[27,3]` (legacy low), moving with the prefix (`[38,2]`/`[35,3]` for the
`REX` and VEX rows). `X86-P78` is the 116-byte vector. The `0.71.0` boundary is
`E-FORM-001` (`N01er`), a missing base is `E-OPERAND-002` (`N02da`, `expected:
5`, `found: 4`) and `disp8 = 128` is `E-RANGE-001` (`N03zu`).

`0.73.0` gives the 8-bit `mov` the same indexed shape in its three
no-new-prefix windows (`ADR-0109`): `r8` (`%al`-`%dl`, no `REX`), `r8h`
(`%ah`-`%dh`, no `REX`) and `r8-rex` (`%spl`-`%dil`, a `40` prefix). Twelve
rows cross {load, store} × {`disp8`, `disp32`}: `movb 8(%rax,%rcx,4), %al` is
`8a 44 88 08` (4 B), `movb %ah, …` is `8a 64 88 08`, and `movb %spl, …` is
`40 8a 64 88 08` (5 B). The value slot is `[11,3]`/`[19,3]` with the window's
exclusion, the base `[16,3]`/`[24,3]`, the index `[19,3]`/`[27,3]`, the scale
`[22,2]`/`[30,2]`, and the displacement `[24,…]`/`[32,…]`. The high window
(`%r8b`-`%r15b`) needs `REX.R` and stays deferred. `X86-P79` is the 70-byte
vector. The `0.72.0` boundary is `E-FORM-001` (`N01es`), a missing base is
`E-OPERAND-002` (`N02db`, `expected: 5`, `found: 4`) and `disp8 = 128` is
`E-RANGE-001` (`N03zv`).

`0.74.0` adds the register/register `sub` row `29 /r` at three widths
(`ADR-0110`): `subq %rcx, %rax` is `48 29 c8` (3 B), `subl %ecx, %eax` is
`29 c8` (2 B) and `subw %cx, %ax` is `66 29 c8` (3 B). The destination is
`REX.B` + `ModRM.r/m` on the 64-bit row (just `ModRM.r/m` at 32/16 bits), the
source is `REX.R` + `ModRM.reg`, and both are three-bit, so `%r8`-`%r15`
stays deferred. The memory-destination direction `2B /r` stays absent.
`X86-P80` is the 16-byte vector. The `0.73.0` boundary is `E-FORM-001`
(`N01et`), the absent `2B` direction is `E-FORM-001` (`N01ej`), a missing
source is `E-OPERAND-002` (`N02dc`, `expected: 2`, `found: 1`) and `%r8` on a
three-bit field is `E-OPERAND-004` (`N14cg`).

`0.75.0` extends that direction to the rest of the integer ALU family
(`ADR-0113`): fifteen rows, one per mnemonic and width. `add` gains
`rm64-r64`, `rm32-r32` and `rm16-r16` (it had only the three 64-bit immediate
rows); `and`, `or`, `xor` and `cmp` gain all three widths (they had no rows).
`addq %rcx, %rax` is `48 01 c8` (3 B), `addl %ecx, %eax` is `01 c8` (2 B) and
`addw %cx, %ax` is `66 01 c8` (3 B); `and`, `or`, `xor` and `cmp` use
`21`/`09`/`31`/`39` with the same geometry. The destination is `REX.B` +
`ModRM.r/m` on the 64-bit row (just `ModRM.r/m` at 32/16 bits), the source is
`REX.R` + `ModRM.reg`, and both fields are independent: the vector measures
both operand orders. The 64-bit rows therefore reach `%r8`-`%r15`; the 32/16
bit rows are three-bit and the high window stays deferred. The `opcode+1`
sibling (`03`/`0B`/`23`/`2B`/`33`/`3B`) stays absent, including its
register/register spelling (`EC-42`). `X86-P81` is the 80-byte vector of
thirty instructions. `adc` has no row (`N01eu`), the sibling direction is
`E-FORM-001` (`N01ev`), the `0.74.0` boundary is `E-FORM-001` (`N01ew`), a
missing source is `E-OPERAND-002` (`N02dd`) and register `8` on a 32-bit row
is `E-OPERAND-004` (`N14ch`).

`0.76.0` extends the immediate family (`ADR-0114`): thirty-six rows. `add` and
`sub` gain 32/16-bit pairs (`83 /r ib` and `81 /r id`/`iw`); `and`, `or`, `xor`
and `cmp` gain all three widths in both immediate widths; and the four 64-bit
`%rax` short forms (`25`, `0D`, `35`, `3D`) land. `addl $1, %ebx` is
`83 c3 01` (3 B), `addl $300, %ecx` is `81 c1 2c 01 00 00` (6 B),
`addw $1, %bx` is `66 83 c3 01` (4 B) and `addw $300, %cx` is
`66 81 c1 2c 01` (5 B). The `imm8` rows sign-extend to the operand size; the
full-width rows carry `imm32` at 32/64 bits and `imm16` at 16 bits. The 64-bit
`ModRM` rows put the destination in `REX.B` + `ModRM.r/m` and reach
`%r8`-`%r15`; the 32/16-bit rows are three-bit. The `%rax` short form carries
only the immediate slot, because the accumulator is implicit in the form
(`EC-04`). `X86-P82` is the 176-byte vector of thirty-six instructions. `test`
has no row (`N01ex`), the `0.75.0` boundary is `E-FORM-001` (`N01ey`),
`imm8 = 128` is `E-RANGE-001` (`N03zw`) and `imm16 = 32768` is `E-RANGE-001`
(`N03zx`).

`0.77.0` adds the `mov` immediate family (`ADR-0115`): five rows, because
`REX.W B8+rd` is `movabs` with a 64-bit immediate and stays out. `66 B8+rw iw`
and `B8+rd id` put the destination in the opcode's low three bits
(`movw $1, %bx` is `66 bb 01 00`, `movl $300, %ecx` is `b9 2c 01 00 00`);
`66 C7 /0 iw`, `C7 /0 id` and `REX.W C7 /0 id` put it in `ModRM.r/m`
(`66 c7 c3 01 00`, `c7 c3 01 00 00 00`, `48 c7 c3 2c 01 00 00`). Both shapes
of the same width decode to the same instruction (`EC-04`). The 64-bit row
reaches `%r8`-`%r15` through `REX.B` in the `REX.W` byte (`49 c7 c0 ...`); the
16/32-bit rows stay three-bit because `%r8w`/`%r8d` would add a `REX` byte
(`66 41 b9 2c 01`, `41 b9 2c 01 00 00`). `X86-P83` is the 54-byte vector of ten
instructions. `movabs` has no row (`N01ez`), the `0.76.0` boundary is
`E-FORM-001` (`N01fa`) and `imm32 = 2147483648` does not sign-extend into a
64-bit destination, so it is `E-RANGE-001` (`N03zy`).

`0.78.0` adds the `sub` memory directions (`ADR-0116`): twelve rows, the `29 /r`
store direction and the `2B /r` load direction at 64/32/16 bits with
`base + disp8` and `base + disp32`. `29` keeps the memory destination in
`ModRM.r/m` and the register in `ModRM.reg` -- `subq %rcx, 8(%rax)` is
`48 29 48 08` -- while `2B` keeps the register in `ModRM.reg` and the memory
source in `ModRM.r/m`: `subq 8(%rax), %rcx` is `48 2b 48 08`, so the same
operands differ only in the opcode byte (`EC-42`). The base is a 64-bit
register at every width, matching the `mov` memory rows; its field is three
bits at 32/16 bits (`[8,3]`/`[16,3]`) and `%rsp` is excluded because it needs
`SIB`. The 64-bit rows fold `REX.B` into the `REX.W` byte (`[0,1]`, `%r8`-`%r15`
reachable) and exclude `%rsp`/`%r12`. The mod field is `01` for `disp8` and
`10` for `disp32`; the zero-displacement shape (`mod = 00`, `48 29 08`) is a
separate template and stays out. `X86-P84` is the 62-byte vector of twelve
instructions. The indexed sibling is absent (`N01fb`, `E-FORM-001`), the
`0.77.0` boundary is `E-FORM-001` (`N01fc`) and `disp8 = 128` is
`E-RANGE-001` (`N03zz`).

### 8.2 `aarch64` `0.1.0` … `0.20.0`

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
| `aarch64:b/imm26` | `00000014` | target: `aarch64.rel`/`imm26` → `[0,26]` | 4 | `A64-P21` — `0.18.0` only |
| `aarch64:br/rn` | `00001fd6` | src: `aarch64.gpr64`/`x64` → `[5,5]` | 4 | `A64-P22` — `0.18.0` only |
| `aarch64:blr/rn` | `00003fd6` | src: `aarch64.gpr64`/`x64` → `[5,5]` | 4 | `A64-P22` — `0.18.0` only |
| `aarch64:ret/rn` | `00005fd6` | src: `aarch64.gpr64`/`x64` → `[5,5]` | 4 | `A64-P22` — `0.18.0` only |
| `aarch64:adr/x64-imm21` | `00000010` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; target: `aarch64.rel`/`imm21` → `[5,19]`, `[29,2]` | 4 | `EC-43`, `A64-P23` — `0.19.0` only |
| `aarch64:mul/w32-w32-w32` | `007c001b` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]` | 4 | `EC-44`, `A64-P24` — `Ra` pinned to 31, `0.20.0` only |
| `aarch64:mul/x64-x64-x64` | `007c009b` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]` | 4 | `EC-44`, `A64-P24` — `Ra` pinned to 31, `0.20.0` only |
| `aarch64:csel/w32-w32-w32-cond4` | `0000801a` | dest: `aarch64.gpr32`/`w32` → `[0,5]`; src: `aarch64.gpr32`/`w32` → `[5,5]`; src2: `aarch64.gpr32`/`w32` → `[16,5]`; imm: `aarch64.cond`/`cond4` → `[12,4]` | 4 | `A64-P24` — `0.20.0` only |
| `aarch64:csel/x64-x64-x64-cond4` | `0000809a` | dest: `aarch64.gpr64`/`x64` → `[0,5]`; src: `aarch64.gpr64`/`x64` → `[5,5]`; src2: `aarch64.gpr64`/`x64` → `[16,5]`; imm: `aarch64.cond`/`cond4` → `[12,4]` | 4 | `A64-P24` — `0.20.0` only |

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
sixty-eight and adds the eight `movk`/`movn` rows (ADR-0026); `0.18.0` repeats
all one hundred and seventy-six and adds the four unconditional-transfer rows
(ADR-0100); `0.19.0` repeats all one hundred and eighty and adds the `adr` row
(ADR-0118); `0.20.0` repeats all one hundred and eighty-one and adds the two
`mul` and two `csel` rows (ADR-0119).
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
eighty-five forms come
from forty-eight encode nodes: `ADD_64_addsub_shift` is read four times, once with `imm6`
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
fields as operands, `B_only_branch_imm` contributes `b`'s row (its
`BL_only_branch_imm` sibling has been `bl` since `0.1.0`), and
`BR_64_branch_reg`, `BLR_64_branch_reg` and `RET_64R_branch_reg` contribute one
row each with `Rn` as the single operand (`ADR-0100`), `ADR_only_pcreladdr`
contributes `adr`'s row with `op` fixed to 0 (its `ADRP_only_pcreladdr` sibling
has been `adrp` since `0.1.0`, `ADR-0118`), `MADD_32A_dp_3src` and
`MADD_64A_dp_3src` contribute `mul`'s rows with `Ra` pinned to 31, and
`CSEL_32_condsel`/`CSEL_64_condsel` contribute `csel`'s rows with `cond` as the
fourth operand (`ADR-0119`), and each of the eight
load/store rows reads one node whose
addressing-kind bits are fixed and whose `imm12`/`imm9` is the single variable
field (`ADR-0022` adds the three store `imm9` nodes); `LDR_64_loadlit` is the one
node with no base register, and its `imm19` is the single variable field
(`ADR-0023`); `LDR_64_ldst_regoff` and `STR_64_ldst_regoff` are each read eight
times, once per `option`/`S` pair (`ADR-0024`), and the 32-bit pair
`LDR_32_ldst_regoff`/`STR_32_ldst_regoff` eight times each on the same pattern
(`ADR-0025`); the ten `CMP`/`CMN` alias
nodes are read for verification only, because
they carry no `encoding` and the bytes stay the base node's (`ADR-0021`); the two
`MUL` alias nodes are read the same way, over the `MADD` base nodes
(`ADR-0119`). The
generator states each pinned value explicitly and asserts that `0.1.0` … `0.19.0`
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
(§4.1: first placement, most significant bits). `adr` is the same value over the
same two fields, and only bit 31 separates the two rows (`EC-43`).

`bl` and `adrp` are the two rows whose field is not a plain integer, and the
next subsection is the rule that follows from it. `adr` is the split without the
scaling: its 21-bit content is a byte displacement, so a plan states bytes and
the fixup is `pcrel_begin` + `identity` with `align_bits: 0`.

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

`adr` and `adrp` are that argument at its sharpest: the two rows have identical
placements and differ in one template bit, so a slot-level transform could not
tell a byte displacement from a page count at all. The byte reading is the plan's
`identity`, the page reading is its `page`, and a plan that names `adr` and asks
for the page transform has named a form that does not exist (`N01ff`, `EC-43`).

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
| `riscv:lui/rd-imm20` | `37000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; target: `riscv.rel`/`imm20` → `[12,20]` | 4 | `RV-P9` (field half) |
| `riscv:jalr/rd-rs1-imm12` | `67000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; src: `riscv.xreg`/`xreg` → `[15,5]`; imm: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P10` |
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

### 8.6 `rv64` `0.5.0`

`0.5.0` contains every row of §8.5 unchanged, plus the five remaining B-type
mnemonics (`ADR-0104`):

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `riscv:bne/rs1-rs2-imm12` | `63100000` | src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]`; target: `riscv.rel`/`imm12` → `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` | 4 | `RV-P11` |
| `riscv:blt/rs1-rs2-imm12` | `63400000` | src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]`; target: `riscv.rel`/`imm12` → `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` | 4 | `RV-P11` |
| `riscv:bge/rs1-rs2-imm12` | `63500000` | src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]`; target: `riscv.rel`/`imm12` → `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` | 4 | `RV-P11` |
| `riscv:bltu/rs1-rs2-imm12` | `63600000` | src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]`; target: `riscv.rel`/`imm12` → `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` | 4 | `RV-P11` |
| `riscv:bgeu/rs1-rs2-imm12` | `63700000` | src: `riscv.xreg`/`xreg` → `[15,5]`; src2: `riscv.xreg`/`xreg` → `[20,5]`; target: `riscv.rel`/`imm12` → `[31,1]`, `[7,1]`, `[25,6]`, `[8,4]` | 4 | `RV-P11` |

The five nodes sit in the same `encoding.match` family as `beq`
(`1100011`, `funct3 = 001`/`100`/`101`/`110`/`111`), and each carries the same
`location: "31|7|30-25|11-8"` and `left_shift: 1`. Only template bits 12-14
change, so the scatter, the signed 12-bit field and the `scale` fixup rule are
the ones §8.4 already pins for `beq`. The generator reads the five resolved
nodes and asserts those identities before writing the rows; `RV-P11` is the
byte vector (`EXP-0105`). A plan that names `bne` against `0.4.0` is
`E-FORM-001` (`N01en`), and the field boundary is `N04h` (`2048` is one past
the signed 12-bit content range).

### 8.7 `rv64` `0.6.0`

`0.6.0` contains every row of §8.6 unchanged, plus the other load/store widths
(`ADR-0117`):

| `form_id` | template | slots (role: kind/target_type → placements) | Bytes | Covers |
|---|---|---|---|---|
| `riscv:lb/rd-base-imm12` | `03000000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P12` |
| `riscv:lh/rd-base-imm12` | `03100000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P12` |
| `riscv:lw/rd-base-imm12` | `03200000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P12` |
| `riscv:lbu/rd-base-imm12` | `03400000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P12` |
| `riscv:lhu/rd-base-imm12` | `03500000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P12` |
| `riscv:lwu/rd-base-imm12` | `03600000` | dest: `riscv.xreg`/`xreg` → `[7,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[20,12]` | 4 | `RV-P12` |
| `riscv:sb/rs-base-imm12` | `23000000` | src: `riscv.xreg`/`xreg` → `[20,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[25,7]`, `[7,5]` | 4 | `RV-P12` |
| `riscv:sh/rs-base-imm12` | `23100000` | src: `riscv.xreg`/`xreg` → `[20,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[25,7]`, `[7,5]` | 4 | `RV-P12` |
| `riscv:sw/rs-base-imm12` | `23200000` | src: `riscv.xreg`/`xreg` → `[20,5]`; base: `riscv.xreg`/`xreg` → `[15,5]`; disp: `riscv.imm`/`imm12` → `[25,7]`, `[7,5]` | 4 | `RV-P12` |

Each row reuses its `ld`/`sd` sibling's geometry and changes only `funct3`
(bits 12-14): the loads keep the contiguous 12-bit immediate at 31-20, the
stores the S-type scatter 31-25|11-7, and `xs1` stays at 19-15 with `xd` at
11-7 or `xs2` at 24-20. The nine nodes are `inst/I/{lb,lh,lw,lbu,lhu,lwu}.yaml`
(`0000011`) and `inst/I/{sb,sh,sw}.yaml` (`0100011`); the generator reads each
one and asserts its `encoding.match`, the `imm` scatter, `sign_extend: true`
and the base `I` extension before writing the row. `lwu` is additionally
restricted to `xlen: 64` in its node, which the generator asserts. RV64 does
not scale the immediate, so `disp` is the byte displacement and no transform is
involved.

No `EC` row is added: the width is chosen by the mnemonic, so it is a form
variant rather than a field whose value the materializer could pick (`INV-01`,
`INV-02`). `fence` (`EC-24`), `ecall`/`ebreak`, the atomics (`EC-26`) and the
compressed load/store family (`EC-19`, `EC-23`) stay out. `RV-P12` is the
44-byte vector of eleven instructions (`EXP-0116`). `fence` has no row in any
version (`N01fd`, `E-FORM-001`), naming a `0.6.0` row against `0.5.0` is
`E-FORM-001` (`N01fe`), and `disp = 2048` is `E-RANGE-001` (`N03a0`).

## 9. Load-time checks

| Check | Code |
|---|---|
| `definition_format` unsupported (only `fmp-def/0.1` and `fmp-def/0.2` are accepted) | `E-DEF-001` |
| `namespace`/`version` not shipped by this materializer | `E-DEF-002` |
| a `fmp-def/0.2` form without `requires_extensions`, or a name that is empty, repeated, unsorted, or not in the table's `enabled_extensions` | `E-DEF-001` |
| a `fmp-def/0.1` form that carries `requires_extensions` (unknown field) | `E-DEF-001` |
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

`E-TARGET-003` is not a load-time check. It compares a plan's set with a form
the plan names, so it is raised by static instruction validation
(`01_contract.md` §13 step 6) and leaves the table loadable.

## 10. Open

- `OD-06` (digest coverage) is settled for this document shape by §6; the
  measurement that confirms both halves is the digest test in `EXP-0004` §4.
- `OD-07` (AArch64 knowledge source) is settled by ADR-0005 and pinned by
  ADR-0006: the facts come from the Arm MRS 2026-06 OPENSOURCE packaging, and
  the Arm notice ships with the generated table. The format did not need to
  change for it: `adrp`'s split `immhi:immlo` is two placements of one slot, as
  §4.1 anticipated, and `adr` reuses it unchanged in `0.19.0`; `mul` and
  `csel` in `0.20.0` add no new slot kind either — the alias pins an existing
  field and `csel` reuses `cond4`.
  `definitions/aarch64/0.1.0.json` … `0.20.0.json` now exist
  (§8.2); each is a superset that adds its own rows without a format change
  (ADR-0011 to ADR-0026, ADR-0100, ADR-0118, ADR-0119). What is
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
