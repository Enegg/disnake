# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
import datetime
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from .entitlement import Entitlement
from .errors import NoMoreItems
from .object import Object
from .utils import maybe_coroutine, time_snowflake

__all__ = (
    "ReactionIterator",
    "HistoryIterator",
    "GuildIterator",
    "MemberIterator",
    "EntitlementIterator",
)

if TYPE_CHECKING:
    from .abc import Messageable, Snowflake
    from .client import Client
    from .guild import Guild
    from .member import Member
    from .message import Message
    from .state import ConnectionState
    from .types.entitlement import Entitlement as EntitlementPayload
    from .types.guild import Guild as GuildPayload
    from .types.member import MemberWithUser as MemberWithUserPayload
    from .types.message import Message as MessagePayload
    from .types.user import PartialUser as PartialUserPayload
    from .user import User

T = TypeVar("T")
OT = TypeVar("OT")
_Func = Callable[[T], OT | Awaitable[OT]]

OLDEST_OBJECT = Object(id=0)


class _AsyncIterator(AsyncIterator[T]):
    __slots__ = ()

    async def next(self) -> T:
        raise NotImplementedError

    def get(self, **attrs: Any) -> Awaitable[T | None]:
        def predicate(elem: T) -> bool:
            for attr, val in attrs.items():
                nested = attr.split("__")
                obj = elem
                for attribute in nested:
                    obj = getattr(obj, attribute)

                if obj != val:
                    return False
            return True

        return self.find(predicate)

    async def find(self, predicate: _Func[T, bool]) -> T | None:
        while True:
            try:
                elem = await self.next()
            except NoMoreItems:
                return None

            ret = await maybe_coroutine(predicate, elem)
            if ret:
                return elem

    def chunk(self, max_size: int) -> _ChunkedAsyncIterator[T]:
        if max_size <= 0:
            msg = "async iterator chunk sizes must be greater than 0."
            raise ValueError(msg)
        return _ChunkedAsyncIterator(self, max_size)

    def map(self, func: _Func[T, OT]) -> _MappedAsyncIterator[OT]:
        return _MappedAsyncIterator(self, func)

    def filter(self, predicate: _Func[T, bool] | None) -> _FilteredAsyncIterator[T]:
        return _FilteredAsyncIterator(self, predicate)

    async def flatten(self) -> list[T]:
        return [element async for element in self]

    async def __anext__(self) -> T:
        try:
            return await self.next()
        except NoMoreItems:
            raise StopAsyncIteration from None


class _ChunkedAsyncIterator(_AsyncIterator[list[T]]):
    def __init__(self, iterator: _AsyncIterator[T], max_size: int) -> None:
        self.iterator = iterator
        self.max_size = max_size

    async def next(self) -> list[T]:
        ret: list[T] = []
        n = 0
        while n < self.max_size:
            try:
                item = await self.iterator.next()
            except NoMoreItems:
                if ret:
                    return ret
                raise
            else:
                ret.append(item)
                n += 1
        return ret


class _MappedAsyncIterator(_AsyncIterator[OT]):
    def __init__(self, iterator: _AsyncIterator[T], func: _Func[T, OT]) -> None:
        self.iterator = iterator
        self.func = func

    async def next(self) -> OT:
        # this raises NoMoreItems and will propagate appropriately
        item = await self.iterator.next()
        return await maybe_coroutine(self.func, item)


class _FilteredAsyncIterator(_AsyncIterator[T]):
    def __init__(self, iterator: _AsyncIterator[T], predicate: _Func[T, bool] | None) -> None:
        self.iterator = iterator

        if predicate is None:
            predicate = bool  # similar to the `filter` builtin, a `None` filter drops falsy items

        self.predicate: _Func[T, bool] = predicate

    async def next(self) -> T:
        getter = self.iterator.next
        pred = self.predicate
        while True:
            # propagate NoMoreItems similar to _MappedAsyncIterator
            item = await getter()
            ret = await maybe_coroutine(pred, item)
            if ret:
                return item


