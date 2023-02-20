from logging import DEBUG, Formatter, StreamHandler, getLogger
from os import getenv
from pathlib import Path
from platform import machine, system
from shutil import which
from sysconfig import get_config_var
from tarfile import open
from typing import List, NotRequired, Optional, TypedDict, cast

from requests import get

from .types import Architecture, Host, literal_union_to_strlst

LOGGER = getLogger(__name__)
LOGGER.setLevel(DEBUG)

LOG_HANDLER = StreamHandler()
LOG_HANDLER.setLevel(DEBUG)

LOG_FORMATTER = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_HANDLER.setFormatter(LOG_FORMATTER)
LOGGER.addHandler(LOG_HANDLER)


class NodeVersion(TypedDict):
    version: str
    date: str
    npm: NotRequired[str]
    v8: str
    uv: NotRequired[str]
    zlib: NotRequired[str]
    openssl: NotRequired[str]
    modules: NotRequired[str]
    lts: bool
    security: bool
    files: List[str]


class NodeJS:
    _path: Path
    _src_proto: str = 'https'
    _bld_host: str = ''
    _src_host: str = 'nodejs.org'
    _src_path: str = '/download/release'
    _node_path: Optional[Path] = None
    _versions: List[NodeVersion]

    @property
    def is_x86_64_musl(self) -> bool:
        return get_config_var('HOST_GNU_TYPE') == 'x86_64-pc-linux-musl'

    @property
    def node_uri(self) -> str:
        return f'{self._src_proto}://{self._bld_host}{self._src_host}{self._src_path}'

    def _populate_versions(self) -> None:
        request = get(f'{self.node_uri}/index.json')
        request.raise_for_status()
        self._versions = request.json()

    @property
    def node_latest(self) -> NodeVersion:
        return self._versions[0]

    def node_bin_uri(self, version: str):
        host: str = system().lower()
        arch = machine()

        prefix: Optional[Host] = None
        postfix: Optional[str] = None
        suffix: Optional[Architecture] = None

        if host.startswith('linux'):
            prefix = 'linux'
        elif host.startswith('darwin'):
            prefix = 'osx'
        elif host.startswith('win') or host.startswith('cygwin'):
            prefix = 'win'

        if arch in literal_union_to_strlst(Architecture):
            suffix = cast(Architecture, arch)
        elif arch == 'x86_64':
            suffix = 'x64'
        elif (
            arch.startswith('aarch64')
            or arch.startswith('armv8')
            or arch.startswith('arm64')
        ):
            suffix = 'arm64'
        elif arch == 'i686':
            suffix = 'x86'
        elif arch.startswith('ppc64'):
            suffix = 'ppc64le'
        elif arch.startswith('s390x'):
            suffix = 's390x'

        if self.is_x86_64_musl:
            postfix = 'musl'

        components: List[Optional[str]] = [prefix, suffix, postfix]
        package_components: List[str] = [
            component for component in components if component
        ]
        package: str = '-'.join(package_components)
        filename: str = f'node-{version}-{package}'
        fileuri: str = f'{self.node_uri}/{version}/{filename}.tar.gz'

        return filename, fileuri

    def _setup_node(self, version: str):
        filename, fileuri = self.node_bin_uri(version)

        with get(fileuri, stream=True) as request, open(
            fileobj=request.raw, mode='r'
        ) as handle:
            request.raise_for_status()
            handle.extractall(self._path)
        self._node_path = self._path / f'{filename}' / 'bin' / 'node'

        if which(self._node_path) is None:
            raise Exception(
                'Unable to detect system-node or download a valid nodejs binary'
            )

    def _detect_system_node(self) -> None:
        node_path = which('node')

        if node_path:
            LOGGER.info(f'Found system node at: {node_path}')
            self._node_path = Path(node_path)

    @property
    def node_path(self) -> Optional[Path]:
        return self._node_path

    def __init__(self, path: Path):
        if self.is_x86_64_musl:
            self._bld_host = 'unofficial-builds.'
        self._path = path

        self._detect_system_node()
        force_prebuilt = getenv('PREBUILT') == '1'

        if self._node_path is None or force_prebuilt:
            LOGGER.info('Populating versions')
            self._populate_versions()
            LOGGER.info(
                f'Setting up NodeJS from remote with version {self.node_latest["version"]}'
            )
            self._setup_node(self.node_latest['version'])
