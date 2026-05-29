# SPDX-License-Identifier: MIT

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

if TYPE_CHECKING:
    from disnake import ApplicationCommandInteraction

    from .errors import CommandError

T = TypeVar("T")

FuncT = TypeVar("FuncT", bound=Callable[..., Any])

Coro: TypeAlias = Coroutine[Any, Any, T]
MaybeCoro: TypeAlias = T | Coro[T]
CoroFunc: TypeAlias = Callable[..., Coro[Any]]

AppCheck: TypeAlias = Callable[["ApplicationCommandInteraction"], MaybeCoro[bool]]
Hook: TypeAlias = Callable[["ApplicationCommandInteraction"], Coro[Any]]
Error: TypeAlias = Callable[["ApplicationCommandInteraction", "CommandError"], Coro[Any]]


# This is merely a tag type to avoid circular import issues.
# Yes, this is a terrible solution but ultimately it is the only solution.
class _BaseCommand:
    __slots__ = ()
