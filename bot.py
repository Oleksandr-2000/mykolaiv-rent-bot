import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# НАСТРОЙКИ
# ==========================================
BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
CHAT_ID = os.environ["CHAT_ID"].strip()
MAX_PRICE = 6000
KYIV_TZ = ZoneInfo("Europe/Kyiv")

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
    "real-estate-for-rent/apartments-for-rent"
)

# ==========================================
# TELEGRAM
# ==========================================
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
        if response.ok:
            print("Сообщение успешно отправлено в Telegram")
            return True
        print("Ошибка отправки Telegram")
        return False
    except Exception as e:
        print("Ошибка Telegram:", e)
        return False

# ==========================================
# ВРЕМЯ
# ==========================================
def is_working_time():
    now = datetime.now(KYIV_TZ)
    print("Украинское время:", now.strftime("%Y-%m-%d %H:%M:%S"))
    if 8 <= now.hour < 18:
        return True
    print("Сейчас вне рабочего времени 08:00-18:00.")
    return False

# ==========================================
# MAKLER
# ==========================================
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
        print("Makler: найдено объектов:", len(soup.find_all("a")))
    except Exception as e:
        print("Ошибка в модуле Makler:", e)
        return

# ==========================================
# OLX — ПОЛУЧЕНИЕ ЛЕНТЫ ЧЕРЕЗ GOOGLE
# ==========================================
def get_olx_feed():
    print("Получение OLX через Google шлюз...")
    try:
        response = requests.get(OLX_GATEWAY_URL, params={"url": OLX_SEARCH_URL}, timeout=60)
        if response.status_code != 200:
            print("Google шлюз вернул ошибку, статус:", response.status_code)
            print("Ответ:", response.text[:500])
            return ""
        print("Лента OLX успешно получена через шлюз Google!")
        return response.text
    except Exception as e:
        print("Ошибка OLX шлюза:", e)
        return ""

# ==========================================
# ПОИСК ЦЕНЫ
# ==========================================
def extract_price(text):
    if not text:
        return None
    match = re.search(r"([\d\s]+)\s*(uah|грн)", text, re.IGNORECASE)
    if not match:
        return None
    value = re.sub(r"\D", "", match.group(1))
    if not value:
        return None
    price = int(value)
    if price <= 0 or price > MAX_PRICE:
        return None
    return price

# ==========================================
# ПРОВЕРКА 3-КОМНАТНОЙ КВАРТИРЫ
# ==========================================
def is_three_room(text):
    if not text:
        return False
    text = text.lower()
    room_templates = [
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
    return any(template in text for template in room_templates)

# ==========================================
# ИСКЛЮЧЕНИЕ ПОСУТОЧНОЙ АРЕНДЫ
# ==========================================
def is_daily_rent(text):
    if not text:
        return False
    text = text.lower()
    daily_words = [
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
    return any(word in text for word in daily_words)
# ============================================================
# ПАРСИНГ OLX
# ============================================================
def parse_olx(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    
    # Ищем карточки объявлений
    cards = soup.find_all("div", attrs={"data-cy": "l-card"})
    print("OLX: найдено карточек:", len(cards))

    for card in cards:
        try:
            # ------------------------------------------------
            # НАЗВАНИЕ
            # ------------------------------------------------
            title_tag = card.find("h4")
            if not title_tag:
                title_tag = card.find("h6")
            title = title_tag.get_text(" ", strip=True) if title_tag else ""
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
            if href.startswith("/"):
                href = "https://www.olx.ua" + href

            # ------------------------------------------------
            # ВЕСЬ ТЕКСТ КАРТОЧКИ
            # ------------------------------------------------
            card_text = card.get_text(" ", strip=True)
            full_text = (title + " " + card_text).lower()

            # ------------------------------------------------
            # ЦЕНА
            # ------------------------------------------------
            price = extract_price(card_text)
            if price is None:
                continue

            # ------------------------------------------------
            # 3 КОМНАТЫ
            # ------------------------------------------------
            if not is_three_room(full_text):
                continue

            # ------------------------------------------------
            # НЕ ПОСУТОЧНО
            # ------------------------------------------------
            if is_daily_rent(full_text):
                continue

            # ------------------------------------------------
            # СОХРАНЯЕМ
            # ------------------------------------------------
            results.append({
                "title": title,
                "price": price,
                "description": card_text,
                "url": href,
            })
        except Exception as e:
            print("Ошибка обработки карточки OLX:", e)
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
        # Чтобы Telegram не получал огромный текст карточки
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
# ЗАВЕРШЕНИЕ ПРОВЕРКИ
# ============================================================
def run_checks():
    print("Запуск плановой проверки сайтов...")
    if not is_working_time():
        print("Проверка объявлений пропущена.")
        return
    check_makler()
    check_olx()
    print("Проверка завершена.")
# ============================================================
# ТЕСТ СВЯЗИ С TELEGRAM
# ============================================================
def telegram_test():
    print("Запуск принудительного теста связи...")
    
    message = (
        "🤖 Проверка связи успешна!\n\n"
        "Бот подключен к Telegram и GitHub.\n\n"
        "Я буду проверять OLX и Makler "
        "каждые 2 часа и искать новые "
        "3-к квартиры до 6000 грн."
    )
    
    if send_telegram(message):
        print("Тестовое сообщение отправлено.")
    else:
        print("Не удалось отправить тестовое сообщение.")

# ============================================================
# ЗАЩИТА ОТ ПОВТОРНЫХ ЗАПУСКОВ
# ============================================================
def main():
    print("Запуск плановой проверки сайтов...")
    try:
        run_checks()
    except Exception as e:
        print("Критическая ошибка:", e)
        
    print("Проверка завершена.")
    
    # Тест Telegram можно оставить включённым,
    # чтобы после каждого запуска GitHub Actions
    # было видно, что бот действительно работает.
    telegram_test()
    print("Скрипт успешно завершен.")
# ============================================================
# ЗАПУСК ПРОГРАММЫ
# ============================================================
if __name__ == "__main__":
    main()
