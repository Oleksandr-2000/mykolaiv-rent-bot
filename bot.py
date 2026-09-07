import requests
from bs4 import BeautifulSoup

url = "https://makler.ua/"

response = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

print("HTTP:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

for a in soup.find_all("a", href=True):

    href = a["href"]
    text = a.get_text(" ", strip=True)

    if "809" in href:

        print("ССЫЛКА:", href)
        print("ТЕКСТ:", text)
        print("---")
