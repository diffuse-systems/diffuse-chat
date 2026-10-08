#!/usr/bin/env python3
import contextlib
import io
import pathlib
import tempfile
import types
import unittest
import unittest.mock

from test_firewall_advice import load


class Ran:
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


def chat_for(here, registered):
    chat = load()
    calls = {"registration": [], "ran": [], "register": []}
    chat.read_env = lambda: {"DIFFUSE_CHAT_SERVICE_EMAIL": "diffuse-chat@localhost.invalid"}
    chat.write_env = lambda values: calls["registration"].append(values["ALLOW_REGISTRATION"])
    chat.compose = lambda files, *a, **k: ""
    chat.wait_for_librechat = lambda port, seconds=180: True
    chat._running_config_is_enterprise = lambda: True
    chat.coordinator_here = lambda: here
    chat.say = lambda message: print(message)

    def librechat(path, payload=None, **_):
        calls["register"].append(payload)
        return 200, "{}"

    chat.librechat = librechat
    chat.mongo_eval = lambda script: "\n".join(f"{i},{e}" for e, i in registered.items())
    return chat, calls


class Users(unittest.TestCase):
    def run_import(self, here, rows):
        chat, calls = chat_for(here, {"marie@klinik.example": "6a8e01", "jonas@klinik.example": "6a8e02"})
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "users.csv"
            source.write_text(rows)
            fake = unittest.mock.Mock(return_value=Ran("2 identities imported from identities.csv."))
            with unittest.mock.patch.object(chat.subprocess, "run", fake), \
                 contextlib.redirect_stdout(out):
                code = chat.command_users(types.SimpleNamespace(action="import", file=str(source)))
            written = (pathlib.Path(tmp) / "identities.csv").read_text()
        return code, calls, written, out.getvalue(), fake

    def test_import_creates_the_accounts_and_enrols_them_on_this_coordinator(self):
        code, calls, written, said, ran = self.run_import(
            True, "email,name,password\nmarie@klinik.example,Marie Weber,\n"
                  "# a comment\njonas@klinik.example,Jonas Brandt,chosen-one\n")
        self.assertEqual(code, 0)
        self.assertEqual(calls["registration"], ["true", "false"])
        self.assertEqual([p["email"] for p in calls["register"]],
                         ["marie@klinik.example", "jonas@klinik.example"])
        self.assertEqual(calls["register"][1]["password"], "chosen-one")
        self.assertEqual(written, "subject,address,models,pool\n"
                                  "6a8e02,jonas@klinik.example,,\n6a8e01,marie@klinik.example,,\n")
        command = ran.call_args.args[0]
        self.assertEqual(command[-4:-1], ["diffuse-coordinator", "identity", "import"])
        generated = calls["register"][0]["password"]
        self.assertGreaterEqual(len(generated), 20)
        self.assertIn(generated, said)
        self.assertNotIn("chosen-one", said)

    def test_elsewhere_it_prints_the_command_for_the_coordinator(self):
        _, _, _, said, ran = self.run_import(False, "jonas@klinik.example,Jonas Brandt,x\n")
        ran.assert_not_called()
        self.assertIn("sudo diffuse-coordinator identity import identities.csv", said)

    def test_a_malformed_row_is_refused_by_line(self):
        chat = load()
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "users.csv"
            source.write_text("email,name\nnot-an-address\n")
            with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit):
                chat.read_people(source)
        self.assertIn("line 2", err.getvalue())


if __name__ == "__main__":
    unittest.main()
