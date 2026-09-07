import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/real-estate/real-estate-for-rent/apartments-for-rent/"

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

    title_tag = article.select_one(
        ".ls-detail_antTitle a"
    )

    price_tag = article.select_one(
        ".ls-detail_price"
    )

    text_tag = article.select_one(
        ".ls-detail_anText"
    )

    if title_tag is None:
        continue

    title = title_tag.get_text(
        " ",
        strip=True
    )

    description = ""

    if text_tag:
        description = text_tag.get_text(
            " ",
            strip=True
        )

    full_text = (
        title + " " + description
    ).lower()

    price = 0

    if price_tag:

        price_text = price_tag.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"(\d[\d\s]*)\s*(uah|грн)",
            price_text,
            re.IGNORECASE
        )

        if match:
            price = int(
                re.sub(
                    r"\D",
                    "",
                    match.group(1)
                )
            )

    room_ok = any(
        x in full_text
        for x in [
            "3х кімнатну",
            "3-х кімнатну",
            "3 кімнатну",
            "3-комнатную",
            "3 комнатную",
            "3-х комнатную",
            "3х комнатную"
        ]
    )

    daily = any(
        x in full_text
        for x in [
            "посуточно",
            "подобово",
            "за сутки",
            "за ночь",
            "на ночь"
        ]
    )

    room_inside = any(
        x in full_text
        for x in [
            "1 комната в 3",
            "1 кімната в 3",
            "комната в 3х комнатной",
            "кімната в 3х кімнатній"
        ]
    )

    if (
        price > 0
        and price <= 6000
        and room_ok
        and not daily
        and not room_inside
    (sad)

        href = title_tag.get("href", "")

        link = urljoin(
            URL,
            href
        )

        results.append(
            {
                "title": title,
                "price": price,
                "description": description,
                "link": link
            }
        )

print(
    "Подходящих объявлений:",
    len(results)
)

if results:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Найдены подходящие объявления:\n\n"
    )

    for item in results[:10]:

        message += (
            "🏠 " + item["title"] + "\n"
            "💰 " + str(item["price"]) + " грн\n"
            "📝 " + item["description"] + "\n"
            "🔗 " + item["link"] + "\n\n"
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

