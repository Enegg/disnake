# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
from abc import ABC
from collections.abc import Callable, Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeAlias,
    overload,
    runtime_checkable,
)

from . import utils
from .enums import (
    ChannelType,
)
from .file import File
from .flags import ChannelFlags, MessageFlags
from .mentions import AllowedMentions
from .object import Object
from .permissions import PermissionOverwrite, Permissions
from .role import Role

__all__ = (
    "Snowflake",
    "User",
    "PrivateChannel",
    "GuildChannel",
    "Messageable",
)

if TYPE_CHECKING:
    from datetime import datetime

    from .asset import Asset
    from .channel import CategoryChannel, DMChannel, GroupChannel, PartialMessageable
    from .embeds import Embed
    from .guild import Guild, GuildChannel as AnyGuildChannel, GuildMessageable
    from .iterators import HistoryIterator
    from .member import Member
    from .message import Message, MessageReference, PartialMessage
    from .poll import Poll
    from .state import ConnectionState
    from .types.channel import (
        GuildChannel as GuildChannelPayload,
        OverwriteType,
        PermissionOverwrite as PermissionOverwritePayload,
    )
    from .ui._types import MessageComponents
    from .user import ClientUser

    MessageableChannel: TypeAlias = GuildMessageable | DMChannel | GroupChannel | PartialMessageable
    # include non-messageable channels, e.g. category/forum
    AnyChannel: TypeAlias = MessageableChannel | AnyGuildChannel

    SnowflakeTime: TypeAlias = "Snowflake | datetime"

MISSING = utils.MISSING


@runtime_checkable
class Snowflake(Protocol):
    """An ABC that details the common operations on a Discord model.

    Almost all :ref:`Discord models <discord_model>` meet this
    abstract base class.

    If you want to create a snowflake on your own, consider using
    :class:`.Object`.

    Attributes
    ----------
    id: :class:`int`
        The model's unique ID.
    """

    __slots__ = ()
    id: int


