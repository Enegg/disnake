# SPDX-License-Identifier: MIT

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Literal, NamedTuple

import disnake.abc

from . import utils
from .asset import Asset
from .enums import (
    ChannelType,
    ThreadLayout,
    ThreadSortOrder,
    VideoQualityMode,
    try_enum,
)
from .flags import ChannelFlags
from .iterators import ArchivedThreadIterator
from .mixins import Hashable
from .object import Object
from .partial_emoji import PartialEmoji
from .permissions import Permissions
from .threads import ForumTag, Thread
from .utils import MISSING

__all__ = (
    "TextChannel",
    "VoiceChannel",
    "StageChannel",
    "DMChannel",
    "CategoryChannel",
    "NewsChannel",
    "ThreadWithMessage",
    "ForumChannel",
    "MediaChannel",
    "GroupChannel",
    "PartialMessageable",
)

if TYPE_CHECKING:
    from typing_extensions import Self

    from .abc import Snowflake
    from .emoji import Emoji
    from .guild import Guild, GuildChannel as GuildChannelType
    from .member import Member, VoiceState
    from .message import Message, PartialMessage
    from .role import Role
    from .state import ConnectionState
    from .types.channel import (
        CategoryChannel as CategoryChannelPayload,
        DMChannel as DMChannelPayload,
        ForumChannel as ForumChannelPayload,
        GroupDMChannel as GroupChannelPayload,
        MediaChannel as MediaChannelPayload,
        StageChannel as StageChannelPayload,
        TextChannel as TextChannelPayload,
        VoiceChannel as VoiceChannelPayload,
    )
    from .types.threads import ThreadArchiveDurationLiteral
    from .user import BaseUser, ClientUser, User


