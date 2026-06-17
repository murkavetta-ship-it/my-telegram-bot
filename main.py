import os
import telebot

# Настройки бота
BOT_TOKEN = "8916051883:AAH9HWISsdjfZaXyCOfGTCKrEmH5xrGlkk8"
CHANNEL_ID = -1003735848662

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Привет! Перешли мне пост с ценой грн, я сам добавлю '+вага' и отправлю в канал.")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    text = message.text or message.caption or ""
    if not text:
        return

    # Автоматически заменяем 'грн' на 'грн +вага'
    if "грн" in text:
        new_text = text.replace("грн", "грн +вага")
    elif "Грн" in text:
        new_text = text.replace("Грн", "Грн +вага")
    else:
        new_text = text

    try:
        if message.content_type == 'text':
            bot.send_message(chat_id=CHANNEL_ID, text=new_text, parse_mode="HTML")
        elif message.content_type == 'photo':
            photo_id = message.photo[-1].file_id
            bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=new_text, parse_mode="HTML")
        elif message.content_type == 'video':
            bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id, caption=new_text, parse_mode="HTML")
        
        bot.reply_to(message, "Готово! Пост изменен и отправлен в канал.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при отправке: {e}")

if __name__ == "__main__":
    print("Бот успешно запущен и ожидает сообщений...")
    # Запускаем фоновый веб-сервер, чтобы Render не усыплял бота
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    # Включаем самого бота
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
