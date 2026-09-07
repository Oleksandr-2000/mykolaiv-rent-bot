print("ТЕСТ НОВОГО BOT.PY")

for i in range(3):
    print("Цикл:", i)

print("Цикл завершён")

import os

print("BOT_TOKEN:", "есть" if os.environ.get("BOT_TOKEN") else "НЕТ")
print("CHAT_ID:", "есть" if os.environ.get("CHAT_ID") else "НЕТ")

print("ФАЙЛ ЗАПУСКАЕТСЯ")
