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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8916051883:AAEDiJIcniHtsgmHGmw_qx4KrARoU7gC67g")
CHANNEL_ID = -1003735848662          # Канал "Брендменю" (Ваш)
CHANNEL_ID_SISTER = -1003857424835   # Канал "Шоппинг" (Сестры)
ARCHIVE_CHANNEL_ID = -1003783532522  # Ваш архив для утренних картинок

SETTINGS_FILE = "settings_v2.json"

# Базовые настройки по умолчанию для двух независимых профилей
DEFAULT_SETTINGS = {
    "my": {  # Профиль для Брендменю (Ваш)
        "usd_rate": 45.5, "eur_rate": 52.5, "gbp_rate": 61.5,
        "commission": 1.10, "global_discount": 0
    },
    "sis": {  # Профиль для Шоппинг (Сестры)
        "usd_rate": 45.5, "eur_rate": 52.5, "gbp_rate": 61.5,
        "commission": 1.10, "global_discount": 0
    }
}

def load_settings():
    """Загрузка раздельных настроек из файла памяти"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Сохранение раздельных настроек в память"""
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
    "💫 Доброго ранку! Нехай кожен момент сьогоднішнього дня приносить радість та натхнення! ✨",
    "🕊️ Мирного та тихого ранку! Нехай цей день буде безпечним, спокійним та принесе лише хороші новини! ✨",
    "☀️ Доброго ранку! Бажаю мирного неба над головою, затишку в оселі та гармонії в душі! ✨",
    "🌸 Чудового ранку! Нехай день пройде під мирним небом, спокійно та продуктивно! Бережіть себе! ❤️"
]

def morning_scheduler():
    """Function to automatically send exactly ONE morning post from the archive at 08:30 Kyiv time"""
    import pytz
    kiev_tz = pytz.timezone("Europe/Kyiv")
    already_sent = False
    
    while True:
        now = datetime.now(kiev_tz)
        current_time = now.strftime("%H:%M")
        
        if current_time == "08:30" and not already_sent:
            published = False
            potential_ids = list(range(1, 500))
            random.shuffle(potential_ids)
            
            for random_id in potential_ids:
                try:
                    caption_text = random.choice(DEFAULT_CAPTIONS)
                    bot.copy_message(
                        chat_id=CHANNEL_ID,
                        from_chat_id=ARCHIVE_CHANNEL_ID,
                        message_id=random_id,
                        caption=caption_text
                    )
                    try: bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=random_id)
                    except: pass
                    published = True
                    break
                except:
                    continue
            
            if not published:
                try: bot.send_message(chat_id=CHANNEL_ID, text=random.choice(DEFAULT_CAPTIONS))
                except: pass
            already_sent = True
        elif current_time != "08:30":
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

def clean_and_convert_text(text, profile="my"):
    """Умный калькулятор: берет изменяемые курсы и комиссии на основе профиля конкретного канала"""
    all_settings = load_settings()
    settings = all_settings.get(profile, all_settings["my"])
    
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
                except: continue
    else:
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            original_price, currency = fetch_price_from_url(urls)
            if original_price:
                rate = settings["usd_rate"] if currency == 'USD' else (settings["eur_rate"] if currency == 'EUR' else settings["gbp_rate"])
                final_price = math.ceil(original_price * discount_factor * rate * current_commission)
                text = f"{final_price}грн+вага\n{url}"

    text = text.replace("грн+вага+вага", "грн+вага")
    return text.strip()
# --- ИНТЕРАКТИВНАЯ КЛАВИАТУРА НАСТРОЕК (ДЛЯ ДВУХ ПРОФИЛЕЙ) ---
def get_settings_keyboard(user_id):
    all_settings = load_settings()
    # Если зашел главный админ канала Шоппинг (сестра) — даем ей профиль sis, иначе — ваш my
    profile = "sis" if str(user_id) == "222222222" or user_id == CHANNEL_ID_SISTER else "my"
    settings = all_settings[profile]
    
    comm_pct = int(round((settings["commission"] - 1) * 100))
    disc = settings["global_discount"]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_usd = types.InlineKeyboardButton(f"💵 USD: {settings['usd_rate']}", callback_data=f"set_usd_{profile}")
    btn_eur = types.InlineKeyboardButton(f"💶 EUR: {settings['eur_rate']}", callback_data=f"set_eur_{profile}")
    btn_gbp = types.InlineKeyboardButton(f"💷 GBP: {settings['gbp_rate']}", callback_data=f"set_gbp_{profile}")
    btn_com = types.InlineKeyboardButton(f"📈 Комиссия: +{comm_pct}%", callback_data=f"set_com_{profile}")
    btn_disc = types.InlineKeyboardButton(f"🏷️ Скидка дня: {f'-{disc}%' if disc > 0 else 'Выкл'}", callback_data=f"set_disc_{profile}")
    btn_status = types.InlineKeyboardButton("🔄 Обновить статус", callback_data=f"show_status_{profile}")
    
    markup.add(btn_usd, btn_eur)
    markup.add(btn_gbp, btn_com)
    markup.add(btn_disc)
    markup.add(btn_status)
    return markup

