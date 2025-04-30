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
    """Encrypted storage handler"""
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.data = {
            "filters": {"important": [], "neutral": [], "blocked": []},
            "reminders": {},
            "diary": []
        }
        self.load()
    
    def save(self):
        try:
            with open("hikkaguardian.enc", "wb") as f:
                encrypted = self.cipher.encrypt(json.dumps(self.data).encode())
                f.write(encrypted)
        except Exception as e:
            logger.error(f"Save error: {e}")

    def load(self):
        try:
            with open("hikkaguardian.enc", "rb") as f:
                decrypted = self.cipher.decrypt(f.read()).decode()
                self.data = json.loads(decrypted)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {
                "filters": {"important": [], "neutral": [], "blocked": []},
                "reminders": {},
                "diary": []
            }
        except Exception as e:
            logger.error(f"Load error: {e}")

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Digital Shield for Introverts"""
    strings = {
        "name": "HikkaGuardian",
        "meal_time": "🍱 <b>Time to eat!</b>\nRecommendation: {}",
        "sleep_time": "🌙 <b>Prepare for sleep</b>\nRoom temperature: {}°C",
        "filter_help": "❌ Format: .hgfilter <important|neutral|blocked> <list>",
        "diary_empty": "❌ Please enter diary text"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MEAL_TIMES", ["10:00", "13:00", "19:00"], "Meal reminders schedule",
            "SLEEP_TIME", "23:00", "Sleep reminder time",
            "ALLOW_AUTO_DELETE", True, "Auto-delete messages"
        )
        self.db = HikkaGuardianDB()
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        self._schedule_reminders()

    def _schedule_reminders(self):
        async def reminder_loop():
            while True:
                try:
                    now = datetime.now().strftime("%H:%M")
                    if now in self.config["MEAL_TIMES"]:
                        await self.client.send_message(
                            "me",
                            self.strings["meal_time"].format("buckwheat with vegetables")
                        )
                    if now == self.config["SLEEP_TIME"]:
                        await self.client.send_message(
                            "me",
                            self.strings["sleep_time"].format(22)
                        )
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Reminder error: {e}")
                    await asyncio.sleep(300)

        if not self.reminder_task or self.reminder_task.done():
            self.reminder_task = asyncio.create_task(reminder_loop())

    async def watcher(self, message: Message):
        """Message filtering logic"""
        try:
            if not isinstance(message.peer_id, PeerUser):
                return

            text = (message.text or "").lower()
            sender = await message.get_sender()

            if str(sender.id) in self.db.data["filters"]["important"]:
                await message.pin()
                return

            if self.config["ALLOW_AUTO_DELETE"]:
                blocked_pattern = re.compile(
                    "|".join(re.escape(word) for word in self.db.data["filters"]["blocked"]),
                    re.IGNORECASE
                )
                if blocked_pattern.search(text):
                    await message.delete()
                    await self.client.send_message(
                        "me",
                        f"🚫 Deleted message from {sender.first_name}: {text[:50]}..."
                    )
        except Exception as e:
            logger.error(f"Watcher error: {e}")

    @loader.unrestricted
    async def hgfiltercmd(self, message: Message):
        """Filter management command"""
        try:
            args = utils.get_args_raw(message).split(" ", 1)
            if len(args) < 2:
                await utils.answer(message, self.strings["filter_help"])
                return

            filter_type, content = args
            if filter_type not in self.db.data["filters"]:
                await utils.answer(message, 
                    f"❌ Invalid filter type. Available: {', '.join(self.db.data['filters'].keys())}"
                )
                return

            self.db.data["filters"][filter_type] = [x.strip() for x in content.split(",")]
            self.db.save()
            await utils.answer(message, f"✅ Filter '{filter_type}' updated!")
        except Exception as e:
            logger.error(f"Filter command error: {e}")

    @loader.unrestricted
    async def hgdiarycmd(self, message: Message):
        """Diary entry command"""
        try:
            entry = utils.get_args_raw(message)
            if not entry:
                await utils.answer(message, self.strings["diary_empty"])
                return

            self.db.data["diary"].append({
                "date": datetime.now().isoformat(),
                "text": entry
            })
            self.db.save()
            await utils.answer(message, "📖 Entry added to encrypted diary")
        except Exception as e:
            logger.error(f"Diary command error: {e}")

    @loader.unrestricted
    async def hgstatcmd(self, message: Message):
        """Statistics command"""
        try:
            stats = (
                f"🌸 <b>Statistics:</b>\n"
                f"Diary entries: {len(self.db.data['diary'])}\n"
                f"Important contacts: {len(self.db.data['filters']['important'])}\n"
                f"Blocked words: {len(self.db.data['filters']['blocked'])}"
            )
            await utils.answer(message, stats)
        except Exception as e:
            logger.error(f"Stats command error: {e}")

async def setup(client):
    await client.load_module(HikkaGuardianMod())
