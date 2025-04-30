from hikka import loader, utils
from telethon.tl.types import Message
from telethon.errors import ChatWriteForbidden, FloodWaitError
import random
import asyncio
import logging

@loader.tds
class CubeSpamMod(loader.Module):
    """Автоматическая отправка кубиков с настраиваемым интервалом"""
    strings = {"name": "CubeSpam"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "default_interval", 
            10, 
            lambda: "Интервал по умолчанию (секунды)"
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
        self.log = logging.getLogger(__name__)

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._me = await client.get_me()
        self.log.info("CubeSpam module initialized")

    async def _spam_loop(self):
        self.log.info("Spam loop started")
        while True:
            try:
                if not self._client.is_connected():
                    await self._client.connect()
                
                chat = await self._client.get_input_entity(self.chat_id)
                num = random.randint(1, 6)
                
                await self._client.send_message(
                    entity=chat,
                    message=self.emoji_map[num],
                    silent=True
                )
                self.log.debug(f"Sent cube {num} to {self.chat_id}")
                
                await asyncio.sleep(self.interval)
                
            except ChatWriteForbidden:
                self.log.error("No permissions to send messages")
                await self._stop_spam()
                break
            except FloodWaitError as e:
                self.log.warning(f"Flood wait: {e.seconds} seconds")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                self.log.error(f"Critical error: {repr(e)}")
                await self._stop_spam()
                break

    async def _stop_spam(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        self.log.info("Spam stopped")

    @loader.command
    async def cubespam(self, message: Message):
        """Запустить/остановить спам кубиками"""
        args = utils.get_args_raw(message)
        
        if self.task and not self.task.done():
            await self._stop_spam()
            await utils.answer(message, "🚫 Спам успешно остановлен")
            return

        try:
            self.interval = int(args) if args else self.config["default_interval"]
            if self.interval < 3:
                await utils.answer(message, "❌ Интервал не может быть меньше 3 секунд")
                return
        except ValueError:
            await utils.answer(message, "⚠️ Некорректный интервал. Использую значение по умолчанию")
            self.interval = self.config["default_interval"]

        self.chat_id = message.chat_id
        self.log.info(f"Starting spam in {self.chat_id} with interval {self.interval}s")
        
        try:
            self.task = asyncio.create_task(self._spam_loop())
            await utils.answer(message, f"🎲 Спам запущен!\nЧат: {self.chat_id}\nИнтервал: {self.interval} сек")
        except Exception as e:
            await utils.answer(message, f"🔥 Ошибка запуска: {str(e)}")
            self.log.exception("Startup failed")

    async def on_unload(self):
        await self._stop_spam()
        self.log.info("Module unloaded")
