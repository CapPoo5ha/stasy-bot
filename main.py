import asyncio
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv  # pip install python-dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError

# ===== ЗАГРУЗКА КОНФИГУРАЦИИ =====
load_dotenv()  # Читает .env файл

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
MATERIAL_URL = os.getenv('MATERIAL_URL')

# Проверка, что всё загрузилось
if not all([TOKEN, ADMIN_ID, CHANNEL_USERNAME, MATERIAL_URL]):
    raise ValueError("❌ Проверь .env файл! Все поля обязательны.")

DATA_FILE = 'users.json'

# ===== ИСПРАВЛЕНИЕ ДЛЯ WINDOWS =====
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Загрузка/сохранение данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'users': {}, 'stats': {'materials': 0, 'broadcasts': 0}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

@dp.message(Command('start'))
async def start_handler(message: Message):
    user_id = message.chat.id
    if str(user_id) not in data['users']:
        data['users'][str(user_id)] = {
            'first_interaction': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'has_material': False  # Новый флаг по умолчанию
        }
    else:
        data['users'][str(user_id)]['last_activity'] = datetime.now().isoformat()
    save_data(data)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Получить полезный материал", callback_data="check_subscription")]
    ])
    
    await message.answer(
        f"👋 Привет!\n\n"
        f"Подпишись на канал <b>{CHANNEL_USERNAME}</b> и нажми кнопку, "
        f"чтобы получить эксклюзивный материал по маркетингу! 🚀",
        reply_markup=markup,
        parse_mode='HTML'
    )

@dp.callback_query(F.data == 'check_subscription')
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)
    
    # Инициализируем пользователя, если нет
    if user_key not in data['users']:
        data['users'][user_key] = {
            'first_interaction': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'has_material': False
        }
        save_data(data)
    
    user_data = data['users'][user_key]
    
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        is_subscribed = member.status in ['member', 'administrator', 'creator']
        
        # Логика блокировки:
        # - Если подписан И НЕ имеет материал — выдаём
        # - Если подписан И имеет материал — напоминаем, что уже получил
        # - Если НЕ подписан И имеет материал — блокируем, пока не переподпишется (флаг не сбрасывается)
        # - Если НЕ подписан И НЕ имеет — стандартно просим подписаться
        
        if is_subscribed:
            # Сброс флага при переподписке (если был отписан)
            if user_data.get('has_material', False):
                user_data['has_material'] = False
                save_data(data)
                await callback.message.answer(
                    "🎉 <b>Добро пожаловать обратно!</b>\n\n"
                    "Вы переподписались — вот свежий материал заново:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📖 Получить материал", url=MATERIAL_URL)]
                    ]),
                    parse_mode='HTML'
                )
                return
            
            if not user_data.get('has_material', False):
                # Выдаём материал
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📖 Получить материал", url=MATERIAL_URL)]
                ])
                
                await callback.message.answer(
                    "✅ <b>Вы подписаны!</b>\n\n"
                    f"Вот ваш полезный материал по маркетингу и ботам Telegram:",
                    reply_markup=markup,
                    parse_mode='HTML'
                )
                
                # Устанавливаем флаг
                user_data['has_material'] = True
                user_data['received_material'] = datetime.now().isoformat()
                data['stats']['materials'] += 1
                save_data(data)
            else:
                # Уже имеет материал
                await callback.message.answer(
                    "✅ <b>Вы подписаны!</b>\n\n"
                    "Вы уже получали этот материал ранее. "
                    "Хотите что-то новое? Следите за обновлениями в канале! 🚀",
                    parse_mode='HTML'
                )
        else:
            # Не подписан
            if user_data.get('has_material', False):
                await callback.message.answer(
                    "🔒 <b>Материал заблокирован!</b>\n\n"
                    f"Вы уже получали его, но отписались от {CHANNEL_USERNAME}. "
                    "Подпишитесь заново, чтобы разблокировать доступ! ✨",
                    parse_mode='HTML'
                )
            else:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"📢 Подписаться на {CHANNEL_USERNAME}", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_subscription")]
                ])
                
                await callback.message.answer(
                    f"❌ <b>Вы не подписаны</b> на канал {CHANNEL_USERNAME}\n\n"
                    "Подпишись и нажми 'Проверить подписку' ещё раз! ✨",
                    reply_markup=markup,
                    parse_mode='HTML'
                )
    
    except Exception as e:
        await callback.message.answer(
            f"⚠️ Ошибка проверки. Убедись, что бот — админ в канале.\n"
            f"Детали: {str(e)}"
        )
    
    await callback.answer()

