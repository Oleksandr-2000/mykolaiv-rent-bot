import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
CHAT_ID = os.environ["CHAT_ID"].strip()


# =========================
# MAKLER
# =========================

MAKLER_URL = (
    "https://makler.ua/ua/real-estate/"
    "real-estate-for-rent/apartments-for-rent"
    "?list&region[]=17&city[]=384&city[]=372&city[]=373"
    "&city[]=374&city[]=375&city[]=376&city[]=377"
    "&city[]=378&city[]=3130&city[]=379&city[]=380"
    "&city[]=381&city[]=382&city[]=3131&city[]=3416"
    "&city[]=3132&city[]=3418&city[]=383&city[]=386"
    "&city[]=385&city[]=387&city[]=3133&city[]=388"
    "&city[]=3134&city[]=3417&city[]=389&city[]=390"
    "&currency_id=5&list=detail"
)


# =========================
# OLX
# =========================

OLX_RSS_URL = "ВСТАВЬ_СЮДА_ССЫЛКУ_ОЛХ_ШЛЮЗА"


# =========================
# HEADERS
# =========================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# =========================
# КЭШ
# =========================

MAKLER_CACHE = "makler_cache.txt"
OLX_CACHE = "olx_cache.txt"


def load_cache(filename):

    if os.path.exists(filename):

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return {
                line.strip()
                for line in f
                if line.strip()
            }

    return set()


def save_cache(filename, cache_set):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        for item in cache_set:
            f.write(item + "\n")


sent_makler_ads = load_cache(
    MAKLER_CACHE
)

sent_olx_ads = load_cache(
    OLX_CACHE
)


# =========================
# ВРЕМЯ УКРАИНЫ
# =========================

def is_work_time():

    now = datetime.now(
        ZoneInfo("Europe/Kyiv")
    )

    print(
        "Украинское время:",
        now.strftime("%Y-%m-%d %H:%M:%S")
    )

    if 8 <= now.hour < 18:

        return True

    print(
        "Сейчас вне рабочего времени "
        "08:00-18:00."
    )

    return False


# =========================
# TELEGRAM
# =========================

def send_telegram_message(message_text):

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:

        response = requests.post(
            telegram_url,
            json=payload,
            timeout=30
        )

        print(
            "Telegram HTTP:",
            response.status_code
        )

        print(
            "Telegram ответ:",
            response.text
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):

            print(
                "Telegram вернул ошибку:",
                data
            )

            return False

        print(
            "Сообщение успешно отправлено "
            "в Telegram"
        )

        return True

    except Exception as e:

        print(
            "Ошибка отправки сообщения "
            "в Telegram:",
            e
        )

        return False
        # =========================
# MAKLER
# =========================

