#!/usr/bin/env python3
import ast
import pathlib
import unittest

from test_firewall_advice import SCRIPT, load


def calls_in(function):
    tree = ast.parse(SCRIPT.read_text())
    body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    names = {n.func.id for n in ast.walk(body) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    texts = [n.value for n in ast.walk(body) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    return names, texts


class Sharing(unittest.TestCase):
    def test_an_owner_entry_alone_is_not_sharing(self):
        chat = load()
        chat.mongo_eval = lambda script: "66ab01,0" if "principalType: \"public\"" in script else "3"
        self.assertEqual(chat.agent_sharing(), ("66ab01", 0))
        chat.mongo_eval = lambda script: "66ab01,1"
        self.assertEqual(chat.agent_sharing(), ("66ab01", 1))
        chat.mongo_eval = lambda script: "none,-1"
        self.assertEqual(chat.agent_sharing(), (None, -1))

    def test_up_and_doctor_ask_the_same_question(self):
        for function in ("command_up", "command_doctor"):
            names, texts = calls_in(function)
            self.assertIn("agent_sharing", names, function)
            self.assertFalse([t for t in texts if "aclentries" in t], function)


if __name__ == "__main__":
    unittest.main()
