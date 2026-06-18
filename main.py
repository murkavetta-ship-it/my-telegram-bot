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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8016051883:AAED1JiCniHttsmnGmw_qx4kRArOU7gC67g")
CHANNEL_ID = -1002373540662          # Канал "Брендменю" (Ваш)
CHANNEL_ID_SISTER = -1001857424835   # Канал "Шоппинг" (Сестры)
ARCHIVE_CHANNEL_ID = -1001783532522  # Ваш архив для утренних картинок

SETTINGS_FILE = "settings_v2.json"

USER_BUFFERS = {}
ALBUM_BUFFERS = {}

DEFAULT_SETTINGS = {
    "my": {
        "usd_rate": 45.5, "eur_rate": 52.5, "gbp_rate": 61.5,
        "commission": 1.10, "global_discount": 0, "use_signature": True
    },
    "sis": {
        "usd_rate": 45.5, "eur_rate": 52.5, "gbp_rate": 61.5,
        "commission": 1.10, "global_discount": 0, "use_signature": True
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
    except:
        pass

bot = telebot.TeleBot(BOT_TOKEN)

DEFAULT_CAPTIONS = [
    "☀️Доброго ранку! Гарного та продуктивного дня! 💐",
    "☕️Ранок починається з кави та гарного настрою! Бажаю всім вдалого дня! ❤️",
    "☀️Прокидайтеся з посмішкою! Нехай сьогоднішній день принесе багато радості! ☀️",
    "✨Чудового ранку! Бажаю, щоб сьогодні все задумане вдалося! ❤️",
    "🌱Доброго ранку, красуні! Бажаю натхнення та яскравого дня! ❤️",
    "🌸Прекрасного ранку! Нехай цей день принесе море позитиву та вдалих знахідок! ✨",
    "☕️Доброго ранку! Нехай сьогоднішній день будет легким, сонячним та наповненим приємними моментами! ☕️",
    "🍩Затишного ранку та смачної кави! Бажаю чудового настрою на весь день! ❤️",
    "☀️Радісного ранку! Прокидайтеся та підкорюйте цей світ своєю посмішкою! Гарного дня! ☀️",
    "✨Доброго ранку! Нехай кожен момент сьогоднішнего дня приносить радість та натхнення! ✨",
    "🕊️Мирного та тихого ранку! Нехай цей день буде безпечним, спокійним та принесе лише хороші новини! ✨",
    "☀️Доброго ранку! Бажаю мирного неба над головою, затишку в оселі та гармонії в душі! ✨",
    "❤️Чудового ранку! Нехай день пройде під мирним небом, спокійно та продуктивно! Бережіть себе! ❤️"
]
def morning_scheduler():
    import pytz
    kiev_tz = pytz.timezone("Europe/Kyiv")
    morning_sent_today = False
    
    while True:
        try:
            now = datetime.now(kiev_tz)
            current_time = now.strftime("%H:%M")
            
            # --- 1. ОТЛОЖЕННЫЙ ПОСТИНГ ПО ТАЙМЕРАМ (Каждую минуту) ---
            for check_id in range(1, 600):
                try:
                    test_msg = bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=check_id)
                    bot.delete_message(chat_id=CHANNEL_ID, message_id=test_msg.message_id)
                    
                    txt = test_msg.text or test_msg.caption or ""
                    
                    match = re.search(r'#timer_(my|sis|both)_(\d{2}:\d{2})', txt)
                    if match and match.group(2) == current_time:
                        ch_type = match.group(1)
                        
                        target_channels = []
                        if ch_type == "my": target_channels = [CHANNEL_ID]
                        elif ch_type == "sis": target_channels = [CHANNEL_ID_SISTER]
                        elif ch_type == "both": target_channels = [CHANNEL_ID, CHANNEL_ID_SISTER]
                        
                        queue_item = {
                            "raw_original_text": txt.split(match.group(0))[-1].strip(),
                            "type": "album" if test_msg.media_group_id else test_msg.content_type,
                            "file_id": test_msg.photo[-1].file_id if test_msg.content_type == 'photo' else (test_msg.video.file_id if test_msg.content_type == 'video' else None)
                        }
                        
                        ids_to_delete = [check_id]
                        
                        if test_msg.media_group_id:
                            album_pieces = [test_msg]
                            for n_id in range(check_id - 5, check_id + 6):
                                if n_id == check_id: continue
                                try:
                                    s_msg = bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=n_id)
                                    bot.delete_message(chat_id=CHANNEL_ID, message_id=s_msg.message_id)
                                    if s_msg.media_group_id == test_msg.media_group_id:
                                        album_pieces.append(s_msg)
                                        ids_to_delete.append(n_id)
                                except: continue
                            album_pieces.sort(key=lambda x: x.message_id)
                            queue_item["file_id"] = [{"type": p.content_type, "file_id": p.photo[-1].file_id if p.content_type == 'photo' else p.video.file_id} for p in album_pieces]
                        
                        execute_instant_publication([queue_item], target_channels, None)
                        
                        for d_id in ids_to_delete:
                            try: bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=d_id)
                            except: pass
                except:
                    continue

            # --- 2. УТРЕННИЙ ПОСТ В 08:30 ---
            if current_time == "08:30" and not morning_sent_today:
                morning_published = False
                potential_morning_ids = list(range(1, 500))
                random.shuffle(potential_morning_ids)
                
                for r_id in potential_morning_ids:
                    try:
                        caption_text = random.choice(DEFAULT_CAPTIONS)
                        probe_msg = bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=r_id)
                        bot.delete_message(chat_id=CHANNEL_ID, message_id=probe_msg.message_id)
                        
                        morning_ids_delete = [r_id]
                        
                        if probe_msg.media_group_id:
                            m_album = [probe_msg]
                            m_tg_id = probe_msg.media_group_id
                            
                            for c_id in range(r_id - 5, r_id + 6):
                                if c_id == r_id: continue
                                try:
                                    s_msg = bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=c_id)
                                    bot.delete_message(chat_id=CHANNEL_ID, message_id=s_msg.message_id)
                                    if s_msg.media_group_id == m_tg_id:
                                        m_album.append(s_msg)
                                        morning_ids_delete.append(c_id)
                                except: continue
                                    
                            m_album.sort(key=lambda x: x.message_id)
                            media_group = []
                            for index, msg in enumerate(m_album):
                                current_caption = caption_text if index == 0 else None
                                if msg.photo: media_group.append(types.InputMediaPhoto(msg.photo[-1].file_id, caption=current_caption))
                                elif msg.video: media_group.append(types.InputMediaVideo(msg.video.file_id, caption=current_caption))
                                    
                            bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
                            morning_published = True
                        else:
                            bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=r_id, caption=caption_text)
                            morning_published = True
                            
                        if morning_published:
                            for msg_id in morning_ids_delete:
                                try: bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=msg_id)
                                except: pass
                            morning_sent_today = True
                            break
                    except:
                        continue
                
                if not morning_published:
                    try: bot.send_message(chat_id=CHANNEL_ID, text=random.choice(DEFAULT_CAPTIONS))
                    except: pass
                    morning_sent_today = True
                    
            elif current_time != "08:30":
                morning_sent_today = False

        except Exception as e:
            print(f"[-] Ошибка планировщика: {e}")
            
        time.sleep(60)

