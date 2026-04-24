import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from PIL import Image
from pydub import AudioSegment

# Bot tokenini yozing (Hozirgi tokenni yangilab olishni maslahat beraman)
TOKEN = "8636087303:AAEsZvZ6JO0lD8mCwtbuIQBnTBDAejZgCnE" 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Start komandasi
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Assalomu alaykum! \n\n"
                         "📸 Rasm yuborsangiz -> Uni PNG formatga (hujjat qilib) o'zgartiraman.\n"
                         "🎵 Qo'shiq yuborsangiz -> Uni Ovozli xabar (Voice/OGG) qilib beraman.")

# Rasm formatini o'zgartirish qismi
@dp.message(F.photo)
async def convert_photo(message: Message):
    msg = await message.answer("Rasm yuklab olinmoqda va formatlanmoqda... ⏳")
    try:
        # Eng yuqori sifatdagi rasmni olish
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        input_path = f"{photo.file_id}.jpg"
        output_path = f"{photo.file_id}.png"
        
        await bot.download_file(file.file_path, input_path)

        # Pillow yordamida rasmni PNG ga o'girish
        img = Image.open(input_path)
        img.save(output_path, "PNG")

        # Tayyor faylni yuborish
        document = FSInputFile(output_path)
        await message.answer_document(document, caption="✅ PNG formatiga o'tkazildi.")

        # Kompyuterdagi vaqtinchalik fayllarni o'chirish
        os.remove(input_path)
        os.remove(output_path)
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text(f"❌ Rasm formatini o'zgartirishda xatolik yuz berdi: {e}")

# Audio/Qo'shiq formatini o'zgartirish qismi
@dp.message(F.audio | F.voice)
async def convert_audio(message: Message):
    msg = await message.answer("Audio yuklab olinmoqda va formatlanmoqda... ⏳")
    
    # Fayl turini aniqlash
    if message.audio:
        file_id = message.audio.file_id
        ext = ".mp3"
    else:
        file_id = message.voice.file_id
        ext = ".ogg"

    try:
        file = await bot.get_file(file_id)
        input_path = f"in_{file_id}{ext}"
        output_path = f"out_{file_id}.ogg"
        
        await bot.download_file(file.file_path, input_path)

        # Pydub orqali audioni Voice formatiga o'tkazish
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="ogg", codec="libopus")

        # Tayyor faylni yuborish
        voice = FSInputFile(output_path)
        await message.answer_voice(voice, caption="✅ Format o'zgartirildi.")

        # Kompyuterdagi vaqtinchalik fayllarni o'chirish
        os.remove(input_path)
        os.remove(output_path)
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text("❌ Xatolik yuz berdi!\n\n"
                            "Eslatma: Audio formatini o'zgartirish uchun kompyuteringizda "
                            "FFmpeg o'rnatilgan bo'lishi shart.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
