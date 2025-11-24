# main.py — финальная версия с фото + 3 кнопками + webhook для Render
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
from aiogram.exceptions import TelegramForbiddenError

# ==================== КОНФИГ ====================
load_dotenv()

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')      # например @stasyanastasie
MATERIAL_URL = "https://xmind.ai/share/rvBYg697"       # шаблон
PRIVATE_CHAT = "https://t.me/Meilleur_amie"                 # ← замени на свой личный чат

if not all([TOKEN, ADMIN_ID, CHANNEL_USERNAME]):
    raise ValueError("Проверь переменные в Render!")

DATA_FILE = 'users.json'
PHOTO_PATH = "welcome.jpg"      # фото обязательно должно быть в корне проекта

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==================== БАЗА ====================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'users': {}, 'stats': {'materials': 0, 'broadcasts': 0}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ==================== ПРИВЕТСТВИЕ ====================
WELCOME_TEXT = (
    "Приветствую тебя, маркетинговый и креативный энтузиаст!\n\n"
    "Я Настя — маркетолог-стратег, и в этой сфере варюсь уже более 3 лет:\n"
    "работала на фрилансе в более 30 нишах\n"
    "работала в креативном маркетинговом агентстве с федеральными и международными заказчиками\n"
    "разработала 100+ рекламных кампаний и десятки масштабных стратегий\n\n"
    "Забирай шаблон, без которого я не сажусь за аналитику ЦА. Или мини-аудит своей ЦА\n\n"
    "Чтобы забрать — подпишись сперва на канал!"
)

@dp.message(Command('start'))
async def start_handler(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in data['users']:
        data['users'][user_id] = {
            'first_interaction': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'has_material': False
        }
    save_data(data)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Забрать шаблон", callback_data="get_template")],
        [InlineKeyboardButton(text="Получить мини-аудит", url=PRIVATE_CHAT)],
        [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
    ])

    if os.path.exists(PHOTO_PATH):
        await message.answer_photo(
            photo=FSInputFile(PHOTO_PATH),
            caption=WELCOME_TEXT,
            reply_markup=markup,
            parse_mode='HTML'
        )
    else:
        await message.answer(WELCOME_TEXT, reply_markup=markup, parse_mode='HTML')

# ==================== ПОЛУЧИТЬ ШАБЛОН (с проверкой подписки) ====================
@dp.callback_query(F.data == "get_template")
async def get_template(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            # подписан — выдаём
            await callback.message.answer(
                "Готово! Вот твой шаблон для аналитики ЦА:\n\n"
                f"<code>{MATERIAL_URL}</code>\n\n"
                "Сохрани и пользуйся на здоровье!",
                parse_mode='HTML', disable_web_page_preview=True
            )
            data['users'][user_key]['has_material'] = True
            data['stats']['materials'] = data['stats'].get('materials', 0) + 1
            save_data(data)
        else:
            # не подписан
            await callback.message.answer(
                f"Ты ещё не подписан на {CHANNEL_USERNAME}\n\n"
                "Подпишись по кнопке ниже и нажми «Забрать шаблон» ещё раз",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="Я подписался — проверить", callback_data="get_template")]
                ])
            )
    except Exception as e:
        await callback.message.answer("Ошибка проверки подписки, попробуй позже")

    await callback.answer()

# ==================== АДМИНКА ====================
@dp.message(Command('broadcast'))
async def broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return
    if len(message.text.split()) < 2: 
        return await message.answer("Использование: /broadcast текст")
    text = message.text.split(maxsplit=1)[1]
    sent = failed = 0
    for uid in list(data['users'].keys()):
        try:
            await bot.send_message(int(uid), text)
            sent += 1
        except TelegramForbiddenError:
            del data['users'][uid]
            failed += 1
        except:
            failed += 1
    data['stats']['broadcasts'] = data['stats'].get('broadcasts', 0) + 1
    save_data(data)
    await message.answer(f"Отправлено: {sent}\nОшибок/блоков: {failed}")

@dp.message(Command('stats'))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID: return
    total = len(data['users'])
    materials = data['stats'].get('materials', 0)
    await message.answer(f"Всего пользователей: {total}\nВыдано шаблонов: {materials}")

# ==================== WEBHOOK ДЛЯ RENDER (решает ошибку портов) ====================
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

async def main():
    port = int(os.getenv("PORT", 10000))
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot.set_webhook(url=webhook_url)
    
    print(f"Бот запущен на {webhook_url}")
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())