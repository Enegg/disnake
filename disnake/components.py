# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

from .enums import ButtonStyle, ChannelType, ComponentType, TextInputStyle, try_enum
from .partial_emoji import PartialEmoji, _EmojiTag
from .utils import MISSING, assert_never, get_slots

if TYPE_CHECKING:
    from typing_extensions import Self

    from .emoji import Emoji
    from .types.components import (
        ActionRowPayload,
        BaseSelectMenuPayload,
        ButtonPayload,
        ChannelSelectMenuPayload,
        ComponentPayload,
        ConstrainedComponentPayloadT,
        MentionableSelectMenuPayload,
        MessageComponentPayload,
        ModalComponentPayload,
        RoleSelectMenuPayload,
        SelectOptionPayload,
        StringSelectMenuPayload,
        TextInputPayload,
        UrlButtonPayload,
        UserSelectMenuPayload,
    )

    ComponentishT = TypeVar("ComponentishT", bound="Componentish", infer_variance=True)
else:
    ComponentishT = TypeVar("ComponentishT", bound="Componentish")

__all__ = (
    "Component",
    "ActionRow",
    "Button",
    "UrlButton",
    "BaseSelectMenu",
    "StringSelectMenu",
    "SelectMenu",
    "UserSelectMenu",
    "RoleSelectMenu",
    "MentionableSelectMenu",
    "ChannelSelectMenu",
    "SelectOption",
    "TextInput",
)

C = TypeVar("C", bound="Component")

AnyButton = Union["Button", "UrlButton"]
AnySelectMenu = Union[
    "StringSelectMenu",
    "UserSelectMenu",
    "RoleSelectMenu",
    "MentionableSelectMenu",
    "ChannelSelectMenu",
]
MessageComponent = Union[AnyButton, AnySelectMenu]

if TYPE_CHECKING:  # TODO: remove when we add modal select support
    from typing_extensions import TypeAlias

# ModalComponent = Union["TextInput", "AnySelectMenu"]
ModalComponent: TypeAlias = "TextInput"


@runtime_checkable
class Componentish(Protocol[ConstrainedComponentPayloadT]):
    @property
    def type(self) -> ComponentType:
        ...

    def to_dict(self) -> ConstrainedComponentPayloadT:
        ...


@runtime_checkable
class ActionRowish(Protocol[ComponentishT]):
    @property
    def type(self) -> ComponentType:
        ...

    @property
    def children(self) -> Sequence[ComponentishT]:
        ...

    @overload
    def to_dict(self: ActionRowish[Componentish[MessageComponentPayload]]) -> ActionRowPayload[MessageComponentPayload]:
        ...

    @overload
    def to_dict(self: ActionRowish[Componentish[ModalComponentPayload]]) -> ActionRowPayload[ModalComponentPayload]:
        ...


NestedComponents = Union[
    ActionRowish[Componentish[ConstrainedComponentPayloadT]],
    Componentish[ConstrainedComponentPayloadT],
    Sequence[
        Union[
            ActionRowish[Componentish[ConstrainedComponentPayloadT]],
            Sequence[Componentish[ConstrainedComponentPayloadT]],
        ]
    ]
]
NestedMessageComponents = NestedComponents[MessageComponentPayload]
NestedModalComponents = NestedComponents[ModalComponentPayload]


class Component:
    """Represents a Discord Bot UI Kit Component.

    Currently, the only components supported by Discord are:

    - :class:`ActionRow`
    - :class:`Button`
    - subtypes of :class:`BaseSelectMenu` (:class:`ChannelSelectMenu`, :class:`MentionableSelectMenu`, :class:`RoleSelectMenu`, :class:`StringSelectMenu`, :class:`UserSelectMenu`)
    - :class:`TextInput`

    .. versionadded:: 2.0

    Attributes
    ----------
    type: :class:`ComponentType`
        The type of component.
    """

    __slots__: Tuple[str, ...] = ()

    __repr_info__: ClassVar[Tuple[str, ...]]
    type: ClassVar[ComponentType]

    def __repr__(self) -> str:
        attrs = " ".join(f"{key}={getattr(self, key)!r}" for key in self.__repr_info__)
        return f"<{self.__class__.__name__} {attrs}>"

    @classmethod
    def _raw_construct(cls, **kwargs) -> Self:
        self = cls.__new__(cls)
        for slot in get_slots(cls):
            try:
                value = kwargs[slot]
            except KeyError:
                pass
            else:
                setattr(self, slot, value)
        return self

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> Self:
        """Construct a Component from its raw payload as received from discord."""
        raise NotImplementedError


