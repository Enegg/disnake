# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING, Generic, Literal, overload

from .types.ids import (
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
)

if TYPE_CHECKING:
    from typing_extensions import Self, TypeVar

    IdT = TypeVar(
        "IdT",
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
        int,
        infer_variance=True,
        default=int,
    )

__all__ = (
    "EqualityComparable",
    "Hashable",
)


class EqualityComparable(Generic[IdT]):
    __slots__ = ()

    id: IdT

    @overload
    def __eq__(self, other: "Self") -> bool: ...
    @overload
    def __eq__(self, other: object) -> Literal[False]: ...
    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    @overload
    def __ne__(self, other: "Self") -> bool: ...
    @overload
    def __ne__(self, other: object) -> Literal[True]: ...
    def __ne__(self, other: object) -> bool:
        return not isinstance(other, self.__class__) or self.id != other.id


class Hashable(EqualityComparable[IdT]):
    __slots__ = ()

    def __hash__(self) -> int:
        return self.id >> 22
