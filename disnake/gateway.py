# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import sys
import threading
import time
import traceback
import zlib
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Literal,
    NamedTuple,
    Protocol,
    TypeVar,
)

import aiohttp

from . import utils
from .activity import BaseActivity
from .errors import ConnectionClosed

if TYPE_CHECKING:
    from typing_extensions import Self

    from .client import Client
    from .state import ConnectionState
    from .types.gateway import (
        GatewayPayload,
        HeartbeatCommand,
        IdentifyCommand,
        PresenceUpdateCommand,
        RequestMembersCommand,
        ResumeCommand,
        VoiceHeartbeatData,
        VoiceStateCommand,
    )

    T = TypeVar("T")

    class DispatchFunc(Protocol):
        def __call__(self, event: str, *args: Any) -> None: ...

    class GatewayErrorFunc(Protocol):
        async def __call__(
            self, event: str, data: Any, shard_id: int | None, exc: Exception, /
        ) -> None: ...

    class CallHooksFunc(Protocol):
        async def __call__(self, key: str, *args: Any, **kwargs: Any) -> None: ...

    class HookFunc(Protocol):
        async def __call__(self, *args: Any) -> None: ...


__all__ = ("DiscordWebSocket", "KeepAliveHandler", "ReconnectWebSocket")

_VOICE_VERSION = 8

_log = logging.getLogger(__name__)


class ReconnectWebSocket(Exception):
    """Signals to safely reconnect the websocket."""

    def __init__(self, shard_id: int | None, *, resume: bool = True) -> None:
        self.shard_id = shard_id
        self.resume = resume
        self.op = "RESUME" if resume else "IDENTIFY"


class WebSocketClosure(Exception):
    """An exception to make up for the fact that aiohttp doesn't signal closure."""


class EventListener(NamedTuple):
    predicate: Callable[[dict[str, Any]], bool]
    event: str
    result: Callable[[dict[str, Any]], Any] | None
    future: asyncio.Future[Any]


class GatewayRatelimiter:
    # The default is 110 to give room for at least 10 heartbeats per minute
    def __init__(self, count: int = 110, per: float = 60.0) -> None:
        # maximum number of commands per interval (`self.per`)
        self.max: int = count
        # interval length in seconds
        self.per: float = per

        # remaining commands within current window
        self.remaining: int = count
        # start epoch time of current window
        self.window: float = 0.0

        self.lock: asyncio.Lock = asyncio.Lock()
        self.shard_id: int | None = None

    def is_ratelimited(self) -> bool:
        current = time.time()
        if current > self.window + self.per:
            return False
        return self.remaining == 0

    def get_delay(self) -> float:
        current = time.time()

        # if current window elapsed, reset to max
        if current > self.window + self.per:
            self.remaining = self.max

        # if no command used yet, start new window
        if self.remaining == self.max:
            self.window = current

        # if no commands remain in current window, return delay
        if self.remaining == 0:
            return self.per - (current - self.window)

        # subtract one command in current window, return no delay
        self.remaining -= 1
        return 0.0

    async def block(self) -> None:
        async with self.lock:
            delta = self.get_delay()
            if delta:
                _log.warning(
                    "WebSocket in shard ID %s is ratelimited, waiting %.2f seconds",
                    self.shard_id,
                    delta,
                )
                await asyncio.sleep(delta)


