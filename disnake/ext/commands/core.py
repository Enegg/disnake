# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

import disnake
from disnake.utils import (
    _generated,
    _overload_with_permissions,
    iscoroutinefunction,
)

from .cooldowns import BucketType, Cooldown, CooldownMapping, DynamicCooldownMapping, MaxConcurrency
from .errors import (
    BotMissingAnyRole,
    BotMissingPermissions,
    BotMissingRole,
    CheckAnyFailure,
    CheckFailure,
    CommandError,
    CommandInvokeError,
    MissingAnyRole,
    MissingPermissions,
    MissingRole,
    NoPrivateMessage,
    NotOwner,
    NSFWChannelRequired,
    PrivateMessageOnly,
)

if TYPE_CHECKING:
    from typing import Concatenate

    from typing_extensions import ParamSpec

    from disnake.message import Message

    from ._types import AppCheck, Coro, CoroFunc, Error, Hook


__all__ = (
    "has_role",
    "has_permissions",
    "has_any_role",
    "check",
    "check_any",
    "app_check",
    "app_check_any",
    "before_invoke",
    "after_invoke",
    "bot_has_role",
    "bot_has_permissions",
    "bot_has_any_role",
    "cooldown",
    "dynamic_cooldown",
    "max_concurrency",
    "dm_only",
    "guild_only",
    "is_owner",
    "is_nsfw",
    "has_guild_permissions",
    "bot_has_guild_permissions",
)

MISSING: Any = disnake.utils.MISSING

T = TypeVar("T")
VT = TypeVar("VT")
CommandT = TypeVar("CommandT", bound="Command")
GroupT = TypeVar("GroupT", bound="Group")
HookT = TypeVar("HookT", bound="Hook")
ErrorT = TypeVar("ErrorT", bound="Error")


if TYPE_CHECKING:
    P = ParamSpec("P")

    CommandCallback: TypeAlias = Callable[Concatenate[object, P], Coro[T]]
else:
    P = TypeVar("P")


def wrap_callback(coro: Callable[..., Coro[T]]) -> Callable[..., Coro[T | None]]:
    # there's no way to type it nicely without causing issues down the line
    @functools.wraps(coro)
    async def wrapped(*args: Any, **kwargs: Any) -> T | None:
        try:
            ret = await coro(*args, **kwargs)
        except CommandError:
            raise
        except asyncio.CancelledError:
            return None
        except Exception as exc:
            raise CommandInvokeError(exc) from exc
        return ret

    return wrapped


def hooked_wrapped_callback(
    command: Command[Any, ..., T],
    ctx: disnake.ApplicationCommandInteraction,
    coro: Callable[..., Coro[T]],
) -> Callable[..., Coro[T | None]]:
    # there's no way to type it nicely without causing issues down the line
    @functools.wraps(coro)
    async def wrapped(*args: Any, **kwargs: Any) -> T | None:
        try:
            ret = await coro(*args, **kwargs)
        except CommandError:
            ctx.command_failed = True
            raise
        except asyncio.CancelledError:
            ctx.command_failed = True
            return None
        except Exception as exc:
            ctx.command_failed = True
            raise CommandInvokeError(exc) from exc
        finally:
            if command._max_concurrency is not None:
                await command._max_concurrency.release(ctx)  # pyright: ignore[reportArgumentType]

            await command.call_after_hooks(ctx)
        return ret

    return wrapped


# Decorators


