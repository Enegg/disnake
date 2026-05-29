# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Literal, TypedDict

from typing_extensions import NotRequired

from .appinfo import PartialAppInfo
from .channel import InviteChannel
from .user import PartialUser

InviteType = Literal[0, 1, 2]
InviteTargetType = Literal[1, 2]


class VanityInvite(TypedDict):
    code: str | None
    uses: NotRequired[int]


class _InviteMetadata(TypedDict, total=False):
    uses: int
    max_uses: int
    max_age: int
    temporary: bool
    created_at: str


class Invite(_InviteMetadata):
    code: str
    type: InviteType
    channel: InviteChannel | None
    inviter: NotRequired[PartialUser]
    target_type: NotRequired[InviteTargetType]
    target_user: NotRequired[PartialUser]
    target_application: NotRequired[PartialAppInfo]
    approximate_presence_count: NotRequired[int]
    approximate_member_count: NotRequired[int]
    expires_at: str | None
