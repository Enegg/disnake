# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .asset import Asset
from .colour import Colour
from .flags import RoleFlags
from .mixins import Hashable
from .partial_emoji import PartialEmoji
from .permissions import Permissions
from .utils import MISSING, _get_as_snowflake, snowflake_time

__all__ = (
    "RoleTags",
    "Role",
)

if TYPE_CHECKING:
    import datetime

    from typing_extensions import Self

    from .guild import Guild
    from .member import Member
    from .state import ConnectionState
    from .types.role import Role as RolePayload, RoleTags as RoleTagPayload


class RoleTags:
    """Represents tags on a role.

    A role tag is a piece of extra information attached to a managed role
    that gives it context for the reason the role is managed.

    While this can be accessed, a useful interface is also provided in the
    :class:`Role` and :class:`Guild` classes as well.

    .. versionadded:: 1.6

    Attributes
    ----------
    bot_id: :class:`int` | :data:`None`
        The bot's user ID that manages this role.
    integration_id: :class:`int` | :data:`None`
        The integration ID that manages the role.

        Roles with this ID matching the guild's ``guild_subscription`` integration
        are considered subscription roles.
    subscription_listing_id: :class:`int` | :data:`None`
        The ID of this role's subscription listing, if applicable.

        .. versionadded:: 2.9
    """

    __slots__ = (
        "bot_id",
        "integration_id",
        "subscription_listing_id",
        "_premium_subscriber",
        "_guild_connections",
        "_available_for_purchase",
    )

    def __init__(self, data: RoleTagPayload) -> None:
        self.bot_id: int | None = _get_as_snowflake(data, "bot_id")
        self.integration_id: int | None = _get_as_snowflake(data, "integration_id")
        self.subscription_listing_id: int | None = _get_as_snowflake(
            data, "subscription_listing_id"
        )

        # NOTE: A value of null/None for this corresponds to True.
        # If a field is missing, it corresponds to False.
        # This is different from other fields where "null" means "not there".
        self._premium_subscriber: Any | None = data.get("premium_subscriber", MISSING)
        self._guild_connections: Any | None = data.get("guild_connections", MISSING)
        self._available_for_purchase: Any | None = data.get("available_for_purchase", MISSING)

    def is_bot_managed(self) -> bool:
        """Whether the role is associated with a bot.

        :return type: :class:`bool`
        """
        return self.bot_id is not None

    def is_integration(self) -> bool:
        """Whether the role is managed by an integration.

        :return type: :class:`bool`
        """
        return self.integration_id is not None

    def is_premium_subscriber(self) -> bool:
        """Whether the role is the premium subscriber, AKA "boost", role for the guild.

        :return type: :class:`bool`
        """
        return self._premium_subscriber is None

    def is_linked_role(self) -> bool:
        """Whether the role is a linked role for the guild.

        .. versionadded:: 2.8

        :return type: :class:`bool`
        """
        return self._guild_connections is None

    def is_available_for_purchase(self) -> bool:
        """Whether the role is a subscription role and available for purchase.

        .. versionadded:: 2.9

        :return type: :class:`bool`
        """
        return self._available_for_purchase is None

    def is_subscription(self) -> bool:
        """Whether the role is associated with a role subscription.

        .. versionadded:: 2.9

        :return type: :class:`bool`
        """
        return self.subscription_listing_id is not None

    def __repr__(self) -> str:
        return (
            f"<RoleTags bot_id={self.bot_id} integration_id={self.integration_id} "
            f"subscription_listing_id={self.subscription_listing_id} "
            f"premium_subscriber={self.is_premium_subscriber()} "
            f"available_for_purchase={self.is_available_for_purchase()} "
            f"linked_role={self.is_linked_role()}>"
        )


