from pathlib import Path
from subprocess import CompletedProcess
from sys import argv
from tempfile import TemporaryDirectory

from pyright.node_project import NodeProject


def main() -> int:
    args = argv[1:]
    completed_process: CompletedProcess[bytes]

    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        project = NodeProject(tmpdir_path)
        project.add_dependency('pyright', unplug=True)
        project.bootstrap()
        completed_process = project.run('pyright-langserver', *args)
    return completed_process.returncode
