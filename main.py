import os
import re
import math
import time
import random
import threading
from datetime import datetime
import telebot

# === НАСТРОЙКИ БОТА ===
BOT_TOKEN = "8916051883:AAH9HWISsdjfZaXyCOfGTCKrEmH5xrGlkk8"
CHANNEL_ID = -1003735848662        # Ваш главный канал
ARCHIVE_CHANNEL_ID = -1003783532522 # Ваш секретный архив с картинками
# ======================

bot = telebot.TeleBot(BOT_TOKEN)

# Базовые пожелания на случай, если архив пуст
DEFAULT_CAPTIONS = [
    "☀️ Доброго ранку! Гарного та продуктивного дня! ✨",
    "☕️ Ранок починається з кави та гарного настрою! Бажаю всім вдалого дня! ❤️",
    "💫 Прокидайтеся з посмішкою! Нехай сьогоднішній день принесе багато радості! 🌸",
    "🌿 Чудового ранку! Бажаю, щоб сьогодні все задумане вдалося! ☀️",
    "✨ Доброго ранку, красуні! Бажаю натхнення та яскравого дня! 💖",
    "🛍️ Прекрасного ранку! Нехай цей день принесе море позитиву та вдалих знахідок! ✨",
    "🌟 Доброго ранку! Нехай сегодняшій день буде легким, сонячним та наповненим приємними моментами! 🌸",
    "☕️ Затишного ранку та смачної кави! Бажаю чудового настрою на весь день! 💞",
    "🦋 Радісного ранку! Прокидайтеся та підкорюйте цей світ своєю посмішкою! Гарного дня! ☀️",
    "🌺 Доброго ранку! Нехай кожен момент сьогоднішнього дня приносить радість та натхнення! ✨",
    "🕊️ Мирного та тихого ранку! Нехай цей день буде безпечним, спокійним та принесе лише хороші новини! 🙏✨",
    "☀️ Доброго ранку! Бажаю мирного неба над головою, затишку в оселі та гармонії в душі! 🌸🌿",
    "✨ Чудового ранку! Нехай день пройде під мирним небом, спокійно та продуктивно! Бережіть себе! ❤️"
]

# Функция, которая проверяет время и отправляет случайный пост (фото или видео) из архива
# 05:00 по времени сервера Render — это ровно 08:00 по Киевскому времени
def morning_scheduler():
    already_sent = False
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        if current_time == "05:00":
            if not already_sent:
                try:
                    # Сканируем последние 50 сообщений из вашего архива
                    updates = bot.get_chat_history(chat_id=ARCHIVE_CHANNEL_ID, limit=50)
                    
                    # Фильтруем сообщения, где есть ИЛИ фото, ИЛИ видео
                    media_messages = [msg for msg in updates if msg.content_type in ['photo', 'video']]
                    
                    if media_messages:
                        # Выбираем случайное медиа-сообщение
                        random_msg = random.choice(media_messages)
                        
                        # Определяем случайный текст пожелания
                        if random_msg.caption:
                            caption_text = random_msg.caption
                        else:
                            caption_text = random.choice(DEFAULT_CAPTIONS)
                        
                        # Проверяем тип контента и отправляем правильной командой
                        if random_msg.content_type == 'photo':
                            photo_id = random_msg.photo[-1].file_id
                            bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=caption_text)
                        elif random_msg.content_type == 'video':
                            video_id = random_msg.video.file_id
                            bot.send_video(chat_id=CHANNEL_ID, video=video_id, caption=caption_text)
                            
                        print("Утренний медиа-пост из архива успешно отправлен!")
                    else:
                        print("В канале-архиве не найдено подходящих фото или видео.")
                except Exception as e:
                    print(f"Ошибка при автоматической отправке утреннего поста: {e}")
                already_sent = True
        else:
            already_sent = False
            
        time.sleep(30)

def clean_and_convert_text(text):
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'https?://t\.me/[a-zA-Z0-9_+]{4,}(?!/)\b', '', text)
    
    usd_rate = 45.5
    commission = 1.10
    
    def replace_usd(match):
        usd_amount_str = match.group(1) or match.group(2)
        try:
            usd_amount = float(usd_amount_str)
            uah_amount = usd_amount * usd_rate * commission
            uah_final = math.ceil(uah_amount)
            return f"{uah_final} грн+вага"
        except:
            return match.group(0)

    usd_pattern = r'\$(\d+(?:\.\d+)?)|\b(\d+(?:\.\d+)?)\s*\$'
    
    if "$" in text:
        text = re.sub(usd_pattern, replace_usd, text)
    elif "грн" in text.lower():
        if "грн" in text:
            text = text.replace("грн", "грн+вага")
        else:
            text = text.replace("Грн", "Грн+вага")
    elif text.strip().isdigit():
        text = f"{text.strip()} грн+вага"
    else:
        text = re.sub(r'(\d+)\b(?! грн)', r'\1 грн+вага', text)
        
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text).strip()
    return text

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Привет! Всё работает: калькулятор активен, а утренний архив успешно подключен!")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    text = message.text or message.caption or ""
    if not text:
        return
    new_text = clean_and_convert_text(text)
    try:
        if message.content_type == 'text':
            bot.send_message(chat_id=CHANNEL_ID, text=new_text, parse_mode="HTML", disable_web_page_preview=True)
        elif message.content_type == 'photo':
            photo_id = message.photo[-1].file_id
            bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=new_text, parse_mode="HTML")
        elif message.content_type == 'video':
            bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id, caption=new_text, parse_mode="HTML")
        bot.reply_to(message, "Готово!")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    scheduler_thread = threading.Thread(target=morning_scheduler, daemon=True)
    scheduler_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
