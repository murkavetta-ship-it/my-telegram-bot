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
    """Улучшенный калькулятор: точечно заменяет абсолютно все цены по всему тексту поста"""
    # 1. Проверяем скидку купона (например: -20%)
    discount_factor = 1.0
    discount_match = re.search(r'-(\d+)%', text)
    if discount_match:
        discount_factor = (100 - int(discount_match.group(1))) / 100

    # Определяем индивидуальную комиссию для Crocs
    current_commission = 1.05 if "crocs" in text.lower() else COMMISSION

    # 2. Ищем все упоминания валют: форматы 8.00£, 9.00$, 10€, £8.00, $55
    currency_pattern = r'([\d.,]+\s*[$€£]|[$€£]\s*[\d.,]+)'
    matches = re.findall(currency_pattern, text)

    extracted_prices = []
    
    if matches:
        # Убираем дубликаты совпадений, если они есть, сохраняя порядок
        unique_matches = list(dict.fromkeys(matches))
        
        for raw_match in unique_matches:
            # Находим цифры и знак внутри этого совпадения
            price_digit_match = re.search(r'[\d.,]+', raw_match)
            symbol_match = re.search(r'[$€£]', raw_match)
            
            if price_digit_match and symbol_match:
                try:
                    price_val = float(price_digit_match.group().replace(',', '.'))
                    symbol = symbol_match.group()
                    
                    # Привязываем правильный курс к значку
                    if symbol == '$': rate = USD_RATE
                    elif symbol == '€': rate = EUR_RATE
                    elif symbol == '£': rate = GBP_RATE
                    
                    # Считаем вашу цену в гривнах
                    uah_price = math.ceil(price_val * discount_factor * rate * current_commission)
                    extracted_prices.append(uah_price)
                    
                    # ТОЧЕЧНАЯ ЗАМЕНА: заменяем старую валюту на новую цену грн во ВСЕМ тексте
                    text = text.replace(raw_match, f"{uah_price}грн+вага")
                except:
                    continue

        # 3. Делаем красивую шапку-вилку цен на самой первой строчке
        if extracted_prices:
            if len(extracted_prices) == 1:
                price_header = f"{extracted_prices[0]}грн+вага"
            else:
                price_header = f"{extracted_prices[0]}грн+вага - {extracted_prices[1]}грн+вага"
            
            # Добавляем вилку в самый верх, сохраняя весь остальной измененный текст снизу
            text = f"{price_header}\n{text}"
            
    else:
        # Если цен в валюте в тексте вообще нет — включаем стандартный парсер по ссылке
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            original_price, currency = fetch_price_from_url(urls[0])
            if original_price:
                rate = USD_RATE if currency == 'USD' else (EUR_RATE if currency == 'EUR' else GBP_RATE)
                final_price = math.ceil(original_price * discount_factor * rate * current_commission)
                lines = text.split('\n')
                lines[0] = f"{final_price}грн+вага"
                text = '\n'.join(lines)

    # Финальная зачистка от случайных наслоений
    text = text.replace("грн+вага+вага", "грн+вага")
    return text.strip()

# --- МОДУЛЬ 3: ОБРАБОТЧИКИ СООБЩЕНИЙ ТЕЛЕГРАМ ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Привет, Богиня! 👑 Тотальный калькулятор цен по всему тексту запущен. Больше никакой старой валюты в постах!")

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
        bot.reply_to(message, "Готово, Богиня! Пост полностью очищен от валюты и пересчитан! 🔥")
    except Exception as e:
        bot.reply_to(message, f"Ошибка отправки: {e}")

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=morning_scheduler, daemon=True)
    scheduler_thread.start()
    import os
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
