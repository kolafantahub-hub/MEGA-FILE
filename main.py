import asyncio
from os import getenv
from dotenv import load_dotenv
import asyncio
import logging
from io import BytesIO
import tempfile
import subprocess

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image

load_dotenv()

IP_TOKEN =getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_state = {}

# ---------------- START ----------------
@dp.message(F.text == "/start")
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🖼 Rasm", callback_data="rasm"),
            InlineKeyboardButton(text="🎵 Audio", callback_data="audio")
        ]
    ])

    await message.answer("Nimani konvert qilamiz?", reply_markup=kb)

# ---------------- TYPE SELECT ----------------
@dp.callback_query(F.data.in_(["rasm", "audio"]))
async def choose_type(call: CallbackQuery):
    user_state[call.from_user.id] = {"type": call.data}
    await call.message.answer("Fayl yuboring 📤")
    await call.answer()

# ---------------- FILE RECEIVE ----------------
@dp.message(F.photo | F.document | F.audio)
async def get_file(message: Message):
    uid = message.from_user.id
    if uid not in user_state:
        return

    file = message.photo[-1] if message.photo else message.document or message.audio

    file_info = await bot.get_file(file.file_id)
    downloaded = await bot.download_file(file_info.file_path)

    file_bytes = BytesIO(downloaded.read())
    user_state[uid]["file"] = file_bytes

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    if user_state[uid]["type"] == "rasm":
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="JPG", callback_data="to_jpg"),
            InlineKeyboardButton(text="PNG", callback_data="to_png")
        ])
    else:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="MP3", callback_data="to_mp3"),
            InlineKeyboardButton(text="WAV", callback_data="to_wav")
        ])

    await message.answer("Qaysi formatga o‘tkazamiz?", reply_markup=kb)

# ---------------- CONVERT ----------------
@dp.callback_query(F.data.startswith("to_"))
async def convert(call: CallbackQuery):
    uid = call.from_user.id
    data = user_state.get(uid)

    if not data:
        return

    infile = data["file"]
    infile.seek(0)

    out_format = call.data.replace("to_", "")
    output = BytesIO()

    try:
        # 🖼 RASM
        if data["type"] == "rasm":
            img = Image.open(infile)
            img.save(output, format=out_format.upper())
            output.name = f"image.{out_format}"

        # 🎵 AUDIO (ffmpeg)
        else:
            with tempfile.NamedTemporaryFile(delete=False) as temp_in:
                temp_in.write(infile.read())
                temp_in_path = temp_in.name

            temp_out_path = temp_in_path + f".{out_format}"

            subprocess.run([
                "ffmpeg",
                "-y",
                "-i", temp_in_path,
                temp_out_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            with open(temp_out_path, "rb") as f:
                output.write(f.read())

            output.name = f"audio.{out_format}"

        output.seek(0)
        await bot.send_document(uid, output)

    except Exception as e:
        await call.message.answer(f"Xatolik: {e}")

    await call.answer()

# ---------------- MAIN ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
