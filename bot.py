import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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

links = []

for a in soup.find_all("a", href=True):

    href = a["href"]

    # Нас интересуют только ссылки вида /an/123456
    if not re.search(r"/an/\d+", href):
        continue

    full_url = urljoin(URL, href)

    if full_url not in links:
        links.append(full_url)


print("================================")
print("НАЙДЕНЫ НАСТОЯЩИЕ ОБЪЯВЛЕНИЯ:", len(links))
print("================================")

for link in links[:10]:
    print(link)


# Показываем HTML родительского элемента первой настоящей ссылки
if links:

    first_link = links[0]

    first_a = None

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if re.search(r"/an/\d+", href):
            first_a = a
            break

    if first_a:

        print("\n========== НАСТОЯЩАЯ КАРТОЧКА ==========")

        parent = first_a

        # Поднимаемся на несколько уровней,
        # чтобы увидеть контейнер объявления
        for _ in range(4):

            if parent.parent:
                parent = parent.parent

        print(parent.prettify()[:8000])

        print("========== КОНЕЦ КАРТОЧКИ ==========")


# Telegram
message = (
    "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    f"Найдено настоящих объявлений: {len(links)}"
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