@runtime_checkable
class User(Snowflake, Protocol):
    """An ABC that details the common operations on a Discord user.

    The following classes implement this ABC:

    - :class:`~disnake.User`
    - :class:`~disnake.ClientUser`
    - :class:`~disnake.Member`

    This ABC must also implement :class:`~disnake.abc.Snowflake`.

    Attributes
    ----------
    name: :class:`str`
        The user's username.
    discriminator: :class:`str`
        The user's discriminator.

        .. note::
            This is being phased out by Discord; the username system is moving away from ``username#discriminator``
            to users having a globally unique username.
            The value of a single zero (``"0"``) indicates that the user has been migrated to the new system.
            See the `help article <https://dis.gd/app-usernames>`__ for details.

    global_name: :class:`str` | :data:`None`
        The user's global display name, if set.
        This takes precedence over :attr:`.name` when shown.

        .. versionadded:: 2.9

    bot: :class:`bool`
        Whether the user is a bot account.
    """

    __slots__ = ()

    name: str
    discriminator: str
    global_name: str | None
    bot: bool

    @property
    def display_name(self) -> str:
        """:class:`str`: Returns the user's display name."""
        raise NotImplementedError

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention the given user."""
        raise NotImplementedError

    @property
    def avatar(self) -> Asset | None:
        """:class:`~disnake.Asset` | :data:`None`: Returns an :class:`~disnake.Asset` for
        the avatar the user has.
        """
        raise NotImplementedError


# FIXME: this shouldn't be a protocol. isinstance(thread, PrivateChannel) returns true, and issubclass doesn't work.
@runtime_checkable
class PrivateChannel(Snowflake, Protocol):
    """An ABC that details the common operations on a private Discord channel.

    The following classes implement this ABC:

    - :class:`~disnake.DMChannel`
    - :class:`~disnake.GroupChannel`

    This ABC must also implement :class:`~disnake.abc.Snowflake`.

    Attributes
    ----------
    me: :class:`~disnake.ClientUser`
        The user representing yourself.
    """

    __slots__ = ()

    me: ClientUser


class _Overwrites:
    __slots__ = ("id", "allow", "deny", "type")

    ROLE = 0
    MEMBER = 1

    def __init__(self, data: PermissionOverwritePayload) -> None:
        self.id: int = int(data["id"])
        self.allow: int = int(data.get("allow", 0))
        self.deny: int = int(data.get("deny", 0))
        self.type: OverwriteType = data["type"]

    def _asdict(self) -> PermissionOverwritePayload:
        return {
            "id": self.id,
            "allow": str(self.allow),
            "deny": str(self.deny),
            "type": self.type,
        }

    def is_role(self) -> bool:
        return self.type == 0

    def is_member(self) -> bool:
        return self.type == 1


class GuildChannel(ABC):
    """An ABC that details the common operations on a Discord guild channel.

    The following classes implement this ABC:

    - :class:`.TextChannel`
    - :class:`.VoiceChannel`
    - :class:`.CategoryChannel`
    - :class:`.StageChannel`
    - :class:`.ForumChannel`
    - :class:`.MediaChannel`

    This ABC must also implement :class:`.abc.Snowflake`.

    Attributes
    ----------
    name: :class:`str`
        The channel name.
    guild: :class:`.Guild`
        The guild the channel belongs to.
    position: :class:`int`
        The position in the channel list. This is a number that starts at 0.
        e.g. the top channel is position 0.
    """

    __slots__ = ()

    id: int
    name: str
    guild: Guild
    type: ChannelType
    position: int
    category_id: int | None
    _flags: int
    _state: ConnectionState
    _overwrites: list[_Overwrites]

    if TYPE_CHECKING:

        def __init__(
            self, *, state: ConnectionState, guild: Guild, data: Mapping[str, Any]
        ) -> None: ...

    def __str__(self) -> str:
        return self.name

    @property
    def _sorting_bucket(self) -> int:
        raise NotImplementedError

    def _update(self, guild: Guild, data: dict[str, Any]) -> None:
        raise NotImplementedError

    def _fill_overwrites(self, data: GuildChannelPayload) -> None:
        self._overwrites = []
        everyone_index = 0
        everyone_id = self.guild.id

        for index, overridden in enumerate(data.get("permission_overwrites", [])):
            overwrite = _Overwrites(overridden)
            self._overwrites.append(overwrite)

            if overwrite.type == _Overwrites.MEMBER:
                continue

            if overwrite.id == everyone_id:
                # the @everyone role is not guaranteed to be the first one
                # in the list of permission overwrites, however the permission
                # resolution code kind of requires that it is the first one in
                # the list since it is special. So we need the index so we can
                # swap it to be the first one.
                everyone_index = index

        # do the swap
        tmp = self._overwrites
        if tmp:
            tmp[everyone_index], tmp[0] = tmp[0], tmp[everyone_index]

    @property
    def changed_roles(self) -> list[Role]:
        r""":class:`list`\[:class:`.Role`]: Returns a list of roles that have been overridden from
        their default values in the :attr:`.Guild.roles` attribute.
        """
        ret: list[Role] = []
        g = self.guild
        for overwrite in filter(lambda o: o.is_role(), self._overwrites):
            role = g.get_role(overwrite.id)
            if role is None:
                continue

            role = copy.copy(role)
            role.permissions.handle_overwrite(overwrite.allow, overwrite.deny)
            ret.append(role)
        return ret

    @property
    def mention(self) -> str:
        """:class:`str`: The string that allows you to mention the channel."""
        return f"<#{self.id}>"

    @property
    def created_at(self) -> datetime:
        """:class:`datetime.datetime`: Returns the channel's creation time in UTC."""
        return utils.snowflake_time(self.id)

    def overwrites_for(self, obj: Role | User) -> PermissionOverwrite:
        """Returns the channel-specific overwrites for a member or a role.

        Parameters
        ----------
        obj: :class:`.Role` | :class:`.abc.User`
            The role or user denoting
            whose overwrite to get.

        Returns
        -------
        :class:`~disnake.PermissionOverwrite`
            The permission overwrites for this object.
        """
        predicate: Callable[[_Overwrites], bool]
        if isinstance(obj, User):
            predicate = lambda p: p.is_member()
        elif isinstance(obj, Role):
            predicate = lambda p: p.is_role()
        else:
            predicate = lambda p: True

        for overwrite in filter(predicate, self._overwrites):
            if overwrite.id == obj.id:
                allow = Permissions(overwrite.allow)
                deny = Permissions(overwrite.deny)
                return PermissionOverwrite.from_pair(allow, deny)

        return PermissionOverwrite()

    @property
    def overwrites(self) -> dict[Role | Member, PermissionOverwrite]:
        r"""Returns all of the channel's overwrites.

        This is returned as a dictionary where the key contains the target which
        can be either a :class:`~disnake.Role` or a :class:`~disnake.Member` and the value is the
        overwrite as a :class:`~disnake.PermissionOverwrite`.

        Returns
        -------
        :class:`dict`\[:class:`~disnake.Role` | :class:`~disnake.Member`, :class:`~disnake.PermissionOverwrite`]
            The channel's permission overwrites.
        """
        ret = {}
        for ow in self._overwrites:
            allow = Permissions(ow.allow)
            deny = Permissions(ow.deny)
            overwrite = PermissionOverwrite.from_pair(allow, deny)
            target = None

            if ow.is_role():
                target = self.guild.get_role(ow.id)
            elif ow.is_member():
                target = self.guild.get_member(ow.id)

            # TODO: There is potential data loss here in the non-chunked
            # case, i.e. target is None because get_member returned nothing.
            # This can be fixed with a slight breaking change to the return type,
            # i.e. adding disnake.Object to the list of it
            # However, for now this is an acceptable compromise.
            if target is not None:
                ret[target] = overwrite
        return ret

    @property
    def category(self) -> CategoryChannel | None:
        """:class:`~disnake.CategoryChannel` | :data:`None`: The category this channel belongs to.

        If there is no category then this is :data:`None`.
        """
        if isinstance(self.guild, Object):
            return None
        return self.guild.get_channel(self.category_id)  # pyright: ignore[reportReturnType, reportArgumentType]

    @property
    def permissions_synced(self) -> bool:
        """:class:`bool`: Whether or not the permissions for this channel are synced with the
        category it belongs to.

        If there is no category then this is ``False``.

        .. versionadded:: 1.3
        """
        if self.category_id is None or isinstance(self.guild, Object):
            return False

        category = self.guild.get_channel(self.category_id)
        return bool(category and category.overwrites == self.overwrites)

    @property
    def flags(self) -> ChannelFlags:
        """:class:`.ChannelFlags`: The channel flags for this channel.

        .. versionadded:: 2.6
        """
        return ChannelFlags._from_value(self._flags)

    @property
    def jump_url(self) -> str:
        """A URL that can be used to jump to this channel.

        .. versionadded:: 2.4

        .. note::

            This exists for all guild channels but may not be usable by the client for all guild channel types.
        """
        return f"https://discord.com/channels/{self.guild.id}/{self.id}"

    def _apply_implict_permissions(self, base: Permissions) -> None:
        # if you can't send a message in a channel then you can't have certain
        # permissions as well
        if not base.send_messages:
            base.send_tts_messages = False
            base.send_voice_messages = False
            base.send_polls = False
            base.mention_everyone = False
            base.embed_links = False
            base.attach_files = False

        # if you can't view a channel then you have no permissions there
        if not base.view_channel:
            denied = Permissions.all_channel()
            base.value &= ~denied.value

    def permissions_for(
        self,
        obj: Member | Role,
        /,
        *,
        ignore_timeout: bool = MISSING,
    ) -> Permissions:
        """Handles permission resolution for the :class:`~disnake.Member`
        or :class:`~disnake.Role`.

        This function takes into consideration the following cases:

        - Guild owner
        - Guild roles
        - Channel overrides
        - Member overrides
        - Timeouts

        If a :class:`~disnake.Role` is passed, then it checks the permissions
        someone with that role would have, which is essentially:

        - The default role permissions
        - The permissions of the role used as a parameter
        - The default role permission overwrites
        - The permission overwrites of the role used as a parameter

        .. note::
            If the channel originated from an :class:`.Interaction` and
            the :attr:`.guild` attribute is unavailable, such as with
            user-installed applications in guilds, this method will not work
            due to an API limitation.
            Consider using :attr:`.Interaction.permissions` or :attr:`~.Interaction.app_permissions` instead.

        .. versionchanged:: 2.0
            The object passed in can now be a role object.

        Parameters
        ----------
        obj: :class:`~disnake.Member` | :class:`~disnake.Role`
            The object to resolve permissions for. This could be either
            a member or a role. If it's a role then member overwrites
            are not computed.
        ignore_timeout: :class:`bool`
            Whether or not to ignore the user's timeout.
            Defaults to ``False``.

            .. versionadded:: 2.4

            .. note::

                This only applies to :class:`~disnake.Member` objects.

            .. versionchanged:: 2.6

                The default was changed to ``False``.

        Raises
        ------
        TypeError
            ``ignore_timeout`` is only supported for :class:`~disnake.Member` objects.

        Returns
        -------
        :class:`~disnake.Permissions`
            The resolved permissions for the member or role.
        """
        # The current cases can be explained as:
        # Guild owner get all permissions -- no questions asked. Otherwise...
        # The @everyone role gets the first application.
        # After that, the applied roles that the user has in the channel
        # (or otherwise) are then OR'd together.
        # After the role permissions are resolved, the member permissions
        # have to take into effect.
        # After all that is done.. you have to do the following:

        # The operation first takes into consideration the denied
        # and then the allowed.

        # Timeouted users have only view_channel and read_message_history
        # if they already have them.
        if ignore_timeout is not MISSING and isinstance(obj, Role):
            msg = "ignore_timeout is only supported for disnake.Member objects"
            raise TypeError(msg)

        if ignore_timeout is MISSING:
            ignore_timeout = False

        if self.guild.owner_id == obj.id:
            return Permissions.all()

        default = self.guild.default_role
        base = Permissions(default.permissions.value)

        # Handle the role case first
        if isinstance(obj, Role):
            base.value |= obj._permissions

            if base.administrator:
                return Permissions.all()

            # Apply @everyone allow/deny first since it's special
            try:
                maybe_everyone = self._overwrites[0]
                if maybe_everyone.id == self.guild.id:
                    base.handle_overwrite(allow=maybe_everyone.allow, deny=maybe_everyone.deny)
            except IndexError:
                pass

            if obj.is_default():
                return base

            overwrite = utils.get(self._overwrites, type=_Overwrites.ROLE, id=obj.id)
            if overwrite is not None:
                base.handle_overwrite(overwrite.allow, overwrite.deny)

            return base

        roles = obj._roles
        get_role = self.guild.get_role

        # Apply guild roles that the member has.
        for role_id in roles:
            role = get_role(role_id)
            if role is not None:
                base.value |= role._permissions

        # Guild-wide Administrator -> True for everything
        # Bypass all channel-specific overrides
        if base.administrator:
            return Permissions.all()

        # Apply @everyone allow/deny first since it's special
        try:
            maybe_everyone = self._overwrites[0]
            if maybe_everyone.id == self.guild.id:
                base.handle_overwrite(allow=maybe_everyone.allow, deny=maybe_everyone.deny)
                remaining_overwrites = self._overwrites[1:]
            else:
                remaining_overwrites = self._overwrites
        except IndexError:
            remaining_overwrites = self._overwrites

        denies = 0
        allows = 0

        # Apply channel specific role permission overwrites
        for overwrite in remaining_overwrites:
            if overwrite.is_role() and roles.has(overwrite.id):
                denies |= overwrite.deny
                allows |= overwrite.allow

        base.handle_overwrite(allow=allows, deny=denies)

        # Apply member specific permission overwrites
        for overwrite in remaining_overwrites:
            if overwrite.is_member() and overwrite.id == obj.id:
                base.handle_overwrite(allow=overwrite.allow, deny=overwrite.deny)
                break

        # if you have a timeout then you can't have any permissions
        # except read messages and read message history
        if not ignore_timeout and obj.current_timeout:
            allowed = Permissions(view_channel=True, read_message_history=True)
            base.value &= allowed.value

        return base


