from hikka import loader, utils
from telethon.tl.types import Message
from datetime import datetime
import asyncio
import logging
import re

logger = logging.getLogger(__name__)

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Универсальный модуль с гибкими настройками"""
    strings = {"name": "HikkaGuardian"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "MEAL_TIMES",
                ["10:00", "13:00", "19:00"],
                "Время напоминаний (ЧЧ:ММ через запятую)",
                validator=loader.validators.Series(
                    loader.validators.RegExp(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
                )
            ),
            loader.ConfigValue(
                "BLOCKED_WORDS",
                ["спам", "реклама"],
                "Запрещенные слова через запятую",
                validator=loader.validators.Series(
                    loader.validators.String()
                )
            )
        )

    async def client_ready(self, client, db):
        self.client = client
        self._validate_time_format()
        self._start_reminders()

    def _validate_time_format(self):
        """Кастомная валидация времени"""
        for time_str in self.config["MEAL_TIMES"]:
            if not re.match(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", time_str):
                raise ValueError(f"Некорректное время: {time_str}")

    def _start_reminders(self):
        async def reminder_loop():
            while True:
                now = datetime.now().strftime("%H:%M")
                if now in self.config["MEAL_TIMES"]:
                    await self.client.send_message("me", "🍱 Время поесть!")
                await asyncio.sleep(60)
        
        asyncio.create_task(reminder_loop())

    async def watcher(self, message: Message):
        if any(word in message.text.lower() 
               for word in self.config["BLOCKED_WORDS"]):
            await message.delete()

async def setup(client):
    await client.load_module(HikkaGuardianMod())
