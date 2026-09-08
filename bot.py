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


# Правильная страница Makler:
# Николаев, аренда квартир
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


# СЮДА ДОЛЖНА БЫТЬ ВСТАВЛЕНА
# НАСТОЯЩАЯ ССЫЛКА ТВОЕГО GOOGLE APPS SCRIPT
OLX_RSS_URL = "ВСТАВЬ_ССЫЛКУ_ОЛХ_ШЛЮЗА"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


MAKLER_CACHE = "makler_cache.txt"
OLX_CACHE = "olx_cache.txt"


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

    # Работаем круглогодично с 08:00 до 18:00
    if 8 <= now.hour < 18:
        return True

    print(
        "Сейчас вне рабочего времени "
        "08:00-18:00."
    )

    return False


# =========================
# КЭШ
# =========================

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

        print(
            "Makler HTTP:",
            response.status_code
        )

        print(
            "Размер страницы:",
            len(response.text)
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        articles = soup.find_all(
            "article",
            id=re.compile(r"^tr_an-")
        )

        print(
            "Найдено article:",
            len(articles)
        )

        results = []

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

            # -------------------------
            # ЦЕНА
            # -------------------------

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

            # -------------------------
            # 3 КОМНАТЫ
            # -------------------------

            room_ok = False

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

            for template in room_templates:
                if template in full_text:
                    room_ok = True
                    break

            if not room_ok:
                continue

            # -------------------------
            # ИСКЛЮЧАЕМ ПОСУТОЧНО
            # -------------------------

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
                for word in stop_words
           (sad)
                continue
 
            # -------------------------
            # ССЫЛКА
            # -------------------------

            href = title_tag.get(
                "href",
                ""
            )

            if href.startswith("/"):
                link = (
                    f"https://makler.ua{href}"
                )
            else:
                link = href

            if not link:
                continue

            # -------------------------
            # НОВОЕ ОБЪЯВЛЕНИЕ
            # -------------------------

            if link in sent_makler_ads:
                continue

            sent_makler_ads.add(link)

            print(
                "ОБЪЯВЛЕНИЕ:",
                title
            )

            print(
                "ЦЕНА:",
                price,
                "UAH"
            )

            print("---")

            card = (
                f"🏠 {title}\n"
                f"💵 {price} грн\n"
                f"📄 {description}\n"
                f"🔗 [Открыть на Makler]({link})"
            )

            results.append(card)

        print(
            "Подходящих объявлений:",
            len(results)
        )

        if results:

            message = (
                "🏠 НИКОЛАЕВ АРЕНДА\n\n"
                "Найдены подходящие объявления:\n\n"
                + "\n\n---\n\n".join(results)
            )

            if send_telegram_message(message):
                save_cache(
                    MAKLER_CACHE,
                    sent_makler_ads
                )

        else:
            print(
                "Новых объявлений "
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
        # Проверяем, вставлена ли ссылка шлюза
        if not OLX_RSS_URL.startswith("http"):
            print(
                "OLX_RSS_URL не настроен."
            )
            print(
                "Вставьте настоящую ссылку "
                "Google Apps Script."
            )
            return

        response = requests.get(
            OLX_RSS_URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            "OLX шлюз HTTP:",
            response.status_code
        )

        if response.status_code != 200:
            print(
                "Google шлюз вернул ошибку, "
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
            "Лента OLX успешно получена "
            "через шлюз Google!"
        )

        print(
            "Найдено объектов:",
            len(items)
        )

        for item in reversed(items):

            title_tag = item.find(
                "title"
            )

            link_tag = item.find(
                "link"
            )

            description_tag = item.find(
                "description"
            )

            title = (
                title_tag.text.strip()
                if title_tag
                else ""
            )

            link = (
                link_tag.text.strip()
                if link_tag
                else ""
            )

            description = (
                description_tag.text.strip()
                if description_tag
                else ""
            )

            if not link:
                continue

            clean_link = link.split("#")[0]

            full_text = (
                title + " " + description
            ).lower()

            # -------------------------
            # ИСКЛЮЧАЕМ ПОСУТОЧНЫЕ
            # -------------------------

            stop_words = [
                "посуточно",
                "доба",
                "добово",
                "за сутки",
                "за ночь",
                "на ночь",
                "сниму",
                "шукаю",
                "ищу квартиру",
                "шукаю квартиру"
            ]

            if any(
                word in full_text
                for word in stop_words
            (sad)
                continue

            # -------------------------
            # ИЩЕМ 3 КОМНАТЫ
            # -------------------------

            room_ok = False

            room_templates = [
                "3-к",
                "3 к",
                "3к",
                "3-комн",
                "3 комн",
                "трикімн",
                "три кімн",
                "трехкомн",
                "трёхкомн",
                "3-х комн",
                "3х комн",
                "3-х кімн",
                "3х кімн",
                "3-кімн",
                "3 кімн"
            ]

            for template in room_templates:

                if template in full_text:
                    room_ok = True
                    break

            if not room_ok:
                continue

            # -------------------------
            # НЕ ОТПРАВЛЯЕМ ПОВТОРНО
            # -------------------------

            if clean_link in sent_olx_ads:
                continue

            sent_olx_ads.add(
                clean_link
            )

            # -------------------------
            # ЦЕНА
            # -------------------------

            price_search = re.search(
                r"(\d[\d\s])\s(грн|uah)",
                title,
                re.IGNORECASE
            )

            if price_search:

                price_str = (
                    f"{price_search.group(1).strip()} "
                    f"грн"
                )

            else:

                price_str = (
                    "Цена указана на сайте"
                )

            print(
                "OLX ОБЪЯВЛЕНИЕ:",
                title
            )

            print(
                "OLX ЦЕНА:",
                price_str
            )

            print("---")

            card = (
                f"🏠 {title}\n"
                f"💵 {price_str}\n"
                f"🔗 [Открыть на OLX]({clean_link})"
            )

            results_olx.append(
                card
            )

        print(
            "Подходящих объявлений OLX:",
            len(results_olx)
        )

        if results_olx:

            message = (
                "🏠 НОВЫЕ ОБЪЯВЛЕНИЯ НА OLX:\n\n"
                + "\n\n---\n\n".join(
                    results_olx
                )
            )

            if send_telegram_message(
                message
            (sad)

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
         f"🔗 [Открыть на OLX]({clean_link})"
            )

            results_olx.append(card)

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


if name == "main":
    print(
        "Запуск плановой проверки сайтов..."
    )

    if is_work_time():
        check_makler()
        check_olx()
    else:
        print(
            "Проверка сайтов не выполняется: "
            "сейчас вне времени 08:00-18:00."
        )

    print(
        "Проверка завершена. "
        "Запуск принудительного теста связи..."
    )

    send_telegram_message(
        "🤖 Проверка связи успешна!\n\n"
        "Бот полностью настроен и работает. "
        "Проверка OLX и Makler выполняется "
        "каждые 2 часа с 08:00 до 18:00 "
        "по украинскому времени. "
        "Ищу новые 3-комнатные квартиры "
        "до 6000 грн."
    )

    print(
        "Тестовое сообщение отправлено. "
        "Скрипт успешно завершен."
    )
