# EXP-0006 — the upstream Arm MRS package is not under the BSD notice XirAsm reproduces

- Date: 2026-11-04
- Subject: the licence and release identity of the Arm MRS drop behind `OD-07`
- Basis: **experiment** for every hash and every quoted string below
- Reproduce: `python tools/check_mrs.py` in the repository root
- Amended by: `EXP-0007` — every finding below holds **only** for the
  `AARCHMRS_A_profile_FAT-2026-06` packaging. The later
  `AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz` declares BSD-3-Clause and
  matches the manifest hashes exactly, so §3's "not the public upstream file" and
  §4's "the BSD text was not found upstream" are false for that packaging. Read
  the two records together: the licence and the bytes are properties of an
  archive, not of a release.

## 1. What was read

The user downloaded the Arm A-profile package to
`C:\Users\hanni\Downloads\AARCHMRS_A_profile_FAT-2026-06\` and it was copied to
the disposable drop point `research/external/arm-mrs/`.

Package contents (from its own `README.md`):

> This is the Arm Architecture Machine Readable Specification containing the
> Features.json for A-profile Architecture.

So the FAT package carries **`Features.json` only**. It does not carry
`Instructions.json`, the file the AArch64 encoding slice needs.

## 2. Release identity — matches

`Features.json` declares, in `_meta.version`:

```json
{ "architecture": "vFATAp1-A", "build": "818", "ref": "2026-06_rel",
  "schema": "2.9.5", "timestamp": "2026-06-24 17:12:14" }
```

That is the same release block XirAsm's generated manifest records
(`research/external/XirAsm/include/arm/a64/generated/latest/manifest.json`,
`source_lock.version`). Measured size and hash of the drop:

```text
Features.json  size 1590274
sha256 6d5c19e70492db0edb7a0a51efddf78573a311289771097cc8ad6e2000129b58
```

## 3. The manifest's file hash does not identify the upstream file — measured

The same XirAsm manifest records `source_lock.files.Features.json` as

```text
633259000ffd3da32900bd0c0c1beae4a9eea7095c278f74d62a00c846b41187
```

The upstream `Features.json` of the **same declared release** hashes to
`6d5c19e7…` instead. Four attempted normalisations did not close the gap:

| Transform of the upstream file | SHA-256 |
|---|---|
| raw bytes | `6d5c19e7…` |
| CRLF → LF | `6d5c19e7…` (unchanged; the file is already LF) |
| canonical JSON (`sort_keys`, `(',', ':')`, UTF-8) | `14417dee…` |
| canonical JSON without `_meta` | `bc5fe179…` |

The 2026-09 package's `Features.json` also does not match
(`d4bc3952…`, size 1,654,735).

**Conclusion:** the manifest hash covers a processed copy or another artifact,
not the public upstream file. It cannot be used as a release pin for a drop.
Release identity must be read from the document's own `_meta.version`, which is
what `tools/check_mrs.py` now does.

## 4. Licence — the upstream notice is proprietary, not BSD-3-Clause

`Features.json`, `_meta.license`:

> "copyright": "Copyright (c) 2010-2026 Arm Limited or its affiliates. All rights reserved.",
> "info": "This document is Non_confidential. This document may only be used and
> distributed in accordance with the terms of the agreement entered into by Arm
> and the party that Arm delivered this document to."

And `docs/notice.html` in the same package:

> No part of this document may be reproduced in any form by any means without
> the express prior written permission of Arm Limited ("Arm"). No license,
> express or implied, by estoppel or otherwise to any intellectual property
> rights is granted by this document unless specifically stated.

Compare `research/external/XirAsm/include/arm/a64/generated/latest/NOTICE`,
which says "the upstream data carries the following notice" and then reproduces
a **three-clause BSD** text. That BSD text was not found in the upstream package
we read. It may describe XirAsm's generated data rather than Arm's input, but
the NOTICE presents it as the upstream terms, and the upstream file contradicts
it.

## 5. What this settles and what it does not

Settled:

- The 2026-06 A-profile **FAT** package's own terms forbid reproduction without
  prior written permission and bind use/distribution to the recipient's Arm
  agreement.
- XirAsm's BSD-3-Clause reading cannot be used to justify shipping
  MRS-derived tables.
- The manifest's file hashes are not upstream pins.

Not settled:

- The terms of the **`Instructions.json` package**. It was not downloaded, so
  its notice was not read. It is plausible that the same terms apply to the
  same release, but that is `inference`, not evidence.
- Whether the user's own Arm agreement permits redistribution of derived tables
  in a public Apache-2.0 repository. That is a legal question, not a
  measurement.

## 6. Consequence

`ADR-0005` assumed the MRS data could be used and that a BSD notice travelled
with it. The read text does not support that assumption. The ADR must be
superseded before any AArch64 table is generated from this drop, and no
MRS-derived file may enter `definitions/` until the redistribution question is
answered.

The x86-64 slice is unaffected: it uses no Arm data.
