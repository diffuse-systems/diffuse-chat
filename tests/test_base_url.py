#!/usr/bin/env python3
import contextlib
import io
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from test_firewall_advice import load


def chat_with(here, names, local, port=8443):
    chat = load()
    chat.coordinator_here = lambda: here
    chat.certificate_names = lambda path="": names
    chat.private_addresses = lambda: local
    chat.api_port = lambda path="": port
    chat.say = lambda message: None
    return chat


def refused(chat, values):
    err = io.StringIO()
    with contextlib.redirect_stderr(err), self_exit() as caught:
        chat.choose_base_url(values)
    return caught, err.getvalue()


@contextlib.contextmanager
def self_exit():
    caught = []
    try:
        yield caught
    except SystemExit as exit:
        caught.append(exit.code)


class BaseUrl(unittest.TestCase):
    def test_the_example_name_is_not_a_working_default(self):
        caught, said = refused(chat_with(False, [], []),
                               {"DIFFUSE_BASE_URL": "https://coordinator.internal:8443/v1"})
        self.assertEqual(caught, [1])
        self.assertIn("still the example", said)

    def test_on_the_coordinator_it_takes_a_private_address_the_certificate_names(self):
        chat = chat_with(True, ["de-coordinator", "127.0.0.1", "10.0.1.1"], ["10.0.1.1", "172.17.0.1"])
        values = {"DIFFUSE_BASE_URL": "https://coordinator.internal:8443/v1"}
        chat.choose_base_url(values)
        self.assertEqual(values["DIFFUSE_BASE_URL"], "https://10.0.1.1:8443/v1")

    def test_an_address_the_operator_set_is_kept(self):
        chat = chat_with(True, ["10.0.1.1"], ["10.0.1.1"])
        values = {"DIFFUSE_BASE_URL": "https://10.0.1.9:8443/v1"}
        chat.choose_base_url(values)
        self.assertEqual(values["DIFFUSE_BASE_URL"], "https://10.0.1.9:8443/v1")

    def test_with_no_fitting_address_it_names_what_the_certificate_has(self):
        caught, said = refused(chat_with(True, ["127.0.0.1", "203.0.113.5"], ["10.0.1.1"]), {})
        self.assertEqual(caught, [1])
        self.assertIn("127.0.0.1, 203.0.113.5", said)

    @unittest.skipUnless(shutil.which("openssl"), "no openssl")
    def test_the_names_are_read_from_a_real_certificate(self):
        with tempfile.TemporaryDirectory() as tmp:
            cert = pathlib.Path(tmp) / "c.crt"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt",
                            "ec_paramgen_curve:P-256", "-nodes", "-keyout", f"{tmp}/k",
                            "-out", str(cert), "-days", "1", "-subj", "/CN=x",
                            "-addext", "subjectAltName=IP:10.0.1.1,DNS:de-coordinator"],
                           capture_output=True, check=True)
            names = load().certificate_names(str(cert))
        self.assertEqual(sorted(names), ["10.0.1.1", "de-coordinator"])


if __name__ == "__main__":
    unittest.main()
