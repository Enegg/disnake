# SPDX-License-Identifier: MIT

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    NamedTuple,
    TypeAlias,
    overload,
)

from . import utils
from .app_commands import GuildApplicationCommandPermissions
from .asset import Asset
from .channel import (
    CategoryChannel,
    ForumChannel,
    MediaChannel,
    StageChannel,
    TextChannel,
    VoiceChannel,
    _guild_channel_factory,
    _threaded_guild_channel_factory,
)
from .emoji import Emoji
from .enums import (
    ChannelType,
    ContentFilter,
    Locale,
    NotificationLevel,
    NSFWLevel,
    VerificationLevel,
    try_enum,
)
from .errors import ClientException, HTTPException, InvalidData
from .flags import SystemChannelFlags
from .iterators import MemberIterator
from .member import Member
from .mixins import Hashable
from .role import Role
from .threads import Thread

__all__ = ("Guild",)

VocalGuildChannel: TypeAlias = VoiceChannel | StageChannel
MISSING = utils.MISSING

if TYPE_CHECKING:
    from .abc import Snowflake, SnowflakeTime
    from .app_commands import APIApplicationCommand
    from .state import ConnectionState
    from .types.channel import GuildChannel as GuildChannelPayload
    from .types.guild import Guild as GuildPayload, GuildFeature, MFALevel
    from .types.threads import Thread as ThreadPayload
    from .webhook import Webhook

    GuildMessageable: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
    GuildChannel: TypeAlias = (
        VoiceChannel | StageChannel | TextChannel | CategoryChannel | ForumChannel | MediaChannel
    )
    ByCategoryItem: TypeAlias = tuple[CategoryChannel | None, list[GuildChannel]]


class _GuildLimit(NamedTuple):
    emoji: int
    stickers: int
    bitrate: float
    filesize: int
    sounds: int


