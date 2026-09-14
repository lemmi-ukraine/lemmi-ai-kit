"""Isolated, disposable project for the flow tools' exact certification probes."""

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def probe_project():
    """Never initialize git or write probe output inside a plugin installation."""
    source = Path(__file__).resolve().parent.parent / "assets/probe-project"
    with tempfile.TemporaryDirectory(prefix="flow-mapping-probes-") as directory:
        project = Path(directory)
        shutil.copytree(source, project, dirs_exist_ok=True)
        for args in (
            ["init", "-q"],
            ["add", "--", "."],
            [
                "-c",
                "user.name=Flow probe",
                "-c",
                "user.email=probe@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "Synthetic flow fixture",
            ],
        ):
            subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
        yield project
