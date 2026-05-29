# SPDX-License-Identifier: MIT

from __future__ import annotations

import datetime
import itertools
import sys
from collections.abc import Callable
from operator import attrgetter
from typing import TYPE_CHECKING, Any, TypeAlias, cast, overload

import disnake.abc

from . import utils
from .activity import ActivityTypes, create_activity
from .asset import Asset, AssetBytes
from .colour import Colour
from .enums import Status, try_enum
from .flags import MemberFlags
from .permissions import Permissions
from .user import BaseUser, User, _UserTag
from .utils import MISSING, _assetbytes_to_base64_data

__all__ = (
    "VoiceState",
    "Member",
)

if TYPE_CHECKING:
    from typing_extensions import Self

    from .channel import DMChannel, StageChannel, VoiceChannel
    from .flags import PublicUserFlags
    from .guild import Guild
    from .message import Message
    from .partial_emoji import PartialEmoji
    from .role import Role
    from .state import ConnectionState
    from .types.activity import PresenceData
    from .types.gateway import GuildMemberUpdateEvent
    from .types.member import (
        BaseMember as BaseMemberPayload,
        Member as MemberPayload,
        MemberWithUser as MemberWithUserPayload,
        UserWithMember as UserWithMemberPayload,
    )
    from .types.user import AvatarDecorationData as AvatarDecorationDataPayload, User as UserPayload
    from .types.voice import (
        GuildVoiceState as GuildVoiceStatePayload,
        VoiceState as VoiceStatePayload,
    )
    from .user import Collectibles, PrimaryGuild

    VocalGuildChannel: TypeAlias = VoiceChannel | StageChannel


class VoiceState:
    """Represents a Discord user's voice state.

    Attributes
    ----------
    deaf: :class:`bool`
        Whether the user is currently deafened by the guild.
    mute: :class:`bool`
        Whether the user is currently muted by the guild.
    self_mute: :class:`bool`
        Whether the user is currently muted by their own accord.
    self_deaf: :class:`bool`
        Whether the user is currently deafened by their own accord.
    self_stream: :class:`bool`
        Whether the user is currently streaming via 'Go Live' feature.

        .. versionadded:: 1.3

    self_video: :class:`bool`
        Whether the user is currently broadcasting video.
    suppress: :class:`bool`
        Whether the user is suppressed from speaking.

        Only applies to stage channels.

        .. versionadded:: 1.7

    requested_to_speak_at: :class:`datetime.datetime` | :data:`None`
        An aware datetime object that specifies the date and time in UTC that the member
        requested to speak. It will be :data:`None` if they are not requesting to speak
        anymore or have been accepted to speak.

        Only applies to stage channels.

        .. versionadded:: 1.7

    afk: :class:`bool`
        Whether the user is currently in the AFK channel in the guild.
    channel: :class:`VoiceChannel` | :class:`StageChannel` | :data:`None`
        The voice channel that the user is currently connected to. :data:`None` if the user
        is not currently in a voice channel.
    """

    __slots__ = (
        "session_id",
        "deaf",
        "mute",
        "self_mute",
        "self_stream",
        "self_video",
        "self_deaf",
        "afk",
        "channel",
        "requested_to_speak_at",
        "suppress",
    )

    def __init__(
        self,
        *,
        data: VoiceStatePayload | GuildVoiceStatePayload,
        channel: VocalGuildChannel | None = None,
    ) -> None:
        self.session_id: str = data["session_id"]
        self._update(data, channel)

    def _update(
        self,
        data: VoiceStatePayload | GuildVoiceStatePayload,
        channel: VocalGuildChannel | None,
    ) -> None:
        self.self_mute: bool = data.get("self_mute", False)
        self.self_deaf: bool = data.get("self_deaf", False)
        self.self_stream: bool = data.get("self_stream", False)
        self.self_video: bool = data.get("self_video", False)
        self.afk: bool = data.get("suppress", False)
        self.mute: bool = data.get("mute", False)
        self.deaf: bool = data.get("deaf", False)
        self.suppress: bool = data.get("suppress", False)
        self.requested_to_speak_at: datetime.datetime | None = utils.parse_time(
            data.get("request_to_speak_timestamp")
        )
        self.channel: VocalGuildChannel | None = channel

    def __repr__(self) -> str:
        attrs = (
            ("self_mute", self.self_mute),
            ("self_deaf", self.self_deaf),
            ("self_stream", self.self_stream),
            ("suppress", self.suppress),
            ("requested_to_speak_at", self.requested_to_speak_at),
            ("channel", self.channel),
        )
        inner = " ".join(f"{k!s}={v!r}" for k, v in attrs)
        return f"<{self.__class__.__name__} {inner}>"


