from hikkatl.types import Message
from hikka import loader, utils
import asyncio

@loader.tds
class RubenovaMod(loader.Module):
    """Выдача информации Rubenova с задержкой"""
    strings = {"name": "Rubenova"}

    @loader.command()
    async def rubenovacmd(self, message: Message):
        """- отправить дожу с задержкой"""
        await asyncio.sleep(5)
        text = """⣾Country: Беларусь,Гомель
⠀⠀⠀⠀⠀⠀⠀⢀⡾Discord name: seksualnaniebezpiecznaxd,asteriaxddlol
⠀⠀⠀⠀⠀⠀⢠⡞Number: +375256079163
⠀⠀⠀⠀⠀⣠⠟Vk: https://vk.com/id569562770
⠀⠀⠀⠀⣰⠏ФИО: Коваленко Кристина Станиславовна
⠀⠀⠀⣴⠋photo: http://postimg.su/bEK5yqiq
⠀⠀⣼⠃tiktok(old): https://tiktok.com/@6938759559214777350
⢀⣼⠃tiktok(new):https://www.tiktok.com/@imperiyakristina2007?_t=ZM-8wZSDZVbiWW&_r=1
Doxxed by Kastyan"""
        await utils.answer(message, text)
