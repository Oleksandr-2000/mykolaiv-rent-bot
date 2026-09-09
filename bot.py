import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

# ============================================================
# НАСТРОЙКИ
# ============================================================
BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
CHAT_ID = os.environ["CHAT_ID"].strip()
MAX_PRICE = 6000
KYIV_TZ = ZoneInfo("Europe/Kyiv")

# ============================================================
# ССЫЛКИ ДЛЯ ПОИСКА
# ============================================================
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
# ФИЛЬТРЫ И СПИСКИ КЛЮЧЕВЫХ СЛОВ
# ============================================================
DAILY_WORDS = [
    "посуная", "посуточный", "посуточное", "посуточно",
    "за сутки", "за ночь", "на ночь", "доба", "добово",
]

ROOM_TEMPLATES = [
    "3х кімнатну", "3-х кімнатну", "3 кімнатну", "3-комнатная",
    "3 комнатная", "3-х комнатная", "3х комнатная", "3-комн",
    "3 комн", "3-к.", "3-к", "3 к/к", "3-к/к",
]

# ============================================================
# ЛОГИКА ФИЛЬТРАЦИИ И ВАЛИДАЦИИ
# ============================================================
def is_daily_rent(text):
    if not text:
        return False
    text = text.lower()
    return any(word in text for word in DAILY_WORDS)

def is_three_room(text):
    if not text:
        return False
    text = text.lower()
    return any(template.lower() in text for template in ROOM_TEMPLATES)

def extract_price(text):
    if not text:
        return None

    patterns = [
        r"([\d\s]{1,12})\s*грн",
        r"([\d\s]{1,12})\s*₴",
        r"([\d\s]{1,12})\s*UAH",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue

        value = re.sub(r"\D", "", match.group(1))
        if not value:
            continue
        try:
            price = int(value)
        except ValueError:
            continue

        if 0 < price <= MAX_PRICE:
            return price
    return None

def is_valid_listing(title, description="", price=None):
    full_text = (str(title) + " " + str(description)).lower()
    if is_daily_rent(full_text):
        return False
    if not is_three_room(full_text):
        return False
    if price is not None and price > MAX_PRICE:
        return False
    return True

# ============================================================
# ВРЕМЯ
# ============================================================
def print_current_time():
    now = datetime.now(KYIV_TZ)
    print("Украинское время:", now.strftime("%Y-%m-%d %H:%M:%S"))
    return now
# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Ошибка: BOT_TOKEN или CHAT_ID не задан.")
        return False

    url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, data=data, timeout=30)
        print("Telegram HTTP:", response.status_code)
        if response.ok:
            print("Сообщение успешно отправлено в Telegram")
            return True
        print("Ошибка Telegram:", response.text[:500])
        return False
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)
        return False

# ============================================================
# PLAYWRIGHT — ПОЛУЧЕНИЕ OLX
# ============================================================
def get_olx_html():
    print("Открываем OLX через системный Chromium...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium"
            )
            page = browser.new_page(
                viewport={"width": 1440, "height": 1000},
                locale="uk-UA",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/140.0.0.0 Safari/537.36"
                )
            )
            page.goto(OLX_SEARCH_URL, wait_until="domcontentloaded", timeout=90000)
            print("OLX: страница открыта.")

            # Ждём загрузки объявлений JavaScript
            page.wait_for_timeout(7000)
            html = page.content()
            print("OLX: HTML получен, размер:", len(html))
            
            browser.close()
            return html
    except Exception as e:
        print("Ошибка Playwright OLX:", e)
        return ""