def flatten_user(cls: type[Member]) -> type[Member]:
    for attr, value in itertools.chain(BaseUser.__dict__.items(), User.__dict__.items()):
        # ignore private/special methods
        if attr.startswith("_"):
            continue

        # don't override what we already have
        if attr in cls.__dict__:
            continue

        # if it's a slotted attribute or a property, redirect it
        # slotted members are implemented as member_descriptors in Type.__dict__
        if not hasattr(value, "__annotations__"):
            getter = attrgetter(f"_user.{attr}")
            setattr(cls, attr, property(getter, doc=f"Equivalent to :attr:`User.{attr}`"))
        else:
            # Technically, this can also use attrgetter
            # However I'm not sure how I feel about "functions" returning properties
            # It probably breaks something in Sphinx.
            # probably a member function by now
            def generate_function(x: str) -> Callable[..., Any]:
                # We want sphinx to properly show coroutine functions as coroutines
                if utils.iscoroutinefunction(value):  # noqa: B023

                    async def general(self, *args: Any, **kwargs: Any) -> Any:  # pyright: ignore[reportRedeclaration]
                        return await getattr(self._user, x)(*args, **kwargs)

                else:

                    def general(self, *args: Any, **kwargs: Any) -> Any:
                        return getattr(self._user, x)(*args, **kwargs)

                general.__name__ = x
                return general

            func = generate_function(attr)
            func = utils.copy_doc(value)(func)
            setattr(cls, attr, func)

    return cls


