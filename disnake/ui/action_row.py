# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Generator, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Generic, NoReturn, TypeVar, cast, overload

from ..components import (
    ActionRow as ActionRowComponent,
    ActionRowChildComponent,
    ActionRowMessageComponent as ActionRowMessageComponentRaw,
    Button as ButtonComponent,
    ChannelSelectMenu as ChannelSelectComponent,
    Checkbox as CheckboxComponent,
    CheckboxGroup as CheckboxGroupComponent,
    Component,
    Container as ContainerComponent,
    FileComponent as FileComponent,
    FileUpload as FileUploadComponent,
    Label as LabelComponent,
    MediaGallery as MediaGalleryComponent,
    MentionableSelectMenu as MentionableSelectComponent,
    RadioGroup as RadioGroupComponent,
    RoleSelectMenu as RoleSelectComponent,
    Section as SectionComponent,
    Separator as SeparatorComponent,
    StringSelectMenu as StringSelectComponent,
    TextDisplay as TextDisplayComponent,
    TextInput as TextInputComponent,
    Thumbnail as ThumbnailComponent,
    UserSelectMenu as UserSelectComponent,
)
from ..enums import ComponentType
from ..utils import SequenceProxy, assert_never, copy_doc
from ._types import (
    ActionRowChildT,
    ActionRowMessageComponent,
    ComponentInput,
    MessageTopLevelComponent,
    NonActionRowChildT,
)
from .button import Button
from .checkbox import Checkbox
from .checkbox_group import CheckboxGroup
from .container import Container
from .file import File
from .file_upload import FileUpload
from .item import UIComponent, WrappedComponent
from .label import Label
from .media_gallery import MediaGallery
from .radio_group import RadioGroup
from .section import Section
from .select import ChannelSelect, MentionableSelect, RoleSelect, StringSelect, UserSelect
from .separator import Separator
from .text_display import TextDisplay
from .text_input import TextInput
from .thumbnail import Thumbnail

if TYPE_CHECKING:
    from typing import TypeAlias

    from typing_extensions import Self

    from ..message import Message
    from ..types.components import (
        ActionRow as ActionRowPayload,
        MessageTopLevelComponent as MessageTopLevelComponentPayload,
    )

__all__ = (
    "ActionRow",
    "Components",
    "MessageUIComponent",
    "walk_components",
    "components_from_message",
)

# FIXME(3.0): legacy
MessageUIComponent: TypeAlias = ActionRowMessageComponent
Components: TypeAlias = ComponentInput[ActionRowChildT, NoReturn]


