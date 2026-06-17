import os
import re
import math
import telebot

# Настройки бота
BOT_TOKEN = "8916051883:AAH9HWISsdjfZaXyCOfGTCKrEmH5xrGlkk8"
CHANNEL_ID = -1003735848662

bot = telebot.TeleBot(BOT_TOKEN)

def convert_dollars_to_uah(text):
    # Курс и комиссия
    usd_rate = 45.5
    commission = 1.10 # +10%
    
    # Функция пересчета для найденного совпадения
    def replace_usd(match):
        # Извлекаем только число из найденного текста (например, из '$16.80' или '40$')
        usd_amount_str = match.group(1) or match.group(2)
        try:
            usd_amount = float(usd_amount_str)
            # Считаем формулу: цена * 45.5 + 10% комиссии
            uah_amount = usd_amount * usd_rate * commission
            # Округляем до целого числа вверх без копеек
            uah_final = math.ceil(uah_amount)
            return f"{uah_final} грн+вага"
        except:
            return match.group(0) # Если не получилось посчитать, оставляем как было

    # Регулярное выражение ищет форматы: $16.80, $40, 40$, 16.80$
    # Оно автоматически находит и целые числа, и числа с точкой
    pattern = r'\$(\d+(?:\.\d+)?)|\b(\d+(?:\.\d+)?)\s*\$'
    
    # Заменяем все доллары на пересчитанные гривны
    return re.sub(pattern, replace_usd, text)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Привет! Я готов. Перешли мне любой пост, я пересчитаю $ в грн по формуле и добавлю '+вага'.")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    text = message.text or message.caption or ""
    if not text:
        return

    # 1. Сначала обрабатываем и пересчитываем доллары, если они есть
    if "$" in text:
        new_text = convert_dollars_to_uah(text)
    
    # 2. Если долларов нет, но есть обычное слово 'грн' — просто дописываем '+вага'
    elif "грн" in text.lower():
        if "грн" in text:
            new_text = text.replace("грн", "грн+вага")
        else:
            new_text = text.replace("Грн", "Грн+вага")

    # 3. Если это просто чистое число без валюты — делаем из него грн+вага
    elif text.strip().isdigit():
        new_text = f"{text.strip()} грн+вага"
        
    # 4. В остальных случаях ищем любые другие чистые цифры и превращаем в грн+вага
    else:
        new_text = re.sub(r'(\d+)\b(?! грн)', r'\1 грн+вага', text)

    try:
        if message.content_type == 'text':
            bot.send_message(chat_id=CHANNEL_ID, text=new_text, parse_mode="HTML", disable_web_page_preview=True)
        elif message.content_type == 'photo':
            photo_id = message.photo[-1].file_id
            bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=new_text, parse_mode="HTML")
        elif message.content_type == 'video':
            bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id, caption=new_text, parse_mode="HTML")
        
        bot.reply_to(message, "Готово! Пост пересчитан и отправлен в канал.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при отправке: {e}")

if __name__ == "__main__":
    print("Бот успешно запущен и ожидает сообщений...")
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
