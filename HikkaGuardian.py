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
    """Безопасное хранилище данных с шифрованием"""
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
            "version": 4,
            "diary": [],
            "filters": {
                "blocked": ["спам", "реклама"],
                "important": []
            }
        }

    def _validate(self, data):
        return all(key in data for key in ["version", "filters", "diary"])

    def save(self):
        try:
            with open("hikkaguardian.tmp", "wb") as f:
                f.write(self.cipher.encrypt(json.dumps(self.data).encode()))
            os.replace("hikkaguardian.tmp", "hikkaguardian.enc")
            os.chmod("hikkaguardian.enc", 0o600)
        except Exception as e:
            logger.error(f"Save Error: {e}")

    def load(self):
        try:
            if not os.path.exists("hikkaguardian.enc"):
                self.data = self.default_data()
                return
            
            with open("hikkaguardian.enc", "rb") as f:
                decrypted = self.cipher.decrypt(f.read())
                data = json.loads(decrypted.decode())
                
                if self._validate(data):
                    self.data = data
                    if data["version"] < 4:
                        self._migrate(data)
                else:
                    raise ValueError("Invalid DB structure")
        except Exception as e:
            logger.error(f"Load Error: {e}")
            self._emergency_recovery()

    def _migrate(self, old_data):
        self.data = self.default_data()
        self.data.update(old_data)
        self.data["version"] = 4
        self.save()

    def _emergency_recovery(self):
        backup_name = f"hikkaguardian.bak.{datetime.now().timestamp()}"
        os.rename("hikkaguardian.enc", backup_name)
        self.data = self.default_data()
        self.save()
        logger.critical(f"Database recovered. Backup: {backup_name}")

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Персонализированный помощник для комфортного использования"""
    strings = {"name": "HikkaGuardian"}

    def __init__(self):
        self.db = HikkaGuardianDB()
        self.config = loader.ModuleConfig(
            "ENABLED", True, 
            lambda: "Активировать модуль",
            "AUTO_DELETE", True,
            lambda: "Автоматическое удаление сообщений",
            "ALLOWED_USERS", [],
            lambda: "Доверенные пользователи (ID через запятую)",
            "MEAL_TIMES", ["10:00", "13:00", "19:00"],
            lambda: "Время напоминаний о еде",
            "SLEEP_TIME", "23:00",
            lambda: "Время отхода ко сну",
            "BLOCKED_WORDS", ["спам", "тревога"],
            lambda: "Запрещенные слова/фразы",
            "USE_REGEX", False,
            lambda: "Фильтровать через регулярные выражения",
            "THEME_COLOR", "#7289DA",
            lambda: "Цвет интерфейса (HEX-формат)",
            "LANGUAGE", "ru",
            lambda: "Язык интерфейса (ru/en)",
            "BACKUP_ENABLED", True,
            lambda: "Автоматические бэкапы данных"
        )
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        self._validate_config()
        self._start_reminders()

    def _validate_config(self):
        errors = []
        
        # Проверка формата времени
        for time_str in self.config["MEAL_TIMES"]:
            try:
                hours, minutes = map(int, time_str.split(":"))
                time(hours, minutes)
            except ValueError:
                errors.append(f"Неверный формат времени: {time_str}")
        
        # Проверка HEX-цвета
        if not re.match(r"^#[0-9a-fA-F]{6}$", self.config["THEME_COLOR"]):
            errors.append("Некорректный HEX-цвет")
        
        if errors:
            logger.error("Ошибки конфигурации: " + ", ".join(errors))
            self.config["ENABLED"] = False

    def _start_reminders(self):
        async def reminder_loop():
            while True:
                try:
                    now = datetime.now().strftime("%H:%M")
                    
                    # Напоминания о еде
                    if now in self.config["MEAL_TIMES"]:
                        await self.client.send_message(
                            "me",
                            f"🍱 Время поесть! Текущие настройки:\n"
                            f"• Цвет: {self.config['THEME_COLOR']}\n"
                            f"• Язык: {self.config['LANGUAGE']}"
                        )
                    
                    # Напоминание ко сну
                    if now == self.config["SLEEP_TIME"]:
                        await self.client.send_message(
                            "me",
                            "🌙 Пора готовиться ко сну! Выключите яркий свет."
                        )
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка напоминаний: {e}")
                    await asyncio.sleep(300)

        if self.config["ENABLED"] and not self.reminder_task:
            self.reminder_task = asyncio.create_task(reminder_loop())

    @loader.unrestricted
    async def hgsetcmd(self, message: Message):
        """Изменить настройки модуля"""
        args = utils.get_args_raw(message)
        
        if not args:
            return await self._show_settings(message)
            
        try:
            key, value = args.split(" ", 1)
            key = key.upper()
            
            if key not in self.config:
                return await utils.answer(message, "❌ Неизвестный параметр")
            
            # Преобразование типов
            if key in ["ENABLED", "AUTO_DELETE", "USE_REGEX", "BACKUP_ENABLED"]:
                value = value.lower() in ["true", "1", "yes", "вкл"]
            elif key == "MEAL_TIMES":
                value = [t.strip() for t in value.split(",")]
            elif key == "ALLOWED_USERS":
                value = [int(u.strip()) for u in value.split(",")]
            
            self.config[key] = value
            await utils.answer(message, f"✅ {key} успешно обновлен")
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка: {str(e)}")

    async def _show_settings(self, message: Message):
        """Показать текущие настройки"""
        settings = []
        for key, config_item in self.config._mod_config.items():
            value = self.config[key]
            doc = getattr(config_item, "doc", "Без описания")
            settings.append(
                f"• <b>{key}</b>: <code>{value}</code>\n"
                f"<i>{doc}</i>\n"
            )
        
        await utils.answer(
            message,
            "⚙️ <b>Текущие настройки HikkaGuardian</b>\n\n" + "\n".join(settings),
            parse_mode="HTML"
        )

    @loader.unrestricted
    async def hgdiarycmd(self, message: Message):
        """Добавить запись в дневник"""
        entry = utils.get_args_raw(message)
        if not entry:
            return await utils.answer(message, "❌ Введите текст записи")
            
        self.db.data["diary"].append({
            "date": datetime.now().isoformat(),
            "text": entry,
            "mood": None
        })
        self.db.save()
        await utils.answer(message, "📖 Запись успешно сохранена")

    async def watcher(self, message: Message):
        """Система фильтрации сообщений"""
        if not self.config["ENABLED"] or not self.config["AUTO_DELETE"]:
            return
            
        try:
            text = (message.text or "").lower()
            
            # Проверка фильтров
            if self.config["USE_REGEX"]:
                pattern = re.compile(
                    "|".join(map(re.escape, self.config["BLOCKED_WORDS"])),
                    flags=re.IGNORECASE
                )
                match = pattern.search(text)
            else:
                match = any(word in text for word in self.config["BLOCKED_WORDS"])
            
            if match:
                await message.delete()
                logger.info(f"Удалено сообщение: {text[:50]}...")
                
        except Exception as e:
            logger.error(f"Ошибка фильтрации: {e}")

async def setup(client):
    await client.load_module(HikkaGuardianMod())