def check_makler():

    global sent_makler_ads

    try:

        response = requests.get(
            MAKLER_URL,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        articles = soup.find_all(
            "article",
            id=re.compile(r"^tr_an-")
        )

        results = []

        print(
            f"Makler: найдено объектов: "
            f"{len(articles)}"
        )

        for article in articles:

            title_tag = article.select_one(
                ".ls-detail_antTitle a"
            )

            price_tag = article.select_one(
                ".ls-detail_price"
            )

            text_tag = article.select_one(
                ".ls-detail_anText"
            )

            if not title_tag:
                continue

            title = title_tag.get_text(
                " ",
                strip=True
            )

            price_text = (
                price_tag.get_text(
                    " ",
                    strip=True
                )
                if price_tag
                else ""
            )

            description = (
                text_tag.get_text(
                    " ",
                    strip=True
                )
                if text_tag
                else ""
            )

            full_text = (
                title + " " + description
            ).lower()

            # =========================
            # ЦЕНА
            # =========================

            price_match = re.search(
                r"([\d\s]+)\s*(uah|грн)",
                price_text,
                re.IGNORECASE
            )

            if not price_match:
                continue

            price = int(
                re.sub(
                    r"\D",
                    "",
                    price_match.group(1)
                )
            )

            if price <= 0 or price > 6000:
                continue

            # =========================
            # 3 КОМНАТЫ
            # =========================

            room_templates = [
                "3х кімнатну",
                "3-х кімнатну",
                "3 кімнатну",
                "3-комнатная",
                "3 комнатная",
                "3-х комнатная",
                "3х комнатная",
                "3-комн",
                "3 комн",
                "3-к.",
                "3-к",
                "3 к/к",
                "3-к/к"
            ]

            room_ok = any(
                template in full_text
                for template in room_templates
            )

            if not room_ok:
                continue

            # =========================
            # ИСКЛЮЧАЕМ ПОСУТОЧНО
            # =========================

            daily_words = [
                "посуная",
                "тестирование",
                "за сутки",
                "за ночь",
                "на ночь",
                "посуарный",
                "посуточное",
                "посуточно",
                "доба",
                "добово"
            ]

            if any(
                word in full_text
                for word in daily_words
            ):
                continue

            # =========================
            # ССЫЛКА
            # =========================

            href = title_tag.get(
                "href",
                ""
            )

            link = (
                f"https://makler.ua{href}"
                if href.startswith("/")
                else href
            )

            if not link:
                continue

            # =========================
            # ПРОВЕРКА КЭША
            # =========================

            if link in sent_makler_ads:
                continue

            sent_makler_ads.add(link)

            card = (
                f"🏠 {title}\n"
                f"💵 {price} грн\n"
                f"📄 {description}\n"
                f"🔗 [Открыть на Makler]({link})"
            )

            results.append(card)

        # =========================
        # ОТПРАВКА В TELEGRAM
        # =========================

        if results:

            message = (
                "🏠 НОВЫЕ ОБЪЯВЛЕНИЯ НА MAKLER:\n\n"
                + "\n\n---\n\n".join(results)
            )

            if send_telegram_message(message):

                save_cache(
                    MAKLER_CACHE,
                    sent_makler_ads
                )

        else:

            print(
                "Новых подходящих объявлений "
                "на Makler пока нет."
            )

    except Exception as e:

        print(
            f"Ошибка в модуле Makler: {e}"
        )
        # =========================
# OLX
# =========================

def check_olx():

    global sent_olx_ads

    try:

        if not OLX_RSS_URL:
            print(
                "OLX_RSS_URL не указан."
            )
            return

        response = requests.get(
            OLX_RSS_URL,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:

            print(
                f"Google шлюз вернул ошибку, "
                f"статус: {response.status_code}"
            )

            return

        soup = BeautifulSoup(
            response.content,
            "lxml-xml"
        )

        items = soup.find_all("item")

        results_olx = []

        print(
            f"Лента OLX успешно получена через шлюз Google! "
            f"Найдено объектов: {len(items)}"
        )

        for item in reversed(items):

            title_tag = item.find("title")
            link_tag = item.find("link")
            description_tag = item.find("description")

            title = (
                title_tag.get_text(
                    " ",
                    strip=True
                )
                if title_tag
                else ""
            )

            link = (
                link_tag.get_text(
                    " ",
                    strip=True
                )
                if link_tag
                else ""
            )

            description = (
                description_tag.get_text(
                    " ",
                    strip=True
                )
                if description_tag
                else ""
            )

            if not link:
                continue

            clean_link = link.split("#")[0]

            full_text = (
                title + " " + description
            ).lower()

            # =========================
            # ИСКЛЮЧАЕМ НЕНУЖНОЕ
            # =========================

            stop_words = [
                "посуточно",
                "доба",
                "добово",
                "сниму",
                "шукаю",
                "ищу квартиру",
                "шукаю квартиру"
            ]

            if any(
                word in full_text
                for word in stop_words
            ):
                continue

            # =========================
            # 3 КОМНАТЫ
            # =========================

            room_templates = [
                "3-к",
                "3 к",
                "3к",
                "3-комн",
                "3 комн",
                "трикімн",
                "трехкомн",
                "трёхкомн",
                "3-х комн",
                "3х комн",
                "3-х кімн",
                "3х кімн",
                "3-кімн",
                "3 кімн",
                "2-3"
            ]

            room_ok = any(
                template in full_text
                for template in room_templates
            )

            if not room_ok:
                continue

            # =========================
            # ПРОВЕРКА КЭША
            # =========================

            if clean_link in sent_olx_ads:
                continue

            sent_olx_ads.add(clean_link)

            # =========================
            # ЦЕНА
            # =========================

            price_search = re.search(
                r"(\d[\d\s]*)\s*(грн|uah)",
                title,
                re.IGNORECASE
            )

            if price_search:

                price_value = int(
                    re.sub(
                        r"\D",
                        "",
                        price_search.group(1)
                    )
                )

                if price_value <= 0 or price_value > 6000:
                    continue

                price_str = (
                    f"{price_value} грн"
                )

            else:

                price_str = (
                    "Цена указана на сайте"
                )

            # =========================
            # КАРТОЧКА
            # =========================

            card = (
                f"🏠 {title}\n"
                f"💵 {price_str}\n"
                f"🔗 [Открыть на OLX]({clean_link})"
            )

            results_olx.append(card)

        # =========================
        # ОТПРАВКА
        # =========================

        if results_olx:

            message = (
                "🏠 НОВЫЕ ОБЪЯВЛЕНИЯ НА OLX:\n\n"
                + "\n\n---\n\n".join(results_olx)
            )

            if send_telegram_message(message):

                save_cache(
                    OLX_CACHE,
                    sent_olx_ads
                )

        else:

            print(
                "Новых подходящих объявлений "
                "на OLX пока нет."
            )

    except Exception as e:

        print(
            f"Ошибка в модуле OLX: {e}"
        )
        # =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":

    print(
        "Запуск плановой проверки сайтов..."
    )
    check_makler() 
    check_olx() 
    # Проверяем рабочее время
    

    # =========================
    # ТЕСТ TELEGRAM
    # =========================

    print(
        "Проверка завершена. "
        "Запуск принудительного теста связи..."
    )

    send_telegram_message(
        "🤖 Проверка связи успешна!\n\n"
        "Бот полностью настроен, подключен к GitHub "
        "и вашему шлюзу Google.\n\n"
        "Я буду проверять OLX и Makler каждые 2 часа "
        "и присылать сюда новые 3-к квартиры "
        "до 6000 грн."
    )

    print(
        "Тестовое сообщение отправлено. "
        "Скрипт успешно завершен."
    )
    
