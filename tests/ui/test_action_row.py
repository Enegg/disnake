# SPDX-License-Identifier: MIT

from unittest import mock

import pytest

import disnake
from disnake.ui import (
    ActionRow,
    Button,
    Label,
    Separator,
    StringSelect,
    TextInput,
)
from disnake.ui.action_row import normalize_components, normalize_components_to_dict

button1 = Button()
button2 = Button()
button3 = Button()
select = StringSelect()
text_input = TextInput(label="a", custom_id="b")
separator = Separator()
label__text = Label("a", text_input)
label__select = Label("a", select)


class TestActionRow:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ([], 0),
            ([button1], 1),
            ([button1] * 4, 4),
            ([select], 5),
        ],
    )
    def test_width(self, value, expected) -> None:
        assert ActionRow(*value).width == expected

    def test_dunder(self) -> None:
        r = ActionRow(button1, button2)
        assert r[1] is button2

        del r[0]
        assert list(r.children) == [button2]

    def test_rows_from_message(self) -> None:
        rows = [
            ActionRow(button1, button2),
            ActionRow(select),
            ActionRow(button2),
            ActionRow(button3),
        ]

        message = mock.Mock(disnake.Message)
        message.components = [r._underlying for r in rows]
        result = ActionRow.rows_from_message(message)

        assert len(result) == len(rows)
        # compare component types and IDs
        for actual, expected in zip(result, rows, strict=True):
            assert [(type(c), c.custom_id) for c in actual] == [
                (type(c), c.custom_id) for c in expected
            ]

    def test_rows_from_message__invalid(self) -> None:
        message = mock.Mock(disnake.Message)
        message.components = [ActionRow(text_input)._underlying]

        # check non-strict behavior
        non_strict = ActionRow.rows_from_message(message, strict=False)
        assert len(non_strict) == 1
        assert len(non_strict[0]) == 0

        # check (default) strict behavior
        with pytest.raises(TypeError, match=r"Encountered unknown component type: .*text_input"):
            ActionRow.rows_from_message(message)

    def test_walk_components(self) -> None:
        rows = [
            ActionRow(button1, button2),
            ActionRow(select),
            ActionRow(button2),
            ActionRow(button3),
        ]

        expected = [(row, component) for row in rows for component in row.children]
        for (act_row, act_cmp), (exp_row, exp_cmp) in zip(
            ActionRow.walk_components(rows), expected, strict=True
        ):
            # test mutation (rows)
            # (remove row below the one containing select1)
            if act_cmp is select:
                rows.pop(rows.index(act_row) + 1)

            assert act_row is exp_row
            assert act_cmp is exp_cmp


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([], []),
        ([[]], [[]]),
        # nested lists
        (button1, [[button1]]),
        ([button1], [[button1]]),
        ([button1, button2], [[button1, button2]]),
        ([text_input, select], [[text_input], [select]]),
        (([button1],), [[button1]]),
        ([(button1,), button2], [[button1], [button2]]),
        # actionrows
        (ActionRow(button1), [[button1]]),
        ([ActionRow(button1)], [[button1]]),
        ([ActionRow(button1), button2], [[button1], [button2]]),
        ([button1, button2, ActionRow(button3)], [[button1, button2], [button3]]),
        # width limit
        ([button1] * 10, [[button1] * 5] * 2),
        ([button1, select], [[button1], [select]]),
        ([select, button1, button2], [[select], [button1, button2]]),
    ],
)
def test_normalize_components__actionrow(value, expected) -> None:
    rows = normalize_components(value)
    assert all(isinstance(row, ActionRow) for row in rows)
    assert [list(row.children) for row in rows] == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # simple cases
        ([separator], [separator]),
        ([separator, ActionRow(button1)], [separator, [button1]]),
        ([ActionRow(button1), separator], [[button1], separator]),
        ([separator, ActionRow(button1), separator], [separator, [button1], separator]),
        # flat list
        ([button1, separator], [[button1], separator]),
        ([separator, button1], [separator, [button1]]),
        (
            [separator, button1, button2, separator, button3],
            [separator, [button1, button2], separator, [button3]],
        ),
    ],
)
def test_normalize_components__v2(value, expected) -> None:
    result = normalize_components(value)
    assert [(list(c.children) if isinstance(c, ActionRow) else c) for c in result] == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([text_input], [[text_input]]),
        ([select], [select]),  # should not wrap select in action row
        (
            [label__text, text_input, select, label__select, text_input],
            [label__text, [text_input], select, label__select, [text_input]],
        ),
    ],
)
def test_normalize_components__modal(value, expected) -> None:
    result = normalize_components(value, modal=True)
    assert [(list(c.children) if isinstance(c, ActionRow) else c) for c in result] == expected


def test_normalize_components__invalid() -> None:
    for value in (42, [42], [ActionRow(), 42], iter([button1])):
        with pytest.raises(TypeError, match=r"`components` must be a"):
            normalize_components(value)  # pyright: ignore[reportArgumentType, reportCallIssue]
    for value in ([[[]]], [[[ActionRow()]]]):
        with pytest.raises(TypeError, match=r"components should be of type"):
            normalize_components(value)  # pyright: ignore[reportArgumentType, reportCallIssue]


def test_normalize_components_to_dict() -> None:
    result, is_v2 = normalize_components_to_dict([button1, button2, select, ActionRow(button3)])
    assert result == [
        {
            "type": 1,
            "id": 0,
            "components": [button1.to_component_dict(), button2.to_component_dict()],
        },
        {
            "type": 1,
            "id": 0,
            "components": [select.to_component_dict()],
        },
        {
            "type": 1,
            "id": 0,
            "components": [button3.to_component_dict()],
        },
    ]
    assert not is_v2


def test_normalize_components_to_dict__v2() -> None:
    _, is_v2 = normalize_components_to_dict([button1, separator, button2])
    assert is_v2
