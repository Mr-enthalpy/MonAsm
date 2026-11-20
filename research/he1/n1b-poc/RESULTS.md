# N1b path-layer probe: three-platform results

> Evidence only. This file is not a contract and is never a build input. The
> normative requirement is `ADR-0128` §3; this file records one feasibility
> experiment and does not declare N1b accepted.

- Probe commit: `1b6d952` (`research/he1/n1b-poc/n1b_poc.c`,
  `.github/workflows/n1b-poc.yml`).
- Workflow run: `44729976671` (push). Jobs: `136266936382` (Windows),
  `136266936622` (macOS), `136266936724` (Ubuntu).
- A first run `44729849396` failed to compile on macOS (`O_NOFOLLOW` hidden by
  strict C mode). The passing run is a build of the fixed source, not a retry of
  a green test.
- Probe time: 2026-11-20, 11:43Z–11:44Z.

## What was measured

The program opens a directory handle once, then opens each child component
relative to that handle:

| Platform | Mechanism | Why it is the relevant API |
|---|---|---|
| Linux 7.0.0-1020-azure | `openat2(dirfd, name, RESOLVE_NO_SYMLINKS \| RESOLVE_NO_MAGICLINKS)` | refuses links at every component relative to the handle, without a `stat`→`open` window |
| macOS Darwin 25.6.0 | `openat(dirfd, name, O_NOFOLLOW)` per component | the directory fd fixes the parent; `O_NOFOLLOW` refuses the final component of each step |
| Windows 10.0 build 26100 | `NtCreateFile(RootDirectory=handle, FILE_OPEN_REPARSE_POINT)`, then `FileAttributeTagInfo` | Win32 has no relative-by-handle open; the native call keeps the parent fixed and opens the reparse point itself instead of following it |

## Per-platform results

All required cases passed on all three platforms. The exact rows:

| Case | Linux | macOS | Windows |
|---|---|---|---|
| `plain` nested read | PASS `hello-n1b` | PASS `hello-n1b` | PASS `hello-n1b` |
| `intermediate_link` | PASS, symlink refused `errno 20` | PASS, symlink refused `errno 20` | PASS, junction refused, reparse tag `0xa0000003` |
| `final_link` | PASS, symlink refused `errno 40` | PASS, symlink refused `errno 62` | PASS, file symlink refused, reparse tag `0xa000000c` |
| `final_reparse_dir` | n/a (POSIX has no reparse point) | n/a | PASS, refused `0xc00000ba` (`STATUS_FILE_IS_A_DIRECTORY`) |
| `fifo` | PASS, mode `010600` rejected, `0 ms` | PASS, mode `010600` rejected, `0 ms` | n/a (no POSIX FIFO in the Win32 namespace) |
| `swap` | PASS, read `original-dir` | PASS, read `original-dir` | PASS, read `original-dir` |

Raw summary lines:

```
N1b-PoC platform="Linux 7.0.0-1020-azure" api="openat2(RESOLVE_NO_SYMLINKS|RESOLVE_NO_MAGICLINKS) per component"
N1b-PoC summary platform="Linux 7.0.0-1020-azure" failures=0
N1b-PoC platform="Darwin 25.6.0" api="openat(O_NOFOLLOW) per component against the parent dirfd"
N1b-PoC summary platform="Darwin 25.6.0" failures=0
N1b-PoC platform="Windows 10.0 build 26100" api="NtCreateFile(RootDirectory=dir handle, FILE_OPEN_REPARSE_POINT)"
N1b-PoC summary platform="Windows 10.0 build 26100" failures=0
```

## What the probe establishes

1. The open-time guarantee is implementable on all three hosted platforms with
   a handle-relative, no-follow open; it does not require a `stat`→`open`
   sequence, and the swap case shows the child still comes from the directory
   whose handle was opened, not from a replacement at the same path.
2. Windows reparse points can be refused without following them, for both an
   intermediate junction and a final file symlink, by opening the reparse point
   itself and checking `FILE_ATTRIBUTE_REPARSE_POINT`.
3. A POSIX FIFO is rejected as non-regular at open time, before any read, with no
   measurable block (`0 ms` on both runners). The open uses `O_NONBLOCK`, so the
   FIFO cannot block the reader even transiently.
4. `std::fs` alone is not the mechanism: the three rows use platform-specific
   calls, which is why `ADR-0128` §3 permits a dedicated path-layer dependency.

## Limits (do not read this as N1b acceptance)

- This is a **feasibility probe on hosted runner images**, not the product PoC
  and not the hardened reader. N1b still requires the committed PoC deliverable
  and the reader with these semantics in H2b; the acceptance table must carry
  platform version, API name and observed result, and a missing row still stops
  the verdict.
- Windows has no POSIX FIFO entry that can appear in a package path; the
  Windows-specific non-regular case is the file-type check. A named-pipe path
  (`\\.\pipe\...`) is outside the tree namespace; the reader must still refuse
  it, but this probe does not exercise it.
- Only two reparse tags were observed (mount point and symlink). Other tags
  (`IO_REPARSE_TAG_APPEXECLINK`, cloud placeholders, WSL metadata) are rejected
  by the same attribute check but were not created and observed here.
- POSIX mount points, bind mounts and APFS firmlinks are not symlinks and were
  not probed. Whether they must be refused is a contract question for the
  reader; this probe makes no claim about them.
- Hard links are ordinary regular files, not links to follow; the probe does not
  distinguish them, and no requirement currently does.
- Case-folding collisions, network filesystems, UNC paths and non-ASCII names
  were not exercised.
- The probe ran on GitHub's current `ubuntu-latest`, `macos-latest` and
  `windows-latest` images only. A supported-platform matrix, minimum OS
  versions and the dependency choice remain H2b decisions.

## Reproduce

```
cc -std=gnu11 -O2 -Wall -Wextra -o n1b_poc research/he1/n1b-poc/n1b_poc.c
./n1b_poc "$TMPDIR/n1b"
```

On Windows, build with `clang -std=c11` or MSVC `/std:c11`; the program links no
extra library because `NtCreateFile` is resolved from `ntdll.dll` at run time.
The workflow `.github/workflows/n1b-poc.yml` runs the same source on the three
hosted images for `research/he1/n1b-poc/**` changes.
