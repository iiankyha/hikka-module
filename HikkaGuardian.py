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
    """Персонализированный ассистент для комфортного использования"""
    strings = {"name": "HikkaGuardian"}

    def __init__(self):
        self.db = HikkaGuardianDB()
        self.config = loader.ModuleConfig(
            "ENABLED", True, 
            lambda: "Активировать модуль",
            "AUTO_DELETE", True,
            lambda: "Автоудаление сообщений",
            "ALLOWED_USERS", [], 
            lambda: "Доверенные пользователи (ID)",
            "MEAL_REMINDERS", ["10:00", "13:00", "19:00"],
            lambda: "Время приема пищи",
            "SLEEP_TIME", "23:00",
            lambda: "Время отхода ко сну",
            "BLOCKED_WORDS", ["спам", "тревога"], 
            lambda: "Запрещенные слова",
            "USE_REGEX", False,
            lambda: "Использовать регулярки",
            "THEME_COLOR", "#7289DA",
            lambda: "Цвет интерфейса (HEX)",
            "LANGUAGE", "ru",
            lambda: "Язык интерфейса",
            "BACKUP_ENABLED", True,
            lambda: "Авто-бэкапы"
        )
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        self._validate_config()
        self._start_reminders()
        
    def _validate_config(self):
        errors = []
        for t in self.config["MEAL_REMINDERS"]:
            try:
                time(*map(int, t.split(":")))
            except:
                errors.append(f"Некорректное время: {t}")
                
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", self.config["THEME_COLOR"]):
            errors.append("Неверный формат цвета")
            
        if errors:
            logger.error("Config errors: " + ", ".join(errors))
            self.config["ENABLED"] = False

    def _start_reminders(self):
        async def reminder_loop():
            while True:
                try:
                    now = datetime.now().strftime("%H:%M")
                    if now in self.config["MEAL_REMINDERS"]:
                        await self._send_reminder("🍱 Время поесть!")
                    if now == self.config["SLEEP_TIME"]:
                        await self._send_reminder("🌙 Пора спать!")
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Reminder Error: {str(e)}")
                    await asyncio.sleep(300)

        if self.config["ENABLED"]:
            self.reminder_task = asyncio.create_task(reminder_loop())

    async def _send_reminder(self, text):
        await self.client.send_message(
            "me",
            f"🔔 {text}\nЦвет интерфейса: {self.config['THEME_COLOR']}"
        )

    @loader.unrestricted
    async def hgsetcmd(self, message: Message):
        """Изменить настройку"""
        args = utils.get_args_raw(message)
        if not args:
            return await self._show_settings(message)
            
        try:
            key, value = args.split(" ", 1)
            key = key.upper()
            if key not in self.config:
                return await utils.answer(message, "❌ Неизвестный параметр")
                
            if key in ["ENABLED", "AUTO_DELETE", "USE_REGEX", "BACKUP_ENABLED"]:
                value = value.lower() in ["true", "1", "yes"]
            elif key == "MEAL_REMINDERS":
                value = value.split(",")
            elif key == "ALLOWED_USERS":
                value = [int(x) for x in value.split(",")]
                
            self.config[key] = value
            await utils.answer(message, f"✅ {key} обновлен")
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка: {str(e)}")

    async def _show_settings(self, message: Message):
        settings = []
        for key, value in self.config.get_attrs().items():
            desc = value.doc if hasattr(value, "doc") else "-"
            settings.append(
                f"• <b>{key}</b>: <code>{self.config[key]}</code>\n"
                f"<i>{desc}</i>\n"
            )
        await utils.answer(
            message,
            f"⚙️ <b>Настройки HikkaGuardian</b>\n\n" + "\n".join(settings),
            parse_mode="HTML"
        )

    @loader.unrestricted
    async def hgdiarycmd(self, message: Message):
        """Добавить запись в дневник"""
        entry = utils.get_args_raw(message)
        if not entry:
            await utils.answer(message, "❌ Введите текст записи")
            return

        self.db.data["diary"].append({
            "date": datetime.now().isoformat(),
            "text": entry
        })
        self.db.save()
        await utils.answer(message, "📖 Запись сохранена")

    async def watcher(self, message: Message):
        if not self.config["ENABLED"]:
            return
            
        if self.config["AUTO_DELETE"]:
            text = (message.text or "").lower()
            blocked_words = self.config["BLOCKED_WORDS"]
            
            if self.config["USE_REGEX"]:
                pattern = re.compile(
                    "|".join(map(re.escape, blocked_words)),
                    flags=re.IGNORECASE
                )
                match = pattern.search(text)
            else:
                match = any(word in text for word in blocked_words)
                
            if match:
                await message.delete()
                logger.info(f"Удалено сообщение: {text[:50]}...")

async def setup(client):
    await client.load_module(HikkaGuardianMod())