class TextChannel(disnake.abc.Messageable, disnake.abc.GuildChannel, Hashable):
    """Represents a Discord guild text channel.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the channel's hash.

        .. describe:: str(x)

            Returns the channel's name.

    Attributes
    ----------
    name: :class:`str`
        The channel's name.
    guild: :class:`Guild`
        The guild the channel belongs to.
    id: :class:`int`
        The channel's ID.
    category_id: :class:`int` | :data:`None`
        The category channel ID this channel belongs to, if applicable.
    topic: :class:`str` | :data:`None`
        The channel's topic. :data:`None` if it doesn't exist.
    position: :class:`int`
        The position in the channel list. This is a number that starts at 0. e.g. the
        top channel is position 0.
    last_message_id: :class:`int` | :data:`None`
        The last message ID of the message sent to this channel. It may
        *not* point to an existing or valid message.
    slowmode_delay: :class:`int`
        The number of seconds a member must wait between sending messages
        in this channel.

        A value of `0` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

        See also :attr:`default_thread_slowmode_delay`.

    default_thread_slowmode_delay: :class:`int`
        The default number of seconds a member must wait between sending messages
        in newly created threads in this channel.

        A value of ``0`` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

        .. versionadded:: 2.8

    nsfw: :class:`bool`
        Whether the channel is marked as "not safe for work".

        .. note::

            To check if the channel or the guild of that channel are marked as NSFW, consider :meth:`is_nsfw` instead.
    default_auto_archive_duration: :class:`int`
        The default auto archive duration in minutes for threads created in this channel.

        .. versionadded:: 2.0

    last_pin_timestamp: :class:`datetime.datetime` | :data:`None`
        The time the most recent message was pinned, or :data:`None` if no message is currently pinned.

        .. versionadded:: 2.5
    """

    __slots__ = (
        "name",
        "id",
        "guild",
        "topic",
        "_state",
        "nsfw",
        "category_id",
        "position",
        "slowmode_delay",
        "default_thread_slowmode_delay",
        "last_message_id",
        "default_auto_archive_duration",
        "last_pin_timestamp",
        "_overwrites",
        "_flags",
        "_type",
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: TextChannelPayload) -> None:
        self._state: ConnectionState = state
        self.id: int = int(data["id"])
        self._type: Literal[0, 5] = data["type"]
        self._update(guild, data)

    def __repr__(self) -> str:
        attrs = (
            ("id", self.id),
            ("name", self.name),
            ("position", self.position),
            ("nsfw", self.nsfw),
            ("news", self.is_news()),
            ("category_id", self.category_id),
            ("default_auto_archive_duration", self.default_auto_archive_duration),
            ("flags", self.flags),
        )
        joined = " ".join(f"{k!s}={v!r}" for k, v in attrs)
        return f"<{self.__class__.__name__} {joined}>"

    def _update(self, guild: Guild, data: TextChannelPayload) -> None:
        self.guild: Guild = guild
        # apparently this can be nullable in the case of a bad api deploy
        self.name: str = data.get("name") or ""
        self.category_id: int | None = utils._get_as_snowflake(data, "parent_id")
        self.topic: str | None = data.get("topic")
        self.position: int = data["position"]
        self._flags = data.get("flags", 0)
        self.nsfw: bool = data.get("nsfw", False)
        # Does this need coercion into `int`? No idea yet.
        self.slowmode_delay: int = data.get("rate_limit_per_user", 0)
        self.default_thread_slowmode_delay: int = data.get("default_thread_rate_limit_per_user", 0)
        self.default_auto_archive_duration: ThreadArchiveDurationLiteral = data.get(
            "default_auto_archive_duration", 1440
        )
        self._type: Literal[0, 5] = data.get("type", self._type)
        self.last_message_id: int | None = utils._get_as_snowflake(data, "last_message_id")
        self.last_pin_timestamp: datetime.datetime | None = utils.parse_time(
            data.get("last_pin_timestamp")
        )
        self._fill_overwrites(data)

    async def _get_channel(self) -> Self:
        return self

    @property
    def type(self) -> Literal[ChannelType.text, ChannelType.news]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.text` or :attr:`ChannelType.news`.
        """
        if self._type == ChannelType.text.value:
            return ChannelType.text
        return ChannelType.news

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.text.value

    @utils.copy_doc(disnake.abc.GuildChannel.permissions_for)
    def permissions_for(
        self,
        obj: Member | Role,
        /,
        *,
        ignore_timeout: bool = MISSING,
    ) -> Permissions:
        base = super().permissions_for(obj, ignore_timeout=ignore_timeout)
        self._apply_implict_permissions(base)

        # text channels do not have voice related permissions
        denied = Permissions.voice()
        base.value &= ~denied.value
        return base

    @property
    def members(self) -> list[Member]:
        r""":class:`list`\[:class:`Member`]: Returns all members that can see this channel."""
        if isinstance(self.guild, Object):
            return []
        return [m for m in self.guild.members if self.permissions_for(m).view_channel]

    @property
    def threads(self) -> list[Thread]:
        r""":class:`list`\[:class:`Thread`]: Returns all the threads that you can see.

        .. versionadded:: 2.0
        """
        if isinstance(self.guild, Object):
            return []
        return [thread for thread in self.guild._threads.values() if thread.parent_id == self.id]

    def is_nsfw(self) -> bool:
        """Whether the channel is marked as NSFW.

        :return type: :class:`bool`
        """
        return self.nsfw

    def is_news(self) -> bool:
        """Whether the channel is a news channel.

        :return type: :class:`bool`
        """
        return self._type == ChannelType.news.value

    @property
    def last_message(self) -> Message | None:
        """Gets the last message in this channel from the cache.

        The message might not be valid or point to an existing message.

        .. admonition:: Reliable Fetching
            :class: helpful

            For a slightly more reliable method of fetching the
            last message, consider using either :meth:`history`
            or :meth:`fetch_message` with the :attr:`last_message_id`
            attribute.

        Returns
        -------
        :class:`Message` | :data:`None`
            The last message in this channel or :data:`None` if not found.
        """
        return self._state._get_message(self.last_message_id) if self.last_message_id else None

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """Creates a :class:`PartialMessage` from the given message ID.

        This is useful if you want to work with a message and only have its ID without
        doing an unnecessary API call.

        .. versionadded:: 1.6

        Parameters
        ----------
        message_id: :class:`int`
            The message ID to create a partial message for.

        Returns
        -------
        :class:`PartialMessage`
            The partial message object.
        """
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)

    def get_thread(self, thread_id: int, /) -> Thread | None:
        """Returns a thread with the given ID.

        .. versionadded:: 2.0

        Parameters
        ----------
        thread_id: :class:`int`
            The ID to search for.

        Returns
        -------
        :class:`Thread` | :data:`None`
            The returned thread or :data:`None` if not found.
        """
        if isinstance(self.guild, Object):
            return None
        return self.guild.get_thread(thread_id)

    def archived_threads(
        self,
        *,
        private: bool = False,
        joined: bool = False,
        limit: int | None = 50,
        before: Snowflake | datetime.datetime | None = None,
    ) -> ArchivedThreadIterator:
        """Returns an :class:`~disnake.AsyncIterator` that iterates over all archived threads in the channel.

        You must have :attr:`~Permissions.read_message_history` permission to use this. If iterating over private threads
        then :attr:`~Permissions.manage_threads` permission is also required.

        .. versionadded:: 2.0

        Parameters
        ----------
        limit: :class:`int` | :data:`None`
            The number of threads to retrieve.
            If :data:`None`, retrieves every archived thread in the channel. Note, however,
            that this would make it a slow operation.
        before: :class:`abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
            Retrieve archived channels before the given date or ID.
        private: :class:`bool`
            Whether to retrieve private archived threads.
        joined: :class:`bool`
            Whether to retrieve private archived threads that you've joined.
            You cannot set ``joined`` to ``True`` and ``private`` to ``False``.

        Raises
        ------
        Forbidden
            You do not have permissions to get archived threads.
        HTTPException
            The request to get the archived threads failed.

        Yields
        ------
        :class:`Thread`
            The archived threads.
        """
        return ArchivedThreadIterator(
            self.id, self.guild, limit=limit, joined=joined, private=private, before=before
        )


class VocalGuildChannel(disnake.abc.GuildChannel, Hashable):
    __slots__ = (
        "name",
        "id",
        "guild",
        "bitrate",
        "user_limit",
        "_state",
        "position",
        "_overwrites",
        "category_id",
        "rtc_region",
        "video_quality_mode",
        "_flags",
    )

    def __init__(
        self,
        *,
        state: ConnectionState,
        guild: Guild,
        data: VoiceChannelPayload | StageChannelPayload,
    ) -> None:
        self._state: ConnectionState = state
        self.id: int = int(data["id"])
        self._update(guild, data)

    def _get_voice_client_key(self) -> tuple[int, str]:
        return self.guild.id, "guild_id"

    def _get_voice_state_pair(self) -> tuple[int, int]:
        return self.guild.id, self.id

    def _update(self, guild: Guild, data: VoiceChannelPayload | StageChannelPayload) -> None:
        self.guild = guild
        # apparently this can be nullable in the case of a bad api deploy
        self.name: str = data.get("name") or ""
        rtc = data.get("rtc_region")
        self.rtc_region: str | None = rtc
        self.video_quality_mode: VideoQualityMode = try_enum(
            VideoQualityMode, data.get("video_quality_mode", 1)
        )
        self._flags = data.get("flags", 0)
        self.category_id: int | None = utils._get_as_snowflake(data, "parent_id")
        self.position: int = data["position"]
        # these don't exist in partial channel objects of slash command options
        self.bitrate: int = data.get("bitrate", 0)
        self.user_limit: int = data.get("user_limit", 0)
        self._fill_overwrites(data)

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.voice.value

    @property
    def members(self) -> list[Member]:
        r""":class:`list`\[:class:`Member`]: Returns all members that are currently inside this voice channel."""
        if isinstance(self.guild, Object):
            return []

        ret: list[Member] = []
        for user_id, state in self.guild._voice_states.items():
            if state.channel and state.channel.id == self.id:
                member = self.guild.get_member(user_id)
                if member is not None:
                    ret.append(member)
        return ret

    @property
    def voice_states(self) -> dict[int, VoiceState]:
        r"""Returns a mapping of member IDs who have voice states in this channel.

        .. versionadded:: 1.3

        .. note::

            This function is intentionally low level to replace :attr:`members`
            when the member cache is unavailable.

        Returns
        -------
        :class:`~collections.abc.Mapping`\[:class:`int`, :class:`VoiceState`]
            The mapping of member ID to a voice state.
        """
        if isinstance(self.guild, Object):
            return {}

        return {
            key: value
            for key, value in self.guild._voice_states.items()
            if value.channel and value.channel.id == self.id
        }

    @utils.copy_doc(disnake.abc.GuildChannel.permissions_for)
    def permissions_for(
        self,
        obj: Member | Role,
        /,
        *,
        ignore_timeout: bool = MISSING,
    ) -> Permissions:
        base = super().permissions_for(obj, ignore_timeout=ignore_timeout)
        self._apply_implict_permissions(base)

        # voice channels cannot be edited by people who can't connect to them
        # It also implicitly denies all other voice perms
        if not base.connect:
            denied = Permissions.voice()
            # voice channels also deny all text related permissions
            denied.value |= Permissions.text().value
            # stage channels remove the stage permissions
            denied.value |= Permissions.stage().value

            denied.update(
                manage_channels=True,
                manage_roles=True,
                create_events=True,
                manage_events=True,
                manage_webhooks=True,
            )
            base.value &= ~denied.value
        return base


class VoiceChannel(disnake.abc.Messageable, VocalGuildChannel):
    """Represents a Discord guild voice channel.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the channel's hash.

        .. describe:: str(x)

            Returns the channel's name.

    Attributes
    ----------
    name: :class:`str`
        The channel's name.
    guild: :class:`Guild`
        The guild the channel belongs to.
    id: :class:`int`
        The channel's ID.
    category_id: :class:`int` | :data:`None`
        The category channel ID this channel belongs to, if applicable.
    position: :class:`int`
        The position in the channel list. This is a number that starts at 0. e.g. the
        top channel is position 0.
    bitrate: :class:`int`
        The channel's preferred audio bitrate in bits per second.
    user_limit: :class:`int`
        The channel's limit for number of members that can be in a voice channel.
    rtc_region: :class:`str` | :data:`None`
        The region for the voice channel's voice communication.
        A value of :data:`None` indicates automatic voice region detection.

        .. versionadded:: 1.7

        .. versionchanged:: 2.5
            No longer a ``VoiceRegion`` instance.

    video_quality_mode: :class:`VideoQualityMode`
        The camera video quality for the voice channel's participants.
    nsfw: :class:`bool`
        Whether the channel is marked as "not safe for work".

        .. note::

            To check if the channel or the guild of that channel are marked as NSFW, consider :meth:`is_nsfw` instead.

        .. versionadded:: 2.3

    slowmode_delay: :class:`int`
        The number of seconds a member must wait between sending messages
        in this channel.

        A value of `0` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

        .. versionadded:: 2.3

    last_message_id: :class:`int` | :data:`None`
        The last message ID of the message sent to this channel. It may
        *not* point to an existing or valid message.

        .. versionadded:: 2.3

    status: :class:`str` | :data:`None`
        The channel's status, if any.

        This can be edited using :meth:`set_status`.

        .. versionadded:: |vnext|
    """

    __slots__ = (
        "nsfw",
        "slowmode_delay",
        "last_message_id",
        "status",
    )

    def __repr__(self) -> str:
        attrs = (
            ("id", self.id),
            ("name", self.name),
            ("rtc_region", self.rtc_region),
            ("position", self.position),
            ("bitrate", self.bitrate),
            ("video_quality_mode", self.video_quality_mode),
            ("user_limit", self.user_limit),
            ("category_id", self.category_id),
            ("nsfw", self.nsfw),
            ("flags", self.flags),
        )
        joined = " ".join(f"{k!s}={v!r}" for k, v in attrs)
        return f"<{self.__class__.__name__} {joined}>"

    def _update(self, guild: Guild, data: VoiceChannelPayload) -> None:
        super()._update(guild, data)
        self.nsfw: bool = data.get("nsfw", False)
        self.slowmode_delay: int = data.get("rate_limit_per_user", 0)
        self.last_message_id: int | None = utils._get_as_snowflake(data, "last_message_id")
        self.status: str | None = data.get("status")

    async def _get_channel(self) -> Self:
        return self

    @property
    def type(self) -> Literal[ChannelType.voice]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.voice`.
        """
        return ChannelType.voice

    def is_nsfw(self) -> bool:
        """Whether the channel is marked as NSFW.

        .. versionadded:: 2.3

        :return type: :class:`bool`
        """
        return self.nsfw

    @property
    def last_message(self) -> Message | None:
        """Gets the last message in this channel from the cache.

        The message might not be valid or point to an existing message.

        .. admonition:: Reliable Fetching
            :class: helpful

            For a slightly more reliable method of fetching the
            last message, consider using either :meth:`history`
            or :meth:`fetch_message` with the :attr:`last_message_id`
            attribute.

        .. versionadded:: 2.3

        Returns
        -------
        :class:`Message` | :data:`None`
            The last message in this channel or :data:`None` if not found.
        """
        return self._state._get_message(self.last_message_id) if self.last_message_id else None

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """Creates a :class:`PartialMessage` from the given message ID.

        This is useful if you want to work with a message and only have its ID without
        doing an unnecessary API call.

        .. versionadded:: 2.3

        Parameters
        ----------
        message_id: :class:`int`
            The message ID to create a partial message for.

        Returns
        -------
        :class:`PartialMessage`
            The partial message object.
        """
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