class KeepAliveHandler(threading.Thread):
    def __init__(
        self,
        *args: Any,
        ws: HeartbeatWebSocket,
        interval: float,
        shard_id: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.ws: HeartbeatWebSocket = ws
        self._main_thread_id: int = ws.thread_id
        self.interval: float = interval
        self.daemon: bool = True
        self.shard_id: int | None = shard_id
        self.msg = "Keeping shard ID %s websocket alive with sequence %s."
        self.block_msg = "Shard ID %s heartbeat blocked for more than %s seconds."
        self.behind_msg = "Can't keep up, shard ID %s websocket is %.1fs behind."
        self._stop_ev: threading.Event = threading.Event()
        self._last_ack: float = time.perf_counter()
        self._last_send: float = time.perf_counter()
        self._last_recv: float = time.perf_counter()
        self.latency: float = float("inf")
        self.heartbeat_timeout: float = ws._max_heartbeat_timeout

    def run(self) -> None:
        while not self._stop_ev.wait(self.interval):
            if self._last_recv + self.heartbeat_timeout < time.perf_counter():
                _log.warning(
                    "Shard ID %s has stopped responding to the gateway. Closing and restarting.",
                    self.shard_id,
                )
                coro = self.ws.close(4000)
                f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)

                try:
                    f.result()
                except Exception:
                    _log.exception("An error occurred while stopping the gateway. Ignoring.")
                except BaseException:
                    # Since the thread is at the end of its lifecycle here anyway,
                    # simply suppress any BaseException that might occur while closing the ws.
                    pass
                self.stop()
                return

            data = self.get_payload()
            _log.debug(self.msg, self.shard_id, data["d"])
            coro = self.ws.send_heartbeat(data)
            f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)
            try:
                # block until sending is complete
                total = 0
                while True:
                    try:
                        f.result(10)
                        break
                    except concurrent.futures.TimeoutError:
                        total += 10
                        try:
                            frame = sys._current_frames()[self._main_thread_id]
                        except KeyError:
                            msg = self.block_msg
                            _log.warning(msg, self.shard_id, total)
                        else:
                            stack = "".join(traceback.format_stack(frame))
                            msg = f"{self.block_msg}\nLoop thread traceback (most recent call last):\n%s"
                            _log.warning(msg, self.shard_id, total, stack)

            except Exception:
                self.stop()
            else:
                self._last_send = time.perf_counter()

    def get_payload(self) -> HeartbeatCommand:
        return {"op": self.ws.HEARTBEAT, "d": self.ws.get_heartbeat_data()}

    def stop(self) -> None:
        self._stop_ev.set()

    def tick(self) -> None:
        self._last_recv = time.perf_counter()

    def ack(self) -> None:
        ack_time = time.perf_counter()
        self._last_ack = ack_time
        self.latency = ack_time - self._last_send
        if self.latency > 10:
            _log.warning(self.behind_msg, self.shard_id, self.latency)


class DiscordClientWebSocketResponse(aiohttp.ClientWebSocketResponse):
    async def close(self, *, code: int = 4000, message: bytes = b"") -> bool:
        return await super().close(code=code, message=message)


class HeartbeatWebSocket(Protocol):
    # assigning any value to make pyright infer this as a classvar
    HEARTBEAT: Final[Literal[1, 3]] = 1

    thread_id: int
    loop: asyncio.AbstractEventLoop
    _max_heartbeat_timeout: float

    async def close(self, code: int) -> None: ...

    async def send_heartbeat(self, data: HeartbeatCommand) -> None: ...

    def get_heartbeat_data(self) -> int | None | VoiceHeartbeatData: ...


