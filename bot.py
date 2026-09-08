import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Инициализация токенов из переменных окружения GitHub Actions
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# URL для Makler (из вашего кода)
MAKLER_URL = "https://makler.ua[]=17&city[]=384&city[]=372&city[]=373&city[]=374&city[]=375&city[]=376"

# URL для OLX (RSS-лента: Николаев, 3 комнаты, до 6000 грн)
OLX_RSS_URL = "https://olx.ua"

ZAGOLOVKI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Глобальные множества для отслеживания отправленного жилья, чтобы не спамить дублями
отправленные_маstatus = set()
отправленные_olx = set()

def send_telegram_message(message_text):
    """Единая функция для отправки уведомлений в Telegram чат"""
    telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text
    }
    try:
        ответ_телеграмма = requests.post(telegram_url, json=payload, timeout=30)
        ответ_телеграмма.raise_for_status()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

def check_makler():
    """Полная оригинальная логика парсинга Makler с вашими фильтрами"""
    try:
        ответ = requests.get(MAKLER_URL, headers=ZAGOLOVKI, timeout=30)
        ответ.raise_for_status()
        
        print("Найти статью:", ответ.status_code)
        суп = BeautifulSoup(ответ.text, "html.parser")
        
        # Поиск блоков по вашему регулярному выражению для класса tr_an-
        статьи = суп.find_all("article", id=re.compile(r"^tr_an-"))
        print("Найти статью:", len(статьи))
        
        результаты = []
        
        for статья in статьи:
            заголовок_тег = статья.select_one(".ls-detail_antTitle a")
            ценник = статья.select_one(".ls-detail_price")
            текстовый_тег = статья.select_one(".ls-detail_anText")
            
            if not заголовок_тег:
                continue
                
            заголовок = заголовок_тег.get_text(" ", strip=True)
            
            цена_текст = ценник.get_text(" ", strip=True) if ценник else ""
            описание = текстовый_тег.get_text(" ", strip=True) if текстовый_тег else ""
            
            полный_текст = (заголовок + " " + описание).lower()
            
            # Проверка цены регулярным выражением
            цена_соответствие = re.search(r"([\d\s]+)\s*(uah|грн)", цена_текст, re.IGNORECASE)
            if not цена_соответствие:
                continue
                
            цена = int(re.sub(r"\D", "", цена_соответствие.group(1)))
            
            # Фильтр цены от 0 до 6000 грн
            if цена <= 0 or цена > 6000:
                continue
                
            # Проверка шаблонов комнат (строго 3-комнатные)
            комната_ok = False
            шаблоны_комнат = [
                "3х кімнатну", "3-х кімнатну", "3 кімнатну", "3-комнатная",
                "3 комнатная", "3-х комнатная", "3х комнатная", "3-комнатная",
                "3-комнатная", "3-к.", "3-к", "3 к/к", "3-к/к"
            ]
            for шаблон in шаблоны_комнат:
                if шаблон in полный_текст:
                    комната_ok = True
                    break
                    
            if not комната_ok:
                continue
                
            # Исключение посуточных ключевых слов
            ежедневные_слова = ["посуная", "тестирование", "за сутки", "за ночь", "на ночь", "посуарный", "посуточное", "посуточно", "доба"]
            is_daily = False
            for слово in ежедневные_слова:
                if слово in полный_текст:
                    is_daily = True
                    break
                    
            if is_daily:
                continue
                
            # Сбор ссылки объявления
            href = заголовок_тег.get("href", "")
            связь = urljoin("https://makler.ua", href)
            
            # Если это абсолютно новая ссылка, которой не было в отправленных
            if связь not in отправленные_маstatus:
                отправленные_маstatus.add(связь)
                
                # Формируем структуру карточки как на ваших скриншотах
                карточка = f"🏠 {заголовок}\n💵 {цена} грн\n📄 {описание}\n🔗 {связь}"
                результаты.append(карточка)
                
        print("Подходящие объявления:", len(результаты))
        
        if результаты:
            сообщение = "🏠 НИКОЛАЕВ АРЕНДА\n\nНайдены подходящие объявления:\n\n" + "\n\n".join(результаты)
            send_telegram_message(сообщение)
            
    except Exception as e:
        print(f"Ошибка в модуле Makler: {e}")

def check_olx():
    """Новый изолированный модуль парсинга OLX через RSS"""
    try:
        ответ = requests.get(OLX_RSS_URL, headers=ZAGOLOVKI, timeout=30)
        if ответ.status_code != 200:
            return
            
        суп = BeautifulSoup(ответ.content, "xml")
        объявления = суп.find_all("item")
        
        результаты_olx = []
        
        # Проверяем от старых к свежим
        for объявление in reversed(объявления):
            заголовок = объявление.find("title").text if объявление.find("title") else ""
            ссылка = объявление.find("link").text if объявление.find("link") else ""
            описание = объявление.find("description").text if объявление.find("description") else ""
            
            if not ссылка:
                continue
                
            чистая_ссылка = ссылка.split("#")[0]
            весь_текст = (заголовок + " " + описание).lower()
            
            # Фильтр стоп-слов для OLX (посуточно и "сниму жилье")
            стоп_слова = ["посуточно", "доба", "добово", "сниму", "шукаю", "ищу квартиру", "ищу 3"]
            if any(слово in весь_текст for слово в стоп_слова):
                continue
                
            if чистая_ссылка not in отправленные_olx:
                отправленные_olx.add(чистая_ссылка)
                
                # Поиск цены в тексте объявления на OLX RSS
                цена_поиск = re.search(r"(\d[\d\s]*)\s*(грн|uah)", заголовок, re.IGNORECASE)
                цена_стр = "Цена указана на сайте"
                if цена_поиск:
                    цена_стр = f"{цена_поиск.group(1).strip()} грн"
                
                карточка = f"🏠 {заголовок}\n💵 {цена_стр}\n🔗 {чистая_ссылка}"
                результаты_olx.append(карточка)
                
        if результаты_olx:
            сообщение = "🏠 НИКОЛАЕВ АРЕНДА (OLX)\n\nНайдены новые объекты:\n\n" + "\n\n".join(результаты_olx)
            send_telegram_message(сообщение)
            
    except Exception as e:
        print(f"Ошибка в модуле OLX: {e}")

if __name__ == "__main__":
    print("Бот запущен. Выполняется первичный сбор текущих объявлений...")
    
    # Первые вызовы заполнят базу отправленных ссылок, чтобы не присылать старые дубли
    check_makler()
    check_olx()
    
    # Бесконечный цикл проверки каждые 10 минут
    while True:
        print("Плановая проверка обновлений на сайтах...")
        check_makler()
        check_olx()
        time.sleep(600)  # 600 секунд = 10 минут