@bot.message_handler(commands=['start', 'settings'])
def show_settings_panel(message):
    profile_name = "Шоппинг 👭" if message.chat.id == CHANNEL_ID_SISTER else "Брендменю 🛍"
    bot.send_message(
        message.chat.id, 
        f"Привет, Богиня! 👑 Добро пожаловать в панель управления тарифами: **{profile_name}**.\n\n"
        "Нажимайте на кнопки ниже, чтобы мгновенно изменить курсы, общую наценку или активировать глобальную скидку дня. Ваши личные настройки полностью независимы!", 
        reply_markup=get_settings_keyboard(message.chat.id),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    all_settings = load_settings()
    bot.answer_callback_query(call.id)
    
    # Определяем какой профиль редактируется на основе хвоста callback_data (_my или _sis)
    profile = "sis" if call.data.endswith("_sis") else "my"
    settings = all_settings[profile]
    profile_title = "Шоппинг 👭" if profile == "sis" else "Брендменю 🛍"
    
    if call.data.startswith("show_status_"):
        comm_pct = int(round((settings["commission"] - 1) * 100))
        disc_val = settings.get("global_discount", 0)
        
        text = (
            f"📊 Текущие тарифы панели **{profile_title}**:\n"
            f"• Курс USD: {settings['usd_rate']} грн\n"
            f"• Курс EUR: {settings['eur_rate']} грн\n"
            f"• Курс GBP: {settings['gbp_rate']} грн\n"
            f"• Ваша комиссия: +{comm_pct}%\n"
            f"• Скидка дня: {f'-{disc_val}%' if disc_val > 0 else 'Нет'}"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_settings_keyboard(call.message.chat.id))
        
    elif any(call.data.startswith(x) for x in ["set_usd_", "set_eur_", "set_gbp_", "set_com_", "set_disc_"]):
        action = call.data.split("_")[1] # usd, eur, gbp, com, disc
        prompt_texts = {
            "usd": f"[{profile_title}] Введите новый курс доллара 🇺🇸:",
            "eur": f"[{profile_title}] Введите новый курс евро 🇪🇺:",
            "gbp": f"[{profile_title}] Введите новый курс фунта 🇬🇧:",
            "com": f"[{profile_title}] Введите процент комиссии 📈 (только цифру):",
            "disc": f"[{profile_title}] Введите глобальную скидку дня 🏷️ в % (или 0):"
        }
        msg = bot.send_message(call.message.chat.id, prompt_texts[action])
        bot.register_next_step_handler(msg, process_setting_input, action, profile)
    # --- ЛОГИКА МАССОВОЙ ПУБЛИКАЦИИ С ИДЕАЛЬНЫМ ПОРЯДКОМ И ЗАЩИТОЙ ---
    elif call.data in ["pub_my", "pub_sis", "pub_both"]:
        user_id = call.message.chat.id
        queue = USER_BUFFERS.get(user_id, [])
        
        if not queue:
            bot.send_message(user_id, "❌ Ваша корзина заготовок пуста! Отправьте сначала посты.")
            return
            
        target_channels = []
        if call.data == "pub_my": target_channels = [CHANNEL_ID]
        elif call.data == "pub_sis": target_channels = [CHANNEL_ID_SISTER]
        elif call.data == "pub_both": target_channels = [CHANNEL_ID, CHANNEL_ID_SISTER]
        
        bot.edit_message_text(f"⏳ Публикую массив из **{len(queue)}** постов в строгом порядке получения...", chat_id=user_id, message_id=call.message.message_id)
        
        # Сортируем строго по хронологии захода в бот
        queue.sort(key=lambda x: x["position"])
        
        success_count = 0
        try:
            for item in queue:
                msg_type = item["type"]
                file_id = item["file_id"]
                raw_text = item["raw_original_text"] # Берем чистый исходник, чтобы пересчитать по тарифам конкретного канала!
                
                # Зачищаем старые подписи, если они были
                if raw_text and "🛍 Для замовлень 🛍" in raw_text:
                    raw_text = raw_text.split("🛍 Для замовлень 🛍")[0].strip()
                
                for ch_id in target_channels:
                    # Бот автоматически пересчитывает один и тот же пост по индивидуальным тарифам выбранного канала!
                    current_profile = "my" if ch_id == CHANNEL_ID else "sis"
                    msg_text = clean_and_convert_text(raw_text, current_profile) if raw_text else ""
                    
                    if msg_text:
                        if ch_id == CHANNEL_ID:
                            signature = (
                                "\n\n🛍 Для замовлень 🛍\n"
                                "бандлер https://bunddler.com\n"
                                "📲для зв'язку: @LankaMurrr"
                            )
                        else:
                            signature = (
                                "\n\n🛍 Для замовлень 🛍\n"
                                "бандлер https://bunddler.com\n"
                                "📲для зв'язку: @nata_c_he"
                            )
                        final_text = f"{msg_text}{signature}"
                    else:
                        final_text = ""
                    
                    if msg_type == 'text':
                        bot.send_message(chat_id=ch_id, text=final_text, parse_mode="HTML", disable_web_page_preview=True)
                    elif msg_type == 'photo':
                        bot.send_photo(chat_id=ch_id, photo=file_id, caption=final_text if final_text else None, parse_mode="HTML")
                    elif msg_type == 'video':
                        bot.send_video(chat_id=ch_id, video=file_id, caption=final_text if final_text else None, parse_mode="HTML")
                
                success_count += 1
                time.sleep(3.5)  # Плавный интервал от флуда
                
            USER_BUFFERS[user_id] = []  # Чистим буфер
            bot.send_message(user_id, f"✅ Успешно выгружено **{success_count}** постов строго по вашему порядку!")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка отправки на {success_count}-м посте: {e}")

def process_setting_input(message, action, profile):
    try:
        val = float(message.text.replace(',', '.').strip())
        all_settings = load_settings()
        
        if action == "usd": all_settings[profile]["usd_rate"] = val
        elif action == "eur": all_settings[profile]["eur_rate"] = val
        elif action == "gbp": all_settings[profile]["gbp_rate"] = val
        elif action == "com": all_settings[profile]["commission"] = 1 + (val / 100)
        elif action == "disc": all_settings[profile]["global_discount"] = int(val)
        
        save_settings(all_settings)
        bot.send_message(message.chat.id, "✅ Настройки успешно сохранены в память профиля! Нажмите /settings для проверки.")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка ввода числа. Нажмите /settings и попробуйте снова.")

# --- УМНЫЙ ХЕНДЛЕР СБОРА ПОСТОВ В КОРЗИНУ ---
USER_BUFFERS = {}

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    text = message.text or message.caption or ""
    user_id = message.chat.id
    
    if text.startswith('/'): return
    
    if user_id not in USER_BUFFERS:
        USER_BUFFERS[user_id] = []
        
    if text.strip().lower() in ["давай", "давай ", "готово", "пуск"]:
        queue_len = len(USER_BUFFERS[user_id])
        if queue_len == 0:
            bot.send_message(user_id, "🫙 Корзина пуста. Сначала накидайте постов!")
            return
            
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_my = types.InlineKeyboardButton("🛍️ В Брендменю", callback_data="pub_my")
        btn_sis = types.InlineKeyboardButton("👭 В Шоппинг", callback_data="pub_sis")
        btn_both = types.InlineKeyboardButton("🌍 В оба канала", callback_data="pub_both")
        markup.add(btn_my, btn_sis)
        markup.add(btn_both)
        
        bot.send_message(user_id, f"📦 Собрано **{queue_len}** постов. Порядок зафиксирован!\nКуда отправляем эту серию анонсов?", reply_markup=markup)
        return

    current_position = len(USER_BUFFERS[user_id]) + 1
    file_id = None
    if message.content_type == 'photo': file_id = message.photo[-1].file_id
    elif message.content_type == 'video': file_id = message.video.file_id
    
    # Сохраняем ЧИСТЫЙ исходный текст. Пересчет произойдет в момент клика на нужный канал!
    USER_BUFFERS[user_id].append({
        "type": message.content_type,
        "file_id": file_id,
        "raw_original_text": text,
        "position": current_position
    })
    
    bot.reply_to(message, f"📥 Пост {current_position} успешно добавлен в серию. Когда закончите, напишите слово **Давай**")

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=morning_scheduler, daemon=True)
    scheduler_thread.start()
    
    import os
    port = int(os.environ.get("PORT", 10000))
    os.system(f"python -m http.server {port} &")
    
    print("[+] Бот успешно запущен на два раздельных профиля...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
