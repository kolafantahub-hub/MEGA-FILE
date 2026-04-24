import asyncio
import os
import subprocess
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from PIL import Image

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# --- TOKENNI SHU YERGA YOZING ---
TOKEN = "BU_YERGA_BOTFATHERDAN_OLINGAN_TOKENNI_QOYING" 
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Vaqtinchalik fayllar uchun papka
if not os.path.exists("temp"):
    os.makedirs("temp")

class ConvertState(StatesGroup):
    waiting_for_file = State()
    choosing_format = State()

# --- KLAVIATURALAR ---
def main_menu():
    buttons = [
        [InlineKeyboardButton(text="Rasm 🖼", callback_data="mode_image")],
        [InlineKeyboardButton(text="Audio (Qo'shiq) 🎵", callback_data="mode_audio")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def image_formats():
    buttons = [
        [InlineKeyboardButton(text="JPG ga", callback_data="to_jpg")],
        [InlineKeyboardButton(text="PNG ga", callback_data="to_png")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def audio_formats():
    buttons = [
        [InlineKeyboardButton(text="MP3 ga 🎧", callback_data="to_mp3")],
        [InlineKeyboardButton(text="WAV ga 📻", callback_data="to_wav")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Salom! Men rasm va audio fayllarni o'zgartira olaman. Tanlang:", 
                         reply_markup=main_menu())

@dp.callback_query(F.data.startswith("mode_"))
async def set_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]
    await state.update_data(current_mode=mode)
    await state.set_state(ConvertState.waiting_for_file)
    text = "Menga rasm yuboring 🖼" if mode == "image" else "Menga audio fayl yuboring 🎵"
    await callback.message.edit_text(text)

@dp.message(ConvertState.waiting_for_file)
async def handle_file(message: Message, state: FSMContext):
    data = await state.get_data()
    mode = data.get("current_mode")

    if mode == "image" and message.photo:
        file_id = message.photo[-1].file_id
        kb = image_formats()
    elif mode == "audio" and (message.audio or message.voice or message.document):
        file_id = message.audio.file_id if message.audio else message.document.file_id
        kb = audio_formats()
    else:
        await message.answer("Xato fayl turi! Iltimos, tanlangan turga mos fayl yuboring.")
        return

    await state.update_data(file_id=file_id)
    await state.set_state(ConvertState.choosing_format)
    await message.answer("Qaysi formatga o'tkazmoqchisiz?", reply_markup=kb)

@dp.callback_query(ConvertState.choosing_format, F.data.startswith("to_"))
async def process_conversion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_format = callback.data.split("_")[1]
    file_id = data['file_id']
    mode = data['current_mode']

    msg = await callback.message.edit_text("⏳ Ishlanmoqda...")
    
    file = await bot.get_file(file_id)
    input_path = f"temp/in_{file_id}"
    output_path = f"temp/out_{file_id}.{target_format}"

    await bot.download_file(file.file_path, input_path)

    try:
        if mode == "image":
            # Rasm konvertatsiyasi
            with Image.open(input_path) as img:
                if target_format == "jpg":
                    img.convert("RGB").save(output_path, "JPEG")
                else:
                    img.save(output_path, "PNG")
        else:
            # Audio konvertatsiyasi (FFmpeg orqali)
            subprocess.run(['ffmpeg', '-i', input_path, output_path, '-y'], check=True)

        await callback.message.answer_document(FSInputFile(output_path), caption="Tayyor! ✅")
    except Exception as e:
        logging.error(e)
        await callback.message.answer("❌ Xatolik yuz berdi. FFmpeg o'rnatilganini tekshiring.")

    # Tozalash
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