def check(predicate: AppCheck) -> Callable[[T], T]:
    r"""A decorator that adds a check to the :class:`.Command` or its
    subclasses. These checks could be accessed via :attr:`.Command.checks`.

    These checks should be predicates that take in a single parameter taking
    a :class:`.Context`. If the check returns a ``False``-like value then
    during invocation a :exc:`.CheckFailure` exception is raised and sent to
    the :func:`.on_command_error` event.

    If an exception should be thrown in the predicate then it should be a
    subclass of :exc:`.CommandError`. Any exception not subclassed from it
    will be propagated while those subclassed will be sent to
    :func:`.on_command_error`.

    A special attribute named ``predicate`` is bound to the value
    returned by this decorator to retrieve the predicate passed to the
    decorator. This allows the following introspection and chaining to be done:

    .. code-block:: python3

        def owner_or_permissions(**perms):
            original = commands.has_permissions(**perms).predicate
            async def extended_check(ctx):
                if ctx.guild is None:
                    return False
                return ctx.guild.owner_id == ctx.author.id or await original(ctx)
            return commands.check(extended_check)

    .. note::

        The function returned by ``predicate`` is **always** a coroutine,
        even if the original function was not a coroutine.

    .. note::
        See :func:`.app_check` for this function's application command counterpart.

    .. versionchanged:: 1.3
        The ``predicate`` attribute was added.

    Examples
    --------
    Creating a basic check to see if the command invoker is you.

    .. code-block:: python3

        def check_if_it_is_me(ctx):
            return ctx.message.author.id == 85309593344815104

        @bot.command()
        @commands.check(check_if_it_is_me)
        async def only_for_me(ctx):
            await ctx.send('I know you!')

    Transforming common checks into its own decorator:

    .. code-block:: python3

        def is_me():
            def predicate(ctx):
                return ctx.message.author.id == 85309593344815104
            return commands.check(predicate)

        @bot.command()
        @is_me()
        async def only_me(ctx):
            await ctx.send('Only you!')

    Parameters
    ----------
    predicate: :class:`~collections.abc.Callable`\[[:class:`Context`], :class:`bool`]
        The predicate to check if the command should be invoked.
    """

    def decorator(
        func: Command[Any, ..., Any] | CoroFunc,
    ) -> Command[Any, ..., Any] | CoroFunc:
        if hasattr(func, "__command_flag__"):
            func.checks.append(predicate)
        else:
            if not hasattr(func, "__commands_checks__"):
                func.__commands_checks__ = []  # pyright: ignore[reportAttributeAccessIssue]

            func.__commands_checks__.append(predicate)  # pyright: ignore[reportAttributeAccessIssue]

        return func

    if iscoroutinefunction(predicate):
        decorator.predicate = predicate
    else:

        @functools.wraps(predicate)  # pyright: ignore[reportArgumentType]
        async def wrapper(ctx):
            return predicate(ctx)  # pyright: ignore[reportCallIssue]

        decorator.predicate = wrapper

    return decorator  # pyright: ignore[reportReturnType]


def check_any(*checks: AppCheck) -> Callable[[T], T]:
    r"""A :func:`check` that is added that checks if any of the checks passed
    will pass, i.e. using logical OR.

    If all checks fail then :exc:`.CheckAnyFailure` is raised to signal the failure.
    It inherits from :exc:`.CheckFailure`.

    .. note::

        The ``predicate`` attribute for this function **is** a coroutine.

    .. note::
        See :func:`.app_check_any` for this function's application command counterpart.

    .. versionadded:: 1.3

    Parameters
    ----------
    *checks: :class:`~collections.abc.Callable`\[[:class:`Context`], :class:`bool`]
        An argument list of checks that have been decorated with
        the :func:`check` decorator.

    Raises
    ------
    TypeError
        A check passed has not been decorated with the :func:`check`
        decorator.

    Examples
    --------
    Creating a basic check to see if it's the bot owner or
    the server owner:

    .. code-block:: python3

        def is_guild_owner():
            def predicate(ctx):
                return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
            return commands.check(predicate)

        @bot.command()
        @commands.check_any(commands.is_owner(), is_guild_owner())
        async def only_for_owners(ctx):
            await ctx.send('Hello mister owner!')
    """
    unwrapped = []
    for wrapped in checks:
        try:
            pred = wrapped.predicate
        except AttributeError:
            msg = f"{wrapped!r} must be wrapped by commands.check decorator"
            raise TypeError(msg) from None
        else:
            unwrapped.append(pred)

    async def predicate(ctx: AnyContext) -> bool:
        errors = []
        for func in unwrapped:
            try:
                value = await func(ctx)
            except CheckFailure as e:
                errors.append(e)
            else:
                if value:
                    return True
        # if we're here, all checks failed
        raise CheckAnyFailure(unwrapped, errors)

    return check(predicate)


def app_check(predicate: AppCheck) -> Callable[[T], T]:
    r"""Same as :func:`.check`, but for app commands.

    .. versionadded:: 2.10

    Parameters
    ----------
    predicate: :class:`~collections.abc.Callable`\[[:class:`disnake.ApplicationCommandInteraction`], :class:`bool`]
        The predicate to check if the command should be invoked.
    """
    return check(predicate)  # pyright: ignore[reportArgumentType]  # impl is the same, typings are different


def app_check_any(*checks: AppCheck) -> Callable[[T], T]:
    r"""Same as :func:`.check_any`, but for app commands.

    .. note::
        See :func:`.check_any` for this function's prefix command counterpart.

    .. versionadded:: 2.10

    Parameters
    ----------
    *checks: :class:`~collections.abc.Callable`\[[:class:`disnake.ApplicationCommandInteraction`], :class:`bool`]
        An argument list of checks that have been decorated with
        the :func:`app_check` decorator.

    Raises
    ------
    TypeError
        A check passed has not been decorated with the :func:`app_check`
        decorator.
    """
    try:
        return check_any(*checks)  # pyright: ignore[reportArgumentType]  # impl is the same, typings are different
    except TypeError as e:
        msg = str(e).replace("commands.check", "commands.app_check")  # fix err message
        raise TypeError(msg) from None


