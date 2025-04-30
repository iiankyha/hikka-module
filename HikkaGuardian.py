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
    """Encrypted storage manager"""
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
                f.write(self.cipher.encrypt(
                    json.dumps(self.data).encode()
                ))
        except Exception as e:
            logger.error(f"DB Save Error: {str(e)}")

    def load(self):
        try:
            with open("hikkaguardian.enc", "rb") as f:
                self.data = json.loads(
                    self.cipher.decrypt(f.read()).decode()
                )
        except FileNotFoundError:
            self.data = {
                "filters": {"important": [], "neutral": [], "blocked": []},
                "reminders": {},
                "diary": []
            }
        except json.JSONDecodeError:
            logger.error("DB Corrupted, creating new one")
            self.data = {
                "filters": {"important": [], "neutral": [], "blocked": []},
                "reminders": {},
                "diary": []
            }
        except Exception as e:
            logger.error(f"DB Load Error: {str(e)}")

@loader.tds
class HikkaGuardianMod(loader.Module):
    """Digital Sanctuary for Introverts"""
    strings = {
        "name": "HikkaGuardian",
        "meal": "🍱 Time to eat! Suggested meal: {}",
        "sleep": "🌙 Wind down for sleep. Ideal temp: {}°C",
        "filter_help": "🚫 Format: .hgfilter <type> <words>",
        "diary_added": "📔 Diary entry encrypted",
        "stats": """🌸 **Your Stats**
        Entries: {}
        Important: {}
        Blocked: {}"""
    }

    __dependencies__ = ["cryptography"]

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MEAL_TIMES", ["10:00", "13:00", "19:00"], 
            "Meal reminder schedule",
            "SLEEP_TIME", "23:00", 
            "Bedtime reminder",
            "AUTO_DELETE", True,
            "Enable message filtering"
        )
        self.db = HikkaGuardianDB()
        self.reminder_task = None

    async def client_ready(self, client, db):
        self.client = client
        self._start_reminders()

    def _start_reminders(self):
        async def reminder_cycle():
            while True:
                try:
                    now = datetime.now().strftime("%H:%M")
                    if now in self.config["MEAL_TIMES"]:
                        await self.client.send_message(
                            "me",
                            self.strings("meal").format("rice bowl with veggies")
                        )
                    if now == self.config["SLEEP_TIME"]:
                        await self.client.send_message(
                            "me",
                            self.strings("sleep").format(22)
                        )
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Reminder Error: {str(e)}")
                    await asyncio.sleep(300)

        if not self.reminder_task or self.reminder_task.done():
            self.reminder_task = asyncio.create_task(reminder_cycle())

    async def watcher(self, message: Message):
        """Message filtering system"""
        try:
            if not isinstance(message.peer_id, PeerUser):
                return

            if self.config["AUTO_DELETE"]:
                text = (message.text or "").lower()
                blocked_pattern = re.compile(
                    "|".join(map(re.escape, self.db.data["filters"]["blocked"])),
                    flags=re.IGNORECASE
                )
                if blocked_pattern.search(text):
                    await message.delete()
                    await self.client.send_message(
                        "me",
                        f"🚫 Deleted message containing sensitive content"
                    )

            sender = await message.get_sender()
            if str(sender.id) in self.db.data["filters"]["important"]:
                await message.pin()

        except Exception as e:
            logger.error(f"Watcher Error: {str(e)}")

    @loader.unrestricted
    async def hgfiltercmd(self, message: Message):
        """Manage filters"""
        try:
            args = utils.get_args_raw(message).split(" ", 1)
            if len(args) < 2:
                await utils.answer(message, self.strings("filter_help"))
                return

            f_type, content = args
            if f_type not in self.db.data["filters"]:
                await utils.answer(
                    message,
                    f"Invalid type! Available: {', '.join(self.db.data['filters'])}"
                )
                return

            self.db.data["filters"][f_type] = [
                item.strip() for item in content.split(",")
            ]
            self.db.save()
            await utils.answer(message, f"✅ {f_type.capitalize()} filter updated")

        except Exception as e:
            logger.error(f"Filter Error: {str(e)}")
            await utils.answer(message, "❌ Filter update failed")

    @loader.unrestricted
    async def hgdiarycmd(self, message: Message):
        """Add diary entry"""
        try:
            entry = utils.get_args_raw(message)
            if not entry:
                await utils.answer(message, "📝 Please provide diary text")
                return

            self.db.data["diary"].append({
                "date": datetime.now().isoformat(),
                "text": entry
            })
            self.db.save()
            await utils.answer(message, self.strings("diary_added"))

        except Exception as e:
            logger.error(f"Diary Error: {str(e)}")
            await utils.answer(message, "❌ Failed to save entry")

    @loader.unrestricted
    async def hgstatcmd(self, message: Message):
        """View stats"""
        try:
            stats = self.strings("stats").format(
                len(self.db.data["diary"]),
                len(self.db.data["filters"]["important"]),
                len(self.db.data["filters"]["blocked"])
            )
            await utils.answer(message, stats)
        except Exception as e:
            logger.error(f"Stats Error: {str(e)}")
            await utils.answer(message, "❌ Failed to load stats")

async def setup(client):
    await client.load_module(HikkaGuardianMod())
