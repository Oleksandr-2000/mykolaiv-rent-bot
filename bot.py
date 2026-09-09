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
# OLX GOOGLE GATEWAY
# ============================================================
OLX_GATEWAY_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbypfojtqC_AZEqbFwlSQ_cH6RLHRxe9s8PyaTp8aFLn801nQKnvdK8KyvAZ0iXdkjBgUw"
    "/exec"
)

# ============================================================
# ПОИСК OLX
# ============================================================
OLX_SEARCH_URL = (
    "https://www.olx.ua/uk/nedvizhimost/kvartiry/"
    "dolgosrochnaya-arenda-kvartir/nikolaev_106/"
    "?currency=UAH"
    "&search%5Bfilter_float_price:to%5D=6000"
    "&search%5Bfilter_enum_number_of_rooms_string%5D%5B0%5D=trehkomnatnye"
)

# ============================================================
# MAKLER
# ============================================================
MAKLER_URL = (
    "https://makler.ua/ua/real-estate/"
    "real-estate-for-rent/apartments-for-rent"
)

# ============================================================
# СЛОВА ДЛЯ ФИЛЬТРАЦИИ
# ============================================================
DAILY_WORDS = [
    "посуная", "тестирование", "за сутки", "за ночь", "на ночь",
    "посуточный", "посуточное", "посуточно", "доба", "добово"
]

ROOM_TEMPLATES = [
    "3х кімнатну", "3-х кімнатну", "3 кімнатну", "3-комнатная",
    "3 комнатная", "3-х комнатная", "3х комнатная", "3-комн",
    "3 комн", "3-к.", "3-к", "3 к/к", "3-к/к"
]

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Ошибка: BOT_TOKEN или CHAT_ID не заданы.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, data=data, timeout=30)
        print("Telegram HTTP:", response.status_code)
        if response.ok:
            result = response.json()
            if result.get("ok"):
                print("Сообщение успешно отправлено в Telegram")
                return True
        print("Ошибка Telegram:", response.text)
    except Exception as e:
        print("Ошибка Telegram:", e)
    return False

# ============================================================
# ВРЕМЯ
# ============================================================
def print_current_time():
    now = datetime.now(KYIV_TZ)
    print("Украинское время:", now.strftime("%Y-%m-%d %H:%M:%S"))
    return now

