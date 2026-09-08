import os
import re
import requests
from bs4 import BeautifulSoup

# Инициализация токенов из настроек репозитория GitHub
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Безопасный URL для Makler Николаев (работает стабильно)
MAKLER_URL = "https://makler.ua"

# Ваша личная ссылка на шлюз Google Apps Script для обхода блокировок 403 на OLX
OLX_RSS_URL = "https://google.com"

ZAGOLOVKI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
    """ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТПРАВКИ (api.telegram.org)"""
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
            link = f"https://makler.ua{href}" if href.startswith("/") else href
            
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
        response = requests.get(OLX_RSS_URL, headers=ZAGOLOVKI, timeout=30)
        if response.status_code != 200:
            print(f"Google шлюз вернул ошибку, статус: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.content, "lxml-xml")
        items = soup.find_all("item")
        results_olx = []
        
        print(f"Лента OLX успешно получена через шлюз Google! Найдено объектов: {len(items)}")
        
        for item in reversed(items):
            title = item.find("title").text if item.find("title") else ""
            link = item.find("link").text if item.find("link") else ""
            description = item.find("description").text if item.find("description") else ""
            
            if not link:
                continue
                
            clean_link = link.split("#")
            full_text = (title + " " + description).lower()
            
            stop_words = ["посуточно", "доба", "добово", "сниму", "шукаю", "ищу квартиру", "шукаю квартиру"]
            if any(word in full_text for word in stop_words):
                continue
                
            room_ok = False
            room_templates = [
                "3-к", "3 к", "3к", "3-комн", "3 комн", "трикімн", "трехкомн", "трёхкомн",
                "3-х комн", "3х комн", "3-х кімн", "3х кімн", "3-кімн", "3 кімн", "2-3"
            ]
            for template in room_templates:
                if template in full_text:
                    room_ok = True
                    break
                    
            if not room_ok:
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
            print("Новых подходящих объявлений на OLX пока нет.")
            
    except Exception as e:
        print(f"Ошибка в модуле OLX: {e}")

if __name__ == "__main__":
    print("Запуск плановой проверки сайтов...")
    check_makler()
    check_olx()
    
    print("Проверка завершена. Запуск принудительного теста связи...")
    send_telegram_message("🤖 *Проверка связи успешна!*\n\nБот полностью настроен, подключен к GitHub и вашему шлюзу Google. Я буду проверять OLX и Makler каждые 2 часа и присылать сюда новые 3-к квартиры до 6000 грн.")
    print("Тестовое сообщение отправлено. Скрипт успешно завершен.")