class DiscordWebSocket:
    """Implements a WebSocket for Discord's gateway v10.

    Attributes
    ----------
    DISPATCH
        Receive only. Denotes an event to be sent to Discord, such as READY.
    HEARTBEAT
        When received tells Discord to keep the connection alive.
        When sent asks if your connection is currently alive.
    IDENTIFY
        Send only. Starts a new session.
    PRESENCE
        Send only. Updates your presence.
    VOICE_STATE
        Send only. Starts a new connection to a voice guild.
    VOICE_PING
        Send only. Checks ping time to a voice guild, do not use.
    RESUME
        Send only. Resumes an existing connection.
    RECONNECT
        Receive only. Tells the client to reconnect to a new gateway.
    REQUEST_MEMBERS
        Send only. Asks for the full member list of a guild.
    INVALIDATE_SESSION
        Receive only. Tells the client to optionally invalidate the session
        and IDENTIFY again.
    HELLO
        Receive only. Tells the client the heartbeat interval.
    HEARTBEAT_ACK
        Receive only. Confirms receiving of a heartbeat. Not having it implies
        a connection issue.
    GUILD_SYNC
        Send only. Requests a guild sync.
    gateway
        The gateway we are currently connected to.
    token
        The authentication token for discord.
    """

    DISPATCH: Final[Literal[0]] = 0
    HEARTBEAT: Final[Literal[1]] = 1
    IDENTIFY: Final[Literal[2]] = 2
    PRESENCE: Final[Literal[3]] = 3
    VOICE_STATE: Final[Literal[4]] = 4
    VOICE_PING: Final[Literal[5]] = 5
    RESUME: Final[Literal[6]] = 6
    RECONNECT: Final[Literal[7]] = 7
    REQUEST_MEMBERS: Final[Literal[8]] = 8
    INVALIDATE_SESSION: Final[Literal[9]] = 9
    HELLO: Final[Literal[10]] = 10
    HEARTBEAT_ACK: Final[Literal[11]] = 11
    GUILD_SYNC: Final[Literal[12]] = 12

    def __init__(
        self, socket: aiohttp.ClientWebSocketResponse, *, loop: asyncio.AbstractEventLoop
    ) -> None:
        self.socket: aiohttp.ClientWebSocketResponse = socket
        self.loop: asyncio.AbstractEventLoop = loop

        # an empty dispatcher to prevent crashes
        self._dispatch: DispatchFunc = lambda event, *args: None
        self._dispatch_gateway_error: GatewayErrorFunc | None = None
        # generic event listeners
        self._dispatch_listeners: list[EventListener] = []
        # the keep alive
        self._keep_alive: KeepAliveHandler | None = None
        self.thread_id: int = threading.get_ident()

        # ws related stuff
        self.session_id: str | None = None
        self.sequence: int | None = None
        # this may or may not include url parameters, we only need the host part of the url anyway
        self.resume_gateway: str | None = None
        self._zlib: zlib._Decompress = zlib.decompressobj()
        self._buffer: bytearray = bytearray()
        self._close_code: int | None = None
        self._rate_limiter: GatewayRatelimiter = GatewayRatelimiter()

        # set in `from_client`
        self.token: str
        self._connection: ConnectionState
        self._discord_parsers: dict[str, Callable[[dict[str, Any]], Any]]
        self.gateway: str
        self.call_hooks: CallHooksFunc
        self._initial_identify: bool
        self.shard_id: int | None
        self.shard_count: int | None
        self._max_heartbeat_timeout: float

    @property
    def open(self) -> bool:
        return not self.socket.closed

    def is_ratelimited(self) -> bool:
        return self._rate_limiter.is_ratelimited()

    def debug_log_receive(self, data: str, /) -> None:
        self._dispatch("socket_raw_receive", data)

    def log_receive(self, data: str, /) -> None:
        pass

    @classmethod
    async def from_client(
        cls,
        client: Client,
        *,
        initial: bool = False,
        gateway: str | None = None,
        shard_id: int | None = None,
        session: str | None = None,
        sequence: int | None = None,
        resume: bool = False,
    ) -> Self:
        """Creates a main websocket for Discord from a :class:`Client`.

        This is for internal use only.
        """
        params = client.gateway_params
        if gateway:
            gateway = client.http._format_gateway_url(
                gateway,
                encoding=params.encoding,
                zlib=params.zlib,
            )
        else:
            gateway = await client.http.get_gateway(encoding=params.encoding, zlib=params.zlib)

        socket = await client.http.ws_connect(gateway)
        ws = cls(socket, loop=client.loop)

        # dynamically add attributes needed
        ws.token = client.http.token  # pyright: ignore[reportAttributeAccessIssue]
        ws._connection = client._connection
        ws._discord_parsers = client._connection.parsers
        ws._dispatch = client.dispatch
        ws.gateway = gateway
        ws.resume_gateway = gateway
        ws.call_hooks = client._connection.call_hooks
        ws._initial_identify = initial
        ws.shard_id = shard_id
        ws._rate_limiter.shard_id = shard_id
        ws.shard_count = client._connection.shard_count
        ws.session_id = session
        ws.sequence = sequence
        ws._max_heartbeat_timeout = client._connection.heartbeat_timeout

        if client._enable_debug_events:
            ws.send = ws.debug_send
            ws.log_receive = ws.debug_log_receive

        if client._enable_gateway_error_handler:
            ws._dispatch_gateway_error = client._dispatch_gateway_error

        _log.debug("Created websocket connected to %s", gateway)

        # poll event for OP Hello
        await ws.poll_event()

        if not resume:
            await ws.identify()
            return ws

        await ws.resume()
        return ws

    def wait_for(
        self,
        event: str,
        predicate: Callable[[dict[str, Any]], bool],
        result: Callable[[dict[str, Any]], T] | None = None,
    ) -> asyncio.Future[T]:
        r"""Waits for a DISPATCH'd event that meets the predicate.

        Parameters
        ----------
        event: :class:`str`
            The event name in all upper case to wait for.
        predicate: :class:`~collections.abc.Callable`\[[:class:`dict`\[:class:`str`, :data:`~typing.Any`]], :class:`bool`]
            A function that takes a data parameter to check for event
            properties. The data parameter is the 'd' key in the JSON message.
        result: :class:`~collections.abc.Callable`\[[:class:`dict`\[:class:`str`, :data:`~typing.Any`]], T] | :data:`None`
            A function that takes the same data parameter and executes to send
            the result to the future. If :data:`None`, returns the data.

        Returns
        -------
        asyncio.Future
            A future to wait for.
        """
        future = self.loop.create_future()
        entry = EventListener(event=event, predicate=predicate, result=result, future=future)
        self._dispatch_listeners.append(entry)
        return future

    async def identify(self) -> None:
        """Sends the IDENTIFY packet."""
        state = self._connection

        payload: IdentifyCommand = {
            "op": self.IDENTIFY,
            "d": {
                "token": self.token,
                "properties": {
                    "os": sys.platform,
                    "browser": "disnake",
                    "device": "disnake",
                },
                "large_threshold": 250,
                "intents": state._intents.value,
            },
        }

        if self.shard_id is not None and self.shard_count is not None:
            payload["d"]["shard"] = (self.shard_id, self.shard_count)

        if state._activity is not None or state._status is not None:
            payload["d"]["presence"] = {
                "status": state._status or "online",
                "activities": (state._activity,) if state._activity else (),
                "since": 0,
                "afk": False,
            }

        await self.call_hooks("before_identify", self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)
        _log.info("Shard ID %s has sent the IDENTIFY payload.", self.shard_id)

    async def resume(self) -> None:
        """Sends the RESUME packet."""
        # these should never be None if resuming, but instead of asserting
        # we just send those values and handle the INVALIDATE_SESSION
        seq: int = self.sequence  # pyright: ignore[reportAssignmentType]
        session_id: str = self.session_id  # pyright: ignore[reportAssignmentType]

        payload: ResumeCommand = {
            "op": self.RESUME,
            "d": {"seq": seq, "session_id": session_id, "token": self.token},
        }

        await self.send_as_json(payload)
        _log.info("Shard ID %s has sent the RESUME payload.", self.shard_id)

    async def received_message(self, raw_msg: str | bytes, /) -> None:
        if isinstance(raw_msg, bytes):
            self._buffer.extend(raw_msg)

            if len(raw_msg) < 4 or raw_msg[-4:] != b"\x00\x00\xff\xff":
                return
            raw_msg = self._zlib.decompress(self._buffer)
            raw_msg = raw_msg.decode("utf-8")
            self._buffer = bytearray()

        self.log_receive(raw_msg)
        msg: GatewayPayload = utils._from_json(raw_msg)
        del raw_msg  # no need to keep this in memory

        _log.debug("For Shard ID %s: WebSocket Event: %s", self.shard_id, msg)
        event = msg.get("t")
        if event:
            self._dispatch("socket_event_type", event)

        op = msg.get("op")
        data: Any = msg.get("d")
        seq = msg.get("s")
        if seq is not None:
            self.sequence = seq

        if self._keep_alive:
            self._keep_alive.tick()

        if op != self.DISPATCH:
            if op == self.RECONNECT:
                # "reconnect" can only be handled by the Client
                # so we terminate our connection and raise an
                # internal exception signalling to reconnect.
                _log.debug("Received RECONNECT opcode.")
                await self.close()
                raise ReconnectWebSocket(self.shard_id)

            if op == self.HEARTBEAT_ACK:
                if self._keep_alive:
                    self._keep_alive.ack()
                return

            if op == self.HEARTBEAT:
                if self._keep_alive:
                    beat = self._keep_alive.get_payload()
                    await self.send_as_json(beat)
                return

            if op == self.HELLO:
                interval: float = data["heartbeat_interval"] / 1000.0
                self._keep_alive = KeepAliveHandler(
                    ws=self, interval=interval, shard_id=self.shard_id
                )
                # send a heartbeat immediately
                await self.send_as_json(self._keep_alive.get_payload())
                self._keep_alive.start()
                return

            if op == self.INVALIDATE_SESSION:
                if data is True:
                    await self.close()
                    raise ReconnectWebSocket(self.shard_id)

                self.sequence = None
                self.session_id = None
                self.resume_gateway = None
                _log.info("Shard ID %s session has been invalidated.", self.shard_id)
                await self.close(code=1000)
                raise ReconnectWebSocket(self.shard_id, resume=False)

            _log.warning("Unknown OP code %s.", op)
            return

        if event == "READY":
            self._trace = trace = data.get("_trace", [])
            self.sequence = seq
            self.session_id = data["session_id"]
            self.resume_gateway = data["resume_gateway_url"]
            # pass back shard ID to ready handler
            data["__shard_id__"] = self.shard_id
            _log.info(
                "Shard ID %s has connected to Gateway: %s (Session ID: %s, Resume URL: %s).",
                self.shard_id,
                ", ".join(trace),
                self.session_id,
                self.resume_gateway,
            )

        elif event == "RESUMED":
            self._trace = trace = data.get("_trace", [])
            # pass back the shard ID to resume handler
            data["__shard_id__"] = self.shard_id
            _log.info(
                "Shard ID %s has successfully RESUMED session %s under trace %s.",
                self.shard_id,
                self.session_id,
                ", ".join(trace),
            )

        try:
            func = self._discord_parsers[event]  # pyright: ignore[reportArgumentType]
        except KeyError:
            _log.debug("Unknown event %s.", event)
        else:
            try:
                func(data)
            except Exception as e:
                if self._dispatch_gateway_error is None:
                    # error handler disabled, raise immediately
                    raise

                if event in {"READY", "RESUMED"}:  # exceptions in these events are fatal
                    raise

                event_name: str = event  # pyright: ignore[reportAssignmentType]  # event can't be None here
                asyncio.create_task(
                    self._dispatch_gateway_error(event_name, data, self.shard_id, e)
                )

        # remove the dispatched listeners
        removed: list[int] = []
        for index, entry in enumerate(self._dispatch_listeners):
            if entry.event != event:
                continue

            future = entry.future
            if future.cancelled():
                removed.append(index)
                continue

            try:
                valid = entry.predicate(data)
            except Exception as exc:
                future.set_exception(exc)
                removed.append(index)
            else:
                if valid:
                    ret = data if entry.result is None else entry.result(data)
                    future.set_result(ret)
                    removed.append(index)

        for index in reversed(removed):
            del self._dispatch_listeners[index]

    @property
    def latency(self) -> float:
        """:class:`float`: Measures latency between a HEARTBEAT and a HEARTBEAT_ACK in seconds."""
        heartbeat = self._keep_alive
        return float("inf") if heartbeat is None else heartbeat.latency

    def _can_handle_close(self) -> bool:
        # bandaid fix for https://github.com/aio-libs/aiohttp/issues/8138
        # tl;dr: on aiohttp >= 3.9.0 and python < 3.11.0, aiohttp returns close code 1000 (OK)
        # on abrupt connection loss, not 1006 (ABNORMAL_CLOSURE) like one would expect, ultimately
        # due to faulty ssl lifecycle handling in cpython.
        # If we end up in a situation where the close code is 1000 but we didn't
        # initiate the closure (i.e. `self._close_code` isn't set), assume this has happened and
        # try to reconnect.
        if self._close_code is None and self.socket.close_code == 1000:
            _log.info(
                "Websocket remote in shard ID %s closed with %s. Assuming the connection dropped.",
                self.shard_id,
                self.socket.close_code,
            )
            return True  # consider this a reconnectable close code

        code = self._close_code or self.socket.close_code
        return code not in (1000, 4004, 4010, 4011, 4012, 4013, 4014)

    async def poll_event(self) -> None:
        """Polls for a DISPATCH event and handles the general gateway loop.

        Raises
        ------
        ConnectionClosed
            The websocket connection was terminated for unhandled reasons.
        """
        try:
            msg = await self.socket.receive(timeout=self._max_heartbeat_timeout)
            if msg.type is aiohttp.WSMsgType.TEXT or msg.type is aiohttp.WSMsgType.BINARY:
                await self.received_message(msg.data)
            elif msg.type is aiohttp.WSMsgType.ERROR:
                _log.debug("Received %s", msg)
                # This is usually just an intermittent gateway hiccup, so try to reconnect again and resume
                raise WebSocketClosure from msg.data
            elif msg.type in (
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.CLOSE,
            ):
                _log.debug("Received %s", msg)
                raise WebSocketClosure
        except (asyncio.TimeoutError, WebSocketClosure) as e:
            # Ensure the keep alive handler is closed
            if self._keep_alive:
                self._keep_alive.stop()
                self._keep_alive = None

            if isinstance(e, asyncio.TimeoutError):
                _log.info("Timed out receiving packet. Attempting a reconnect.")
                raise ReconnectWebSocket(self.shard_id) from None

            code = self._close_code or self.socket.close_code
            if self._can_handle_close():
                _log.info("Websocket closed with %s, attempting a reconnect.", code)
                raise ReconnectWebSocket(self.shard_id) from None
            else:
                _log.info("Websocket closed with %s, cannot reconnect.", code)
                raise ConnectionClosed(self.socket, shard_id=self.shard_id, code=code) from None

    async def debug_send(self, data: str, /) -> None:
        await self._rate_limiter.block()
        self._dispatch("socket_raw_send", data)
        await self.socket.send_str(data)

    async def send(self, data: str, /) -> None:
        await self._rate_limiter.block()
        await self.socket.send_str(data)

    async def send_as_json(self, data: Any) -> None:
        try:
            await self.send(utils._to_json(data))
        except RuntimeError as exc:
            if not self._can_handle_close():
                raise ConnectionClosed(self.socket, shard_id=self.shard_id) from exc

    async def send_heartbeat(self, data: HeartbeatCommand) -> None:
        # This bypasses the rate limit handling code since it has a higher priority
        try:
            await self.socket.send_str(utils._to_json(data))
        except RuntimeError as exc:
            if not self._can_handle_close():
                raise ConnectionClosed(self.socket, shard_id=self.shard_id) from exc

    def get_heartbeat_data(self) -> int | None:
        return self.sequence

    async def change_presence(
        self,
        *,
        activity: BaseActivity | None = None,
        status: str | None = None,
        since: int = 0,
    ) -> None:
        if activity is not None:
            if not isinstance(activity, BaseActivity):
                msg = "activity must derive from BaseActivity."
                raise TypeError(msg)
            activity_data = (activity.to_dict(),)
        else:
            activity_data = ()

        if status == "idle":
            since = int(time.time() * 1000)

        payload: PresenceUpdateCommand = {
            "op": self.PRESENCE,
            "d": {
                "status": status or "online",
                "activities": activity_data,
                "since": since,
                "afk": False,
            },
        }

        sent = utils._to_json(payload)
        _log.debug('Sending "%s" to change status', sent)
        await self.send(sent)

    async def request_chunks(
        self,
        guild_id: int,
        query: str | None = None,
        *,
        limit: int,
        user_ids: list[int] | None = None,
        presences: bool = False,
        nonce: str | None = None,
    ) -> None:
        payload: RequestMembersCommand = {
            "op": self.REQUEST_MEMBERS,
            "d": {"guild_id": guild_id, "presences": presences, "limit": limit},
        }

        if nonce:
            payload["d"]["nonce"] = nonce

        if user_ids:
            payload["d"]["user_ids"] = user_ids

        if query is not None:
            payload["d"]["query"] = query

        await self.send_as_json(payload)

    async def voice_state(
        self,
        guild_id: int,
        channel_id: int | None,
        self_mute: bool = False,
        self_deaf: bool = False,
    ) -> None:
        payload: VoiceStateCommand = {
            "op": self.VOICE_STATE,
            "d": {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "self_mute": self_mute,
                "self_deaf": self_deaf,
            },
        }

        _log.debug("Updating our voice state to %s.", payload)
        await self.send_as_json(payload)

    async def close(self, code: int = 4000) -> None:
        if self._keep_alive:
            self._keep_alive.stop()
            self._keep_alive = None

        self._close_code = code
        await self.socket.close(code=code)
