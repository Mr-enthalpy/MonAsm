"""Does the pinned UDB resolved-spec archive match an upstream repo commit?

Supporting check for the ADR-0007 pin (`EV-24`). The export carries no commit of
its own, but every resolved node records a SOURCE MAP of
`key -> file:line:column` positions for the file it was generated from. If the
upstream tree has drifted, those positions stop landing near the expected token;
a structural change moves them by many lines, not by one, so a +-1 line window
still detects drift while tolerating block scalars whose text starts below the
key.

One deviation is counted separately rather than excused: the map records one
entry per list element (`.../not/0`, `.../not/4`), so the last key segment is a
number, not a token; the parent key is checked instead and reported as
"indexed".

Not a gate: it needs the disposable drops, so it is run by hand when the pin is
reviewed. `tools/check_rv64_source.py` is the gate; this narrows the remaining
`unverified` part of the revision.

Usage:
    python tools/udb_binding.py <resolved_spec/_> <repo spec/std/isa> [--misses]
"""

import io
import os
import re
import sys

NODES = [
    r"inst\I\add.yaml",
    r"inst\I\addi.yaml",
    r"inst\I\beq.yaml",
    r"inst\I\jal.yaml",
    r"inst\I\auipc.yaml",
    r"inst\I\ld.yaml",
    r"inst\I\sd.yaml",
    r"inst\C\c.addi.yaml",
]

MAP = re.compile(r"^#\s+(\S+)\s+->\s+.*?:(\d+):(\d+)\s*$")
WINDOW = 1


def load(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read().splitlines()


def token_for(key):
    """Last non-numeric segment, plus whether a list index was skipped."""
    parts = key.split("/")
    for part in reversed(parts):
        if not part.isdigit():
            return part, len(parts) > 0 and parts[-1].isdigit()
    return parts[0], True


def check_node(archive_dir, repo_dir, rel, show_misses):
    arc = os.path.join(archive_dir, rel)
    rep = os.path.join(repo_dir, rel)
    if not (os.path.exists(arc) and os.path.exists(rep)):
        return None
    lines = load(rep)
    direct = indexed = miss = 0
    for entry in load(arc):
        match = MAP.match(entry)
        if not match:
            continue
        key, row = match.group(1), int(match.group(2))
        token, is_index = token_for(key)
        low, high = max(1, row - WINDOW), min(len(lines), row + WINDOW)
        if 1 <= row and any(token in lines[n - 1] for n in range(low, high + 1)):
            if is_index:
                indexed += 1
            else:
                direct += 1
        else:
            miss += 1
            if show_misses:
                print("    miss %-44s -> line %d" % (key, row))
    return direct, indexed, miss


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    archive_dir, repo_dir = argv[1], argv[2]
    show = "--misses" in argv
    total = [0, 0, 0]
    for rel in NODES:
        result = check_node(archive_dir, repo_dir, rel, show)
        if result is None:
            print("%-18s MISSING on one side" % rel)
            continue
        direct, indexed, miss = result
        for slot, value in zip(range(3), result):
            total[slot] += value
        verdict = "bound" if miss == 0 else "DRIFT"
        print(
            "%-18s %3d direct + %3d indexed  %s"
            % (rel, direct, indexed, verdict)
        )
    print("-" * 58)
    print(
        "total: %d direct + %d indexed positions, %d unexplained"
        % (total[0], total[1], total[2])
    )
    return 0 if total[2] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