def has_role(item: int | str) -> Callable[[T], T]:
    """A :func:`.check` that is added that checks if the member invoking the
    command has the role specified via the name or ID specified.

    If a string is specified, you must give the exact name of the role, including
    caps and spelling.

    If an integer is specified, you must give the exact snowflake ID of the role.

    If the message is invoked in a private message context then the check will
    return ``False``.

    This check raises one of two special exceptions, :exc:`.MissingRole` if the user
    is missing a role, or :exc:`.NoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.CheckFailure`.

    .. versionchanged:: 1.1

        Raise :exc:`.MissingRole` or :exc:`.NoPrivateMessage`
        instead of generic :exc:`.CheckFailure`

    Parameters
    ----------
    item: :class:`int` | :class:`str`
        The name or ID of the role to check.
    """

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if ctx.guild is None:
            raise NoPrivateMessage

        # ctx.guild is None doesn't narrow ctx.author to Member
        assert isinstance(ctx.author, disnake.Member)

        if isinstance(item, int):
            role = disnake.utils.get(ctx.author.roles, id=item)
        else:
            role = disnake.utils.get(ctx.author.roles, name=item)
        if role is None:
            raise MissingRole(item)
        return True

    return check(predicate)


def has_any_role(*items: int | str) -> Callable[[T], T]:
    r"""A :func:`.check` that is added that checks if the member invoking the
    command has **any** of the roles specified. This means that if they have
    one out of the three roles specified, then this check will return `True`.

    Similar to :func:`.has_role`\, the names or IDs passed in must be exact.

    This check raises one of two special exceptions, :exc:`.MissingAnyRole` if the user
    is missing all roles, or :exc:`.NoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.CheckFailure`.

    .. versionchanged:: 1.1

        Raise :exc:`.MissingAnyRole` or :exc:`.NoPrivateMessage`
        instead of generic :exc:`.CheckFailure`

    Parameters
    ----------
    items: :class:`list`\[:class:`str` | :class:`int`]
        An argument list of names or IDs to check that the member has roles wise.

    Example
    --------

    .. code-block:: python3

        @bot.command()
        @commands.has_any_role('Library Devs', 'Moderators', 492212595072434186)
        async def cool(ctx):
            await ctx.send('You are cool indeed')
    """

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if ctx.guild is None:
            raise NoPrivateMessage

        # ctx.guild is None doesn't narrow ctx.author to Member
        assert isinstance(ctx.author, disnake.Member)

        getter = functools.partial(disnake.utils.get, ctx.author.roles)
        if any(
            getter(id=item) is not None if isinstance(item, int) else getter(name=item) is not None
            for item in items
        ):
            return True
        # NOTE: variance problems
        raise MissingAnyRole(list(items))  # pyright: ignore[reportArgumentType]

    return check(predicate)


def bot_has_role(item: int) -> Callable[[T], T]:
    """Similar to :func:`.has_role` except checks if the bot itself has the
    role.

    This check raises one of two special exceptions, :exc:`.BotMissingRole` if the bot
    is missing the role, or :exc:`.NoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.CheckFailure`.

    .. versionchanged:: 1.1

        Raise :exc:`.BotMissingRole` or :exc:`.NoPrivateMessage`
        instead of generic :exc:`.CheckFailure`
    """

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if ctx.guild is None:
            raise NoPrivateMessage

        me = cast("disnake.Member", ctx.me)
        if isinstance(item, int):
            role = disnake.utils.get(me.roles, id=item)
        else:
            role = disnake.utils.get(me.roles, name=item)
        if role is None:
            raise BotMissingRole(item)
        return True

    return check(predicate)


def bot_has_any_role(*items: int) -> Callable[[T], T]:
    """Similar to :func:`.has_any_role` except checks if the bot itself has
    any of the roles listed.

    This check raises one of two special exceptions, :exc:`.BotMissingAnyRole` if the bot
    is missing all roles, or :exc:`.NoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.CheckFailure`.

    .. versionchanged:: 1.1

        Raise :exc:`.BotMissingAnyRole` or :exc:`.NoPrivateMessage`
        instead of generic checkfailure
    """

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if ctx.guild is None:
            raise NoPrivateMessage

        me = cast("disnake.Member", ctx.me)
        getter = functools.partial(disnake.utils.get, me.roles)
        if any(
            getter(id=item) is not None if isinstance(item, int) else getter(name=item) is not None
            for item in items
        ):
            return True
        raise BotMissingAnyRole(list(items))

    return check(predicate)


