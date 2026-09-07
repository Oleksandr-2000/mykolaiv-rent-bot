import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

LIST_URL = (
    "https://www.olx.ua/nedvizhimost/kvartiry/"
    "dolgosrochnaya-arenda-kvartir/3-kmnati/nikolaev_106/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
    )
}


def get_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_number(text):
    numbers = re.findall(r"\d[\d\s]*", text)
    if not numbers:
        return None

    return int(re.sub(r"\D", "", numbers[0]))


def check_ad(url):
    try:
        soup = get_page(url)
        text = " ".join(soup.stripped_strings)
        low = text.lower()

        # Объявление должно быть активным
        if "уже не активно" in low or "старница устарела" in low:
            return None

        # Только помесячная аренда
        if "помісячно" not in low and "помесячно" not in low:
            return None

        # Исключаем посуточную аренду
        bad_words = [
            "посуточно",
            "подобово",
            "сутки",
            "почасово",
            "за ночь",
        ]

        if any(word in low for word in bad_words):
            return None

        # Только 3 комнаты
        room_patterns = [
            r"3\s*кімнати",
            r"3\s*комнат",
            r"3[- ]ком",
            r"3х\s*кімнат",
            r"3х\s*комнат",
        ]

        if not any(re.search(pattern, low) for pattern in room_patterns):
            return None

        # Цена
        price_match = re.search(
            r"Ціна\s*:\s*([\d\s]+)\s*грн",
            text,
            re.IGNORECASE
        )

        if not price_match:
            price_match = re.search(
                r"([\d\s]+)\s*грн",
                text,
                re.IGNORECASE
            )

        if not price_match:
            return None

        price = int(re.sub(r"\D", "", price_match.group(1)))

        if price > 6000:
            return None

        # Ищем этаж
        floor = None
        total_floors = None

        floor_match = re.search(
            r"Поверх\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if floor_match:
            floor = int(floor_match.group(1))

        # Проверяем варианты 3/9, 3 / 9
        fraction = re.search(
            r"\b(\d+)\s*/\s*(\d+)\b",
            text
        )

        if fraction:
            floor = int(fraction.group(1))
            total_floors = int(fraction.group(2))

        # Если этажность известна — исключаем последний этаж
        if floor is not None and total_floors is not None:
            if floor >= total_floors:
                return None

        title = soup.find("h1")

        if title:
            title = title.get_text(" ", strip=True)
        else:
            title = "3-комнатная квартира"

        # Адрес
        address = ""

        street_match = re.search(
            r"Вулиця\s+(.+?)(?:Район|Ціна|Поделиться)",
            text,
            re.IGNORECASE
        )

        if street_match:
            address = street_match.group(1).strip()

        return {
            "title": title,
            "price": price,
            "floor": floor,
            "address": address,
            "url": url,
        }

    except Exception as error:
        print("Ошибка проверки:", url, error)
        return None


# Получаем список объявлений
soup = get_page(LIST_URL)

inks = []

for a in soup.find_all("a", href=True):

    href = a["href"]

    if "/an/" not in href:
        continue
if not re.search(r"/an/\d+", href):
    continue

https://re.search
    full_url = urljoin(LIST_URL, href)

    if full_url not in links:
        links.append(full_url)


print("Найдено ссылок на объявления:", len(links))

if links:
    test_soup = get_page(links[0])
    print("===== ПЕРВОЕ ОБЪЯВЛЕНИЕ =====")
    print(" ".join(test_soup.stripped_strings)[:5000])
    print("===== КОНЕЦ ОБЪЯВЛЕНИЯ =====")

results = []

# Проверяем первые 30 объявлений
for link in links[:30]:

    ad = check_ad(link)

    if ad:
        results.append(ad)

    if len(results) >= 10:
        break


print("Подходящих объявлений:", len(results))


# Формируем сообщение
if results:

    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    message += "Найдены подходящие объявления:\n\n"

    for ad in results:

        floor_text = (
            str(ad["floor"])
            if ad["floor"] is not None
            else "не указан"
        )

        message += (
            f"🏠 {ad['title']}\n"
            f"💰 {ad['price']} грн/мес\n"
            f"🏢 Этаж: {floor_text}\n"
        )

        if ad["address"]:
            message += f"📍 {ad['address']}\n"

        message += f"🔗 {ad['url']}\n\n"

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих объявлений пока не найдено."
    )


# Отправляем Telegram
telegram_url = (
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
)

response = requests.post(
    telegram_url,
    json={
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    },
    timeout=30,
)

response.raise_for_status()

print("Сообщение отправлено в Telegram")
