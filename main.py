import os
import re
import time
import json
import math
import random
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types

# --- НАСТРОЙКИ БОТА ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8916051883:AAHSiQeFy6rtOSGDGgx0DIEO1weX1MQLw0Q")
CHANNEL_ID = -1003735848662      # Канал "Брендменю" (Ваш)
CHANNEL_ID_SISTER = -1001857424835 # Канал "Шоппинг" (Сестры)
ARCHIVE_CHANNEL_ID = -1001783532522 # Ваш архив для утренних картинок

SETTINGS_FILE = "settings_v2.json"

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
    except Exception as e:
        print(f"[-] Ошибка сохранения настроек: {e}")

bot = telebot.TeleBot(BOT_TOKEN)

DEFAULT_CAPTIONS = [
    "☀️ Доброго ранку! Гарного та продуктивного дня! 🌅",
    "☕️ Ранок починається з кави та гарного настрою! Бажаю всім вдалого дня! ❤️",
    "✨ Прокидайтеся з посмішкою! Нехай сьогоднішній день принесе багато радості! ☀️",
    "✨ Чудового ранку! Бажаю, щоб сьогодні все задумане вдалося! 🌸",
    "🌸 Доброго ранку, красуні! Бажаю натхнення та яскравого дня! ❤️",
    "✨ Прекрасного ранку! Нехай цей день принесе море позитиву та вдалих знахідок! ✨",
    "🔮 Доброго ранку! Нехай сьогоднішній день буде легким, сонячним та наповненим приємними моментами! 🍇",
    "☕️ Затишного ранку та смачної кави! Бажаю чувого настрою на весь день! ❤️",
    "☀️ Радісного ранку! Прокидайтеся та підкорюйте цей світ своєю посмішкою! ... Гарного дня! ☀️",
    "✨ Доброго ранку! Нехай кожен момент сьогоднішнього дня приносить радість та натхнення! ✨",
    "🕊 Мирного та тихого ранку! Нехай цей день буде безпечним, спокійним та принесе лише хороші новини! ✨",
    "✨ Доброго ранку! Бажаю мирного неба над головою, затишку в оселі та гармонії в душі! ✨",
    "💖 Чудового ранку! Нехай день пройде під мирним небом, спокійно та продуктивно! Бережіть себе! 💖"
]

