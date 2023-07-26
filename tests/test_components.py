
from disnake.components import Button, ActionRow, UrlButton, TextInput
from disnake.types.components import ButtonPayload
from disnake.ui import Button as UIButton, Modal
from disnake import ButtonStyle, MessageInteraction, ComponentType
from disnake.abc import Messageable


class SomeComponent:
    type = ComponentType.button

    def to_dict(self) -> ButtonPayload:
        return {
            "type": 2,
            "style": 1,
            "custom_id": "blahaj"
        }


async def test_types(sender: Messageable, inter: MessageInteraction) -> None:
    button = Button(ButtonStyle.gray, "xyz")
    url_button = UrlButton("https://google.com")
    ui_button = UIButton()
    foreign = SomeComponent()
    action_row = ActionRow([button, ui_button, foreign])


    await sender.send(components=button)
    await sender.send(components=[action_row, [button, url_button, ui_button], [foreign]])
    await inter.response.send_message(components=[action_row])

    modal_action_row = ActionRow([TextInput("abc")])
    Modal(title="invalid", components=[foreign])
    modal = Modal(title="xyz", components=[modal_action_row, [TextInput("foo")]])
    await sender.send(components=modal)
    await inter.response.send_modal(modal)