def fetch_price_from_url(url):
    """Ваш оригинальный парсер сайтов"""
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
                cleaned = re.sub(r'[^\d.,]', '', text).replace(',', '.')
                try:
                    val = float(cleaned)
                    if 0.5 < val < 5000: potential_prices.append(val)
                except: continue
        if potential_prices: return min(potential_prices), currency
    except: pass
    return None, None
def clean_and_convert_text(text, profile="my"):
    """Ваш умный калькулятор с поддержкой точек и запятых в копейках"""
    all_settings = load_settings()
    settings = all_settings.get(profile, all_settings["my"])
    
    discount_factor = 1.0
    discount_match = re.search(r'-\s*(\d+)%', text)
    if discount_match:
        discount_factor = (100 - int(discount_match.group(1))) / 100
    elif settings.get("global_discount", 0) > 0:
        discount_factor = (100 - settings["global_discount"]) / 100
        
    current_commission = 1.05 if "crocs" in text.lower() else settings["commission"]
    
    # Регулярка теперь видит и точки, и запятые!
    currency_pattern = r'(?:\$[\d\s.,]+)|(?:[\d\s.,]+\$)|(?:€[\d\s.,]+)|(?:[\d\s.,]+€)|(?:£[\d\s.,]+)|(?:[\d\s.,]+£)'
    matches = [m.group() for m in re.finditer(currency_pattern, text)] if any(s in text for s in '$€£') else []
    
    if matches:
        unique_matches = list(dict.fromkeys(matches))
        for raw_match in unique_matches:
            price_digit_match = re.search(r'\d+(?:[.,]\d+)?', raw_match)
            symbol_match = re.search(r'[\$€£]', raw_match)
            
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
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            original_price, currency = fetch_price_from_url(urls)
            if original_price:
                rate = settings["usd_rate"] if currency == 'USD' else (settings["eur_rate"] if currency == 'EUR' else settings["gbp_rate"])
                final_price = math.ceil(original_price * discount_factor * rate * current_commission)
                text = f"{final_price}грн+вага\n{urls}"
                
    text = text.replace("грн+вага+вага", "грн+вага")
    return text.strip()

