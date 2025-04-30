from hikka import loader, utils
from telethon.tl.types import Message, PeerUser
from datetime import datetime, time
import asyncio
import logging
from cryptography.fernet import Fernet, InvalidToken
import json
import re
import os

logger = logging.getLogger(__name__)

class HikkaGuardianDB:
    """Безопасное хранилище данных"""
    def __init__(self):
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
        self.data = None
        self._initialize()

    def _load_or_create_key(self):
        key_file = "hikka_guardian.key"
        try:
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    return f.read()
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            os.chmod(key_file, 0o600)
            return key
        except Exception as e:
            logger.critical(f"Key Error: {e}")
            raise

    def _initialize(self):
        try:
            self.load()
        except Exception as e:
            logger.error(f"DB Init Error: {e}")
            self.data = self.default_data()
            self.save()

    def default_data(self):
        return {
            "version": 5,
            "diary": [],
            "filters": {
                "blocked": ["спам", "реклама"],
                "important": []
            }
        }

    def save(self):
        try:
            with open("hikkaguardian.tmp", "wb") as f:
                f.write(self.cipher.encrypt(json.dumps(self.data).encode()))
            os.replace("hikkaguardian.tmp", "hikkaguardian.enc")
        except Exception as e:
            logger.error(f"Save Error: {e}")

    def load(self):
        try:
            if not os.path.exists("hikkaguardian.enc"):
                self.data = self.default_data()
                return
            
            with open("hikkaguardian.enc", "rb") as f:
                decrypted = self.cipher.decrypt(f.read())
                self.data = json.loads(decrypted.decode())
                
        except Exception as e:
            logger.error(f"Load Error: {e}")
            self._emergency_recovery()

    def _emergency_recovery(self):
        self.data = self.default_data()
        self.save()

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Персонализированный ассистент для комфортного использования"""
    strings = {"name": "HikkaGuardian"}

    def __init__(self):
        self.db = HikkaGuardianDB()
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "ENABLED",
                True,
                "Активировать модуль",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "AUTO_DELETE",
                True,
                "Автоматическое удаление сообщений",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "MEAL_TIMES",
                ["10:00", "13:00", "19:00"],
                "Время напоминаний о еде",
                validator=loader.validators.Series(
                    loader.validators.Time()
                )
            ),
            loader.ConfigValue(
                "BLOCKED_WORDS",
                ["спам", "тревога"],
                "Запрещенные слова/фразы",
                validator=loader.validators.Series(
                    loader.validators.String()
                )
            )
        )
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        self._start_reminders()

    def _start_reminders(self):
        async def reminder_loop():
            while True:
                now = datetime.now().strftime("%H:%M")
                if now in self.config["MEAL_TIMES"]:
                    await self.client.send_message("me", "🍱 Время поесть!")
                await asyncio.sleep(60)

        self.reminder_task = asyncio.create_task(reminder_loop())

    @loader.unrestricted
    async def hgsetcmd(self, message: Message):
        """Изменить настройки"""
        args = utils.get_args_raw(message)
        if not args:
            return await self._show_settings(message)
            
        try:
            key, value = args.split(" ", 1)
            self.config[key] = value
            await utils.answer(message, f"✅ {key} обновлен")
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка: {str(e)}")

    async def _show_settings(self, message: Message):
        """Показать настройки через новый API"""
        settings = []
        for key in self.config:
            value = self.config[key]
            doc = self.config.get_doc(key)
            settings.append(
                f"• <b>{key}</b>: <code>{value}</code>\n"
                f"<i>{doc}</i>\n"
            )
            
        await utils.answer(
            message,
            "⚙️ <b>Настройки HikkaGuardian</b>\n\n" + "\n".join(settings),
            parse_mode="HTML"
        )

    async def watcher(self, message: Message):
        if self.config["AUTO_DELETE"]:
            text = (message.text or "").lower()
            if any(word in text for word in self.config["BLOCKED_WORDS"]):
                await message.delete()

async def setup(client):
    await client.load_module(HikkaGuardianMod())
