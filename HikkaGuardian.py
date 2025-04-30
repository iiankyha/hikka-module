from hikka import loader, utils
from telethon.tl.types import Message
import random
import asyncio

@loader.tds
class CubeSpamMod(loader.Module):
    """Спам кубиком с настраиваемым интервалом (работает в любых чатах)"""
    strings = {"name": "CubeSpam"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "default_interval", 10, "Интервал по умолчанию в секундах"
        )
        self.task = None
        self.interval = self.config["default_interval"]
        self.emoji_map = {
            1: "🎲 1️⃣",
            2: "🎲 2️⃣",
            3: "🎲 3️⃣",
            4: "🎲 4️⃣",
            5: "🎲 5️⃣",
            6: "🎲 6️⃣"
        }
        self.chat_id = None

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        # Восстанавливаем последний использованный чат
        self.chat_id = self._db.get("CubeSpam", "chat_id", None)

    async def spam_cube(self):
        while True:
            try:
                num = random.randint(1, 6)
                await self._client.send_message(
                    self.chat_id,
                    self.emoji_map[num]
                )
                await asyncio.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"Ошибка: {str(e)}")
                await self.stop_spam()
                break

    async def stop_spam(self):
        if self.task and not self.task.done():
            self.task.cancel()
        self.task = None

    @loader.command
    async def cubespam(self, message: Message):
        """- запустить/остановить спам (интервал в секундах)"""
        args = utils.get_args_raw(message)
        
        # Если уже запущен - останавливаем
        if self.task and not self.task.done():
            await self.stop_spam()
            await utils.answer(message, "🛑 Спам остановлен")
            return

        # Устанавливаем новый chat_id
        self.chat_id = message.chat_id
        self._db.set("CubeSpam", "chat_id", self.chat_id)

        # Парсим интервал
        try:
            self.interval = int(args) if args else self.config["default_interval"]
        except ValueError:
            await utils.answer(message, "❌ Неверный интервал")
            return

        # Запускаем спам
        self.task = asyncio.create_task(self.spam_cube())
        await utils.answer(message, f"🎲 Спам запущен с интервалом {self.interval} сек")

    async def on_unload(self):
        await self.stop_spam()
