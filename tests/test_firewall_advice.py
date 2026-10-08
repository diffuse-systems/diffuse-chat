#!/usr/bin/env python3
import ast
import importlib.machinery
import importlib.util
import pathlib
import re
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "diffuse-chat"

OPENS_TO_ALL = re.compile(
    r"ufw allow (in )?(proto \w+ )?\d+(/\w+)?\b"
    r"|ufw allow (in )?(proto \w+ )?to any port"
    r"|--add-port="
    r"|firewall open --from any"
)


def opens_to_all(text):
    return [line for line in text.splitlines() if OPENS_TO_ALL.search(line) and " from " not in line]


def load():
    loader = importlib.machinery.SourceFileLoader("diffuse_chat", str(SCRIPT))
    spec = importlib.util.spec_from_loader("diffuse_chat", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class FirewallAdvice(unittest.TestCase):
    def test_the_guard_catches_the_advice_1_3_3_gave(self):
        for line in ("With ufw:   sudo ufw allow 8443/tcp",
                     "sudo firewall-cmd --add-port=8443/tcp --permanent",
                     "sudo diffuse-coordinator firewall open --from any"):
            self.assertTrue(opens_to_all(line), line)
        self.assertFalse(opens_to_all("sudo diffuse-coordinator firewall open --from local,172.18.0.0/16"))

    def test_no_string_of_the_script_opens_a_port_to_every_source(self):
        tree = ast.parse(SCRIPT.read_text())
        texts = []
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                texts.append((node.lineno, "".join(
                    part.value if isinstance(part, ast.Constant) else "8443"
                    for part in node.values)))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                texts.append((node.lineno, node.value))
        found = [f"diffuse-chat:{lineno}: {line.strip()}"
                 for lineno, text in texts for line in opens_to_all(text)]
        self.assertFalse(found, "\n".join(found))

    def test_a_firewall_timeout_is_answered_with_the_docker_subnet(self):
        module = load()
        headline, repairs = module.diagnose("ETIMEDOUT", "https://10.0.1.1:8443/v1", "172.18.0.0/16")
        self.assertIn("firewall", headline)
        text = "\n".join(repairs)
        self.assertIn("sudo diffuse-coordinator firewall open --from local,172.18.0.0/16", text)
        self.assertFalse(opens_to_all(text), text)

    def test_up_adds_the_docker_subnet_to_what_is_already_let_in(self):
        module = load()
        answers = {}

        class Ran:
            def __init__(self, stdout):
                self.stdout, self.returncode = stdout, 0

        def fake(command, **_):
            return Ran(answers["status"])

        module.subprocess.run = fake
        answers["status"] = '{"on": true, "from": "local,10.20.0.0/16"}'
        self.assertEqual(module.firewall_opening("172.18.0.0/16"),
                         ["diffuse-coordinator", "firewall", "open", "--from",
                          "local,10.20.0.0/16,172.18.0.0/16"])
        answers["status"] = '{"on": true, "from": "local,172.18.0.0/16"}'
        self.assertIsNone(module.firewall_opening("172.18.0.0/16"))
        answers["status"] = '{"on": false, "from": null}'
        self.assertIsNone(module.firewall_opening("172.18.0.0/16"))


if __name__ == "__main__":
    unittest.main()
