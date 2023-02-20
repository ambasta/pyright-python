from json import loads
from os import environ
from pathlib import Path
from subprocess import DEVNULL, CompletedProcess
from sys import argv, exit
from tempfile import TemporaryDirectory
from typing import Any, NoReturn, Optional

from . import __pyright_version__, node


def main(*args: str, **kwargs: Any) -> int:
    return run(*args, **kwargs).returncode


def run(
    *args: str,
    **kwargs: Any,
) -> CompletedProcess[bytes] | CompletedProcess[str]:
    retcode: CompletedProcess[bytes] | CompletedProcess[str]

    with TemporaryDirectory(prefix='pyright-python-langserver.') as tmpdir:
        version = environ.get('PYRIGHT_PYTHON_FORCE_VERSION', __pyright_version__)

        if version == 'latest':
            version = node.latest('pyright')

        node_pkg = Path(tmpdir) / 'node_modules' / 'pyright' / 'package.json'

        current_version: Optional[str] = None

        if node_pkg.exists():
            current_version = loads(node_pkg.read_text()).get('version')

        if current_version != version:
            # node.init(cwd=tmpdir, stdout=DEVNULL, stderr=DEVNULL)
            # node.add('pyright')
            node.run(
                'yarn',
                'init',
                '-y',
                cwd=tmpdir,
                check=True,
                stdout=DEVNULL,
                stderr=DEVNULL,
            )
            node.run('yarn', 'add', 'pyright', cwd=tmpdir, check=True)
        binary = Path(tmpdir) / 'node_modules' / 'pyright' / 'langserver.index.js'

        if not binary.exists():
            raise RuntimeError(
                f'Expected language server entrypoint: {binary} to exist'
            )
        retcode = node.run('node', binary, '--', *args, **kwargs)
    return retcode


def entrypoint() -> NoReturn:
    exit(main(*argv[1:]))


if __name__ == '__main__':
    entrypoint()
