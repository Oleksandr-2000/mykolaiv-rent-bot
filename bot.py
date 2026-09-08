import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# НАСТРОЙКИ
# ============================================================
BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
CHAT_ID = os.environ["CHAT_ID"].strip()
MAX_PRICE = 6000
KYIV_TZ = ZoneInfo("Europe/Kyiv")

# ============================================================
# ССЫЛКИ И ШЛЮЗЫ
# ============================================================
OLX_GATEWAY_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbypfojtqC_AZEqbFwlSQ_cH6RLHRxe9s8PyaTp8aFLn801nQKnvdK8KyvAZ0iXdkjBgUw"
    "/exec"
)

OLX_SEARCH_URL = (
    "https://www.olx.ua/uk/nedvizhimost/kvartiry/"
    "dolgosrochnaya-arenda-kvartir/nikolaev_106/"
    "?currency=UAH"
    "&search%5Bfilter_float_price:to%5D=6000"
    "&search%5Bfilter_enum_number_of_rooms_string%5D%5B0%5D=trehkomnatnye"
)

MAKLER_URL = (
    "https://makler.ua/ua/real-estate/"
    "real-estate-for-rent/apartments-for-rent/"
)

# ============================================================
# ШАБЛОНЫ ФИЛЬТРАЦИИ ОБЪЯВЛЕНИЙ
# ============================================================
DAILY_WORDS = [
    "посуная",
    "тестирование",
    "за сутки",
    "за ночь",
    "на ночь",
    "посуточный",
    "посуточное",
    "посуточно",
    "доба",
    "добово",
]

ROOM_TEMPLATES = [
    "3х кімнатну",
    "3-х кімнатну",
    "3 кімнатну",
    "3-комнатная",
    "3 комнатная",
    "3-х комнатная",
    "3х комнатная",
    "3-комн",
    "3 комн",
    "3-к.",
    "3-к",
    "3 к/к",
    "3-к/к",
]
# ============================================================
# ОТПРАВКА СООБЩЕНИЯ В TELEGRAM
# ============================================================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, data=data, timeout=30)
        print("Telegram HTTP:", response.status_code)
        print("Telegram ответ:", response.text)

        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print("Сообщение успешно отправлено в Telegram")
                return True

        print("Ошибка отправки сообщения в Telegram")
        return False
    except Exception as e:
        print("Ошибка Telegram:", e)
        return False

# ============================================================
# ПРОВЕРКА, ЧТО ОБЪЯВЛЕНИЕ ПОДХОДИТ
# ============================================================
def is_daily(text):
    text = text.lower()
    for word in DAILY_WORDS:
        if word in text:
            return True
    return False

def is_three_room(text):
    text = text.lower()
    for template in ROOM_TEMPLATES:
        if template.lower() in text:
            return True
    return False

def get_price(text):
    text = text.replace("\xa0", " ")
    patterns = [
        r"(\d[\d\s]{1,8})\s*грн",
        r"(\d[\d\s]{1,8})\s*₴",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_text = match.group(1).replace(" ", "")
            try:
                return int(price_text)
            except ValueError:
                pass
    return None

def is_valid_listing(title, description="", price=None):
    full_text = (str(title) + " " + str(description)).lower()
    if is_daily(full_text):
        return False
    if not is_three_room(full_text):
        return False
    if price is not None and price > MAX_PRICE:
        return False
    return True

# ============================================================
# ПОЛУЧЕНИЕ ТЕКУЩЕГО ВРЕМЕНИ
# ============================================================
def print_current_time():
    now = datetime.now(KYIV_TZ)
    print("Украинское время:", now.strftime("%Y-%m-%d %H:%M:%S"))
    return now
# ============================================================
# ОТПРАВКА СООБЩЕНИЯ В TELEGRAM
# ============================================================
def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Ошибка: BOT_TOKEN или CHAT_ID не задан.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print("Telegram HTTP:", response.status_code)
        if response.ok:
            print("Сообщение успешно отправлено в Telegram")
            return True
        print("Ошибка Telegram:", response.text)
        return False
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)
        return False

# ============================================================
# ФОРМИРОВАНИЕ СООБЩЕНИЯ ОБ ОБЪЯВЛЕНИЯХ
# ============================================================
def format_listing(listing, source):
    title = listing.get("title", "Без названия")
    description = listing.get("description", "")
    price = listing.get("price")
    url = listing.get("url", "")

    if price is None:
        price_text = "Цена не указана"
    else:
        price_text = f"{price} грн"

    message = (
        f"🏠 {title}\n"
        f"💵 {price_text}\n"
        f"📄 {description}\n"
    )

    if url:
        message += f"🔗 Открыть на {source}: {url}"
    return message

def send_listings(listings, source):
    if not listings:
        print(f"Новых подходящих объявлений на {source} пока нет.")
        return

    header = f"🏠 НОВЫЕ ОБЪЯВЛЕНИЯ НА {source.upper()}:\n\n"
    messages = []
    current_message = header

    for listing in listings:
        item = format_listing(listing, source)
        item += "\n\n---\n\n"

        if len(current_message) + len(item) > 4000:
            messages.append(current_message)
            current_message = item
        else:
            current_message += item

    if current_message.strip():
        messages.append(current_message)

    for message in messages:
        send_telegram_message(message)

# ============================================================
# ПРОВЕРКА ВРЕМЕНИ
# ============================================================
def can_run_check():
    # Проверка работает круглосуточно.
    # Ограничения по времени отключены.
    return True
# ============================================================
# ОСНОВНАЯ ПРОВЕРКА
# ============================================================
def main():
    print("Запуск плановой проверки сайтов...")
    now = print_current_time()

    if not can_run_check():
        print("Проверка объявлений пропущена.")
        return

    print("Начинаем проверку объявлений...")

    # --------------------------------------------------------
    # MAKLER
    # --------------------------------------------------------
    try:
        check_makler()
    except Exception as e:
        print("Ошибка в модуле Makler:", e)

    # --------------------------------------------------------
    # OLX
    # --------------------------------------------------------
    try:
        check_olx()
    except Exception as e:
        print("Ошибка в модуле OLX:", e)

    print("Проверка завершена.")
    print("Скрипт успешно завершен.")

# ============================================================
# ЗАПУСК ПРОГРАММЫ
# ============================================================
if __name__ == "__main__":
    main()