def morning_scheduler():
    import pytz
    kiev_tz = pytz.timezone("Europe/Kyiv")
    morning_sent_today = False
    
    while True:
        try:
            from datetime import datetime
            now = datetime.now(kiev_tz)
            current_time = now.strftime("%H:%M")
            
            # --- 1. ОТЛОЖЕННЫЙ ПОСТИНГ ПО ТАЙМЕРАМ (Каждую минуту) ---
            # Бот аккуратно проверяет сообщения в архиве на наличие меток времени
            for check_id in range(1, 600):
                try:
                    # Временно пересылаем, чтобы прочитать скрытые метки
                    test_msg = bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=check_id)
                    bot.delete_message(chat_id=CHANNEL_ID, message_id=test_msg.message_id)
                    
                    txt = test_msg.text or test_msg.caption or ""
                    
                    # Ищем маркер таймера текущей минуты, например #timer_my_15:40
                    match = re.search(r'#timer_(my|sis|both)_(\d{2}):(\d{2})', txt)
                    if match and f"{match.group(2)}:{match.group(3)}" == current_time:
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
                                except:
                                    continue
                            album_pieces.sort(key=lambda x: x.message_id)
                        media_group = []
                        for index, p in enumerate(album_pieces):
                            caption = queue_item["raw_original_text"] if index == 0 else None
                            if p.content_type == 'photo':
                                media_group.append(types.InputMediaPhoto(p.photo[-1].file_id, caption=caption, parse_mode="HTML"))
                            elif p.content_type == 'video':
                                media_group.append(types.InputMediaVideo(p.video.file_id, caption=caption, parse_mode="HTML"))
                        
                        for ch_id in target_channels:
                            try:
                                bot.send_media_group(chat_id=ch_id, media=media_group)
                            except Exception as e:
                                print(f"[-] Ошибка отложенной отправки альбома: {e}")
                                
                        for d_id in ids_to_delete:
                            try: bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=d_id)
                            except: pass
                        time.sleep(60)
                        continue
                    else:
                        for ch_id in target_channels:
                            try:
                                if queue_item["type"] == 'photo':
                                    bot.send_photo(chat_id=ch_id, photo=queue_item["file_id"], caption=queue_item["raw_original_text"], parse_mode="HTML")
                                elif queue_item["type"] == 'video':
                                    bot.send_video(chat_id=ch_id, video=queue_item["file_id"], caption=queue_item["raw_original_text"], parse_mode="HTML")
                                elif queue_item["type"] == 'text':
                                    bot.send_message(chat_id=ch_id, text=queue_item["raw_original_text"], parse_mode="HTML", disable_web_page_preview=True)
                            except Exception as e:
                                print(f"[-] Ошибка отложенной отправки одиночного: {e}")
                                
                        try: bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=check_id)
                        except: pass
                        time.sleep(60)
                        continue
                except:
                    continue

            # --- 2. ОРИГИНАЛЬНЫЙ УТРЕННИЙ ПОСТ В 08:30 ---
            if current_time == "08:30" and not morning_sent_today:
                caption_text = random.choice(DEFAULT_CAPTIONS)
                r_id = random.randint(1, 1000)
                
                try:
                    test_msg = bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=r_id)
                    bot.delete_message(chat_id=CHANNEL_ID, message_id=test_msg.message_id)
                except:
                    continue
                    
                morning_published = False
                morning_ids_delete = [r_id]
                
                if test_msg.media_group_id:
                    m_tg_id = test_msg.media_group_id
                    m_album = [test_msg]
                    
                    for c_id in range(r_id - 5, r_id + 6):
                        if c_id == r_id: continue
                        try:
                            s_msg = bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=ARCHIVE_CHANNEL_ID, message_id=c_id)
                            bot.delete_message(chat_id=CHANNEL_ID, message_id=s_msg.message_id)
                            if s_msg.media_group_id == m_tg_id:
                                m_album.append(s_msg)
                                morning_ids_delete.append(c_id)
                        except:
                            continue
                            
                    m_album.sort(key=lambda x: x.message_id)
                    
                    media_group = []
                    for index, msg in enumerate(m_album):
                        caption = f"{caption_text}\n\n{msg.caption}" if index == 0 and msg.caption else (caption_text if index == 0 else None)
                        if msg.content_type == 'photo':
                            media_group.append(types.InputMediaPhoto(msg.photo[-1].file_id, caption=caption))
                        elif msg.content_type == 'video':
                            media_group.append(types.InputMediaVideo(msg.video.file_id, caption=caption))
                    
                    try:
                        bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
                        morning_published = True
                    except Exception as e:
                        print(f"[-] Ошибка отправки утреннего альбома: {e}")
                else:
                    caption = f"{caption_text}\n\n{test_msg.caption}" if test_msg.caption else caption_text
                    try:
                        if test_msg.content_type == 'photo':
                            bot.send_photo(chat_id=CHANNEL_ID, photo=test_msg.photo[-1].file_id, caption=caption)
                        elif test_msg.content_type == 'video':
                            bot.send_video(chat_id=CHANNEL_ID, video=test_msg.video.file_id, caption=caption)
                        morning_published = True
                    except Exception as e:
                        print(f"[-] Ошибка отправки одиночного утреннего поста: {e}")
                
                if morning_published:
                    morning_sent_today = True
                    for d_id in morning_ids_delete:
                        try: bot.delete_message(chat_id=ARCHIVE_CHANNEL_ID, message_id=d_id)
                        except: pass
            
            if current_time == "00:00":
                morning_sent_today = False
                
        except Exception as e:
            print(f"[-] Ошибка планировщика: {e}")
            
        time.sleep(60)
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
                cleaned = re.sub(r'[^\d.,]', '', text).replace(',', '.')
                try:
                    val = float(cleaned)
                    if 0.5 < val < 5000: potential_prices.append(val)
                except:
                    continue
        if potential_prices: return min(potential_prices), currency
    except:
        pass
    return None, None

