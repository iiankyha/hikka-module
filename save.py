from hikka import loader, utils
from telethon.tl.types import Message, PeerUser
from datetime import datetime, timedelta
import asyncio
import logging
from cryptography.fernet import Fernet
import json
import re

logger = logging.getLogger(__name__)

class HikkaGuardianDB:
    """Класс для работы с зашифрованным хранилищем"""
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.data = {
            "filters": {"important": [], "neutral": [], "blocked": []},
            "reminders": {},
            "diary": []
        }
    
    def save(self):
        with open("hikkaguardian.enc", "wb") as f:
            f.write(self.cipher.encrypt(json.dumps(self.data).encode()))

    def load(self):
        try:
            with open("hikkaguardian.enc", "rb") as f:
                self.data = json.loads(self.cipher.decrypt(f.read()).decode())
        except FileNotFoundError:
            self.save()

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Цифровой щит для интровертов"""
    strings = {
        "name": "HikkaGuardian",
        "meal_time": "🍱 <b>Время поесть!</b>\nРекомендация: {}",
        "sleep_time": "🌙 <b>Постепенно готовься ко сну</b>\nТемпература в комнате: {}°C"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MEAL_TIMES", ["10:00", "13:00", "19:00"], "Время напоминаний о еде",
            "SLEEP_TIME", "23:00", "Время напоминания о сне",
            "ALLOW_AUTO_DELETE", True, "Автоудаление сообщений из чатов"
        )
        self.db = HikkaGuardianDB()
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        self.db.load()
        self._schedule_reminders()

    def _schedule_reminders(self):
        async def reminder_loop():
            while True:
                now = datetime.now().strftime("%H:%M")
                if now in self.config["MEAL_TIMES"]:
                    await self.client.send_message(
                        "me",
                        self.strings["meal_time"].format("гречневая каша с овощами")
                    )
                if now == self.config["SLEEP_TIME"]:
                    await self.client.send_message(
                        "me",
                        self.strings["sleep_time"].format(22)
                    )
                await asyncio.sleep(60)
        
        self.reminder_task = asyncio.create_task(reminder_loop())

    async def watcher(self, message: Message):
        """Автоматическая фильтрация входящих сообщений"""
        if not isinstance(message.peer_id, PeerUser):
            return

        text = (message.text or "").lower()
        sender = await message.get_sender()

        # Важные контакты
        if str(sender.id) in self.db.data["filters"]["important"]:
            await message.pin()
            return

        # Блокировка триггерных слов
        blocked_pattern = "|".join(self.db.data["filters"]["blocked"])
        if re.search(blocked_pattern, text, re.IGNORECASE):
            await message.delete()
            await self.client.send_message(
                "me",
                f"🚫 Удалено сообщение от {sender.first_name}: {text[:50]}..."
            )

    @loader.unrestricted
    async def hgfiltercmd(self, message: Message):
        """Добавить фильтры .hgfilter <тип> <список>"""
        args = utils.get_args_raw(message).split(" ", 1)
        if len(args) < 2:
            await utils.answer(message, "❌ Формат: .hgfilter <important|neutral|blocked> <список>")
            return

        filter_type, content = args
        if filter_type not in self.db.data["filters"]:
            await utils.answer(message, f"❌ Неверный тип фильтра. Доступно: {', '.join(self.db.data['filters'].keys())}")
            return

        self.db.data["filters"][filter_type] = [x.strip() for x in content.split(",")]
        self.db.save()
        await utils.answer(message, f"✅ Фильтр '{filter_type}' обновлен!")

    @loader.unrestricted
    async def hgdiarycmd(self, message: Message):
        """Добавить запись в дневник .hgdiary <текст>"""
        entry = utils.get_args_raw(message)
        if not entry:
            await utils.answer(message, "❌ Введите текст записи")
            return

        self.db.data["diary"].append({
            "date": datetime.now().isoformat(),
            "text": entry
        })
        self.db.save()
        await utils.answer(message, "📖 Запись добавлена в зашифрованный дневник")

    @loader.unrestricted
    async def hgstatcmd(self, message: Message):
        """Статистика активности"""
        stats = (
            f"🌸 <b>Ваша статистика:</b>\n"
            f"Записей в дневнике: {len(self.db.data['diary'])}\n"
            f"Важных контактов: {len(self.db.data['filters']['important']}\n"
            f"Блокированных слов: {len(self.db.data['filters']['blocked']}"
        )
        await utils.answer(message, stats)

async def setup(client):
    await client.load_module(HikkaGuardianMod())
