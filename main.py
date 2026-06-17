import os
import re
import math
import time
import random
import json
import threading
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types

# --- НАСТРОЙКИ БОТА ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8916051883:AAH9HWISsdjfZaXyCOfGTCKrEmH5xrGlkk8")
CHANNEL_ID = -1003735848662         # Ваш главный канал для постов
ARCHIVE_CHANNEL_ID = -1003783532522 # Ваш секретный архив с картинками

SETTINGS_FILE = "settings.json"

# Базовые настройки по умолчанию
DEFAULT_SETTINGS = {
    "usd_rate": 45.5,
    "eur_rate": 52.5,
    "gbp_rate": 61.5,
    "commission": 1.10,
    "global_discount": 0  # Глобальная скидка дня в % (0 - если выключена)
}

def load_settings():
    """Загрузка настроек из файла памяти"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Сохранение настроек в память"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[-] Ошибка сохранения настроек: {e}")

bot = telebot.TeleBot(BOT_TOKEN)

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
    "💫 Доброго ранку! Нехай каждый момент сьогоднішнього дня приносить радість та натхнення! ✨",
    "🕊️ Мирного та тихого ранку! Нехай цей день буде безпечним, спокійним та принесе лише хороші новини! ✨",
    "☀️ Доброго ранку! Бажаю мирного неба над головою, затишку в оселі та гармонії в душі! ✨",
    "🌺 Чудового ранку! Нехай день пройде под мирним небом, спокійно та продуктивно! Бережіть себе! ❤️"
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
    """Резервный парсер сайтов"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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
    """Умный калькулятор: заменяет цены строго на их местах в тексте"""
    settings = load_settings()
    
    # 1. Проверяем скидку купона (например: -20%)
    discount_factor = 1.0
    discount_match = re.search(r'-(\d+)%', text)
    if discount_match:
        discount_factor = (100 - int(discount_match.group(1))) / 100
    elif settings["global_discount"] > 0:
        discount_factor = (100 - settings["global_discount"]) / 100

    # Определяем индивидуальную комиссию для Crocs
    current_commission = 1.05 if "crocs" in text.lower() else settings["commission"]

    # 2. Улучшенный всеядный поиск валют: находит любые форматы (4.00£, £4.00, 4£, £4, 4.00 £)
    currency_pattern = r'(\d+[\.,]\d+|\d+)\s*([$€£])|([$€£])\s*(\d+[\.,]\d+|\d+)'
    matches = re.findall(currency_pattern, text)
    
    if matches:
        # Собираем список всех найденных оригинальных кусков текста с ценами для точной замены
        raw_matches_to_replace = []
        # Паттерн для поиска цен в тексте, чтобы вытащить точные подстроки
        for raw_found in re.finditer(r'(\d+[\.,]\d+[$€£]|\d+[$€£]|[$€£]\d+[\.,]\d+|[$€£]\d+|\d+[\.,]\d+\s+[$€£]|[$€£]\s+\d+[\.,]\d+)', text):
            raw_matches_to_replace.append(raw_found.group())
            
        unique_matches = list(dict.fromkeys(raw_matches_to_replace))
        
        for raw_match in unique_matches:
            price_digit_match = re.search(r'\d+[\.,]\d+|\d+', raw_match)
            symbol_match = re.search(r'[$€£]', raw_match)
            
            if price_digit_match and symbol_match:
                try:
                    price_val = float(price_digit_match.group().replace(',', '.'))
                    symbol = symbol_match.group()
                    
                    if symbol == '$': rate = settings["usd_rate"]
                    elif symbol == '€': rate = settings["eur_rate"]
                    elif symbol == '£': rate = settings["gbp_rate"]
                    
                    # Считаем цену в гривнах
                    uah_price = math.ceil(price_val * discount_factor * rate * current_commission)
                    
                    # Заменяем старую валюту на новую цену прямо на её месте по всему тексту
                    text = text.replace(raw_match, f"{uah_price}грн+вага")
                except:
                    continue
            
    else:
        # Резервный парсер по ссылке, если в тексте вообще нет значков валют
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            original_price, currency = fetch_price_from_url(urls)
            if original_price:
                rate = settings["usd_rate"] if currency == 'USD' else (settings["eur_rate"] if currency == 'EUR' else settings["gbp_rate"])
                final_price = math.ceil(original_price * discount_factor * rate * current_commission)
                lines = text.split('\n')
                lines = f"{final_price}грн+вага"
                text = '\n'.join(lines)

    # Зачистка от случайных наслоений
    text = text.replace("грн+вага+вага", "грн+вага")
    return text.strip()

# --- ИНТЕРАКТИВНАЯ КЛАВИАТУРА НАСТРОЕК ---
def get_settings_keyboard():
    settings = load_settings()
    comm_pct = int(round((settings["commission"] - 1) * 100))
    disc = settings["global_discount"]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_usd = types.InlineKeyboardButton(f"💵 USD: {settings['usd_rate']}", callback_data="set_usd")
    btn_eur = types.InlineKeyboardButton(f"💶 EUR: {settings['eur_rate']}", callback_data="set_eur")
    btn_gbp = types.InlineKeyboardButton(f"💷 GBP: {settings['gbp_rate']}", callback_data="set_gbp")
    btn_com = types.InlineKeyboardButton(f"📈 Комиссия: +{comm_pct}%", callback_data="set_com")
    btn_disc = types.InlineKeyboardButton(f"🏷️ Скидка дня: {f'-{disc}%' if disc > 0 else 'Выкл'}", callback_data="set_disc")
    btn_status = types.InlineKeyboardButton("🔄 Обновить статус", callback_data="show_status")
    
    markup.add(btn_usd, btn_eur)
    markup.add(btn_gbp, btn_com)
    markup.add(btn_disc)
    markup.add(btn_status)
    return markup

@bot.message_handler(commands=['start', 'settings'])
def show_settings_panel(message):
    bot.send_message(
        message.chat_id, 
        "Привет, Богиня! 👑 Добро пожаловать в панель управления тарифами.\n\n"
        "Нажимайте на кнопки ниже, чтобы мгновенно изменить курсы, общую наценку или активировать глобальную скидку на сегодня. Посты, пересланные без команд, будут сразу пересчитываться по этим тарифам!", 
        reply_markup=get_settings_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    settings = load_settings()
    bot.answer_callback_query(call.id)
    
        if call.data == "show_status":
        comm_pct = int(round((settings["commission"] - 1.0) * 100))
      disc_val = settings.get("global_discount", 0)
    disc_text = f"-{disc_val}%" if disc_val > 0 else "Нет"

    text = (
        f"📊 **Текущие активные тарифы:**\n\n"
        f"🔹 Курс USD: {settings['usd_rate']} грн\n"
        f"🔹 Курс EUR: {settings['eur_rate']} грн\n"
        f"🔹 Курс GBP: {settings['gbp_rate']} грн\n"
        f"🔹 Ваша комиссия: +{comm_pct}%\n"
        f"🔹 Скидка дня: {disc_text}"
    )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_settings_keyboard(), parse_mode="Markdown")
        
    elif call.data in ["set_usd", "set_eur", "set_gbp", "set_com", "set_disc"]:
        prompt_texts = {
            "set_usd": "Введите новый курс доллара 🇺🇸 (например, 46.2):",
