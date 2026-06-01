import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = '8379181877:AAFQHcg6hWosPVSr_cmqfLxlqtIqeHCF5QI'

# @PEACEFULL_WARRIOR23 profilingizning Telegram ID raqami
ADMIN_ID = 5413481232  

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

# База данных подписчиков (времменая)
users_db = set()

# Состояние ожидания локации от админа
class ZborState(StatesGroup):
    waiting_for_location = State()

# 1. Команда /start - собирает пользователей в базу
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    users_db.add(message.from_user.id)
    await message.reply("Здравствуйте! Добро пожаловать в бот оповещений СБОР. Ожидайте сообщений от администратора.")

# 2. Команда /zbor только для вас (Админа)
@dp.message_handler(commands=['zbor'], user_id=ADMIN_ID)
async def cmd_zbor(message: types.Message):
    await message.reply("УВАЖАЕМЫЙ АДМИН! Где будет сБОР? Пожалуйста, отправьте локацию (геопозицию).")
    await ZborState.waiting_for_location.set()

# 3. Ловим локацию от админа и рассылаем всем подписчикам
@dp.message_handler(content_types=['location'], state=ZborState.waiting_for_location, user_id=ADMIN_ID)
async def broad_cast_zbor(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    
    success_count = 0
    
    # Рассылка всем пользователям в базе
    for user_id in users_db:
        try:
            await bot.send_message(
                user_id, 
                "🚨 **ВНИМАНИЕ! Администратор объявил СБОР! Всем общий сбор!**\n\nМесто встречи указано на локации ниже:"
            )
            await bot.send_location(user_id, latitude=lat, longitude=lon)
            success_count += 1
        except Exception as e:
            print(f"Ошибка при отправке пользователю {user_id}: {e}")
            
    await message.reply(f"📢 Уведомление о сборе и локация успешно отправлены {success_count} подписчикам!")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
