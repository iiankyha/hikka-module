from hikka import loader, utils
from telethon.tl.types import Message
import random
import asyncio
import logging

@loader.tds
class UserCubeSpam(loader.Module):
    """Спам кубиками от вашего аккаунта"""
    strings = {"name": "UserCubeSpam"}
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "interval", 
            10,
            "Интервал отправки в секундах",
            validator=loader.validators.Integer(minimum=5)
        )
        self.task = None
        self.log = logging.getLogger(__name__)
        self.cubes = ["🎲 1️⃣", "🎲 2️⃣", "🎲 3️⃣", "🎲 4️⃣", "🎲 5️⃣", "🎲 6️⃣"]

    async def client_ready(self, client, db):
        self._client = client  # Клиент вашего аккаунта
        self._db = db

    async def cube_loop(self):
        """Основной цикл отправки"""
        while True:
            try:
                await self._client.send_message(
                    self.target_chat,
                    random.choice(self.cubes)
                await asyncio.sleep(self.config["interval"])
                
            except Exception as e:
                self.log.error(f"Ошибка: {e}")
                await self.stop_spam()
                break

    @loader.command
    async def cubego(self, message: Message):
        """Запустить спам в этом чате"""
        if self.task:
            await utils.answer(message, "❌ Спам уже запущен!")
            return
            
        self.target_chat = message.chat_id  # Отправка в текущий чат
        self.task = asyncio.create_task(self.cube_loop())
        await utils.answer(
            message,
            f"✅ Кубики запущены!\n"
            f"Интервал: {self.config['interval']} сек\n"
            f"Остановка: .cubestop"
        )

    @loader.command
    async def cubestop(self, message: Message):
        """Остановить спам"""
        if self.task:
            self.task.cancel()
            await utils.answer(message, "🛑 Спам остановлен")
        else:
            await utils.answer(message, "⚠️ Спам не активен")

    async def on_unload(self):
        if self.task:
            self.task.cancel()
