import asyncio
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError

# ===== ЗАГРУЗКА КОНФИГУРАЦИИ =====
load_dotenv()

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
MATERIAL_URL = os.getenv('MATERIAL_URL')

if not all([TOKEN, ADMIN_ID, CHANNEL_USERNAME, MATERIAL_URL]):
    raise ValueError("❌ Проверь .env файл! Все поля обязательны.")

DATA_FILE = 'users.json'

# ===== ИСПРАВЛЕНИЕ ДЛЯ WINDOWS + RENDER =====
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ===== ПОРТ ДЛЯ RENDER =====
PORT = int(os.getenv('PORT', 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== РАБОТА С ДАННЫМИ =====
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
    user_key = str(user_id)
    
    if user_key not in data['users']:
        data['users'][user_key] = {
            'first_interaction': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'has_material': False
        }
    else:
        data['users'][user_key]['last_activity'] = datetime.now().isoformat()
    
    save_data(data)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Проверить подписку", callback_data="check_subscription")]
    ])
    
    await message.answer(
        f"👋 <b>Привет!</b>\n\n"
        f"Подпишись на канал <b>{CHANNEL_USERNAME}</b> и нажми кнопку,\n"
        f"чтобы получить эксклюзивный материал по маркетингу! 🚀",
        reply_markup=markup,
        parse_mode='HTML'
    )

@dp.callback_query(F.data == 'check_subscription')
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)
    
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
        
        if is_subscribed:
            # СБРОС ФЛАГА при переподписке
            if user_data.get('has_material', False) and not is_subscribed:
                user_data['has_material'] = False
                save_data(data)
            
            # Показываем кнопку ПОЛУЧИТЬ МАТЕРИАЛ (проверка при клике)
            material_btn_text = "🔓 Получить материал" if not user_data.get('has_material', False) else "🔓 Получить заново"
            
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=material_btn_text, callback_data="get_material")]
            ])
            
            status_text = "новичок" if not user_data.get('has_material', False) else "вернулся"
            await callback.message.answer(
                f"✅ <b>Вы подписаны!</b>\n\n"
                f"Нажмите кнопку — <b>подписка проверится заново</b> при получении:\n"
                f"• Материал для {status_text} ✨",
                reply_markup=markup,
                parse_mode='HTML'
            )
            
        else:
            # НЕ ПОДПИСАН
            if user_data.get('has_material', False):
                await callback.message.answer(
                    f"🔒 <b>Материал заблокирован!</b>\n\n"
                    f"Вы получили его ранее, но отписались от {CHANNEL_USERNAME}.\n"
                    f"<b>Подпишитесь заново</b> для разблокировки! 🔓",
                    parse_mode='HTML'
                )
            else:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"📢 Подписаться на {CHANNEL_USERNAME}", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_subscription")]
                ])
                
                await callback.message.answer(
                    f"❌ <b>Вы не подписаны</b> на {CHANNEL_USERNAME}\n\n"
                    "1️⃣ Подпишитесь по кнопке\n"
                    "2️⃣ Нажмите 'Проверить подписку'",
                    reply_markup=markup,
                    parse_mode='HTML'
                )
    
    except Exception as e:
        await callback.message.answer(
            f"⚠️ <b>Ошибка проверки</b>\n\n"
            f"Убедись, что бот — <b>админ</b> в канале.\n"
            f"Детали: <code>{str(e)}</code>",
            parse_mode='HTML'
        )
    
    await callback.answer()

@dp.callback_query(F.data == 'get_material')
async def get_material(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)
    user_data = data['users'].get(user_key, {})
    
    try:
        # КРИТИЧЕСКАЯ ПРОВЕРКА ПОДПИСКИ ПРЯМО ПРИ КЛИКЕ
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        is_subscribed = member.status in ['member', 'administrator', 'creator']
        
        if is_subscribed:
            # ✅ ПОДПИСКА АКТИВНА — ВЫДАЁМ МАТЕРИАЛ КАК ТЕКСТ
            await callback.message.answer(
                f"🎉 <b>ПОДПИСКА ПОДТВЕРЖДЕНА!</b>\n\n"
                f"📚 <b>Ваш эксклюзивный материал:</b>\n"
                f"<code>{MATERIAL_URL}</code>\n\n"
                f"💡 Сохраните ссылку! Оставайтесь подписанным за обновлениями 🚀",
                parse_mode='HTML'
            )
            
            # Обновляем статистику
            user_data['has_material'] = True
            user_data['received_material'] = datetime.now().isoformat()
            data['stats']['materials'] += 1
            save_data(data)
            
        else:
            # ❌ ОТПИСАЛСЯ ПОСЛЕ КНОПКИ ПРОВЕРКИ
            await callback.message.answer(
                f"🚫 <b>ОШИБКА! Вы отписались!</b>\n\n"
                f"Материал <b>ЗАБЛОКИРОВАН</b>.\n\n"
                f"🔄 <b>Подпишитесь заново</b> на {CHANNEL_USERNAME}\n"
                f"   ↓ Нажмите /start для разблокировки",
                parse_mode='HTML'
            )
    
    except Exception as e:
        await callback.message.answer(
            f"⚠️ <b>Ошибка получения</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"Попробуйте /start"
        )
    
    await callback.answer()