class StageChannel(disnake.abc.Messageable, VocalGuildChannel):
    """Represents a Discord guild stage channel.

    .. versionadded:: 1.7

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the channel's hash.

        .. describe:: str(x)

            Returns the channel's name.

    Attributes
    ----------
    name: :class:`str`
        The channel's name.
    guild: :class:`Guild`
        The guild the channel belongs to.
    id: :class:`int`
        The channel's ID.
    topic: :class:`str` | :data:`None`
        The channel's topic. :data:`None` if it isn't set.
    category_id: :class:`int` | :data:`None`
        The category channel ID this channel belongs to, if applicable.
    position: :class:`int`
        The position in the channel list. This is a number that starts at 0. e.g. the
        top channel is position 0.
    bitrate: :class:`int`
        The channel's preferred audio bitrate in bits per second.
    user_limit: :class:`int`
        The channel's limit for number of members that can be in a stage channel.
    rtc_region: :class:`str` | :data:`None`
        The region for the stage channel's voice communication.
        A value of :data:`None` indicates automatic voice region detection.

        .. versionchanged:: 2.5
            No longer a ``VoiceRegion`` instance.

    video_quality_mode: :class:`VideoQualityMode`
        The camera video quality for the stage channel's participants.

        .. versionadded:: 2.0
    nsfw: :class:`bool`
        Whether the channel is marked as "not safe for work".

        .. note::

            To check if the channel or the guild of that channel are marked as NSFW, consider :meth:`is_nsfw` instead.

        .. versionadded:: 2.9

    slowmode_delay: :class:`int`
        The number of seconds a member must wait between sending messages
        in this channel.

        A value of `0` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

        .. versionadded:: 2.9

    last_message_id: :class:`int` | :data:`None`
        The last message ID of the message sent to this channel. It may
        *not* point to an existing or valid message.

        .. versionadded:: 2.9
    """

    __slots__ = (
        "topic",
        "nsfw",
        "slowmode_delay",
        "last_message_id",
    )

    def __repr__(self) -> str:
        attrs = (
            ("id", self.id),
            ("name", self.name),
            ("topic", self.topic),
            ("rtc_region", self.rtc_region),
            ("position", self.position),
            ("bitrate", self.bitrate),
            ("video_quality_mode", self.video_quality_mode),
            ("user_limit", self.user_limit),
            ("category_id", self.category_id),
            ("nsfw", self.nsfw),
            ("flags", self.flags),
        )
        joined = " ".join(f"{k!s}={v!r}" for k, v in attrs)
        return f"<{self.__class__.__name__} {joined}>"

    def _update(self, guild: Guild, data: StageChannelPayload) -> None:
        super()._update(guild, data)
        self.topic: str | None = data.get("topic")
        self.nsfw: bool = data.get("nsfw", False)
        self.slowmode_delay: int = data.get("rate_limit_per_user", 0)
        self.last_message_id: int | None = utils._get_as_snowflake(data, "last_message_id")

    async def _get_channel(self) -> Self:
        return self

    @property
    def type(self) -> Literal[ChannelType.stage_voice]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.stage_voice`.
        """
        return ChannelType.stage_voice

    @property
    def last_message(self) -> Message | None:
        """Gets the last message in this channel from the cache.

        The message might not be valid or point to an existing message.

        .. admonition:: Reliable Fetching
            :class: helpful

            For a slightly more reliable method of fetching the
            last message, consider using either :meth:`history`
            or :meth:`fetch_message` with the :attr:`last_message_id`
            attribute.

        .. versionadded:: 2.9

        Returns
        -------
        :class:`Message` | :data:`None`
            The last message in this channel or :data:`None` if not found.
        """
        return self._state._get_message(self.last_message_id) if self.last_message_id else None

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """Creates a :class:`PartialMessage` from the given message ID.

        This is useful if you want to work with a message and only have its ID without
        doing an unnecessary API call.

        .. versionadded:: 2.9

        Parameters
        ----------
        message_id: :class:`int`
            The message ID to create a partial message for.

        Returns
        -------
        :class:`PartialMessage`
            The partial message object.
        """
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


class CategoryChannel(disnake.abc.GuildChannel, Hashable):
    """Represents a Discord channel category.

    These are useful to group channels to logical compartments.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the category's hash.

        .. describe:: str(x)

            Returns the category's name.

    Attributes
    ----------
    name: :class:`str`
        The category name.
    guild: :class:`Guild`
        The guild the category belongs to.
    id: :class:`int`
        The category channel ID.
    position: :class:`int`
        The position in the category list. This is a number that starts at 0. e.g. the
        top category is position 0.
    nsfw: :class:`bool`
        If the channel is marked as "not safe for work".

        .. note::

            To check if the channel or the guild of that channel are marked as NSFW, consider :meth:`is_nsfw` instead.
    """

    __slots__ = (
        "name",
        "id",
        "guild",
        "nsfw",
        "_state",
        "position",
        "_overwrites",
        "category_id",
        "_flags",
    )

    def __init__(
        self, *, state: ConnectionState, guild: Guild, data: CategoryChannelPayload
    ) -> None:
        self._state: ConnectionState = state
        self.id: int = int(data["id"])
        self._update(guild, data)

    def __repr__(self) -> str:
        return f"<CategoryChannel id={self.id} name={self.name!r} position={self.position} nsfw={self.nsfw} flags={self.flags!r}>"

    def _update(self, guild: Guild, data: CategoryChannelPayload) -> None:
        self.guild: Guild = guild
        # apparently this can be nullable in the case of a bad api deploy
        self.name: str = data.get("name") or ""
        self.category_id: int | None = utils._get_as_snowflake(data, "parent_id")
        self._flags = data.get("flags", 0)
        self.nsfw: bool = data.get("nsfw", False)
        self.position: int = data["position"]
        self._fill_overwrites(data)

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.category.value

    @property
    def type(self) -> Literal[ChannelType.category]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.category`.
        """
        return ChannelType.category

    @utils.copy_doc(disnake.abc.GuildChannel.permissions_for)
    def permissions_for(
        self,
        obj: Member | Role,
        /,
        *,
        ignore_timeout: bool = MISSING,
    ) -> Permissions:
        base = super().permissions_for(obj, ignore_timeout=ignore_timeout)
        self._apply_implict_permissions(base)

        return base

    def is_nsfw(self) -> bool:
        """Whether the category is marked as NSFW.

        :return type: :class:`bool`
        """
        return self.nsfw

    @property
    def channels(self) -> list[GuildChannelType]:
        r""":class:`list`\[:class:`abc.GuildChannel`]: Returns the channels that are under this category.

        These are sorted by the official Discord UI, which places voice channels below the text channels.
        """
        if isinstance(self.guild, Object):
            return []

        def comparator(channel: GuildChannelType) -> tuple[bool, int]:
            return (
                not isinstance(channel, (TextChannel, ThreadOnlyGuildChannel)),
                channel.position,
            )

        ret = [c for c in self.guild.channels if c.category_id == self.id]
        ret.sort(key=comparator)
        return ret

    @property
    def text_channels(self) -> list[TextChannel]:
        r""":class:`list`\[:class:`TextChannel`]: Returns the text channels that are under this category."""
        if isinstance(self.guild, Object):
            return []

        ret = [
            c
            for c in self.guild.channels
            if c.category_id == self.id and isinstance(c, TextChannel)
        ]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def voice_channels(self) -> list[VoiceChannel]:
        r""":class:`list`\[:class:`VoiceChannel`]: Returns the voice channels that are under this category."""
        if isinstance(self.guild, Object):
            return []

        ret = [
            c
            for c in self.guild.channels
            if c.category_id == self.id and isinstance(c, VoiceChannel)
        ]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def stage_channels(self) -> list[StageChannel]:
        r""":class:`list`\[:class:`StageChannel`]: Returns the stage channels that are under this category.

        .. versionadded:: 1.7
        """
        if isinstance(self.guild, Object):
            return []

        ret = [
            c
            for c in self.guild.channels
            if c.category_id == self.id and isinstance(c, StageChannel)
        ]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def forum_channels(self) -> list[ForumChannel]:
        r""":class:`list`\[:class:`ForumChannel`]: Returns the forum channels that are under this category.

        .. versionadded:: 2.5
        """
        if isinstance(self.guild, Object):
            return []

        ret = [
            c
            for c in self.guild.channels
            if c.category_id == self.id and isinstance(c, ForumChannel)
        ]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def media_channels(self) -> list[MediaChannel]:
        r""":class:`list`\[:class:`MediaChannel`]: Returns the media channels that are under this category.

        .. versionadded:: 2.10
        """
        if isinstance(self.guild, Object):
            return []

        ret = [
            c
            for c in self.guild.channels
            if c.category_id == self.id and isinstance(c, MediaChannel)
        ]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret


class NewsChannel(TextChannel):
    """Represents a Discord news channel

    An exact 1:1 copy of :class:`TextChannel` meant for command annotations
    """

    type: ChannelType = ChannelType.news


class ThreadWithMessage(NamedTuple):
    thread: Thread
    message: Message


class ThreadOnlyGuildChannel(disnake.abc.GuildChannel, Hashable):
    __slots__ = (
        "id",
        "name",
        "category_id",
        "topic",
        "position",
        "nsfw",
        "last_thread_id",
        "_flags",
        "default_auto_archive_duration",
        "guild",
        "slowmode_delay",
        "default_thread_slowmode_delay",
        "default_sort_order",
        "_available_tags",
        "_default_reaction_emoji_id",
        "_default_reaction_emoji_name",
        "_state",
        "_type",
        "_overwrites",
    )

    def __init__(
        self,
        *,
        state: ConnectionState,
        guild: Guild,
        data: ForumChannelPayload | MediaChannelPayload,
    ) -> None:
        self._state: ConnectionState = state
        self.id: int = int(data["id"])
        self._type: int = data["type"]
        self._update(guild, data)

    def __repr__(self) -> str:
        attrs = (
            ("id", self.id),
            ("name", self.name),
            ("topic", self.topic),
            ("position", self.position),
            ("nsfw", self.nsfw),
            ("category_id", self.category_id),
            ("default_auto_archive_duration", self.default_auto_archive_duration),
            ("flags", self.flags),
        )
        joined = " ".join(f"{k!s}={v!r}" for k, v in attrs)
        return f"<{type(self).__name__} {joined}>"

    def _update(self, guild: Guild, data: ForumChannelPayload | MediaChannelPayload) -> None:
        self.guild: Guild = guild
        # apparently this can be nullable in the case of a bad api deploy
        self.name: str = data.get("name") or ""
        self.category_id: int | None = utils._get_as_snowflake(data, "parent_id")
        self.topic: str | None = data.get("topic")
        self.position: int = data["position"]
        self._flags = data.get("flags", 0)
        self.nsfw: bool = data.get("nsfw", False)
        self.last_thread_id: int | None = utils._get_as_snowflake(data, "last_message_id")
        self.default_auto_archive_duration: ThreadArchiveDurationLiteral = data.get(
            "default_auto_archive_duration", 1440
        )
        self.slowmode_delay: int = data.get("rate_limit_per_user", 0)
        self.default_thread_slowmode_delay: int = data.get("default_thread_rate_limit_per_user", 0)

        tags = [
            ForumTag._from_data(data=tag, state=self._state)
            for tag in data.get("available_tags", [])
        ]
        self._available_tags: dict[int, ForumTag] = {tag.id: tag for tag in tags}

        default_reaction_emoji = data.get("default_reaction_emoji") or {}
        # emoji_id may be `0`, use `None` instead
        self._default_reaction_emoji_id: int | None = (
            utils._get_as_snowflake(default_reaction_emoji, "emoji_id") or None
        )
        self._default_reaction_emoji_name: str | None = default_reaction_emoji.get("emoji_name")

        self.default_sort_order: ThreadSortOrder | None = (
            try_enum(ThreadSortOrder, order)
            if (order := data.get("default_sort_order")) is not None
            else None
        )

        self._fill_overwrites(data)

    async def _get_channel(self) -> Self:
        return self

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.text.value

    @utils.copy_doc(disnake.abc.GuildChannel.permissions_for)
    def permissions_for(
        self,
        obj: Member | Role,
        /,
        *,
        ignore_timeout: bool = MISSING,
    ) -> Permissions:
        base = super().permissions_for(obj, ignore_timeout=ignore_timeout)
        self._apply_implict_permissions(base)

        # thread-only channels do not have voice related permissions
        denied = Permissions.voice()
        base.value &= ~denied.value
        return base

    @property
    def members(self) -> list[Member]:
        r""":class:`list`\[:class:`Member`]: Returns all members that can see this channel."""
        if isinstance(self.guild, Object):
            return []
        return [m for m in self.guild.members if self.permissions_for(m).view_channel]

    @property
    def threads(self) -> list[Thread]:
        r""":class:`list`\[:class:`Thread`]: Returns all the threads that you can see."""
        if isinstance(self.guild, Object):
            return []
        return [thread for thread in self.guild._threads.values() if thread.parent_id == self.id]

    def is_nsfw(self) -> bool:
        """Whether the channel is marked as NSFW.

        :return type: :class:`bool`
        """
        return self.nsfw

    def requires_tag(self) -> bool:
        """Whether all newly created threads in this channel are required to have a tag.

        This is a shortcut to :attr:`self.flags.require_tag <ChannelFlags.require_tag>`.

        .. versionadded:: 2.6

        :return type: :class:`bool`
        """
        return self.flags.require_tag

    @property
    def default_reaction(self) -> Emoji | PartialEmoji | None:
        """:class:`Emoji` | :class:`PartialEmoji` | :data:`None`:
        The default emoji shown for reacting to threads.

        Due to a Discord limitation, this will have an empty
        :attr:`~PartialEmoji.name` if it is a custom :class:`PartialEmoji`.

        .. versionadded:: 2.6
        """
        return self._state._get_emoji_from_fields(
            name=self._default_reaction_emoji_name,
            id=self._default_reaction_emoji_id,
        )

    @property
    def last_thread(self) -> Thread | None:
        """Gets the last created thread in this channel from the cache.

        The thread might not be valid or point to an existing thread.

        .. admonition:: Reliable Fetching
            :class: helpful

            For a slightly more reliable method of fetching the
            last thread, use :meth:`Guild.fetch_channel` with the :attr:`last_thread_id`
            attribute.

        Returns
        -------
        :class:`Thread` | :data:`None`
            The last created thread in this channel or :data:`None` if not found.
        """
        return self._state.get_channel(self.last_thread_id) if self.last_thread_id else None  # pyright: ignore[reportReturnType]

    @property
    def available_tags(self) -> list[ForumTag]:
        r""":class:`list`\[:class:`ForumTag`]: The available tags for threads in this channel.

        To create/edit/delete tags, use :func:`edit`.

        .. versionadded:: 2.6
        """
        return list(self._available_tags.values())

    def get_thread(self, thread_id: int, /) -> Thread | None:
        """Returns a thread with the given ID.

        Parameters
        ----------
        thread_id: :class:`int`
            The ID to search for.

        Returns
        -------
        :class:`Thread` | :data:`None`
            The returned thread of :data:`None` if not found.
        """
        if isinstance(self.guild, Object):
            return None
        return self.guild.get_thread(thread_id)

    def archived_threads(
        self,
        *,
        limit: int | None = 50,
        before: Snowflake | datetime.datetime | None = None,
    ) -> ArchivedThreadIterator:
        """Returns an :class:`~disnake.AsyncIterator` that iterates over all archived threads in the channel.

        You must have :attr:`~Permissions.read_message_history` permission to use this.

        Parameters
        ----------
        limit: :class:`int` | :data:`None`
            The number of threads to retrieve.
            If :data:`None`, retrieves every archived thread in the channel. Note, however,
            that this would make it a slow operation.
        before: :class:`abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
            Retrieve archived channels before the given date or ID.

        Raises
        ------
        Forbidden
            You do not have permissions to get archived threads.
        HTTPException
            The request to get the archived threads failed.

        Yields
        ------
        :class:`Thread`
            The archived threads.
        """
        return ArchivedThreadIterator(
            self.id, self.guild, limit=limit, joined=False, private=False, before=before
        )

    def get_tag(self, tag_id: int, /) -> ForumTag | None:
        """Returns a thread tag with the given ID.

        .. versionadded:: 2.6

        Parameters
        ----------
        tag_id: :class:`int`
            The ID to search for.

        Returns
        -------
        :class:`ForumTag` | :data:`None`
            The tag with the given ID, or :data:`None` if not found.
        """
        return self._available_tags.get(tag_id)

    def get_tag_by_name(self, name: str, /) -> ForumTag | None:
        """Returns a thread tag with the given name.

        Tags can be uniquely identified based on the name, as tag names
        in a channel must be unique.

        .. versionadded:: 2.6

        Parameters
        ----------
        name: :class:`str`
            The name to search for.

        Returns
        -------
        :class:`ForumTag` | :data:`None`
            The tag with the given name, or :data:`None` if not found.
        """
        return utils.get(self._available_tags.values(), name=name)


class ForumChannel(ThreadOnlyGuildChannel):
    """Represents a Discord guild forum channel.

    .. versionadded:: 2.5

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the channel's hash.

        .. describe:: str(x)

            Returns the channel's name.

    Attributes
    ----------
    id: :class:`int`
        The channel's ID.
    name: :class:`str`
        The channel's name.
    guild: :class:`Guild`
        The guild the channel belongs to.
    topic: :class:`str` | :data:`None`
        The channel's topic. :data:`None` if it isn't set.
    category_id: :class:`int` | :data:`None`
        The category channel ID this channel belongs to, if applicable.
    position: :class:`int`
        The position in the channel list. This is a number that starts at 0. e.g. the
        top channel is position 0.
    nsfw: :class:`bool`
        Whether the channel is marked as "not safe for work".

        .. note::

            To check if the channel or the guild of that channel are marked as NSFW, consider :meth:`is_nsfw` instead.
    last_thread_id: :class:`int` | :data:`None`
        The ID of the last created thread in this channel. It may
        *not* point to an existing or valid thread.
    default_auto_archive_duration: :class:`int`
        The default auto archive duration in minutes for threads created in this channel.
    slowmode_delay: :class:`int`
        The number of seconds a member must wait between creating threads
        in this channel.

        A value of ``0`` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

        See also :attr:`default_thread_slowmode_delay`.

    default_thread_slowmode_delay: :class:`int`
        The default number of seconds a member must wait between sending messages
        in newly created threads in this channel.

        A value of ``0`` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

        .. versionadded:: 2.6

    default_sort_order: :class:`ThreadSortOrder` | :data:`None`
        The default sort order of threads in this channel.
        Members will still be able to change this locally.

        .. versionadded:: 2.6

    default_layout: :class:`ThreadLayout`
        The default layout of threads in this channel.
        Members will still be able to change this locally.

        .. versionadded:: 2.8
    """

    __slots__ = ("default_layout",)

    def _update(self, guild: Guild, data: ForumChannelPayload) -> None:
        super()._update(guild=guild, data=data)
        self.default_layout: ThreadLayout = (
            try_enum(ThreadLayout, layout)
            if (layout := data.get("default_forum_layout")) is not None
            else ThreadLayout.not_set
        )

    @property
    def type(self) -> Literal[ChannelType.forum]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.forum`.
        """
        return ChannelType.forum


class MediaChannel(ThreadOnlyGuildChannel):
    """Represents a Discord guild media channel.

    Media channels are very similar to forum channels - only threads can be created in them,
    with only minor differences in functionality.

    .. versionadded:: 2.10

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the channel's hash.

        .. describe:: str(x)

            Returns the channel's name.

    Attributes
    ----------
    id: :class:`int`
        The channel's ID.
    name: :class:`str`
        The channel's name.
    guild: :class:`Guild`
        The guild the channel belongs to.
    topic: :class:`str` | :data:`None`
        The channel's topic. :data:`None` if it isn't set.
    category_id: :class:`int` | :data:`None`
        The category channel ID this channel belongs to, if applicable.
    position: :class:`int`
        The position in the channel list. This is a number that starts at 0. e.g. the
        top channel is position 0.
    nsfw: :class:`bool`
        Whether the channel is marked as "not safe for work".

        .. note::

            To check if the channel or the guild of that channel are marked as NSFW, consider :meth:`is_nsfw` instead.
    last_thread_id: :class:`int` | :data:`None`
        The ID of the last created thread in this channel. It may
        *not* point to an existing or valid thread.
    default_auto_archive_duration: :class:`int`
        The default auto archive duration in minutes for threads created in this channel.
    slowmode_delay: :class:`int`
        The number of seconds a member must wait between creating threads
        in this channel.

        A value of ``0`` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

        See also :attr:`default_thread_slowmode_delay`.

    default_thread_slowmode_delay: :class:`int`
        The default number of seconds a member must wait between sending messages
        in newly created threads in this channel.

        A value of ``0`` denotes that it is disabled.
        Bots, and users with :attr:`~Permissions.bypass_slowmode` permissions, bypass slowmode.

    default_sort_order: :class:`ThreadSortOrder` | :data:`None`
        The default sort order of threads in this channel.
        Members will still be able to change this locally.
    """

    __slots__ = ()

    @property
    def type(self) -> Literal[ChannelType.media]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.media`.
        """
        return ChannelType.media

    def hides_media_download_options(self) -> bool:
        """Whether the channel hides the embedded media download options.

        This is a shortcut to :attr:`self.flags.hide_media_download_options <ChannelFlags.hide_media_download_options>`.

        :return type: :class:`bool`
        """
        return self.flags.hide_media_download_options


