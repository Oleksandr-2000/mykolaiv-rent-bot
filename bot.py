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

    r = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    r.raise_for_status()


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
    description = (
        text_tag.get_text(" ", strip=True)
        if text_tag
        else ""
    )

    full_text = f"{title} {description}".lower()

    # Цена
    price = None

    if price_tag:
        price_text = price_tag.get_text(" ", strip=True)

        match = re.search(
            r"(\d[\d\s]*)\s*(uah|грн)",
            price_text,
            re.IGNORECASE,
        )

        if match:
            price = int(
                re.sub(r"\D", "", match.group(1))
            )

    if price is None:
        continue

    # Максимальная цена
    if price > 6000:
        continue

    # Только 3 комнаты
    three_rooms = any(
        re.search(pattern, full_text)
        for pattern in [
            r"\b3[- ]комнат",
            r"\b3[- ]кімнат",
            r"\b3х[- ]?комнат",
            r"\b3х[- ]?кімнат",
            r"\bтри[- ]комнат",
            r"\bтри[- ]кімнат",
        ]
    )

    if not three_rooms:
        continue

    # Исключаем посуточные варианты
    daily_words = [
        "посуточно",
        "подобово",
        "посуточная",
        "подобова",
        "за сутки",
        "за ночь",
        "ночь",
    ]

    if any(word in full_text for word in daily_words):
        continue

    # Ссылка
    href = link_tag.get("href")

    if not href:
        continue

    link = urljoin(LIST_URL, href)

    results.append({
        "title": title,
        "price": price,
        "description": description,
        "link": link,
    })


print("Подходящих объявлений:", len(results))


if results:

    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    message += "Найдены подходящие объявления:\n\n"

    for item in results[:10]:

        message += (
            f"🏠 {item['title']}\n"
            f"💰 {item['price']} грн\n"
            f"📝 {item['description'][:300]}\n"
            f"🔗 {item['link']}\n\n"
        )

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих объявлений пока не найдено."
    )


send_telegram(message)

print("Сообщение отправлено в Telegram")
