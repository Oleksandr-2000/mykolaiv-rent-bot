import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

LIST_URL = "https://makler.ua/ua/nik-nikolaev/real-estate/real-estate-for-rent/apartments-for-rent"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8",
}


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()


response = requests.get(
    LIST_URL,
    headers=HEADERS,
    timeout=30,
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

print("Размер страницы:", len(response.text))

articles = soup.find_all("article")

print("Найдено article:", len(articles))

results = []


for article in articles:

    title_tag = article.select_one(".ls-detail_antTitle")
    price_tag = article.select_one(".ls-detail_price")
    text_tag = article.select_one(".ls-detail_anText")
    link_tag = article.select_one("a.ls-detail_anUrl")

    if not title_tag or not link_tag:
        continue

    title = title_tag.get_text(" ", strip=True)

    description = ""

    if text_tag:
        description = text_tag.get_text(" ", strip=True)

    full_text = f"{title} {description}".lower()

    # --------------------------------
    # ЦЕНА
    # --------------------------------

    price = None

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

    if price is None:
        continue

    if price > 6000:
        continue

    # --------------------------------
    # ТОЛЬКО ВСЯ 3-КОМНАТНАЯ КВАРТИРА
    # --------------------------------

    three_rooms = any(
        re.search(pattern, full_text)
        for pattern in [
            r"\bздаю\s+3х\s+кімнатну",
            r"\bздам\s+3х\s+кімнатну",
            r"\bздається\s+3[- ]кімнатна",
            r"\bсдам\s+3[- ]комнатную",
            r"\bсдается\s+3[- ]комнатная",
            r"\bсдаю\s+3[- ]комнатную",
            r"\bаренда\s+3[- ]комнатной",
            r"\bоренда\s+3[- ]кімнатної",
        ]
    )

    if not three_rooms:
        continue

    # --------------------------------
    # НЕ БЕРЁМ ОТДЕЛЬНУЮ КОМНАТУ
    # --------------------------------

    single_room_words = [
        "1 комната в 3",
        "1 кімната в 3",
        "комната в 3х комнатной",
        "кімната в 3х кімнатній",
        "комнату в 3х комнатной",
        "кімнату в 3х кімнатній",
    ]

    if any(
        word in full_text
        for word in single_room_words
    (sad)
        continue

    # --------------------------------
    # ИСКЛЮЧАЕМ ПОСУТОЧНУЮ АРЕНДУ
    # --------------------------------

    daily_words = [
        "посуточно",
        "подобово",
        "посуточная",
        "подобова",
        "за сутки",
        "за ночь",
        "ночь",
    ]

    if any(
        word in full_text
        for word in daily_words
    (sad)
        continue

    # --------------------------------
    # ССЫЛКА
    # --------------------------------

    href = link_tag.get("href")

    if not href:
        continue

    link = urljoin(
        LIST_URL,
        href
    )

    results.append({
        "title": title,
        "price": price,
        "description": description,
        "link": link,
    })


print(
    "Подходящих объявлений:",
    len(results)
)


# --------------------------------
# TELEGRAM
# --------------------------------

if results:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Найдены подходящие объявления:\n\n"
    )

    for item in results[:10]:

        message += (
            f"🏠 {item['title']}\n"
            f"💰 {item['price']} грн/мес\n"
            f"📝 {item['description'][:400]}\n"
            f"🔗 {item['link']}\n\n"
        )

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих объявлений пока не найдено."
    )


send_telegram(message)

print("Сообщение отправлено в Telegram")
