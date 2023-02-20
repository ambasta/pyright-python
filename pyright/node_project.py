from logging import DEBUG, Formatter, StreamHandler, getLogger
from os import getenv, remove, rmdir, stat
from os.path import exists, isfile
from pathlib import Path
from shutil import which
from subprocess import DEVNULL, Popen, run
from typing import Optional, OrderedDict, cast

from .errors import UnsupportedPackageManager
from .nodejs import NodeJS
from .types import PackageManager, literal_union_to_strlst

LOGGER = getLogger(__name__)
LOGGER.setLevel(DEBUG)

LOG_HANDLER = StreamHandler()
LOG_HANDLER.setLevel(DEBUG)

LOG_FORMATTER = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_HANDLER.setFormatter(LOG_FORMATTER)
LOGGER.addHandler(LOG_HANDLER)


class NodeProject:
    _managers: OrderedDict[PackageManager, Path] = OrderedDict()
    _pkg_manager: Path
    _project_root: Path

    def _detect_availale_pkg_managers(self, path: Optional[Path] = None):
        for manager in literal_union_to_strlst(PackageManager):
            manager_path = which(manager, path=path)

            if manager_path:
                LOGGER.info(
                    f'Found package manager {manager}"" at path "{manager_path}"'
                )
                self._managers[cast(PackageManager, manager)] = Path(manager_path)

    def _ensure_pkg_manager(self, pkg_manager: str):
        if which(pkg_manager) is None:
            raise RuntimeError(f'Package manager {pkg_manager} not found')

    def _detect_pkg_manager(self):
        pkg_manager = getenv('NODE_PKG_MANAGER')

        if pkg_manager is None and len(self._managers) == 0:
            raise RuntimeError('No usable package managers found')
        pkg_manager = pkg_manager or next(iter(self._managers))

        if pkg_manager not in self._managers:
            raise UnsupportedPackageManager(pkg_manager, self._managers.keys())
        pkg_manager = pkg_manager or next(iter(self._managers))
        self._pkg_manager = self._managers[pkg_manager]
        LOGGER.debug(f'Using package manager {pkg_manager} at {self._pkg_manager}')

    def _setup_node(self):
        nodejs = NodeJS(self._project_root)
        nodejs._setup_node(nodejs.node_latest['version'])
        self._detect_availale_pkg_managers(nodejs.node_path)

    @property
    def _is_yarn(self) -> bool:
        return self._pkg_manager.name in ['yarn', 'yarnpkg']

    @property
    def _is_npm(self) -> bool:
        return self._pkg_manager.name == 'npm'

    def __init__(self, path: Path) -> None:
        self._project_root = path
        nodejs = NodeJS(self._project_root)
        self._pkg_json_path = self._project_root / 'package.json'

        if nodejs.node_path is None:
            raise Exception('No valid nodejs found')
        self._detect_availale_pkg_managers(nodejs.node_path.parent)
        self._detect_pkg_manager()
        self._initialize_if_needed()

    def _initialize_if_needed(self):
        needs_initialization: bool = False

        if exists(self._pkg_json_path):
            LOGGER.debug(f'Found existing package.json at {self._pkg_json_path}')

            if isfile(self._pkg_json_path):
                if stat(self._pkg_json_path).st_size == 0:
                    LOGGER.debug(f'"{self._pkg_json_path}" is an empty file. removing')
                    remove(self._pkg_json_path)
                    needs_initialization = True
            else:
                LOGGER.debug(f'"{self._pkg_json_path}" is a directory. removing')
                rmdir(self._pkg_json_path)
                needs_initialization = True
        else:
            LOGGER.debug(
                f'No existing package.json at {self._pkg_json_path}. Will initialize'
            )
            needs_initialization = True

        if needs_initialization:
            self._initialize_project()

    def _initialize_project(self):
        LOGGER.debug(
            f'Running command {self._pkg_manager} init -y -2 in {self._project_root}'
        )
        init_process = Popen(
            [self._pkg_manager, 'init', '-y', '-2'],
            cwd=self._project_root,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        init_process.wait()

    def add_dependency(self, dep: str, unplug: bool = False):
        install_keyword = 'add' if self._is_yarn else 'install'
        LOGGER.debug(
            f'Running command {self._pkg_manager} {install_keyword} {dep} in {self._project_root}'
        )
        init_process = Popen(
            [self._pkg_manager, install_keyword, dep],
            cwd=self._project_root,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        init_process.wait()

        if unplug and self._is_yarn:
            LOGGER.debug(
                f'Running command {self._pkg_manager} unplug {dep} in {self._project_root}'
            )
            unplug_process = Popen(
                [self._pkg_manager, 'unplug', dep],
                cwd=self._project_root,
                stdout=DEVNULL,
                stderr=DEVNULL,
            )
            unplug_process.wait()

    def bootstrap(self):
        LOGGER.debug(
            f'Running command {self._pkg_manager} install in {self._project_root}'
        )
        install_process = Popen(
            [self._pkg_manager, 'install'],
            cwd=self._project_root,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        install_process.wait()

    def run(self, binary: str, *args: str):
        runner = self._pkg_manager

        if self._is_npm:
            runner = self._pkg_manager.parent / 'npx'
        LOGGER.debug(
            f'Running command {runner} {binary} {args} in {self._project_root}'
        )
        return run([runner, binary, *args], cwd=self._project_root)