# ============================================================
# ФИЛЬТРЫ И СОРТИРОВКА ЦЕНЫ
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
    text = text.replace("\xa0", " ")
    patterns = [
        r"([\d\s]+)\s*(?:грн|uah|₴)",
        r"([\d\s]+)\s*грив",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        value = re.sub(r"\D", "", match.group(1))
        if not value:
            continue
        price = int(value)
        if 0 < price <= MAX_PRICE:
            return price
    return None
# ============================================================
# ПРОВЕРКА ОБЪЯВЛЕНИЯ
# ============================================================
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
# ПОЛУЧЕНИЕ OLX ЧЕРЕЗ GOOGLE ШЛЮЗ
# ============================================================
def get_olx_feed():
    print("Получение OLX через Google шлюз...")
    try:
        response = requests.get(
            OLX_GATEWAY_URL,
            params={"url": OLX_SEARCH_URL},
            timeout=60
        )
        if response.status_code != 200:
            print("Google шлюз вернул ошибку, статус:", response.status_code)
            print("Ответ:", response.text[:500])
            return ""
        print("Лента OLX успешно получена через шлюз Google!")
        return response.text
    except Exception as e:
        print("Ошибка OLX шлюза:", e)
        return ""

# ============================================================
# ПАРСИНГ OLX
# ============================================================
def parse_olx(html):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen_urls = set()

    # --------------------------------------------------------
    # Способ 1: стандартные карточки OLX
    # --------------------------------------------------------
    cards = soup.find_all("div", attrs={"data-cy": "l-card"})
    print("OLX: стандартных карточек:", len(cards))

    for card in cards:
        try:
            title_tag = card.find(["h4", "h6"])
            title = title_tag.get_text(" ", strip=True) if title_tag else ""

            link_tag = card.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            if not href:
                continue

            if href.startswith("/"):
                href = "https://olx.ua" + href

            card_text = card.get_text(" ", strip=True)
            price = extract_price(card_text)

            if not is_valid_listing(title, card_text, price):
                continue

            if href in seen_urls:
                continue

            seen_urls.add(href)
            results.append({
                "title": title,
                "price": price,
                "description": card_text,
                "url": href,
            })

        except Exception as e:
            print("Ошибка стандартной карточки OLX:", e)

    # --------------------------------------------------------
    # Способ 2: ищем ссылки на объявления OLX
    # --------------------------------------------------------
    if not cards:
        print("OLX: стандартных карточек нет.")
        print("OLX: запускаем альтернативный поиск...")

    links = soup.find_all("a", href=True)
    olx_links = []

    for link in links:
        href = link.get("href", "")
        if "/d/uk/obyavlenie/" in href:
            olx_links.append(link)
        elif "/d/uk/" in href:
            olx_links.append(link)
        elif "/d/obyavlenie/" in href:
            olx_links.append(link)

    print("OLX: найдено ссылок на объявления:", len(olx_links))

    for link in olx_links:
        try:
            href = link.get("href", "")
            if not href:
                continue

            if href.startswith("/"):
                href = "https://olx.ua" + href

            if href in seen_urls:
                continue

            # Получаем текст ближайшего блока
            container = link
            for _ in range(4):
                if container.parent:
                    container = container.parent

            block_text = container.get_text(" ", strip=True)
            title = link.get_text(" ", strip=True)

            # Если текст ссылки короткий, ищем заголовок внутри блока
            if len(title) < 5:
                title_tag = container.find(["h4", "h6", "h3", "h2"])
                if title_tag:
                    title = title_tag.get_text(" ", strip=True)

            if not title:
                continue

            price = extract_price(block_text)

            if not is_valid_listing(title, block_text, price):
                continue

            seen_urls.add(href)
            results.append({
                "title": title,
                "price": price,
                "description": block_text,
                "url": href,
            })

        except Exception as e:
            print("Ошибка альтернативного парсинга OLX:", e)

    # --------------------------------------------------------
    # Убираем дубли
    # --------------------------------------------------------
    unique = {}
    for item in results:
        url = item.get("url")
        if url:
            unique[url] = item

    results = list(unique.values())
    print("OLX: всего подходящих объявлений:", len(results))
    return results

# ============================================================
# ФОРМИРОВАНИЕ СООБЩЕНИЯ OLX
# ============================================================
def format_olx_message(items):
    if not items:
        return ""
    lines = ["🏠 НОВЫЕ ОБЪЯВЛЕНИЯ НА OLX:"]
    for item in items:
        lines.append("")
        lines.append("🏠 " + item["title"])
        lines.append("💵 " + str(item["price"]) + " грн")
        
        description = item.get("description", "")
        if len(description) > 300:
            description = description[:300] + "..."
        if description:
            lines.append("📄 " + description)
            
        lines.append("🔗 Открыть на OLX")
        lines.append(item["url"])
        lines.append("---")
    return "\n".join(lines)

# ============================================================
# ПРОВЕРКА OLX
# ============================================================
def check_olx():
    print("Проверка OLX...")
    html = get_olx_feed()
    if not html:
        print("OLX: данные не получены.")
        return

    items = parse_olx(html)
    print("OLX: найдено подходящих:", len(items))
    if not items:
        print("Новых подходящих объявлений на OLX пока нет.")
        return

    message = format_olx_message(items)
    if message:
        send_telegram(message)

# ============================================================
# ФОРМИРОВАНИЕ УНИВЕРСАЛЬНОГО СООБЩЕНИЯ (ДЛЯ ПАКЕТНОЙ ОТПРАВКИ)
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
                title = link.get_text(" ", strip=True)
                href = link.get("href", "")

                if not title or not href:
                    continue

                if href.startswith("/"):
                    href = "https://makler.ua" + href

                parent = link.parent
                description = parent.get_text(" ", strip=True) if parent else title
                full_text = title + " " + description
                price = extract_price(full_text)

                if not is_valid_listing(title, description, price):
                    continue

                results.append({
                    "title": title,
                    "description": description,
                    "price": price,
                    "url": href,
                })
            except Exception as e:
                print("Ошибка обработки объявления Makler:", e)

        # Убираем дубли
        unique = {}
        for item in results:
            unique[item["url"]] = item
        results = list(unique.values())

        print("Makler: найдено подходящих:", len(results))
        if not results:
            print("Новых подходящих объявлений на Makler пока нет.")
            return

        send_listings(results, "Makler")

    except Exception as e:
        print("Ошибка в модуле Makler:", e)

# ============================================================
# ОСНОВНАЯ ПРОВЕРКА
# ============================================================
def run_checks():
    print("Запуск плановой проверки сайтов...")
    print_current_time()
    print("Начинаем проверку объявлений...")

    # Makler
    try:
        check_makler()
    except Exception as e:
        print("Ошибка Makler:", e)

    # OLX
    try:
        check_olx()
    except Exception as e:
        print("Ошибка OLX:", e)

    print("Проверка завершена.")

# ============================================================
# ЗАПУСК
# ============================================================
def main():
    run_checks()

if __name__ == "__main__":
    main()
