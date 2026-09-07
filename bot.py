import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/nik-nikolaev/real-estate/real-estate-for-rent/apartments-for-rent"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

results = []

# Ищем все ссылки на объявления
for a in soup.find_all("a", href=True):
    text = " ".join(a.stripped_strings)

    if not text:
        continue

    low = text.lower()

    # Только 3 комнаты
    if not re.search(r"\b3\s*[-хx]?\s*(?:ком|кім)", low):
        continue

    # Исключаем посуточную аренду
    bad_words = [
        "посуточно",
        "посут",
        "сутки",
        "ночь",
        "ночь",
        "почасово",
        "час",
    ]

    if any(word in low for word in bad_words):
        continue

    # Ищем цену в гривнах
    price_match = re.search(
        r"(\d[\d\s]*)\s*(?:uah|грн)",
        text,
        re.IGNORECASE
    )

    if not price_match:
        continue

    price = int(re.sub(r"\D", "", price_match.group(1)))

    if price > 6000:
        continue

    # Проверяем этаж
    floor_match = re.search(
        r"(?:поверх|этаж)\s*(\d+)",
        low
    )

    floor = floor_match.group(1) if floor_match else "не указан"

    # Ссылка
    link = urljoin(URL, a["href"])

    # Название
    title = text.replace("\n", " ").strip()

    results.append({
        "title": title[:400],
        "price": price,
        "floor": floor,
        "link": link
    })


# Убираем дубли
unique = {}

for item in results:
    unique[item["link"]] = item

results = list(unique.values())


if results:
    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    message += "Найдены варианты до 6000 грн:\n\n"

    for item in results[:10]:
        message += (
            f"🏠 {item['title']}\n"
            f"💰 {item['price']} грн\n"
            f"🏢 Этаж: {item['floor']}\n"
            f"🔗 {item['link']}\n\n"
        )
else:
    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих новых объявлений не найдено."
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

print(f"Найдено вариантов: {len(results)}")

