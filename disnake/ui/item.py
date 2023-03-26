# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Generic,
    Optional,
    Protocol,
    Tuple,
    overload,
)

__all__ = ("Item", "WrappedComponent")

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, Self, TypeVar

    from ..components import Componentish, MessageComponent
    from ..enums import ComponentType
    from ..interactions import MessageInteraction
    from ..types.components import ConstrainedComponentPayloadT
    from ..types.components import MessageComponentPayload
    from .view import View

else:
    from typing import TypeVar
    ParamSpec = TypeVar

V = TypeVar("V", bound="Optional[View]", infer_variance=True, default=None)
I = TypeVar("I", bound="Item", infer_variance=True)
ItemCallbackType = Callable[[Any, I, MessageInteraction], Coroutine[Any, Any, Any]]


class Itemish(Componentish[ConstrainedComponentPayloadT], Protocol[ConstrainedComponentPayloadT]):
    @property
    def _underlying(self) -> Componentish[ConstrainedComponentPayloadT]:
        ...

    @property
    def width(self) -> int:
        ...


class WrappedComponent(ABC, Generic[ConstrainedComponentPayloadT]):
    """Represents the base UI component that all UI components inherit from.

    The following classes implement this ABC:

    - :class:`disnake.ui.Button`
    - subtypes of :class:`disnake.ui.BaseSelect` (:class:`disnake.ui.ChannelSelect`, :class:`disnake.ui.MentionableSelect`, :class:`disnake.ui.RoleSelect`, :class:`disnake.ui.StringSelect`, :class:`disnake.ui.UserSelect`)
    - :class:`disnake.ui.TextInput`

    .. versionadded:: 2.4
    """

    __repr_attributes__: Tuple[str, ...]

    @property
    @abstractmethod
    def _underlying(self) -> Componentish[ConstrainedComponentPayloadT]:
        ...

    @property
    @abstractmethod
    def width(self) -> int:
        ...

    def __repr__(self) -> str:
        attrs = " ".join(f"{key}={getattr(self, key)!r}" for key in self.__repr_attributes__)
        return f"<{type(self).__name__} {attrs}>"

    @property
    def type(self) -> ComponentType:
        return self._underlying.type

    def to_dict(self) -> ConstrainedComponentPayloadT:
        return self._underlying.to_dict()


class Item(WrappedComponent[MessageComponentPayload], Generic[V]):
    """Represents the base UI item that all UI items inherit from.

    This class adds more functionality on top of the :class:`WrappedComponent` base class.
    This functionality mostly relates to :class:`disnake.ui.View`.

    The current UI items supported are:

    - :class:`disnake.ui.Button`
    - subtypes of :class:`disnake.ui.BaseSelect` (:class:`disnake.ui.ChannelSelect`, :class:`disnake.ui.MentionableSelect`, :class:`disnake.ui.RoleSelect`, :class:`disnake.ui.StringSelect`, :class:`disnake.ui.UserSelect`)

    .. versionadded:: 2.0
    """

    __repr_attributes__: Tuple[str, ...] = ("row",)

    @overload
    def __init__(self: Item[None]) -> None:
        ...

    @overload
    def __init__(self: Item[V]) -> None:
        ...

    def __init__(self) -> None:
        self._view: V = None  # type: ignore
        self._row: Optional[int] = None
        self._rendered_row: Optional[int] = None
        # This works mostly well but there is a gotcha with
        # the interaction with from_component, since that technically provides
        # a custom_id most dispatchable items would get this set to True even though
        # it might not be provided by the library user. However, this edge case doesn't
        # actually affect the intended purpose of this check because from_component is
        # only called upon edit and we're mainly interested during initial creation time.
        self._provided_custom_id: bool = False

    def refresh_component(self, component: MessageComponent) -> None:
        return None

    def refresh_state(self, interaction: MessageInteraction) -> None:
        return None

    @classmethod
    def from_component(cls, component: MessageComponent) -> Self:
        return cls()

    @property
    def dispatchable(self) -> bool:
        return False

    @property
    def persistent(self) -> bool:
        return self._provided_custom_id

    @property
    def row(self) -> Optional[int]:
        return self._row

    @row.setter
    def row(self, value: Optional[int]) -> None:
        if value is None:
            self._row = None
        elif 5 > value >= 0:
            self._row = value
        else:
            raise ValueError("row cannot be negative or greater than or equal to 5")

    @property
    def view(self) -> V:
        """Optional[:class:`View`]: The underlying view for this item."""
        return self._view

    async def callback(self, interaction: MessageInteraction, /) -> None:
        """|coro|

        The callback associated with this UI item.

        This can be overriden by subclasses.

        Parameters
        ----------
        interaction: :class:`.MessageInteraction`
            The interaction that triggered this UI item.
        """
        pass


# while the decorators don't actually return a descriptor that matches this protocol,
# this protocol ensures that type checkers don't complain about statements like `self.button.disabled = True`,
# which work as `View.__init__` replaces the handler with the item
class DecoratedItem(Protocol[I]):
    @overload
    def __get__(self, obj: None, objtype: Any) -> ItemCallbackType:
        ...

    @overload
    def __get__(self, obj: Any, objtype: Any) -> I:
        ...


T = TypeVar("T", infer_variance=True)
P = ParamSpec("P")


class Object(Protocol[T, P]):
    def __new__(cls) -> T:
        ...

    def __init__(*args: P.args, **kwargs: P.kwargs) -> None:
        ...
