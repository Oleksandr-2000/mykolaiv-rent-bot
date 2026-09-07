import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/real-estate/real-estate-for-rent/apartments-for-rent/"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8",
}


def send_telegram(text):
    telegram_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        telegram_url,
        json={
            "chat_id": CHAT_ID,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()


# Получаем страницу
response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30,
)

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser",
)


print("Размер страницы:", len(response.text))


articles = soup.find_all(
    "article",
    id=re.compile(r"^tr_an-\d+$")
)


print("Найдено объявлений:", len(articles))


results = []


for article in articles:

    title_tag = article.select_one(
        "a.ls-detail_anUrl"
    )

    price_tag = article.select_one(
        ".ls-detail_price"
    )

    text_tag = article.select_one(
        ".ls-detail_anText"
    )

    if not title_tag:
        continue

    title = title_tag.get_text(
        " ",
        strip=True,
    )

    description = ""

    if text_tag:
        description = text_tag.get_text(
            " ",
            strip=True,
        )

    full_text = (
        title + " " + description
    ).lower()


    # -----------------------------
    # Цена
    # -----------------------------

    if not price_tag:
        continue

    price_text = price_tag.get_text(
        " ",
        strip=True,
    )

    price_match = re.search(
        r"(\d[\d\s]*)\s*(uah|грн)",
        price_text,
        re.IGNORECASE,
    )

    if not price_match:
        continue

    price = int(
        re.sub(
            r"\D",
            "",
            price_match.group(1),
        )
    )


    # До 6000 грн
    if price > 6000:
        continue


    # -----------------------------
    # Только 3 комнаты
    # -----------------------------

    room_patterns = [
        r"3[- ]комнатн",
        r"3[- ]кімнатн",
        r"3х[- ]комнатн",
        r"3х[- ]кімнатн",
        r"3 х комнатн",
        r"3 х кімнатн",
    ]

    if not any(
        re.search(pattern, full_text)
        for pattern in room_patterns
    (sad)
        continue


    # -----------------------------
    # Не отдельная комната
    # -----------------------------

    bad_room_patterns = [
        "1 комната в 3",
        "1 кімната в 3",
        "комната в 3х комнатной",
        "кімната в 3х кімнатній",
        "комнату в 3х комнатной",
        "кімнату в 3х кімнатній",
    ]

    if any(
        word in full_text
        for word in bad_room_patterns
    (sad)
        continue


    # -----------------------------
    # Исключаем посуточную аренду
    # -----------------------------

    daily_words = [
        "посуточно",
        "подобово",
        "посуточная",
        "подобова",
        "за сутки",
        "за ночь",
        "на ночь",
    ]

    if any(
        word in full_text
        for word in daily_words
    (sad)
        continue


    # -----------------------------
    # Ссылка
    # -----------------------------

    href = title_tag.get(
        "href"
    )

    if not href:
        continue

    link = urljoin(
        URL,
        href,
    )


    results.append(
        {
            "title": title,
            "price": price,
            "description": description,
            "link": link,
        }
    )


print(
    "Подходящих объявлений:",
    len(results),
)


# -----------------------------
# Формируем сообщение
# -----------------------------

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

print(
    "Сообщение отправлено в Telegram"
)