class ReactionIterator(_AsyncIterator[Union["User", "Member"]]):
    def __init__(self, message, emoji, limit: int = 100, after=None) -> None:
        self.message = message
        self.limit = limit
        self.after = after
        state = message._state
        self.getter = state.http.get_reaction_users
        self.state = state
        self.emoji = emoji
        self.guild = message.guild
        self.channel_id = message.channel.id
        self.users = asyncio.Queue()

    async def next(self) -> User | Member:
        if self.users.empty():
            await self.fill_users()

        try:
            return self.users.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems from None

    async def fill_users(self) -> None:
        if self.limit > 0:
            retrieve = min(self.limit, 100)

            after = self.after.id if self.after else None
            data: list[PartialUserPayload] = await self.getter(
                self.channel_id, self.message.id, self.emoji, retrieve, after=after
            )

            if data:
                self.limit -= retrieve
                self.after = Object(id=int(data[-1]["id"]))

            for element in reversed(data):
                if self.guild is None or isinstance(self.guild, Object):
                    await self.users.put(self.state.create_user(data=element))
                else:
                    member_id = int(element["id"])
                    member = self.guild.get_member(member_id)
                    if member is not None:
                        await self.users.put(member)
                    else:
                        await self.users.put(self.state.create_user(data=element))


