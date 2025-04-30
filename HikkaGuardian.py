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
    """Усовершенствованное хранилище данных"""
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
            logger.critical(f"Key Error: {str(e)}")
            raise

    def _initialize(self):
        try:
            self.load()
        except Exception as e:
            logger.error(f"Init Error: {str(e)}")
            self.data = self.default_data()
            self.save()

    def default_data(self):
        return {
            "version": 3,
            "diary": [],
            "filters": {
                "blocked": ["спам", "реклама"],
                "important": []
            }
        }

    def _validate(self, data):
        return isinstance(data, dict) and all(
            key in data for key in ["version", "filters", "diary"]
        )

    def save(self):
        try:
            temp_file = "hikkaguardian.tmp"
            with open(temp_file, "wb") as f:
                f.write(self.cipher.encrypt(
                    json.dumps(self.data).encode("utf-8")
                ))
            os.replace(temp_file, "hikkaguardian.enc")
            os.chmod("hikkaguardian.enc", 0o600)
        except Exception as e:
            logger.error(f"Save Failed: {str(e)}")

    def load(self):
        try:
            if not os.path.exists("hikkaguardian.enc"):
                self.data = self.default_data()
                self.save()
                return

            with open("hikkaguardian.enc", "rb") as f:
                decrypted = self.cipher.decrypt(f.read())
                data = json.loads(decrypted.decode("utf-8"))

                if self._validate(data):
                    self.data = data
                    if data["version"] < 3:
                        self._migrate(data)
                else:
                    raise ValueError("Invalid structure")

        except (InvalidToken, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Critical Load Error: {str(e)}")
            self._emergency_recovery()
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}")
            self._emergency_recovery()

    def _migrate(self, old_data):
        self.data = self.default_data()
        self.data.update(old_data)
        self.data["version"] = 3
        self.save()

    def _emergency_recovery(self):
        backup_file = f"hikkaguardian.bak.{datetime.now().timestamp()}"
        os.rename("hikkaguardian.enc", backup_file)
        self.data = self.default_data()
        self.save()
        logger.critical(f"Database recovered! Backup: {backup_file}")

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Универсальный модуль для комфортного использования"""
    strings = {"name": "HikkaGuardian"}

    def __init__(self):
        self.db = HikkaGuardianDB()
        self.config = loader.ModuleConfig(
            # Основные настройки
            "ENABLED", True, 
            lambda: "Активировать модуль",
            
            "AUTO_DELETE", True,
            lambda: "Автоудаление сообщений",
            
            "ALLOWED_USERS", [], 
            lambda: "Доверенные пользователи (ID)",
            
            # Время и напоминания
            "MEAL_REMINDERS", ["10:00", "13:00", "19:00"],
            lambda: "Время приема пищи",
            
            "SLEEP_TIME", "23:00",
            lambda: "Время отхода ко сну",
            
            # Фильтрация
            "BLOCKED_WORDS", ["спам", "тревога"], 
            lambda: "Запрещенные слова",
            
            "USE_REGEX", False,
            lambda: "Использовать регулярки",
            
            # Персона
