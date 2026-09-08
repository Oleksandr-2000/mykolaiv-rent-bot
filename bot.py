import os
import re
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Инициализация токенов из настроек репозитория GitHub
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# URL сайтов для парсинга (Николаев, 3 комнаты, до 6000 грн)
MAKLER_URL = "https://makler.ua[]=17&city[]=384&city[]=372&city[]=373&city[]=374&city[]=375&city[]=376"
OLX_RSS_URL = "https://olx.ua"

ZAGOLOVKI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def send_telegram_message(message_text):
    """Отправка уведомлений в Telegram"""
    telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown"
    }
    try:
        response_tg = requests.post(telegram_url, json=payload, timeout=30)
        response_tg.raise_for_status()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

def check_makler():
    """Парсинг Makler за последние 2 часа"""
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
            
            # Проверка цены
            price_match = re.search(r"([\d\s]+)\s*(uah|грн)", price_text, re.IGNORECASE)
            if not price_match:
                continue
            price = int(re.sub(r"\D", "", price_match.group(1)))
            if price <= 0 or price > 6000:
                continue
                
            # Проверка строго 3 комнат
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
                
            # Исключаем посуточные
            daily_words = ["посуная", "тестирование", "за сутки", "за ночь", "на ночь", "посуарный", "посуточное", "посуточно", "доба"]
            if any(word in full_text for word in daily_words):
                continue
                
            href = title_tag.get("href", "")
            link = urljoin("https://makler.ua", href)
            
            card = f"🏠 *{title}*\n💵 {price} грн\n📄 {description}\n🔗 [Открыть на Makler]({link})"
            results.append(card)
            
        if results:
            message = "🏠 *НОВЫЕ ОБЪЯВЛЕНИЯ НА MAKLER (за 2 часа):*\n\n" + "\n\n---\n\n".join(results)
            send_telegram_message(message)
            
    except Exception as e:
        print(f"Ошибка в модуле Makler: {e}")

def check_olx():
    """Парсинг OLX за последние 2 часа по времени публикации из RSS"""
    try:
        response = requests.get(OLX_RSS_URL, headers=ZAGOLOVKI, timeout=30)
        if response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        
        results_olx = []
        текущее_время = datetime.now(timezone.utc)
        лимит_времени = текущее_время - timedelta(hours=2)
        
        for item in items:
            pub_date_tag = item.find("pubDate")
            if pub_date_tag:
                try:
                    # Пример формата: Tue, 08 Sep 2026 05:00:00 +0000
                    pub_time = datetime.strptime(pub_date_tag.text.strip(), "%a, %d %b %Y %H:%M:%S %z")
                    if pub_time < лимит_времени:
                        continue  # Объявление старее 2 часов, пропускаем
                except Exception:
                    pass
            
            title = item.find("title").text if item.find("title") else ""
            link = item.find("link").text if item.find("link") else ""
            description = item.find("description").text if item.find("description") else ""
            
            if not link:
                continue
                
            clean_link = link.split("#")[0]
            full_text = (title + " " + description).lower()
            
            # Фильтр стоп-слов
            stop_words = ["посуточно", "доба", "добово", "сниму", "шукаю", "ищу квартиру", "ищу 3"]
            if any(word in full_text for word in stop_words):
                continue
                
            price_search = re.search(r"(\d[\d\s]*)\s*(грн|uah)", title, re.IGNORECASE)
            price_str = f"{price_search.group(1).strip()} грн" if price_search else "Цена в объявлении"
            
            card = f"🏠 *{title}*\n💵 {price_str}\n🔗 [Открыть на OLX]({clean_link})"
            results_olx.append(card)
            
        if results_olx:
            message = "🏠 *НОВЫЕ ОБЪЯВЛЕНИЯ НА OLX (за 2 часа):*\n\n" + "\n\n---\n\n".join(results_olx)
            send_telegram_message(message)
            
    except Exception as e:
        print(f"Ошибка в модуле OLX: {e}")

if __name__ == "__main__":
    print("Запуск плановой проверки сайтов...")
    check_makler()
    check_olx()
    print("Проверка успешно завершена.")