class ActionRow(UIComponent, Generic[ActionRowChildT]):
    """Represents a UI action row. Useful for lower level component manipulation.

    .. collapse:: operations

        .. describe:: x[i]

            Returns the component at position ``i``. Also supports slices.

            .. versionadded:: 2.6

        .. describe:: len(x)

            Returns the number of components in this row.
            Note that this means empty rows will be considered falsy.

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
    id: :class:`int`
        The numeric identifier for the component. Must be unique within a message.
        This is always present in components received from the API.
        If set to ``0`` (the default) when sending a component, the API will assign
        sequential identifiers to the components in the message.

        .. versionadded:: 2.11
    """

    __repr_attributes__: ClassVar[tuple[str, ...]] = ("_children",)

    def __init__(self, *components: ActionRowChildT, id: int = 0) -> None:
        self._id: int = id
        self._children: list[ActionRowChildT] = list(components)

    def __len__(self) -> int:
        return len(self._children)

    # these are reimplemented here to store the value in a separate attribute,
    # since `ActionRow` lazily constructs `_underlying`, unlike most components
    @property
    @copy_doc(UIComponent.id)
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = value

    @property
    def children(self) -> Sequence[ActionRowChildT]:
        r""":class:`~collections.abc.Sequence`\[:class:`WrappedComponent`]:
        A read-only proxy of the UI components stored in this action row. To add/remove
        components to/from the action row, use its methods to directly modify it.

        .. versionchanged:: 2.6
            Returns an immutable sequence instead of a list.
        """
        return SequenceProxy(self._children)

    @property
    def width(self) -> int:
        return sum(child.width for child in self._children)

    @property
    def _underlying(self) -> ActionRowComponent[ActionRowChildComponent]:
        return ActionRowComponent._raw_construct(
            type=ComponentType.action_row,
            id=self._id,
            children=[comp._underlying for comp in self._children],
        )

    # already provided by base type, reimplemented here for more precise return types
    def to_component_dict(self) -> ActionRowPayload:
        return self._underlying.to_dict()

    @classmethod
    def from_component(cls, action_row: ActionRowComponent) -> Self:
        return cls(
            *cast(
                "list[ActionRowChildT]",
                [_to_ui_component(c) for c in action_row.children],
            ),
            id=action_row.id,
        )

    def __delitem__(self, index: int | slice) -> None:
        del self._children[index]

    @overload
    def __getitem__(self, index: int) -> ActionRowChildT: ...

    @overload
    def __getitem__(self, index: slice[int]) -> Sequence[ActionRowChildT]: ...

    def __getitem__(self, index: int | slice[int]) -> ActionRowChildT | Sequence[ActionRowChildT]:
        return self._children[index]

    def __iter__(self) -> Iterator[ActionRowChildT]:
        return iter(self._children)

    @classmethod
    def rows_from_message(
        cls,
        message: Message,
        *,
        strict: bool = True,
    ) -> list[ActionRow[ActionRowMessageComponent]]:
        r"""Create a list of up to 5 action rows from the components on an existing message.

        This will abide by existing component format on the message, including component
        ordering and rows. Components will be transformed to UI kit components, such that
        they can be easily modified and re-sent as action rows.

        .. note::
            This only supports :class:`ActionRow`\s and associated components, i.e. no v2 components.
            See :func:`.ui.components_from_message` for a function that supports all component types.

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
            Strict-mode is enabled, and an unknown component type is encountered
            or message uses v2 components (see also :attr:`.MessageFlags.is_components_v2`).

        Returns
        -------
        :class:`list`\[:class:`ActionRow`]:
            The action rows parsed from the components on the message.
        """
        rows: list[ActionRow[ActionRowMessageComponent]] = []
        for row in message.components:
            if not isinstance(row, ActionRowComponent):
                # can happen if message uses components v2
                if strict:
                    msg = f"Unexpected top-level component type: {row.type!r}"
                    raise TypeError(msg)
                continue

            rows.append(current_row := ActionRow())
            for component in row.children:
                if item := _message_component_to_item(component):
                    current_row._children.append(item)
                elif strict:
                    msg = f"Encountered unknown component type: {component.type!r}."
                    raise TypeError(msg)

        return rows

    @staticmethod
    def walk_components(
        action_rows: Sequence[ActionRow[ActionRowChildT]],
    ) -> Generator[tuple[ActionRow[ActionRowChildT], ActionRowChildT]]:
        r"""Iterate over the components in a sequence of action rows, yielding each
        individual component together with the action row of which it is a child.

        .. note::
            This only supports :class:`ActionRow`\s, i.e. no v2 components.
            See :func:`.ui.walk_components` for a function that supports all component types.

        .. versionadded:: 2.6

        Parameters
        ----------
        action_rows: :class:`~collections.abc.Sequence`\[:class:`ActionRow`]
            The sequence of action rows over which to iterate.

        Yields
        ------
        :class:`tuple`\[:class:`ActionRow`, :class:`WrappedComponent`]
            A tuple containing an action row and a component of that action row.
        """
        for row in tuple(action_rows):
            for component in tuple(row._children):
                yield row, component


# n.b. the typings with `modal = True` are technically slightly off here,
# however this is only used internally and does not affect public typings
@overload
def normalize_components(
    components: ComponentInput[NoReturn, NonActionRowChildT], /, modal: bool = False
) -> Sequence[NonActionRowChildT]: ...


@overload
def normalize_components(
    components: ComponentInput[ActionRowChildT, NonActionRowChildT], /, modal: bool = False
) -> Sequence[ActionRow[ActionRowChildT] | NonActionRowChildT]: ...


def normalize_components(
    components: ComponentInput[ActionRowChildT, NonActionRowChildT], /, modal: bool = False
) -> Sequence[ActionRow[ActionRowChildT] | NonActionRowChildT]:
    """Wraps consecutive actionrow-compatible components or lists in `ActionRow`s,
    while respecting the width limit. Other components are returned as-is.

    If `modal` is `True`, only wraps `TextInput`s in action rows, and returns other (otherwise
    actionrow-compatible) components as-is.
    """
    if not isinstance(components, Sequence):
        components = [components]

    result: list[ActionRow[ActionRowChildT] | NonActionRowChildT] = []
    auto_row: ActionRow[ActionRowChildT] = ActionRow[ActionRowChildT]()

    wrap_types = TextInput if modal else WrappedComponent

    for component in components:
        if isinstance(component, wrap_types):
            # action row child component, try to insert into current row, otherwise create new row
            try:
                auto_row._children.append(component)
            except ValueError:
                result.append(auto_row)
                auto_row = ActionRow[ActionRowChildT](component)
        else:
            if auto_row.width > 0:
                # if the current action row has items, finish it
                result.append(auto_row)
                auto_row = ActionRow[ActionRowChildT]()

            if isinstance(component, UIComponent):
                # append non-actionrow-child components as-is
                # (action rows, v2 components, or actionrow-child components in modals)
                result.append(component)

            elif isinstance(component, Sequence):
                result.append(ActionRow[ActionRowChildT](*component))

            else:
                assert_never(component)
                msg = (
                    "`components` must be a single component, "
                    "a sequence/list of components (or action rows), "
                    "or a nested sequence/list of action row compatible components"
                )
                raise TypeError(msg)

    if auto_row.width > 0:
        result.append(auto_row)

    return result