class Role(Hashable):
    """Represents a Discord role in a :class:`Guild`.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two roles are equal.

        .. describe:: x != y

            Checks if two roles are not equal.

        .. describe:: x > y

            Checks if a role is higher than another in the hierarchy.

        .. describe:: x < y

            Checks if a role is lower than another in the hierarchy.

        .. describe:: x >= y

            Checks if a role is higher or equal to another in the hierarchy.

        .. describe:: x <= y

            Checks if a role is lower or equal to another in the hierarchy.

        .. describe:: hash(x)

            Return the role's hash.

        .. describe:: str(x)

            Returns the role's name.

    Attributes
    ----------
    id: :class:`int`
        The ID of the role.
    name: :class:`str`
        The name of the role.
    guild: :class:`Guild`
        The guild the role belongs to.
    hoist: :class:`bool`
         Indicates if the role will be displayed separately from other members.
    position: :class:`int`
        The position of the role. This number is usually positive. The bottom
        role has a position of 0.

        .. warning::

            Multiple roles can have the same position number. As a consequence
            of this, comparing via role position is prone to subtle bugs if
            checking for role hierarchy. The recommended and correct way to
            compare for roles in the hierarchy is using the comparison
            operators on the role objects themselves.
    managed: :class:`bool`
        Indicates if the role is managed by the guild through some form of
        integrations such as Twitch.
    mentionable: :class:`bool`
        Indicates if the role can be mentioned by users.
    tags: :class:`RoleTags` | :data:`None`
        The role tags associated with this role.
    """

    __slots__ = (
        "id",
        "name",
        "_permissions",
        "position",
        "managed",
        "mentionable",
        "hoist",
        "_icon",
        "_emoji",
        "guild",
        "tags",
        "_flags",
        "_state",
        "_primary_color",
        "_secondary_color",
        "_tertiary_color",
    )

    def __init__(self, *, guild: Guild, state: ConnectionState, data: RolePayload) -> None:
        self.guild: Guild = guild
        self._state: ConnectionState = state
        self.id: int = int(data["id"])
        self._update(data)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r}>"

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, Role) or not isinstance(self, Role):
            return NotImplemented

        if self.guild != other.guild:
            msg = "cannot compare roles from two different guilds."
            raise RuntimeError(msg)

        # the @everyone role is always the lowest role in hierarchy
        guild_id = self.guild.id
        if self.id == guild_id:
            # everyone_role < everyone_role -> False
            return other.id != guild_id

        if self.position < other.position:
            return True

        if self.position == other.position:
            return int(self.id) > int(other.id)

        return False

    def __le__(self, other: Self) -> bool:
        r = Role.__lt__(other, self)
        if r is NotImplemented:
            return NotImplemented
        return not r

    def __gt__(self, other: Self) -> bool:
        return Role.__lt__(other, self)

    def __ge__(self, other: Self) -> bool:
        r = Role.__lt__(self, other)
        if r is NotImplemented:
            return NotImplemented
        return not r

    def _update(self, data: RolePayload) -> None:
        self.name: str = data["name"]
        self._permissions: int = int(data.get("permissions", 0))
        self.position: int = data.get("position", 0)
        colors = data["colors"]
        self._primary_color: int = colors["primary_color"]
        self._secondary_color: int | None = colors["secondary_color"]
        self._tertiary_color: int | None = colors["tertiary_color"]
        self.hoist: bool = data.get("hoist", False)
        self._icon: str | None = data.get("icon")
        self._emoji: str | None = data.get("unicode_emoji")
        self.managed: bool = data.get("managed", False)
        self.mentionable: bool = data.get("mentionable", False)

        self.tags: RoleTags | None = None
        if "tags" in data:
            self.tags = RoleTags(data["tags"])

        self._flags: int = data.get("flags", 0)

    def is_default(self) -> bool:
        """Checks if the role is the default role.

        :return type: :class:`bool`
        """
        return self.guild.id == self.id

    def is_bot_managed(self) -> bool:
        """Whether the role is associated with a bot.

        .. versionadded:: 1.6

        :return type: :class:`bool`
        """
        return self.tags is not None and self.tags.is_bot_managed()

    def is_premium_subscriber(self) -> bool:
        """Whether the role is the premium subscriber, AKA "boost", role for the guild.

        .. versionadded:: 1.6

        :return type: :class:`bool`
        """
        return self.tags is not None and self.tags.is_premium_subscriber()

    def is_linked_role(self) -> bool:
        """Whether the role is a linked role for the guild.

        .. versionadded:: 2.8

        :return type: :class:`bool`
        """
        return self.tags is not None and self.tags.is_linked_role()

    def is_integration(self) -> bool:
        """Whether the role is managed by an integration.

        .. versionadded:: 1.6

        :return type: :class:`bool`
        """
        return self.tags is not None and self.tags.is_integration()

    def is_available_for_purchase(self) -> bool:
        """Whether the role is a subscription role and available for purchase.

        .. versionadded:: 2.9

        :return type: :class:`bool`
        """
        return self.tags is not None and self.tags.is_available_for_purchase()

    def is_subscription(self) -> bool:
        """Whether the role is associated with a role subscription.

        .. versionadded:: 2.9

        :return type: :class:`bool`
        """
        return self.tags is not None and self.tags.is_subscription()

    def is_assignable(self) -> bool:
        """Whether the role is able to be assigned or removed by the bot.

        .. versionadded:: 2.0

        :return type: :class:`bool`
        """
        me = self.guild.me
        return (
            not self.is_default()
            and not self.managed
            and (me.top_role > self or me.id == self.guild.owner_id)
        )

    @property
    def permissions(self) -> Permissions:
        """:class:`Permissions`: Returns the role's permissions."""
        return Permissions(self._permissions)

    @property
    def colour(self) -> Colour:
        """:class:`Colour`: Returns the role colour. An alias exists under ``color``.

        .. note::

            This is equivalent to :meth:`primary_colour`.
        """
        return self.primary_colour

    @property
    def color(self) -> Colour:
        """:class:`Colour`: Returns the role color. An alias exists under ``colour``.

        .. note::

            This is equivalent to :meth:`primary_color`.
        """
        return self.primary_colour

    @property
    def primary_colour(self) -> Colour:
        """:class:`Colour`: Returns the primary colour for the role. An alias exists under ``primary_color``.

        .. versionadded:: 2.11
        """
        return Colour(self._primary_color)

    @property
    def primary_color(self) -> Colour:
        """:class:`Colour`: Returns the primary color for the role. An alias exists under ``primary_colour``.

        .. versionadded:: 2.11
        """
        return self.primary_colour

    @property
    def secondary_colour(self) -> Colour | None:
        """:class:`Colour` | :data:`None`: Returns the secondary colour for the role, if any. An alias exists under ``secondary_color``.

        .. versionadded:: 2.11
        """
        if self._secondary_color:
            return Colour(self._secondary_color)
        return None

    @property
    def secondary_color(self) -> Colour | None:
        """:class:`Colour` | :data:`None`: Returns the secondary color for the role, if any. An alias exists under ``secondary_colour``.

        .. versionadded:: 2.11
        """
        return self.secondary_colour

    @property
    def tertiary_colour(self) -> Colour | None:
        """:class:`Colour` | :data:`None`: Returns the tertiary colour for the role, if any. An alias exists under ``tertiary_color``.

        .. versionadded:: 2.11
        """
        if self._tertiary_color:
            return Colour(self._tertiary_color)
        return None

    @property
    def tertiary_color(self) -> Colour | None:
        """:class:`Colour` | :data:`None`: Returns the tertiary color for the role, if any. An alias exists under ``tertiary_colour``.

        .. versionadded:: 2.11
        """
        return self.tertiary_colour

    @property
    def icon(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns the role's icon asset, if available.

        .. versionadded:: 2.0
        """
        if self._icon is None:
            return None
        return Asset._from_role_icon(self._state, self.id, self._icon)

    @property
    def emoji(self) -> PartialEmoji | None:
        """:class:`PartialEmoji` | :data:`None`: Returns the role's emoji, if available.

        .. versionadded:: 2.0
        """
        if self._emoji is None:
            return None
        return PartialEmoji(name=self._emoji)

    @property
    def flags(self) -> RoleFlags:
        """:class:`RoleFlags`: Returns the role's flags.

        .. versionadded:: 2.10
        """
        return RoleFlags._from_value(self._flags)

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns the role's creation time in UTC."""
        return snowflake_time(self.id)

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention a role."""
        if self.is_default():
            return "@everyone"
        return f"<@&{self.id}>"

    @property
    def members(self) -> list[Member]:
        r""":class:`list`\[:class:`Member`]: Returns all the members with this role."""
        all_members = self.guild.members
        if self.is_default():
            return all_members

        role_id = self.id
        return [member for member in all_members if member._roles.has(role_id)]
