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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8310351083:AAFSw5Y-KC3C5TE6sMuS_m3wWiw6uY7z_kQ")
CHANNEL_ID = -1003735848662          # Ваш главный канал для постов
CHANNEL_ID_SISTER = -1003857424835   # Реальный ID канала вашей сестры
ARCHIVE_CHANNEL_ID = -1003783532522  # Ваш архив для утренних картинок

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
    "🕊️ Мирного та тихого ранку! Нехай цей день буде безпечним, спокійным та принесе лише хороші новини! ✨",
    "☀️ Доброго ранку! Бажаю мирного неба над головою, затишку в оселі та гармонії в душі! ✨",
    "🌸 Чудового ранку! Нехай день пройде под мирним небом, спокійно та продуктивно! Бережіть себе! ❤️"
]

def morning_scheduler():
    """Функция автоматической отправки строго ОДНОГО утреннего поста строго в 08:30 по Киеву"""
    import pytz
    kiev_tz = pytz.timezone("Europe/Kyiv")
    already_sent = False
    
    while True:
        now = datetime.now(kiev_tz)
        current_time = now.strftime("%H:%M")
        
        if current_time == "08:30" and not already_sent:
            published = False
            
            # Собираем список возможных ID (от 1 до 500) и перемешиваем их в случайном порядке
            potential_ids = list(range(1, 500))
            random.shuffle(potential_ids)
            
            # Проверяем перемешанные ID по одному, пока не найдем ПЕРВЫЙ живой пост
            for random_id in potential_ids:
                try:
                    caption_text = random.choice(DEFAULT_CAPTIONS)
                    
                    # Пробуем скопировать этот пост. Если он существует — он опубликуется
                    bot.copy_message(
                        chat_id=CHANNEL_ID,
                        from_chat_id=ARCHIVE_CHANNEL_ID,
                        message_id=random_id,
                        caption=caption_text
                    )
                    
                    # Пытаемся удалить его из архива, чтобы он больше не повторялся
                    try:
                        bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=random_id)
                    except:
                        pass
                        
                    published = True
                    break  # 🔥 СТРОГИЙ СТОП-КРАН: Как только ОДИН пост отправлен, цикл ПОЛНОСТЬЮ прекращается!
                except:
                    continue  # Если ID пустой, просто идем дальше
            
            # Резервный вариант на случай, если архив абсолютно пуст
            if not published:
                try:
                    bot.send_message(chat_id=CHANNEL_ID, text=random.choice(DEFAULT_CAPTIONS))
                except:
                    pass
                    
            already_sent = True
        elif current_time != "08:30":
            already_sent = False
        time.sleep(30)
        
       def fetch_price_from_url(url):
    """Резервный парсер сайтов"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

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
    
    discount_factor = 1.0
    discount_match = re.search(r'-(\d+)%', text)
    if discount_match:
        discount_factor = (100 - int(discount_match.group(1))) / 100
    elif settings["global_discount"] > 0:
        discount_factor = (100 - settings["global_discount"]) / 100

    current_commission = 1.05 if "crocs" in text.lower() else settings["commission"]

    currency_pattern = r'(?:[$€£]\s*)?\d+(?:[\.,]\d+)?(?:\s*[$€£])?'
    matches = [m.group() for m in re.finditer(currency_pattern, text) if any(s in m.group() for s in '$€£')]
    
    if matches:
        unique_matches = list(dict.fromkeys(matches))
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
                    
                    uah_price = math.ceil(price_val * discount_factor * rate * current_commission)
                    text = text.replace(raw_match, f"{uah_price}грн+вага")
                except:
                    continue
    else:
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            original_price, currency = fetch_price_from_url(urls)
            if original_price:
                rate = settings["usd_rate"] if currency == 'USD' else (settings["eur_rate"] if currency == 'EUR' else settings["gbp_rate"])
                final_price = math.ceil(original_price * discount_factor * rate * current_commission)
                lines = text.split('\n')
                lines = f"{final_price}грн+вага"
                text = '\n'.join(lines)

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
        message.chat.id, 
        "Привет, Богиня! 👑 Добро пожаловать в панель управления тарифами.\n\n"
        "Нажимайте на кнопки ниже, чтобы мгновенно изменить курсы, общую наценку или активировать глобальную скидку на сегодня. Посты, пересланные без команд, будут сразу пересчитываться по этим тарифам!", 
        reply_markup=get_settings_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    settings = load_settings()
    bot.answer_callback_query(call.id)
    
    if call.data == "show_status":
        comm_pct = int(round((settings["commission"] - 1) * 100))
        disc_val = settings.get("global_discount", 0)
        
        text = (
            f"📊 Текущие активные тарифы:\n"
            f"• Курс USD: {settings['usd_rate']} грн\n"
            f"• Курс EUR: {settings['eur_rate']} грн\n"
            f"• Курс GBP: {settings['gbp_rate']} грн\n"
            f"• Ваша комиссия: +{comm_pct}%\n"
            f"• Скидка дня: {f'-{disc_val}%' if disc_val > 0 else 'Нет'}"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_settings_keyboard())
        
    elif call.data in ["set_usd", "set_eur", "set_gbp", "set_com", "set_disc"]:
        prompt_texts = {
            "set_usd": "Введите новый курс доллара 🇺🇸 (например, 46.2):",
            "set_eur": "Введите новый курс евро 🇪🇺 (например, 53.1):",
            "set_gbp": "Введите новый курс фунта 🇬🇧 (например, 62.4):",
            "set_com": "Введите процент комиссии 📈 (только цифру, например 12 если хотите +12%):",
            "set_disc": "Введите глобальную скидку дня 🏷️ в % (например 20, или 0 чтобы выключить её):"
        }
        msg = bot.send_message(call.message.chat.id, prompt_texts[call.data])
        bot.register_next_step_handler(msg, process_setting_input, call.data)
        
    # --- ЛОГИКА КНОПОК ОТПРАВКИ В КАНАЛЫ ---
    elif call.data in ["pub_my", "pub_sis", "pub_both"]:
        msg_text = call.message.text or call.message.caption or ""
        if "Предпросмотр анонса:" in msg_text:
            msg_text = msg_text.replace("📝 Предпросмотр анонса:\n\n", "")
            
        target_channels = []
        if call.data == "pub_my": target_channels = [CHANNEL_ID]
        elif call.data == "pub_sis": target_channels = [CHANNEL_ID_SISTER]
        elif call.data == "pub_both": target_channels = [CHANNEL_ID, CHANNEL_ID_SISTER]
        
        try:
            for ch_id in target_channels:
                if call.message.content_type == 'text':
                    bot.send_message(chat_id=ch_id, text=msg_text, parse_mode="HTML", disable_web_page_preview=True)
                elif call.message.content_type == 'photo':
                    bot.send_photo(chat_id=ch_id, photo=call.message.photo[-1].file_id, caption=msg_text, parse_mode="HTML")
                elif call.message.content_type == 'video':
                    bot.send_video(chat_id=ch_id, video=call.message.video.file_id, caption=msg_text, parse_mode="HTML")
            
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, "🚀 Пост успешно опубликован в выбранные каналы!")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Ошибка публикации: {e}. Убедитесь, что бот добавлен в админы каналов.")

def process_setting_input(message, action):
    try:
        val = float(message.text.replace(',', '.').strip())
        settings = load_settings()
        
        if action == "set_usd": settings["usd_rate"] = val
        elif action == "set_eur": settings["eur_rate"] = val
        elif action == "set_gbp": settings["gbp_rate"] = val
        elif action == "set_com": settings["commission"] = 1 + (val / 100)
        elif action == "set_disc": settings["global_discount"] = int(val)
        
        save_settings(settings)
        bot.send_message(message.chat.id, "✅ Настройки успешно обновлены и сохранены в память! Нажмите /settings чтобы увидеть новую панель.")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Нужно ввести корректное число. Попробуйте снова через меню /settings.")

# --- ХЕНДЛЕР ПРИЕМА АНОНСОВ ДЛЯ ПРЕДПРОСМОТРА ---
@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    text = message.text or message.caption or ""
    if not text: return
    if text.startswith('/'): return
    
    new_text = clean_and_convert_text(text)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_my = types.InlineKeyboardButton("🛍️ В мой канал", callback_data="pub_my")
    btn_sis = types.InlineKeyboardButton("👭 В канал сестры", callback_data="pub_sis")
    btn_both = types.InlineKeyboardButton("🌍 В оба канала", callback_data="pub_both")
    markup.add(btn_my, btn_sis)
    markup.add(btn_both)
    
    try:
        if message.content_type == 'text':
            bot.send_message(message.chat.id, f"📝 **Предпросмотр анонса:**\n\n{new_text}", parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        elif message.content_type == 'photo':
            bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=new_text, parse_mode="HTML", reply_markup=markup)
        elif message.content_type == 'video':
            bot.send_video(message.chat.id, video=message.video.file_id, caption=new_text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        bot.reply_to(message, f"Ошибка предпросмотра: {e}")

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=morning_scheduler, daemon=True)
    scheduler_thread.start()
    
    import os
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    
    print("[+] Бот успешно запущен и готов к работе...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