class ActionRow(Component, Generic[ConstrainedComponentPayloadT]):
    """Represents an action row.

    This is a containter component that holds up to 5 children components.

    This inherits from :class:`Component`.

    .. versionadded:: 2.0

    Attributes
    ----------
    type: :class:`ComponentType`
        The type of component.
    children: List[Componentish[ConstrainedComponentPayloadT]]
        The children components that this holds, if any.
    """

    __slots__: Tuple[str, ...] = ("children",)

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__
    type: ClassVar = ComponentType.action_row

    def __init__(self, children: List[Componentish[ConstrainedComponentPayloadT]]) -> None:
        self.children = children

    def to_dict(self) -> ActionRowPayload[ConstrainedComponentPayloadT]:
        return {
            "type": self.type.value,
            "components": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_payload(cls, payload: ActionRowPayload[ConstrainedComponentPayloadT]) -> Self:
        children = [
            _component_factory(d) for d in payload.get("components", ())
        ]
        return cls(children)


class UrlButton(Component):
    """Represents a url button from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.0

    Attributes
    ----------
    url: :class:`str`
        The URL this button sends you to.
    disabled: :class:`bool`
        Whether the button is disabled or not.
    label: Optional[:class:`str`]
        The label of the button, if any.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji of the button, if available.
    """

    __slots__: Tuple[str, ...] = (
        "url",
        "disabled",
        "label",
        "emoji",
    )
    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__
    type: ClassVar = ComponentType.button

    def __init__(
        self,
        url: str,
        disabled: bool = False,
        label: Optional[str] = None,
        emoji: Optional[PartialEmoji] = None
    ) -> None:
        self.url = url
        self.disabled = disabled
        self.label = label
        self.emoji = emoji

    @property
    def custom_id(self) -> None:
        return None

    def to_dict(self) -> UrlButtonPayload:
        payload: UrlButtonPayload = {
            "type": ComponentType.button.value,
            "style": ButtonStyle.url.value,
            "url": self.url,
            "disabled": self.disabled,
        }

        if self.label:
            payload["label"] = self.label

        if self.emoji:
            payload["emoji"] = self.emoji.to_dict()

        return payload

    @classmethod
    def from_payload(cls, payload: UrlButtonPayload) -> Self:
        try:
            emoji = PartialEmoji.from_dict(payload["emoji"])
        except KeyError:
            emoji = None

        return cls(
            url=payload["url"],
            disabled=payload.get("disabled", False),
            label=payload.get("label"),
            emoji=emoji
        )


class Button(Component):
    """Represents a button from the Discord Bot UI Kit.

    This inherits from :class:`Component`.

    .. versionadded:: 2.0

    Attributes
    ----------
    style: :class:`.ButtonStyle`
        The style of the button.
    custom_id: Optional[:class:`str`]
        The ID of the button that gets received during an interaction.
        If this button is for a URL, it does not have a custom ID.
    url: Optional[:class:`str`]
        The URL this button sends you to.
    disabled: :class:`bool`
        Whether the button is disabled or not.
    label: Optional[:class:`str`]
        The label of the button, if any.
    emoji: Optional[:class:`PartialEmoji`]
        The emoji of the button, if available.
    """

    __slots__: Tuple[str, ...] = (
        "style",
        "custom_id",
        "disabled",
        "label",
        "emoji",
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__
    type: ClassVar = ComponentType.button

    def __init__(
        self,
        style: ButtonStyle,
        custom_id: str,
        disabled: bool = False,
        label: Optional[str] = None,
        emoji: Optional[PartialEmoji] = None
    ) -> None:
        self.style = style
        self.custom_id = custom_id
        self.disabled = disabled
        self.label = label
        self.emoji = emoji

    def to_dict(self) -> ButtonPayload:
        payload: ButtonPayload = {
            "type": 2,
            "style": self.style.value,
            "custom_id": self.custom_id,
            "disabled": self.disabled,
        }

        if self.label:
            payload["label"] = self.label

        if self.emoji:
            payload["emoji"] = self.emoji.to_dict()

        return payload

    @classmethod
    def from_payload(cls, payload: ButtonPayload) -> Self:
        try:
            emoji = PartialEmoji.from_dict(payload["emoji"])
        except KeyError:
            emoji = None

        return cls(
            style=try_enum(ButtonStyle, payload["style"]),
            custom_id=payload["custom_id"],
            disabled=payload.get("disabled", False),
            label=payload.get("label"),
            emoji=emoji
        )


class BaseSelectMenu(Component):
    """Represents an abstract select menu from the Discord Bot UI Kit.

    A select menu is functionally the same as a dropdown, however
    on mobile it renders a bit differently.

    The currently supported select menus are:

    - :class:`~disnake.StringSelectMenu`
    - :class:`~disnake.UserSelectMenu`
    - :class:`~disnake.RoleSelectMenu`
    - :class:`~disnake.MentionableSelectMenu`
    - :class:`~disnake.ChannelSelectMenu`

    .. versionadded:: 2.7

    Attributes
    ----------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    options: List[:class:`SelectOption`]
        A list of options that can be selected in this select menu.
    disabled: :class:`bool`
        Whether the select menu is disabled or not.
    """

    __slots__: Tuple[str, ...] = (
        "custom_id",
        "placeholder",
        "min_values",
        "max_values",
        "disabled",
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__

    def __init__(
        self,
        custom_id: str,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False
    ) -> None:
        self.custom_id = custom_id
        self.placeholder = placeholder
        self.min_values = min_values
        self.max_values = max_values
        self.disabled = disabled

    def to_dict(self) -> BaseSelectMenuPayload:
        payload: BaseSelectMenuPayload = {
            "type": self.type.value,
            "custom_id": self.custom_id,
            "min_values": self.min_values,
            "max_values": self.max_values,
            "disabled": self.disabled,
        }

        if self.placeholder:
            payload["placeholder"] = self.placeholder

        return payload

    @classmethod
    def from_payload(cls, payload: BaseSelectMenuPayload) -> Self:
        return cls(
            custom_id=payload["custom_id"],
            placeholder=payload.get("placeholder"),
            min_values=payload.get("min_values", 1),
            max_values=payload.get("max_values", 1),
            disabled=payload.get("disabled", False)
        )


class StringSelectMenu(BaseSelectMenu):
    """Represents a string select menu from the Discord Bot UI Kit.

    .. versionadded:: 2.0

    .. versionchanged:: 2.7
        Renamed from ``SelectMenu`` to ``StringSelectMenu``.

    Attributes
    ----------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    disabled: :class:`bool`
        Whether the select menu is disabled or not.
    options: List[:class:`SelectOption`]
        A list of options that can be selected in this select menu.
    """

    __slots__: Tuple[str, ...] = ("options",)

    __repr_info__: ClassVar[Tuple[str, ...]] = BaseSelectMenu.__repr_info__ + __slots__
    type: ClassVar = ComponentType.string_select

    def __init__(
        self,
        custom_id: str,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        options: List[SelectOption] = MISSING
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled
        )
        self.options = [] if options is MISSING else options

    def to_dict(self) -> StringSelectMenuPayload:
        payload = cast("StringSelectMenuPayload", super().to_dict())
        payload["type"] = ComponentType.string_select.value
        payload["options"] = [op.to_dict() for op in self.options]
        return payload

    @classmethod
    def from_payload(cls, payload: StringSelectMenuPayload) -> Self:
        self = super().from_payload(payload)
        self.options = [
            SelectOption.from_dict(option) for option in payload.get("options", [])
        ]
        return self


SelectMenu = StringSelectMenu  # backwards compatibility


class UserSelectMenu(BaseSelectMenu):
    """Represents a user select menu from the Discord Bot UI Kit.

    .. versionadded:: 2.7

    Attributes
    ----------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    disabled: :class:`bool`
        Whether the select menu is disabled or not.
    """

    __slots__: Tuple[str, ...] = ()
    type: ClassVar = ComponentType.user_select

    if TYPE_CHECKING:

        def to_dict(self) -> UserSelectMenuPayload:
            return cast("UserSelectMenuPayload", super().to_dict())


class RoleSelectMenu(BaseSelectMenu):
    """Represents a role select menu from the Discord Bot UI Kit.

    .. versionadded:: 2.7

    Attributes
    ----------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    disabled: :class:`bool`
        Whether the select menu is disabled or not.
    """

    __slots__: Tuple[str, ...] = ()
    type: ClassVar = ComponentType.role_select

    if TYPE_CHECKING:

        def to_dict(self) -> RoleSelectMenuPayload:
            return cast("RoleSelectMenuPayload", super().to_dict())


class MentionableSelectMenu(BaseSelectMenu):
    """Represents a mentionable (user/member/role) select menu from the Discord Bot UI Kit.

    .. versionadded:: 2.7

    Attributes
    ----------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    disabled: :class:`bool`
        Whether the select menu is disabled or not.
    """

    __slots__: Tuple[str, ...] = ()
    type: ClassVar = ComponentType.mentionable_select

    if TYPE_CHECKING:

        def to_dict(self) -> MentionableSelectMenuPayload:
            return cast("MentionableSelectMenuPayload", super().to_dict())


class ChannelSelectMenu(BaseSelectMenu):
    """Represents a channel select menu from the Discord Bot UI Kit.

    .. versionadded:: 2.7

    Attributes
    ----------
    custom_id: Optional[:class:`str`]
        The ID of the select menu that gets received during an interaction.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is selected, if any.
    min_values: :class:`int`
        The minimum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    max_values: :class:`int`
        The maximum number of items that must be chosen for this select menu.
        Defaults to 1 and must be between 1 and 25.
    disabled: :class:`bool`
        Whether the select menu is disabled or not.
    channel_types: Optional[List[:class:`ChannelType`]]
        A list of channel types that can be selected in this select menu.
        If ``None``, channels of all types may be selected.
    """

    __slots__: Tuple[str, ...] = ("channel_types",)

    __repr_info__: ClassVar[Tuple[str, ...]] = BaseSelectMenu.__repr_info__ + __slots__
    type: ClassVar = ComponentType.channel_select

    def __init__(
        self,
        custom_id: str,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        channel_types: Optional[List[ChannelType]] = None
        ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled
        )
        self.channel_types = channel_types

    def to_dict(self) -> ChannelSelectMenuPayload:
        payload = cast("ChannelSelectMenuPayload", super().to_dict())
        payload["type"] = ComponentType.channel_select.value
        if self.channel_types:
            payload["channel_types"] = [t.value for t in self.channel_types]
        return payload

    @classmethod
    def from_payload(cls, payload: ChannelSelectMenuPayload) -> Self:
        # on the API side, an empty list is (currently) equivalent to no value
        channel_types = payload.get("channel_types")
        self = super().from_payload(payload)
        self.channel_types = (
            [try_enum(ChannelType, t) for t in channel_types] if channel_types else None
        )
        return self


class SelectOption:
    """Represents a string select menu's option.

    .. versionadded:: 2.0

    Attributes
    ----------
    label: :class:`str`
        The label of the option. This is displayed to users.
        Can only be up to 100 characters.
    value: :class:`str`
        The value of the option. This is not displayed to users.
        If not provided when constructed then it defaults to the
        label. Can only be up to 100 characters.
    description: Optional[:class:`str`]
        An additional description of the option, if any.
        Can only be up to 100 characters.
    emoji: Optional[Union[:class:`str`, :class:`Emoji`, :class:`PartialEmoji`]]
        The emoji of the option, if available.
    default: :class:`bool`
        Whether this option is selected by default.
    """

    __slots__: Tuple[str, ...] = (
        "label",
        "value",
        "description",
        "emoji",
        "default",
    )

    def __init__(
        self,
        *,
        label: str,
        value: str = MISSING,
        description: Optional[str] = None,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
        default: bool = False,
    ) -> None:
        self.label = label
        self.value = label if value is MISSING else value
        self.description = description

        if emoji is not None:
            if isinstance(emoji, str):
                emoji = PartialEmoji.from_str(emoji)
            elif isinstance(emoji, _EmojiTag):
                emoji = emoji._to_partial()
            else:
                raise TypeError(
                    f"expected emoji to be str, Emoji, or PartialEmoji not {emoji.__class__}"
                )

        self.emoji = emoji
        self.default = default

    def __repr__(self) -> str:
        return (
            f"<SelectOption label={self.label!r} value={self.value!r} description={self.description!r} "
            f"emoji={self.emoji!r} default={self.default!r}>"
        )

    def __str__(self) -> str:
        if self.emoji:
            base = f"{self.emoji} {self.label}"
        else:
            base = self.label

        if self.description:
            return f"{base}\n{self.description}"
        return base

    @classmethod
    def from_dict(cls, data: SelectOptionPayload) -> Self:
        try:
            emoji = PartialEmoji.from_dict(data["emoji"])
        except KeyError:
            emoji = None

        return cls(
            label=data["label"],
            value=data["value"],
            description=data.get("description"),
            emoji=emoji,
            default=data.get("default", False),
        )

    def to_dict(self) -> SelectOptionPayload:
        payload: SelectOptionPayload = {
            "label": self.label,
            "value": self.value,
            "default": self.default,
        }

        if self.emoji:
            payload["emoji"] = self.emoji.to_dict()

        if self.description:
            payload["description"] = self.description

        return payload


class TextInput(Component):
    """Represents a text input from the Discord Bot UI Kit.

    .. versionadded:: 2.4

    Attributes
    ----------
    custom_id: :class:`str`
        The ID of the text input that gets received during an interaction.
    style: :class:`TextInputStyle`
        The style of the text input.
    label: :class:`str`
        The label of the text input.
    min_length: Optional[:class:`int`]
        The minimum length of the text input.
    max_length: Optional[:class:`int`]
        The maximum length of the text input.
    required: :class:`bool`
        Whether the text input is required. Defaults to ``True``.
    value: Optional[:class:`str`]
        The pre-filled text of the text input.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is entered.
    """

    __slots__: Tuple[str, ...] = (
        "custom_id",
        "style",
        "label",
        "min_length",
        "max_length",
        "required",
        "value",
        "placeholder",
    )

    __repr_info__: ClassVar[Tuple[str, ...]] = __slots__
    type: ClassVar = ComponentType.text_input

    def __init__(
        self,
        *,
        custom_id: str,
        label: str,
        style: TextInputStyle = TextInputStyle.short,
        placeholder: Optional[str] = None,
        value: Optional[str] = None,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
        ) -> None:

        self.custom_id: str = custom_id
        self.style: TextInputStyle = style
        self.label: str = label
        self.placeholder: Optional[str] = placeholder
        self.value: Optional[str] = value
        self.required: bool = required
        self.min_length: Optional[int] = min_length
        self.max_length: Optional[int] = max_length

    def to_dict(self) -> TextInputPayload:
        payload: TextInputPayload = {
            "type": self.type.value,
            "style": self.style.value,
            "label": self.label,
            "custom_id": self.custom_id,
            "required": self.required,
        }

        if self.placeholder is not None:
            payload["placeholder"] = self.placeholder

        if self.value is not None:
            payload["value"] = self.value

        if self.min_length is not None:
            payload["min_length"] = self.min_length

        if self.max_length is not None:
            payload["max_length"] = self.max_length

        return payload

    @classmethod
    def from_payload(cls, payload: TextInputPayload) -> Self:
        style = payload.get("style", TextInputStyle.short.value)
        return cls(
            custom_id=payload["custom_id"],
            style=try_enum(TextInputStyle, style),
            label=payload["label"],
            placeholder=payload.get("placeholder"),
            value=payload.get("value"),
            required=payload.get("required", True),
            min_length=payload.get("min_length"),
            max_length=payload.get("max_length")
        )


def _component_factory(data: ComponentPayload, *, type: Type[C] = Component) -> C:
    # NOTE: due to speed, this method does not use the ComponentType enum
    #       as this runs every single time a component is received from the api
    # NOTE: The type param is purely for type-checking, it has no implications on runtime behavior.
    component_type = data["type"]
    if component_type == 1:
        return ActionRow.from_payload(data)  # type: ignore
    elif component_type == 2:
        if "url" in data:
            return UrlButton.from_payload(data)  # type: ignore
        return Button.from_payload(data)  # type: ignore
    elif component_type == 3:
        return StringSelectMenu.from_payload(data)  # type: ignore
    elif component_type == 4:
        return TextInput.from_payload(data)  # type: ignore
    elif component_type == 5:
        return UserSelectMenu.from_payload(data)  # type: ignore
    elif component_type == 6:
        return RoleSelectMenu.from_payload(data)  # type: ignore
    elif component_type == 7:
        return MentionableSelectMenu.from_payload(data)  # type: ignore
    elif component_type == 8:
        return ChannelSelectMenu.from_payload(data)  # type: ignore
    else:
        assert_never(component_type)
        as_enum = try_enum(ComponentType, component_type)
        return Component._raw_construct(type=as_enum)  # type: ignore
