"""Every internal link in the Markdown documentation must point at a file and a heading that exist.

Learners and AI agents follow these links; a broken one sends them nowhere. External (http) links are not checked.
Headings are matched with GitHub's rule: lowercase, punctuation removed, spaces turned into hyphens, duplicates
numbered. Explicit <a id="..."> anchors count as well.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".venv", "node_modules", ".lab", "reports", "instructor", "__pycache__", "lab-proof"}
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def markdown_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(".md"):
                yield os.path.join(base, name)


def slug(text):
    text = re.sub(r"`|\*|_(?=\w)|(?<=\w)_", "", text)  # inline code and emphasis marks
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # a link inside a heading keeps only its text
    text = re.sub(r"<[^>]+>", "", text.lower())
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.strip().replace(" ", "-")


def anchors(path):
    found, seen, in_code = set(), {}, False
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            found.update(re.findall(r'<a\s+id="([^"]+)"', line))
            match = HEADING.match(line)
            if match:
                base = slug(match.group(2))
                count = seen.get(base, 0)
                seen[base] = count + 1
                found.add(base if count == 0 else "{}-{}".format(base, count))
    return found


def links(path):
    in_code = False
    with open(path, encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, 1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            for match in LINK.finditer(re.sub(r"`[^`]*`", "", line)):
                yield number, match.group(1)


def test_internal_links_and_anchors_exist():
    cache, problems = {}, []
    for path in markdown_files():
        for number, target in links(path):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
                continue  # http, mailto and so on
            file_part, _, fragment = target.partition("#")
            destination = path if not file_part else os.path.normpath(os.path.join(os.path.dirname(path), file_part))
            relative = os.path.relpath(path, ROOT)
            if not os.path.exists(destination):
                problems.append("{}:{} -> {} (file not found)".format(relative, number, target))
                continue
            if fragment and destination.endswith(".md"):
                if destination not in cache:
                    cache[destination] = anchors(destination)
                if fragment.lower() not in {a.lower() for a in cache[destination]}:
                    problems.append("{}:{} -> {} (no such heading)".format(relative, number, target))
    assert not problems, "broken documentation links:\n" + "\n".join(problems)
