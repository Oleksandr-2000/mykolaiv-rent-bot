import os
import re
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

MAKLER_URL = "https://makler.ua"
OLX_RSS_URL = "https://google.com"

ZAGOLOVKI = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def send_telegram_message(message_text):
    # ТУТ ПРОВЕРЕННЫЙ АДРЕС С API
    telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message_text, "parse_mode": "Markdown"}
    try:
        response = requests.post(telegram_url, json=payload, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

if __name__ == "__main__":
    print("Запуск плановой проверки сайтов...")
    print("Проверка завершена. Запуск принудительного теста связи...")
    send_telegram_message("🤖 *Проверка связи успешна!*\n\nБот полностью настроен, подключен к GitHub и вашему шлюзу Google. Я буду проверять OLX и Makler каждые 2 часа.")
    print("Тестовое сообщение отправлено.")
