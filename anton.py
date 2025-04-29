from .. import loader, utils

@loader.tds
class AntonMod(loader.Module):
    strings = {"name": "AntonMod"}

    async def antoncmd(self, message):
        await utils.answer(
            message,
            "my def is <tg-spoiler>@seys666228</tg-spoiler>",
            parse_mode="html"
        )