class HistoryIterator(_AsyncIterator["Message"]):
    """Iterator for receiving a channel's message history.

    The messages endpoint has two behaviours we care about here:
    If ``before`` is specified, the messages endpoint returns the `limit`
    newest messages before ``before``, sorted with newest first. For filling over
    100 messages, update the ``before`` parameter to the oldest message received.
    Messages will be returned in order by time.
    If ``after`` is specified, it returns the ``limit`` oldest messages after
    ``after``, sorted with newest first. For filling over 100 messages, update the
    ``after`` parameter to the newest message received. If messages are not
    reversed, they will be out of order (99-0, 199-100, so on)

    A note that if both ``before`` and ``after`` are specified, ``before`` is ignored by the
    messages endpoint.

    Parameters
    ----------
    messageable: :class:`abc.Messageable`
        Messageable class to retrieve message history from.
    limit: :class:`int`
        Maximum number of messages to retrieve
    before: :class:`abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
        Message before which all messages must be.
    after: :class:`abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
        Message after which all messages must be.
    around: :class:`abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
        Message around which all messages must be. Limit max 101. Note that if
        limit is an even number, this will return at most limit+1 messages.
    oldest_first: :class:`bool` | :data:`None`
        If set to ``True``, return messages in oldest->newest order. Defaults to
        ``True`` if `after` is specified, otherwise ``False``.
    """

    def __init__(
        self,
        messageable: Messageable,
        limit: int | None = 100,
        before: Snowflake | datetime.datetime | None = None,
        after: Snowflake | datetime.datetime | None = None,
        around: Snowflake | datetime.datetime | None = None,
        oldest_first: bool | None = None,
    ) -> None:
        if isinstance(before, datetime.datetime):
            before = Object(id=time_snowflake(before, high=False))
        if isinstance(after, datetime.datetime):
            after = Object(id=time_snowflake(after, high=True))
        if isinstance(around, datetime.datetime):
            around = Object(id=time_snowflake(around))

        if oldest_first is None:
            self.reverse = after is not None
        else:
            self.reverse = oldest_first

        self.messageable = messageable
        self.limit = limit
        self.before = before
        self.after = after or OLDEST_OBJECT
        self.around = around

        self._filter: Callable[[MessagePayload], bool] | None = None

        self.state = self.messageable._state
        self.logs_from = self.state.http.logs_from
        self.messages = asyncio.Queue()

        if self.around:
            if self.limit is None:
                msg = "history does not support around with limit=None"
                raise ValueError(msg)
            if self.limit > 101:
                msg = "history max limit 101 when specifying around parameter"
                raise ValueError(msg)
            elif self.limit == 101:
                self.limit = 100  # Thanks Discord

            self._retrieve_messages = self._retrieve_messages_around_strategy
            if before and self.after:
                self._filter = lambda m: self.after.id < int(m["id"]) < before.id
            elif before:
                self._filter = lambda m: int(m["id"]) < before.id
            elif self.after:
                self._filter = lambda m: self.after.id < int(m["id"])
        else:
            if self.reverse:
                self._retrieve_messages = self._retrieve_messages_after_strategy
                if before:
                    self._filter = lambda m: int(m["id"]) < before.id
            else:
                self._retrieve_messages = self._retrieve_messages_before_strategy
                if self.after and self.after != OLDEST_OBJECT:
                    self._filter = lambda m: int(m["id"]) > self.after.id

    async def next(self) -> Message:
        if self.messages.empty():
            await self.fill_messages()

        try:
            return self.messages.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems from None

    def _get_retrieve(self) -> bool:
        limit = self.limit
        if limit is None or limit > 100:
            retrieve = 100
        else:
            retrieve = limit
        self.retrieve = retrieve
        return retrieve > 0

    async def fill_messages(self) -> None:
        if not hasattr(self, "channel"):
            # do the required set up
            channel = await self.messageable._get_channel()
            self.channel = channel

        if self._get_retrieve():
            data = await self._retrieve_messages(self.retrieve)
            if len(data) < 100:
                self.limit = 0  # terminate the infinite loop

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            channel = self.channel
            for element in data:
                await self.messages.put(self.state.create_message(channel=channel, data=element))

    async def _retrieve_messages(self, retrieve: int) -> list[MessagePayload]:
        """Retrieve messages and update next parameters."""
        raise NotImplementedError

    async def _retrieve_messages_before_strategy(self, retrieve: int) -> list[MessagePayload]:
        """Retrieve messages using before parameter."""
        before = self.before.id if self.before else None
        data: list[MessagePayload] = await self.logs_from(self.channel.id, retrieve, before=before)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.before = Object(id=int(data[-1]["id"]))
        return data

    async def _retrieve_messages_after_strategy(self, retrieve: int) -> list[MessagePayload]:
        """Retrieve messages using after parameter."""
        after = self.after.id if self.after else None
        data: list[MessagePayload] = await self.logs_from(self.channel.id, retrieve, after=after)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.after = Object(id=int(data[0]["id"]))
        return data

    async def _retrieve_messages_around_strategy(self, retrieve: int) -> list[MessagePayload]:
        """Retrieve messages using around parameter."""
        if self.around:
            around = self.around.id if self.around else None
            data: list[MessagePayload] = await self.logs_from(
                self.channel.id, retrieve, around=around
            )
            self.around = None
            return data
        return []