def get_settings_keyboard(user_id):
    all_settings = load_settings()
    profile = "sis" if str(user_id) == "222222222" or user_id == CHANNEL_ID_SISTER else "my"
    settings = all_settings[profile]
    
    comm_pct = int(round((settings["commission"] - 1) * 100))
    disc = settings["global_discount"]
    
    sig_status = settings.get("use_signature", True)
    sig_text = "✍️ Подпись: ✅ Включена" if sig_status else "✍️ Подпись: ❌ Выключена"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_usd = types.InlineKeyboardButton(f"💵 USD: {settings['usd_rate']}", callback_data=f"set_usd_{profile}")
    btn_eur = types.InlineKeyboardButton(f"💶 EUR: {settings['eur_rate']}", callback_data=f"set_eur_{profile}")
    btn_gbp = types.InlineKeyboardButton(f"💷 GBP: {settings['gbp_rate']}", callback_data=f"set_gbp_{profile}")
    btn_com = types.InlineKeyboardButton(f"🧾 Комиссия: +{comm_pct}%", callback_data=f"set_com_{profile}")
    btn_disc = types.InlineKeyboardButton(f"🏷️ Скидка дня: {f'{disc}%' if disc > 0 else 'Выкл'}", callback_data=f"set_disc_{profile}")
    btn_sig = types.InlineKeyboardButton(sig_text, callback_data=f"toggle_sig_{profile}")
    btn_status = types.InlineKeyboardButton("🔄 Обновить статус", callback_data=f"show_status_{profile}")
    
    markup.add(btn_usd, btn_eur)
    markup.add(btn_gbp, btn_com)
    markup.add(btn_disc, btn_sig)
    markup.add(btn_status)
    return markup
