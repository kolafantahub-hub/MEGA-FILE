"""
🤖 Media Format Converter Bot — Aiogram 3.x
Rasmlar: JPG, PNG, WEBP, BMP, GIF, TIFF
Audiolar: MP3, OGG, WAV, FLAC, AAC, M4A

Python 3.13+ uchun: pydub o'rniga ffmpeg to'g'ridan-to'g'ri ishlatiladi
"""

import asyncio
import io
import logging
import subprocess
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from PIL import Image

# ─── Sozlamalar ───────────────────────────────────────────────
BOT_TOKEN = "8708808623:AAFRxA1OkkYfSg5oNHCilfscep_3W0ofyG4"   # @BotFather dan olingan token

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ─── Holatlar ─────────────────────────────────────────────────
class ConvertState(StatesGroup):
    waiting_format = State()

# ─── Qo'llab-quvvatlanadigan formatlar ───────────────────────
IMAGE_FORMATS = ["JPG", "PNG", "WEBP", "BMP", "GIF", "TIFF"]
AUDIO_FORMATS = ["MP3", "OGG", "WAV", "FLAC", "AAC", "M4A"]

# ─── Yordamchi: inline klaviatura ─────────────────────────────
def format_keyboard(formats: list[str], media_type: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"📄 {fmt}",
            callback_data=f"convert:{media_type}:{fmt}"
        )]
        for fmt in formats
    ]
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ─── /start ───────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Salom! Men <b>Media Converter Bot</b>man.\n\n"
        "📸 <b>Rasm yuborish</b> → formatni tanlang → konvertatsiya tayyor!\n"
        "🎵 <b>Audio yuborish</b> → formatni tanlang → yuklab oling!\n\n"
        "<b>Qo'llab-quvvatlanadigan formatlar:</b>\n"
        f"🖼 Rasmlar: {', '.join(IMAGE_FORMATS)}\n"
        f"🔊 Audiolar: {', '.join(AUDIO_FORMATS)}\n\n"
        "Boshlash uchun rasm yoki audio fayl yuboring! 🚀",
        parse_mode="HTML"
    )

# ─── /help ────────────────────────────────────────────────────
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "1️⃣ Rasm yoki audio fayl yuboring\n"
        "2️⃣ Kerakli formatni tanlang\n"
        "3️⃣ Konvertatsiya qilingan faylni oling\n\n"
        "<b>Eslatma:</b> GIF uchun animatsiya saqlanmaydi.\n"
        "Muammo bo'lsa @admin ga yozing.",
        parse_mode="HTML"
    )

# ─── Rasm qabul qilish ────────────────────────────────────────
@dp.message(F.photo | (F.document & F.document.mime_type.startswith("image/")))
async def receive_image(message: Message, state: FSMContext):
    if message.photo:
        file_id  = message.photo[-1].file_id
        orig_ext = "JPG"
    else:
        file_id  = message.document.file_id
        file_name = message.document.file_name or "image"
        orig_ext = Path(file_name).suffix.lstrip(".").upper() or "JPG"

    await state.set_state(ConvertState.waiting_format)
    await state.update_data(file_id=file_id, media_type="image", orig_ext=orig_ext)

    await message.answer(
        f"🖼 Rasm qabul qilindi! (<code>{orig_ext}</code>)\n\n"
        "Qaysi formatga o'tkazish kerak?",
        parse_mode="HTML",
        reply_markup=format_keyboard(IMAGE_FORMATS, "image")
    )

# ─── Audio qabul qilish ───────────────────────────────────────
@dp.message(F.audio | F.voice | (F.document & F.document.mime_type.startswith("audio/")))
async def receive_audio(message: Message, state: FSMContext):
    if message.audio:
        file_id   = message.audio.file_id
        file_name = message.audio.file_name or "audio.mp3"
    elif message.voice:
        file_id   = message.voice.file_id
        file_name = "voice.ogg"
    else:
        file_id   = message.document.file_id
        file_name = message.document.file_name or "audio"

    orig_ext = Path(file_name).suffix.lstrip(".").upper() or "MP3"

    await state.set_state(ConvertState.waiting_format)
    await state.update_data(file_id=file_id, media_type="audio", orig_ext=orig_ext)

    await message.answer(
        f"🎵 Audio qabul qilindi! (<code>{orig_ext}</code>)\n\n"
        "Qaysi formatga o'tkazish kerak?",
        parse_mode="HTML",
        reply_markup=format_keyboard(AUDIO_FORMATS, "audio")
    )

# ─── Format tanlash (callback) ────────────────────────────────
@dp.callback_query(F.data.startswith("convert:"))
async def process_conversion(callback: CallbackQuery, state: FSMContext):
    _, media_type, target_fmt = callback.data.split(":")
    data = await state.get_data()

    if not data:
        await callback.answer("⚠️ Avval fayl yuboring!", show_alert=True)
        return

    await callback.message.edit_text(f"⏳ {target_fmt} formatiga o'tkazilmoqda...")
    await state.clear()

    try:
        file = await bot.get_file(data["file_id"])
        file_bytes = await bot.download_file(file.file_path)
        raw = file_bytes.read()

        if media_type == "image":
            result_bytes, out_name = convert_image(raw, target_fmt)
        else:
            result_bytes, out_name = convert_audio(raw, data["orig_ext"], target_fmt)

        doc = BufferedInputFile(result_bytes, filename=out_name)
        await callback.message.answer_document(
            doc,
            caption=f"✅ Tayyor! <b>{data['orig_ext']} → {target_fmt}</b>",
            parse_mode="HTML"
        )
        await callback.message.delete()

    except Exception as e:
        logger.exception("Konvertatsiya xatosi")
        await callback.message.edit_text(f"❌ Xatolik yuz berdi:\n<code>{e}</code>", parse_mode="HTML")

# ─── Bekor qilish ─────────────────────────────────────────────
@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi. Yangi fayl yuborishingiz mumkin.")

# ─── Rasm konvertatsiya funksiyasi ────────────────────────────
def convert_image(raw: bytes, target: str) -> tuple[bytes, str]:
    img = Image.open(io.BytesIO(raw)).convert("RGBA")

    pil_format = target
    if target == "JPG":
        pil_format = "JPEG"
        img = img.convert("RGB")
    elif target in ("BMP", "TIFF"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format=pil_format)
    ext = "jpg" if target == "JPG" else target.lower()
    return buf.getvalue(), f"converted.{ext}"

# ─── Audio konvertatsiya funksiyasi (ffmpeg orqali) ──────────
def convert_audio(raw: bytes, orig_ext: str, target: str) -> tuple[bytes, str]:
    in_ext  = orig_ext.lower()
    out_ext = target.lower()

    with tempfile.TemporaryDirectory() as tmp:
        in_path  = Path(tmp) / f"input.{in_ext}"
        out_path = Path(tmp) / f"output.{out_ext}"

        in_path.write_bytes(raw)

        cmd = ["ffmpeg", "-y", "-i", str(in_path), str(out_path)]
        result = subprocess.run(cmd, capture_output=True)

        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            raise RuntimeError(f"ffmpeg xatosi:\n{err[-500:]}")

        return out_path.read_bytes(), f"converted.{out_ext}"

# ─── Noto'g'ri xabar ──────────────────────────────────────────
@dp.message()
async def unknown_message(message: Message):
    await message.answer(
        "🤔 Tushunmadim. Iltimos, rasm yoki audio fayl yuboring.\n"
        "Yordam uchun /help"
    )

# ─── Ishga tushirish ──────────────────────────────────────────
async def main():
    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
