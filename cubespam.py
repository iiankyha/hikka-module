from hikka import loader, utils
from telethon.tl.types import Message
from telethon.errors import ChatWriteForbidden, FloodWaitError
import random
import asyncio
import logging

@loader.tds
class CubeSpamMod(loader.Module):
    """Спам кубиками с настраиваемым интервалом"""
    strings = {"name": "CubeSpam"}
    
    requirements = {
        "telethon": "telethon>=1.28.0",
        "hikkatl": "hikkatl>=1.2.0"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "default_interval", 
            10,
            "Интервал по умолчанию в секундах"
        )
        self.task = None
        self.active = False
        self.interval = self.config["default_interval"]
        self.chat_id = None
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
        self.log.info("Модуль CubeSpam инициализирован")

    async def spam_loop(self):
        while self.active:
            try:
                num = random.randint(1, 6)
                await self._client.send_message(
                    self.chat_id,
                    self.emoji_map[num]
                )
                await asyncio.sleep(self.interval)
                
            except ChatWriteForbidden:
                await self.stop_spam()
                break
            except FloodWaitError as e:
                self.log.warning(f"Флуд-контроль: {e.seconds} сек")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                self.log.error(f"Ошибка: {str(e)}")
                await self.stop_spam()
                break

    async def stop_spam(self):
        if self.task:
            self.task.cancel()
        self.active = False
        self.task = None

    @loader.command
    async def cubespam(self, message: Message):
        """Запустить/остановить спам"""
        args = utils.get_args_raw(message)
        
        if self.active:
            await self.stop_spam()
            await utils.answer(message, "🛑 Остановлено")
            return

        try:
            self.interval = int(args) if args else self.config["default_interval"]
            if self.interval < 3:
                await utils.answer(message, "❌ Минимум 3 секунды")
                return
        except ValueError:
            await utils.answer(message, "⚠️ Использую интервал по умолчанию")
            self.interval = self.config["default_interval"]

        self.chat_id = message.chat_id
        self.active = True
        self.task = asyncio.create_task(self.spam_loop())
        await utils.answer(message, f"🎲 Запущено! Интервал: {self.interval} сек")

    async def on_unload(self):
        await self.stop_spam()
