"""
Convert the Claude Design export's HTML into JSX, mechanically.
Every inline style, every colour, every clamp() survives byte for byte. Nothing
is retyped by eye, which is the one way a port loses a design.
"""
from __future__ import annotations
import pathlib
import re
import sys
SRC = pathlib.Path("design-pretty.html")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NUMERIC_ATTRS = {"rows", "cols", "maxLength", "minLength", "size", "span", "start", "tabIndex", "width", "height"}
BOOL_ATTRS = {"noValidate", "disabled", "readOnly", "checked", "autoFocus", "multiple", "required", "hidden"}
ATTR_MAP = {
    "class": "className", "for": "htmlFor", "tabindex": "tabIndex", "colspan": "colSpan",
    "rowspan": "rowSpan", "maxlength": "maxLength", "readonly": "readOnly", "autocomplete": "autoComplete",
    "srcset": "srcSet", "novalidate": "noValidate", "contenteditable": "contentEditable",
    "spellcheck": "spellCheck", "autofocus": "autoFocus", "enterkeyhint": "enterKeyHint",
    "inputmode": "inputMode", "crossorigin": "crossOrigin",
}
def css_prop_to_js(prop: str) -> str:
    prop = prop.strip()
    if prop.startswith("--"):
        return f'"{prop}"'
    parts = prop.split("-")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])
LOOP_VARS: set[str] = set()
#: Hover and focus styles the canvas carried as attributes. React has no inline
#: pseudo classes, so each unique declaration becomes one class and one real CSS
#: rule, which keeps the design's hover states instead of dropping them.
PSEUDO_RULES: dict[tuple[str, str], str] = {}
def pseudo_class(kind: str, declarations: str) -> str:
    key = (kind, declarations.strip())
    if key not in PSEUDO_RULES:
        PSEUDO_RULES[key] = f"rc-{kind}-{len(PSEUDO_RULES) + 1}"
    return PSEUDO_RULES[key]
def pseudo_css() -> str:
    lines = []
    for (kind, declarations), name in PSEUDO_RULES.items():
        body = " ".join(part.strip() + ";" for part in declarations.rstrip(";").split(";") if part.strip())
        selector = "hover" if kind == "hover" else "focus-visible"
        lines.append(f".{name}:{selector} {{ {body} }}")
    return chr(10).join(lines)
def qualify(name: str) -> str:
    """Loop variables are their own; everything else comes from the vars object."""
    head = name.split(".")[0].split("[")[0]
    return name if head in LOOP_VARS else f"v.{name}"
def expr(text: str) -> str:
    """A value that may contain {{ bindings }} becomes a JS expression."""
    if "{{" not in text:
        return None
    # exactly one binding and nothing else
    m = re.fullmatch(r"\s*\{\{\s*(.+?)\s*\}\}\s*", text, re.S)
    if m:
        inner = m.group(1)
        return qualify(inner) if re.fullmatch(r"[A-Za-z_$][\w$.]*", inner) else inner
    # mixed text and bindings becomes a template literal
    body = re.sub(r"\{\{\s*(.+?)\s*\}\}", lambda mm: "${" + qualify(mm.group(1)) + "}", text)
    body = body.replace("`", "\\`")
    return f"`{body}`"
def style_to_object(value: str) -> str:
    """style="a: b; c: {{ d }}" becomes a JSX style object, bindings intact."""
    out = []
    depth = 0
    current = ""
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            out.append(current)
            current = ""
        else:
            current += ch
    out.append(current)
    pairs = []
    for decl in out:
        if ":" not in decl:
            continue
        prop, _, val = decl.partition(":")
        if not prop.strip():
            continue
        val = val.strip()
        js = expr(val)
        if js is None:
            js = '"' + val.replace("\\", "\\\\").replace('"', '\\"') + '"'
        pairs.append((css_prop_to_js(prop), js))
    seen = {}
    for key, val in pairs:
        seen[key] = val
    body = ", ".join(f"{k}: {v}" for k, v in seen.items())
    # Cast so the design's plain strings satisfy the stricter CSS property types.
    return "{{ " + body + " } as React.CSSProperties}"
