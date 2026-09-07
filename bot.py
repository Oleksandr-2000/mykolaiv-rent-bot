import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://makler.ua/ua/nik-nikolaev/real-estate/real-estate-for-rent/apartments-for-rent"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
}

response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

print("Размер страницы:", len(response.text))
print(
    "Заголовок:",
    soup.title.get_text(strip=True)
    if soup.title
    else "нет"
)

# Ищем все ссылки на объявления
links = []

for a in soup.find_all("a", href=True):

    href = a["href"]

    if "/an/" not in href:
        continue

    if href not in links:
        links.append(href)

print("Найдено ссылок:", len(links))

# Показываем первые 5 элементов,
# в которых находятся ссылки на объявления
count = 0

for a in soup.find_all("a", href=True):

    if "/an/" not in a["href"]:
        continue

    parent = a.parent

    print("\n========== КАРТОЧКА", count + 1, "==========")
    print(parent.prettify()[:4000])
    print("========== КОНЕЦ КАРТОЧКИ ==========\n")

    count += 1

    if count >= 5:
        break


# Telegram
message = (
    "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    f"Диагностика Makler завершена.\n"
    f"Найдено ссылок: {len(links)}"
)

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

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
