# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar

from ..components import Button as ButtonComponent
from ..enums import ButtonStyle, ComponentType
from ..partial_emoji import PartialEmoji, _EmojiTag
from ..utils import MISSING
from .item import WrappedComponent

__all__ = ("Button",)

if TYPE_CHECKING:
    from typing_extensions import Self

    from ..emoji import Emoji


class Button(WrappedComponent):
    """Represents a UI button.

    .. versionadded:: 2.0

    Parameters
    ----------
    style: :class:`disnake.ButtonStyle`
        The style of the button.
    custom_id: :class:`str` | :data:`None`
        The ID of the button that gets received during an interaction.
        If this button is for a URL or an SKU, it does not have a custom ID.
    url: :class:`str` | :data:`None`
        The URL this button sends you to.
    disabled: :class:`bool`
        Whether the button is disabled.
    label: :class:`str` | :data:`None`
        The label of the button, if any.
    emoji: :class:`.PartialEmoji` | :class:`.Emoji` | :class:`str` | :data:`None`
        The emoji of the button, if available.
    sku_id: :class:`int` | :data:`None`
        The ID of a purchasable SKU, for premium buttons.
        Premium buttons additionally cannot have a ``label``, ``url``, or ``emoji``.

        .. versionadded:: 2.11
    id: :class:`int`
        The numeric identifier for the component. Must be unique within a message.
        This is always present in components received from the API.
        If set to ``0`` (the default) when sending a component, the API will assign
        sequential identifiers to the components in the message.

        .. versionadded:: 2.11
    row: :class:`int` | :data:`None`
        The relative row this button belongs to. A Discord component can only have 5
        rows. By default, items are arranged automatically into those 5 rows. If you'd
        like to control the relative positioning of the row then passing an index is advised.
        For example, row=1 will show up before row=2. Defaults to :data:`None`, which is automatic
        ordering. The row number must be between 0 and 4 (i.e. zero indexed).
    """

    __repr_attributes__: ClassVar[tuple[str, ...]] = (
        "style",
        "url",
        "disabled",
        "label",
        "emoji",
        "sku_id",
        "row",
    )
    # We have to set this to MISSING in order to overwrite the abstract property from UIComponent
    _underlying: ButtonComponent = MISSING

    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.secondary,
        label: str | None = None,
        disabled: bool = False,
        custom_id: str | None = None,
        url: str | None = None,
        emoji: str | Emoji | PartialEmoji | None = None,
        sku_id: int | None = None,
        id: int = 0,
    ) -> None:
        super().__init__()

        self._provided_custom_id = custom_id is not None
        mutually_exclusive = 3 - (custom_id, url, sku_id).count(None)

        if mutually_exclusive == 0:
            custom_id = os.urandom(16).hex()
        elif mutually_exclusive != 1:
            msg = "cannot mix url, sku_id and custom_id with Button"
            raise TypeError(msg)

        if url is not None:
            style = ButtonStyle.link
        if sku_id is not None:
            style = ButtonStyle.premium

        if emoji is not None:
            if isinstance(emoji, str):
                emoji = PartialEmoji.from_str(emoji)
            elif isinstance(emoji, _EmojiTag):
                emoji = emoji._to_partial()
            else:
                msg = f"expected emoji to be str, Emoji, or PartialEmoji not {emoji.__class__}"
                raise TypeError(msg)

        self._underlying = ButtonComponent._raw_construct(
            type=ComponentType.button,
            id=id,
            custom_id=custom_id,
            url=url,
            disabled=disabled,
            label=label,
            style=style,
            emoji=emoji,
            sku_id=sku_id,
        )

    @property
    def width(self) -> int:
        return 1

    @property
    def style(self) -> ButtonStyle:
        """:class:`disnake.ButtonStyle`: The style of the button."""
        return self._underlying.style

    @style.setter
    def style(self, value: ButtonStyle) -> None:
        self._underlying.style = value

    @property
    def custom_id(self) -> str | None:
        """:class:`str` | :data:`None`: The ID of the button that gets received during an interaction.

        If this button is for a URL or an SKU, it does not have a custom ID.
        """
        return self._underlying.custom_id

    @custom_id.setter
    def custom_id(self, value: str | None) -> None:
        if value is not None and not isinstance(value, str):
            msg = "custom_id must be None or str"
            raise TypeError(msg)

        self._underlying.custom_id = value

    @property
    def url(self) -> str | None:
        """:class:`str` | :data:`None`: The URL this button sends you to."""
        return self._underlying.url

    @url.setter
    def url(self, value: str | None) -> None:
        if value is not None and not isinstance(value, str):
            msg = "url must be None or str"
            raise TypeError(msg)
        self._underlying.url = value

    @property
    def disabled(self) -> bool:
        """:class:`bool`: Whether the button is disabled."""
        return self._underlying.disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._underlying.disabled = bool(value)

    @property
    def label(self) -> str | None:
        """:class:`str` | :data:`None`: The label of the button, if available."""
        return self._underlying.label

    @label.setter
    def label(self, value: str | None) -> None:
        self._underlying.label = str(value) if value is not None else value

    @property
    def emoji(self) -> PartialEmoji | None:
        """:class:`.PartialEmoji` | :data:`None`: The emoji of the button, if available."""
        return self._underlying.emoji

    @emoji.setter
    def emoji(self, value: str | Emoji | PartialEmoji | None) -> None:
        if value is not None:
            if isinstance(value, str):
                self._underlying.emoji = PartialEmoji.from_str(value)
            elif isinstance(value, _EmojiTag):
                self._underlying.emoji = value._to_partial()
            else:
                msg = f"expected str, Emoji, or PartialEmoji, received {value.__class__} instead"
                raise TypeError(msg)
        else:
            self._underlying.emoji = None

    @property
    def sku_id(self) -> int | None:
        """:class:`int` | :data:`None`: The ID of a purchasable SKU, for premium buttons.

        .. versionadded:: 2.11
        """
        return self._underlying.sku_id

    @sku_id.setter
    def sku_id(self, value: int | None) -> None:
        if value is not None and not isinstance(value, int):
            msg = "sku_id must be None or int"
            raise TypeError(msg)
        self._underlying.sku_id = value

    @classmethod
    def from_component(cls, button: ButtonComponent) -> Self:
        return cls(
            style=button.style,
            label=button.label,
            disabled=button.disabled,
            custom_id=button.custom_id,
            url=button.url,
            emoji=button.emoji,
            sku_id=button.sku_id,
            id=button.id,
        )
