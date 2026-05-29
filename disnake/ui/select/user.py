# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, ClassVar

from ...abc import Snowflake
from ...components import UserSelectMenu
from ...enums import ComponentType, SelectDefaultValueType
from ...member import Member
from ...object import Object
from ...user import ClientUser, User
from ...utils import MISSING
from .base import BaseSelect, SelectDefaultValueInputType

if TYPE_CHECKING:
    from typing_extensions import Self


__all__ = ("UserSelect",)


class UserSelect(BaseSelect[UserSelectMenu, "User | Member"]):
    r"""Represents a UI user select menu.

    This is usually represented as a drop down menu.

    In order to get the selected items that the user has chosen, use :attr:`.values`.

    .. versionadded:: 2.7

    Parameters
    ----------
    custom_id: :class:`str`
        The ID of the select menu that gets received during an interaction.
        If not given then one is generated for you.
    placeholder: :class:`str` | :data:`None`
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    disabled: :class:`bool`
        Whether the select is disabled.
    default_values: :class:`~collections.abc.Sequence`\[:class:`~disnake.User` | :class:`.Member` | :class:`.SelectDefaultValue` | :class:`.Object`] | :data:`None`
        The list of values (users/members) that are selected by default.
        If set, the number of items must be within the bounds set by ``min_values`` and ``max_values``.

        .. versionadded:: 2.10
    required: :class:`bool`
        Whether the select menu is required. Only applies to components in modals.
        Defaults to ``True``.

        .. versionadded:: 2.11
    id: :class:`int`
        The numeric identifier for the component. Must be unique within a message or modal.
        This is always present in components received from the API.
        If set to ``0`` (the default) when sending a component, the API will assign
        sequential identifiers to the components in the message or modal.

        .. versionadded:: 2.11

    Attributes
    ----------
    values: :class:`list`\[:class:`~disnake.User`, :class:`.Member`]
        A list of users/members that have been selected by the user.
    """

    _default_value_type_map: ClassVar[
        Mapping[SelectDefaultValueType, tuple[type[Snowflake], ...]]
    ] = {
        SelectDefaultValueType.user: (Member, User, ClientUser, Object),
    }

    def __init__(
        self,
        *,
        custom_id: str = MISSING,
        placeholder: str | None = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        default_values: Sequence[SelectDefaultValueInputType[User | Member]] | None = None,
        required: bool = True,
        id: int = 0,
    ) -> None:
        super().__init__(
            UserSelectMenu,
            ComponentType.user_select,
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            default_values=default_values,
            required=required,
            id=id,
        )

    @classmethod
    def from_component(cls, component: UserSelectMenu) -> Self:
        return cls(
            custom_id=component.custom_id,
            placeholder=component.placeholder,
            min_values=component.min_values,
            max_values=component.max_values,
            disabled=component.disabled,
            default_values=component.default_values,
            required=component.required,
            id=component.id,
        )
