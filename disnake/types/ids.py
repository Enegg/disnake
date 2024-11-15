from typing import Any, Callable, Coroutine, List, NewType, Protocol, Union, overload

from typing_extensions import Concatenate, Never, ParamSpec, TypeAlias, TypeVar

__all__ = (
    "ApplicationCommandId",
    "ApplicationId",
    "AttachmentId",
    "CategoryId",
    "ChannelId",
    "EmojiId",
    "GuildId",
    "InteractionId",
    "MemberId",
    "MessageId",
    "PrivateChannelId",
    "RoleId",
    "StickerId",
    "ThreadId",
    "UserId",
    "WebhookId",
    "overload_fetch",
    "overload_get",
    "overload_get_seq",
)

ApplicationCommandId = NewType("ApplicationCommandId", int)
ApplicationId = NewType("ApplicationId", int)
AttachmentId = NewType("AttachmentId", int)
ChannelId = NewType("ChannelId", int)
CategoryId: TypeAlias = ChannelId
EmojiId = NewType("EmojiId", int)
GuildId = NewType("GuildId", int)
InteractionId = NewType("InteractionId", int)
MessageId = NewType("MessageId", int)
PrivateChannelId = NewType("PrivateChannelId", int)
RoleId = NewType("RoleId", int)
StickerId = NewType("StickerId", int)
ThreadId = NewType("ThreadId", int)
UserId = NewType("UserId", int)
MemberId: TypeAlias = UserId
WebhookId = NewType("WebhookId", int)

ChannelOrThreadId = Union[ChannelId, ThreadId]
ObjectId = Union[
    ApplicationCommandId,
    ApplicationId,
    AttachmentId,
    ChannelId,
    EmojiId,
    GuildId,
    InteractionId,
    MessageId,
    PrivateChannelId,
    RoleId,
    StickerId,
    ThreadId,
    UserId,
    WebhookId,
]

IdT = TypeVar("IdT", bound=ObjectId, infer_variance=True)
RetT = TypeVar("RetT", infer_variance=True)
RetInvalidT = TypeVar("RetInvalidT", infer_variance=True)
P = ParamSpec("P")


class AcceptsID(Protocol[IdT, P, RetT, RetInvalidT]):
    @overload
    def __call__(self, id: IdT, /, *args: P.args, **kwargs: P.kwargs) -> RetT: ...
    @overload
    def __call__(self, id: ObjectId, /, *args: P.args, **kwargs: P.kwargs) -> RetInvalidT: ...
    @overload
    def __call__(self, id: int, /, *args: P.args, **kwargs: P.kwargs) -> RetT: ...


def overload_fetch(
    func: Callable[Concatenate[Any, IdT, P], Coroutine[Any, Any, RetT]], /
) -> AcceptsID[IdT, P, Coroutine[Any, Any, RetT], Coroutine[Any, Any, Never]]:
    return func  # type: ignore


def overload_get(
    func: Callable[Concatenate[Any, IdT, P], RetT], /
) -> AcceptsID[IdT, P, RetT, None]:
    return func  # type: ignore


def overload_get_seq(
    func: Callable[Concatenate[Any, IdT, P], List[RetT]], /
) -> AcceptsID[IdT, P, List[RetT], List[Never]]:
    return func  # type: ignore