class Guild(Hashable):
    r"""Represents a Discord guild.

    This is referred to as a "server" in the official Discord UI.

    .. collapse:: operations

        .. describe:: x == y

            Checks if two guilds are equal.

        .. describe:: x != y

            Checks if two guilds are not equal.

        .. describe:: hash(x)

            Returns the guild's hash.

        .. describe:: str(x)

            Returns the guild's name.

    Attributes
    ----------
    name: :class:`str`
        The guild's name.
    emojis: :class:`tuple`\[:class:`Emoji`, ...]
        All emojis that the guild owns.
    stickers: :class:`tuple`\[:class:`GuildSticker`, ...]
        All stickers that the guild owns.

        .. versionadded:: 2.0

    soundboard_sounds: :class:`tuple`\[:class:`GuildSoundboardSound`, ...]
        All soundboard sounds that the guild owns.

        .. versionadded:: 2.10

    afk_timeout: :class:`int`
        The timeout to get sent to the AFK channel.
    afk_channel: :class:`VoiceChannel` | :data:`None`
        The channel that denotes the AFK channel. :data:`None` if it doesn't exist.
    id: :class:`int`
        The guild's ID.
    owner_id: :class:`int` | :data:`None`
        The guild owner's ID. Use :attr:`Guild.owner` if you need a :class:`Member` object instead.
        This may be :data:`None` if the guild is :attr:`~Guild.unavailable`.
    unavailable: :class:`bool`
        Whether the guild is unavailable. If this is ``True`` then the
        reliability of other attributes outside of :attr:`Guild.id` is slim and they might
        all be :data:`None`. It is best to not do anything with the guild if it is unavailable.

        Check :func:`on_guild_unavailable` and :func:`on_guild_available` events.
    max_presences: :class:`int` | :data:`None`
        The maximum amount of presences for the guild.
    max_members: :class:`int` | :data:`None`
        The maximum amount of members for the guild.

        .. note::

            This attribute is only available via :meth:`.Client.fetch_guild`.
    max_video_channel_users: :class:`int` | :data:`None`
        The maximum amount of users in a video channel.

        .. versionadded:: 1.4

    max_stage_video_channel_users: :class:`int` | :data:`None`
        The maximum amount of users in a stage video channel.

        .. versionadded: 2.9

    description: :class:`str` | :data:`None`
        The guild's description.
    mfa_level: :class:`int`
        Indicates the guild's two-factor authentication level. If this value is 0 then
        the guild does not require 2FA for their administrative members
        to take moderation actions. If the value is 1, then 2FA is required.
    verification_level: :class:`VerificationLevel`
        The guild's verification level.
    explicit_content_filter: :class:`ContentFilter`
        The guild's explicit content filter.
    default_notifications: :class:`NotificationLevel`
        The guild's notification settings.
    features: :class:`list`\[:class:`str`]
        A list of features that the guild has. The features that a guild can have are
        subject to arbitrary change by Discord.

        A partial list of features is below:

        - ``ANIMATED_BANNER``: Guild can upload an animated banner.
        - ``ANIMATED_ICON``: Guild can upload an animated icon.
        - ``AUTO_MODERATION``: Guild has set up auto moderation rules.
        - ``BANNER``: Guild can upload and use a banner. (i.e. :attr:`.banner`)
        - ``COMMUNITY``: Guild is a community server.
        - ``CREATOR_MONETIZABLE_PROVISIONAL``: Guild has enabled monetization.
        - ``CREATOR_STORE_PAGE``: Guild has enabled the role subscription promo page.
        - ``DEVELOPER_SUPPORT_SERVER``: Guild is set as a support server in the app directory.
        - ``DISCOVERABLE``: Guild shows up in Server Discovery.
        - ``ENABLED_DISCOVERABLE_BEFORE``: Guild had Server Discovery enabled at least once.
        - ``FEATURABLE``: Guild is able to be featured in Server Discovery.
        - ``HAS_DIRECTORY_ENTRY``: Guild is listed in a student hub.
        - ``HUB``: Guild is a student hub.
        - ``INVITE_SPLASH``: Guild's invite page can have a special splash.
        - ``INVITES_DISABLED``: Guild has paused invites, preventing new users from joining.
        - ``LINKED_TO_HUB``: Guild is linked to a student hub.
        - ``MEMBER_VERIFICATION_GATE_ENABLED``: Guild has Membership Screening enabled.
        - ``MORE_EMOJI``: Guild has increased custom emoji slots.
        - ``MORE_SOUNDBOARD``: Guild has increased custom soundboard slots.
        - ``MORE_STICKERS``: Guild has increased custom sticker slots.
        - ``NEWS``: Guild can create news channels.
        - ``NEW_THREAD_PERMISSIONS``: Guild is using the new thread permission system.
        - ``PARTNERED``: Guild is a partnered server.
        - ``PREVIEW_ENABLED``: Guild can be viewed before being accepted via Membership Screening.
        - ``PRIVATE_THREADS``: Guild has access to create private threads (no longer has any effect).
        - ``RAID_ALERTS_DISABLED``: Guild has disabled alerts for join raids in the configured safety alerts channel.
        - ``ROLE_ICONS``: Guild has access to role icons.
        - ``ROLE_SUBSCRIPTIONS_AVAILABLE_FOR_PURCHASE``: Guild has role subscriptions that can be purchased.
        - ``ROLE_SUBSCRIPTIONS_ENABLED``: Guild has enabled role subscriptions.
        - ``SEVEN_DAY_THREAD_ARCHIVE``: Guild has access to the seven day archive time for threads (no longer has any effect).
        - ``SOUNDBOARD``: Guild has created soundboard sounds.
        - ``TEXT_IN_VOICE_ENABLED``: Guild has text in voice channels enabled (no longer has any effect).
        - ``THREE_DAY_THREAD_ARCHIVE``: Guild has access to the three day archive time for threads (no longer has any effect).
        - ``THREADS_ENABLED``: Guild has access to threads (no longer has any effect).
        - ``TICKETED_EVENTS_ENABLED``: Guild has enabled ticketed events (no longer has any effect).
        - ``VANITY_URL``: Guild can have a vanity invite URL (e.g. discord.gg/disnake).
        - ``VERIFIED``: Guild is a verified server.
        - ``VIP_REGIONS``: Guild has VIP voice regions.
        - ``WELCOME_SCREEN_ENABLED``: Guild has enabled the welcome screen.
    premium_progress_bar_enabled: :class:`bool`
        Whether the server boost progress bar is enabled.
    premium_tier: :class:`int`
        The premium tier for this guild. Corresponds to "Nitro Server" in the official UI.
        The number goes from 0 to 3 inclusive.
    premium_subscription_count: :class:`int`
        The number of "boosts" this guild currently has.
    preferred_locale: :class:`Locale`
        The preferred locale for the guild. Used when filtering Server Discovery
        results to a specific language.

        .. versionchanged:: 2.5
            Changed to :class:`Locale` instead of :class:`str`.

    nsfw_level: :class:`NSFWLevel`
        The guild's NSFW level.

        .. versionadded:: 2.0

    approximate_member_count: :class:`int` | :data:`None`
        The approximate number of members in the guild.
        Only available for manually fetched guilds.

        .. versionadded:: 2.3

    approximate_presence_count: :class:`int` | :data:`None`
        The approximate number of members currently active in the guild.
        This includes idle, dnd, online, and invisible members. Offline members are excluded.
        Only available for manually fetched guilds.

        .. versionadded:: 2.3

    widget_enabled: :class:`bool` | :data:`None`
        Whether the widget is enabled.

        .. versionadded:: 2.5

        .. note::

            This value is unreliable and will only be set after the guild was updated at least once.
            Avoid using this and use :func:`widget_settings` instead.

    widget_channel_id: :class:`int` | :data:`None`
        The widget channel ID, if set.

        .. versionadded:: 2.5

        .. note::

            This value is unreliable and will only be set after the guild was updated at least once.
            Avoid using this and use :func:`widget_settings` instead.

    vanity_url_code: :class:`str` | :data:`None`
        The vanity invite code for this guild, if set.

        To get a full :class:`Invite` object, see :attr:`Guild.vanity_invite`.

        .. versionadded:: 2.5

    incidents_data: :class:`IncidentsData` | :data:`None`
        Data about various security incidents/actions in this guild, like disabled invites/DMs.

        .. versionadded:: 2.11
    """

    __slots__ = (
        "afk_timeout",
        "afk_channel",
        "name",
        "id",
        "unavailable",
        "owner_id",
        "mfa_level",
        "emojis",
        "features",
        "verification_level",
        "explicit_content_filter",
        "default_notifications",
        "description",
        "max_presences",
        "max_members",
        "max_video_channel_users",
        "max_stage_video_channel_users",
        "premium_progress_bar_enabled",
        "premium_tier",
        "premium_subscription_count",
        "preferred_locale",
        "nsfw_level",
        "approximate_member_count",
        "approximate_presence_count",
        "widget_enabled",
        "widget_channel_id",
        "vanity_url_code",
        "incidents_data",
        "_members",
        "_channels",
        "_icon",
        "_banner",
        "_state",
        "_roles",
        "_member_count",
        "_large",
        "_splash",
        "_voice_states",
        "_system_channel_id",
        "_system_channel_flags",
        "_discovery_splash",
        "_rules_channel_id",
        "_public_updates_channel_id",
        "_stage_instances",
        "_scheduled_events",
        "_threads",
        "_region",
        "_safety_alerts_channel_id",
    )

    _PREMIUM_GUILD_LIMITS: ClassVar[dict[int | None, _GuildLimit]] = {
        None: _GuildLimit(emoji=50, stickers=5, bitrate=96e3, filesize=10485760, sounds=8),
        0: _GuildLimit(emoji=50, stickers=5, bitrate=96e3, filesize=10485760, sounds=8),
        1: _GuildLimit(emoji=100, stickers=15, bitrate=128e3, filesize=10485760, sounds=24),
        2: _GuildLimit(emoji=150, stickers=30, bitrate=256e3, filesize=52428800, sounds=36),
        3: _GuildLimit(emoji=250, stickers=60, bitrate=384e3, filesize=104857600, sounds=48),
    }

    def __init__(self, *, data: GuildPayload, state: ConnectionState) -> None:
        self._channels: dict[int, GuildChannel] = {}
        self._members: dict[int, Member] = {}
        self._threads: dict[int, Thread] = {}
        self._state: ConnectionState = state
        self._from_data(data)

    def _add_channel(self, channel: GuildChannel, /) -> None:
        self._channels[channel.id] = channel

    def _remove_channel(self, channel: Snowflake, /) -> None:
        self._channels.pop(channel.id, None)

    def _add_member(self, member: Member, /) -> None:
        self._members[member.id] = member

    def _store_thread(self, payload: ThreadPayload, /) -> Thread:
        thread = Thread(guild=self, state=self._state, data=payload)
        self._threads[thread.id] = thread
        return thread

    def _remove_member(self, member: Snowflake, /) -> None:
        self._members.pop(member.id, None)

    def _add_thread(self, thread: Thread, /) -> None:
        self._threads[thread.id] = thread

    def _remove_thread(self, thread: Snowflake, /) -> None:
        self._threads.pop(thread.id, None)

    def _clear_threads(self) -> None:
        self._threads.clear()

    def _remove_threads_by_channel(self, channel_id: int) -> None:
        to_remove = [k for k, t in self._threads.items() if t.parent_id == channel_id]
        for k in to_remove:
            del self._threads[k]

    def _filter_threads(self, channel_ids: set[int]) -> dict[int, Thread]:
        to_remove: dict[int, Thread] = {
            k: t for k, t in self._threads.items() if t.parent_id in channel_ids
        }
        for k in to_remove:
            del self._threads[k]
        return to_remove

    def __str__(self) -> str:
        return self.name or ""

    def __repr__(self) -> str:
        attrs = (
            ("id", self.id),
            ("name", self.name),
            ("shard_id", self.shard_id),
            ("chunked", self.chunked),
            ("member_count", getattr(self, "_member_count", None)),
        )
        inner = " ".join(f"{k!s}={v!r}" for k, v in attrs)
        return f"<Guild {inner}>"

    def _add_role(self, role: Role, /) -> None:
        # roles get added to the bottom (position 1, pos 0 is @everyone)
        # so since self.roles has the @everyone role, we can't increment
        # its position because it's stuck at position 0. Luckily x += False
        # is equivalent to adding 0. So we cast the position to a bool and
        # increment it.
        for r in self._roles.values():
            r.position += not r.is_default()

        self._roles[role.id] = role

    def _remove_role(self, role_id: int, /) -> Role:
        # this raises KeyError if it fails..
        role = self._roles.pop(role_id)

        # since it didn't, we can change the positions now
        # basically the same as above except we only decrement
        # the position if we're above the role we deleted.
        for r in self._roles.values():
            r.position -= r.position > role.position

        return role

    def get_command(self, application_command_id: int, /) -> APIApplicationCommand | None:
        """Gets a cached application command matching the specified ID.

        Parameters
        ----------
        application_command_id: :class:`int`
            The application command ID to search for.

        Returns
        -------
        :class:`.APIUserCommand` | :class:`.APIMessageCommand` | :class:`.APISlashCommand` | :data:`None`
            The application command if found, or :data:`None` otherwise.
        """
        return self._state._get_guild_application_command(self.id, application_command_id)

    def get_command_named(self, name: str, /) -> APIApplicationCommand | None:
        """Gets a cached application command matching the specified name.

        Parameters
        ----------
        name: :class:`str`
            The application command name to search for.

        Returns
        -------
        :class:`.APIUserCommand` | :class:`.APIMessageCommand` | :class:`.APISlashCommand` | :data:`None`
            The application command if found, or :data:`None` otherwise.
        """
        return self._state._get_guild_command_named(self.id, name)

    def _from_data(self, guild: GuildPayload) -> None:
        # according to Stan, this is always available even if the guild is unavailable
        # I don't have this guarantee when someone updates the guild.
        member_count = guild.get("member_count", None)
        if member_count is not None:
            self._member_count: int = member_count

        self.name: str = guild.get("name", "")
        self._region: str = guild.get("region", "")
        self.verification_level: VerificationLevel = try_enum(
            VerificationLevel, guild.get("verification_level")
        )
        self.default_notifications: NotificationLevel = try_enum(
            NotificationLevel, guild.get("default_message_notifications")
        )
        self.explicit_content_filter: ContentFilter = try_enum(
            ContentFilter, guild.get("explicit_content_filter", 0)
        )
        self.afk_timeout: int = guild.get("afk_timeout", 0)
        self._icon: str | None = guild.get("icon")
        self._banner: str | None = guild.get("banner")
        self.unavailable: bool = guild.get("unavailable", False)
        self.id: int = int(guild["id"])
        self._roles: dict[int, Role] = {}
        state = self._state  # speed up attribute access
        for r in guild.get("roles", []):
            role = Role(guild=self, data=r, state=state)
            self._roles[role.id] = role

        self.mfa_level: MFALevel = guild.get("mfa_level", 0)
        self.emojis: tuple[Emoji, ...] = tuple(
            state.store_emoji(self, d) for d in guild.get("emojis", [])
        )
        self.features: list[GuildFeature] = guild.get("features", [])
        self._splash: str | None = guild.get("splash")
        self._system_channel_id: int | None = utils._get_as_snowflake(guild, "system_channel_id")
        self.description: str | None = guild.get("description")
        self.max_presences: int | None = guild.get("max_presences")
        self.max_members: int | None = guild.get("max_members")
        self.max_video_channel_users: int | None = guild.get("max_video_channel_users")
        self.max_stage_video_channel_users: int | None = guild.get("max_stage_video_channel_users")
        self.premium_tier: int = guild.get("premium_tier", 0)
        self.premium_subscription_count: int = guild.get("premium_subscription_count") or 0
        self._system_channel_flags: int = guild.get("system_channel_flags", 0)
        self.preferred_locale: Locale = try_enum(Locale, guild.get("preferred_locale"))
        self._discovery_splash: str | None = guild.get("discovery_splash")
        self._rules_channel_id: int | None = utils._get_as_snowflake(guild, "rules_channel_id")
        self._public_updates_channel_id: int | None = utils._get_as_snowflake(
            guild, "public_updates_channel_id"
        )
        self.nsfw_level: NSFWLevel = try_enum(NSFWLevel, guild.get("nsfw_level", 0))
        self.premium_progress_bar_enabled: bool = guild.get("premium_progress_bar_enabled", False)
        self.approximate_presence_count: int | None = guild.get("approximate_presence_count")
        self.approximate_member_count: int | None = guild.get("approximate_member_count")
        self.widget_enabled: bool | None = guild.get("widget_enabled")
        self.widget_channel_id: int | None = utils._get_as_snowflake(guild, "widget_channel_id")
        self.vanity_url_code: str | None = guild.get("vanity_url_code")
        self._safety_alerts_channel_id: int | None = utils._get_as_snowflake(
            guild, "safety_alerts_channel_id"
        )

        cache_joined = self._state.member_cache_flags.joined
        self_id = self._state.self_id
        for mdata in guild.get("members", []):
            # NOTE: Are we sure it's fine to not have the user part here?
            member = Member(data=mdata, guild=self, state=state)  # pyright: ignore[reportArgumentType]
            if cache_joined or member.id == self_id:
                self._add_member(member)

        self._sync(guild)
        self._large: bool | None = None if member_count is None else self._member_count >= 250

        self.owner_id: int | None = utils._get_as_snowflake(guild, "owner_id")
        self.afk_channel: VocalGuildChannel | None = self.get_channel(
            utils._get_as_snowflake(guild, "afk_channel_id")  # pyright: ignore[reportAttributeAccessIssue, reportArgumentType]
        )

    # TODO: refactor/remove?
    def _sync(self, data: GuildPayload) -> None:
        if "large" in data:
            self._large = data["large"]

        empty_tuple = ()
        for presence in data.get("presences", []):
            user_id = int(presence["user"]["id"])
            member = self.get_member(user_id)
            if member is not None:
                member._presence_update(presence, empty_tuple)  # pyright: ignore[reportArgumentType]

        if "channels" in data:
            channels = data["channels"]
            for c in channels:
                factory, _ = _guild_channel_factory(c["type"])
                if factory:
                    self._add_channel(factory(guild=self, data=c, state=self._state))  # pyright: ignore[reportArgumentType]

        if "threads" in data:
            threads = data["threads"]
            for thread in threads:
                self._add_thread(Thread(guild=self, state=self._state, data=thread))

    @property
    def channels(self) -> list[GuildChannel]:
        r""":class:`list`\[:class:`abc.GuildChannel`]: A list of channels that belong to this guild."""
        return list(self._channels.values())

    @property
    def threads(self) -> list[Thread]:
        r""":class:`list`\[:class:`Thread`]: A list of threads that you have permission to view.

        .. versionadded:: 2.0
        """
        return list(self._threads.values())

    @property
    def large(self) -> bool:
        """:class:`bool`: Whether the guild is a 'large' guild.

        A large guild is defined as having more than ``large_threshold`` count
        members, which for this library is set to the maximum of 250.
        """
        if self._large is None:
            try:
                return self._member_count >= 250
            except AttributeError:
                return len(self._members) >= 250
        return self._large

    @property
    def me(self) -> Member:
        """:class:`Member`: Similar to :attr:`Client.user` except an instance of :class:`Member`.
        This is essentially used to get the member version of yourself.
        """
        self_id = self._state.user.id
        # The self member is *always* cached
        return self.get_member(self_id)  # pyright: ignore[reportReturnType]

    @property
    def text_channels(self) -> list[TextChannel]:
        r""":class:`list`\[:class:`TextChannel`]: A list of text channels that belong to this guild.

        This is sorted by the position and are in UI order from top to bottom.
        """
        r = [ch for ch in self._channels.values() if isinstance(ch, TextChannel)]
        r.sort(key=lambda c: (c.position, c.id))
        return r

    def by_category(self) -> list[ByCategoryItem]:
        r"""Returns every :class:`CategoryChannel` and their associated channels.

        These channels and categories are sorted in the official Discord UI order.

        If the channels do not have a category, then the first element of the tuple is
        :data:`None`.

        Returns
        -------
        :class:`list`\[:class:`tuple`\[:class:`CategoryChannel` | :data:`None`, :class:`list`\[:class:`abc.GuildChannel`]]]:
            The categories and their associated channels.
        """
        grouped: dict[int | None, list[GuildChannel]] = {}
        for channel in self._channels.values():
            if isinstance(channel, CategoryChannel):
                grouped.setdefault(channel.id, [])
                continue

            try:
                grouped[channel.category_id].append(channel)
            except KeyError:
                grouped[channel.category_id] = [channel]

        def key(t: ByCategoryItem) -> tuple[tuple[int, int], list[GuildChannel]]:
            k, v = t
            return ((k.position, k.id) if k else (-1, -1), v)

        _get = self._channels.get
        as_list: list[ByCategoryItem] = [(_get(k), v) for k, v in grouped.items()]  # pyright: ignore[reportAssignmentType, reportArgumentType]
        as_list.sort(key=key)
        for _, channels in as_list:
            channels.sort(key=lambda c: (c._sorting_bucket, c.position, c.id))
        return as_list

    def _resolve_channel(self, id: int | None, /) -> GuildChannel | Thread | None:
        if id is None:
            return None

        return self._channels.get(id) or self._threads.get(id)

    def get_channel_or_thread(self, channel_id: int, /) -> Thread | GuildChannel | None:
        """Returns a channel or thread with the given ID.

        .. versionadded:: 2.0

        Parameters
        ----------
        channel_id: :class:`int`
            The ID to search for.

        Returns
        -------
        :class:`Thread` | :class:`.abc.GuildChannel` | :data:`None`
            The returned channel or thread or :data:`None` if not found.
        """
        return self._channels.get(channel_id) or self._threads.get(channel_id)

    def get_channel(self, channel_id: int, /) -> GuildChannel | None:
        """Returns a channel with the given ID.

        .. note::

            This does *not* search for threads.

        Parameters
        ----------
        channel_id: :class:`int`
            The ID to search for.

        Returns
        -------
        :class:`.abc.GuildChannel` | :data:`None`
            The returned channel or :data:`None` if not found.
        """
        return self._channels.get(channel_id)

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
        return self._threads.get(thread_id)

    @property
    def system_channel(self) -> TextChannel | None:
        """:class:`TextChannel` | :data:`None`: Returns the guild's channel used for system messages.

        If no channel is set, then this returns :data:`None`.
        """
        channel_id = self._system_channel_id
        return channel_id and self._channels.get(channel_id)  # pyright: ignore[reportReturnType]

    @property
    def system_channel_flags(self) -> SystemChannelFlags:
        """:class:`SystemChannelFlags`: Returns the guild's system channel settings."""
        return SystemChannelFlags._from_value(self._system_channel_flags)

    @property
    def rules_channel(self) -> TextChannel | None:
        """:class:`TextChannel` | :data:`None`: Returns the guild's channel used for the rules.
        The guild must be a Community guild.

        If no channel is set, then this returns :data:`None`.

        .. versionadded:: 1.3
        """
        channel_id = self._rules_channel_id
        return channel_id and self._channels.get(channel_id)  # pyright: ignore[reportReturnType]

    @property
    def public_updates_channel(self) -> TextChannel | None:
        """:class:`TextChannel` | :data:`None`: Returns the guild's channel where admins and
        moderators of the guild receive notices from Discord. The guild must be a
        Community guild.

        If no channel is set, then this returns :data:`None`.

        .. versionadded:: 1.4
        """
        channel_id = self._public_updates_channel_id
        return channel_id and self._channels.get(channel_id)  # pyright: ignore[reportReturnType]

    @property
    def safety_alerts_channel(self) -> TextChannel | None:
        """:class:`TextChannel` | :data:`None`: Returns the guild's channel where admins and
        moderators of the guild receive safety alerts from Discord. The guild must be a
        Community guild.

        If no channel is set, then this returns :data:`None`.

        .. versionadded:: 2.9
        """
        channel_id = self._safety_alerts_channel_id
        return channel_id and self._channels.get(channel_id)  # pyright: ignore[reportReturnType]

    @property
    def emoji_limit(self) -> int:
        """:class:`int`: The maximum number of emoji slots this guild has.

        Premium emojis (i.e. those associated with subscription roles) count towards a
        separate limit of 25.
        """
        more_emoji = 200 if "MORE_EMOJI" in self.features else 50
        return max(more_emoji, self._PREMIUM_GUILD_LIMITS[self.premium_tier].emoji)

    @property
    def sticker_limit(self) -> int:
        """:class:`int`: The maximum number of sticker slots this guild has.

        .. versionadded:: 2.0
        """
        more_stickers = 60 if "MORE_STICKERS" in self.features else 0
        return max(more_stickers, self._PREMIUM_GUILD_LIMITS[self.premium_tier].stickers)

    @property
    def bitrate_limit(self) -> float:
        """:class:`float`: The maximum bitrate for voice channels this guild can have.
        For stage channels, the maximum bitrate is 64000.
        """
        vip_guild = self._PREMIUM_GUILD_LIMITS[3].bitrate if "VIP_REGIONS" in self.features else 0
        return max(vip_guild, self._PREMIUM_GUILD_LIMITS[self.premium_tier].bitrate)

    @property
    def filesize_limit(self) -> int:
        """:class:`int`: The maximum number of bytes files can have when uploaded to this guild."""
        return self._PREMIUM_GUILD_LIMITS[self.premium_tier].filesize

    @property
    def members(self) -> list[Member]:
        r""":class:`list`\[:class:`Member`]: A list of members that belong to this guild."""
        return list(self._members.values())

    def get_member(self, user_id: int, /) -> Member | None:
        """Returns a member with the given ID.

        Parameters
        ----------
        user_id: :class:`int`
            The ID to search for.

        Returns
        -------
        :class:`Member` | :data:`None`
            The member or :data:`None` if not found.
        """
        return self._members.get(user_id)

    @property
    def roles(self) -> list[Role]:
        r""":class:`list`\[:class:`Role`]: Returns a :class:`list` of the guild's roles in hierarchy order.

        The first element of this list will be the lowest role in the
        hierarchy.
        """
        return sorted(self._roles.values())

    def get_role(self, role_id: int, /) -> Role | None:
        """Returns a role with the given ID.

        Parameters
        ----------
        role_id: :class:`int`
            The ID to search for.

        Returns
        -------
        :class:`Role` | :data:`None`
            The role or :data:`None` if not found.
        """
        return self._roles.get(role_id)

    @property
    def default_role(self) -> Role:
        """:class:`Role`: Gets the @everyone role that all members have by default."""
        # The @everyone role is *always* given
        return self.get_role(self.id)  # pyright: ignore[reportReturnType]

    @property
    def premium_subscriber_role(self) -> Role | None:
        """:class:`Role` | :data:`None`: Gets the premium subscriber role, AKA "boost" role, in this guild, if any.

        .. versionadded:: 1.6
        """
        for role in self._roles.values():
            if role.is_premium_subscriber():
                return role
        return None

    @property
    def self_role(self) -> Role | None:
        """:class:`Role` | :data:`None`: Gets the role associated with this client's user, if any.

        .. versionadded:: 1.6
        """
        self_id = self._state.self_id
        for role in self._roles.values():
            tags = role.tags
            if tags and tags.bot_id == self_id:
                return role
        return None

    @property
    def owner(self) -> Member | None:
        """:class:`Member` | :data:`None`: Returns the member that owns the guild."""
        return self.get_member(self.owner_id)  # pyright: ignore[reportArgumentType]

    @property
    def icon(self) -> Asset | None:
        """:class:`Asset` | :data:`None`: Returns the guild's icon asset, if available."""
        if self._icon is None:
            return None
        return Asset._from_guild_icon(self._state, self.id, self._icon)

    @property
    def member_count(self) -> int:
        """:class:`int`: Returns the true member count regardless of it being loaded fully or not.

        .. warning::

            Due to a Discord limitation, in order for this attribute to remain up-to-date and
            accurate, it requires :attr:`Intents.members` to be specified.
        """
        try:
            return self._member_count
        except AttributeError:
            return len(self._members)

    @property
    def region(self) -> str:
        """:class:`str` | :data:`None`: The region the guild belongs on.

        .. deprecated:: 2.5

            VoiceRegion is no longer set on the guild, and is set on the individual voice channels instead.
            See :attr:`VoiceChannel.rtc_region` and :attr:`StageChannel.rtc_region` instead.

        .. versionchanged:: 2.5
            No longer a ``VoiceRegion`` instance.
        """
        utils.warn_deprecated(
            "Guild.region is deprecated and will be removed in a future version.", stacklevel=2
        )
        return self._region

    @property
    def chunked(self) -> bool:
        """:class:`bool`: Whether the guild is "chunked".

        A chunked guild means that :attr:`member_count` is equal to the
        number of members stored in the internal :attr:`members` cache.

        If this value returns ``False``, then you should request for
        offline members.
        """
        count = getattr(self, "_member_count", None)
        if count is None:
            return False
        return count == len(self._members)

    @property
    def shard_id(self) -> int:
        """:class:`int`: Returns the shard ID for this guild if applicable."""
        count = self._state.shard_count
        if count is None:
            return 0
        return (self.id >> 22) % count

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns the guild's creation time in UTC."""
        return utils.snowflake_time(self.id)

    def get_member_named(self, name: str, /) -> Member | None:
        """Returns the first member found that matches the name provided.

        The lookup strategy is as follows (in order):

        1. Lookup by nickname.
        2. Lookup by global name.
        3. Lookup by username.

        The name can have an optional discriminator argument, e.g. "Jake#0001",
        in which case it will be treated as a username + discriminator combo
        (note: this only works with usernames, not nicknames).

        If no member is found, :data:`None` is returned.

        .. versionchanged:: 2.9
            Now takes :attr:`User.global_name` into account.

        Parameters
        ----------
        name: :class:`str`
            The name of the member to lookup (with an optional discriminator).

        Returns
        -------
        :class:`Member` | :data:`None`
            The member in this guild with the associated name. If not found
            then :data:`None` is returned.
        """
        username, _, discriminator = name.rpartition("#")
        if username and (
            discriminator == "0" or (len(discriminator) == 4 and discriminator.isdecimal())
        ):
            # legacy behavior
            result = utils.get(self._members.values(), name=username, discriminator=discriminator)
            if result is not None:
                return result

        def pred(m: Member) -> bool:
            return m.nick == name or m.global_name == name or m.name == name

        return utils.find(pred, self._members.values())

    async def leave(self) -> None:
        """|coro|

        Leaves the guild.

        .. note::

            You cannot leave the guild that you own, you must delete it instead
            via :meth:`delete`.

        Raises
        ------
        HTTPException
            Leaving the guild failed.
        """
        await self._state.http.leave_guild(self.id)

    async def fetch_channels(self) -> Sequence[GuildChannel]:
        r"""|coro|

        Retrieves all :class:`abc.GuildChannel` that the guild has.

        .. note::

            This method is an API call. For general usage, consider :attr:`channels` instead.

        .. versionadded:: 1.2

        Raises
        ------
        InvalidData
            An unknown channel type was received from Discord.
        HTTPException
            Retrieving the channels failed.

        Returns
        -------
        :class:`~collections.abc.Sequence`\[:class:`abc.GuildChannel`]
            All channels that the guild has.
        """
        data = await self._state.http.get_all_guild_channels(self.id)

        def convert(d: GuildChannelPayload) -> GuildChannel:
            factory, _ = _guild_channel_factory(d["type"])
            if factory is None:
                raise InvalidData("Unknown channel type {type} for channel ID {id}.".format_map(d))

            return factory(
                guild=self,
                state=self._state,
                data=d,  # pyright: ignore[reportArgumentType]
            )

        return [convert(d) for d in data]

    # TODO: Remove Optional typing here when async iterators are refactored
    def fetch_members(
        self, *, limit: int | None = 1000, after: SnowflakeTime | None = None
    ) -> MemberIterator:
        """Retrieves an :class:`.AsyncIterator` that enables receiving the guild's members.

        In order to use this, the :attr:`~Intents.members` intent must be
        enabled in the developer portal.

        .. note::

            This method is an API call. For general usage, consider :attr:`members` instead.

        .. versionadded:: 1.3

        .. versionchanged:: 2.9
            No longer requires the intent to be enabled on the websocket connection.

        All parameters are optional.

        Parameters
        ----------
        limit: :class:`int` | :data:`None`
            The number of members to retrieve. Defaults to 1000.
            Pass :data:`None` to fetch all members. Note that this is potentially slow.
        after: :class:`.abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
            Retrieve members after this date or object.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.

        Raises
        ------
        ClientException
            The members intent is not enabled in the developer portal.
        HTTPException
            Retrieving the members failed.

        Yields
        ------
        :class:`.Member`
            The member with the member data parsed.

        Examples
        --------
        Usage ::

            async for member in guild.fetch_members(limit=150):
                print(member.name)

        Flattening into a list ::

            members = await guild.fetch_members(limit=150).flatten()
            # members is now a list of Member...
        """
        # `hasattr` check to avoid issues with uninitialized state
        if hasattr(self._state, "application_flags"):
            flags = self._state.application_flags
            if not (flags.gateway_guild_members_limited or flags.gateway_guild_members):
                msg = "The `members` intent must be enabled in the Developer Portal to be able to use this method."
                raise ClientException(msg)

        return MemberIterator(self, limit=limit, after=after)

    async def fetch_member(self, member_id: int, /) -> Member:
        """|coro|

        Retrieves a :class:`Member` with the given ID.

        .. note::

            This method is an API call. If you have :attr:`Intents.members` and member cache enabled, consider :meth:`get_member` instead.

        Parameters
        ----------
        member_id: :class:`int`
            The member's ID to fetch from.

        Raises
        ------
        NotFound
            A member with this ID does not exist in the guild.
        Forbidden
            You do not have access to the guild.
        HTTPException
            Retrieving the member failed.

        Returns
        -------
        :class:`Member`
            The member from the member ID.
        """
        data = await self._state.http.get_member(self.id, member_id)
        return Member(data=data, state=self._state, guild=self)

    async def fetch_channel(self, channel_id: int, /) -> GuildChannel | Thread:
        """|coro|

        Retrieves a :class:`.abc.GuildChannel` or :class:`.Thread` with the given ID.

        .. note::

            This method is an API call. For general usage, consider :meth:`get_channel_or_thread` instead.

        .. versionadded:: 2.0

        Raises
        ------
        InvalidData
            An unknown channel type was received from Discord
            or the guild the channel belongs to is not the same
            as the one in this object points to.
        HTTPException
            Retrieving the channel failed.
        NotFound
            Invalid Channel ID.
        Forbidden
            You do not have permission to fetch this channel.

        Returns
        -------
        :class:`.abc.GuildChannel` | :class:`.Thread`
            The channel from the ID.
        """
        data = await self._state.http.get_channel(channel_id)

        factory, ch_type = _threaded_guild_channel_factory(data["type"])
        if factory is None:
            raise InvalidData("Unknown channel type {type} for channel ID {id}.".format_map(data))

        if ch_type in (ChannelType.group, ChannelType.private):
            msg = "Channel ID resolved to a private channel"
            raise InvalidData(msg)

        assert "guild_id" in data
        guild_id = int(data["guild_id"])
        if self.id != guild_id:
            msg = "Guild ID resolved to a different guild"
            raise InvalidData(msg)

        channel: GuildChannel = factory(  # pyright: ignore[reportAssignmentType]
            guild=self,
            state=self._state,
            data=data,  # pyright: ignore[reportArgumentType]
        )
        return channel

    async def webhooks(self) -> list[Webhook]:
        r"""|coro|

        Gets the list of webhooks from this guild.

        You must have :attr:`~.Permissions.manage_webhooks` permission
        to use this.

        Raises
        ------
        Forbidden
            You don't have permissions to get the webhooks.

        Returns
        -------
        :class:`list`\[:class:`Webhook`]
            The webhooks for this guild.
        """
        from .webhook import Webhook

        data = await self._state.http.guild_webhooks(self.id)
        return [Webhook.from_state(d, state=self._state) for d in data]

    async def fetch_emojis(self) -> list[Emoji]:
        r"""|coro|

        Retrieves all custom :class:`Emoji`\s that the guild has.

        .. note::

            This method is an API call. For general usage, consider :attr:`emojis` instead.

        Raises
        ------
        HTTPException
            Retrieving the emojis failed.

        Returns
        -------
        :class:`list`\[:class:`Emoji`]
            The retrieved emojis.
        """
        data = await self._state.http.get_all_custom_emojis(self.id)
        return [Emoji(guild=self, state=self._state, data=d) for d in data]

    async def fetch_emoji(self, emoji_id: int, /) -> Emoji:
        """|coro|

        Retrieves a custom :class:`Emoji` from the guild.

        .. note::

            This method is an API call.
            For general usage, consider iterating over :attr:`emojis` instead.

        Parameters
        ----------
        emoji_id: :class:`int`
            The emoji's ID.

        Raises
        ------
        NotFound
            The emoji requested could not be found.
        HTTPException
            An error occurred fetching the emoji.

        Returns
        -------
        :class:`Emoji`
            The retrieved emoji.
        """
        data = await self._state.http.get_custom_emoji(self.id, emoji_id)
        return Emoji(guild=self, state=self._state, data=data)

    async def fetch_role(self, role_id: int, /) -> Role:
        """|coro|

        Retrieve a :class:`Role`.

        .. note::

            This method is an API call. For general usage, consider :meth:`get_role` or :attr:`roles` instead.

        .. versionadded:: 2.10

        Parameters
        ----------
        role_id: :class:`int`
            The ID of the role to retrieve.

        Raises
        ------
        NotFound
            The role requested could not be found.
        HTTPException
            Retrieving the role failed.

        Returns
        -------
        :class:`Role`
            The retrieved role.
        """
        data = await self._state.http.get_role(self.id, role_id=role_id)
        return Role(guild=self, state=self._state, data=data)

    async def fetch_roles(self) -> list[Role]:
        r"""|coro|

        Retrieves all :class:`Role` that the guild has.

        .. note::

            This method is an API call. For general usage, consider :attr:`roles` instead.

        .. versionadded:: 1.3

        Raises
        ------
        HTTPException
            Retrieving the roles failed.

        Returns
        -------
        :class:`list`\[:class:`Role`]
            All roles that the guild has.
        """
        data = await self._state.http.get_roles(self.id)
        return [Role(guild=self, state=self._state, data=d) for d in data]

    @overload
    async def get_or_fetch_member(
        self, member_id: int, *, strict: Literal[False] = ...
    ) -> Member | None: ...

    @overload
    async def get_or_fetch_member(self, member_id: int, *, strict: Literal[True]) -> Member: ...

    async def get_or_fetch_member(self, member_id: int, *, strict: bool = False) -> Member | None:
        """|coro|

        Tries to get the member from the cache. If it fails,
        fetches the member from the API and caches it.

        If you want to make a bulk get-or-fetch call, use :meth:`get_or_fetch_members`.

        This only propagates exceptions when the ``strict`` parameter is enabled.

        Parameters
        ----------
        member_id: :class:`int`
            The ID to search for.
        strict: :class:`bool`
            Whether to propagate exceptions from :func:`fetch_member`
            instead of returning :data:`None` in case of failure
            (e.g. if the member wasn't found).
            Defaults to ``False``.

        Returns
        -------
        :class:`Member` | :data:`None`
            The member with the given ID, or :data:`None` if not found and ``strict`` is set to ``False``.
        """
        member = self.get_member(member_id)
        if member is not None:
            return member
        try:
            member = await self.fetch_member(member_id)
            self._add_member(member)
        except HTTPException:
            if strict:
                raise
            return None
        return member

    getch_member = get_or_fetch_member

    async def chunk(self, *, cache: bool = True) -> list[Member] | None:
        r"""|coro|

        Returns a :class:`list` of all guild members.

        Requests all members that belong to this guild. In order to use this,
        :meth:`Intents.members` must be enabled.

        This is a websocket operation and can be slow.

        .. versionadded:: 1.5

        Parameters
        ----------
        cache: :class:`bool`
            Whether to cache the members as well.

        Raises
        ------
        ClientException
            The members intent is not enabled.

        Returns
        -------
        :class:`list`\[:class:`Member`] | :data:`None`
             Returns a list of all the members within the guild.
        """
        if not self._state._intents.members:
            msg = "Intents.members must be enabled to use this."
            raise ClientException(msg)

        if not self._state.is_guild_evicted(self):
            return await self._state.chunk_guild(self, cache=cache)
        return None

    async def query_members(
        self,
        query: str | None = None,
        *,
        limit: int = 5,
        user_ids: list[int] | None = None,
        presences: bool = False,
        cache: bool = True,
    ) -> list[Member]:
        r"""|coro|

        Request members that belong to this guild whose name starts with
        the query given.

        This is a websocket operation and can be slow.

        See also :func:`search_members`.

        .. versionadded:: 1.3

        Parameters
        ----------
        query: :class:`str` | :data:`None`
            The string that the names start with.
        limit: :class:`int`
            The maximum number of members to send back. This must be
            a number between 5 and 100.
        presences: :class:`bool`
            Whether to request for presences to be provided. This defaults
            to ``False``.

            .. versionadded:: 1.6

        cache: :class:`bool`
            Whether to cache the members internally. This makes operations
            such as :meth:`get_member` work for those that matched.
        user_ids: :class:`list`\[:class:`int`] | :data:`None`
            List of user IDs to search for. If the user ID is not in the guild then it won't be returned.

            .. versionadded:: 1.4


        Raises
        ------
        asyncio.TimeoutError
            The query timed out waiting for the members.
        ValueError
            Invalid parameters were passed to the function
        ClientException
            The presences intent is not enabled.

        Returns
        -------
        :class:`list`\[:class:`Member`]
            The list of members that have matched the query.
        """
        if presences and not self._state._intents.presences:
            msg = "Intents.presences must be enabled to use this."
            raise ClientException(msg)

        if query is None:
            if user_ids is None:
                msg = "Must pass either query or user_ids"
                raise ValueError(msg)

        elif not query:
            msg = "Cannot pass empty query string."
            raise ValueError(msg)

        elif user_ids is not None:
            msg = "Cannot pass both query and user_ids"
            raise ValueError(msg)

        if user_ids is not None and not user_ids:
            msg = "user_ids must contain at least 1 value"
            raise ValueError(msg)

        limit = min(100, limit or 5)
        return await self._state.query_members(
            self, query=query, limit=limit, user_ids=user_ids, presences=presences, cache=cache
        )

    async def get_or_fetch_members(
        self,
        user_ids: list[int],
        *,
        presences: bool = False,
        cache: bool = True,
    ) -> list[Member]:
        r"""|coro|

        Tries to get the guild members matching the provided IDs from cache.
        If some of them were not found, the method requests the missing members using websocket operations.
        If ``cache`` kwarg is ``True`` (default value) the missing members will be cached.

        If more than 100 members are missing, several websocket operations are made.

        Websocket operations can be slow, however, this method is cheaper than multiple :meth:`get_or_fetch_member` calls.

        .. versionadded:: 2.4

        Parameters
        ----------
        user_ids: :class:`list`\[:class:`int`]
            List of user IDs to search for. If the user ID is not in the guild then it won't be returned.
        presences: :class:`bool`
            Whether to request for presences to be provided. Defaults to ``False``.
        cache: :class:`bool`
            Whether to cache the missing members internally. This makes operations
            such as :meth:`get_member` work for those that matched.
            It also speeds up this method on repeated calls. Defaults to ``True``.

        Raises
        ------
        asyncio.TimeoutError
            The query timed out waiting for the members.
        ClientException
            The presences intent is not enabled.

        Returns
        -------
        :class:`list`\[:class:`Member`]
            The list of members with the given IDs, if they exist.
        """
        if presences and not self._state._intents.presences:
            msg = "Intents.presences must be enabled to use this."
            raise ClientException(msg)

        members: list[Member] = []
        unresolved_ids: list[int] = []

        for user_id in user_ids:
            member = self.get_member(user_id)
            if member is None:
                unresolved_ids.append(user_id)
            else:
                members.append(member)

        if not unresolved_ids:
            return members

        if len(unresolved_ids) == 1:
            # fetch_member is cheaper than query_members
            try:
                member = await self.fetch_member(unresolved_ids[0])
                members.append(member)
                if cache:
                    self._add_member(member)
            except HTTPException:
                pass
        else:
            # We have to split the request into several smaller requests
            # because the limit is 100 members per request.
            for i in range(0, len(unresolved_ids), 100):
                limit = min(100, len(unresolved_ids) - i)
                members += await self._state.query_members(
                    self,
                    query=None,
                    limit=limit,
                    user_ids=unresolved_ids[i : i + 100],
                    presences=presences,
                    cache=cache,
                )

        return members

    getch_members = get_or_fetch_members

    # Application command permissions

    async def bulk_fetch_command_permissions(self) -> list[GuildApplicationCommandPermissions]:
        """|coro|

        Requests a list of :class:`GuildApplicationCommandPermissions` configured for this guild.

        .. versionadded:: 2.1
        """
        return await self._state.bulk_fetch_command_permissions(self.id)

    async def fetch_command_permissions(
        self, command_id: int
    ) -> GuildApplicationCommandPermissions:
        """|coro|

        Retrieves :class:`GuildApplicationCommandPermissions` for a specific command.

        .. versionadded:: 2.1

        Parameters
        ----------
        command_id: :class:`int`
            The ID of the application command, or the application ID to fetch application-wide permissions.

            .. versionchanged:: 2.5
                Can now also fetch application-wide permissions.

        Returns
        -------
        :class:`GuildApplicationCommandPermissions`
            The application command permissions.
        """
        return await self._state.fetch_command_permissions(self.id, command_id)

    @overload
    async def timeout(
        self,
        user: Snowflake,
        *,
        duration: float | datetime.timedelta | None,
        reason: str | None = None,
    ) -> Member: ...

    @overload
    async def timeout(
        self,
        user: Snowflake,
        *,
        until: datetime.datetime | None,
        reason: str | None = None,
    ) -> Member: ...

    async def timeout(
        self,
        user: Snowflake,
        *,
        duration: float | datetime.timedelta | None = MISSING,
        until: datetime.datetime | None = MISSING,
        reason: str | None = None,
    ) -> Member:
        """|coro|

        Times out the member from the guild; until then, the member will not be able to interact with the guild.

        Exactly one of ``duration`` or ``until`` must be provided. To remove a timeout, set one of the parameters to :data:`None`.

        The user must meet the :class:`abc.Snowflake` abc.

        You must have the :attr:`~Permissions.moderate_members` permission to do this.

        .. versionadded:: 2.3

        Parameters
        ----------
        user: :class:`abc.Snowflake`
            The member to timeout.
        duration: :class:`float` | :class:`datetime.timedelta` | :data:`None`
            The duration (seconds or timedelta) of the member's timeout. Set to :data:`None` to remove the timeout.
            Supports up to 28 days in the future.
            May not be used in combination with the ``until`` parameter.
        until: :class:`datetime.datetime` | :data:`None`
            The expiry date/time of the member's timeout. Set to :data:`None` to remove the timeout.
            Supports up to 28 days in the future.
            May not be used in combination with the ``duration`` parameter.
        reason: :class:`str` | :data:`None`
            The reason for this timeout. Shows up on the audit log.

        Raises
        ------
        Forbidden
            You do not have permissions to timeout this member.
        HTTPException
            Timing out the member failed.

        Returns
        -------
        :class:`Member`
            The newly updated member.
        """
        if not (duration is MISSING) ^ (until is MISSING):
            msg = "Exactly one of `duration` and `until` must be provided"
            raise ValueError(msg)

        payload: dict[str, Any] = {}

        if duration is not MISSING:
            if duration is None:
                until = None
            elif isinstance(duration, datetime.timedelta):
                until = utils.utcnow() + duration
            else:
                until = utils.utcnow() + datetime.timedelta(seconds=duration)

        # at this point `until` cannot be `MISSING`
        payload["communication_disabled_until"] = utils.isoformat_utc(until)

        data = await self._state.http.edit_member(self.id, user.id, reason=reason, **payload)
        return Member(data=data, guild=self, state=self._state)