class GuildIterator(_AsyncIterator["Guild"]):
    """Iterator for receiving the client's guilds.

    The guilds endpoint has the same two behaviours as described
    in :class:`HistoryIterator`:
    If ``before`` is specified, the guilds endpoint returns the ``limit``
    newest guilds before ``before``, sorted with newest first. For filling over
    100 guilds, update the ``before`` parameter to the oldest guild received.
    Guilds will be returned in order by time.
    If `after` is specified, it returns the ``limit`` oldest guilds after ``after``,
    sorted with newest first. For filling over 100 guilds, update the ``after``
    parameter to the newest guild received, If guilds are not reversed, they
    will be out of order (99-0, 199-100, so on)

    Not that if both ``before`` and ``after`` are specified, ``before`` is ignored by the
    guilds endpoint.

    Parameters
    ----------
    bot: :class:`disnake.Client`
        The client to retrieve the guilds from.
    limit: :class:`int`
        Maximum number of guilds to retrieve.
    before: :class:`abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
        Object before which all guilds must be.
    after: :class:`abc.Snowflake` | :class:`datetime.datetime` | :data:`None`
        Object after which all guilds must be.
    """

    def __init__(
        self,
        bot: Client,
        limit: int | None,
        before: Snowflake | datetime.datetime | None = None,
        after: Snowflake | datetime.datetime | None = None,
        with_counts: bool = True,
    ) -> None:
        if isinstance(before, datetime.datetime):
            before = Object(id=time_snowflake(before, high=False))
        if isinstance(after, datetime.datetime):
            after = Object(id=time_snowflake(after, high=True))

        self.bot = bot
        self.limit = limit
        self.before = before
        self.after = after
        self.with_counts = with_counts

        self._filter: Callable[[GuildPayload], bool] | None = None

        self.state = self.bot._connection
        self.get_guilds = self.bot.http.get_guilds
        self.guilds: asyncio.Queue[Guild] = asyncio.Queue()

        if self.before:
            self.reverse = True
            self._retrieve_guilds = self._retrieve_guilds_before_strategy
            if after:
                self._filter = lambda m: int(m["id"]) > after.id
        else:
            self.reverse = False
            self._retrieve_guilds = self._retrieve_guilds_after_strategy

    async def next(self) -> Guild:
        if self.guilds.empty():
            await self.fill_guilds()

        try:
            return self.guilds.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems from None

    def _get_retrieve(self) -> bool:
        limit = self.limit
        if limit is None or limit > 200:
            retrieve = 200
        else:
            retrieve = limit
        self.retrieve = retrieve
        return retrieve > 0

    def create_guild(self, data: GuildPayload) -> Guild:
        from .guild import Guild

        return Guild(state=self.state, data=data)

    async def fill_guilds(self) -> None:
        if self._get_retrieve():
            data = await self._retrieve_guilds(self.retrieve)
            if len(data) < 200:
                self.limit = 0

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            for element in data:
                await self.guilds.put(self.create_guild(element))

    async def _retrieve_guilds(self, retrieve: int) -> list[GuildPayload]:
        """Retrieve guilds and update next parameters."""
        raise NotImplementedError

    async def _retrieve_guilds_before_strategy(self, retrieve: int) -> list[GuildPayload]:
        """Retrieve guilds using before parameter."""
        before = self.before.id if self.before else None
        data: list[GuildPayload] = await self.get_guilds(
            retrieve, before=before, with_counts=self.with_counts
        )
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.before = Object(id=int(data[0]["id"]))
        return data

    async def _retrieve_guilds_after_strategy(self, retrieve: int) -> list[GuildPayload]:
        """Retrieve guilds using after parameter."""
        after = self.after.id if self.after else None
        data: list[GuildPayload] = await self.get_guilds(
            retrieve, after=after, with_counts=self.with_counts
        )
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.after = Object(id=int(data[-1]["id"]))
        return data


class MemberIterator(_AsyncIterator["Member"]):
    def __init__(
        self,
        guild: Guild,
        limit: int | None = 1000,
        after: Snowflake | datetime.datetime | None = None,
    ) -> None:
        if isinstance(after, datetime.datetime):
            after = Object(id=time_snowflake(after, high=True))

        self.guild = guild
        self.limit = limit
        self.after = after or OLDEST_OBJECT

        self.state = self.guild._state
        self.get_members = self.state.http.get_members
        self.members = asyncio.Queue()

    async def next(self) -> Member:
        if self.members.empty():
            await self.fill_members()

        try:
            return self.members.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems from None

    def _get_retrieve(self) -> bool:
        limit = self.limit
        if limit is None or limit > 1000:
            retrieve = 1000
        else:
            retrieve = limit
        self.retrieve = retrieve
        return retrieve > 0

    async def fill_members(self) -> None:
        if self._get_retrieve():
            after = self.after.id if self.after else None
            data = await self.get_members(self.guild.id, self.retrieve, after)
            if not data:
                # no data, terminate
                return

            if self.limit is not None:
                self.limit -= self.retrieve
            if len(data) < 1000:
                self.limit = 0  # terminate loop

            self.after = Object(id=int(data[-1]["user"]["id"]))

            for element in reversed(data):
                await self.members.put(self.create_member(element))

    def create_member(self, data: MemberWithUserPayload) -> Member:
        from .member import Member

        return Member(data=data, guild=self.guild, state=self.state)