@overload
@_generated
def has_permissions(
    *,
    add_reactions: bool = ...,
    administrator: bool = ...,
    attach_files: bool = ...,
    ban_members: bool = ...,
    bypass_slowmode: bool = ...,
    change_nickname: bool = ...,
    connect: bool = ...,
    create_events: bool = ...,
    create_forum_threads: bool = ...,
    create_guild_expressions: bool = ...,
    create_instant_invite: bool = ...,
    create_private_threads: bool = ...,
    create_public_threads: bool = ...,
    deafen_members: bool = ...,
    embed_links: bool = ...,
    external_emojis: bool = ...,
    external_stickers: bool = ...,
    kick_members: bool = ...,
    manage_channels: bool = ...,
    manage_emojis: bool = ...,
    manage_emojis_and_stickers: bool = ...,
    manage_events: bool = ...,
    manage_guild: bool = ...,
    manage_guild_expressions: bool = ...,
    manage_messages: bool = ...,
    manage_nicknames: bool = ...,
    manage_permissions: bool = ...,
    manage_roles: bool = ...,
    manage_threads: bool = ...,
    manage_webhooks: bool = ...,
    mention_everyone: bool = ...,
    moderate_members: bool = ...,
    move_members: bool = ...,
    mute_members: bool = ...,
    pin_messages: bool = ...,
    priority_speaker: bool = ...,
    read_message_history: bool = ...,
    read_messages: bool = ...,
    request_to_speak: bool = ...,
    send_messages: bool = ...,
    send_messages_in_threads: bool = ...,
    send_polls: bool = ...,
    send_tts_messages: bool = ...,
    send_voice_messages: bool = ...,
    set_voice_channel_status: bool = ...,
    speak: bool = ...,
    start_embedded_activities: bool = ...,
    stream: bool = ...,
    use_application_commands: bool = ...,
    use_embedded_activities: bool = ...,
    use_external_apps: bool = ...,
    use_external_emojis: bool = ...,
    use_external_sounds: bool = ...,
    use_external_stickers: bool = ...,
    use_slash_commands: bool = ...,
    use_soundboard: bool = ...,
    use_voice_activation: bool = ...,
    view_audit_log: bool = ...,
    view_channel: bool = ...,
    view_creator_monetization_analytics: bool = ...,
    view_guild_insights: bool = ...,
) -> Callable[[T], T]: ...


@overload
@_generated
def has_permissions() -> Callable[[T], T]: ...


@_overload_with_permissions
def has_permissions(**perms: bool) -> Callable[[T], T]:
    """A :func:`.check` that is added that checks if the member has all of
    the permissions necessary.

    Note that this check operates on the current channel permissions, not the
    guild wide permissions.

    The permissions passed in must be exactly like the properties shown under
    :class:`.disnake.Permissions`.

    This check raises a special exception, :exc:`.MissingPermissions`
    that is inherited from :exc:`.CheckFailure`.

    .. versionchanged:: 2.6
        Considers if the author is timed out.

    Parameters
    ----------
    perms
        An argument list of permissions to check for.

    Example
    ---------

    .. code-block:: python3

        @bot.command()
        @commands.has_permissions(manage_messages=True)
        async def test(ctx):
            await ctx.send('You can manage messages.')

    """
    invalid = set(perms) - set(disnake.Permissions.VALID_FLAGS)
    if invalid:
        msg = f"Invalid permission(s): {', '.join(invalid)}"
        raise TypeError(msg)

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        permissions = ctx.permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise MissingPermissions(missing)

    return check(predicate)


