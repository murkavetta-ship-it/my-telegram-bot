import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# === НАСТРОЙКИ БОТА ===
BOT_TOKEN = "8916051883:AAH9HWISsdjfZaXyCOfGTCKrEmH5xrG1kk8" # Ваш токен
CHANNEL_ID = -1003735848662 # ID вашего канала
# ======================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Привет! Перешли мне пост с ценой грн, я сам добавлю '+вага' и отправлю в канал.")

@dp.message()
async def handle_message(message: types.Message):
    text = message.text or message.caption or ""
    if not text:
        return

    if "грн" in text:
        new_text = text.replace("грн", "грн +вага")
    elif "Грн" in text:
        new_text = text.replace("Грн", "Грн +вага")
    else:
        new_text = text

    try:
        if message.text:
            await bot.send_message(chat_id=CHANNEL_ID, text=new_text, parse_mode="HTML")
        elif message.photo:
            photo_id = message.photo[-1].file_id
            await bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=new_text, parse_mode="HTML")
        elif message.video:
            await bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id, caption=new_text, parse_mode="HTML")
        await message.answer("Готово! Пост отправлен в канал.")
    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}")

# Упрощенный запуск без сложного polling-цикла
if __name__ == "__main__":
    print("Бот успешно запущен и ожидает сообщений...")
    try:
        asyncio.run(dp.start_polling(bot, handle_as_tasks=False))
    except KeyboardInterrupt:
        print("Бот остановлен.")