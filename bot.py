import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

LIST_URL = "https://www.olx.ua/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/3-kmnati/nikolaev_106/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
}


def get_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


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


# Получаем страницу OLX
response = requests.get(
    LIST_URL,
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


# Собираем ссылки на объявления
links = []

for a in soup.find_all("a", href=True):

    href = a["href"]

    if "/d/obyavlenie/" not in href:
        continue

    full_url = urljoin(LIST_URL, href)

    if full_url not in links:
        links.append(full_url)


print("Найдено ссылок OLX:", len(links))


# Показываем первые найденные ссылки для диагностики
for link in links[:10]:
    print("OLX:", link)


# Пока только проверяем, что OLX отдаёт объявления.
# Фильтрацию сделаем после успешного теста.

if links:

    message = "🏠 НИКОЛАЕВ АРЕНДА\n\n"
    message += "OLX найдено объявлений: "
    message += str(len(links))
    message += "\n\n"

    for link in links[:5]:
        message += f"🔗 {link}\n"

else:

    message = (
        "🏠 НИКОЛАЕВ АРЕНДА\n\n"
        "OLX не вернул ссылки на объявления."
    )


send_telegram(message)

print("Сообщение отправлено в Telegram")
