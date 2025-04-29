# -*- coding: utf-8 -*-
from .. import loader, utils


@loader.tds
class AntonMod(loader.Module):
    """Отвечает &laquo;my def is @seys666228&raquo; со спойлером"""

    strings = {"name": "AntonMod"}

    async def antoncmd(self, message):
        # Отправляем сообщение, оборачивая ник в спойлер через HTML-разметку
        await utils.answer(
            message,
            "my def is <tg-spoiler>@seys666228</tg-spoiler>",
            parse_mode="html",