@flatten_user
class Member(disnake.abc.Messageable, _UserTag):
    r"""Represents a Discord member to a :class:`Guild`.

    This implements a lot of the functionality of :class:`User`.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two members are equal.
            Note that this works with :class:`User` instances too.

        .. describe:: x != y

            Checks if two members are not equal.
            Note that this works with :class:`User` instances too.

        .. describe:: hash(x)

            Returns the member's hash.

        .. describe:: str(x)

            Returns the member's username (with discriminator, if not migrated to new system yet).

    Attributes
    ----------
    joined_at: :class:`datetime.datetime` | :data:`None`
        An aware datetime object that specifies the date and time in UTC that the member joined the guild.
        If the member left and rejoined the guild, this will be the latest date. In certain cases, this can be :data:`None`.
    activities: :class:`tuple`\[:class:`BaseActivity` | :class:`Spotify`]
        The activities that the user is currently doing.

        .. note::

            Due to a Discord API limitation, a user's Spotify activity may not appear
            if they are listening to a song with a title longer
            than 128 characters. See :issue-dpy:`1738` for more information.
    guild: :class:`Guild`
        The guild that the member belongs to.
    nick: :class:`str` | :data:`None`
        The guild specific nickname of the user.
        This takes precedence over :attr:`.global_name` and :attr:`.name` when shown.
    pending: :class:`bool`
        Whether the member is pending member verification.

        .. versionadded:: 1.6

    premium_since: :class:`datetime.datetime` | :data:`None`
        An aware datetime object that specifies the date and time in UTC when the member used their
        "Nitro boost" on the guild, if available. This could be :data:`None`.
    """

    __slots__ = (
        "_roles",
        "joined_at",
        "premium_since",
        "activities",
        "guild",
        "pending",
        "nick",
        "_client_status",
        "_user",
        "_state",
        "_avatar",
        "_banner",
        "_communication_disabled_until",
        "_flags",
        "_avatar_decoration_data",
    )

    if TYPE_CHECKING:
        name: str
        id: int
        discriminator: str
        global_name: str | None
        bot: bool
        system: bool
        created_at: datetime.datetime
        default_avatar: Asset
        avatar: Asset | None
        dm_channel: DMChannel | None
        create_dm = User.create_dm
        mutual_guilds: list[Guild]
        public_flags: PublicUserFlags
        banner: Asset | None
        accent_color: Colour | None
        accent_colour: Colour | None
        avatar_decoration: Asset | None
        collectibles: Collectibles
        primary_guild: PrimaryGuild | None

    @overload
    def __init__(
        self,
        *,
        data: MemberWithUserPayload | GuildMemberUpdateEvent,
        guild: Guild,
        state: ConnectionState,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        data: BaseMemberPayload,
        guild: Guild,
        state: ConnectionState,
        user_data: UserPayload,
    ) -> None: ...

    def __init__(
        self,
        *,
        data: BaseMemberPayload | MemberWithUserPayload | GuildMemberUpdateEvent,
        guild: Guild,
        state: ConnectionState,
        user_data: UserPayload | None = None,
    ) -> None:
        self._state: ConnectionState = state
        if user_data is None:
            user_data = cast("MemberWithUserPayload", data)["user"]
        self._user: User = state.store_user(user_data)
        self.guild: Guild = guild

        self.joined_at: datetime.datetime | None = utils.parse_time(data.get("joined_at"))
        self.premium_since: datetime.datetime | None = utils.parse_time(data.get("premium_since"))
        self._roles: utils.SnowflakeList = utils.SnowflakeList(map(int, data["roles"]))
        self._client_status: dict[str | None, str] = {None: "offline"}
        self.activities: tuple[ActivityTypes, ...] = ()
        self.nick: str | None = data.get("nick")
        self.pending: bool = data.get("pending", False)
        self._avatar: str | None = data.get("avatar")
        self._banner: str | None = data.get("banner")
        timeout_datetime = utils.parse_time(data.get("communication_disabled_until"))
        self._communication_disabled_until: datetime.datetime | None = timeout_datetime
        self._flags: int = data.get("flags", 0)
        self._avatar_decoration_data: AvatarDecorationDataPayload | None = data.get(
            "avatar_decoration_data"
        )

    def __str__(self) -> str:
        return str(self._user)

    def __repr__(self) -> str:
        return (
            f"<Member id={self._user.id} name={self._user.name!r} global_name={self._user.global_name!r} discriminator={self._user.discriminator!r}"
            f" bot={self._user.bot} nick={self.nick!r} guild={self.guild!r}>"
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _UserTag) and other.id == self.id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self._user)

    @classmethod
    def _from_message(cls, *, message: Message, data: MemberPayload) -> Self:
        user_data = message.author._to_minimal_user_json()  # pyright: ignore[reportAttributeAccessIssue]
        return cls(
            data=data,
            user_data=user_data,
            guild=message.guild,  # pyright: ignore[reportArgumentType]
            state=message._state,
        )

    def _update_from_message(self, data: MemberPayload) -> None:
        self.joined_at = utils.parse_time(data.get("joined_at"))
        self.premium_since = utils.parse_time(data.get("premium_since"))
        self._roles = utils.SnowflakeList(map(int, data["roles"]))
        self.nick = data.get("nick", None)
        self.pending = data.get("pending", False)
        self._flags = data.get("flags", 0)

    @classmethod
    def _try_upgrade(
        cls,
        *,
        data: UserPayload | UserWithMemberPayload,
        guild: Guild,
        state: ConnectionState,
    ) -> User | Self:
        # A User object with a 'member' key
        if "member" in data:
            member_data: BaseMemberPayload = data["member"]
            return cls(data=member_data, user_data=data, guild=guild, state=state)
        return state.create_user(data)

    @classmethod
    def _copy(cls, member: Member) -> Self:
        self = cls.__new__(cls)  # to bypass __init__

        self._roles = utils.SnowflakeList(member._roles, is_sorted=True)
        self.joined_at = member.joined_at
        self.premium_since = member.premium_since
        self._client_status = member._client_status.copy()
        self.guild = member.guild
        self.nick = member.nick
        self.pending = member.pending
        self.activities = member.activities
        self._state = member._state
        self._avatar = member._avatar
        self._banner = member._banner
        self._communication_disabled_until = member.current_timeout
        self._flags = member._flags
        self._avatar_decoration_data = member._avatar_decoration_data

        # Reference will not be copied unless necessary by PRESENCE_UPDATE
        # See below
        self._user = member._user
        return self

    async def _get_channel(self) -> DMChannel:
        return await self.create_dm()

    def _update(self, data: GuildMemberUpdateEvent) -> None:
        # the nickname change is optional,
        # if it isn't in the payload then it didn't change
        if "nick" in data:
            self.nick = data["nick"]

        if "pending" in data:
            self.pending = data["pending"]

        self.premium_since = utils.parse_time(data.get("premium_since"))
        self._roles = utils.SnowflakeList(map(int, data["roles"]))
        self._avatar = data.get("avatar")
        self._banner = data.get("banner")
        timeout_datetime = utils.parse_time(data.get("communication_disabled_until"))
        self._communication_disabled_until = timeout_datetime
        self._flags = data.get("flags", 0)
        self._avatar_decoration_data = data.get("avatar_decoration_data")

    def _presence_update(self, data: PresenceData, user: UserPayload) -> tuple[User, User] | None:
        self.activities = tuple(create_activity(a, state=self._state) for a in data["activities"])
        self._client_status = {
            sys.intern(key): sys.intern(value)  # pyright: ignore[reportArgumentType, reportCallIssue]
            for key, value in data.get("client_status", {}).items()
        }
        self._client_status[None] = sys.intern(data["status"])

        if len(user) > 1:
            return self._update_inner_user(user)
        return None

    def _update_inner_user(self, user: UserPayload) -> tuple[User, User] | None:
        u = self._user
        original = (
            u.name,
            u.discriminator,
            u.global_name,
            u._avatar,
            u._avatar_decoration_data,
            u._public_flags,
            u._collectibles,
            u._primary_guild,
        )
        # These keys seem to always be available
        modified = (
            user["username"],
            user["discriminator"],
            user.get("global_name"),
            user["avatar"],
            user.get("avatar_decoration_data"),
            user.get("public_flags", 0),
            user.get("collectibles"),
            user.get("primary_guild"),
        )
        if original != modified:
            to_return = User._copy(self._user)
            (
                u.name,
                u.discriminator,
                u.global_name,
                u._avatar,
                u._avatar_decoration_data,
                u._public_flags,
                u._collectibles,
                u._primary_guild,
            ) = modified
            # Signal to dispatch on_user_update
            return to_return, u
        return None

    @property
    def status(self) -> Status:
        """:class:`Status`: The member's overall status. If the value is unknown, then it will be a :class:`str` instead."""
        return try_enum(Status, self._client_status[None])

    @property
    def raw_status(self) -> str:
        """:class:`str`: The member's overall status as a string value.

        .. versionadded:: 1.5
        """
        return self._client_status[None]

    @status.setter
    def status(self, value: Status) -> None:
        # internal use only
        self._client_status[None] = str(value)

    @property
    def tag(self) -> str:
        """:class:`str`: An alias of :attr:`.discriminator`."""
        return self.discriminator

    @property
    def mobile_status(self) -> Status:
        """:class:`Status`: The member's status on a mobile device, if applicable."""
        return try_enum(Status, self._client_status.get("mobile", "offline"))

    @property
    def desktop_status(self) -> Status:
        """:class:`Status`: The member's status on the desktop client, if applicable."""
        return try_enum(Status, self._client_status.get("desktop", "offline"))

    @property
    def web_status(self) -> Status:
        """:class:`Status`: The member's status on the web client, if applicable."""
        return try_enum(Status, self._client_status.get("web", "offline"))

    def is_on_mobile(self) -> bool:
        """Whether the member is active on a mobile device.

        :return type: :class:`bool`
        """
        return "mobile" in self._client_status

    @property
    def colour(self) -> Colour:
        """:class:`Colour`: A property that returns a colour denoting the rendered colour
        for the member. If the default colour is the one rendered then an instance
        of :meth:`Colour.default` is returned.

        There is an alias for this named :attr:`color`.
        """
        roles = self.roles[1:]  # remove @everyone

        # highest order of the colour is the one that gets rendered.
        # if the highest is the default colour then the next one with a colour
        # is chosen instead
        for role in reversed(roles):
            if role.colour.value:
                return role.colour
        return Colour.default()

    @property
    def color(self) -> Colour:
        """:class:`Colour`: A property that returns a color denoting the rendered color for
        the member. If the default color is the one rendered then an instance of :meth:`Colour.default`
        is returned.

        There is an alias for this named :attr:`colour`.
        """
        return self.colour

    @property
    def roles(self) -> list[Role]:
        r""":class:`list`\[:class:`Role`]: A :class:`list` of :class:`Role` that the member belongs to. Note
        that the first element of this list is always the default '@everyone'
        role.

        These roles are sorted by their position in the role hierarchy.
        """
        result: list[Role] = []
        g = self.guild
        for role_id in self._roles:
            role = g.get_role(role_id)
            if role:
                result.append(role)
        result.append(g.default_role)
        result.sort()
        return result

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention the member."""
        return f"<@{self._user.id}>"

    @property
    def display_name(self) -> str:
        """:class:`str`: Returns the user's display name.

        If they have a guild-specific :attr:`nickname <.nick>`, then
        that is returned. If not, this is their :attr:`global name <.global_name>`
        if set, or their :attr:`username <.name>` otherwise.

        .. versionchanged:: 2.9
            Added :attr:`.global_name`.
        """
        return self.nick or self.global_name or self.name

    @property
    def display_avatar(self) -> Asset:
        """:class:`Asset`: Returns the member's display avatar.

        For regular members this is just their avatar, but
        if they have a guild specific avatar then that
        is returned instead.

        .. versionadded:: 2.0
        """
        return self.guild_avatar or self._user.avatar or self._user.default_avatar

    @property
    def guild_avatar(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns an :class:`Asset` for the guild avatar
        the member has. If unavailable, :data:`None` is returned.

        .. versionadded:: 2.0
        """
        if self._avatar is None:
            return None
        return Asset._from_guild_avatar(self._state, self.guild.id, self.id, self._avatar)

    # TODO
    # implement a `display_banner` property
    # for more info on why this wasn't implemented read this discussion
    # https://github.com/DisnakeDev/disnake/pull/1204#discussion_r1685773429
    @property
    def guild_banner(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns an :class:`Asset` for the guild banner
        the member has. If unavailable, :data:`None` is returned.

        .. versionadded:: 2.10
        """
        if self._banner is None:
            return None
        return Asset._from_guild_banner(self._state, self.guild.id, self.id, self._banner)

    @property
    def activity(self) -> ActivityTypes | None:
        """:class:`BaseActivity` | :class:`Spotify` | :data:`None`: Returns the primary
        activity the user is currently doing. Could be :data:`None` if no activity is being done.

        .. note::

            Due to a Discord API limitation, this may be :data:`None` if
            the user is listening to a song on Spotify with a title longer
            than 128 characters. See :issue-dpy:`1738` for more information.

        .. note::

            A user may have multiple activities, these can be accessed under :attr:`activities`.
        """
        if self.activities:
            return self.activities[0]
        return None

    def mentioned_in(self, message: Message) -> bool:
        """Whether the member is mentioned in the specified message.

        Parameters
        ----------
        message: :class:`Message`
            The message to check.

        Returns
        -------
        :class:`bool`
            Indicates if the member is mentioned in the message.
        """
        if message.guild is None or message.guild.id != self.guild.id:
            return False

        if self._user.mentioned_in(message):
            return True

        return any(self._roles.has(role.id) for role in message.role_mentions)

    @property
    def top_role(self) -> Role:
        """:class:`Role`: Returns the member's highest role.

        This is useful for figuring where a member stands in the role
        hierarchy chain.
        """
        guild = self.guild
        if len(self._roles) == 0:
            return guild.default_role

        return max(guild.get_role(rid) or guild.default_role for rid in self._roles)

    @property
    def role_icon(self) -> Asset | PartialEmoji | None:
        """:class:`Asset` | :class:`PartialEmoji` | :data:`None`: Returns the member's displayed role icon, if any.

        .. versionadded:: 2.5
        """
        roles = self.roles[1:]  # remove @everyone

        for role in reversed(roles):
            if icon := (role.icon or role.emoji):
                return icon
        return None

    @property
    def guild_permissions(self) -> Permissions:
        """:class:`Permissions`: Returns the member's guild permissions.

        This only takes into consideration the guild permissions
        and not most of the implied permissions or any of the
        channel permission overwrites. For 100% accurate permission
        calculation, please use :meth:`abc.GuildChannel.permissions_for`.

        This does take into consideration guild ownership and the
        administrator implication.
        """
        if self.guild.owner_id == self.id:
            return Permissions.all()

        base = Permissions.none()
        for r in self.roles:
            base.value |= r.permissions.value

        if base.administrator:
            return Permissions.all()

        return base

    @property
    def current_timeout(self) -> datetime.datetime | None:
        """:class:`datetime.datetime` | :data:`None`: Returns the datetime when the timeout expires.

        If the member is not timed out or the timeout has already expired, returns :data:`None`.

        .. versionadded:: 2.3
        """
        if (
            self._communication_disabled_until is not None
            and self._communication_disabled_until < utils.utcnow()
        ):
            self._communication_disabled_until = None

        return self._communication_disabled_until

    @property
    def flags(self) -> MemberFlags:
        """:class:`MemberFlags`: Returns the member's flags.

        .. versionadded:: 2.8
        """
        return MemberFlags._from_value(self._flags)

    @property
    def display_avatar_decoration(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns the member's display avatar decoration.

        For regular members this is just their avatar decoration, but
        if they have a guild specific avatar decoration then that
        is returned instead.

        .. versionadded:: 2.10

        .. note::

            Since Discord always sends an animated PNG for animated avatar decorations,
            the following methods will not work as expected:

            - :meth:`Asset.replace`
            - :meth:`Asset.with_size`
            - :meth:`Asset.with_format`
            - :meth:`Asset.with_static_format`
        """
        return self.guild_avatar_decoration or self._user.avatar_decoration

    @property
    def guild_avatar_decoration(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns an :class:`Asset` for the guild avatar decoration
        the member has. If unavailable, :data:`None` is returned.

        .. versionadded:: 2.10

        .. note::

            Since Discord always sends an animated PNG for animated avatar decorations,
            the following methods will not work as expected:

            - :meth:`Asset.replace`
            - :meth:`Asset.with_size`
            - :meth:`Asset.with_format`
            - :meth:`Asset.with_static_format`
        """
        if self._avatar_decoration_data is None:
            return None
        return Asset._from_avatar_decoration(self._state, self._avatar_decoration_data["asset"])

    async def _edit_self(
        self,
        *,
        nick: str | None = MISSING,
        bio: str | None = MISSING,
        avatar: AssetBytes | None = MISSING,
        banner: AssetBytes | None = MISSING,
        reason: str | None = None,
    ) -> Member | None:
        payload: dict[str, Any] = {}

        if nick is not MISSING:
            payload["nick"] = nick or ""

        if bio is not MISSING:
            payload["bio"] = bio

        if avatar is not MISSING:
            payload["avatar"] = await _assetbytes_to_base64_data(avatar)

        if banner is not MISSING:
            payload["banner"] = await _assetbytes_to_base64_data(banner)

        data = await self._state.http.edit_my_member(self.guild.id, reason=reason, **payload)
        return Member(data=data, guild=self.guild, state=self._state)

    def get_role(self, role_id: int, /) -> Role | None:
        """Returns a role with the given ID from roles which the member has.

        .. versionadded:: 2.0

        Parameters
        ----------
        role_id: :class:`int`
            The role ID to search for.

        Returns
        -------
        :class:`Role` | :data:`None`
            The role or :data:`None` if not found in the member's roles.
        """
        return self.guild.get_role(role_id) if self._roles.has(role_id) else None