def clean_and_convert_text(text, profile="my"):
    """Умный калькулятор: берет изменяемые курсы и комиссии на основе профиля конкретного канала"""
    all_settings = load_settings()
    settings = all_settings.get(profile, all_settings["my"])
    
    discount_factor = 1.0
    discount_match = re.search(r'-\s*(\d+)%', text)
    if discount_match:
        discount_factor = (100 - int(discount_match.group(1))) / 100
    elif settings.get("global_discount", 0) > 0:
        discount_factor = (100 - settings["global_discount"]) / 100
        
    current_commission = 1.05 if "crocs" in text.lower() else settings["commission"]
    
    currency_pattern = r'(?:\$[\s\d]+)|(?:[\d\s]+\$)|(?:€[\d\s]+)|(?:[\d\s]+€)|(?:£[\d\s]+)|(?:[\d\s]+£)'
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
                    
                    gah_price = math.ceil(price_val * discount_factor * rate * current_commission)
                    text = text.replace(raw_match, f"{gah_price}грн+вага")
                except:
                    continue
    else:
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            original_price, currency = fetch_price_from_url(urls)
            if original_price:
                rate = settings["usd_rate"] if currency == 'USD' else (settings["eur_rate"] if currency == 'EUR' else settings["gbp_rate"])
                final_price = math.ceil(original_price * discount_factor * rate * current_commission)
                text = f"{final_price}грн+вага\n\n{urls}"
                
    text = text.replace("грн+вага+вага", "грн+вага")
    return text.strip()

