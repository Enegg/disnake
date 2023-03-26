# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generator,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

from ..components import ActionRow as ActionRowComponent
from ..components import (
    ActionRowish,
    Componentish,
    NestedComponents,
)
from ..components import Button as ButtonComponent
from ..components import ChannelSelectMenu as ChannelSelectComponent
from ..components import MentionableSelectMenu as MentionableSelectComponent
from ..components import RoleSelectMenu as RoleSelectComponent
from ..components import StringSelectMenu as StringSelectComponent
from ..components import UrlButton as UrlButtonComponent
from ..components import UserSelectMenu as UserSelectComponent
from ..enums import ButtonStyle, ChannelType, ComponentType, TextInputStyle
from ..utils import MISSING, SequenceProxy, assert_never
from .button import Button, UrlButton
from .item import WrappedComponent, WrappedComponentishT
from .select import ChannelSelect, MentionableSelect, RoleSelect, StringSelect, UserSelect
from .select.string import SelectOptionInput, V
from .text_input import TextInput

if TYPE_CHECKING:
    from typing_extensions import Self

    from ..emoji import Emoji
    from ..message import Message
    from ..partial_emoji import PartialEmoji
    from ..types.components import ActionRowPayload, ConstrainedComponentPayloadT

__all__ = (
    "ActionRow",
    "MessageComponent",
    "ModalComponent",
)

AnyButton = Union[Button[V], UrlButton[V]]
AnySelect = Union[
    "ChannelSelect[V]",
    "MentionableSelect[V]",
    "RoleSelect[V]",
    "StringSelect[V]",
    "UserSelect[V]",
]

MessageComponent = Union[AnyButton[Any], AnySelect[Any]]
ModalComponent = TextInput  # Union[TextInput, "AnySelect[Any]"]
StrictComponentT = TypeVar("StrictComponentT", MessageComponent, ModalComponent)
UIComponentT = TypeVar("UIComponentT", bound=WrappedComponent)
# this is cursed
ButtonCompatibleActionRowT = TypeVar(
    "ButtonCompatibleActionRowT",
    bound="Union[ActionRow[MessageComponent], ActionRow[WrappedComponent]]",
)
SelectCompatibleActionRowT = TypeVar(
    "SelectCompatibleActionRowT",
    bound="Union[ActionRow[MessageComponent], ActionRow[WrappedComponent]]",  # to add: ActionRow[ModalComponent]
)
TextInputCompatibleActionRowT = TypeVar(
    "TextInputCompatibleActionRowT",
    bound="Union[ActionRow[ModalComponent], ActionRow[WrappedComponent]]",
)