class DMChannel(disnake.abc.Messageable, Hashable):
    """Represents a Discord direct message channel.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the channel's hash.

        .. describe:: str(x)

            Returns a string representation of the channel

    Attributes
    ----------
    recipient: :class:`User` | :data:`None`
        The user you are participating with in the direct message channel.
        If this channel is received through the gateway, the recipient information
        may not be always available.
    me: :class:`ClientUser`
        The user presenting yourself.
    id: :class:`int`
        The direct message channel ID.
    last_pin_timestamp: :class:`datetime.datetime` | :data:`None`
        The time the most recent message was pinned, or :data:`None` if no message is currently pinned.

        .. versionadded:: 2.5
    """

    __slots__ = (
        "id",
        "recipient",
        "me",
        "last_pin_timestamp",
        "_state",
        "_flags",
    )

    def __init__(self, *, me: ClientUser, state: ConnectionState, data: DMChannelPayload) -> None:
        self._state: ConnectionState = state
        self.recipient: User | None = None
        if recipients := data.get("recipients"):
            self.recipient = state.store_user(recipients[0])  # pyright: ignore[reportArgumentType]

        self.me: ClientUser = me
        self.id: int = int(data["id"])
        self.last_pin_timestamp: datetime.datetime | None = utils.parse_time(
            data.get("last_pin_timestamp")
        )
        self._flags: int = data.get("flags", 0)

    async def _get_channel(self) -> Self:
        return self

    def __str__(self) -> str:
        if self.recipient:
            return f"Direct Message with {self.recipient}"
        return "Direct Message with Unknown User"

    def __repr__(self) -> str:
        return f"<DMChannel id={self.id} recipient={self.recipient!r}>"

    @classmethod
    def _from_message(cls, state: ConnectionState, channel_id: int, user_id: int) -> Self:
        self = cls.__new__(cls)
        self._state = state
        self.id = channel_id
        # state.user won't be None here
        self.me = state.user
        self.recipient = state.get_user(user_id) if user_id != self.me.id else None
        self.last_pin_timestamp = None
        self._flags = 0
        return self

    @property
    def type(self) -> Literal[ChannelType.private]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.private`.
        """
        return ChannelType.private

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns the direct message channel's creation time in UTC."""
        return utils.snowflake_time(self.id)

    @property
    def jump_url(self) -> str:
        """A URL that can be used to jump to this channel.

        .. versionadded:: 2.4
        """
        return f"https://discord.com/channels/@me/{self.id}"

    @property
    def flags(self) -> ChannelFlags:
        """:class:`.ChannelFlags`: The channel flags for this channel.

        .. versionadded:: 2.6
        """
        return ChannelFlags._from_value(self._flags)

    def permissions_for(
        self,
        obj: object = None,
        /,
        *,
        ignore_timeout: bool = MISSING,
    ) -> Permissions:
        """Handles permission resolution for a :class:`User`.

        This function is there for compatibility with other channel types.

        Actual direct messages do not really have the concept of permissions.

        This returns all the :meth:`Permissions.private_channel` permissions set to ``True``.

        Parameters
        ----------
        obj: :class:`User`
            The user to check permissions for. This parameter is ignored
            but kept for compatibility with other ``permissions_for`` methods.

        ignore_timeout: :class:`bool`
            Whether to ignore the guild timeout when checking permsisions.
            This parameter is ignored but kept for compatibility with other ``permissions_for`` methods.

        Returns
        -------
        :class:`Permissions`
            The resolved permissions.
        """
        return Permissions.private_channel()

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """Creates a :class:`PartialMessage` from the given message ID.

        This is useful if you want to work with a message and only have its ID without
        doing an unnecessary API call.

        .. versionadded:: 1.6

        Parameters
        ----------
        message_id: :class:`int`
            The message ID to create a partial message for.

        Returns
        -------
        :class:`PartialMessage`
            The partial message object.
        """
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


class GroupChannel(disnake.abc.Messageable, Hashable):
    r"""Represents a Discord group channel.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two channels are equal.

        .. describe:: x != y

            Checks if two channels are not equal.

        .. describe:: hash(x)

            Returns the channel's hash.

        .. describe:: str(x)

            Returns a string representation of the channel

    Attributes
    ----------
    recipients: :class:`list`\[:class:`User`]
        The users you are participating with in the group channel.
        If this channel is received through the gateway, the recipient information
        may not be always available.
    me: :class:`ClientUser`
        The user representing yourself.
    id: :class:`int`
        The group channel ID.
    owner: :class:`User` | :data:`None`
        The user that owns the group channel.
    owner_id: :class:`int`
        The owner ID that owns the group channel.

        .. versionadded:: 2.0

    name: :class:`str` | :data:`None`
        The group channel's name if provided.
    """

    __slots__ = ("id", "recipients", "owner_id", "owner", "_icon", "name", "me", "_state")

    def __init__(
        self, *, me: ClientUser, state: ConnectionState, data: GroupChannelPayload
    ) -> None:
        self._state: ConnectionState = state
        self.id: int = int(data["id"])
        self.me: ClientUser = me
        self._update_group(data)

    def _update_group(self, data: GroupChannelPayload) -> None:
        self.owner_id: int | None = utils._get_as_snowflake(data, "owner_id")
        self._icon: str | None = data.get("icon")
        self.name: str | None = data.get("name")
        self.recipients: list[User] = [
            self._state.store_user(u) for u in data.get("recipients", [])
        ]

        self.owner: BaseUser | None
        if self.owner_id == self.me.id:
            self.owner = self.me
        else:
            self.owner = utils.find(lambda u: u.id == self.owner_id, self.recipients)

    async def _get_channel(self) -> Self:
        return self

    def __str__(self) -> str:
        if self.name:
            return self.name

        if len(self.recipients) == 0:
            return "Unnamed"

        return ", ".join([x.name for x in self.recipients])

    def __repr__(self) -> str:
        return f"<GroupChannel id={self.id} name={self.name!r}>"

    @property
    def type(self) -> Literal[ChannelType.group]:
        """:class:`ChannelType`: The channel's Discord type.

        This always returns :attr:`ChannelType.group`.
        """
        return ChannelType.group

    @property
    def icon(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns the channel's icon asset if available."""
        if self._icon is None:
            return None
        return Asset._from_icon(self._state, self.id, self._icon, path="channel")

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns the channel's creation time in UTC."""
        return utils.snowflake_time(self.id)

    def permissions_for(
        self,
        obj: Snowflake,
        /,
        *,
        ignore_timeout: bool = MISSING,
    ) -> Permissions:
        """Handles permission resolution for a :class:`User`.

        This function is there for compatibility with other channel types.

        Actual direct messages do not really have the concept of permissions.

        This returns all the :meth:`Permissions.private_channel` permissions set to ``True``.

        This also checks the kick_members permission if the user is the owner.

        Parameters
        ----------
        obj: :class:`~disnake.abc.Snowflake`
            The user to check permissions for.

        ignore_timeout: :class:`bool`
            Whether to ignore the guild timeout when checking permsisions.
            This parameter is ignored but kept for compatibility with other ``permissions_for`` methods.

        Returns
        -------
        :class:`Permissions`
            The resolved permissions for the user.
        """
        base = Permissions.private_channel()

        if obj.id == self.owner_id:
            base.kick_members = True

        return base

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """Creates a :class:`PartialMessage` from the given message ID.

        This is useful if you want to work with a message and only have its ID without
        doing an unnecessary API call.

        .. versionadded:: 2.10

        Parameters
        ----------
        message_id: :class:`int`
            The message ID to create a partial message for.

        Returns
        -------
        :class:`PartialMessage`
            The partial message object.
        """
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


class PartialMessageable(disnake.abc.Messageable, Hashable):
    """Represents a partial messageable to aid with working messageable channels when
    only a channel ID is present.

    The only way to construct this class is through :meth:`Client.get_partial_messageable`.

    Note that this class is trimmed down and has no rich attributes.

    .. versionadded:: 2.0

    .. collapse:: operations

        .. describe:: x == y

            Checks if two partial messageables are equal.

        .. describe:: x != y

            Checks if two partial messageables are not equal.

        .. describe:: hash(x)

            Returns the partial messageable's hash.

    Attributes
    ----------
    id: :class:`int`
        The channel ID associated with this partial messageable.
    type: :class:`ChannelType` | :data:`None`
        The channel type associated with this partial messageable, if given.
    """

    def __init__(self, state: ConnectionState, id: int, type: ChannelType | None = None) -> None:
        self._state: ConnectionState = state
        self.id: int = id
        self.type: ChannelType | None = type

    async def _get_channel(self) -> Self:
        return self

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """Creates a :class:`PartialMessage` from the given message ID.

        This is useful if you want to work with a message and only have its ID without
        doing an unnecessary API call.

        Parameters
        ----------
        message_id: :class:`int`
            The message ID to create a partial message for.

        Returns
        -------
        :class:`PartialMessage`
            The partial message object.
        """
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


def _guild_channel_factory(
    channel_type: int,
) -> tuple[type[GuildChannelType] | None, ChannelType]:
    value = try_enum(ChannelType, channel_type)
    if value is ChannelType.text:
        return TextChannel, value
    elif value is ChannelType.voice:
        return VoiceChannel, value
    elif value is ChannelType.category:
        return CategoryChannel, value
    elif value is ChannelType.news:
        return TextChannel, value
    elif value is ChannelType.stage_voice:
        return StageChannel, value
    elif value is ChannelType.forum:
        return ForumChannel, value
    elif value is ChannelType.media:
        return MediaChannel, value
    else:
        return None, value


def _channel_factory(
    channel_type: int,
) -> tuple[type[GuildChannelType | DMChannel | GroupChannel] | None, ChannelType]:
    cls, value = _guild_channel_factory(channel_type)
    if value is ChannelType.private:
        return DMChannel, value
    elif value is ChannelType.group:
        return GroupChannel, value
    else:
        return cls, value


def _threaded_channel_factory(
    channel_type: int,
) -> tuple[type[GuildChannelType | DMChannel | GroupChannel | Thread] | None, ChannelType]:
    cls, value = _channel_factory(channel_type)
    if value in (ChannelType.private_thread, ChannelType.public_thread, ChannelType.news_thread):
        return Thread, value
    return cls, value


def _threaded_guild_channel_factory(
    channel_type: int,
) -> tuple[type[GuildChannelType | Thread] | None, ChannelType]:
    cls, value = _guild_channel_factory(channel_type)
    if value in (ChannelType.private_thread, ChannelType.public_thread, ChannelType.news_thread):
        return Thread, value
    return cls, value


def _channel_type_factory(cls: type[disnake.abc.GuildChannel | Thread]) -> list[ChannelType]:
    return {
        # FIXME: this includes private channels; improve this once there's a common base type for all channels
        disnake.abc.GuildChannel: list(ChannelType.__members__.values()),
        VocalGuildChannel: [ChannelType.voice, ChannelType.stage_voice],
        disnake.abc.PrivateChannel: [ChannelType.private, ChannelType.group],
        TextChannel: [ChannelType.text, ChannelType.news],
        DMChannel: [ChannelType.private],
        VoiceChannel: [ChannelType.voice],
        GroupChannel: [ChannelType.group],
        CategoryChannel: [ChannelType.category],
        NewsChannel: [ChannelType.news],
        Thread: [ChannelType.news_thread, ChannelType.public_thread, ChannelType.private_thread],
        StageChannel: [ChannelType.stage_voice],
        ForumChannel: [ChannelType.forum],
        MediaChannel: [ChannelType.media],
    }.get(cls, [])