@dp.message(Command('broadcast'))
async def broadcast_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Только админ!</b>")
    
    if len(message.text.split()) < 2:
        await message.answer(
            "📤 <b>РАССЫЛКА</b>\n\n"
            "<code>/broadcast Ваш текст здесь</code>",
            parse_mode='HTML'
        )
        return
    
    text = message.text.split(maxsplit=1)[1]
    active_users = [int(uid) for uid in data['users'].keys()]
    sent_count = failed_count = 0
    
    for user_id in active_users:
        try:
            await bot.send_message(user_id, text)
            sent_count += 1
        except TelegramForbiddenError:
            del data['users'][str(user_id)]
            failed_count += 1
        except:
            failed_count += 1
    
    data['stats']['broadcasts'] += 1
    data['stats']['last_broadcast'] = datetime.now().isoformat()
    save_data(data)
    
    await message.answer(
        f"📤 <b>РАССЫЛКА ОКОНЧЕНА</b>\n\n"
        f"✅ <b>Отправлено:</b> {sent_count}\n"
        f"❌ <b>Ошибок:</b> {failed_count}\n"
        f"👥 <b>Активных:</b> {len(data['users'])}",
        parse_mode='HTML'
    )

@dp.message(Command('schedule'))
async def schedule_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Только админ!</b>")
    
    if len(message.text.split()) < 3:
        await message.answer(
            "⏰ <b>ОТЛОЖЕННАЯ РАССЫЛКА</b>\n\n"
            "<code>/schedule HH:MM текст</code>\n\n"
            "<i>Пример: /schedule 18:00 Привет!</i>",
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
            f"⏰ <b>Запланировано!</b>\n\n"
            f"📅 <b>{scheduled_time.strftime('%d.%m.%Y %H:%M')}</b>\n"
            f"📝 <i>{text[:50]}...</i>",
            parse_mode='HTML'
        )
        
    except:
        await message.answer("❌ <b>Формат:</b> HH:MM")

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

@dp.message(Command('stats'))
async def stats_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Только админ!</b>")
    
    total_users = len(data['users'])
    materials_sent = data['stats'].get('materials', 0)
    broadcasts = data['stats'].get('broadcasts', 0)
    has_material_count = sum(1 for user in data['users'].values() if user.get('has_material', False))
    
    active_30d = sum(1 for user in data['users'].values() 
                     if 'received_material' in user and 
                     datetime.now() - datetime.fromisoformat(user['received_material']) < timedelta(days=30))
    
    last_broadcast = data['stats'].get('last_broadcast', 'Никогда')
    if last_broadcast != 'Никогда':
        last_broadcast = datetime.fromisoformat(last_broadcast).strftime('%d.%m.%Y %H:%M')
    
    stats_text = (
        f"📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 <b>Всего юзеров:</b> {total_users}\n"
        f"📚 <b>Материалов выдано:</b> {materials_sent}\n"
        f"🔒 <b>Имеют доступ:</b> {has_material_count}\n"
        f"📤 <b>Рассылок:</b> {broadcasts}\n"
        f"🔥 <b>Активных (30д):</b> {active_30d}\n\n"
        f"⏰ <b>Последняя рассылка:</b> {last_broadcast}"
    )
    
    await message.answer(stats_text, parse_mode='HTML')

@dp.message(Command('help'))
async def help_handler(message: Message):
    help_text = (
        f"🤖 <b>БОТ {CHANNEL_USERNAME}</b>\n\n"
        f"👤 <b>Для пользователей:</b>\n"
        f"/start — Начать\n\n"
        f"📤 <b>Для админа ({ADMIN_ID}):</b>\n"
        f"/broadcast текст — Рассылка\n"
        f"/schedule HH:MM текст — Отложенная\n"
        f"/stats — Статистика\n"
        f"/help — Помощь"
    )
    
    await message.answer(help_text, parse_mode='HTML')

# ===== WEBHOOK ДЛЯ RENDER =====
async def main():
    print("🤖 Бот запускается...")
    print(f"📢 Канал: {CHANNEL_USERNAME}")
    print(f"👤 Админ: {ADMIN_ID}")
    print(f"🌐 Порт: {PORT}")
    
    # POLLING для простоты (работает на Render)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())