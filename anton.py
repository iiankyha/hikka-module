from .. import loader, utils

@loader.tds
class AntonMod(loader.Module):
    """
    Replaces the message with "my def is @seys666228" when the .anton command is used.
    """
    strings = {
        "name": "AntonMod"
    }

    async def antonCmd(self, message):
        """
        .anton command handler
        """
        await utils.answer(message, "my def is @seys666228")

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
