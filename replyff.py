from hikkatl.types import Message
from hikkatl.utils import get_display_name
from hikkatl.errors import UserIdInvalidError
from .. import loader, utils
import time

@loader.tds
class AutoReplyLockMod(loader.Module):
    """Автоматический ответ на сообщения выбранных пользователей"""
    strings = {
        "name": "AutoReplyLock",
        "user_locked": "✅ Пользователь {} добавлен в список отслеживания с текстом: {}",
        "user_not_found": "❌ Пользователь не найден",
        "no_args": "❌ Укажите пользователя и текст ответа",
        "user_unlocked": "✅ Пользователь {} удалён из списка",
        "not_in_list": "❌ Пользователь не в списке отслеживания",
        "lock_list": "📝 Список отслеживаемых пользователей:\n\n",
        "list_empty": "❌ Список отслеживания пуст",
        "cooldown": "⏱️ Сообщение было отправлено слишком быстро после предыдущего"
    }

    def __init__(self):
        self.locked_users = {}
        self.last_message_time = {}
        self.cooldown = 1.0  # Минимальный интервал между сообщениями (в секундах)

    async def client_ready(self, client, db):
        self.db = db
        self.locked_users = self.db.get("AutoReplyLock", "locked", {})

    async def lockcmd(self, message: Message):
        """Добавить пользователя в список отслеживания. Использование: .lock @username <текст>"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return

        try:
            user, text = args.split(maxsplit=1)
        except ValueError:
            await utils.answer(message, self.strings("no_args"))
            return

        try:
            user = await message.client.get_entity(user)
        except (TypeError, ValueError, UserIdInvalidError):
            await utils.answer(message, self.strings("user_not_found"))
            return

        user_id = user.id
        chat_id = utils.get_chat_id(message)

        if str(chat_id) not in self.locked_users:
            self.locked_users[str(chat_id)] = {}

        self.locked_users[str(chat_id)][str(user_id)] = text
        self.db.set("AutoReplyLock", "locked", self.locked_users)
        
        await utils.answer(
            message,
            self.strings("user_locked").format(
                f"@{user.username}" if user.username else get_display_name(user),
                text
            )
        )

    async def unlockcmd(self, message: Message):
        """Удалить пользователя из списка отслеживания. Использование: .unlock @username"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return

        try:
            user = await message.client.get_entity(args.strip())
        except (TypeError, ValueError, UserIdInvalidError):
            await utils.answer(message, self.strings("user_not_found"))
            return

        chat_id = utils.get_chat_id(message)
        user_id = user.id
        
        if (str(chat_id) in self.locked_users and 
            str(user_id) in self.locked_users[str(chat_id)]):
            del self.locked_users[str(chat_id)][str(user_id)]
            
            if not self.locked_users[str(chat_id)]:
                del self.locked_users[str(chat_id)]
                
            self.db.set("AutoReplyLock", "locked", self.locked_users)
            await utils.answer(
                message,
                self.strings("user_unlocked").format(
                    f"@{user.username}" if user.username else get_display_name(user)
                )
            )
        else:
            await utils.answer(message, self.strings("not_in_list"))

    async def locklistcmd(self, message: Message):
        """Показать список отслеживаемых пользователей"""
        chat_id = utils.get_chat_id(message)
        if str(chat_id) not in self.locked_users or not self.locked_users[str(chat_id)]:
            await utils.answer(message, self.strings("list_empty"))
            return

        res = self.strings("lock_list")
        for user_id, text in self.locked_users[str(chat_id)].items():
            try:
                user = await message.client.get_entity(int(user_id))
                name = f"@{user.username}" if user.username else get_display_name(user)
                res += f"• {name}: {text}\n"
            except: 
                res += f"• ID:{user_id}: {text}\n"

        await utils.answer(message, res)

    @loader.watcher()
    async def watcher(self, message: Message):
        """Отслеживание сообщений с минимальной задержкой"""
        # Игнорируем служебные сообщения и свои собственные
        if not isinstance(message, Message) or message.out or not message.sender_id:
            return

        chat_id = utils.get_chat_id(message)
        user_id = message.sender_id
        
        # Игнорируем ботов и каналы
        if user_id <= 0:
            return

        # Проверяем наличие пользователя в списке
        chat_str = str(chat_id)
        user_str = str(user_id)
        
        if chat_str not in self.locked_users or user_str not in self.locked_users[chat_str]:
            return

        # Проверка кулдауна
        current_time = time.time()
        last_time = self.last_message_time.get(user_str, 0)
        
        if current_time - last_time < self.cooldown:
            # Можно добавить логирование, но не отправляем сообщение
            return
            
        self.last_message_time[user_str] = current_time

        # Получаем текст ответа
        text = self.locked_users[chat_str][user_str]
        
        # Отправляем ответ напрямую через клиент (минимальная задержка)
        try:
            await message.client.send_message(
                entity=chat_id,
                message=text,
                reply_to=message.id
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем работу
            pass