@overload
@_generated
def bot_has_permissions(
    *,
    add_reactions: bool = ...,
    administrator: bool = ...,
    attach_files: bool = ...,
    ban_members: bool = ...,
    bypass_slowmode: bool = ...,
    change_nickname: bool = ...,
    connect: bool = ...,
    create_events: bool = ...,
    create_forum_threads: bool = ...,
    create_guild_expressions: bool = ...,
    create_instant_invite: bool = ...,
    create_private_threads: bool = ...,
    create_public_threads: bool = ...,
    deafen_members: bool = ...,
    embed_links: bool = ...,
    external_emojis: bool = ...,
    external_stickers: bool = ...,
    kick_members: bool = ...,
    manage_channels: bool = ...,
    manage_emojis: bool = ...,
    manage_emojis_and_stickers: bool = ...,
    manage_events: bool = ...,
    manage_guild: bool = ...,
    manage_guild_expressions: bool = ...,
    manage_messages: bool = ...,
    manage_nicknames: bool = ...,
    manage_permissions: bool = ...,
    manage_roles: bool = ...,
    manage_threads: bool = ...,
    manage_webhooks: bool = ...,
    mention_everyone: bool = ...,
    moderate_members: bool = ...,
    move_members: bool = ...,
    mute_members: bool = ...,
    pin_messages: bool = ...,
    priority_speaker: bool = ...,
    read_message_history: bool = ...,
    read_messages: bool = ...,
    request_to_speak: bool = ...,
    send_messages: bool = ...,
    send_messages_in_threads: bool = ...,
    send_polls: bool = ...,
    send_tts_messages: bool = ...,
    send_voice_messages: bool = ...,
    set_voice_channel_status: bool = ...,
    speak: bool = ...,
    start_embedded_activities: bool = ...,
    stream: bool = ...,
    use_application_commands: bool = ...,
    use_embedded_activities: bool = ...,
    use_external_apps: bool = ...,
    use_external_emojis: bool = ...,
    use_external_sounds: bool = ...,
    use_external_stickers: bool = ...,
    use_slash_commands: bool = ...,
    use_soundboard: bool = ...,
    use_voice_activation: bool = ...,
    view_audit_log: bool = ...,
    view_channel: bool = ...,
    view_creator_monetization_analytics: bool = ...,
    view_guild_insights: bool = ...,
) -> Callable[[T], T]: ...


@overload
@_generated
def bot_has_permissions() -> Callable[[T], T]: ...


@_overload_with_permissions
def bot_has_permissions(**perms: bool) -> Callable[[T], T]:
    """Similar to :func:`.has_permissions` except checks if the bot itself has
    the permissions listed.

    This check raises a special exception, :exc:`.BotMissingPermissions`
    that is inherited from :exc:`.CheckFailure`.

    .. versionchanged:: 2.6
        Considers if the author is timed out.
    """
    invalid = set(perms) - set(disnake.Permissions.VALID_FLAGS)
    if invalid:
        msg = f"Invalid permission(s): {', '.join(invalid)}"
        raise TypeError(msg)

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        permissions = ctx.app_permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise BotMissingPermissions(missing)

    return check(predicate)


@overload
@_generated
def has_guild_permissions(
    *,
    add_reactions: bool = ...,
    administrator: bool = ...,
    attach_files: bool = ...,
    ban_members: bool = ...,
    bypass_slowmode: bool = ...,
    change_nickname: bool = ...,
    connect: bool = ...,
    create_events: bool = ...,
    create_forum_threads: bool = ...,
    create_guild_expressions: bool = ...,
    create_instant_invite: bool = ...,
    create_private_threads: bool = ...,
    create_public_threads: bool = ...,
    deafen_members: bool = ...,
    embed_links: bool = ...,
    external_emojis: bool = ...,
    external_stickers: bool = ...,
    kick_members: bool = ...,
    manage_channels: bool = ...,
    manage_emojis: bool = ...,
    manage_emojis_and_stickers: bool = ...,
    manage_events: bool = ...,
    manage_guild: bool = ...,
    manage_guild_expressions: bool = ...,
    manage_messages: bool = ...,
    manage_nicknames: bool = ...,
    manage_permissions: bool = ...,
    manage_roles: bool = ...,
    manage_threads: bool = ...,
    manage_webhooks: bool = ...,
    mention_everyone: bool = ...,
    moderate_members: bool = ...,
    move_members: bool = ...,
    mute_members: bool = ...,
    pin_messages: bool = ...,
    priority_speaker: bool = ...,
    read_message_history: bool = ...,
    read_messages: bool = ...,
    request_to_speak: bool = ...,
    send_messages: bool = ...,
    send_messages_in_threads: bool = ...,
    send_polls: bool = ...,
    send_tts_messages: bool = ...,
    send_voice_messages: bool = ...,
    set_voice_channel_status: bool = ...,
    speak: bool = ...,
    start_embedded_activities: bool = ...,
    stream: bool = ...,
    use_application_commands: bool = ...,
    use_embedded_activities: bool = ...,
    use_external_apps: bool = ...,
    use_external_emojis: bool = ...,
    use_external_sounds: bool = ...,
    use_external_stickers: bool = ...,
    use_slash_commands: bool = ...,
    use_soundboard: bool = ...,
    use_voice_activation: bool = ...,
    view_audit_log: bool = ...,
    view_channel: bool = ...,
    view_creator_monetization_analytics: bool = ...,
    view_guild_insights: bool = ...,
) -> Callable[[T], T]: ...


