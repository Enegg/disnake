# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import disnake

from .interaction_bot_base import InteractionBotBase

if TYPE_CHECKING:
    import asyncio

    import aiohttp

    from disnake.activity import BaseActivity
    from disnake.client import GatewayParams
    from disnake.enums import Status
    from disnake.flags import (
        ApplicationInstallTypes,
        Intents,
        InteractionContextTypes,
        MemberCacheFlags,
    )
    from disnake.i18n import LocalizationProtocol
    from disnake.mentions import AllowedMentions

    from .flags import CommandSyncFlags


__all__ = (
    "InteractionBot",
    "AutoShardedInteractionBot",
)

MISSING: Any = disnake.utils.MISSING


class InteractionBot(InteractionBotBase, disnake.Client):
    r"""Represents a discord bot for application commands only.

    This class is a subclass of :class:`disnake.Client` and as a result
    anything that you can do with a :class:`disnake.Client` you can do with
    this bot.

    This class also subclasses InteractionBotBase to provide the functionality
    to manage application commands.

    Parameters
    ----------
    test_guilds: :class:`list`\[:class:`int`]
        The list of IDs of the guilds where you're going to test your application commands.
        Defaults to :data:`None`, which means global registration of commands across
        all guilds.

        .. versionadded:: 2.1

    command_sync_flags: :class:`.CommandSyncFlags`
        The command sync flags for the session. This is a way of
        controlling when and how application commands will be synced with the Discord API.
        If not given, defaults to :func:`CommandSyncFlags.default`.

        .. versionadded:: 2.7

    localization_provider: :class:`.LocalizationProtocol`
        An implementation of :class:`.LocalizationProtocol` to use for localization of
        application commands.
        If not provided, the default :class:`.LocalizationStore` implementation is used.

        .. versionadded:: 2.5

    strict_localization: :class:`bool`
        Whether to raise an exception when localizations for a specific key couldn't be found.
        This is mainly useful for testing/debugging, consider disabling this eventually
        as missing localized names will automatically fall back to the default/base name without it.
        Only applicable if the ``localization_provider`` parameter is not provided.
        Defaults to ``False``.

        .. versionadded:: 2.5

    default_install_types: :class:`.ApplicationInstallTypes` | :data:`None`
        The default installation types where application commands will be available.
        This applies to all commands added either through the respective decorators
        or directly using :meth:`.add_slash_command` (etc.).

        Any value set directly on the command, e.g. using the :func:`.install_types` decorator,
        the ``install_types`` parameter, ``slash_command_attrs`` (etc.) at the cog-level, or from
        the :class:`.GuildCommandInteraction` annotation, takes precedence over this default.

        .. versionadded:: 2.10

    default_contexts: :class:`.InteractionContextTypes` | :data:`None`
        The default contexts where application commands will be usable.
        This applies to all commands added either through the respective decorators
        or directly using :meth:`.add_slash_command` (etc.).

        Any value set directly on the command, e.g. using the :func:`.contexts` decorator,
        the ``contexts`` parameter, ``slash_command_attrs`` (etc.) at the cog-level, or from
        the :class:`.GuildCommandInteraction` annotation, takes precedence over this default.

        .. versionadded:: 2.10

    Attributes
    ----------
    owner_id: :class:`int` | :data:`None`
        The ID of the user that owns the bot. If this is not set and is then queried via
        :meth:`.is_owner` then it is fetched automatically using
        :meth:`~.Bot.application_info`.

        This can be provided as a parameter at creation.

    owner_ids: :class:`~collections.abc.Collection`\[:class:`int`] | :data:`None`
        The IDs of the users that own the bot. This is similar to :attr:`owner_id`.
        If this is not set and the application is team based, then it is
        fetched automatically using :meth:`~.Bot.application_info` (taking team roles into account).
        For performance reasons it is recommended to use a :class:`set`
        for the collection. You cannot set both ``owner_id`` and ``owner_ids``.

        This can be provided as a parameter at creation.

    reload: :class:`bool`
        Whether to enable automatic extension reloading on file modification for debugging.
        Whenever you save an extension with reloading enabled the file will be automatically
        reloaded for you so you do not have to reload the extension manually. Defaults to ``False``

        This can be provided as a parameter at creation.

        .. versionadded:: 2.1

    i18n: :class:`.LocalizationProtocol`
        An implementation of :class:`.LocalizationProtocol` used for localization of
        application commands.

        .. versionadded:: 2.5
    """

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            owner_id: int | None = None,
            owner_ids: set[int] | None = None,
            reload: bool = False,
            command_sync_flags: CommandSyncFlags = ...,
            test_guilds: Sequence[int] | None = None,
            default_install_types: ApplicationInstallTypes | None = None,
            default_contexts: InteractionContextTypes | None = None,
            asyncio_debug: bool = False,
            loop: asyncio.AbstractEventLoop | None = None,
            shard_id: int | None = None,
            shard_count: int | None = None,
            enable_debug_events: bool = False,
            enable_gateway_error_handler: bool = True,
            gateway_params: GatewayParams | None = None,
            connector: aiohttp.BaseConnector | None = None,
            proxy: str | None = None,
            proxy_auth: aiohttp.BasicAuth | None = None,
            assume_unsync_clock: bool = True,
            max_messages: int | None = 1000,
            application_id: int | None = None,
            heartbeat_timeout: float = 60.0,
            guild_ready_timeout: float = 2.0,
            allowed_mentions: AllowedMentions | None = None,
            activity: BaseActivity | None = None,
            status: Status | str | None = None,
            intents: Intents | None = None,
            chunk_guilds_at_startup: bool | None = None,
            member_cache_flags: MemberCacheFlags | None = None,
            localization_provider: LocalizationProtocol | None = None,
            strict_localization: bool = False,
        ) -> None: ...


class AutoShardedInteractionBot(InteractionBotBase, disnake.AutoShardedClient):
    """Similar to :class:`.InteractionBot`, except that it is inherited from
    :class:`disnake.AutoShardedClient` instead.
    """

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            owner_id: int | None = None,
            owner_ids: set[int] | None = None,
            reload: bool = False,
            command_sync_flags: CommandSyncFlags = ...,
            test_guilds: Sequence[int] | None = None,
            default_install_types: ApplicationInstallTypes | None = None,
            default_contexts: InteractionContextTypes | None = None,
            asyncio_debug: bool = False,
            loop: asyncio.AbstractEventLoop | None = None,
            shard_ids: list[int] | None = None,  # instead of shard_id
            shard_count: int | None = None,
            enable_debug_events: bool = False,
            enable_gateway_error_handler: bool = True,
            gateway_params: GatewayParams | None = None,
            connector: aiohttp.BaseConnector | None = None,
            proxy: str | None = None,
            proxy_auth: aiohttp.BasicAuth | None = None,
            assume_unsync_clock: bool = True,
            max_messages: int | None = 1000,
            application_id: int | None = None,
            heartbeat_timeout: float = 60.0,
            guild_ready_timeout: float = 2.0,
            allowed_mentions: AllowedMentions | None = None,
            activity: BaseActivity | None = None,
            status: Status | str | None = None,
            intents: Intents | None = None,
            chunk_guilds_at_startup: bool | None = None,
            member_cache_flags: MemberCacheFlags | None = None,
            localization_provider: LocalizationProtocol | None = None,
            strict_localization: bool = False,
        ) -> None: ...
