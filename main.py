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

bot = telebot.TeleBot(BOT_TOKEN)

# Базовые пожелания на случай, если архив пуст
DEFAULT_CAPTIONS = [
    "☀️ Доброго ранку! Гарного та продуктивного дня! ✨",
    "☕ Ранок починається з кави та гарного настрою! Бажаю всім вдалого дня! ❤️",
    "💫 Прокидайтеся з посмішкою! Нехай сьогоднішній день принесе багато радості! ☀️",
    "🍃 Чудового ранку! Бажаю, щоб сьогодні все задумане вдалося! ❤️",
    "✨ Доброго ранку, красуні! Бажаю натхнення та яскравого дня! ❤️",
    "🌷 Прекрасного ранку! Нехай цей день принесе море позитиву та вдалих знахідок! ✨",
    "🌸 Доброго ранку! Нехай сьогоднішній день буде легким, сонячним та наповненим приємними моментами! ☕",
    "☕ Затишного ранку та смачної кави! Бажаю чудового настрою на весь день! ❤️",
    "🍇 Радісного ранку! Прокидайтеся та підкорюйте цей світ своєю посмішкою! Гарного дня! ☀️",
    "💫 Доброго ранку! Нехай кожен момент сьогоднішнього дня приносить радість та натхнення! ✨",
    "🕊️ Мирного та тихого ранку! Нехай цей день буде безпечним, спокійним та принесе лише хороші новини! ✨",
    "☀️ Доброго ранку! Бажаю мирного неба над головою, затишку в оселі та гармонії в душі! ✨",
    "🌺 Чудового ранку! Нехай день пройде под мирним небом, спокійно та продуктивно! Бережіть себе! ❤️"
]

# --- МОДУЛЬ 1: УТРЕННИЙ ШЕДУЛЕР ПОСТОВ ---
def morning_scheduler():
    """Функция автоматической отправки утреннего поста из архива"""
    already_sent = False
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # 05:00 по серверу Render — это 08:00 по Киеву
        if current_time == "05:00":
            if not already_sent:
                try:
                    updates = bot.get_chat_history(chat_id=ARCHIVE_CHANNEL_ID, limit=50)
                    media_messages = [msg for msg in updates if msg.content_type in ['photo', 'video']]
                    
                    if media_messages:
                        random_msg = random.choice(media_messages)
                        caption_text = random_msg.caption if random_msg.caption else random.choice(DEFAULT_CAPTIONS)
                            
                        if random_msg.content_type == 'photo':
                            photo_id = random_msg.photo[-1].file_id
                            bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=caption_text)
                        elif random_msg.content_type == 'video':
                            video_id = random_msg.video.file_id
                            bot.send_video(chat_id=CHANNEL_ID, video=video_id, caption=caption_text)
                        print("[+] Утренний медиа-пост из архива успешно отправлен!")
                except Exception as e:
                    print(f"[-] Ошибка утреннего поста: {e}")
                already_sent = True
        else:
            already_sent = False
        time.sleep(30)