@overload
@_generated
def has_guild_permissions() -> Callable[[T], T]: ...


@_overload_with_permissions
def has_guild_permissions(**perms: bool) -> Callable[[T], T]:
    """Similar to :func:`.has_permissions`, but operates on guild wide
    permissions instead of the current channel permissions.

    If this check is called in a DM context, it will raise an
    exception, :exc:`.NoPrivateMessage`.

    .. versionadded:: 1.3
    """
    invalid = set(perms) - set(disnake.Permissions.VALID_FLAGS)
    if invalid:
        msg = f"Invalid permission(s): {', '.join(invalid)}"
        raise TypeError(msg)

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if not ctx.guild:
            raise NoPrivateMessage

        assert isinstance(ctx.author, disnake.Member)
        permissions = ctx.author.guild_permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise MissingPermissions(missing)

    return check(predicate)


@overload
@_generated
def bot_has_guild_permissions(
    *,
    add_reactions: bool = ...,
    administrator: bool = ...,
    attach_files: bool = ...,
    ban_members: bool = ...,
    bypass_slowmode: bool = ...,
    change_nickname: bool = ...,
    connect: bool = ...,
    create_events: bool = ...,
    create_forum_threads: bool = ...,
    create_guild_expressions: bool = ...,
    create_instant_invite: bool = ...,
    create_private_threads: bool = ...,
    create_public_threads: bool = ...,
    deafen_members: bool = ...,
    embed_links: bool = ...,
    external_emojis: bool = ...,
    external_stickers: bool = ...,
    kick_members: bool = ...,
    manage_channels: bool = ...,
    manage_emojis: bool = ...,
    manage_emojis_and_stickers: bool = ...,
    manage_events: bool = ...,
    manage_guild: bool = ...,
    manage_guild_expressions: bool = ...,
    manage_messages: bool = ...,
    manage_nicknames: bool = ...,
    manage_permissions: bool = ...,
    manage_roles: bool = ...,
    manage_threads: bool = ...,
    manage_webhooks: bool = ...,
    mention_everyone: bool = ...,
    moderate_members: bool = ...,
    move_members: bool = ...,
    mute_members: bool = ...,
    pin_messages: bool = ...,
    priority_speaker: bool = ...,
    read_message_history: bool = ...,
    read_messages: bool = ...,
    request_to_speak: bool = ...,
    send_messages: bool = ...,
    send_messages_in_threads: bool = ...,
    send_polls: bool = ...,
    send_tts_messages: bool = ...,
    send_voice_messages: bool = ...,
    set_voice_channel_status: bool = ...,
    speak: bool = ...,
    start_embedded_activities: bool = ...,
    stream: bool = ...,
    use_application_commands: bool = ...,
    use_embedded_activities: bool = ...,
    use_external_apps: bool = ...,
    use_external_emojis: bool = ...,
    use_external_sounds: bool = ...,
    use_external_stickers: bool = ...,
    use_slash_commands: bool = ...,
    use_soundboard: bool = ...,
    use_voice_activation: bool = ...,
    view_audit_log: bool = ...,
    view_channel: bool = ...,
    view_creator_monetization_analytics: bool = ...,
    view_guild_insights: bool = ...,
) -> Callable[[T], T]: ...


@overload
@_generated
def bot_has_guild_permissions() -> Callable[[T], T]: ...


@_overload_with_permissions
def bot_has_guild_permissions(**perms: bool) -> Callable[[T], T]:
    """Similar to :func:`.has_guild_permissions`, but checks the bot
    members guild permissions.

    .. versionadded:: 1.3
    """
    invalid = set(perms) - set(disnake.Permissions.VALID_FLAGS)
    if invalid:
        msg = f"Invalid permission(s): {', '.join(invalid)}"
        raise TypeError(msg)

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if not ctx.guild:
            raise NoPrivateMessage

        assert isinstance(ctx.me, disnake.Member)
        permissions = ctx.me.guild_permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise BotMissingPermissions(missing)

    return check(predicate)


def dm_only() -> Callable[[T], T]:
    """A :func:`.check` that indicates this command must only be used in a
    DM context. Only private messages are allowed when
    using the command.

    This check raises a special exception, :exc:`.PrivateMessageOnly`
    that is inherited from :exc:`.CheckFailure`.

    .. note::
        For application commands, consider setting the allowed :ref:`contexts <app_command_contexts>` instead.

    .. versionadded:: 1.1
    """

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if ctx.guild_id is not None:
            raise PrivateMessageOnly
        return True

    return check(predicate)