class Messageable:
    """An ABC that details the common operations on a model that can send messages.

    The following classes implement this ABC:

    - :class:`~disnake.TextChannel`
    - :class:`~disnake.DMChannel`
    - :class:`~disnake.GroupChannel`
    - :class:`~disnake.User`
    - :class:`~disnake.Member`
    - :class:`~disnake.Thread`
    - :class:`~disnake.VoiceChannel`
    - :class:`~disnake.StageChannel`
    - :class:`~disnake.ext.commands.Context`
    - :class:`~disnake.PartialMessageable`
    """

    __slots__ = ()
    _state: ConnectionState

    async def _get_channel(self) -> MessageableChannel:
        raise NotImplementedError

    @overload
    async def send(
        self,
        content: str | None = ...,
        *,
        tts: bool = ...,
        embed: Embed = ...,
        file: File = ...,
        nonce: str | int = ...,
        suppress_embeds: bool = ...,
        flags: MessageFlags = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Message | MessageReference | PartialMessage = ...,
        mention_author: bool = ...,
        components: MessageComponents = ...,
        poll: Poll = ...,
    ) -> Message: ...

    @overload
    async def send(
        self,
        content: str | None = ...,
        *,
        tts: bool = ...,
        embed: Embed = ...,
        files: list[File] = ...,
        nonce: str | int = ...,
        suppress_embeds: bool = ...,
        flags: MessageFlags = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Message | MessageReference | PartialMessage = ...,
        mention_author: bool = ...,
        components: MessageComponents = ...,
        poll: Poll = ...,
    ) -> Message: ...

    @overload
    async def send(
        self,
        content: str | None = ...,
        *,
        tts: bool = ...,
        embeds: list[Embed] = ...,
        file: File = ...,
        nonce: str | int = ...,
        suppress_embeds: bool = ...,
        flags: MessageFlags = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Message | MessageReference | PartialMessage = ...,
        mention_author: bool = ...,
        components: MessageComponents = ...,
        poll: Poll = ...,
    ) -> Message: ...

    @overload
    async def send(
        self,
        content: str | None = ...,
        *,
        tts: bool = ...,
        embeds: list[Embed] = ...,
        files: list[File] = ...,
        nonce: str | int = ...,
        suppress_embeds: bool = ...,
        flags: MessageFlags = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Message | MessageReference | PartialMessage = ...,
        mention_author: bool = ...,
        components: MessageComponents = ...,
        poll: Poll = ...,
    ) -> Message: ...

    async def send(
        self,
        content: str | None = None,
        *,
        tts: bool = False,
        embed: Embed | None = None,
        embeds: list[Embed] | None = None,
        file: File | None = None,
        files: list[File] | None = None,
        nonce: str | int | None = None,
        suppress_embeds: bool | None = None,
        flags: MessageFlags | None = None,
        allowed_mentions: AllowedMentions | None = None,
        reference: Message | MessageReference | PartialMessage | None = None,
        mention_author: bool | None = None,
        components: MessageComponents | None = None,
        poll: Poll | None = None,
    ):
        r"""|coro|

        Sends a message to the destination with the content given.

        The content must be a type that can convert to a string through ``str(content)``.

        At least one of ``content``, ``embed``/``embeds``, ``file``/``files``,
        ``components``, ``poll`` or ``view`` must be provided.

        To upload a single file, the ``file`` parameter should be used with a
        single :class:`~disnake.File` object. To upload multiple files, the ``files``
        parameter should be used with a :class:`list` of :class:`~disnake.File` objects.
        **Specifying both parameters will lead to an exception**.

        To upload a single embed, the ``embed`` parameter should be used with a
        single :class:`.Embed` object. To upload multiple embeds, the ``embeds``
        parameter should be used with a :class:`list` of :class:`.Embed` objects.
        **Specifying both parameters will lead to an exception**.

        .. versionchanged:: 2.6
            Raises :exc:`TypeError` or :exc:`ValueError` instead of ``InvalidArgument``.

        Parameters
        ----------
        content: :class:`str` | :data:`None`
            The content of the message to send.
        tts: :class:`bool`
            Whether the message should be sent using text-to-speech.
        embed: :class:`.Embed`
            The rich embed for the content to send. This cannot be mixed with the
            ``embeds`` parameter.
        embeds: :class:`list`\[:class:`.Embed`]
            A list of embeds to send with the content. Must be a maximum of 10.
            This cannot be mixed with the ``embed`` parameter.

            .. versionadded:: 2.0

        file: :class:`~disnake.File`
            The file to upload. This cannot be mixed with the ``files`` parameter.
        files: :class:`list`\[:class:`~disnake.File`]
            A list of files to upload. Must be a maximum of 10.
            This cannot be mixed with the ``file`` parameter.
        nonce: :class:`str` | :class:`int`
            The nonce to use for sending this message. If the message was successfully sent,
            then the message will have a nonce with this value.
        allowed_mentions: :class:`.AllowedMentions`
            Controls the mentions being processed in this message. If this is
            passed, then the object is merged with :attr:`.Client.allowed_mentions`.
            The merging behaviour only overrides attributes that have been explicitly passed
            to the object, otherwise it uses the attributes set in :attr:`.Client.allowed_mentions`.
            If no object is passed at all then the defaults given by :attr:`.Client.allowed_mentions`
            are used instead.

            .. versionadded:: 1.4

        reference: :class:`.Message` | :class:`.MessageReference` | :class:`.PartialMessage`
            A reference to the :class:`.Message` to which you are replying, this can be created using
            :meth:`.Message.to_reference` or passed directly as a :class:`.Message`. You can control
            whether this mentions the author of the referenced message using the :attr:`.AllowedMentions.replied_user`
            attribute of ``allowed_mentions`` or by setting ``mention_author``.

            .. versionadded:: 1.6

            .. note::

                Passing a :class:`.Message` or :class:`.PartialMessage` will only allow replies. To forward a message
                you must explicitly transform the message to a :class:`.MessageReference` using :meth:`.Message.to_reference` and specify the :class:`.MessageReferenceType`,
                or use :meth:`.Message.forward`.

        mention_author: :class:`bool` | :data:`None`
            If set, overrides the :attr:`.AllowedMentions.replied_user` attribute of ``allowed_mentions``.

            .. versionadded:: 1.6

        components: |components_type|
            A list of components to include in the message. This cannot be mixed with ``view``.

            .. versionadded:: 2.4

            .. note::
                Passing v2 components here automatically sets the :attr:`~.MessageFlags.is_components_v2` flag.
                Setting this flag cannot be reverted. Note that this also disables the
                ``content``, ``embeds``, ``stickers``, and ``poll`` fields.

        suppress_embeds: :class:`bool`
            Whether to suppress embeds for the message. This hides
            all the embeds from the UI if set to ``True``.

            .. versionadded:: 2.5

        flags: :class:`.MessageFlags`
            The flags to set for this message.
            Only :attr:`~.MessageFlags.suppress_embeds`, :attr:`~.MessageFlags.suppress_notifications`,
            and :attr:`~.MessageFlags.is_components_v2` are supported.

            If parameter ``suppress_embeds`` is provided,
            that will override the setting of :attr:`.MessageFlags.suppress_embeds`.

            .. versionadded:: 2.9

        poll: :class:`.Poll`
            The poll to send with the message.

            .. versionadded:: 2.10

        Raises
        ------
        HTTPException
            Sending the message failed.
        Forbidden
            You do not have the proper permissions to send the message.
        TypeError
            Specified both ``file`` and ``files``,
            or you specified both ``embed`` and ``embeds``,
            or you specified both ``view`` and ``components``,
            or the ``reference`` object is not a :class:`.Message`,
            :class:`.MessageReference` or :class:`.PartialMessage`.
        ValueError
            The ``files`` or ``embeds`` list is too large, or
            you tried to send v2 components together with ``content``, ``embeds``, ``stickers``, or ``poll``.

        Returns
        -------
        :class:`.Message`
            The message that was sent.
        """
        channel = await self._get_channel()
        state = self._state
        content = str(content) if content is not None else None

        if file is not None and files is not None:
            msg = "cannot pass both file and files parameter to send()"
            raise TypeError(msg)

        if file is not None:
            if not isinstance(file, File):
                msg = "file parameter must be File"
                raise TypeError(msg)
            files = [file]

        if embed is not None and embeds is not None:
            msg = "cannot pass both embed and embeds parameter to send()"
            raise TypeError(msg)

        if embed is not None:
            embeds = [embed]

        embeds_payload = None
        if embeds is not None:
            if len(embeds) > 10:
                msg = "embeds parameter must be a list of up to 10 elements"
                raise ValueError(msg)
            for embed in embeds:
                if embed._files:
                    files = files or []
                    files.extend(embed._files.values())
            embeds_payload = [embed.to_dict() for embed in embeds]

        poll_payload = None
        if poll:
            poll_payload = poll._to_dict()

        allowed_mentions_payload = None
        if allowed_mentions is None:
            allowed_mentions_payload = state.allowed_mentions and state.allowed_mentions.to_dict()
        elif state.allowed_mentions is not None:
            allowed_mentions_payload = state.allowed_mentions.merge(allowed_mentions).to_dict()
        else:
            allowed_mentions_payload = allowed_mentions.to_dict()

        if mention_author is not None:
            allowed_mentions_payload = allowed_mentions_payload or AllowedMentions().to_dict()
            allowed_mentions_payload["replied_user"] = bool(mention_author)

        reference_payload = None
        if reference is not None:
            try:
                reference_payload = reference.to_message_reference_dict()
            except AttributeError:
                msg = "reference parameter must be Message, MessageReference, or PartialMessage"
                raise TypeError(msg) from None

        is_v2 = False
        if components:
            from .ui.action_row import normalize_components_to_dict

            components_payload, is_v2 = normalize_components_to_dict(components)
        else:
            components_payload = None

        # set cv2 flag automatically
        if is_v2:
            flags = MessageFlags._from_value(0 if flags is None else flags.value)
            flags.is_components_v2 = True
        # components v2 cannot be used with other content fields
        if flags and flags.is_components_v2 and (content or embeds or poll):
            msg = "Cannot use v2 components with content, embeds, or polls"
            raise ValueError(msg)

        flags_payload = None
        if suppress_embeds is not None:
            flags = MessageFlags._from_value(0 if flags is None else flags.value)
            flags.suppress_embeds = suppress_embeds
        if flags is not None:
            flags_payload = flags.value

        if files is not None:
            if len(files) > 10:
                msg = "files parameter must be a list of up to 10 elements"
                raise ValueError(msg)
            elif not all(isinstance(file, File) for file in files):
                msg = "files parameter must be a list of File"
                raise TypeError(msg)

            try:
                data = await state.http.send_files(
                    channel.id,
                    files=files,
                    content=content,
                    tts=tts,
                    embeds=embeds_payload,
                    nonce=nonce,
                    allowed_mentions=allowed_mentions_payload,
                    message_reference=reference_payload,
                    components=components_payload,
                    poll=poll_payload,
                    flags=flags_payload,
                )
            finally:
                for f in files:
                    f.close()
        else:
            data = await state.http.send_message(
                channel.id,
                content,
                tts=tts,
                embeds=embeds_payload,
                nonce=nonce,
                allowed_mentions=allowed_mentions_payload,
                message_reference=reference_payload,
                components=components_payload,
                poll=poll_payload,
                flags=flags_payload,
            )

        return state.create_message(channel=channel, data=data)


    async def trigger_typing(self) -> None:
        """|coro|

        Triggers a *typing* indicator to the destination.

        *Typing* indicator will go away after 10 seconds, or after a message is sent.
        """
        channel = await self._get_channel()
        await self._state.http.send_typing(channel.id)

    async def fetch_message(self, id: int, /) -> Message:
        """|coro|

        Retrieves a single :class:`.Message` from the destination.

        Parameters
        ----------
        id: :class:`int`
            The message ID to look for.

        Raises
        ------
        NotFound
            The specified message was not found.
        Forbidden
            You do not have the permissions required to get a message.
        HTTPException
            Retrieving the message failed.

        Returns
        -------
        :class:`.Message`
            The message asked for.
        """
        channel = await self._get_channel()
        data = await self._state.http.get_message(channel.id, id)
        return self._state.create_message(channel=channel, data=data)

    def history(
        self,
        *,
        limit: int | None = 100,
        before: SnowflakeTime | None = None,
        after: SnowflakeTime | None = None,
        around: SnowflakeTime | None = None,
        oldest_first: bool | None = None,
    ) -> HistoryIterator:
        """Returns an :class:`.AsyncIterator` that enables receiving the destination's message history.

        You must have :attr:`.Permissions.read_message_history` permission to use this.

        Examples
        --------
        Usage ::

            counter = 0
            async for message in channel.history(limit=200):
                if message.author == client.user:
                    counter += 1

        Flattening into a list: ::

            messages = await channel.history(limit=123).flatten()
            # messages is now a list of Message...

        All parameters are optional.

        Parameters
        ----------
        limit: :class:`int` | :data:`None`
            The number of messages to retrieve.
            If :data:`None`, retrieves every message in the channel. Note, however,
            that this would make it a slow operation.
        before: :class:`.abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
            Retrieve messages before this date or message.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
        after: :class:`.abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
            Retrieve messages after this date or message.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
        around: :class:`.abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
            Retrieve messages around this date or message.
            If a datetime is provided, it is recommended to use a UTC aware datetime.
            If the datetime is naive, it is assumed to be local time.
            When using this argument, the maximum limit is 101. Note that if the limit is an
            even number then this will return at most limit + 1 messages.
        oldest_first: :class:`bool` | :data:`None`
            If set to ``True``, return messages in oldest->newest order. Defaults to ``True`` if
            ``after`` is specified, otherwise ``False``.

        Raises
        ------
        Forbidden
            You do not have permissions to get channel message history.
        HTTPException
            The request to get message history failed.

        Yields
        ------
        :class:`.Message`
            The message with the message data parsed.
        """
        from .iterators import HistoryIterator  # cyclic import

        return HistoryIterator(
            self, limit=limit, before=before, after=after, around=around, oldest_first=oldest_first
        )