# The endpoint for this paginates like audit logs,
# i.e. descending when no parameter or `before` is given,
# and ascending when `after` is given.
class EntitlementIterator(_AsyncIterator["Entitlement"]):
    def __init__(
        self,
        application_id: int,
        *,
        state: ConnectionState,
        limit: int | None,
        user_id: int | None = None,
        guild_id: int | None = None,
        sku_ids: list[int] | None = None,
        before: Snowflake | datetime.datetime | None = None,
        after: Snowflake | datetime.datetime | None = None,
        exclude_ended: bool = False,
        exclude_deleted: bool = True,
        oldest_first: bool = False,
    ) -> None:
        if isinstance(before, datetime.datetime):
            before = Object(id=time_snowflake(before, high=False))
        if isinstance(after, datetime.datetime):
            after = Object(id=time_snowflake(after, high=True))

        self.application_id: int = application_id
        self.limit: int | None = limit
        self.before: Snowflake | None = before
        self.after: Snowflake = after or OLDEST_OBJECT
        self.user_id: int | None = user_id
        self.guild_id: int | None = guild_id
        self.sku_ids: list[int] | None = sku_ids
        self.exclude_ended: bool = exclude_ended
        self.exclude_deleted: bool = exclude_deleted

        self.state: ConnectionState = state
        self.request = state.http.get_entitlements

        self.entitlements: asyncio.Queue[Entitlement] = asyncio.Queue()

        self._filter: Callable[[EntitlementPayload], bool] | None = None
        if oldest_first:
            self._strategy = self._after_strategy
            if before:
                self._filter = lambda m: int(m["id"]) < before.id
        else:
            self._strategy = self._before_strategy
            if self.after and self.after != OLDEST_OBJECT:
                self._filter = lambda m: int(m["id"]) > self.after.id

    async def next(self) -> Entitlement:
        if self.entitlements.empty():
            await self._fill()

        try:
            return self.entitlements.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems from None

    def _get_retrieve(self) -> bool:
        limit = self.limit
        if limit is None or limit > 100:
            retrieve = 100
        else:
            retrieve = limit
        self.retrieve: int = retrieve
        return retrieve > 0

    async def _fill(self) -> None:
        if not self._get_retrieve():
            return

        data = await self._strategy(self.retrieve)
        if len(data) < 100:
            self.limit = 0  # terminate loop

        if self._filter:
            data = filter(self._filter, data)

        for entitlement in data:
            await self.entitlements.put(Entitlement(data=entitlement, state=self.state))

    async def _before_strategy(self, retrieve: int) -> list[EntitlementPayload]:
        before = self.before.id if self.before else None
        data = await self.request(
            self.application_id,
            before=before,
            limit=retrieve,
            user_id=self.user_id,
            guild_id=self.guild_id,
            exclude_ended=self.exclude_ended,
            exclude_deleted=self.exclude_deleted,
        )

        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.before = Object(id=int(data[-1]["id"]))
        return data

    async def _after_strategy(self, retrieve: int) -> list[EntitlementPayload]:
        after = self.after.id
        data = await self.request(
            self.application_id,
            after=after,
            limit=retrieve,
            user_id=self.user_id,
            guild_id=self.guild_id,
            exclude_ended=self.exclude_ended,
            exclude_deleted=self.exclude_deleted,
        )

        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            # endpoint returns items in ascending order when `after` is used
            self.after = Object(id=int(data[-1]["id"]))
        return data
