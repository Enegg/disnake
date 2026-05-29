# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

__all__ = ("UIComponent", "WrappedComponent")

if TYPE_CHECKING:
    from typing_extensions import Self

    from ..components import ActionRowChildComponent, Component
    from ..enums import ComponentType
    from ..types.components import ActionRowChildComponent as ActionRowChildComponentPayload

UIComponentT = TypeVar("UIComponentT", bound="UIComponent")


def ensure_ui_component(obj: UIComponentT, name: str = "component") -> UIComponentT:
    if not isinstance(obj, UIComponent):
        msg = f"{name} should be a valid UI component, got {type(obj).__name__}."
        raise TypeError(msg)
    return obj


class UIComponent(ABC):
    """Represents the base UI component that all UI components inherit from.

    The following classes implement this ABC:

    - :class:`disnake.ui.ActionRow`
    - :class:`disnake.ui.Button`
    - subtypes of :class:`disnake.ui.BaseSelect` (:class:`disnake.ui.ChannelSelect`, :class:`disnake.ui.MentionableSelect`, :class:`disnake.ui.RoleSelect`, :class:`disnake.ui.StringSelect`, :class:`disnake.ui.UserSelect`)
    - :class:`disnake.ui.TextInput`
    - :class:`disnake.ui.Section`
    - :class:`disnake.ui.TextDisplay`
    - :class:`disnake.ui.Thumbnail`
    - :class:`disnake.ui.MediaGallery`
    - :class:`disnake.ui.File`
    - :class:`disnake.ui.Separator`
    - :class:`disnake.ui.Container`
    - :class:`disnake.ui.Label`
    - :class:`disnake.ui.FileUpload`
    - :class:`disnake.ui.RadioGroup`
    - :class:`disnake.ui.CheckboxGroup`
    - :class:`disnake.ui.Checkbox`

    .. versionadded:: 2.11
    """

    __repr_attributes__: ClassVar[tuple[str, ...]]

    @property
    @abstractmethod
    def _underlying(self) -> Component: ...

    def __repr__(self) -> str:
        attrs = " ".join(
            f"{key.lstrip('_')}={getattr(self, key)!r}" for key in self.__repr_attributes__
        )
        return f"<{type(self).__name__} {attrs}>"

    @property
    def is_v2(self) -> bool:
        return self._underlying.is_v2

    @property
    def type(self) -> ComponentType:
        return self._underlying.type

    @property
    def id(self) -> int:
        """:class:`int`: The numeric identifier for the component.
        Must be unique within a message or modal.
        This is always present in components received from the API.

        .. versionadded:: 2.11
        """
        return self._underlying.id

    @id.setter
    def id(self, value: int) -> None:
        self._underlying.id = value

    def to_component_dict(self) -> dict[str, Any]:
        return self._underlying.to_dict()

    @classmethod
    def from_component(cls, component: Component, /) -> Self:
        return cls()


# Essentially the same as the base `UIComponent`, with the addition of `width`.
class WrappedComponent(UIComponent):
    r"""Represents the base UI component that all :class:`ActionRow`\-compatible
    UI components inherit from.

    This class adds more functionality on top of the :class:`UIComponent` base class,
    specifically for action rows.

    The following classes implement this ABC:

    - :class:`disnake.ui.Button`
    - subtypes of :class:`disnake.ui.BaseSelect` (:class:`disnake.ui.ChannelSelect`, :class:`disnake.ui.MentionableSelect`, :class:`disnake.ui.RoleSelect`, :class:`disnake.ui.StringSelect`, :class:`disnake.ui.UserSelect`)
    - :class:`disnake.ui.TextInput`

    .. versionadded:: 2.4
    """

    # the purpose of these two is just more precise typechecking compared to the base type
    if TYPE_CHECKING:

        @property
        @abstractmethod
        def _underlying(self) -> ActionRowChildComponent: ...

        def to_component_dict(self) -> ActionRowChildComponentPayload: ...

    @property
    @abstractmethod
    def width(self) -> int: ...
