# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from .appinfo import PartialAppInfo
from .asset import Asset
from .enums import ChannelType, InviteTarget, InviteType, try_enum
from .mixins import Hashable
from .object import Object
from .utils import _get_as_snowflake, parse_time, snowflake_time

__all__ = ("PartialInviteChannel", "Invite")

if TYPE_CHECKING:
    import datetime

    from typing_extensions import Self

    from .abc import GuildChannel
    from .guild import Guild
    from .state import ConnectionState
    from .types.channel import (
        GroupInviteRecipient as GroupInviteRecipientPayload,
        InviteChannel as InviteChannelPayload,
    )
    from .types.gateway import InviteCreateEvent, InviteDeleteEvent
    from .types.invite import Invite as InvitePayload
    from .user import User

    GatewayInvitePayload: TypeAlias = InviteCreateEvent | InviteDeleteEvent
    InviteGuildType: TypeAlias = "Guild | Object"
    InviteChannelType: TypeAlias = "GuildChannel | PartialInviteChannel | Object"


class PartialInviteChannel:
    """Represents a "partial" invite channel.

    This model will be given when the user is not part of the
    guild the :class:`Invite` resolves to.


    .. collapse:: operations

        .. describe:: x == y

            Checks if two partial channels are the same.

        .. describe:: x != y

            Checks if two partial channels are not the same.

        .. describe:: hash(x)

            Return the partial channel's hash.

        .. describe:: str(x)

            Returns the partial channel's name.

            .. versionchanged:: 2.5
                if the channel is of type :attr:`ChannelType.group`,
                returns the name that's rendered by the official client.

    Attributes
    ----------
    name: :class:`str` | :data:`None`
        The partial channel's name.
    id: :class:`int`
        The partial channel's ID.
    type: :class:`ChannelType`
        The partial channel's type.
    """

    __slots__ = (
        "id",
        "name",
        "type",
        "_recipients",
        "_icon",
        "_state",
    )

    def __init__(self, *, state: ConnectionState, data: InviteChannelPayload) -> None:
        self._state = state
        self.id: int = int(data["id"])
        self.name: str | None = data.get("name")
        self.type: ChannelType = try_enum(ChannelType, data["type"])
        if self.type is ChannelType.group:
            self._recipients: list[GroupInviteRecipientPayload] = data.get("recipients", [])
        else:
            self._recipients = []
        self._icon: str | None = data.get("icon")

    def __str__(self) -> str:
        if self.name:
            return self.name
        if self.type is ChannelType.group:
            return ", ".join([recipient["username"] for recipient in self._recipients]) or "Unnamed"
        return ""

    def __repr__(self) -> str:
        return f"<PartialInviteChannel id={self.id} name={self.name} type={self.type!r}>"

    @property
    def mention(self) -> str:
        """:class:`str`: The string that allows you to mention the channel."""
        return f"<#{self.id}>"

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns the channel's creation time in UTC."""
        return snowflake_time(self.id)

    @property
    def icon(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns the channel's icon asset if available.

        .. versionadded:: 2.6
        """
        if self._icon is None:
            return None
        return Asset._from_icon(self._state, self.id, self._icon, path="channel")


class Invite(Hashable):
    """Represents a Discord :class:`Guild` or :class:`abc.GuildChannel` invite.

    Depending on the way this object was created, some of the attributes can
    have a value of :data:`None` (see table below).

    .. collapse:: operations

        .. describe:: x == y

            Checks if two invites are equal.

        .. describe:: x != y

            Checks if two invites are not equal.

        .. describe:: hash(x)

            Returns the invite hash.

        .. describe:: str(x)

            Returns the invite URL.

    .. _invite_attr_table:

    The following table illustrates what methods will obtain the attributes:

    +------------------------------------+---------------------------------------------------------------------+
    |             Attribute              |                          Method                                     |
    +====================================+=====================================================================+
    | :attr:`max_age`                    | :meth:`Guild.invites` with :attr:`~Permissions.manage_guild`        |
    |                                    | permissions, :meth:`abc.GuildChannel.invites`                       |
    +------------------------------------+---------------------------------------------------------------------+
    | :attr:`max_uses`                   | :meth:`Guild.invites` with :attr:`~Permissions.manage_guild`        |
    |                                    | permissions, :meth:`abc.GuildChannel.invites`                       |
    +------------------------------------+---------------------------------------------------------------------+
    | :attr:`created_at`                 | :meth:`Guild.invites` with :attr:`~Permissions.manage_guild`        |
    |                                    | permissions, :meth:`abc.GuildChannel.invites`                       |
    +------------------------------------+---------------------------------------------------------------------+
    | :attr:`temporary`                  | :meth:`Guild.invites` with :attr:`~Permissions.manage_guild`        |
    |                                    | permissions, :meth:`abc.GuildChannel.invites`                       |
    +------------------------------------+---------------------------------------------------------------------+
    | :attr:`uses`                       | :meth:`Guild.invites` with :attr:`~Permissions.manage_guild`        |
    |                                    | permissions, :meth:`abc.GuildChannel.invites`                       |
    +------------------------------------+---------------------------------------------------------------------+
    | :attr:`approximate_member_count`   | :meth:`Client.fetch_invite` with ``with_counts`` enabled            |
    +------------------------------------+---------------------------------------------------------------------+
    | :attr:`approximate_presence_count` | :meth:`Client.fetch_invite` with ``with_counts`` enabled            |
    +------------------------------------+---------------------------------------------------------------------+
    | :attr:`guild_scheduled_event`      | :meth:`Client.fetch_invite` with valid ``guild_scheduled_event_id`` |
    |                                    | or valid event ID in URL or invite object                           |
    +------------------------------------+---------------------------------------------------------------------+

    If something is not in the table above, then it's available by all methods.

    Attributes
    ----------
    code: :class:`str`
        The URL fragment used for the invite.
    type: :class:`InviteType`
        The type of the invite.

        .. versionadded:: 2.10

    guild: :class:`Guild` | :class:`Object` | :class:`PartialInviteGuild` | :data:`None`
        The guild the invite is for. Can be :data:`None` if it's not a guild invite (see :attr:`type`).
    max_age: :class:`int` | :data:`None`
        How long before the invite expires in seconds.
        A value of ``0`` indicates that it doesn't expire.

        Optional according to the :ref:`table <invite_attr_table>` above.
    max_uses: :class:`int` | :data:`None`
        How many times the invite can be used.
        A value of ``0`` indicates that it has unlimited uses.

        Optional according to the :ref:`table <invite_attr_table>` above.
    created_at: :class:`datetime.datetime` | :data:`None`
        An aware UTC datetime object denoting the time the invite was created.

        Optional according to the :ref:`table <invite_attr_table>` above.
    temporary: :class:`bool` | :data:`None`
        Whether the invite grants temporary membership.
        If ``True``, members who joined via this invite will be kicked upon disconnect.

        Optional according to the :ref:`table <invite_attr_table>` above.
    uses: :class:`int` | :data:`None`
        How many times the invite has been used.

        Optional according to the :ref:`table <invite_attr_table>` above.
    approximate_member_count: :class:`int` | :data:`None`
        The approximate number of members in the guild.

        Optional according to the :ref:`table <invite_attr_table>` above.
    approximate_presence_count: :class:`int` | :data:`None`
        The approximate number of members currently active in the guild.
        This includes idle, dnd, online, and invisible members. Offline members are excluded.

        Optional according to the :ref:`table <invite_attr_table>` above.
    expires_at: :class:`datetime.datetime` | :data:`None`
        The expiration date of the invite. If the value is :data:`None` the invite will never expire.

        .. versionadded:: 2.0

    inviter: :class:`User` | :data:`None`
        The user who created the invite, if any.

        This is :data:`None` in vanity invites, for example.
    channel: :class:`abc.GuildChannel` | :class:`Object` | :class:`PartialInviteChannel` | :data:`None`
        The channel the invite is for.
    target_type: :class:`InviteTarget`
        The type of target for the voice channel invite.

        .. versionadded:: 2.0

    target_user: :class:`User` | :data:`None`
        The user whose stream to display for this invite, if any.

        .. versionadded:: 2.0

    target_application: :class:`PartialAppInfo` | :data:`None`
        The embedded application the invite targets, if any.

        .. versionadded:: 2.0

    guild_scheduled_event: :class:`GuildScheduledEvent` | :data:`None`
        The guild scheduled event included in the invite, if any.

        .. versionadded:: 2.3

    guild_welcome_screen: :class:`WelcomeScreen` | :data:`None`
        The partial guild's welcome screen, if any.

        .. versionadded:: 2.5
    """

    __slots__ = (
        "max_age",
        "code",
        "type",
        "guild",
        "created_at",
        "uses",
        "temporary",
        "max_uses",
        "inviter",
        "channel",
        "target_user",
        "target_type",
        "approximate_member_count",
        "approximate_presence_count",
        "target_application",
        "expires_at",
        "guild_scheduled_event",
        "guild_welcome_screen",
        "_state",
    )

    BASE = "https://discord.gg"

    def __init__(
        self,
        *,
        state: ConnectionState,
        data: InvitePayload | GatewayInvitePayload,
        guild: Guild | None = None,
        channel: PartialInviteChannel | GuildChannel | None = None,
    ) -> None:
        self._state: ConnectionState = state
        self.code: str = data["code"]
        self.type: InviteType = try_enum(InviteType, data.get("type", 0))
        self.guild: InviteGuildType | None = None

        self.max_age: int | None = data.get("max_age")
        self.max_uses: int | None = data.get("max_uses")
        self.created_at: datetime.datetime | None = parse_time(data.get("created_at"))
        self.temporary: bool | None = data.get("temporary")
        self.uses: int | None = data.get("uses")
        self.approximate_presence_count: int | None = data.get("approximate_presence_count")
        self.approximate_member_count: int | None = data.get("approximate_member_count")

        expires_at = data.get("expires_at", None)
        self.expires_at: datetime.datetime | None = parse_time(expires_at) if expires_at else None

        inviter_data = data.get("inviter")
        self.inviter: User | None = (
            None if inviter_data is None else self._state.create_user(inviter_data)  # pyright: ignore[reportArgumentType]
        )

        self.channel: InviteChannelType | None = self._resolve_channel(data.get("channel"), channel)

        target_user_data = data.get("target_user")
        self.target_user: User | None = (
            None if target_user_data is None else self._state.create_user(target_user_data)  # pyright: ignore[reportArgumentType]
        )

        self.target_type: InviteTarget = try_enum(InviteTarget, data.get("target_type", 0))

        application = data.get("target_application")
        self.target_application: PartialAppInfo | None = (
            PartialAppInfo(data=application, state=state) if application else None
        )

    @classmethod
    def from_incomplete(cls, *, state: ConnectionState, data: InvitePayload) -> Self:
        guild: Guild | None = None

        channel: PartialInviteChannel | GuildChannel | None = None
        if channel_data := data.get("channel"):
            channel = PartialInviteChannel(data=channel_data, state=state)

        return cls(state=state, data=data, guild=guild, channel=channel)

    @classmethod
    def from_gateway(cls, *, state: ConnectionState, data: GatewayInvitePayload) -> Self:
        guild_id: int | None = _get_as_snowflake(data, "guild_id")
        guild: Guild | Object | None = state._get_guild(guild_id)
        channel_id = int(data["channel_id"])
        if guild is not None:
            channel = guild.get_channel(channel_id) or Object(id=channel_id)
        else:
            guild = Object(id=guild_id) if guild_id is not None else None
            channel = Object(id=channel_id)

        return cls(
            state=state,
            data=data,
            # objects may be partial due to missing cache
            guild=guild,  # pyright: ignore[reportArgumentType]
            channel=channel,  # pyright: ignore[reportArgumentType]
        )

    def _resolve_channel(
        self,
        data: InviteChannelPayload | None,
        channel: PartialInviteChannel | GuildChannel | None = None,
    ) -> InviteChannelType | None:
        if channel is not None:
            return channel

        if data is None:
            return None

        return PartialInviteChannel(data=data, state=self._state)

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
        s = f"<Invite code={self.code!r} type={self.type!r}"
        if self.type is InviteType.guild:
            s += f" guild={self.guild!r} online={self.approximate_presence_count}"
        if self.type is not InviteType.friend:
            s += f" members={self.approximate_member_count}"
        s += ">"
        return s

    def __hash__(self) -> int:
        return hash(self.code)

    @property
    def id(self) -> str:
        """:class:`str`: Returns the proper code portion of the invite."""
        return self.code

    @property
    def url(self) -> str:
        """:class:`str`: A property that retrieves the invite URL."""
        url = f"{self.BASE}/{self.code}"
        if self.guild_scheduled_event:
            url += f"?event={self.guild_scheduled_event.id}"
        return url
