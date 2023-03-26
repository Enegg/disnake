# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Generic, List, Literal, TypeAlias, Union

from typing_extensions import NotRequired, TypedDict, TypeVar

from .channel import ChannelType
from .emoji import PartialEmoji

ComponentType = Literal[1, 2, 3, 4, 5, 6, 7, 8]
ButtonStyle = Literal[1, 2, 3, 4]
UrlButtonStyle = Literal[5]
TextInputStyle = Literal[1, 2]


MessageComponentPayload = Union["AnyButtonPayload", "AnySelectMenuPayload"]
NestedMessageComponentPayload = Union["ActionRowPayload[MessageComponentPayload]", MessageComponentPayload]
ModalComponentPayload: TypeAlias = "TextInputPayload"
NestedModalComponentPayload = Union["ActionRowPayload[ModalComponentPayload]", ModalComponentPayload]
ComponentPayload = Union[NestedMessageComponentPayload, NestedModalComponentPayload]
ConstrainedComponentPayloadT = TypeVar("ConstrainedComponentPayloadT", MessageComponentPayload, ModalComponentPayload, infer_variance=True)


class ActionRowPayload(TypedDict, Generic[ConstrainedComponentPayloadT]):
    type: Literal[1]
    components: List[ConstrainedComponentPayloadT]


class ButtonPayload(TypedDict):
    type: Literal[2]
    style: ButtonStyle
    label: NotRequired[str]
    emoji: NotRequired[PartialEmoji]
    custom_id: str
    disabled: NotRequired[bool]


class UrlButtonPayload(TypedDict):
    type: Literal[2]
    style: UrlButtonStyle
    label: NotRequired[str]
    emoji: NotRequired[PartialEmoji]
    url: str
    disabled: NotRequired[bool]


class SelectOptionPayload(TypedDict):
    label: str
    value: str
    description: NotRequired[str]
    emoji: NotRequired[PartialEmoji]
    default: NotRequired[bool]


class _SelectMenuPayload(TypedDict):
    custom_id: str
    placeholder: NotRequired[str]
    min_values: NotRequired[int]
    max_values: NotRequired[int]
    disabled: NotRequired[bool]


class BaseSelectMenuPayload(_SelectMenuPayload):
    type: Literal[3, 5, 6, 7, 8]


class StringSelectMenuPayload(_SelectMenuPayload):
    type: Literal[3]
    options: List[SelectOptionPayload]


class UserSelectMenuPayload(_SelectMenuPayload):
    type: Literal[5]


class RoleSelectMenuPayload(_SelectMenuPayload):
    type: Literal[6]


class MentionableSelectMenuPayload(_SelectMenuPayload):
    type: Literal[7]


class ChannelSelectMenuPayload(_SelectMenuPayload):
    type: Literal[8]
    channel_types: NotRequired[List[ChannelType]]


AnyButtonPayload = Union[
    ButtonPayload,
    UrlButtonPayload
]
AnySelectMenuPayload = Union[
    StringSelectMenuPayload,
    UserSelectMenuPayload,
    RoleSelectMenuPayload,
    MentionableSelectMenuPayload,
    ChannelSelectMenuPayload,
]


class ModalPayload(TypedDict):
    title: str
    custom_id: str
    components: List[ActionRowPayload[ModalComponentPayload]]


class TextInputPayload(TypedDict):
    type: Literal[4]
    custom_id: str
    style: TextInputStyle
    label: str
    min_length: NotRequired[int]
    max_length: NotRequired[int]
    required: NotRequired[bool]
    value: NotRequired[str]
    placeholder: NotRequired[str]
