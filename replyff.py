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
        "no_args": "❌ Укажите пользователя или ответьте на сообщение",
        "user_unlocked": "✅ Пользователь {} удалён из списка",
        "not_in_list": "❌ Пользователь не в списке отслеживания",
        "lock_list": "📝 Список отслеживаемых пользователей в чате {}:\n\n",
        "list_empty": "❌ Список отслеживания пуст для этого чата",
        "cooldown": "⏱️ Сообщение было отправлено слишком быстро после предыдущего",
        "reply_required": "❌ Ответьте на сообщение пользователя или укажите @username"
    }

    def __init__(self):
        self.locked_users = {}
        self.last_message_time = {}
        self.cooldown = 1.0
        self._me = None
        self._client = None

    async def client_ready(self, client, db):
        self.db = db
        self._client = client
        self.locked_users = self.db.get("AutoReplyLock", "locked", {})
        self._me = (await client.get_me()).id

    async def _notify(self, text: str):
        """Отправляет уведомление в избранное"""
        await self._client.send_message("me", text)

    async def lockcmd(self, message: Message):
        """Добавить пользователя в список отслеживания. Использование: .lock [@username|ответ] <текст>"""
        args = utils.get_args_raw(message)
        
        # Если есть ответ на сообщение
        if message.is_reply:
            reply = await message.get_reply_message()
            user = reply.sender
            
            # Если текст ответа не указан, используем весь текст сообщения
            if not args:
                await self._notify(self.strings("no_args"))
                return
                
            text = args
        else:
            # Обработка без ответа на сообщение
            if not args:
                await self._notify(self.strings("reply_required"))
                return
                
            try:
                # Пытаемся разделить пользователя и текст
                user_part, text = args.split(maxsplit=1)
            except ValueError:
                await self._notify(self.strings("no_args"))
                return
                
            try:
                user = await message.client.get_entity(user_part)
            except (TypeError, ValueError, UserIdInvalidError):
                await self._notify(self.strings("user_not_found"))
                return

        user_id = user.id
        chat_id = utils.get_chat_id(message)

        if str(chat_id) not in self.locked_users:
            self.locked_users[str(chat_id)] = {}

        self.locked_users[str(chat_id)][str(user_id)] = text
        self.db.set("AutoReplyLock", "locked", self.locked_users)
        
        # Получаем информацию о чате
        chat = await message.get_chat()
        chat_title = chat.title if hasattr(chat, 'title') else "Private Chat"
        
        # Отправляем уведомление в избранное
        await self._notify(
            self.strings("user_locked").format(
                f"@{user.username}" if user.username else get_display_name(user),
                text
            ) + f"\n\nЧат: {chat_title} (ID: {chat_id})"
        )

    async def unlockcmd(self, message: Message):
        """Удалить пользователя из списка отслеживания. Использование: .unlock [@username|ответ]"""
        # Если есть ответ на сообщение
        if message.is_reply:
            reply = await message.get_reply_message()
            user = reply.sender
        else:
            args = utils.get_args_raw(message)
            if not args:
                await self._notify(self.strings("reply_required"))
                return
                
            try:
                user = await message.client.get_entity(args.strip())
            except (TypeError, ValueError, UserIdInvalidError):
                await self._notify(self.strings("user_not_found"))
                return

        chat_id = utils.get_chat_id(message)
        user_id = user.id
        
        if (str(chat_id) in self.locked_users and 
            str(user_id) in self.locked_users[str(chat_id)]):
            del self.locked_users[str(chat_id)][str(user_id)]
            
            if not self.locked_users[str(chat_id)]:
                del self.locked_users[str(chat_id)]
                
            self.db.set("AutoReplyLock", "locked", self.locked_users)
            
            # Получаем информацию о чате
            chat = await message.get_chat()
            chat_title = chat.title if hasattr(chat, 'title') else "Private Chat"
            
            await self._notify(
                self.strings("user_unlocked").format(
                    f"@{user.username}" if user.username else get_display_name(user)
                ) + f"\n\nЧат: {chat_title} (ID: {chat_id})"
            )
        else:
            await self._notify(self.strings("not_in_list"))

    async def locklistcmd(self, message: Message):
        """Показать список отслеживаемых пользователей"""
        chat_id = utils.get_chat_id(message)
        chat = await message.get_chat()
        chat_title = chat.title if hasattr(chat, 'title') else "Private Chat"
        
        if str(chat_id) not in self.locked_users or not self.locked_users[str(chat_id)]:
            await self._notify(f"{self.strings('list_empty')} {chat_title} (ID: {chat_id})")
            return

        res = self.strings("lock_list").format(chat_title)
        for user_id, text in self.locked_users[str(chat_id)].items():
            try:
                user = await message.client.get_entity(int(user_id))
                name = f"@{user.username}" if user.username else get_display_name(user)
                res += f"• {name}: {text}\n"
            except: 
                res += f"• ID:{user_id}: {text}\n"

        await self._notify(res)

    @loader.watcher()
    async def watcher(self, message: Message):
        """Отслеживание сообщений с минимальной задержкой"""
        if not isinstance(message, Message) or message.out or not message.sender_id:
            return

        chat_id = utils.get_chat_id(message)
        user_id = message.sender_id
        
        if user_id <= 0:
            return

        chat_str = str(chat_id)
        user_str = str(user_id)
        
        if chat_str not in self.locked_users or user_str not in self.locked_users[chat_str]:
            return

        current_time = time.time()
        last_time = self.last_message_time.get(user_str, 0)
        
        if current_time - last_time < self.cooldown:
            return
            
        self.last_message_time[user_str] = current_time

        text = self.locked_users[chat_str][user_str]
        
        try:
            await message.client.send_message(
                entity=chat_id,
                message=text,
                reply_to=message.id
            )
        except Exception:
            pass
