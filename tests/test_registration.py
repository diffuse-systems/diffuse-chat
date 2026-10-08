#!/usr/bin/env python3
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import types
import unittest

from test_firewall_advice import load

HERE = pathlib.Path(__file__).resolve().parents[1]


def resolved(registration):
    with tempfile.TemporaryDirectory() as tmp:
        env = pathlib.Path(tmp) / "test.env"
        env.write_text(
            "".join(f"{k}=x\n" for k in ("JWT_SECRET", "JWT_REFRESH_SECRET", "CREDS_KEY", "CREDS_IV",
                                          "DIFFUSE_TOKEN", "DIFFUSE_GATEWAY_TOKEN", "MEILI_MASTER_KEY"))
            + "DIFFUSE_BASE_URL=https://10.0.1.1:8443/v1\nDIFFUSE_CA_CERT=/etc/hosts\n"
            + f"ALLOW_REGISTRATION={registration}\n"
        )
        run = subprocess.run(
            ["docker", "compose", "--env-file", str(env), "-f", "compose.yaml",
             "-f", "compose.enterprise.yaml", "config", "--format", "json"],
            cwd=HERE, capture_output=True, text=True,
            env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")},
        )
        assert run.returncode == 0, run.stderr
        return json.loads(run.stdout)["services"]["librechat"]["environment"]["ALLOW_REGISTRATION"]


class Registration(unittest.TestCase):
    @unittest.skipUnless(shutil.which("docker"), "no docker")
    def test_the_enterprise_container_takes_registration_from_env(self):
        self.assertEqual(resolved("true"), "true")
        self.assertEqual(resolved("false"), "false")

    def test_up_closes_registration_once_the_service_account_exists(self):
        chat = load()
        written, composed = [], []
        values = {"DIFFUSE_BASE_URL": "https://10.0.1.1:8443/v1"}
        stubs = {
            "read_env": lambda: values,
            "write_env": lambda v: written.append(v.get("ALLOW_REGISTRATION")),
            "ensure_secrets": lambda v: [],
            "provisioning_account": lambda v: ("svc@x", "pw"),
            "check_required": lambda v, e: None,
            "human_accounts": lambda e: 0,
            "compose_files": lambda e: ["-f", "compose.yaml"],
            "compose": lambda files, *a, **k: composed.append(a),
            "wait_for_librechat": lambda port, seconds=180: True,
            "configuration_took": lambda f, v: (True, ""),
            "ensure_endpoint_reachable": lambda f, v, e, p: f,
            "ensure_service_account": lambda p, e, w: ("token", None),
            "existing_agent": lambda p, t: "agent",
            "say": lambda m: None,
        }
        for name, stub in stubs.items():
            setattr(chat, name, stub)
        chat.command_up(types.SimpleNamespace(enterprise=True))
        self.assertEqual(written[0], "true", "open while the service account is created")
        self.assertEqual(written[-1], "false")
        self.assertEqual(composed[-1], ("up", "-d"), "the container restarted with it closed")


if __name__ == "__main__":
    unittest.main()
