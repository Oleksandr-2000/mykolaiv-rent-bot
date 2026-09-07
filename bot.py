import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/nik-nikolaev/real-estate/real-estate-for-rent/apartments-for-rent"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
    )
}


def send_telegram(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()


# Загружаем список объявлений
response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

print("Размер страницы:", len(response.text))

# Находим реальные карточки
cards = soup.find_all(
    "article",
    attrs={"id": re.compile(r"^tr_an-\d+$")}
)

print("Найдено карточек:", len(cards))

results = []


for card in cards:

    # -------------------------
    # Ссылка
    # -------------------------

    link_tag = card.select_one("a.ls-detail_anUrl")

    if not link_tag:
        continue

    href = link_tag.get("href")

    if not href:
        continue

    link = urljoin(URL, href)


    # -------------------------
    # Название
    # -------------------------

    title = link_tag.get_text(
        " ",
        strip=True
    )

    title_lower = title.lower()


    # -------------------------
    # Описание
    # -------------------------

    description_tag = card.select_one(
        ".ls-detail_anText"
    )

    description = (
        description_tag.get_text(
            " ",
            strip=True
        )
        if description_tag
        else ""
    )

    full_text = (
        title + " " + description
    )

    text_lower = full_text.lower()


    # -------------------------
    # Цена
    # -------------------------

    price_tag = card.select_one(
        ".ls-detail_price"
    )

    if not price_tag:
        continue

    price_text = price_tag.get_text(
        " ",
        strip=True
    )

    price_match = re.search(
        r"([\d\s]+)",
        price_text
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


    # -------------------------
    # Максимум 6000 грн
    # -------------------------

    if price > 6000:
        continue


    # -------------------------
    # Исключаем посуточные
    # -------------------------

    bad_words = [
        "посуточно",
        "подобово",
        "посуточная",
        "посуточную",
        "сутки",
        "за ночь",
        "почасово",
        "на ночь",
    ]

    if any(
        word in text_lower
        for word in bad_words
    (sad)
        continue


    # -------------------------
    # Только 3 комнаты
    # -------------------------

    room_patterns = [
        r"\b3[- ]комнат",
        r"\b3х[- ]комнат",
        r"\b3х\s*комнат",
        r"\b3\s*комнат",
        r"\b3\s*кімнат",
        r"\b3[- ]кімнат",
        r"\bтр[её]хкомнат",
    ]

    if not any(
        re.search(pattern, text_lower)
        for pattern in room_patterns
    (sad)
        continue


    # -------------------------
    # Сохраняем
    # -------------------------

    results.append({
        "title": title,
        "description": description,
        "price": price,
        "link": link,
    })


print(
    "Подходящих объявлений:",
    len(results)
)


# -------------------------
# Telegram сообщение
# -------------------------

if results:

    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"

    for ad in results[:10]:

        message += (
            f"🏠 {ad['title']}\n"
            f"💰 {ad['price']} грн\n"
            f"📝 {ad['description']}\n"
            f"🔗 {ad['link']}\n\n"
        )

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "Подходящих объявлений пока не найдено."
    )


send_telegram(message)

print("Сообщение отправлено в Telegram")
