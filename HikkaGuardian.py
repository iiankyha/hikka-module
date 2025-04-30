from hikka import loader, utils
from telethon.tl.types import Message, PeerUser
from datetime import datetime
import asyncio
import logging
from cryptography.fernet import Fernet
import json
import re

logger = logging.getLogger(__name__)

class HikkaGuardianDB:
    """Безопасное хранилище данных"""
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.data = None
        self.load()
        
        # Гарантированная инициализация
        if self.data is None:
            self._init_default_data()
            self.save()

    def _init_default_data(self):
        self.data = {
            "filters": {"important": [], "neutral": [], "blocked": []},
            "reminders": {},
            "diary": []
        }

    def save(self):
        try:
            with open("hikkaguardian.enc", "wb") as f:
                f.write(self.cipher.encrypt(json.dumps(self.data).encode()))
        except Exception as e:
            logger.error(f"Save Error: {str(e)}")

    def load(self):
        try:
            with open("hikkaguardian.enc", "rb") as f:
                self.data = json.loads(self.cipher.decrypt(f.read()).decode())
        except Exception as e:
            logger.error(f"Load Error: {str(e)}")
            self._init_default_data()

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Исправленный модуль"""
    strings = {"name": "HikkaGuardian"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "AUTO_DELETE", True, "Автофильтрация"
        )
        self.db = HikkaGuardianDB()

    async def client_ready(self, client, db):
        self.client = client
        # Дополнительная проверка
        if not hasattr(self.db, 'data') or self.db.data is None:
            self.db._init_default_data()

    async def watcher(self, message: Message):
        try:
            if not isinstance(message.peer_id, PeerUser):
                return

            # Проверка и инициализация при каждом вызове
            if self.db.data is None:
                self.db._init_default_data()

            if self.config["AUTO_DELETE"]:
                text = (message.text or "").lower()
                blocked_pattern = re.compile(
                    "|".join(map(re.escape, self.db.data["filters"]["blocked"])),
                    flags=re.IGNORECASE
                )
                if blocked_pattern.search(text):
                    await message.delete()

        except Exception as e:
            logger.error(f"Watcher Error: {str(e)}")

async def setup(client):
    await client.load_module(HikkaGuardianMod())