def normalize_components_to_dict(
    components: ComponentInput[ActionRowChildT, NonActionRowChildT],
) -> tuple[list[MessageTopLevelComponentPayload], bool]:
    """`normalize_components`, but also turns components into dicts.
    Returns ([d1, d2, ...], has_v2_component).
    """
    component_payloads: list[Mapping[str, Any]] = []
    is_v2 = False

    for c in normalize_components(components):
        component_payloads.append(c.to_component_dict())
        is_v2 |= c.is_v2

    return cast("list[MessageTopLevelComponentPayload]", component_payloads), is_v2


ComponentT = TypeVar("ComponentT", Component, UIComponent)


def _walk_internal(component: ComponentT, seen: set[ComponentT]) -> Iterator[ComponentT]:
    if component in seen:
        # prevent infinite recursion in case anyone manages to nest a component in itself
        return
    # add current component, while also creating a copy to allow reusing a component multiple times,
    # as long as it's not within itself
    seen = {*seen, component}

    yield component

    if isinstance(component, (ActionRowComponent, ActionRow)):
        for item in component.children:
            yield from _walk_internal(item, seen)
    elif isinstance(component, (SectionComponent, Section)):
        yield from _walk_internal(component.accessory, seen)
        for item in component.children:
            yield from _walk_internal(item, seen)  # pyright: ignore[reportArgumentType]  # this is fine, pyright loses the conditional type when iterating
    elif isinstance(component, (ContainerComponent, Container)):
        for item in component.children:
            yield from _walk_internal(item, seen)  # pyright: ignore[reportArgumentType]
    elif isinstance(component, (LabelComponent, Label)):
        yield from _walk_internal(component.component, seen)


def walk_components(components: Sequence[ComponentT]) -> Iterator[ComponentT]:
    r"""Iterate over given components, yielding each individual component,
    including child components where applicable (e.g. for :class:`ActionRow` and :class:`Container`).

    .. versionadded:: 2.11

    Parameters
    ----------
    components: :class:`~collections.abc.Sequence`\[:class:`~disnake.Component`] | :class:`~collections.abc.Sequence`\[:class:`UIComponent`]
        The sequence of components to iterate over. This supports both :class:`disnake.Component`
        objects and :class:`.ui.UIComponent` objects.

    Yields
    ------
    :class:`~disnake.Component` | :class:`UIComponent`
        A component from the given sequence or child component thereof.
    """
    seen: set[ComponentT] = set()
    for item in components:
        yield from _walk_internal(item, seen)


def components_from_message(message: Message) -> list[MessageTopLevelComponent]:
    r"""Create a list of :class:`UIComponent`\s from the components of an existing message.

    This will abide by existing component format on the message, including component
    ordering. Components will be transformed to UI kit components, such that
    they can be easily modified and re-sent.

    .. versionadded:: 2.11

    Parameters
    ----------
    message: :class:`disnake.Message`
        The message from which to extract the components.

    Raises
    ------
    TypeError
        An unknown component type is encountered.

    Returns
    -------
    :class:`list`\[:class:`UIComponent`]:
        The ui components parsed from the components on the message.
    """
    components: list[UIComponent] = [_to_ui_component(c) for c in message.components]
    return cast("list[MessageTopLevelComponent]", components)


UI_COMPONENT_LOOKUP: Mapping[type[Component], type[UIComponent]] = {
    ActionRowComponent: ActionRow,
    ButtonComponent: Button,
    StringSelectComponent: StringSelect,
    TextInputComponent: TextInput,
    UserSelectComponent: UserSelect,
    RoleSelectComponent: RoleSelect,
    MentionableSelectComponent: MentionableSelect,
    ChannelSelectComponent: ChannelSelect,
    SectionComponent: Section,
    TextDisplayComponent: TextDisplay,
    ThumbnailComponent: Thumbnail,
    MediaGalleryComponent: MediaGallery,
    FileComponent: File,
    SeparatorComponent: Separator,
    ContainerComponent: Container,
    LabelComponent: Label,
    FileUploadComponent: FileUpload,
    RadioGroupComponent: RadioGroup,
    CheckboxGroupComponent: CheckboxGroup,
    CheckboxComponent: Checkbox,
}


def _to_ui_component(component: Component) -> UIComponent:
    try:
        ui_cls = UI_COMPONENT_LOOKUP[type(component)]
    except KeyError:
        # this should never happen
        msg = f"unknown component type: {type(component)}"
        raise TypeError(msg) from None
    else:
        return ui_cls.from_component(component)


def _message_component_to_item(
    component: ActionRowMessageComponentRaw,
) -> ActionRowMessageComponent | None:
    if isinstance(
        component,
        (
            ButtonComponent,
            StringSelectComponent,
            UserSelectComponent,
            RoleSelectComponent,
            MentionableSelectComponent,
            ChannelSelectComponent,
        ),
    ):
        return _to_ui_component(component)  # pyright: ignore[reportReturnType]

    assert_never(component)
    return None