# ===== ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ =====
@dp.message(Command('broadcast'))
async def broadcast_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Только админ!")
    
    if len(message.text.split()) < 2:
        await message.answer(
            "📤 <b>Рассылка</b>\n\n"
            "Используй: <code>/broadcast Твой текст здесь</code>",
            parse_mode='HTML'
        )
        return
    
    text = message.text.split(maxsplit=1)[1]
    active_users = [int(uid) for uid in data['users'].keys()]
    sent_count = 0
    failed_count = 0
    
    for user_id in active_users:
        try:
            await bot.send_message(user_id, text)
            sent_count += 1
        except TelegramForbiddenError:
            failed_count += 1
            del data['users'][str(user_id)]
        except Exception:
            failed_count += 1
    
    # Статистика
    data['stats']['broadcasts'] += 1
    data['stats']['last_broadcast'] = datetime.now().isoformat()
    save_data(data)
    
    await message.answer(
        f"📤 <b>Рассылка завершена!</b>\n\n"
        f"✅ Отправлено: {sent_count}\n"
        f"❌ Ошибок: {failed_count}\n"
        f"👥 Осталось активных: {len(data['users'])}",
        parse_mode='HTML'
    )

@dp.message(Command('stats'))
async def stats_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Только админ!")
    
    total_users = len(data['users'])
    materials_sent = data['stats'].get('materials', 0)
    broadcasts = data['stats'].get('broadcasts', 0)
    
    # Активные за 30 дней + с материалом
    active_30d = sum(1 for user in data['users'].values() 
                     if 'received_material' in user and 
                     datetime.now() - datetime.fromisoformat(user['received_material']) < timedelta(days=30))
    
    has_material_count = sum(1 for user in data['users'].values() if user.get('has_material', False))
    
    last_broadcast = data['stats'].get('last_broadcast', 'Никогда')
    if last_broadcast != 'Никогда':
        last_broadcast = datetime.fromisoformat(last_broadcast).strftime('%d.%m.%Y %H:%M')
    
    stats_text = (
        f"📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📚 Материалов выдано: {materials_sent}\n"
        f"🔒 Получили материал: {has_material_count}\n"
        f"📤 Рассылок проведено: {broadcasts}\n"
        f"🔥 Активных (30 дней): {active_30d}\n\n"
        f"⏰ Последняя рассылка: {last_broadcast}"
    )
    
    await message.answer(stats_text, parse_mode='HTML')

@dp.message(Command('schedule'))
async def schedule_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Только админ!")
    
    if len(message.text.split()) < 3:
        await message.answer(
            "⏰ <b>Отложенная рассылка</b>\n\n"
            "Формат: <code>/schedule HH:MM текст</code>\n"
            "Пример: <code>/schedule 18:00 Привет, это тест!</code>",
            parse_mode='HTML'
        )
        return
    
    parts = message.text.split(maxsplit=2)
    time_str, text = parts[1], parts[2]
    
    try:
        hour, minute = map(int, time_str.split(':'))
        now = datetime.now()
        scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if scheduled_time <= now:
            scheduled_time += timedelta(days=1)
        
        asyncio.create_task(send_scheduled_broadcast(scheduled_time, text))
        
        await message.answer(
            f"⏰ Рассылка запланирована на <b>{scheduled_time.strftime('%H:%M %d.%m.%Y')}</b>!\n"
            f"📝 Текст: <code>{text[:50]}...</code>",
            parse_mode='HTML'
        )
        
    except ValueError:
        await message.answer("❌ Неверный формат времени! Используй HH:MM")

async def send_scheduled_broadcast(scheduled_time, text):
    delay = (scheduled_time - datetime.now()).total_seconds()
    await asyncio.sleep(delay)
    
    active_users = [int(uid) for uid in data['users'].keys()]
    sent_count = 0
    
    for user_id in active_users:
        try:
            await bot.send_message(user_id, text)
            sent_count += 1
        except:
            pass
    
    data['stats']['broadcasts'] += 1
    data['stats']['last_broadcast'] = scheduled_time.isoformat()
    save_data(data)
    
    print(f"⏰ Отложенная рассылка отправлена в {scheduled_time}! 👥 {sent_count} получателей")

@dp.message(Command('help'))
async def help_handler(message: Message):
    help_text = (
        f"🤖 <b>Помощь по боту @{CHANNEL_USERNAME}</b>\n\n"
        "/start - Начать работу\n"
        "/help - Это сообщение\n\n"
        f"📤 <b>Для админа:</b>\n"
        "/broadcast Текст - Мгновенная рассылка\n"
        "/schedule HH:MM Текст - Отложенная рассылка\n"
        "/stats - Полная статистика"
    )
    
    await message.answer(help_text, parse_mode='HTML')

async def main():
    print("🤖 Бот запущен!")
    print(f"📢 Канал: {CHANNEL_USERNAME}")
    print(f"👤 Админ: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())