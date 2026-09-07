import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/nik-nikolaev/real-estate/real-estate-for-rent/apartments-for-rent"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

response = requests.get(URL, headers=HEADERS, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

results = []

# Ищем ссылки, которые ведут на объявления
for a in soup.find_all("a", href=True):

    href = a["href"]

    if "/an/" not in href:
        continue

    # Берём ближайший контейнер объявления
    card = a.find_parent(["article", "div", "li"])

    if not card:
        continue

    text = " ".join(card.stripped_strings)
    low = text.lower()

    # Только 3 комнаты
    if not re.search(r"\b3\s*(?:кімнат|комнат|комн|ком)\b", low):
        continue

    # Только помесячная аренда
    if "помісячно" not in low and "помесячно" not in low:
        continue

    # Исключаем посуточную аренду
    if any(word in low for word in [
        "посуточно",
        "подобово",
        "сутки",
        "почасово"
    ]):
        continue

    # Ищем цену
    price_matches = re.findall(
        r"(\d[\d\s]*)\s*(?:uah|грн)",
        text,
        re.IGNORECASE
    )

    if not price_matches:
        continue

    prices = []

    for value in price_matches:
        try:
            prices.append(int(re.sub(r"\D", "", value)))
        except ValueError:
            pass

    if not prices:
        continue

    price = min(prices)

    if price > 6000:
        continue

    # Этаж
    floor_match = re.search(
        r"(?:поверх|этаж)\s*[:\-]?\s*(\d+)",
        low
    )

    floor = floor_match.group(1) if floor_match else "не указан"

    # Если явно указан 1/9, 3/9 и т.п.
    fraction_match = re.search(r"\b(\d+)\s*/\s*(\d+)\b", text)

    total_floors = None

    if fraction_match:
        floor = fraction_match.group(1)
        total_floors = fraction_match.group(2)

    # Не последний этаж, если известна этажность
    if total_floors and floor.isdigit():
        if int(floor) >= int(total_floors):
            continue

    link = urljoin(URL, href)

    results.append({
        "text": text[:500],
        "price": price,
        "floor": floor,
        "link": link
    })


# Удаляем дубли
unique = {}

for item in results:
    unique[item["link"]] = item

results = list(unique.values())


if results:

    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    message += "Найдены подходящие объявления:\n\n"

    for item in results[:10]:

        message += (
            f"💰 {item['price']} грн\n"
            f"🏢 Этаж: {item['floor']}\n"
            f"{item['text']}\n"
            f"🔗 {item['link']}\n\n"
        )

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих объявлений пока не найдено."
    )


telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

telegram_response = requests.post(
    telegram_url,
    json={
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    },
    timeout=30
)

telegram_response.raise_for_status()

print("Найдено вариантов:", len(results))