class ActionRow(Generic[WrappedComponentishT]):
    """Represents a UI action row. Useful for lower level component manipulation.

    .. container:: operations

        .. describe:: x[i]

            Returns the component at position ``i``. Also supports slices.

            .. versionadded:: 2.6

        .. describe:: len(x)

            Returns the number of components in this row.

            .. versionadded:: 2.6

        .. describe:: iter(x)

            Returns an iterator for the components in this row.

            .. versionadded:: 2.6

    To handle interactions created by components sent in action rows or entirely independently,
    event listeners must be used. For buttons and selects, the related events are
    :func:`disnake.on_button_click` and :func:`disnake.on_dropdown`, respectively. Alternatively,
    :func:`disnake.on_message_interaction` can be used for either. For modals, the related event is
    :func:`disnake.on_modal_submit`.

    .. versionadded:: 2.4

    .. versionchanged:: 2.6
        Requires and provides stricter typing for contained components.

    Parameters
    ----------
    *components: :class:`WrappedComponent`
        The components of this action row.

        .. versionchanged:: 2.6
            Components can now be either valid in the context of a message, or in the
            context of a modal. Combining components from both contexts is not supported.
    """

    type: ClassVar[Literal[ComponentType.action_row]] = ComponentType.action_row

    # When unspecified and called empty, default to an ActionRow that takes any kind of component.

    @overload
    def __init__(self: ActionRow[WrappedComponent]) -> None:
        ...

    # Explicit definitions are needed to make
    # "ActionRow(StringSelect(), TextInput())" and
    # "ActionRow(StringSelect(), Button())"
    # differentiate themselves properly.

    @overload
    def __init__(self: ActionRow[MessageComponent], *components: MessageComponent) -> None:
        ...

    @overload
    def __init__(self: ActionRow[ModalComponent], *components: ModalComponent) -> None:
        ...

    # Allow use of "ActionRow[StrictUIComponent]" externally.

    @overload
    def __init__(self: ActionRow[StrictComponentT], *components: StrictComponentT) -> None:
        ...

    def __init__(self, *components: WrappedComponentishT) -> None:
        self._children: List[WrappedComponentishT] = []

        for component in components:
            if not isinstance(component, Componentish):
                raise TypeError(
                    f"components should be of type WrappedComponent, got {type(component).__name__}."
                )
            self.append_item(component)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} children={self._children!r}>"

    def __len__(self) -> int:
        return len(self._children)

    @property
    def children(self) -> Sequence[WrappedComponentishT]:
        """Sequence[:class:`WrappedComponent`]:
        A read-only copy of the UI components stored in this action row. To add/remove
        components to/from the action row, use its methods to directly modify it.

        .. versionchanged:: 2.6
            Returns an immutable sequence instead of a list.
        """
        return SequenceProxy(self._children)

    @property
    def width(self) -> int:
        return sum(child.width for child in self._children)

    def append_item(self, item: WrappedComponentishT) -> Self:
        """Append a component to the action row. The component's type must match that
        of the action row.

        This function returns the class instance to allow for fluent-style chaining.

        Parameters
        ----------
        item: :class:`WrappedComponent`
            The component to append to the action row.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.insert_item(len(self), item)
        return self

    def insert_item(self, index: int, item: WrappedComponentishT) -> Self:
        """Insert a component to the action row at a given index. The component's
        type must match that of the action row.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.6

        Parameters
        ----------
        index: :class:`int`
            The index at which to insert the component into the action row.
        item: :class:`WrappedComponent`
            The component to insert into the action row.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        if self.width + item.width > 5:
            raise ValueError("Too many components in this row, can not append a new one.")

        self._children.insert(index, item)
        return self

    def add_button(
        self: ButtonCompatibleActionRowT,
        index: Optional[int] = None,
        *,
        style: ButtonStyle = ButtonStyle.secondary,
        label: Optional[str] = None,
        disabled: bool = False,
        custom_id: Optional[str] = None,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
    ) -> ButtonCompatibleActionRowT:
        """Add a button to the action row.

        To append a pre-existing :class:`~disnake.ui.Button` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionchanged:: 2.6
            Now allows for inserting at a given index. The default behaviour of
            appending is preserved.

        Parameters
        ----------
        index: :class:`int`
            The index at which to insert the button into the action row. If not provided,
            this method defaults to appending the button to the action row.
        style: :class:`.ButtonStyle`
            The style of the button.
        custom_id: Optional[:class:`str`]
            The ID of the button that gets received during an interaction.
        label: Optional[:class:`str`]
            The label of the button, if any.
        disabled: :class:`bool`
            Whether the button is disabled or not.
        emoji: Optional[Union[:class:`.PartialEmoji`, :class:`.Emoji`, :class:`str`]]
            The emoji of the button, if available.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.insert_item(
            len(self) if index is None else index,
            Button(
                style=style,
                label=label,
                disabled=disabled,
                custom_id=custom_id,
                emoji=emoji,
            ),
        )
        return self

    def add_url_button(
        self: ButtonCompatibleActionRowT,
        index: Optional[int] = None,
        *,
        url: str,
        label: Optional[str] = None,
        disabled: bool = False,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
    ) -> ButtonCompatibleActionRowT:
        """Add a button to the action row.

        To append a pre-existing :class:`~disnake.ui.Button` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionchanged:: 2.6
            Now allows for inserting at a given index. The default behaviour of
            appending is preserved.

        Parameters
        ----------
        index: :class:`int`
            The index at which to insert the button into the action row. If not provided,
            this method defaults to appending the button to the action row.
        url: :class:`str`
            The URL this button sends you to.
        label: Optional[:class:`str`]
            The label of the button, if any.
        disabled: :class:`bool`
            Whether the button is disabled or not.
        emoji: Optional[Union[:class:`.PartialEmoji`, :class:`.Emoji`, :class:`str`]]
            The emoji of the button, if available.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.insert_item(
            len(self) if index is None else index,
            UrlButton(
                url=url,
                label=label,
                disabled=disabled,
                emoji=emoji,
            ),
        )
        return self

    def add_string_select(
        self: SelectCompatibleActionRowT,
        *,
        custom_id: str = MISSING,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        options: SelectOptionInput = MISSING,
        disabled: bool = False,
    ) -> SelectCompatibleActionRowT:
        """Add a string select menu to the action row. Can only be used if the action
        row holds message components.

        To append a pre-existing :class:`~disnake.ui.StringSelect` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionchanged:: 2.7
            Renamed from ``add_select`` to ``add_string_select``.

        Parameters
        ----------
        custom_id: :class:`str`
            The ID of the select menu that gets received during an interaction.
            If not given then one is generated for you.
        placeholder: Optional[:class:`str`]
            The placeholder text that is shown if nothing is selected, if any.
        min_values: :class:`int`
            The minimum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        max_values: :class:`int`
            The maximum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        options: Union[List[:class:`disnake.SelectOption`], List[:class:`str`], Dict[:class:`str`, :class:`str`]]
            A list of options that can be selected in this menu. Use explicit :class:`.SelectOption`\\s
            for fine-grained control over the options. Alternatively, a list of strings will be treated
            as a list of labels, and a dict will be treated as a mapping of labels to values.
        disabled: :class:`bool`
            Whether the select is disabled or not.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.append_item(
            StringSelect(
                custom_id=custom_id,
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                options=options,
                disabled=disabled,
            ),
        )
        return self

    add_select = add_string_select  # backwards compatibility

    def add_user_select(
        self: SelectCompatibleActionRowT,
        *,
        custom_id: str = MISSING,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> SelectCompatibleActionRowT:
        """Add a user select menu to the action row. Can only be used if the action
        row holds message components.

        To append a pre-existing :class:`~disnake.ui.UserSelect` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.7

        Parameters
        ----------
        custom_id: :class:`str`
            The ID of the select menu that gets received during an interaction.
            If not given then one is generated for you.
        placeholder: Optional[:class:`str`]
            The placeholder text that is shown if nothing is selected, if any.
        min_values: :class:`int`
            The minimum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        max_values: :class:`int`
            The maximum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        disabled: :class:`bool`
            Whether the select is disabled or not.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.append_item(
            UserSelect(
                custom_id=custom_id,
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
            ),
        )
        return self

    def add_role_select(
        self: SelectCompatibleActionRowT,
        *,
        custom_id: str = MISSING,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> SelectCompatibleActionRowT:
        """Add a role select menu to the action row. Can only be used if the action
        row holds message components.

        To append a pre-existing :class:`~disnake.ui.RoleSelect` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.7

        Parameters
        ----------
        custom_id: :class:`str`
            The ID of the select menu that gets received during an interaction.
            If not given then one is generated for you.
        placeholder: Optional[:class:`str`]
            The placeholder text that is shown if nothing is selected, if any.
        min_values: :class:`int`
            The minimum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        max_values: :class:`int`
            The maximum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        disabled: :class:`bool`
            Whether the select is disabled or not.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.append_item(
            RoleSelect(
                custom_id=custom_id,
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
            ),
        )
        return self

    def add_mentionable_select(
        self: SelectCompatibleActionRowT,
        *,
        custom_id: str = MISSING,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> SelectCompatibleActionRowT:
        """Add a mentionable (user/member/role) select menu to the action row. Can only be used if the action
        row holds message components.

        To append a pre-existing :class:`~disnake.ui.MentionableSelect` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.7

        Parameters
        ----------
        custom_id: :class:`str`
            The ID of the select menu that gets received during an interaction.
            If not given then one is generated for you.
        placeholder: Optional[:class:`str`]
            The placeholder text that is shown if nothing is selected, if any.
        min_values: :class:`int`
            The minimum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        max_values: :class:`int`
            The maximum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        disabled: :class:`bool`
            Whether the select is disabled or not.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.append_item(
            MentionableSelect(
                custom_id=custom_id,
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
            ),
        )
        return self

    def add_channel_select(
        self: SelectCompatibleActionRowT,
        *,
        custom_id: str = MISSING,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        channel_types: Optional[List[ChannelType]] = None,
    ) -> SelectCompatibleActionRowT:
        """Add a channel select menu to the action row. Can only be used if the action
        row holds message components.

        To append a pre-existing :class:`~disnake.ui.ChannelSelect` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.7

        Parameters
        ----------
        custom_id: :class:`str`
            The ID of the select menu that gets received during an interaction.
            If not given then one is generated for you.
        placeholder: Optional[:class:`str`]
            The placeholder text that is shown if nothing is selected, if any.
        min_values: :class:`int`
            The minimum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        max_values: :class:`int`
            The maximum number of items that must be chosen for this select menu.
            Defaults to 1 and must be between 1 and 25.
        disabled: :class:`bool`
            Whether the select is disabled or not.
        channel_types: Optional[List[:class:`.ChannelType`]]
            The list of channel types that can be selected in this select menu.
            Defaults to all types (i.e. ``None``).

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.append_item(
            ChannelSelect(
                custom_id=custom_id,
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                channel_types=channel_types,
            ),
        )
        return self

    def add_text_input(
        self: TextInputCompatibleActionRowT,
        *,
        label: str,
        custom_id: str,
        style: TextInputStyle = TextInputStyle.short,
        placeholder: Optional[str] = None,
        value: Optional[str] = None,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
    ) -> TextInputCompatibleActionRowT:
        """Add a text input to the action row. Can only be used if the action
        row holds modal components.

        To append a pre-existing :class:`~disnake.ui.TextInput` use the
        :meth:`append_item` method instead.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.4

        Parameters
        ----------
        style: :class:`.TextInputStyle`
            The style of the text input.
        label: :class:`str`
            The label of the text input.
        custom_id: :class:`str`
            The ID of the text input that gets received during an interaction.
        placeholder: Optional[:class:`str`]
            The placeholder text that is shown if nothing is entered.
        value: Optional[:class:`str`]
            The pre-filled value of the text input.
        required: :class:`bool`
            Whether the text input is required. Defaults to ``True``.
        min_length: Optional[:class:`int`]
            The minimum length of the text input.
        max_length: Optional[:class:`int`]
            The maximum length of the text input.

        Raises
        ------
        ValueError
            The width of the action row exceeds 5.
        """
        self.append_item(
            TextInput(
                label=label,
                custom_id=custom_id,
                style=style,
                placeholder=placeholder,
                value=value,
                required=required,
                min_length=min_length,
                max_length=max_length,
            ),
        )

        return self

    def clear_items(self) -> Self:
        """Remove all components from the action row.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.6
        """
        self._children.clear()
        return self

    def remove_item(self, item: WrappedComponentishT) -> Self:
        """Remove a component from the action row.

        This function returns the class instance to allow for fluent-style chaining.

        .. versionadded:: 2.6

        Parameters
        ----------
        item: :class:`WrappedComponent`
            The component to remove from the action row.

        Raises
        ------
        ValueError
            The component could not be found on the action row.
        """
        self._children.remove(item)
        return self

    def pop(self, index: int) -> WrappedComponentishT:
        """Pop the component at the provided index from the action row.

        .. versionadded:: 2.6

        Parameters
        ----------
        index: :class:`int`
            The index at which to pop the component.

        Raises
        ------
        IndexError
            There is no component at the provided index.
        """
        self.remove_item(component := self[index])
        return component

    @property
    def _underlying(self: ActionRow[StrictComponentT]) -> ActionRowComponent[StrictComponentT]:
        return ActionRowComponent(
            children=[comp._underlying for comp in self._children],
        )

    def to_dict(self) -> ActionRowPayload[WrappedComponentishT]:
        return self._underlying.to_dict()

    def __delitem__(self, index: Union[int, slice]) -> None:
        del self._children[index]

    @overload
    def __getitem__(self, index: int) -> WrappedComponentishT:
        ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[WrappedComponentishT]:
        ...

    def __getitem__(self, index: Union[int, slice]) -> Union[WrappedComponentishT, Sequence[WrappedComponentishT]]:
        return self._children[index]

    def __iter__(self) -> Iterator[WrappedComponentishT]:
        return iter(self._children)

    @classmethod
    def with_modal_components(cls) -> ActionRow[ModalComponent]:
        """Create an empty action row meant to store components compatible with
        :class:`disnake.ui.Modal`. Saves the need to import type specifiers to
        typehint empty action rows.

        .. versionadded:: 2.6

        Returns
        -------
        :class:`ActionRow`:
            The newly created empty action row, intended for modal components.
        """
        return ActionRow[ModalComponent]()

    @classmethod
    def with_message_components(cls) -> ActionRow[MessageComponent]:
        """Create an empty action row meant to store components compatible with
        :class:`disnake.Message`. Saves the need to import type specifiers to
        typehint empty action rows.

        .. versionadded:: 2.6

        Returns
        -------
        :class:`ActionRow`:
            The newly created empty action row, intended for message components.
        """
        return ActionRow[MessageComponent]()

    @classmethod
    def rows_from_message(
        cls: Type[ActionRow[MessageComponent]],
        message: Message,
        *,
        strict: bool = True,
    ) -> List[ActionRow[MessageComponent]]:
        """Create a list of up to 5 action rows from the components on an existing message.

        This will abide by existing component format on the message, including component
        ordering and rows. Components will be transformed to UI kit components, such that
        they can be easily modified and re-sent as action rows.

        .. versionadded:: 2.6

        Parameters
        ----------
        message: :class:`disnake.Message`
            The message from which to extract the components.
        strict: :class:`bool`
            Whether or not to raise an exception if an unknown component type is encountered.

        Raises
        ------
        TypeError
            Strict-mode is enabled and an unknown component type is encountered.

        Returns
        -------
        List[:class:`MessageActionRow`]:
            The action rows parsed from the components on the message.
        """
        rows: List[ActionRow[MessageComponent]] = []
        for row in message.components:
            rows.append(current_row := cls())
            for component in row.children:
                if isinstance(component, ButtonComponent):
                    current_row.append_item(Button.from_component(component))
                elif isinstance(component, UrlButtonComponent):
                    current_row.append_item(UrlButton.from_component(component))
                elif isinstance(component, StringSelectComponent):
                    current_row.append_item(StringSelect.from_component(component))
                elif isinstance(component, UserSelectComponent):
                    current_row.append_item(UserSelect.from_component(component))
                elif isinstance(component, RoleSelectComponent):
                    current_row.append_item(RoleSelect.from_component(component))
                elif isinstance(component, MentionableSelectComponent):
                    current_row.append_item(MentionableSelect.from_component(component))
                elif isinstance(component, ChannelSelectComponent):
                    current_row.append_item(ChannelSelect.from_component(component))
                else:
                    assert_never(component)
                    if strict:
                        raise TypeError(f"Encountered unknown component type: {component.type!r}.")

        return rows

    @staticmethod
    def walk_components(
        action_rows: Sequence[ActionRow[WrappedComponentishT]],
    ) -> Generator[Tuple[ActionRow[WrappedComponentishT], WrappedComponentishT], None, None]:
        """Iterate over the components in a sequence of action rows, yielding each
        individual component together with the action row of which it is a child.

        .. versionadded:: 2.6

        Parameters
        ----------
        action_rows: Sequence[:class:`ActionRow`]
            The sequence of action rows over which to iterate.

        Yields
        ------
        Tuple[:class:`ActionRow`, :class:`WrappedComponent`]
            A tuple containing an action row and a component of that action row.
        """
        for row in tuple(action_rows):
            for component in tuple(row.children):
                yield row, component


def components_to_rows(components: NestedComponents[ConstrainedComponentPayloadT]) -> List[ActionRow[ConstrainedComponentPayloadT]]:
    if not isinstance(components, Sequence):
        components = [components]

    action_rows: List[ActionRowish[ConstrainedComponentPayloadT]] = []
    auto_row = ActionRow[ConstrainedComponentPayloadT]()

    for component in components:
        if isinstance(component, WrappedComponent):
            try:
                auto_row.append_item(component)
            except ValueError:
                action_rows.append(auto_row)
                auto_row = ActionRow(component)
        else:
            if auto_row.width > 0:
                action_rows.append(auto_row)
                auto_row = ActionRow()

            if isinstance(component, ActionRow):
                action_rows.append(component)

            elif isinstance(component, Sequence):
                action_rows.append(ActionRow(*component))

            else:
                raise TypeError(
                    "`components` must be a `WrappedComponent` or `ActionRow`, "
                    "a sequence/list of `WrappedComponent`s or `ActionRow`s, "
                    "or a nested sequence/list of `WrappedComponent`s"
                )

    if auto_row.width > 0:
        action_rows.append(auto_row)

    return action_rows


def components_to_dict(components: NestedComponents[ConstrainedComponentPayloadT]) -> List[ActionRowPayload[ConstrainedComponentPayloadT]]:
    return [row.to_dict() for row in components_to_rows(components)]
