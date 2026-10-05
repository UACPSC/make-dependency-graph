#!/usr/bin/env python3
"""
makegraph.py - Generate an SVG dependency graph from a Makefile

Usage: makegraph [Makefile] [-o output.svg] [--dot]

The first non-blank comment line in the Makefile is used as the title.

Edges point from a target to its prerequisites. Node colors:
  green - phony targets (.PHONY)
  red   - generated files (targets with rules)
  black - source files (prerequisites only)

Requires Graphviz (dot) to render the SVG.
"""

import argparse
import re
import shutil
import subprocess
import sys

VAR_REF = re.compile(r"\$\(([^()]+)\)|\$\{([^{}]+)\}")


def read_logical_lines(path):
    """Read the Makefile, joining backslash continuations and skipping recipes/comments."""
    with open(path) as f:
        raw = f.read().splitlines()

    lines = []
    buf = ""
    for line in raw:
        # recipe lines start with a tab and are not part of the dependency graph
        if not buf and line.startswith("\t"):
            continue
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        buf += line
        buf = buf.split("#", 1)[0].rstrip()
        if buf.strip():
            lines.append(buf)
        buf = ""
    return lines


def read_title(path):
    """Return the text of the first non-blank comment line, or None."""
    with open(path) as f:
        for line in f:
            # recipe lines start with a tab, so their comments are shell comments
            if line.startswith("\t") or not line.lstrip().startswith("#"):
                continue
            text = line.strip().lstrip("#").strip()
            if text:
                return text
    return None


def expand(text, variables, depth=0):
    """Expand simple $(VAR) and ${VAR} references."""
    if depth > 10:
        return text

    def repl(m):
        name = m.group(1) or m.group(2)
        return expand(variables.get(name, ""), variables, depth + 1)

    return VAR_REF.sub(repl, text)


def parse_makefile(path):
    """Return (ordered list of targets, dict target -> prerequisites, set of phony targets)."""
    variables = {}
    deps = {}
    order = []
    phony = set()

    for line in read_logical_lines(path):
        # variable assignments: VAR = val, VAR := val, VAR ?= val, VAR += val
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*([:?+!]?=)\s*(.*)$", line)
        if m:
            name, op, value = m.groups()
            if op == "+=":
                variables[name] = (variables.get(name, "") + " " + value).strip()
            elif op == "?=":
                variables.setdefault(name, value)
            elif op == ":=":
                variables[name] = expand(value, variables)
            else:
                variables[name] = value
            continue

        # rules: targets : prerequisites [; recipe]
        m = re.match(r"^([^:=]+?)\s*::?\s*(.*)$", line)
        if not m:
            continue
        targets = expand(m.group(1), variables).split()
        prereqs_text = m.group(2).split(";", 1)[0]
        # drop order-only marker but keep the prerequisites
        prereqs = expand(prereqs_text, variables).replace("|", " ").split()

        for target in targets:
            if target == ".PHONY":
                phony.update(prereqs)
                continue
            # skip other special targets and pattern rules
            if target.startswith(".") or "%" in target:
                continue
            if target not in deps:
                deps[target] = []
                order.append(target)
            for p in prereqs:
                if p not in deps[target]:
                    deps[target].append(p)

    return order, deps, phony


def quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_dot(order, deps, phony, title=None):
    out = ["digraph G {"]
    if title:
        out.append(f"    label={quote(title)}; labelloc=t; fontsize=20;")
    out.append("    node [shape=ellipse];")

    out.append("    key [shape=plaintext, label=<")
    out.append("        <table border=\"0\" cellborder=\"0\" cellspacing=\"0\">")
    out.append("        <tr><td align=\"left\"><font color=\"green\">&#9679; Phony Targets</font></td></tr>")
    out.append("        <tr><td align=\"left\"><font color=\"red\">&#9679; Generated Files</font></td></tr>")
    out.append("        <tr><td align=\"left\">&#9679; Source Files</td></tr>")
    out.append("        </table>>];")

    # every node in first-seen order: targets, then prerequisites
    nodes = []
    for t in order:
        for n in [t] + deps[t]:
            if n not in nodes:
                nodes.append(n)

    for n in nodes:
        if n in phony:
            color = "green"
        elif n in deps:
            color = "red"
        else:
            color = "black"
        out.append(f"    {quote(n)} [fontcolor={color}];")

    for t in order:
        for p in deps[t]:
            out.append(f"    {quote(t)} -> {quote(p)};")

    out.append("}")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(prog="makegraph", description="Generate an SVG dependency graph from a Makefile")
    parser.add_argument("makefile", nargs="?", default="Makefile", help="Makefile to read (default: Makefile)")
    parser.add_argument("-o", "--output", default="makegraph.svg", help="output SVG file (default: makegraph.svg)")
    parser.add_argument("--dot", action="store_true", help="print the Graphviz DOT source instead of rendering")
    args = parser.parse_args()

    try:
        dot_source = to_dot(*parse_makefile(args.makefile), title=read_title(args.makefile))
    except OSError as e:
        sys.exit(f"makegraph: {e}")

    if args.dot:
        sys.stdout.write(dot_source)
        return

    if not shutil.which("dot"):
        sys.exit("makegraph: Graphviz 'dot' not found; install Graphviz or use --dot")

    result = subprocess.run(["dot", "-Tsvg", "-o", args.output], input=dot_source, text=True)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
