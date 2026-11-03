# EXP-0007 — the OPENSOURCE MRS package is BSD-3-Clause, and its hashes match the manifest

- Date: 2026-11-04
- Subject: which Arm MRS packaging the AArch64 table may be generated from
- Basis: **experiment** for every hash and every quoted string below
- Corrects: `EXP-0006` §3–§4, which measured a different packaging of the same
  release
- Reproduce: `python tools/check_mrs.py` in the repository root

## 1. Why a second record

`EXP-0006` measured `AARCHMRS_A_profile_FAT-2026-06`, a package that carries
`Features.json` only, whose `_meta.license.info` binds use and distribution to
the recipient's Arm agreement, and whose `Features.json` hashes to `6d5c19e7…` —
not to the `63325900…` XirAsm's manifest records.

The user then supplied a second archive of the same declared release,
`AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz`. It is a different
distribution, not a mirror: different terms, different contents, different
bytes. This record measures that archive. It does not retract `EXP-0006`; it
scopes it.

## 2. The archive that was read

```text
file   C:\Users\hanni\Downloads\AARCHMRS_OPENSOURCE_A_profile_FAT-2026-06.tar.gz
size   5696585
sha256 fe458c521745cc2d07244c416106add69ae8faa12fa3da8aad34fa76ab29399a
```

Extracted into the disposable drop point `research/external/arm-mrs/`:

```powershell
tar -xzf <archive> -C research\external\arm-mrs `
    Instructions.json Features.json README.md docs/notice.html docs/relnotes/index.html
```

Measured contents:

| File | Size (B) | SHA-256 |
|---|---|---|
| `Instructions.json` | 115441429 | `a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe` |
| `Features.json` | 1243621 | `633259000ffd3da32900bd0c0c1beae4a9eea7095c278f74d62a00c846b41187` |

The archive also carries `Registers.json`, `schema/`, and `docs/` (the listing
was read with `tar -tzf`). `Instructions.json` is present, which is the file the
AArch64 encoding slice needs and which the `EXP-0006` package does not contain.

## 3. Release identity — the same, so it does not distinguish the packages

`Instructions.json` `_meta.version`:

```json
{ "architecture": "vFATAp1-A", "build": "818", "ref": "2026-06_rel",
  "schema": "2.9.5", "timestamp": "2026-06-24 17:12:14" }
```

Identical to `EXP-0006` §2 and to XirAsm's `source_lock.version`. Therefore the
release block identifies a *release*, not a *packaging*: two archives that agree
on `ref` and `build` can still differ in licence and in bytes. A pin that names
only `ref` + `build` is not a pin.

## 4. Licence — BSD-3-Clause, declared per file and in the package notice

`_meta.license` in `Instructions.json` (and the same object in `Features.json`):

> "copyright": "Copyright (c) 2010-2026 Arm Limited or its affiliates. All rights reserved."
>
> "info": "This document is Non-confidential and licensed under the BSD 3-clause license."

`README.md` says the notice is the package-wide one, not a schema-only document:

> The [notice](docs/notice.html) gives details of the license terms and conditions
> under which this package is provided.

`README.md` also states the relationship to the proprietary packages:

> This package contains a subset of the information provided in the packages
> with Arm proprietary licenses. Content that is not currently in a machine-readable
> format, as well as all descriptive content, is omitted.

`docs/notice.html`, text content as extracted (quotation marks and the em dash
are the file's):

> AARCHMRS Schema 2.9.5
>
> Copyright 2010-2026 Arm Limited or its affiliates.
>
> Redistribution and use in source and binary forms, with or without
> modification, are permitted provided that the following conditions are met:
>
> 1. Redistributions of source code must retain the above copyright notice, this
>    list of conditions and the following disclaimer.
> 2. Redistributions in binary form must reproduce the above copyright notice,
>    this list of conditions and the following disclaimer in the documentation
>    and/or other materials provided with the distribution.
> 3. Neither the name of the copyright holder nor the names of its contributors
>    may be used to endorse or promote products derived from this software
>    without specific prior written permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
> AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
> IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
> DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
> FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
> DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
> SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
> CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
> OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
> OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The three-clause BSD text XirAsm reproduces is therefore **the upstream notice of
this packaging**, exactly as ADR-0005 assumed. `EXP-0006` §4 read a package whose
notice is different; both statements are true of their own archive.

## 5. The manifest hashes match — measured, and this is the load-bearing part

XirAsm's `include/arm/a64/generated/latest/manifest.json`, `source_lock.files`:

```json
{ "Features.json":     "633259000ffd3da32900bd0c0c1beae4a9eea7095c278f74d62a00c846b41187",
  "Instructions.json": "a1ad2c6538a47cd97d8762791ac5af88bce1d5f6aff096c9b77aef853e76acfe" }
```

Both equal the hashes measured in §2, byte for byte, with no normalisation.
`EXP-0006` §3's conclusion — "the manifest hash covers a processed copy or
another artifact, not the public upstream file" — is falsified for this
packaging. The correct reading of both experiments together:

- The manifest pins the **OPENSOURCE** packaging exactly.
- The manifest does not describe the other `AARCHMRS_A_profile_FAT-2026-06`
  packaging, whose `Features.json` is a different, larger file
  (`1590274` B, `6d5c19e7…`, `EXP-0006` §2).

One hypothesis explains both observations and is now supported by two
measurements: the two archives carry different serialisations of the same
release. What remains `inference` is *why* they differ (generation options,
omitted descriptive content, packaging pipeline); no upstream text was read that
says so.

## 6. What this settles and what it does not

Settled by measurement:

- The OPENSOURCE archive's own files declare BSD-3-Clause, and its
  `docs/notice.html` reproduces the three conditions plus the disclaimer.
- `Instructions.json` and `Features.json` in that archive hash to the values
  XirAsm's manifest records, so the manifest is a usable pin **for this
  packaging**.
- Release identity (`ref` + `build`) is not packaging identity; the `EXP-0006`
  package shares the release block and differs in terms and bytes.

Not settled:

- Whether Arm's other packagings of the same release are also BSD-3-Clause. The
  one measured in `EXP-0006` is not, so this must be decided per archive, by
  hash, never by release.
- Whether derived tables published in this Apache-2.0 repository satisfy
  condition 2 for a binary that embeds them. The table ships as JSON with the
  notice beside it (ADR-0005 §Decision 3, ADR-0006); a future embedded table
  needs the notice in that binary's documentation, and that is a shipping
  checklist item, not a measurement.
- The provenance of the `schema/` tree. XirAsm records
  `schema_tree_sha256 = 5fb04eed…` over 140 schema files; the hash algorithm was
  not read, and the tree was not extracted in this experiment. Not needed for
  the encoding slice, and marked `unverified`.

## 7. Consequence

`ADR-0006` pins this packaging by archive hash, by both file hashes, and by the
declared licence string, and `tools/check_mrs.py` gates on all three. A drop
that satisfies `ref` + `build` but fails a hash is rejected: that is exactly the
`EXP-0006` package, and accepting it would silently swap the licence basis of
`definitions/aarch64/`.

`ADR-0005`'s evidence table row "Arm's download/website terms match the
reproduced notice — unverified" is now verified for this packaging. The ADR's
decision text does not change; only its residual risk is closed, so it is
amended, not superseded.
