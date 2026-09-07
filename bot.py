import os
import re
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/nik-nikolaev/real-estate/real-estate-for-rent/apartments-for-rent"

response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

found = []

for link in soup.find_all("a", href=True):
    text = " ".join(link.stripped_strings)

    # Ищем только 3-комнатные объявления
    if not re.search(r"\b3\s*(?:-|х|x)?\s*(?:ком|к|кім)", text, re.I):
        continue

    # Ищем цену до 6000 грн
    prices = re.findall(r"[\d\s]+(?=\s*(?:UAH|грн))", text, re.I)
    if not prices:
        continue

    price = int(re.sub(r"\D", "", prices[0]))
    if price > 6000:
        continue

    href = link["href"]

    if href.startswith("/"):
        href = "https://makler.ua" + href

    found.append((text, price, href))

# Убираем дубли
unique = {}
for text, price, href in found:
    unique[href] = (text, price, href)

found = list(unique.values())

if not found:
    message = "🏠 «Николаев Аренда»\n\nНовых подходящих объявлений пока не найдено."
else:
    message = "🏠 «Николаев Аренда»\n\nНайдены подходящие объявления:\n\n"

    for text, price, href in found[:10]:
        message += f"💰 {price} грн\n{text[:300]}\n{href}\n\n"

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

result = requests.post(
    telegram_url,
    json={
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    },
    timeout=30
)

result.raise_for_status()

print(f"Отправлено объявлений: {len(found)}")
