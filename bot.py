import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Инициализация токенов из переменных окружения GitHub Actions
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# URL для Makler
MAKLER_URL = "https://makler.ua[]=17&city[]=384&city[]=372&city[]=373&city[]=374&city[]=375&city[]=376"

# URL для OLX (RSS-лента)
OLX_RSS_URL = "https://olx.ua"

ZAGOLOVKI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Глобальные множества для отслеживания отправленного жилья
sent_makler_ads = set()
sent_olx_ads = set()

def send_telegram_message(message_text):
    """Единая функция для отправки уведомлений в Telegram чат"""
    telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text
    }
    try:
        response_tg = requests.post(telegram_url, json=payload, timeout=30)
        response_tg.raise_for_status()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

def check_makler():
    """Логика парсинга Makler с вашими оригинальными фильтрами"""
    try:
        response = requests.get(MAKLER_URL, headers=ZAGOLOVKI, timeout=30)
        response.raise_for_status()
        
        print("Найти статью (статус):", response.status_code)
        soup = BeautifulSoup(response.text, "html.parser")
        
        articles = soup.find_all("article", id=re.compile(r"^tr_an-"))
        print("Найти статью (кол-во):", len(articles))
        
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
            is_daily = False
            for word in daily_words:
                if word in full_text:
                    is_daily = True
                    break
                    
            if is_daily:
                continue
                
            href = title_tag.get("href", "")
            link = urljoin("https://makler.ua", href)
            
            if link not in sent_makler_ads:
                sent_makler_ads.add(link)
                card = f"🏠 {title}\n💵 {price} грн\n📄 {description}\n🔗 {link}"
                results.append(card)
                
        print("Подходящие объявления Makler:", len(results))
        
        if results:
            message = "🏠 НИКОЛАЕВ АРЕНДА\n\nНайдены подходящие объявления:\n\n" + "\n\n".join(results)
            send_telegram_message(message)
            
    except Exception as e:
        print(f"Ошибка в модуле Makler: {e}")

def check_olx():
    """Изолированный модуль парсинга OLX через RSS"""
    try:
        response = requests.get(OLX_RSS_URL, headers=ZAGOLOVKI, timeout=30)
        if response.status_code != 200:
            print(f"OLX вернул статус: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        
        results_olx = []
        
        for item in reversed(items):
            title = item.find("title").text if item.find("title") else ""
            link = item.find("link").text if item.find("link") else ""
            description = item.find("description").text if item.find("description") else ""
            
            if not link:
                continue
                
            clean_link = link.split("#")[0]
            full_text = (title + " " + description).lower()
            
            stop_words = ["посуточно", "доба", "добово", "сниму", "шукаю", "ищу квартиру", "ищу 3"]
            if any(word in full_text for word in stop_words):
                continue
                
            if clean_link not in sent_olx_ads:
                sent_olx_ads.add(clean_link)
                
                price_search = re.search(r"(\d[\d\s]*)\s*(грн|uah)", title, re.IGNORECASE)
                price_str = "Цена указана на сайте"
                if price_search:
                    price_str = f"{price_search.group(1).strip()} грн"
                
                card = f"🏠 {title}\n💵 {price_str}\n🔗 {clean_link}"
                results_olx.append(card)
                
        print("Подходящие объявления OLX:", len(results_olx))
        
        if results_olx:
            message = "🏠 НИКОЛАЕВ АРЕНДА (OLX)\n\nНайдены новые объекты:\n\n" + "\n\n".join(results_olx)
            send_telegram_message(message)
            
    except Exception as e:
        print(f"Ошибка в модуле OLX: {e}")

if __name__ == "__main__":
    print("Бот запущен. Выполняется первичный сбор текущих объявлений...")
    
    check_makler()
    check_olx()
    
    while True:
        print("Плановая проверка обновлений на сайтах...")
        check_makler()
        check_olx()
        time.sleep(600)  # Проверка каждые 10 минут