def convert_attrs(raw: str) -> str:
    out = []
    for m in re.finditer(r'([:\w.-]+)(?:\s*=\s*"([^"]*)")?', raw):
        name, value = m.group(1), m.group(2)
        if name.startswith("hint-") or name in ("prompt-url",):
            continue
        if name in ("style-hover", "style-focus") and value:
            kind = "hover" if name.endswith("hover") else "focus-visible"
            out.append(f'className="{pseudo_class("hover" if kind == "hover" else "focus", value)}"')
            continue
        if name.startswith("sc-camel-on-"):
            event = "".join(part.capitalize() for part in name[len("sc-camel-on-"):].split("-"))
            handler = expr(value or "") or "undefined"
            out.append(f"on{event}={{{handler}}}")
            continue
        if name.startswith("sc-camel-"):
            rest = name[len("sc-camel-"):]
            name = rest[0].lower() + "".join(p.capitalize() for p in rest.split("-"))[1:] if "-" in rest else rest
        if value is None:
            out.append(f"{ATTR_MAP.get(name, name)}")
            continue
        if name == "style":
            whole = re.fullmatch(r"\s*\{\{\s*([\w.$]+)\s*\}\}\s*", value)
            if whole:
                out.append("style={" + qualify(whole.group(1)) + "}")
            else:
                out.append(f"style={style_to_object(value)}")
            continue
        key = ATTR_MAP.get(name, name)
        if "-" in key and not key.startswith(("data-", "aria-")):
            head, *rest = key.split("-")
            key = head + "".join(part[:1].upper() + part[1:] for part in rest)
        if key in NUMERIC_ATTRS and value.isdigit():
            out.append(f"{key}={{{value}}}")
            continue
        if key in BOOL_ATTRS and value in ("true", "false"):
            out.append(f"{key}={{{value}}}")
            continue
        js = expr(value)
        if js is not None:
            out.append(f"{key}={{{js}}}")
        else:
            safe = value.replace("\\", "\\\\").replace('"', "&quot;")
            out.append(f'{key}="{safe}"')
    return (" " + " ".join(out)) if out else ""
def convert(html: str) -> str:
    tokens = re.split(r"(<[^>]+>)", html)
    out = []
    stack = []
    skip_until = None
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("<!--"):
            continue
        if skip_until is not None:
            m = re.match(r"</\s*([\w:-]+)\s*>", tok) if tok.startswith("<") else None
            if m and m.group(1) == skip_until:
                skip_until = None
            continue
        if tok.startswith("<"):
            m = re.match(r"</\s*([\w:-]+)\s*>", tok)
            if m:
                tag = m.group(1)
                if tag in ("sc-if", "sc-for"):
                    kind = stack.pop() if stack else "sc-if"
                    out.append("</Fragment>))}" if kind == "sc-for" else "</>)}")
                else:
                    out.append(f"</{tag}>")
                continue
            m = re.match(r"<\s*([\w:-]+)([^>]*?)(/?)>", tok, re.S)
            if not m:
                continue
            tag, attrs, closed = m.group(1), m.group(2), m.group(3)
            if tag == "sc-if":
                cond = re.search(r'value="([^"]*)"', attrs)
                stack.append("sc-if")
                out.append("{" + (expr(cond.group(1)) if cond else "true") + " && (<>")
                continue
            if tag == "sc-for":
                lst = re.search(r'list="([^"]*)"', attrs)
                as_ = re.search(r'as="([^"]*)"', attrs)
                name = as_.group(1) if as_ else "row"
                LOOP_VARS.add(name)
                stack.append("sc-for")
                out.append("{(" + (expr(lst.group(1)) if lst else "[]") + f" || []).map(({name}, i) => (<Fragment key={{i}}>")
                continue
            body = convert_attrs(attrs)
            if tag == "textarea":
                out.append(f"<textarea{body} />")
                skip_until = "textarea"
                continue
            if tag in VOID or closed:
                out.append(f"<{tag}{body} />")
            else:
                out.append(f"<{tag}{body}>")
            continue
        # text node
        text = tok
        if not text.strip():
            out.append(text if "\n" not in text else " ")
            continue
        js = expr(text)
        if js is not None:
            out.append("{" + js + "}")
        else:
            out.append(text.replace("{", "&#123;").replace("}", "&#125;"))
    return "".join(out)
if __name__ == "__main__":
    start, end, dest = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    lines = SRC.read_text(encoding="utf-8").split("\n")
    chunk = "\n".join(lines[start - 1:end])
    pathlib.Path(dest).write_text(convert(chunk), encoding="utf-8")
    print(f"wrote {dest}: {len(chunk)} chars in, {len(pathlib.Path(dest).read_text(encoding='utf-8'))} out")