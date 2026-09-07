import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/real-estate/real-estate-for-rent/apartments-for-rent?list&region[]=17&city[]=384&city[]=372&city[]=373&city[]=374&city[]=375&city[]=376&city[]=377&city[]=378&city[]=3130&city[]=379&city[]=380&city[]=381&city[]=382&city[]=3131&city[]=3416&city[]=3132&city[]=3418&city[]=383&city[]=386&city[]=385&city[]=387&city[]=3133&city[]=388&city[]=3134&city[]=3417&city[]=389&city[]=390&currency_id=5&list=detail"

headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

print("HTTP:", response.status_code)
print("Размер страницы:", len(response.text))

soup = BeautifulSoup(response.text, "html.parser")

articles = soup.find_all("article", id=re.compile(r"^tr_an-"))
print("Найдено article:", len(articles))

for article in articles:
    title_tag = article.select_one(".ls-detail_antTitle a")
    price_tag = article.select_one(".ls-detail_price")

    if title_tag:
        title = title_tag.get_text(" ", strip=True)
    else:
        title = ""

    if price_tag:
        price = price_tag.get_text(" ", strip=True)
    else:
        price = ""

    print("ОБЪЯВЛЕНИЕ:", title)
    print("ЦЕНА:", price)
    print("---")

results = []

for article in articles:
    title_tag = article.select_one(".ls-detail_antTitle a")
    price_tag = article.select_one(".ls-detail_price")
    text_tag = article.select_one(".ls-detail_anText")

    if title_tag:
        title = title_tag.get_text(" ", strip=True)
    else:
        title = ""

    if price_tag:
        price_text = price_tag.get_text(" ", strip=True)
    else:
        price_text = ""

    if text_tag:
        description = text_tag.get_text(" ", strip=True)
    else:
        description = ""

    full_text = (title + " " + description).lower()

    match = re.search(r"(\d[\d\s]*)\s*(uah|грн)", price_text, re.I)

    if match:
        price = int(re.sub(r"\D", "", match.group(1)))
    else:
        price = 0

    room_ok = "3х кімнатну" in full_text
    room_ok = room_ok or "3-х кімнатну" in full_text
    room_ok = room_ok or "3 кімнатну" in full_text
    room_ok = room_ok or "3-комнатную" in full_text
    room_ok = room_ok or "3 комнатную" in full_text
    room_ok = room_ok or "3-х комнатную" in full_text
    room_ok = room_ok or "3х комнатную" in full_text

    daily = "посуточно" in full_text
    daily = daily or "подобово" in full_text
    daily = daily or "за сутки" in full_text
    daily = daily or "за ночь" in full_text
    daily = daily or "на ночь" in full_text

    if price <= 6000 and price > 0 and room_ok and not daily:
        href = title_tag.get("href", "")
        link = urljoin(URL, href)

        results.append(
            title + "\n"
            + "💰 " + str(price) + " грн\n"
            + "📝 " + description + "\n"
            + "🔗 " + link
        )

print("Подходящих объявлений:", len(results))

if results:
    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    message += "Найдены подходящие объявления:\n\n"
    message += "\n\n".join(results)
else:
    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    message += "Подходящих объявлений пока не найдено."

telegram_url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"

telegram = requests.post(
    telegram_url,
    json={"chat_id": CHAT_ID, "text": message},
    timeout=30
)

telegram.raise_for_status()

print("Сообщение отправлено в Telegram")
