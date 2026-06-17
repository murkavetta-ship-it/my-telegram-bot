import os
import re
import math
import time
import random
import io
import threading
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from PIL import Image
import telebot

# --- НАСТРОЙКИ БОТА ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8916051883:AAH9HWISsdjfZaXyCOfGTCKrEmH5xrGlkk8")
CHANNEL_ID = -1003735848662         # Ваш главный канал для постов
ARCHIVE_CHANNEL_ID = -1003783532522 # Ваш секретный архив с картинками

# Личные курсы валют
USD_RATE = 45.5
EUR_RATE = 52.5
GBP_RATE = 61.5
COMMISSION = 1.10

bot = telebot.TeleBot(BOT_TOKEN)

DEFAULT_CAPTIONS = [
    "☀️ Доброго ранку! Гарного та продуктивного дня! ✨",
    "☕ Ранок починається з кави та гарного настрою! Бажаю всім вдалого дня! ❤️"
]

def morning_scheduler():
    """Функция автоматической отправки утреннего поста из архива"""
    already_sent = False
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        if current_time == "05:00" and not already_sent:
            try:
                updates = bot.get_chat_history(chat_id=ARCHIVE_CHANNEL_ID, limit=50)
                media_messages = [msg for msg in updates if msg.content_type in ['photo', 'video']]
                if media_messages:
                    random_msg = random.choice(media_messages)
                    caption_text = random_msg.caption if random_msg.caption else random.choice(DEFAULT_CAPTIONS)
                    if random_msg.content_type == 'photo':
                        bot.send_photo(chat_id=CHANNEL_ID, photo=random_msg.photo[-1].file_id, caption=caption_text)
                    elif random_msg.content_type == 'video':
                        bot.send_video(chat_id=CHANNEL_ID, video=random_msg.video.file_id, caption=caption_text)
            except Exception as e:
                print(f"[-] Ошибка утреннего поста: {e}")
            already_sent = True
        elif current_time != "05:00":
            already_sent = False
        time.sleep(30)

def fetch_price_from_url(url):
    """Резервный парсер сайтов (если в тексте нет явной цены в валюте)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return None, None
        soup = BeautifulSoup(response.text, 'html.parser')
        url_lower = url.lower()
        
        if any(x in url_lower for x in ['uk', 'sportsdirect', 'uniqlo', 'next', 'hm.com']): currency = 'GBP'
        elif any(x in url_lower for x in ['mangooutlet', 'kiabi', 'zara', 'massimodutti', 'benetton', 'kiko']): currency = 'EUR'
        else: currency = 'USD'

        potential_prices = []
        for tag in soup.find_all(['span', 'div', 'p']):
            text = tag.text.strip()
            if any(sym in text for sym in ['$', '€', '£']):
                cleaned = re.sub(r'[^\d,.]', '', text).replace(',', '.')
                try:
                    val = float(cleaned)
                    if 0.5 < val < 5000: potential_prices.append(val)
                except: continue
        if potential_prices: return min(potential_prices), currency
    except: pass
    return None, None

def clean_and_convert_text(text):
    """Умный текстовый калькулятор + парсер купонов"""
    # 1. Проверяем скидку (например: -20%)
    discount_factor = 1.0
    discount_match = re.search(r'-(\d+)%', text)
    if discount_match:
        discount_factor = (100 - int(discount_match.group(1))) / 100

    # Определяем индивидуальную комиссию для Crocs
    current_commission = 1.05 if "crocs" in text.lower() else COMMISSION

    # 2. Охота на валюту прямо в тексте (Ищет форматы: 8.00£, 9.00$, 10€, £8.00)
    # Ищет любые цифры, рядом с которыми стоят знаки $, €, £
    currency_pattern = r'([\d.,]+)\s*([$€£])|([$€£])\s*([\d.,]+)'
    matches = re.findall(currency_pattern, text)

    extracted_prices = []
    if matches:
        for match in matches:
            # Вытаскиваем цифру и символ из регулярки
            price_str = match[0] or match[3]
            symbol = match[1] or match[2]
            try:
                price_val = float(price_str.replace(',', '.'))
                # Пересчитываем в гривны в зависимости от значка в тексте
                if symbol == '$': rate = USD_RATE
                elif symbol == '€': rate = EUR_RATE
                elif symbol == '£': rate = GBP_RATE
                
                uah_price = math.ceil(price_val * discount_factor * rate * current_commission)
                extracted_prices.append(uah_price)
            except:
                continue

    # 3. Формируем финальный ценник наверх
    if extracted_prices:
        if len(extracted_prices) == 1:
            price_line = f"{extracted_prices[0]}грн+вага"
        else:
            # Если в тексте было две цены (как у H&M — 8 и 9), бот красиво выведет вилку цен!
            price_line = f"{extracted_prices[0]}грн+вага - {extracted_prices[1]}грн+вага"
        
        # Ставим наши готовые цены в самый верх поста
        lines = text.split('\n')
        lines[0] = price_line
        text = '\n'.join(lines)
    else:
        # Если цен в валюте в тексте не нашли — включаем стандартный парсер по ссылке
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            original_price, currency = fetch_price_from_url(urls[0])
            if original_price:
                rate = USD_RATE if currency == 'USD' else (EUR_RATE if currency == 'EUR' else GBP_RATE)
                final_price = math.ceil(original_price * discount_factor * rate * current_commission)
                lines = text.split('\n')
                lines[0] = f"{final_price}грн+вага"
                text = '\n'.join(lines)

    # Очистка от мусора
    text = text.replace("грн+вага+вага", "грн+вага")
    return text.strip()

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Привет, Богиня! 👑 Умный Текстовый Калькулятор и парсер запущены. Полная защита от блокировок сайтов активна!")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    text = message.text or message.caption or ""
    if not text: return
    new_text = clean_and_convert_text(text)
    try:
        if message.content_type == 'text':
            bot.send_message(chat_id=CHANNEL_ID, text=new_text, parse_mode="HTML", disable_web_page_preview=True)
        elif message.content_type == 'photo':
            bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id, caption=new_text, parse_mode="HTML")
        elif message.content_type == 'video':
            bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id, caption=new_text, parse_mode="HTML")
        bot.reply_to(message, "Готово, Богиня! Все цены в тексте пересчитаны! 🔥")
    except Exception as e:
        bot.reply_to(message, f"Ошибка отправки: {e}")

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=morning_scheduler, daemon=True)
    scheduler_thread.start()
    import os
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
