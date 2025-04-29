# -*- coding: utf-8 -*-
# dox_slimes.py — модуль для Hikka Userbot
# Команды:
#   .dox      – имитирует «взлом» и показывает «данные его» со спойлерами
#   .sllimes  – отвечает «еблан»

from .. import loader
import asyncio


@loader.tds
class DoxSlimesMod(loader.Module):
    """Dox & Slimes – мемный модуль"""

    strings = {"name": "DoxSlimes"}

    async def doxcmd(self, message):
        """
        .dox
        1) Анимация «взлом жопы 0–100 %»
        2) «успешно»
        3) Чек-лист «данные его» со спойлерами
        """
        # Анимация прогресса
        for i in range(101):
            await message.edit(f"взлом жопы {i}%")
            await asyncio.sleep(0.05)

        # Статус «успешно» и небольшая пауза
        await message.edit("успешно")
        await asyncio.sleep(1)

        # Фейковые «доки» – все секции в ||…|| будут скрыты спойлером
        await message.edit(
            "данные его\n"
            "живёшь по адресу ||я не ебу лол|| дом ||хуй||\n"
            "отец:\n"
            "- номер ||89|| ||я не ебу лол это фан модуль||\n"
            "- адрес ул. ||хуил))|| дом ||я не ебу лол||\n"
            "мать:\n"
            "- номер ||89|| ||ыыыыы||\n"
            "- адрес ул. ||хиккировича|| дом ||чо||\n"
            "DEANONED BY KOSTYAN))"
        )

    async def sllimescmd(self, message):
        """.sllimes — удаляет команду и пишет «еблан»."""
        await message.delete()
        await message.respond("еблан")
