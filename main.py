import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from PIL import Image

# Bot tokenini shu yerga yozing
TOKEN = "SIZNING_BOT_TOKENINGIZ" 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Vaqtinchalik fayllar uchun papka yaratish
if not os.path.exists("temp"):
    os.makedirs("temp")

# Start komandasi
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Assalomu alaykum! \n\n"
                         "📸 Rasm yuboring (oddiy yoki fayl ko'rinishida) -> "
                         "Men uni PNG formatiga (hujjat qilib) o'zgartirib beraman.")

# Rasmni formatlash va yuborish funksiyasi
async def convert_and_send_png(message: Message, file_id: str, file_unique_id: str):
    msg = await message.answer("Rasm yuklab olinmoqda va formatlanmoqda... ⏳")
    
    input_path = f"temp/in_{file_unique_id}.tmp"
    output_path = f"temp/out_{file_unique_id}.png"
    
    try:
        # Faylni yuklab olish
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, input_path)

        # Pillow yordamida rasmni ochish va PNG ga saqlash
        # (Bu yerda u JPG yoki boshqa formatni avtomatik aniqlaydi)
        img = Image.open(input_path)
        img.save(output_path, "PNG")

        # Tayyor faylni yuborish
        document = FSInputFile(output_path, filename=f"converted_{file_unique_id}.png")
        await message.answer_document(document, caption="✅ Rasmingiz muvaffaqiyatli PNG formatiga o'tkazildi.")

        # Kompyuterdagi vaqtinchalik fayllarni o'chirish
        os.remove(input_path)
        os.remove(output_path)
        await msg.delete()
        
    except Exception as e:
        # Xatolikni terminalda ko'rish uchun logging
        logging.error(f"Xatolik yuz berdi: {e}")
        await msg.edit_text(f"❌ Rasm formatini o'zgartirishda xatolik yuz berdi. "
                            f"Iltimos, qaytadan urinib ko'ring yoki boshqa rasm yuboring.\n\n"
                            f"Texnik xato: {e}")
        # Tozalashga urinish
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

# Oddiy rasm yuborilganda (F.photo)
@dp.message(F.photo)
async def photo_handler(message: Message):
    # Eng yuqori sifatdagi rasmni tanlaymiz
    photo = message.photo[-1]
    await convert_and_send_png(message, photo.file_id, photo.file_unique_id)

# Fayl (hujjat) ko'rinishidagi rasm yuborilganda (F.document)
@dp.message(F.document.mime_type.startswith("image/"))
async def document_photo_handler(message: Message):
    # Faqat rasm turidagi fayllarni qabul qiladi
    await convert_and_send_png(message, message.document.file_id, message.document.file_unique_id)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