def get_settings_keyboard(user_id):
    all_settings = load_settings()
    profile = "sis" if str(user_id) == "222222222" or user_id == CHANNEL_ID_SISTER else "my"
    settings = all_settings[profile]
    
    comm_pct = int(round((settings["commission"] - 1) * 100))
    disc = settings["global_discount"]
    
    sig_status = settings.get("use_signature", True)
    sig_text = f"🔸 Подпись: 🟢 Включена" if sig_status else f"🔸 Подпись: 🔴 Выключена"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_usd = types.InlineKeyboardButton(f"💵 USD: {settings['usd_rate']}", callback_data=f"set_usd_{profile}")
    btn_eur = types.InlineKeyboardButton(f"💶 EUR: {settings['eur_rate']}", callback_data=f"set_eur_{profile}")
    btn_gbp = types.InlineKeyboardButton(f"💷 GBP: {settings['gbp_rate']}", callback_data=f"set_gbp_{profile}")
    btn_com = types.InlineKeyboardButton(f"💼 Комиссия: +{comm_pct}%", callback_data=f"set_com_{profile}")
    btn_disc = types.InlineKeyboardButton(f"🏷️ Скидка дня: {f'{disc}%' if disc > 0 else 'Выкл'}", callback_data=f"set_disc_{profile}")
    btn_sig = types.InlineKeyboardButton(sig_text, callback_data=f"toggle_sig_{profile}")
    btn_status = types.InlineKeyboardButton("🔄 Обновить статус", callback_data=f"show_status_{profile}")
    
    markup.add(btn_usd, btn_eur)
    markup.add(btn_gbp, btn_com)
    markup.add(btn_disc, btn_sig)
    markup.add(btn_status)
    return markup

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
            f"💵 Курс USD: {settings['usd_rate']} грн\n"
            f"💶 Курс EUR: {settings['eur_rate']} грн\n"
            f"💷 Курс GBP: {settings['gbp_rate']} грн\n"
            f"💼 Ваша комиссия: +{comm_pct}%\n"
            f"🏷️ Скидка дня: {f'{disc_val}%' if disc_val > 0 else 'Нет'}\n"
            f"✍️ Подпись анонсов: {sig_str}"
        )
        bot.edit_message_text(text, chat_id=user_id, message_id=call.message.message_id, reply_markup=get_settings_keyboard(call.message.chat.id), parse_mode="Markdown")
        return

    if call.data in ["pub_my", "pub_sis", "pub_both"]:
        user_id = call.message.chat.id
        queue = USER_BUFFERS.get(user_id, [])
        
        if not queue:
            bot.send_message(user_id, "❌ Ваша корзина заготовок пуста! Отправьте сначала посты.")
            return
            
        target_channels = []
        if call.data == "pub_my": target_channels = [CHANNEL_ID]
        elif call.data == "pub_sis": target_channels = [CHANNEL_ID_SISTER]
        elif call.data == "pub_both": target_channels = [CHANNEL_ID, CHANNEL_ID_SISTER]
        
        bot.edit_message_text(f"⏳ Публикую массив из **{len(queue)}** постов в строго полученном порядке...", chat_id=user_id, message_id=call.message.message_id)
        queue.sort(key=lambda x: x["position"])
        
        success_count = 0
        try:
            for item in queue:
                msg_type = item["type"]
                file_id = item["file_id"]
                raw_text = item["raw_original_text"]
                
                for ch_id in target_channels:
                    clean_raw_text = raw_text
                    if clean_raw_text:
                        if "🛒 Для замовлень 📩" in clean_raw_text:
                            clean_raw_text = clean_raw_text.split("🛒 Для замовлень 📩")[0].strip()
                        clean_raw_text = re.sub(r'(\s*Для зв\'язку|контакт|зв\'язок)?\s*:\s*@\w+', '', clean_raw_text, flags=re.IGNORECASE)
                        clean_raw_text = re.sub(r'(?:бандлер|замовлення|сайт)?\s*https?://[^\s]+', '', clean_raw_text, flags=re.IGNORECASE)
                        clean_raw_text = clean_raw_text.strip()
                        
                    current_profile = "my" if ch_id == CHANNEL_ID else "sis"
                    msg_text = clean_and_convert_text(clean_raw_text, current_profile) if clean_raw_text else ""
                    
                    if msg_text:
                        if ch_id == CHANNEL_ID:
                            signature = (
                                "\n\n🛍️ Для замовлень 🛍️\n"
                                '<a href="https://brandmenu.bunddler.com">🛍TM️BrandMenu🤩🌏</a>\n'
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
                        final_text = ""
                        
                    time.sleep(3.5)
                    
                    if msg_type == 'text':
                        bot.send_message(chat_id=ch_id, text=final_text, parse_mode="HTML", disable_web_page_preview=True)
                    elif msg_type == 'album':
                        media_group = []
                        for index, media_item in enumerate(file_id):
                            caption = final_text if index == 0 else None
                            if media_item["type"] == 'photo':
                                media_group.append(types.InputMediaPhoto(media_item["file_id"], caption=caption, parse_mode="HTML"))
                            elif media_item["type"] == 'video':
                                media_group.append(types.InputMediaVideo(media_item["file_id"], caption=caption, parse_mode="HTML"))
                        bot.send_media_group(chat_id=ch_id, media=media_group)
                    elif msg_type == 'photo':
                        if len(final_text) <= 1024:
                            bot.send_photo(chat_id=ch_id, photo=file_id, caption=final_text, parse_mode="HTML")
                        else:
                            bot.send_photo(chat_id=ch_id, photo=file_id)
                            bot.send_message(chat_id=ch_id, text=final_text, parse_mode="HTML", disable_web_page_preview=True)
                    elif msg_type == 'video':
                        if len(final_text) <= 1024:
                            bot.send_video(chat_id=ch_id, video=file_id, caption=final_text, parse_mode="HTML")
                        else:
                            bot.send_video(chat_id=ch_id, video=file_id)
                            bot.send_message(chat_id=ch_id, text=final_text, parse_mode="HTML", disable_web_page_preview=True)
                                
                    success_count += 1
            
            USER_BUFFERS[user_id] = []
            bot.send_message(user_id, f"✅ Успешно опубликовано постов: **{success_count}**!", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(user_id, f"❌ Произошла критическая ошибка при публикации: {e}")
        return

    # Логика ввода новых значений для настроек
    field_map = {
        "set_usd": ("usd_rate", "💵 Введите новый курс USD (например, 45.5):"),
        "set_eur": ("eur_rate", "💶 Введите новый курс EUR (например, 52.5):"),
        "set_gbp": ("gbp_rate", "💷 Введите новый курс GBP (например, 61.5):"),
        "set_com": ("commission", "💼 Введите процент комиссии (например, 10 для +10%):"),
        "set_disc": ("global_discount", "🏷️ Введите процент скидки дня (например, 15 для 15%, или 0 для выключения):")
    }
    
    for prefix, (field_name, prompt_text) in field_map.items():
        if call.data.startswith(prefix + "_"):
            msg = bot.send_message(user_id, prompt_text)
            bot.register_next_step_handler(msg, process_setting_input, field_name, profile)
            return

def process_setting_input(message, field_name, profile):
    user_id = message.chat.id
    try:
        val_raw = message.text.strip().replace(',', '.')
        val = float(val_raw)
        
        all_settings = load_settings()
        
        if field_name == "commission":
            all_settings[profile][field_name] = round(1 + (val / 100), 2)
        elif field_name == "global_discount":
            all_settings[profile][field_name] = int(val)
        else:
            all_settings[profile][field_name] = round(val, 2)
            
        save_settings(all_settings)
        bot.send_message(user_id, "✅ Настройки успешно сохранены и обновлены!", reply_markup=get_settings_keyboard(user_id))
    except:
        msg = bot.send_message(user_id, "❌ Неверный формат ввода. Пожалуйста, введите число:")
        bot.register_next_step_handler(msg, process_setting_input, field_name, profile)

@bot.message_handler(commands=['start', 'settings'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👑 Добро пожаловать в панель управления каналами!", reply_markup=get_settings_keyboard(message.chat.id))

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    user_id = message.chat.id
    
    if message.text and message.text.strip().lower() in ["готово", "пуск", "готово!", "пуск!"]:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👑 Опубликовать в Брендменю", callback_data="pub_my"),
            types.InlineKeyboardButton("🛍️ Опубликовать в Шоппинг (Сестра)", callback_data="pub_sis"),
            types.InlineKeyboardButton("🌟 Опубликовать в ОБА канала", callback_data="pub_both")
        )
        bot.send_message(user_id, f"📥 В корзине собрано **{len(USER_BUFFERS.get(user_id, []))}** постов. Выберите канал для отправки:", reply_markup=markup, parse_mode="Markdown")
        return

    if user_id not in USER_BUFFERS: USER_BUFFERS[user_id] = []
    
    current_position = len(USER_BUFFERS[user_id]) + 1
    
    if message.media_group_id:
        mg_id = message.media_group_id
        if user_id not in ALBUM_BUFFERS: ALBUM_BUFFERS[user_id] = {}
        
        if mg_id not in ALBUM_BUFFERS[user_id]:
            ALBUM_BUFFERS[user_id][mg_id] = {
                "position": current_position,
                "raw_original_text": message.caption or "",
                "items": []
            }
            
            def save_collected_album(u_id, m_id):
                album_data = ALBUM_BUFFERS[u_id].pop(m_id, None)
                if album_data:
                    album_data["items"].sort(key=lambda x: x['msg_id'])
                    USER_BUFFERS[u_id].append({
                        "position": album_data["position"],
                        "type": "album",
                        "file_id": album_data["items"],
                        "raw_original_text": album_data["raw_original_text"]
                    })
                    bot.send_message(u_id, f"📦 Альбом успешно добавлен в корзину! (Позиция №{album_data['position']})")
            
            threading.Timer(2.5, save_collected_album, args=[user_id, mg_id]).start()
            
        media_type = 'photo' if message.content_type == 'photo' else 'video'
        f_id = message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id
        
        ALBUM_BUFFERS[user_id][mg_id]["items"].append({"msg_id": message.message_id, "type": media_type, "file_id": f_id})
        if message.caption:
            ALBUM_BUFFERS[user_id][mg_id]["raw_original_text"] = message.caption
            
    else:
        msg_type = message.content_type
        f_id = message.photo[-1].file_id if msg_type == 'photo' else (message.video.file_id if msg_type == 'video' else None)
        
        USER_BUFFERS[user_id].append({
            "position": current_position,
            "type": msg_type,
            "file_id": f_id,
            "raw_original_text": message.text or message.caption or ""
        })
        bot.send_message(user_id, f"📥 Пост успешно добавлен в корзину! (Позиция №{current_position})")

# Запуск фонового потока планировщика таймеров — СТРОГО ПЕРЕД bot.infinity_polling
threading.Thread(target=morning_scheduler, daemon=True).start()

if __name__ == "__main__":
    print("[+] Бот успешно запущен на Render...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
