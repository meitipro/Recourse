"""
Unpack a Claude Design bundled export into its canvas pages and support.js,
then diff two exports page by page.

    python design/extract.py OLD NEW OUTDIR

OLD and NEW are each a bundled export, the single .html file the design tool
saves, or a directory of pages already unpacked, such as design/ itself. A
bundle is unpacked into OUTDIR/old or OUTDIR/new: the template as
Recourse.dc.html, every text/html resource under its ./Name.dc.html id, and the
template's script as support.js, each page also written flattened, one tag per
line, as *.flat.txt. OUTDIR/diff-<name>.txt holds the unified diff of each
page's flat form, so a diff names the element that changed.
"""

import base64
import difflib
import gzip
import json
import pathlib
import re
import sys


def block(html: str, kind: str) -> str:
    tag = '<script type="__bundler/' + kind + '"'
    at = html.find(tag)
    if at < 0:
        return ""
    start = html.find(">", at) + 1
    return html[start:html.find("</script>", start)]


def unpack(path: pathlib.Path, out: pathlib.Path) -> dict[str, str]:
    html = path.read_text(encoding="utf-8")
    template = json.loads(block(html, "template"))
    manifest = json.loads(block(html, "manifest"))
    resources = json.loads(block(html, "ext_resources") or "[]")
    names = {entry["uuid"]: entry["id"] for entry in resources}

    def decode(entry: dict) -> bytes:
        raw = base64.b64decode(entry["data"])
        return gzip.decompress(raw) if entry.get("compressed") else raw

    files: dict[str, str] = {}
    script = re.search(r'<script src="([0-9a-f-]{36})">', template)
    if script and script.group(1) in manifest:
        files["support.js"] = decode(manifest[script.group(1)]).decode("utf-8")
        template = template.replace(script.group(1), "./support.js")
    files["Recourse.dc.html"] = template
    for uuid, entry in manifest.items():
        if entry.get("mime") == "text/html":
            name = names.get(uuid, uuid + ".html").removeprefix("./")
            text = decode(entry).decode("utf-8")
            if script:
                text = text.replace(script.group(1), "./support.js")
            files[name] = text

    out.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
        (out / (name + ".flat.txt")).write_text(flatten(text), encoding="utf-8")
    other = sorted({entry.get("mime") for entry in manifest.values()})
    print(f"{path.name}: {len(manifest)} resources ({', '.join(m for m in other if m)}); pages: {', '.join(sorted(files))}")
    return files


def pages(path: pathlib.Path, out: pathlib.Path) -> dict[str, str]:
    """A bundled export, or a directory of pages already unpacked."""
    if path.is_dir():
        found = {page.name: page.read_text(encoding="utf-8") for page in sorted(path.glob("*.dc.html"))}
        print(f"{path}: {len(found)} unpacked pages; {', '.join(sorted(found))}")
        return found
    return unpack(path, out)


def flatten(text: str) -> str:
    """One tag or text run per line, so a diff names the element that changed."""
    parts = re.split(r"(<[^>]+>)", text)
    lines = []
    for part in parts:
        part = part.strip()
        if part:
            lines.append(part)
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    old_path, new_path, out_dir = (pathlib.Path(arg) for arg in sys.argv[1:4])
    out_dir.mkdir(parents=True, exist_ok=True)
    old = pages(old_path, out_dir / "old")
    new = pages(new_path, out_dir / "new")
    for name in sorted(set(old) | set(new)):
        if name not in old:
            print(f"  {name}: only in {new_path.name} ({len(new[name])} chars)")
            continue
        if name not in new:
            print(f"  {name}: only in {old_path.name}")
            continue
        a = flatten(old[name]).splitlines()
        b = flatten(new[name]).splitlines()
        diff = list(difflib.unified_diff(a, b, f"old/{name}", f"new/{name}", n=2, lineterm=""))
        changed = sum(1 for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---")))
        (out_dir / f"diff-{name}.txt").write_text("\n".join(diff) + "\n", encoding="utf-8")
        print(f"  {name}: {changed} changed flat lines ({len(a)} before, {len(b)} after)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
