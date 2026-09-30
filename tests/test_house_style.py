#!/usr/bin/env python3
"""No string the script prints holds an em dash.

    python3 -m unittest discover -s tests

The house style is for everything a customer reads, not only the
documentation site: what `./diffuse-chat` says as it runs, its refusals, and
its help, which is the module's docstring. Other docstrings and the comments
are read by whoever maintains the script, and are not held to it.
"""

import ast
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "diffuse-chat"
DASH = "—"


class HouseStyle(unittest.TestCase):
    def test_no_string_the_script_prints_holds_an_em_dash(self):
        tree = ast.parse(SCRIPT.read_text(), filename=str(SCRIPT))
        # Every docstring but the module's, which `--help` prints.
        silent = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                first = node.body[0] if node.body else None
                if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                        and isinstance(first.value.value, str)):
                    silent.add(id(first.value))

        found = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in silent and DASH in node.value):
                for line in node.value.splitlines():
                    if DASH in line:
                        found.append(f"diffuse-chat:{node.lineno}: {line.strip()[:110]}")
        if found:
            self.fail(f"{len(found)} lines the script prints hold an em dash; the house style "
                      "has none: use a comma, a colon or a full stop.\n  " + "\n  ".join(found))


if __name__ == "__main__":
    unittest.main()
