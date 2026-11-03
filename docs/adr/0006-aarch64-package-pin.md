# ADR-0006: the AArch64 source is pinned by MRS packaging, not by release

- Status: accepted
- Date: 2026-11-04
- Settles: the `OD-07` pin (ADR-0005 decided the source; this decides which bytes)
- Amends: ADR-0005
- Supersedes: none
- Superseded by: none

## Context

ADR-0005 fixed the source of AArch64 encoding facts as the Arm Architecture
Machine Readable Specification, 2026-06, and left one residual risk: Arm's own
archive terms had not been read, only the notice XirAsm reproduces.

Reading them produced a sharper problem than expected. Two archives of the
**same declared release** were measured (`EXP-0006`, `EXP-0007`):

| | `AARCHMRS_A_profile_FAT-2026-06` | `AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz` |
|---|---|---|
| `Instructions.json` | absent | present, `115441429` B, `a1ad2c65…` |
| `Features.json` | `1590274` B, `6d5c19e7…` | `1243621` B, `63325900…` |
| `_meta.license.info` | use/distribution bound to the recipient's Arm agreement | "licensed under the BSD 3-clause license" |
| `docs/notice.html` | no reproduction without Arm's prior written permission | three-clause BSD |

Both declare `architecture vFATAp1-A`, `build 818`, `ref 2026-06_rel`,
`schema 2.9.5`, `timestamp 2026-06-24 17:12:14`.

So the release block that ADR-0005 named as the identity — and that
`tools/check_mrs.py` gated on — accepts an archive the project has no right to
redistribute from, and rejects nothing. Release identity is not packaging
identity.

A second fact changes what a pin can rest on: the OPENSOURCE archive's two files
hash **exactly** to XirAsm's `source_lock.files` (`a1ad2c65…`, `63325900…`).
`EXP-0006` §3 read the mismatch as "the manifest describes a processed copy";
the correct reading is that the manifest describes this packaging and not the
other one. The manifest is therefore a valid cross-check, but not a pin of its
own: it is a third-party file in a disposable zone, and a hash match says nothing
about licence terms.

## Decision

1. **The pinned drop is `AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz`**,
   identified by
   `sha256:fe458c521745cc2d07244c416106add69ae8faa12fa3da8aad34fa76ab29399a`
   (`5696585` B). `definitions/aarch64/` may only be generated from a drop that
   satisfies every clause below.
2. **Four conditions, all required, all mechanical.**
   - `_meta.version` equals the 2026-06 release block recorded in `PINNED`;
   - `Instructions.json` hashes to `a1ad2c65…`;
   - `Features.json` hashes to `63325900…`;
   - `_meta.license.info` in both files is "licensed under the BSD 3-clause
     license".
   `tools/check_mrs.py` is the gate. A drop that passes the release check and
   fails a hash or the licence string is **rejected**, not repaired and not
   accepted with a warning (`INV-07`).
3. **The notice ships with the data.** `definitions/aarch64/NOTICE` reproduces
   `docs/notice.html` — copyright line, the three conditions, the disclaimer —
   and names the archive hash it came from. This is condition 1 (source) and
   condition 2 (binary) of the notice. ADR-0005 §Decision 3 is unchanged.
4. **No MRS file enters git.** `research/external/arm-mrs/` stays gitignored and
   deletable; the product build reads only `definitions/`. The pin is a
   verification step run against a user-supplied archive, never a build input.
5. **`check_mrs.py` never reads XirAsm.** Its hashes are ours, recorded in this
   ADR and in the tool. Agreement with `manifest.json` is reported as a
   cross-check when that file happens to be present, and its absence is not a
   failure.
6. **A packaging change is a new ADR.** A new MRS release, or the same release
   in another packaging, is not covered by this pin even if the release block
   matches. That ADR must re-read `_meta.license` and the notice, record the new
   archive hash, and state whether `definitions/aarch64/` is regenerated.

## Consequences

- The `EXP-0006` archive, and anything else that only satisfies `ref` + `build`,
  fails the gate loudly. That is the intended behaviour: it is the archive whose
  terms forbid redistribution.
- The residual-risk row in ADR-0005 ("Arm's terms match the reproduced notice —
  unverified") is closed for this packaging by `EXP-0007` §4. Nothing in
  ADR-0005's decision changes.
- The table's provenance record now has a single 64-bit value per axis: archive
  hash, definition digest (`OD-06`), and the MRS node name per row. `INV-08`
  replay does not depend on the archive still being downloadable, since the
  digest covers the table, not the input.
- Cost: a user with only the proprietary download cannot regenerate the table.
  Accepted — correctness of the licence basis outranks convenience, and the
  shipped table plus digest does not need regeneration to be validated.
- Risk accepted: the OPENSOURCE package is documented by Arm as "a subset of
  the information provided in the packages with Arm proprietary licenses". If a
  later slice needs content that the subset omits, that slice is blocked rather
  than sourced from the other packaging.

## Alternatives considered

- **Pin by release block only** (the `check_mrs.py` behaviour committed in
  `6963944`). Rejected: measured to accept the non-redistributable packaging.
  This is the failure the ADR exists to prevent.
- **Pin by XirAsm's `manifest.json`.** Rejected as the primary pin. It lives in
  a disposable snapshot, it is not a licence statement, and adopting it would
  make a third-party generated file the arbiter of what we may ship.
- **Pin the archive by name only.** Rejected: names are reissued; the same
  filename was measured above to denote two different byte streams.
- **Keep ADR-0005 and treat `EXP-0006` as decisive.** Rejected: it would forbid
  a source whose own files grant exactly the permission ADR-0005 assumed, and it
  would leave the project without an AArch64 knowledge source for a reason that
  is true of a different archive.
- **Supersede ADR-0005.** Rejected as bookkeeping error: the source decision,
  the no-XirAsm-copy rule and the notice obligation all stand. Only the pin was
  underspecified, so this ADR amends it.

## Evidence status

| Claim | Basis | Confidence |
|---|---|---|
| The two archives share the release block and differ in bytes | `EXP-0006` §2, `EXP-0007` §3, measured | high |
| The OPENSOURCE archive declares BSD-3-Clause per file and in `notice.html` | `EXP-0007` §4, read | high |
| Its `Instructions.json`/`Features.json` match XirAsm's manifest hashes | `EXP-0007` §5, measured | high |
| The proprietary packaging's terms forbid reproduction | `EXP-0006` §4, read | high |
| The `schema/` tree hash in the manifest covers the extracted schema tree | not verified; algorithm unread, tree not extracted | **unverified** |
| Derived-table redistribution satisfies notice condition 2 for an embedded binary | not tested; the JSON ships with the notice beside it | **unverified** |

## Review triggers

- A new MRS release or packaging is supplied.
- `check_mrs.py` fails on a drop the user believes is correct.
- A slice needs data absent from the OPENSOURCE subset.
- A table is embedded in a distributed binary.
- Arm changes the `notice.html` text or the `_meta.license` wording.
