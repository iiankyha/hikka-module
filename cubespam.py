from hikka import loader, utils
from telethon.tl.types import Message
import random
import asyncio

@loader.tds
class CubeSpamMod(loader.Module):
    """Спам кубиком с настраиваемым интервалом"""
    strings = {"name": "CubeSpam"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "default_interval", 10, "Интервал по умолчанию в секундах"
        )
        self.task = None
        self.is_active = False
        self.interval = self.config["default_interval"]
        self.emoji_map = {
            1: "🎲 1️⃣",
            2: "🎲 2️⃣",
            3: "🎲 3️⃣",
            4: "🎲 4️⃣",
            5: "🎲 5️⃣",
            6: "🎲 6️⃣"
        }

    async def client_ready(self, client, db):
        self._db = db
        self._client = client

    async def spam_cube(self):
        while self.is_active:
            try:
                num = random.randint(1, 6)
                await self._client.send_message(
                    self._db.get("CubeSpam", "chat_id"),
                    self.emoji_map[num]
                )
                await asyncio.sleep(self.interval)
            except Exception as e:
                self.logger.exception(e)
                break

    @loader.command
    async def cubespam(self, message: Message):
        """- запустить/остановить спам кубиком (интервал в секундах)"""
        args = utils.get_args_raw(message)
        
        if self.is_active:
            self.is_active = False
            if self.task:
                self.task.cancel()
            await utils.answer(message, "🛑 Спам остановлен")
            return

        try:
            self.interval = int(args) if args else self.config["default_interval"]
        except ValueError:
            await utils.answer(message, "❌ Неверный интервал")
            return

        self._db.set("CubeSpam", "chat_id", message.chat_id)
        self.is_active = True
        self.task = asyncio.create_task(self.spam_cube())
        await utils.answer(message, f"🎲 Спам запущен с интервалом {self.interval} сек")

    async def on_unload(self):
        if self.task:
            self.task.cancel()
