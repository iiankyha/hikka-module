from hikka import loader, utils
from telethon.tl.types import Message
import random
import asyncio
import logging

@loader.tds
class CubeSpamMod(loader.Module):
    """Спам эмодзи-кубиками с настраиваемым интервалом"""
    strings = {"name": "CubeSpam"}
    
    __version__ = (1, 0, 2)
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "interval",
                10,
                "Интервал отправки в секундах",
                validator=loader.validators.Integer(minimum=3)
            )
        )
        self.task = None
        self.log = logging.getLogger(__name__)
        self.emoji_cubes = [
            "🎲 1️⃣", "🎲 2️⃣", "🎲 3️⃣",
            "🎲 4️⃣", "🎲 5️⃣", "🎲 6️⃣"
        ]

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

    async def spam_task(self):
        while True:
            try:
                await self._client.send_message(
                    self.chat_id,
                    random.choice(self.emoji_cubes)
                )
                await asyncio.sleep(self.config["interval"])
            except Exception as e:
                self.log.error(f"Ошибка: {e}", exc_info=True)
                break

    @loader.command
    async def cubestart(self, message: Message):
        """Запустить спам кубиками в текущем чате"""
        if self.task and not self.task.done():
            await utils.answer(message, "🚫 Спам уже запущен!")
            return
            
        self.chat_id = message.chat_id
        self.task = asyncio.create_task(self.spam_task())
        await utils.answer(
            message,
            f"🎲 Спам запущен с интервалом {self.config['interval']} сек\n"
            "Для остановки используй команду .cubestop"
        )

    @loader.command
    async def cubestop(self, message: Message):
        """Остановить спам"""
        if self.task and not self.task.done():
            self.task.cancel()
            await utils.answer(message, "🛑 Спам остановлен")
        else:
            await utils.answer(message, "ℹ️ Спам не был запущен")

    async def on_unload(self):
        if self.task:
            self.task.cancel()