# --- МОДУЛЬ 2: УМНЫЙ МУЛЬТИВАЛЮТНЫЙ ПАРСЕР ЦЕН ---
def fetch_price_from_url(url):
    """Автоматически считывает оригинальную цену товара и определяет валюту сайта"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code != 200:
            return None, None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        url_lower = url.lower()
        
        # Улучшенное автоопределение: теперь ловит и hm.com, и ://hm.com
        if any(x in url_lower for x in ['crocs.co.uk', 'ebay.co.uk', 'zalando.co.uk', 'next.co', '://uniqlo.com', 'sportsdirect', 'cocooncenter.co.uk', 'hm.com']):
            currency = 'GBP'  # Англия (Фунты)
            if 'hm.com' in url_lower and not any(us in url_lower for us in ['/us', 'en_us']):
                currency = 'GBP' # Если в H&M нет пометки US, то это Англия по умолчанию
        elif any(x in url_lower for x in ['://mangooutlet.com', 'kiabi', '://cos.com', '://zara.com', '://zara.com', 'zarahome', 'oysho', 'massimodutti', 'benetton', '://kikocosmetics.com', '://kikocosmetics.com', 'cocooncenter.de']):
            currency = 'EUR'  # Европа (Евро)
        else:
            currency = 'USD'  # США (Доллары)

        # Улучшенный поиск цен: теперь находит значки, даже если они прижаты к цифрам вроде 8.00£
        potential_prices = []
        for tag in soup.find_all(['span', 'div', 'p', 'h1', 'h2']):
            text = tag.text.strip()
            if any(sym in text for sym in ['$', '€', '£', 'GBP', 'EUR', 'USD']):
                cleaned = re.sub(r'[^\d,.]', '', text).replace(',', '.')
                try:
                    val = float(cleaned)
                    if 0.5 < val < 5000:
                        potential_prices.append(val)
                except:
                    continue

        if potential_prices:
            return min(potential_prices), currency
            
    except Exception as e:
        print(f"[-] Ошибка парсинга ссылки {url}: {e}")
    return None, None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        url_lower = url.lower()
        
        # 1. Автоопределение валютной зоны сайта (Добавлен британский H&M!)
        if any(x in url_lower for x in ['crocs.co.uk', 'ebay.co.uk', 'zalando.co.uk', 'next.co', '://uniqlo.com', 'sportsdirect', 'cocooncenter.co.uk', '://hm.com']):
            currency = 'GBP'  # Фунты
        elif any(x in url_lower for x in ['://mangooutlet.com', 'kiabi', '://cos.com', '://zara.com', '://zara.com', 'zarahome', 'oysho', 'massimodutti', 'benetton', '://kikocosmetics.com', '://kikocosmetics.com', 'cocooncenter.de']):
            currency = 'EUR'  # Евро
        else:
            currency = 'USD'  # Доллары США (Включая американский H&M, iHerb, 32degrees, Victoria's Secret, Nordstrom и др.)

        # 2. Поиск цен на странице
        potential_prices = []
        for tag in soup.find_all(['span', 'div', 'p', 'h1', 'h2']):
            text = tag.text.strip()
            if any(sym in text for sym in ['$', '€', '£', 'GBP', 'EUR', 'USD']):
                cleaned = re.sub(r'[^\d,.]', '', text).replace(',', '.')
                try:
                    val = float(cleaned)
                    if 0.5 < val < 5000:
                        potential_prices.append(val)
                except:
                    continue

        if potential_prices:
            return min(potential_prices), currency
            
    except Exception as e:
        print(f"[-] Ошибка парсинга ссылки {url}: {e}")
    return None, None

def clean_and_convert_text(text):
    """Применяет купон из текста, рассчитывает цену по тарифам и оформляет пост"""
    # 1. Считываем купон на скидку из текста (например: -20%)
    discount_factor = 1.0
    discount_match = re.search(r'-(\d+)%', text)
    if discount_match:
        discount_percent = int(discount_match.group(1))
        discount_factor = (100 - discount_percent) / 100

    # 2. Находим ссылку на магазин
    urls = re.findall(r'(https?://[^\s]+)', text)
    
    if urls:
        target_url = urls
        original_price, currency = fetch_price_from_url(target_url)
        
        if original_price:
            # Применяем скидку сайта к базовой цене
            discounted_price = original_price * discount_factor
            
            # Учитываем индивидуальную комиссию для Crocs (5% вместо 10%)
            current_commission = 1.05 if "crocs" in target_url.lower() else 1.10
            
            # Считаем итоговую цену в гривнах
            if currency == 'USD':
                final_price = math.ceil(discounted_price * USD_RATE * current_commission)
            elif currency == 'EUR':
                final_price = math.ceil(discounted_price * EUR_RATE * current_commission)
            elif currency == 'GBP':
                final_price = math.ceil(discounted_price * GBP_RATE * current_commission)
                
            # Заменяем первую строчку анонса на наш тариф
            lines = text.split('\n')
            lines = f"{final_price}грн+вага"
            text = '\n'.join(lines)
            
    # Чистка текста от дублирования веса и пробелов
    text = text.replace("грн+вага+вага", "грн+вага").replace("грн+вага", "грн+вага")
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text).strip()
    return text

# --- МОДУЛЬ 3: ОБРАБОТЧИКИ СООБЩЕНИЙ ТЕЛЕГРАМ ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Привет, Богиня! 👑 Все системы запущены, мультивалютный H&M (США/Англия) настроен. Просто пересылай анонсы пачками!")

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
            video_id = message.video.file_id
            bot.send_video(chat_id=CHANNEL_ID, video=video_id, caption=new_text, parse_mode="HTML")
        bot.reply_to(message, "Готово, Богиня! Пост пересчитан по вашему тарифу и опубликован в канале. 🔥")
    except Exception as e:
        bot.reply_to(message, f"Ошибка автоматической публикации: {e}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    scheduler_thread = threading.Thread(target=morning_scheduler, daemon=True)
    scheduler_thread.start()
    
    import os
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
