import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Инициализация токенов из настроек репозитория GitHub
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Исправленная и полная ссылка для Makler
MAKLER_URL = "https://makler.ua[]=17&city[]=384&city[]=372&city[]=373&city[]=374&city[]=375&city[]=376"

# Прямая RSS ссылка на OLX
OLX_RSS_URL = "https://olx.ua"

# Расширенные заголовки для имитации реального браузера и обхода Cloudflare
ZAGOLOVKI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

MAKLER_CACHE = "makler_cache.txt"
OLX_CACHE = "olx_cache.txt"

def load_cache(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_cache(filename, cache_set):
    with open(filename, "w", encoding="utf-8") as f:
        for item in cache_set:
            f.write(f"{item}\n")

sent_makler_ads = load_cache(MAKLER_CACHE)
sent_olx_ads = load_cache(OLX_CACHE)

def send_telegram_message(message_text):
    """Отправка уведомлений в Telegram"""
    telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        response_tg = requests.post(telegram_url, json=payload, timeout=30)
        response_tg.raise_for_status()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

def check_makler():
    global sent_makler_ads
    try:
        response = requests.get(MAKLER_URL, headers=ZAGOLOVKI, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("article", id=re.compile(r"^tr_an-"))
        results = []
        
        for article in articles:
            title_tag = article.select_one(".ls-detail_antTitle a")
            price_tag = article.select_one(".ls-detail_price")
            text_tag = article.select_one(".ls-detail_anText")
            
            if not title_tag:
                continue
                
            title = title_tag.get_text(" ", strip=True)
            price_text = price_tag.get_text(" ", strip=True) if price_tag else ""
            description = text_tag.get_text(" ", strip=True) if text_tag else ""
            full_text = (title + " " + description).lower()
            
            price_match = re.search(r"([\d\s]+)\s*(uah|грн)", price_text, re.IGNORECASE)
            if not price_match:
                continue
            price = int(re.sub(r"\D", "", price_match.group(1)))
            if price <= 0 or price > 6000:
                continue
                
            room_ok = False
            room_templates = [
                "3х кімнатну", "3-х кімнатну", "3 кімнатну", "3-комнатная",
                "3 комнатная", "3-х комнатная", "3х комнатная", "3-комнатная",
                "3-комнатная", "3-к.", "3-к", "3 к/к", "3-к/к"
            ]
            for template in room_templates:
                if template in full_text:
                    room_ok = True
                    break
            if not room_ok:
                continue
                
            daily_words = ["посуная", "тестирование", "за сутки", "за ночь", "на ночь", "посуарный", "посуточное", "посуточно", "доба"]
            if any(word in full_text for word in daily_words):
                continue
                
            href = title_tag.get("href", "")
            link = urljoin("https://makler.ua", href)
            
            if link not in sent_makler_ads:
                sent_makler_ads.add(link)
                card = f"🏠 *{title}*\n💵 {price} грн\n📄 {description}\n🔗 [Открыть на Makler]({link})"
                results.append(card)
            
        if results:
            message = "🏠 *НОВЫЕ ОБЪЯВЛЕНИЯ НА MAKLER:*\n\n" + "\n\n---\n\n".join(results)
            send_telegram_message(message)
            save_cache(MAKLER_CACHE, sent_makler_ads)
        else:
            print("Новых объявлений на Makler пока нет.")
            
    except Exception as e:
        print(f"Ошибка в модуле Makler: {e}")

def check_olx():
    global sent_olx_ads
    try:
        # Используем прокси-зеркало или CORS-прокси для гарантированного обхода ошибки 403 на GitHub
        # Это перенаправляет запрос так, что OLX видит обычного пользователя, а не робота
        proxy_url = f"https://allorigins.win{requests.utils.quote(OLX_RSS_URL)}"
        
        response = requests.get(proxy_url, headers={"User-Agent": ZAGOLOVKI["User-Agent"]}, timeout=30)
        if response.status_code != 200:
            print(f"Прокси вернул статус {response.status_code}. Пробуем напрямую...")
            response = requests.get(OLX_RSS_URL, headers=ZAGOLOVKI, timeout=30)
            
        # Распаковываем содержимое из JSON-ответа прокси
        if "contents" in response.json():
            xml_content = response.json()["contents"]
        else:
            xml_content = response.content

        soup = BeautifulSoup(xml_content, "xml")
        items = soup.find_all("item")
        results_olx = []
        
        print(f"OLX RSS успешно прочитан. Найдено сырых объявлений: {len(items)}")
        
        for item in reversed(items):
            title = item.find("title").text if item.find("title") else ""
            link = item.find("link").text if item.find("link") else ""
            description = item.find("description").text if item.find("description") else ""
            
            if not link:
                continue
                
            clean_link = link.split("#")[0]
            full_text = (title + " " + description).lower()
            
            stop_words = ["посуточно", "доба", "добово", "сниму", "шукаю", "ищу квартиру", "шукаю квартиру"]
            if any(word in full_text for word in stop_words):
                continue
                
            if clean_link not in sent_olx_ads:
                sent_olx_ads.add(clean_link)
                
                price_search = re.search(r"(\d[\d\s]*)\s*(грн|uah)", title, re.IGNORECASE)
                price_str = f"{price_search.group(1).strip()} грн" if price_search else "Цена указана на сайте"
                
                card = f"🏠 *{title}*\n💵 {price_str}\n🔗 [Открыть на OLX]({clean_link})"
                results_olx.append(card)
                
        if results_olx:
            message = "🏠 *НОВЫЕ ОБЪЯВЛЕНИЯ НА OLX:*\n\n" + "\n\n---\n\n".join(results_olx)
            send_telegram_message(message)
            save_cache(OLX_CACHE, sent_olx_ads)
        else:
            print("Новых объявлений на OLX пока нет.")
            
    except Exception as e:
        print(f"Ошибка в модуле OLX: {e}")

if __name__ == "__main__":
    print("Запуск плановой проверки сайтов...")
    check_makler()
    check_olx()
    print("Проверка успешно завершена.")
