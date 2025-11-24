# main.py — финальная версия 2025
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

load_dotenv()

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')      # @твой_канал
MATERIAL_URL = "https://xmind.ai/share/rvBYg697"
PRIVATE_CHAT = "https://t.me/Meilleur_amie"          # ← замени на свой!

if not all([TOKEN, ADMIN_ID, CHANNEL_USERNAME]):
    raise ValueError("Проверь переменные в Render!")

DATA_FILE = 'users.json'
PHOTO_PATH = "welcome.jpg"        # твоё красивое фото

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bot = Bot(token=TOKEN)
dp = Dispatcher()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'users': {}, 'stats': {'materials': 0, 'audits': 0, 'broadcasts': 0}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ==================== ПРИВЕТСТВИЕ ====================
WELCOME_TEXT = (
    "<b>Приветствую тебя, маркетинговый и креативный энтузиаст!</b>\n\n"
    "Я Настя — маркетолог-стратег, и в этой сфере варюсь уже более 3 лет:\n"
    "работала на фрилансе в более 30 нишах\n"
    "работала в креативном маркетинговом агентстве с федеральными и международными заказчиками\n"
    "разработала 100+ рекламных кампаний и десятки масштабных стратегий\n\n"
    "Забирай шаблон, без которого я не сажусь за аналитику ЦА. Или мини-аудит своей ЦА\n\n"
    "<b>Чтобы забрать — подпишись сперва на канал!</b>"
)

@dp.message(Command('start'))
async def start_handler(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in data['users']:
        data['users'][user_id] = {'first_interaction': datetime.now().isoformat(), 'has_material': False}
    data['users'][user_id]['last_activity'] = datetime.now().isoformat()
    save_data(data)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Забрать шаблон", callback_data="get_template")],
        [InlineKeyboardButton(text="Получить мини-аудит ЦА", callback_data="get_audit")],
        [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
    ])

    # Стикер + фото + текст + кнопки
    await message.answer_sticker("CAACAgIAAxkBAAEL9n1m2yAAAd4x8JAAAg1fX8v5v6vAAQIAA8AAAkmuWsHGikU7cGpqNTAE")
    if os.path.exists(PHOTO_PATH):
        await message.answer_photo(
            photo=FSInputFile(PHOTO_PATH),
            caption=WELCOME_TEXT,
            reply_markup=markup,
            parse_mode='HTML'
        )
    else:
        await message.answer(WELCOME_TEXT, reply_markup=markup, parse_mode='HTML')

# ==================== ЗАБРАТЬ ШАБЛОН ====================
@dp.callback_query(F.data == "get_template")
async def get_template(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await callback.message.answer(
                "Готово! Вот твой шаблон для аналитики ЦА:\n\n"
                f"<code>{MATERIAL_URL}</code>\n\n"
                "Сохрани и пользуйся!",
                parse_mode='HTML', disable_web_page_preview=True
            )
            data['users'][str(user_id)]['has_material'] = True
            data['stats']['materials'] = data['stats'].get('materials', 0) + 1
            save_data(data)
        else:
            await callback.message.answer(
                f"Ты ещё не подписан на {CHANNEL_USERNAME}\n\n"
                "Подпишись и нажми кнопку заново",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="Проверить подписку", callback_data="get_template")]
                ])
            )
    except Exception as e:
        await callback.message.answer("Ошибка проверки")
    await callback.answer()

# ==================== МИНИ-АУДИТ ====================
@dp.callback_query(F.data == "get_audit")
async def get_audit(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await callback.message.answer_sticker("CAACAgIAAxkBAAEL9oFm2yAAAd5N8JAAAg2vX8v5v6vAAQIAA8AAAkmuWsHGikU7cGpqNTAE")
            await callback.message.answer(
                "Подписка подтверждена!\n\n"
                "Напиши мне в личку — я сделаю мини-аудит твоей ЦА бесплатно:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Написать мне в личку", url=PRIVATE_CHAT)]
                ])
            )
            data['stats']['audits'] = data['stats'].get('audits', 0) + 1
            save_data(data)
        else:
            await callback.message.answer(
                f"Сначала подпишись на {CHANNEL_USERNAME}\n\n"
                "После подписки нажми кнопку заново",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="Проверить подписку", callback_data="get_audit")]
                ])
            )
    except Exception as e:
        await callback.message.answer("Ошибка проверки")
    await callback.answer()

# ==================== АДМИНКА ====================
@dp.message(Command('stats'))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID: return
    total = len(data['users'])
    templates = data['stats'].get('materials', 0)
    audits = data['stats'].get('audits', 0)
    await message.answer(
        f"Пользователей: {total}\n"
        f"Выдано шаблонов: {templates}\n"
        f"Запросов мини-аудита: {audits}"
    )

# ==================== WEBHOOK ДЛЯ RENDER ====================
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