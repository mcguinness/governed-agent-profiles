#!/usr/bin/env python3
"""Check that messages EXAMPLES.md copies from the drafts still match them.

Each fenced block in EXAMPLES.md preceded by `<!-- verbatim: FILE -->`
must equal, line for line, the content of some fenced block in FILE.
Fence characters and info strings are ignored, as is trailing whitespace.

A new block, one that no draft shows, may be preceded by
`<!-- new: FILE#ANCHOR -->`, naming the draft section whose rules it
follows; FILE must contain that `{#ANCHOR}`. Only the citation is
checked, not the block's content. Unmarked blocks are not checked.

Usage: python3 tools/check_examples.py [EXAMPLES.md]
Exits 1 if any copied block no longer matches its draft, or any new
block cites a section that does not exist.
"""
import os
import re
import sys

FENCE = re.compile(r"^(~~~|```)")
MARKER = re.compile(r"^<!-- verbatim: (\S+) -->$")
NEW_MARKER = re.compile(r"^<!-- new: (\S+?)#([A-Za-z0-9_-]+) -->$")


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
    sources, anchors, copied, new, cited, failures = {}, {}, 0, 0, 0, 0
    for start, body in fenced_blocks(lines):
        m = MARKER.match(lines[start - 1]) if start else None
        if not m:
            new += 1
            n = NEW_MARKER.match(lines[start - 1]) if start else None
            if n:
                cited += 1
                source, anchor = n.groups()
                if source not in anchors:
                    target = os.path.join(root, source)
                    anchors[source] = (set(re.findall(r"\{#([A-Za-z0-9_-]+)\}",
                                                       "\n".join(read_lines(target))))
                                       if os.path.exists(target) else set())
                if anchor not in anchors[source]:
                    failures += 1
                    print(f"{path}:{start + 1}: cites {source}#{anchor}, which does not exist")
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
    print(f"{copied} copied blocks checked; {new} new blocks, {cited} citing a "
          f"draft section; {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
