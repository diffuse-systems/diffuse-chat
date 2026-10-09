#!/usr/bin/env python3
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from test_firewall_advice import load

HERE = pathlib.Path(__file__).resolve().parents[1]
EMAIL = {"EMAIL_SERVICE": "smtp", "EMAIL_FROM": "chat@klinik.example"}


class Domains(unittest.TestCase):
    def setUp(self):
        self.chat = load()
        self.tmp = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self.tmp.name)
        self.chat.DOMAINS = tmp / "compose.domains.yaml"
        self.chat.DOMAINS_CONFIG = tmp / "librechat.domains.yaml"
        self.chat.die = lambda *lines: (_ for _ in ()).throw(SystemExit("\n".join(lines)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_domains_without_an_email_service_are_refused(self):
        with self.assertRaises(SystemExit) as refused:
            self.chat.write_domains({"REGISTRATION_DOMAINS": "klinik.example"}, True)
        self.assertIn("no email service", str(refused.exception))
        self.assertFalse(self.chat.DOMAINS.exists())
        self.assertFalse(self.chat.DOMAINS_CONFIG.exists())

    def test_domains_with_an_email_service_send_the_verified_header(self):
        values = {"REGISTRATION_DOMAINS": "@Klinik.Example, uni.example", **EMAIL}
        self.assertEqual(self.chat.write_domains(values, True), ["klinik.example", "uni.example"])
        config = self.chat.DOMAINS_CONFIG.read_text()
        self.assertIn("X-Diffuse-User-Email-Verified: \"{{LIBRECHAT_USER_EMAILVERIFIED}}\"", config)
        self.assertIn("allowedDomains:\n    - klinik.example\n    - uni.example", config)
        overlay = self.chat.DOMAINS.read_text()
        self.assertIn('ALLOW_REGISTRATION: "true"', overlay)
        self.assertIn('ALLOW_UNVERIFIED_EMAIL_LOGIN: "false"', overlay)
        self.assertIn("EMAIL_SERVICE: ${EMAIL_SERVICE:-}", overlay)
        self.assertIn("librechat.domains.yaml:/app/librechat.yaml:ro", overlay)

    def test_without_domains_no_configuration_sends_the_verified_header(self):
        self.chat.write_domains({"REGISTRATION_DOMAINS": "klinik.example", **EMAIL}, True)
        self.assertTrue(self.chat.DOMAINS.exists())
        self.assertEqual(self.chat.write_domains(EMAIL, True), [])
        self.assertFalse(self.chat.DOMAINS.exists())
        self.assertFalse(self.chat.DOMAINS_CONFIG.exists())
        for path in (HERE / "config").glob("*.yaml"):
            self.assertNotIn("EMAILVERIFIED", path.read_text(), path)

    def test_domains_are_for_the_enterprise_profile(self):
        with self.assertRaises(SystemExit):
            self.chat.write_domains({"REGISTRATION_DOMAINS": "klinik.example", **EMAIL}, False)

    @unittest.skipUnless(shutil.which("docker"), "no docker")
    def test_compose_mounts_the_domain_configuration(self):
        self.chat.write_domains({"REGISTRATION_DOMAINS": "klinik.example", **EMAIL}, True)
        overlay = HERE / "compose.domains.test.yaml"
        overlay.write_text(self.chat.DOMAINS.read_text().replace(
            f"./{self.chat.DOMAINS_CONFIG.name}", str(self.chat.DOMAINS_CONFIG)))
        try:
            env = pathlib.Path(self.tmp.name) / "test.env"
            env.write_text(
                "".join(f"{k}=x\n" for k in ("JWT_SECRET", "JWT_REFRESH_SECRET", "CREDS_KEY",
                                              "CREDS_IV", "DIFFUSE_TOKEN", "DIFFUSE_GATEWAY_TOKEN"))
                + "DIFFUSE_BASE_URL=https://10.0.1.1:8443/v1\nDIFFUSE_CA_CERT=/etc/hosts\n"
                + "EMAIL_SERVICE=smtp\nEMAIL_FROM=chat@klinik.example\n")
            run = subprocess.run(
                ["docker", "compose", "--env-file", str(env), "-f", "compose.yaml",
                 "-f", "compose.enterprise.yaml", "-f", overlay.name, "config", "--format", "json"],
                cwd=HERE, capture_output=True, text=True,
                env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")})
            self.assertEqual(run.returncode, 0, run.stderr)
            service = json.loads(run.stdout)["services"]["librechat"]
            mounted = {v["target"]: v["source"] for v in service["volumes"]}
            self.assertEqual(mounted["/app/librechat.yaml"], str(self.chat.DOMAINS_CONFIG))
            self.assertEqual(service["environment"]["ALLOW_REGISTRATION"], "true")
            self.assertEqual(service["environment"]["EMAIL_SERVICE"], "smtp")
        finally:
            overlay.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
