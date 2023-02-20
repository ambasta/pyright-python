from types import UnionType
from typing import List, Literal, get_args

Host = Literal['aix'] | Literal['linux'] | Literal['osx'] | Literal['win']

PackageManager = Literal['yarn'] | Literal['yarnpkg'] | Literal['pnpm'] | Literal['npm']

Architecture = (
    Literal['x86']
    | Literal['x64']
    | Literal['armv6l']
    | Literal['armv7l']
    | Literal['armv7l']
    | Literal['arm64']
    | Literal['ppc64le']
    | Literal['s390x']
)


def literal_union_to_strlst(union_types: UnionType) -> List[str]:
    values: List[str] = []

    for value_type in get_args(union_types):
        for value in get_args(value_type):
            if value:
                values.append(value)
    return values
