import requests
from bs4 import BeautifulSoup

url = "https://makler.ua/"

response = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

print("HTTP:", response.status_code)
print("Размер:", len(response.text))

soup = BeautifulSoup(response.text, "html.parser")

for a in soup.find_all("a", href=True):

    text = a.get_text(" ", strip=True).lower()
    href = a["href"]

    if "микола" in text or "микол" in href.lower():

        print(
            "НАЙДЕНО:",
            text[:100],
            "=>",
            href
        )
