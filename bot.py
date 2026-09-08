name: Telegram Test

on:
  workflow_dispatch:
  schedule:
    - cron: "0 */2 * * *"

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Install Chromium
        run: |
          python -m playwright install --with-deps chromium

      - name: Run Telegram bot
        run: python bot.py
        env:
          BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
          CHAT_ID: ${{ secrets.CHAT_ID }}
# ============================================================
# ПАРСИНГ OLX
# ============================================================

def parse_olx(html):
    if not html:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    results = []

    # Ищем карточки объявлений
    cards = soup.find_all(
        "div",
        attrs={
            "data-cy": "l-card"
        }
    )

    print(
        "OLX: найдено карточек:",
        len(cards)
    )

    for card in cards:

        try:
            # ------------------------------------------------
            # НАЗВАНИЕ
            # ------------------------------------------------

            title_tag = card.find(
                "h4"
            )

            if not title_tag:
                title_tag = card.find(
                    "h6"
                )

            title = (
                title_tag.get_text(
                    " ",
                    strip=True
                )
                if title_tag
                else ""
            )

            if not title:
                continue

            # ------------------------------------------------
            # ССЫЛКА
            # ------------------------------------------------

            link_tag = card.find(
                "a",
                href=True
            )

            if not link_tag:
                continue

            href = link_tag.get(
                "href",
                ""
            )

            if not href:
                continue

            if href.startswith("/"):
                href = (
                    "https://www.olx.ua"
                    + href
                )

            # ------------------------------------------------
            # ВЕСЬ ТЕКСТ КАРТОЧКИ
            # ------------------------------------------------

            card_text = card.get_text(
                " ",
                strip=True
            )

            full_text = (
                title
                + " "
                + card_text
            ).lower()

            # ------------------------------------------------
            # ЦЕНА
            # ------------------------------------------------

            price = extract_price(
                card_text
            )

            if price is None:
                continue

            # ------------------------------------------------
            # 3 КОМНАТЫ
            # ------------------------------------------------

            if not is_three_room(full_text):
                continue

            # ------------------------------------------------
            # НЕ ПОСУТОЧНО
            # ------------------------------------------------

            if is_daily_rent(full_text):
                continue

            # ------------------------------------------------
            # СОХРАНЯЕМ
            # ------------------------------------------------

            results.append(
                {
                    "title": title,
                    "price": price,
                    "description": card_text,
                    "url": href,
                }
            )

        except Exception as e:
            print(
                "Ошибка обработки карточки OLX:",
                e
            )

    return results


# ============================================================
# ФОРМИРОВАНИЕ СООБЩЕНИЯ OLX
# ============================================================

def format_olx_message(items):
    if not items:
        return ""

    lines = [
        "🏠 НОВЫЕ ОБЪЯВЛЕНИЯ НА OLX:"
    ]

    for item in items:

        lines.append("")
        lines.append(
            "🏠 " + item["title"]
        )

        lines.append(
            "💵 "
            + str(item["price"])
            + " грн"
        )

        description = item.get(
            "description",
            ""
        )

        # Чтобы Telegram не получал
        # огромный текст карточки
        if len(description) > 300:
            description = (
                description[:300]
                + "..."
            )

        if description:
            lines.append(
                "📄 " + description
            )

        lines.append(
            "🔗 Открыть на OLX"
        )

        lines.append(
            item["url"]
        )

        lines.append(
            "---"
        )

    return "\n".join(lines)


# ============================================================
# ПРОВЕРКА OLX
# ============================================================

def check_olx():
    print("Проверка OLX...")

    html = get_olx_feed()

    if not html:
        print(
            "OLX: данные не получены."
        )
        return

    items = parse_olx(
        html
    )

    print(
        "OLX: найдено подходящих:",
        len(items)
    )

    if not items:
        print(
            "Новых подходящих объявлений "
            "на OLX пока нет."
        )
        return

    message = format_olx_message(
        items
    )

    if message:
        send_telegram(
            message
        )


# ============================================================
# ЗАВЕРШЕНИЕ ПРОВЕРКИ
# ============================================================

def run_checks():
    print(
        "Запуск плановой проверки сайтов..."
    )

    if not is_working_time():
        print(
            "Проверка объявлений пропущена."
        )
        return

    check_makler()
    check_olx()

    print(
        "Проверка завершена."
    )
# ============================================================
# ТЕСТ СВЯЗИ С TELEGRAM
# ============================================================

def telegram_test():
    print(
        "Запуск принудительного теста связи..."
    )

    message = (
        "🤖 Проверка связи успешна!\n\n"
        "Бот подключен к Telegram и GitHub.\n\n"
        "Я буду проверять OLX и Makler "
        "каждые 2 часа и искать новые "
        "3-к квартиры до 6000 грн."
    )

    if send_telegram(message):
        print(
            "Тестовое сообщение отправлено."
        )
    else:
        print(
            "Не удалось отправить "
            "тестовое сообщение."
        )


# ============================================================
# ЗАЩИТА ОТ ПОВТОРНЫХ ЗАПУСКОВ
# ============================================================

def main():
    print(
        "Запуск плановой проверки сайтов..."
    )

    try:
        run_checks()

    except Exception as e:
        print(
            "Критическая ошибка:",
            e
        )

    print(
        "Проверка завершена."
    )

    # Тест Telegram можно оставить включённым,
    # чтобы после каждого запуска GitHub Actions
    # было видно, что бот действительно работает.
    telegram_test()

    print(
        "Скрипт успешно завершен."
    )
# ============================================================
# ЗАПУСК ПРОГРАММЫ
# ============================================================

if __name__ == "__main__":
    main()
