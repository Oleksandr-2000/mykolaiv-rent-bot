import requests
from bs4 import BeautifulSoup

url = "https://makler.ua/ua/real-estate/real-estate-for-rent/apartments-for-rent/nikolaev_106/"

response = requests.get(
    url,
    headers={
        "User-Agent": "Mozilla/5.0"
    },
    timeout=30
)

print("HTTP:", response.status_code)
print("Размер страницы:", len(response.text))

soup = BeautifulSoup(response.text, "html.parser")

articles = soup.find_all("article")

print("Найдено article:", len(articles))

for article in articles[:5]:
    title = article.select_one(".ls-detail_antTitle")
    price = article.select_one(".ls-detail_price")

    if title:
        print("Название:", title.get_text(" ", strip=True))

    if price:
        print("Цена:", price.get_text(" ", strip=True))

    print("---")