# ============================================================
# ПАРСИНГ OLX
# ============================================================
def parse_olx(html):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    cards = soup.find_all("div", attrs={"data-cy": "l-card"})
    print("OLX: найдено стандартных карточек:", len(cards))

    # Показываем карточки и их ссылки
    for i, card in enumerate(cards, 1):
        print(f"OLX CARD {i}:", card.get_text(" ", strip=True)[:1000])
        link_tag = card.find("a", href=True)
        if link_tag:
            print(f"OLX URL {i}:", link_tag.get("href"))

    if not cards:
        print("OLX: стандартных карточек нет.")
        return []

    for card in cards:
        try:
            # ------------------------------------------------
            # НАЗВАНИЕ
            # ------------------------------------------------
            title_tag = card.find("h4")
            if not title_tag:
                title_tag = card.find("h6")

            title = ""
            if title_tag:
                title = title_tag.get_text(" ", strip=True)

            if not title:
                continue

            # ------------------------------------------------
            # ССЫЛКА
            # ------------------------------------------------
            link_tag = card.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            if not href:
                continue

            # Не берём объявления, которые OLX добавил через расширенный поиск
            if "extended_search_extended_distance" in href:
                print("OLX: пропускаем объявление из расширенного поиска")
                continue

            if href.startswith("/"):
                href = "https://www.olx.ua" + href

            # ------------------------------------------------
            # ПРОВЕРКА ТЕКСТА И ЦЕНЫ
            # ------------------------------------------------
            card_text = card.get_text(" ", strip=True)
            full_text = (title + " " + card_text).lower()
            price = extract_price(card_text)

            if price is None:
                continue
            if not is_three_room(full_text):
                continue
            if is_daily_rent(full_text):
                continue

            results.append({
                "title": title,
                "price": price,
                "description": card_text,
                "url": href,
            })
        except Exception as e:
            print("Ошибка обработки карточки OLX:", e)

    # --------------------------------------------------------
    # УДАЛЯЕМ ДУБЛИКАТЫ
    # --------------------------------------------------------
    unique = {}
    for item in results:
        url = item.get("url")
        if url:
            unique[url] = item

    results = list(unique.values())
    print("OLX: найдено подходящих:", len(results))
    return results



# ============================================================
# ФОРМИРОВАНИЕ И ОТПРАВКА СООБЩЕНИЙ
# ============================================================
def format_listing(listing, source):
    title = listing.get("title", "Без названия")
    description = listing.get("description", "")
    price = listing.get("price")
    url = listing.get("url", "")

    price_text = "Цена не указана" if price is None else f"{price} грн"
    if len(description) > 300:
        description = description[:300] + "..."

    message = f"🏠 {title}\n💵 {price_text}\n"
    if description:
        message += f"📄 {description}\n"
    if url:
        message += f"🔗 Открыть на {source}\n{url}"
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
        send_telegram(message)

# ============================================================
# ПРОВЕРКА OLX
# ============================================================
def check_olx():
    print("Проверка OLX...")
    html = get_olx_html()
    if not html:
        print("OLX: HTML не получен.")
        return

    items = parse_olx(html)
    if not items:
        print("Новых подходящих объявлений на OLX пока нет.")
        return

    print("OLX: отправляем найденные объявления:", len(items))
    send_listings(items, "OLX")

# ============================================================
# ПРОВЕРКА MAKLER
# ============================================================
def check_makler():
    print("Проверка Makler...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(MAKLER_URL, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)
        print("Makler: найдено ссылок:", len(links))

        results = []
        for link in links:
            try:
                href = link.get("href", "")
                title = link.get_text(" ", strip=True)
                if not href or not title:
                    continue

                if href.startswith("/"):
                    href = "https://makler.ua" + href

                parent = link.parent
                description = parent.get_text(" ", strip=True) if parent else title
                price = extract_price(description)

                if not is_valid_listing(title, description, price):
                    continue

                results.append({
                    "title": title,
                    "description": description,
                    "price": price,
                    "url": href,
                })
            except Exception as e:
                print("Ошибка обработки Makler:", e)

        # Убираем дубли
        unique = {}
        for item in results:
            url = item.get("url")
            if url:
                unique[url] = item
        results = list(unique.values())

        print("Makler: найдено подходящих:", len(results))
        send_listings(results, "Makler")

    except Exception as e:
        print("Ошибка в модуле Makler:", e)

# ============================================================
# УПРАВЛЕНИЕ ЗАПУСКОМ ПРОВЕРОК
# ============================================================
def run_checks():
    print("Запуск плановой проверки сайтов...")
    print_current_time()
    print("Начинаем проверку объявлений...")

    try:
        check_makler()
    except Exception as e:
        print("Ошибка Makler:", e)

    try:
        check_olx()
    except Exception as e:
        print("Ошибка OLX:", e)

    print("Проверка завершена.")

def main():
    run_checks()

if __name__ == "__main__":
    main()
