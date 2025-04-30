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
    """Безопасное хранилище данных с шифрованием"""
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.data = None
        self.load()

    def _init_default_data(self):
        """Инициализация структуры данных по умолчанию"""
        self.data = {
            "filters": {
                "important": [],
                "neutral": [],
                "blocked": []
            },
            "reminders": {},
            "diary": []
        }

    def save(self):
        try:
            if self.data is None:
                self._init_default_data()
                
            with open("hikkaguardian.enc", "wb") as f:
                encrypted = self.cipher.encrypt(
                    json.dumps(self.data).encode()
                )
                f.write(encrypted)
        except Exception as e:
            logger.error(f"DB Save Error: {str(e)}")

    def load(self):
        try:
            with open("hikkaguardian.enc", "rb") as f:
                decrypted = self.cipher.decrypt(f.read()).decode()
                self.data = json.loads(decrypted)
        except FileNotFoundError:
            self._init_default_data()
            self.save()
        except json.JSONDecodeError:
            logger.error("DB corrupted, creating new one")
            self._init_default_data()
            self.save()
        except Exception as e:
            logger.error(f"DB Load Error: {str(e)}")
            self._init_default_data()

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Персональный ассистент для хикикомори"""
    strings = {
        "name": "HikkaGuardian",
        "meal_reminder": "🍱 Время поесть! Рекомендуем: {}",
        "sleep_reminder": "🌙 Пора готовиться ко сну. Идеальная температура: {}°C",
        "filter_help": "❌ Формат: .hgfilter <тип> <список_слов>",
        "diary_success": "📖 Запись добавлена в зашифрованный дневник",
        "stats_header": "🌸 **Ваша статистика:**\nЗаписей: {}\nВажных контактов: {}\nБлокировок: {}"
    }

    __dependencies__ = ["cryptography"]

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MEAL_TIMES", ["10:00", "13:00", "19:00"],
            "Расписание напоминаний о еде",
            "SLEEP_TIME", "23:00",
            "Время напоминания о сне",
            "AUTO_DELETE", True,
            "Автоматическая фильтрация сообщений"
        )
        self.db = HikkaGuardianDB()
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        if self.db.data is None:
            self.db._init_default_data()
        self._start_reminders()

    def _start_reminders(self):
        async def reminder_loop():
            while True:
                try:
                    now = datetime.now().strftime("%H:%M")
                    
                    if now in self.config["MEAL_TIMES"]:
                        await self.client.send_message(
                            "me",
                            self.strings("meal_reminder").format("гречка с овощами")
                        )
                    
                    if now == self.config["SLEEP_TIME"]:
                        await self.client.send_message(
                            "me",
                            self.strings("sleep_reminder").format(22)
                        )
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Reminder Error: {str(e)}")
                    await asyncio.sleep(300)

        if not self.reminder_task or self.reminder_task.done():
            self.reminder_task = asyncio.create_task(reminder_loop())

    async def watcher(self, message: Message):
        """Система фильтрации сообщений"""
        try:
            if not isinstance(message.peer_id, PeerUser):
                return

            if self.db.data is None:
                self.db._init_default_data()

            if self.config["AUTO_DELETE"]:
                text = (message.text or "").lower()
                blocked_words = self.db.data["filters"]["blocked"]
                
                if blocked_words:
                    pattern = re.compile(
                        "|".join(map(re.escape, blocked_words)),
                        flags=re.IGNORECASE
                    )
                    if pattern.search(text):
                        await message.delete()
                        await self.client.send_message(
                            "me",
                            "🚫 Сообщение удалено: обнаружены запрещенные слова"
                        )

            sender = await message.get_sender()
            if str(sender.id) in self.db.data["filters"]["important"]:
                await message.pin()

        except Exception as e:
            logger.error(f"Watcher Error: {str(e)}")

    @loader.unrestricted
    async def hgfiltercmd(self, message: Message):
        """Управление фильтрами: .hgfilter <тип> <слова>"""
        try:
            args = utils.get_args_raw(message).split(" ", 1)
            if len(args) < 2:
                await utils.answer(message, self.strings("filter_help"))
                return

            filter_type, content = args
            if filter_type not in self.db.data["filters"]:
                await utils.answer(
                    message,
                    f"⚠️ Доступные типы: {', '.join(self.db.data['filters'].keys())}"
                )
                return

            self.db.data["filters"][filter_type] = [
                item.strip() for item in content.split(",")
            ]
            self.db.save()
            await utils.answer(
                message,
                f"✅ Фильтр '{filter_type}' обновлен!"
            )
        except Exception as e:
            logger.error(f"Filter Error: {str(e)}")
            await utils.answer(message, "❌ Ошибка обновления фильтров")

    @loader.unrestricted
    async def hgdiarycmd(self, message: Message):
        """Добавить запись в дневник: .hgdiary <текст>"""
        try:
            entry = utils.get_args_raw(message)
            if not entry:
                await utils.answer(message, "📝 Введите текст записи")
                return

            self.db.data["diary"].append({
                "date": datetime.now().isoformat(),
                "text": entry
            })
            self.db.save()
            await utils.answer(message, self.strings("diary_success"))
        except Exception as e:
            logger.error(f"Diary Error: {str(e)}")
            await utils.answer(message, "❌ Ошибка сохранения записи")

    @loader.unrestricted
    async def hgstatcmd(self, message: Message):
        """Показать статистику: .hgstat"""
        try:
            stats = self.strings("stats_header").format(
                len(self.db.data["diary"]),
                len(self.db.data["filters"]["important"]),
                len(self.db.data["filters"]["blocked"])
            )
            await utils.answer(message, stats)
        except Exception as e:
            logger.error(f"Stats Error: {str(e)}")
            await utils.answer(message, "❌ Ошибка загрузки статистики")

async def setup(client):
    await client.load_module(HikkaGuardianMod())
