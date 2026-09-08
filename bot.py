import os
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send_telegram_message(message_text):
    telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown"
    }
    try:
        response_tg = requests.post(telegram_url, json=payload, timeout=30)
        response_tg.raise_for_status()
        print("Тестовое сообщение успешно отправлено в Telegram!")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

if __name__ == "__main__":
    print("ЗАПУСК ПРИНУДИТЕЛЬНОГО ТЕСТА...")
    test_link = "https://olx.ua"
    card = f"🧪 *ПРИНУДИТЕЛЬНЫЙ ТЕСТ БОТА*\n\n🏠 *Оренда квартири від власника для родини*\n💵 6000 грн\n🔗 [Открыть объявление на OLX]({test_link})"
    send_telegram_message(card)
