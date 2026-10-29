#!/usr/bin/env python3
"""Check that messages EXAMPLES.md copies from the drafts still match them.

Each fenced block in EXAMPLES.md preceded by `<!-- verbatim: FILE -->`
must equal, line for line, the content of some fenced block in FILE.
Fence characters and info strings are ignored, as is trailing whitespace.
Blocks without the marker are new to EXAMPLES.md and are not checked.

Usage: python3 tools/check_examples.py [EXAMPLES.md]
Exits 1 if any copied block no longer matches its draft.
"""
import os
import re
import sys

FENCE = re.compile(r"^(~~~|```)")
MARKER = re.compile(r"^<!-- verbatim: (\S+) -->$")


def fenced_blocks(lines):
    """Yield (opening line index, content lines) for each fenced block."""
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        start, fence, body = i, m.group(1), []
        i += 1
        while i < len(lines) and not lines[i].startswith(fence):
            body.append(lines[i].rstrip())
            i += 1
        yield start, body
        i += 1


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "EXAMPLES.md"
    root = os.path.dirname(os.path.abspath(path))
    lines = read_lines(path)
    sources, copied, new, failures = {}, 0, 0, 0
    for start, body in fenced_blocks(lines):
        m = MARKER.match(lines[start - 1]) if start else None
        if not m:
            new += 1
            continue
        copied += 1
        source = m.group(1)
        if source not in sources:
            sources[source] = [b for _, b in
                               fenced_blocks(read_lines(os.path.join(root, source)))]
        if body not in sources[source]:
            failures += 1
            first = next((l for l in body if l.strip()), "")
            print(f"{path}:{start + 1}: no longer matches {source}: {first}")
    print(f"{copied} copied blocks checked, {failures} changed; {new} new blocks")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
