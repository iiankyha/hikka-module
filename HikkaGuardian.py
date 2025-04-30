from hikka import loader, utils
from telethon.tl.types import Message, PeerUser
from datetime import datetime
import asyncio
import logging
from cryptography.fernet import Fernet, InvalidToken
import json
import re
import os

logger = logging.getLogger(__name__)

class HikkaGuardianDB:
    """Усовершенствованное хранилище с восстановлением при ошибках"""
    def __init__(self):
        self.key = self._get_encryption_key()
        self.cipher = Fernet(self.key)
        self.data = self._init_default_data()
        self.load()

    def _get_encryption_key(self):
        """Генерация стабильного ключа шифрования"""
        key_file = "hikka_guardian.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key

    def _init_default_data(self):
        """Создание структуры данных с проверкой"""
        return {
            "filters": {
                "important": [],
                "neutral": [],
                "blocked": []
            },
            "reminders": {},
            "diary": []
        }

    def _validate_data(self, data):
        """Проверка целостности данных"""
        return all(key in data for key in ["filters", "reminders", "diary"])

    def save(self):
        try:
            with open("hikkaguardian.enc", "wb") as f:
                encrypted = self.cipher.encrypt(
                    json.dumps(self.data).encode("utf-8")
                )
                f.write(encrypted)
        except Exception as e:
            logger.error(f"DB Save Error: {str(e)}")
            logger.debug("Traceback:", exc_info=True)

    def load(self):
        try:
            if not os.path.exists("hikkaguardian.enc"):
                self.save()
                return

            with open("hikkaguardian.enc", "rb") as f:
                decrypted = self.cipher.decrypt(f.read()).decode("utf-8")
                loaded_data = json.loads(decrypted)

                if self._validate_data(loaded_data):
                    self.data = loaded_data
                else:
                    raise ValueError("Invalid data structure")

        except (InvalidToken, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Critical DB Error: {str(e)}")
            logger.info("Creating new database...")
            self.data = self._init_default_data()
            self.save()
        except Exception as e:
            logger.error(f"Unexpected Load Error: {str(e)}")
            self.data = self._init_default_data()

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Исправленный модуль с защищенной БД"""
    strings = {"name": "HikkaGuardian"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "AUTO_DELETE", True, "Автофильтрация сообщений"
        )
        self.db = HikkaGuardianDB()
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        if not self._check_db_integrity():
            await self._recover_database()

    def _check_db_integrity(self):
        """Проверка целостности данных"""
        required_keys = ["filters", "reminders", "diary"]
        return all(key in self.db.data for key in required_keys)

    async def _recover_database(self):
        """Экстренное восстановление"""
        logger.critical("Database corruption detected! Reinitializing...")
        self.db.data = self.db._init_default_data()
        self.db.save()
        await self.client.send_message(
            "me",
            "⚠️ База данных восстановлена до заводских настроек"
        )

    async def watcher(self, message: Message):
        """Усовершенствованный обработчик"""
        try:
            if not isinstance(message.peer_id, PeerUser):
                return

            if self.config["AUTO_DELETE"] and self.db.data["filters"]["blocked"]:
                text = (message.text or "").lower()
                pattern = re.compile(
                    "|".join(map(re.escape, self.db.data["filters"]["blocked"])),
                    flags=re.IGNORECASE
                )
                if pattern.search(text):
                    await message.delete()
                    logger.info(f"Deleted message: {text[:50]}...")

        except Exception as e:
            logger.error(f"Watcher Error: {str(e)}")
            logger.debug("Traceback:", exc_info=True)

    # ... остальные методы остаются без изменений ...

async def setup(client):
    await client.load_module(HikkaGuardianMod())
