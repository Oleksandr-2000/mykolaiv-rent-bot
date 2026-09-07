import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/real-estate/real-estate-for-rent/apartments-for-rent/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8",
}


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()


response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30,
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

articles = soup.find_all(
    "article",
    id=re.compile(r"^tr_an-\d+$"),
)

print("Размер страницы:", len(response.text))
print("Найдено объявлений:", len(articles))

results = []

for article in articles:

    title_tag = article.select_one("a.ls-detail_anUrl")
    price_tag = article.select_one(".ls-detail_price")
    text_tag = article.select_one(".ls-detail_anText")

    if title_tag and price_tag:

        title = title_tag.get_text(" ", strip=True)

        description = ""

        if text_tag:
            description = text_tag.get_text(
                " ",
                strip=True,
            )

        text = (
            title + " " + description
        ).lower()

        price_text = price_tag.get_text(
            " ",
            strip=True,
        )

        price_match = re.search(
            r"(\d[\d\s]*)\s*(uah|грн)",
            price_text,
            re.IGNORECASE,
        )

        if price_match:

            price = int(
                re.sub(
                    r"\D",
                    "",
                    price_match.group(1),
                )
            )

            room_ok = bool(
                re.search(
                    r"3[- ]?(х|комнатн|кімнатн)",
                    text,
                    re.IGNORECASE,
                )
            )

            daily = any(
                word in text
                for word in [
                    "посуточно",
                    "подобово",
                    "посуточная",
                    "подобова",
                    "за сутки",
                    "за ночь",
                    "на ночь",
                ]
            )

            single_room = any(
                word in text
                for word in [
                    "1 комната в 3",
                    "1 кімната в 3",
                    "комната в 3х комнатной",
                    "кімната в 3х кімнатній",
                ]
            )

            if (
                price <= 6000
                and room_ok
                and not daily
                and not single_room
            (sad)

                href = title_tag.get("href")

                if href:

                    results.append(
                        {
                            "title": title,
                            "price": price,
                            "description": description,
                            "link": urljoin(
                                URL,
                                href,
                            ),
                        }
                    )


print(
    "Подходящих объявлений:",
    len(results),
)


if results:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Найдены подходящие объявления:\n\n"
    )

    for item in results[:10]:

        message += (
            f"🏠 {item['title']}\n"
            f"💰 {item['price']} грн\n"
            f"📝 {item['description']}\n"
            f"🔗 {item['link']}\n\n"
        )

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих объявлений пока не найдено."
    )


send_telegram(message)

print("Сообщение отправлено в Telegram")