def guild_only() -> Callable[[T], T]:
    """A :func:`.check` that indicates this command must only be used in a
    guild context only. Basically, no private messages are allowed when
    using the command.

    This check raises a special exception, :exc:`.NoPrivateMessage`
    that is inherited from :exc:`.CheckFailure`.

    .. note::
        For application commands, consider setting the allowed :ref:`contexts <app_command_contexts>` instead.
    """

    def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if ctx.guild_id is None:
            raise NoPrivateMessage
        return True

    return check(predicate)


def is_owner() -> Callable[[T], T]:
    """A :func:`.check` that checks if the person invoking this command is the
    owner of the bot.

    This is powered by :meth:`.Bot.is_owner`.

    This check raises a special exception, :exc:`.NotOwner` that is derived
    from :exc:`.CheckFailure`.
    """

    async def predicate(ctx: disnake.ApplicationCommandInteraction) -> bool:
        if not await ctx.bot.is_owner(ctx.author):
            msg = "You do not own this bot."
            raise NotOwner(msg)
        return True

    return check(predicate)


def is_nsfw() -> Callable[[T], T]:
    """A :func:`.check` that checks if the channel is a NSFW channel.

    This check raises a special exception, :exc:`.NSFWChannelRequired`
    that is derived from :exc:`.CheckFailure`.

    .. versionchanged:: 1.1

        Raise :exc:`.NSFWChannelRequired` instead of generic :exc:`.CheckFailure`.
        DM channels will also now pass this check.
    """

    def pred(ctx: disnake.ApplicationCommandInteraction) -> bool:
        ch = ctx.channel
        if ctx.guild is None or (
            isinstance(
                ch,
                (
                    disnake.TextChannel,
                    disnake.VoiceChannel,
                    disnake.Thread,
                    disnake.StageChannel,
                ),
            )
            and ch.is_nsfw()
        ):
            return True
        raise NSFWChannelRequired(ch)  # pyright: ignore[reportArgumentType]

    return check(pred)


def cooldown(
    rate: int, per: float, type: BucketType | Callable[[Message], Any] = BucketType.default
) -> Callable[[T], T]:
    r"""A decorator that adds a cooldown to a :class:`.Command`

    A cooldown allows a command to only be used a specific amount
    of times in a specific time frame. These cooldowns can be based
    either on a per-guild, per-channel, per-user, per-role or global basis.
    Denoted by the third argument of ``type`` which must be of enum
    type :class:`.BucketType`.

    If a cooldown is triggered, then :exc:`.CommandOnCooldown` is triggered in
    :func:`.on_command_error` and the local error handler.

    A command can only have a single cooldown.

    Parameters
    ----------
    rate: :class:`int`
        The number of times a command can be used before triggering a cooldown.
    per: :class:`float`
        The amount of seconds to wait for a cooldown when it's been triggered.
    type: :class:`.BucketType` | :class:`~collections.abc.Callable`\[[:class:`.Message`], :data:`~typing.Any`]
        The type of cooldown to have. If callable, should return a key for the mapping.

        .. versionchanged:: 1.7
            Callables are now supported for custom bucket types.
    """

    def decorator(
        func: Command[CogT, P, T] | CoroFunc,
    ) -> Command[CogT, P, T] | CoroFunc:
        if hasattr(func, "__command_flag__"):
            func._buckets = CooldownMapping(Cooldown(rate, per), type)
        else:
            func.__commands_cooldown__ = CooldownMapping(Cooldown(rate, per), type)  # pyright: ignore[reportAttributeAccessIssue]
        return func

    return decorator  # pyright: ignore[reportReturnType]