@bot.message_handler(commands=['start', 'settings'])
def show_settings_panel(message):
    profile_name = "Шоппинг 🛍️" if message.chat.id == CHANNEL_ID_SISTER else "Брендменю 👑"
    bot.send_message(
        message.chat.id,
        f"Привет, Богиня! 👑 Добро пожаловать в панель управления тарифами: **{profile_name}**.\n\n"
        "Нажимайте на кнопки ниже, чтобы мгновенно изменить курсы, общую наценку или активировать глобальную скидку дня.",
        reply_markup=get_settings_keyboard(message.chat.id),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    all_settings = load_settings()
    bot.answer_callback_query(call.id)
    
    profile = "sis" if call.data.endswith("_sis") else "my"
    settings = all_settings[profile]
    profile_title = "Шоппинг 🛍️" if profile == "sis" else "Брендменю 👑"
    user_id = call.message.chat.id
    
    if call.data.startswith("toggle_sig_"):
        current_sig = settings.get("use_signature", True)
        all_settings[profile]["use_signature"] = not current_sig
        save_settings(all_settings)
        bot.edit_message_reply_markup(chat_id=user_id, message_id=call.message.message_id, reply_markup=get_settings_keyboard(user_id))
        return
    
    if call.data.startswith("show_status_"):
        comm_pct = int(round((settings["commission"] - 1) * 100))
        disc_val = settings.get("global_discount", 0)
        sig_status = settings.get("use_signature", True)
        sig_str = "Включена ✅" if sig_status else "Выключена ❌"
        
        text = (
            f"📊 Текущие тарифы панели **{profile_title}**:\n"
            f"🔹 Курс USD: {settings['usd_rate']} грн\n"
            f"🔹 Курс EUR: {settings['eur_rate']} грн\n"
            f"🔹 Курс GBP: {settings['gbp_rate']} грн\n"
            f"🔹 Ваша комиссия: +{comm_pct}%\n"
            f"🔹 Скидка дня: {f'{disc_val}%' if disc_val > 0 else 'Нет'}\n"
            f"🔹 Подпись анонсов: {sig_str}"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_settings_keyboard(call.message.chat.id), parse_mode="Markdown")
        return

    if call.data in ["time_now", "time_30m", "time_exact"]:
        if call.data == "time_exact":
            msg = bot.send_message(user_id, "⏰ Введите точное время публикации в формате **ЧЧ:ММ** по Киеву (например, `18:45`):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_exact_time_input)
            return
            
        import pytz
        kiev_tz = pytz.timezone("Europe/Kyiv")
        now = datetime.now(kiev_tz)
        
        if call.data == "time_now": target_time = "now"
        elif call.data == "time_30m":
            from datetime import timedelta
            target_time = (now + timedelta(minutes=30)).strftime("%H:%M")
            
        show_channel_selection(user_id, call.message.message_id, target_time)
        return

    if call.data.startswith("target_"):
        _, ch_type, target_time = call.data.split("_")
        queue = USER_BUFFERS.get(user_id, [])
        
        if not queue:
            bot.send_message(user_id, "❌ Ваша корзина заготовок пуста!")
            return
            
        target_channels = []
        if ch_type == "my": target_channels = [CHANNEL_ID]
        elif ch_type == "sis": target_channels = [CHANNEL_ID_SISTER]
        elif ch_type == "both": target_channels = [CHANNEL_ID, CHANNEL_ID_SISTER]
        
        if target_time == "now":
            bot.edit_message_text(f"⏳ Публикую массив из **{len(queue)}** постов в каналы...", chat_id=user_id, message_id=call.message.message_id)
            execute_instant_publication(queue, target_channels, user_id)
        else:
            bot.edit_message_text(f"⏰ Серия успешно запланирована на **{target_time}** по Киеву!", chat_id=user_id, message_id=call.message.message_id, parse_mode="Markdown")
            queue.sort(key=lambda x: x["position"])
            
            for index, item in enumerate(queue):
                prefix = f"#timer_{ch_type}_{target_time}\n" if index == 0 else ""
                raw_text = item["raw_original_text"] or ""
                combined_text = f"{prefix}{raw_text}"
                
                if item["type"] == 'text':
                    bot.send_message(chat_id=ARCHIVE_CHANNEL_ID, text=combined_text)
                elif item["type"] == 'album':
                    media_group = []
                    for idx, media_item in enumerate(item["file_id"]):
                        cap = combined_text if idx == 0 else None
                        if media_item["type"] == 'photo': media_group.append(types.InputMediaPhoto(media_item["file_id"], caption=cap))
                        elif media_item["type"] == 'video': media_group.append(types.InputMediaVideo(media_item["file_id"], caption=cap))
                    bot.send_media_group(chat_id=ARCHIVE_CHANNEL_ID, media=media_group)
                elif item["type"] == 'photo':
                    bot.send_photo(chat_id=ARCHIVE_CHANNEL_ID, photo=item["file_id"], caption=combined_text)
                elif item["type"] == 'video':
                    bot.send_video(chat_id=ARCHIVE_CHANNEL_ID, video=item["file_id"], caption=combined_text)
                    
            USER_BUFFERS[user_id] = []
        return

    if any(call.data.startswith(x) for x in ["set_usd_", "set_eur_", "set_gbp_", "set_com_", "set_disc_"]):
        action = call.data.split("_")
        prompt_texts = {
            "usd": f"[{profile_title}] Введите новый курс доллара us:",
            "eur": f"[{profile_title}] Введите новый курс евро eu:",
            "gbp": f"[{profile_title}] Введите новый курс фунта gb:",
            "com": f"[{profile_title}] Введите процент комиссии (только цифру):",
            "disc": f"[{profile_title}] Введите глобальную скидку дня 🏷️ в % (или 0):"
        }
        msg = bot.send_message(user_id, prompt_texts[action])
        bot.register_next_step_handler(msg, process_setting_input, action, profile)
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

def process_exact_time_input(message):
    user_id = message.chat.id
    time_text = message.text.strip()
    if re.match(r'^\d{2}:\d{2}$', time_text):
        show_channel_selection(user_id, None, time_text)
    else:
        bot.send_message(user_id, "❌ Неверный формат! Напишите время строго как `15:40`. Нажмите слово **Давай** заново, чтобы попробовать.")

def show_channel_selection(user_id, message_id, target_time):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_my = types.InlineKeyboardButton("🛍️ В  Брендменю", callback_data=f"target_my_{target_time}")
    btn_sis = types.InlineKeyboardButton("🛍️ В Шоппинг", callback_data=f"target_sis_{target_time}")
    btn_both = types.InlineKeyboardButton("🔵 В оба канала", callback_data=f"target_both_{target_time}")
    markup.add(btn_my, btn_sis)
    markup.add(btn_both)
    
    text_time = "прямо сейчас" if target_time == "now" else f"в {target_time}"
    if message_id:
        bot.edit_message_text(f"Серия будет отправлена **{text_time}**.\n\nКуда публикуем анонсы?", chat_id=user_id, message_id=message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"Серия будет отправлена **{text_time}**.\n\nКуда публикуем анонсы?", reply_markup=markup, parse_mode="Markdown")

def execute_instant_publication(queue, target_channels, user_id):
    success_count = 0
    all_settings = load_settings()
    
    for item in queue:
        msg_type = item["type"]
        file_id = item["file_id"]
        raw_text = item["raw_original_text"]
        
        for ch_id in target_channels:
            clean_text = raw_text
            if clean_text and "🛍️ Для замовлень 🛍️" in clean_text:
                clean_text = clean_text.split("🛍️ Для замовлень 🛍️")[0].strip()
                
            current_profile = "my" if ch_id == CHANNEL_ID else "sis"
            settings = all_settings.get(current_profile, {})
            
            if clean_text:
                clean_text = re.sub(r'📲?\s*(?:для зв\'язку|контакт|зв\'язок)?\s*:\s*@\w+', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'(?:бандлер|замовлення|сайт)?\s*https?://[^\s]+', '', clean_text, flags=re.IGNORECASE).strip()
                
            msg_text = clean_and_convert_text(clean_text, current_profile) if clean_text else ""
            
            if msg_text and settings.get("use_signature", True):
                if ch_id == CHANNEL_ID:
                    signature = (
                        "\n\n🛍️ Для замовлень 🛍️\n"
                        '<a href="https://brandmenu.bunddler.com">🛍™️𝐵𝓇𝒶𝓃𝒹𝑀𝑒𝓃𝓊🤩🌏</a>\n'
                        "📲для зв'язку: @LankaMurrr"
                    )
                else:
                    signature = (
                        "\n\n🛍️ Для замовлень 🛍️\n"
                        '<a href="https://nataliche16.bunddler.com">💖ШОПІНГ В США 🇺🇸ТА ЄВРОПІ🇪🇺💖</a>\n'
                        "📲для зв'язку: @nata_c_he"
                    )
                final_text = f"{msg_text}{signature}"
            else:
                final_text = msg_text or ""
                
            time.sleep(3.5)
            
            if msg_type == 'text':
                try: bot.send_message(chat_id=ch_id, text=final_text, parse_mode="HTML", disable_web_page_preview=True)
                except: pass
            elif msg_type == 'album':
                media_group = []
                for index, media_item in enumerate(file_id):
                    caption = final_text if index == 0 else None
                    if media_item["type"] == 'photo':
                        media_group.append(types.InputMediaPhoto(media_item["file_id"], caption=caption, parse_mode="HTML"))
                    elif media_item["type"] == 'video':
                        media_group.append(types.InputMediaVideo(media_item["file_id"], caption=caption, parse_mode="HTML"))
                try: bot.send_media_group(chat_id=ch_id, media=media_group)
                except: pass
            elif msg_type == 'photo':
                try:
                    if len(final_text) <= 1024:
                        bot.send_photo(chat_id=ch_id, photo=file_id, caption=final_text, parse_mode="HTML")
                    else:
                        bot.send_photo(chat_id=ch_id, photo=file_id)
                        bot.send_message(chat_id=ch_id, text=final_text, parse_mode="HTML", disable_web_page_preview=True)
                except: pass
            elif msg_type == 'video':
                try:
                    if len(final_text) <= 1024:
                        bot.send_video(chat_id=ch_id, video=file_id, caption=final_text, parse_mode="HTML")
                    else:
                        bot.send_video(chat_id=ch_id, video=file_id)
                        bot.send_message(chat_id=ch_id, text=final_text, parse_mode="HTML", disable_web_page_preview=True)
                except: pass
                
        success_count += 1
    if user_id:
        try: bot.send_message(user_id, f"✅ Успешно выгружено **{success_count}** постов строго по вашему порядку!")
        except: pass

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    # Железно вытаскиваем текст из любого типа сообщения
    text = message.text if message.text else (message.caption if message.caption else "")
    user_id = message.chat.id

    if user_id not in USER_BUFFERS: USER_BUFFERS[user_id] = []
    if text.startswith('/'): return

    if text.strip().lower() in ["давай", "давай ", "готово", "пуск"]:
        queue_len = len(USER_BUFFERS[user_id])
        if queue_len == 0:
            bot.send_message(user_id, "📥 Корзина пуста. Сначала накидайте постов!")
            return
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_now = types.InlineKeyboardButton("🚀 Прямо сейчас", callback_data="time_now")
        btn_30m = types.InlineKeyboardButton("⏱️ Через 30 минут", callback_data="time_30m")
        btn_exact = types.InlineKeyboardButton("⏰ Задать точное время", callback_data="time_exact")
        markup.add(btn_now, btn_30m, btn_exact)
        
        bot.send_message(user_id, f"📥 Собрано **{queue_len}** постов. Порядок зафиксирован!\n\nКогда выгружаем эту серию анонсов?", reply_markup=markup)
        return

    current_position = len(USER_BUFFERS[user_id]) + 1
    file_id = None
    if message.content_type == 'photo': file_id = message.photo[-1].file_id
    elif message.content_type == 'video': file_id = message.video.file_id

    def save_collected_album(mg_id, u_id, chat_id):
        pieces = ALBUM_BUFFERS.pop(mg_id, [])
        if not pieces: return
        pieces.sort(key=lambda x: x['msg_id'])
        
        combined_text = ""
        for p in pieces:
            if p['txt']:
                combined_text = p['txt']
                break
                
        media_list = [{"type": p["type"], "file_id": p["file_id"]} for p in pieces]
        pos = len(USER_BUFFERS[u_id]) + 1
        
        USER_BUFFERS[u_id].append({
            "type": "album",
            "file_id": media_list,
            "raw_original_text": combined_text,
            "position": pos
        })
        bot.send_message(chat_id, f"📥 Альбом (из {len(pieces)} медиа) успешно добавлен в серию под номером {pos}. Когда закончите, напишите слово **Давай**")

    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in ALBUM_BUFFERS:
            ALBUM_BUFFERS[mg_id] = []
            threading.Timer(1.5, save_collected_album, args=[mg_id, user_id, message.chat.id]).start()
            
        ALBUM_BUFFERS[mg_id].append({
            "msg_id": message.message_id,
            "type": message.content_type,
            "file_id": file_id,
            "txt": text
        })
    else:
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
    
    bot.remove_webhook()
    bot.polling(none_stop=True, skip_pending=True, timeout=60)
