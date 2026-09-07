import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/real-estate/real-estate-for-rent/apartments-for-rent?list&region[]=17&city[]=384&city[]=372&city[]=373&city[]=374&city[]=375&city[]=376&city[]=377&city[]=378&city[]=3130&city[]=379&city[]=380&city[]=381&city[]=382&city[]=3131&city[]=3416&city[]=3132&city[]=3418&city[]=383&city[]=386&city[]=385&city[]=387&city[]=3133&city[]=388&city[]=3134&city[]=3417&city[]=389&city[]=390&currency_id=5&list=detail"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

print("HTTP:", response.status_code)
print("Размер страницы:", len(response.text))

soup = BeautifulSoup(response.text, "html.parser")

articles = soup.find_all(
    "article",
    id=re.compile(r"^tr_an-")
)

print("Найдено article:", len(articles))

results = []

for article in articles:

    title_tag = article.select_one(".ls-detail_antTitle a")
    price_tag = article.select_one(".ls-detail_price")
    text_tag = article.select_one(".ls-detail_anText")

    if not title_tag:
        continue

    title = title_tag.get_text(" ", strip=True)

    if price_tag:
        price_text = price_tag.get_text(" ", strip=True)
    else:
        price_text = ""

    if text_tag:
        description = text_tag.get_text(" ", strip=True)
    else:
        description = ""

    full_text = (
        title + " " + description
    ).lower()

    price_match = re.search(
        r"([\d\s]+)\s*(uah|грн)",
        price_text,
        re.IGNORECASE
    )

    if not price_match:
        continue

    price = int(
        re.sub(
            r"\D",
            "",
            price_match.group(1)
        )
    )

    if price <= 0 or price > 6000:
        continue

    room_ok = False

    room_patterns = [
        "3х кімнатну",
        "3-х кімнатну",
        "3 кімнатну",
        "3-комнатную",
        "3 комнатную",
        "3-х комнатную",
        "3х комнатную",
        "3-комнатная",
        "3 комнатная",
        "3-к.",
        "3-к ",
        "3 к/к",
        "3-к/к"
    ]

    for pattern in room_patterns:
        if pattern in full_text:
            room_ok = True
            break

    if not room_ok:
        continue

    daily_words = [
        "посуточно",
        "подобово",
        "за сутки",
        "за ночь",
        "на ночь",
        "посуточная",
        "посуточное"
    ]

    is_daily = False

    for word in daily_words:
        if word in full_text:
            is_daily = True
            break

    if is_daily:
        continue

    href = title_tag.get("href", "")

    link = urljoin(
        "https://makler.ua",
        href
    )

    results.append(
        "🏠 " + title
        + "\n💰 " + str(price) + " грн"
        + "\n📝 " + description
        + "\n🔗 " + link
    )

print("Подходящих объявлений:", len(results))

if results:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Найдены подходящие объявления:\n\n"
        + "\n\n".join(results)
    )

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих объявлений пока не найдено."
    )

telegram_url = (
    "https://api.telegram.org/bot"
    + BOT_TOKEN
    + "/sendMessage"
)

telegram_response = requests.post(
    telegram_url,
    json={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=30
)

telegram_response.raise_for_status()

print("Сообщение отправлено в Telegram")