def dynamic_cooldown(
    cooldown: BucketType | Callable[[Message], Any], type: BucketType = BucketType.default
) -> Callable[[T], T]:
    r"""A decorator that adds a dynamic cooldown to a :class:`.Command`

    This differs from :func:`.cooldown` in that it takes a function that
    accepts a single parameter of type :class:`.disnake.Message` and must
    return a :class:`.Cooldown` or :data:`None`. If :data:`None` is returned then
    that cooldown is effectively bypassed.

    A cooldown allows a command to only be used a specific amount
    of times in a specific time frame. These cooldowns can be based
    either on a per-guild, per-channel, per-user, per-role or global basis.
    Denoted by the third argument of ``type`` which must be of enum
    type :class:`.BucketType`.

    If a cooldown is triggered, then :exc:`.CommandOnCooldown` is triggered in
    :func:`.on_command_error` and the local error handler.

    A command can only have a single cooldown.

    .. versionadded:: 2.0

    Parameters
    ----------
    cooldown: :class:`~collections.abc.Callable`\[[:class:`.disnake.Message`], :class:`.Cooldown` | :data:`None`]
        A function that takes a message and returns a cooldown that will
        apply to this invocation or :data:`None` if the cooldown should be bypassed.
    type: :class:`.BucketType`
        The type of cooldown to have.
    """
    if not callable(cooldown):
        msg = "A callable must be provided"
        raise TypeError(msg)

    def decorator(
        func: Command[CogT, P, T] | CoroFunc,
    ) -> Command[CogT, P, T] | CoroFunc:
        if hasattr(func, "__command_flag__"):
            func._buckets = DynamicCooldownMapping(cooldown, type)
        else:
            func.__commands_cooldown__ = DynamicCooldownMapping(cooldown, type)  # pyright: ignore[reportAttributeAccessIssue]
        return func

    return decorator  # pyright: ignore[reportReturnType]


def max_concurrency(
    number: int, per: BucketType = BucketType.default, *, wait: bool = False
) -> Callable[[T], T]:
    """A decorator that adds a maximum concurrency to a :class:`.Command` or its subclasses.

    This enables you to only allow a certain number of command invocations at the same time,
    for example if a command takes too long or if only one user can use it at a time. This
    differs from a cooldown in that there is no set waiting period or token bucket -- only
    a set number of people can run the command.

    .. versionadded:: 1.3

    Parameters
    ----------
    number: :class:`int`
        The maximum number of invocations of this command that can be running at the same time.
    per: :class:`.BucketType`
        The bucket that this concurrency is based on, e.g. ``BucketType.guild`` would allow
        it to be used up to ``number`` times per guild.
    wait: :class:`bool`
        Whether the command should wait for the queue to be over. If this is set to ``False``
        then instead of waiting until the command can run again, the command raises
        :exc:`.MaxConcurrencyReached` to its error handler. If this is set to ``True``
        then the command waits until it can be executed.
    """

    def decorator(
        func: Command[CogT, P, T] | CoroFunc,
    ) -> Command[CogT, P, T] | CoroFunc:
        value = MaxConcurrency(number, per=per, wait=wait)
        if hasattr(func, "__command_flag__"):
            func._max_concurrency = value
        else:
            func.__commands_max_concurrency__ = value  # pyright: ignore[reportAttributeAccessIssue]
        return func

    return decorator  # pyright: ignore[reportReturnType]


def before_invoke(coro) -> Callable[[T], T]:
    """A decorator that registers a coroutine as a pre-invoke hook.

    This allows you to refer to one before invoke hook for several commands that
    do not have to be within the same cog.

    .. versionadded:: 1.4

    Example
    -------
    .. code-block:: python3

        async def record_usage(ctx):
            print(ctx.author, 'used', ctx.command, 'at', ctx.message.created_at)

        @bot.command()
        @commands.before_invoke(record_usage)
        async def who(ctx): # Output: <User> used who at <Time>
            await ctx.send('i am a bot')

        class What(commands.Cog):

            @commands.before_invoke(record_usage)
            @commands.command()
            async def when(self, ctx): # Output: <User> used when at <Time>
                await ctx.send(f'and i have existed since {ctx.bot.user.created_at}')

            @commands.command()
            async def where(self, ctx): # Output: <Nothing>
                await ctx.send('on Discord')

            @commands.command()
            async def why(self, ctx): # Output: <Nothing>
                await ctx.send('because someone made me')

        bot.add_cog(What())
    """

    def decorator(
        func: Command[CogT, P, T] | CoroFunc,
    ) -> Command[CogT, P, T] | CoroFunc:
        if hasattr(func, "__command_flag__"):
            func.before_invoke(coro)
        else:
            func.__before_invoke__ = coro  # pyright: ignore[reportAttributeAccessIssue]
        return func

    return decorator  # pyright: ignore[reportReturnType]


def after_invoke(coro) -> Callable[[T], T]:
    """A decorator that registers a coroutine as a post-invoke hook.

    This allows you to refer to one after invoke hook for several commands that
    do not have to be within the same cog.

    .. versionadded:: 1.4
    """

    def decorator(
        func: Command[CogT, P, T] | CoroFunc,
    ) -> Command[CogT, P, T] | CoroFunc:
        if hasattr(func, "__command_flag__"):
            func.after_invoke(coro)
        else:
            func.__after_invoke__ = coro  # pyright: ignore[reportAttributeAccessIssue]
        return func

    return decorator  # pyright: ignore[reportReturnType]
