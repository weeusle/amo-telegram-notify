import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    })


@app.route("/", methods=["GET"])
def index():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    # Логируем всё что пришло для отладки
    raw_data = request.get_data(as_text=True)
    print(f"=== WEBHOOK RECEIVED ===")
    print(f"Content-Type: {request.content_type}")
    print(f"Raw data: {raw_data[:2000]}")
    print(f"========================")

    found = False

    # Способ 1: form-data (основной формат amoCRM)
    if request.form:
        form = request.form
        print(f"Form keys: {list(form.keys())[:20]}")

        i = 0
        while True:
            name_key = f"leads[add][{i}][name]"
            if name_key not in form:
                break
            name = form.get(f"leads[add][{i}][name]", "Без названия")
            price = form.get(f"leads[add][{i}][price]", "0")
            send_telegram(
                f"<b>Новая сделка!</b>\n\n"
                f"<b>Название:</b> {name}\n"
                f"<b>Сумма:</b> {price} руб."
            )
            found = True
            i += 1

    # Способ 2: JSON
    if not found:
        try:
            data = request.json or {}
            leads = data.get("leads", {})
            for lead in leads.get("add", []):
                name = lead.get("name", "Без названия")
                price = lead.get("price", "0")
                send_telegram(
                    f"<b>Новая сделка!</b>\n\n"
                    f"<b>Название:</b> {name}\n"
                    f"<b>Сумма:</b> {price} руб."
                )
                found = True
        except Exception:
            pass

    # Если ничего не распознали — отправляем сырые данные для отладки
    if not found:
        send_telegram(f"<b>Webhook получен, но формат не распознан.</b>\n\n{raw_data[:500]}")

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
