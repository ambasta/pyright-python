from typing import Iterable, Optional

from pyright.types import PackageManager


class PyrightError(Exception):
    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NodeError(PyrightError):
    pass


class NoUsablePackageManager(PyrightError):
    pass


class UnsupportedPackageManager(PyrightError):
    def __init__(self, manager: Optional[str], supported: Iterable[PackageManager]):
        super().__init__(
            f'Unsupported package manager `{manager}` specified. Supported pacakge managers are ${", ".join(supported)}'
        )
        pass


class VersionCheckFailed(NodeError):
    pass
