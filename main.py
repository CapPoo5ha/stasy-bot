# main.py — с подготовкой рассылки + кнопка PDF в рассылке
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

load_dotenv()

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')        # @your_channel
MATERIAL_URL = os.getenv('MATERIAL_URL')                # из .env
PRIVATE_CHAT = os.getenv('PRIVATE_CHAT')                # из .env

if not all([TOKEN, CHANNEL_USERNAME, MATERIAL_URL, PRIVATE_CHAT]):
    raise ValueError("Проверь .env: TOKEN, CHANNEL_USERNAME, MATERIAL_URL, PRIVATE_CHAT обязательны!")
   
DATA_FILE = 'users.json'
PHOTO_PATH = "welcome.jpg"
PDF_PATH = "marketing2026.pdf"

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
    "Я Настя — маркетолог-стратег, и в этой сфере варюсь уже более 3 лет:\n\n"
    "\U0001F968 работала на фрилансе в 20+ нишах\n"
    "\U0001F968 работала в креативном маркетинговом агентстве с федеральными и международными заказчиками\n"
    "\U0001F968 разработала 100+ рекламных кампаний и десятки масштабных стратегий\n\n"
    "\U0001F4CE Здесь я делюсь разными полезностями, которые можно забрать бесплатно\n\n"
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
        [InlineKeyboardButton(text="Шаблон анализа ЦА", callback_data="get_template")],
        [InlineKeyboardButton(text="Тренды 2026 + план", callback_data="get_dj")],
        [InlineKeyboardButton(text="Бесплатный мини-аудит ЦА", callback_data="get_audit")],
        [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:] if CHANNEL_USERNAME.startswith('@') else CHANNEL_USERNAME}")]
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

# ==================== ЗАБРАТЬ ШАБЛОН (кнопкой) ====================
@dp.callback_query(F.data == "get_template")
async def get_template(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await callback.message.answer(
                "Готово! Вот твой шаблон для аналитики ЦА:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть шаблон", url=MATERIAL_URL)]
                ])
            )
            data['users'][str(user_id)]['has_material'] = True
            data['stats']['materials'] = data['stats'].get('materials', 0) + 1
            save_data(data)
        else:
            await callback.message.answer(
                f"Сначала подпишись на {CHANNEL_USERNAME}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="Я подписался — проверить", callback_data="get_template")]
                ])
            )
    except Exception:
        await callback.message.answer("Ошибка проверки подписки")
    await callback.answer()

# ==================== ТРЕНДЫ 2026 + ПЛАН (PDF) ====================
@dp.callback_query(F.data == "get_dj")
async def get_dj(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            if os.path.exists(PDF_PATH):
                #await callback.message.chat.send_chat_action("upload_document")
                await callback.message.answer_document(
                    document=FSInputFile(PDF_PATH),
                    caption="Готово! Тут я собрала тренды маркетинга в 2026 и план:\n\nСохрани и используй!",
                )
                data['users'][str(user_id)]['has_pdf'] = True
                data['stats']['materials'] = data['stats'].get('materials', 0) + 1
                save_data(data)
            else:
                await callback.message.answer("Ошибка: PDF-файл не найден на сервере")
        else:
            # Не подписан — показываем кнопки подписки
            await callback.message.answer(
                f"Сначала подпишись на {CHANNEL_USERNAME}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="Я подписался — проверить", callback_data="get_dj")]
                ])
            )
    except Exception as e:
        # Любая ошибка API (бот не админ, канал недоступен и т.д.)
        await callback.message.answer(
            "Не удалось проверить подписку. Убедись, что ты подписан на канал\n"
            "Попробуй позже или напиши" "/start"
        )
        print(f"Ошибка get_chat_member: {e}")  # для логов на сервере
    await callback.answer()

# ==================== МИНИ-АУДИТ ====================
@dp.callback_query(F.data == "get_audit")
async def get_audit(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await callback.message.answer(
                "Подписка подтверждена!\n\nНапиши мне в личку — сделаю мини-аудит твоей ЦА бесплатно:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Написать в личку", url=PRIVATE_CHAT)]
                ])
            )
            data['stats']['audits'] = data['stats'].get('audits', 0) + 1
            save_data(data)
        else:
            await callback.message.answer(
                f"Сначала подпишись на {CHANNEL_USERNAME}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="Я подписался — проверить", callback_data="get_audit")]
                ])
            )
    except Exception:
        await callback.message.answer("Ошибка проверки подписки")
    await callback.answer()

# ==================== ПОДГОТОВКА РАССЫЛКИ ====================
broadcast_pending = False  # флаг ожидания текста

@dp.message(Command('prepare_broadcast'))
async def prepare_broadcast(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return await message.answer("Доступ запрещён — только админ")
    global broadcast_pending
    broadcast_pending = True
    await message.answer("Отправь текст для рассылки.\nЯ добавлю кнопку «Тренды 2026 + план» (PDF).")

@dp.message(F.text & ~F.command)  # ловим обычный текст
async def receive_broadcast_text(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return
    global broadcast_pending
    if broadcast_pending:
        text = message.text
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Тренды 2026 + план", callback_data="get_dj")]
        ])
        sent = failed = 0
        for uid in list(data['users'].keys()):
            try:
                await bot.send_message(int(uid), text, reply_markup=markup, parse_mode='HTML')
                sent += 1
            except:
                failed += 1
        data['stats']['broadcasts'] = data['stats'].get('broadcasts', 0) + 1
        save_data(data)
        await message.answer(f"Рассылка завершена!\nОтправлено: {sent}\nОшибок/блоков: {failed}")
        broadcast_pending = False

# ==================== СТАТИСТИКА ====================
@dp.message(Command('stats'))
async def statists(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return await message.answer("Доступ к статистике запрещён — только для админа")
    total = len(data['users'])
    materials = data['stats'].get('materials', 0)
    audits = data['stats'].get('audits', 0)
    broadcasts = data['stats'].get('broadcasts', 0)  # если есть рассылки
    await message.answer(
        f"Пользователей: {total}\n"
        f"Шаблонов выдано: {materials}\n"
        f"Запросов аудита: {audits}\n"
        f"Рассылок проведено: {broadcasts}"
    )

# ==================== ПОМОЩЬ ДЛЯ АДМИНА ====================
@dp.message(Command('hell'))
async def admin_hell(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return await message.answer("Нет доступа")
    total = len(data['users'])
    help_text = (
        "<b>Админ-панель бота</b>\n\n"
        "/stats — Статистика пользователей и выдач\n"
        "/prepare_broadcast — Подготовить рассылку всем (с кнопкой PDF)\n"
        "/test_broadcast <user_id> — Тестовая рассылка одному человеку\n"
        "/help — Это справочное сообщение\n\n"
        "Удачной работы!"
    )
    await message.answer( f"Пользователей: {total}\n")
    await message.answer( help_text, parse_mode='HTML')

 # ==================== ОБЩИЙ ЛОВЕЦ (ВСЕГДА В КОНЦЕ!) ====================
@dp.message()  # ловит только то, что не попало в команды выше
async def catch_all(message: Message):
    # Игнорируем системные и не-текстовые сообщения
    if message.content_type != 'text':
        return
    # Если это команда — она уже обработана выше
    await start_handler(message)   

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