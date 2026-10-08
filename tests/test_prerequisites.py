#!/usr/bin/env python3
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "diffuse-chat"


class Prerequisites(unittest.TestCase):
    def test_without_docker_it_says_how_to_install_it(self):
        with tempfile.TemporaryDirectory() as empty:
            pathlib.Path(empty, "python3").symlink_to(sys.executable)
            run = subprocess.run([sys.executable, str(SCRIPT), "doctor"], capture_output=True,
                                 text=True, env={"PATH": empty})
        said = run.stdout + run.stderr
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("docker is not on the PATH", said)
        self.assertIn("https://docs.docker.com/engine/install/", said)
        self.assertIn("docker-compose-plugin", said)


if __name__ == "__main__":
    unittest.main()
