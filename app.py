import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def send_telegram(text):
    """Отправляет сообщение в Telegram."""
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
    # amoCRM отправляет данные как form-data, не JSON
    form = request.form

    # Ищем данные о новых сделках в form-data
    # amoCRM шлёт ключи вида: leads[add][0][name], leads[add][0][price]
    i = 0
    while True:
        name_key = f"leads[add][{i}][name]"
        if name_key not in form:
            break

        name = form.get(f"leads[add][{i}][name]", "Без названия")
        price = form.get(f"leads[add][{i}][price]", "0")

        text = (
            f"<b>Новая сделка!</b>\n\n"
            f"<b>Название:</b> {name}\n"
            f"<b>Сумма:</b> {price} руб."
        )

        send_telegram(text)
        i += 1

    # Если ничего не нашли в form-data, пробуем JSON (на всякий случай)
    if i == 0:
        data = request.json or {}
        leads = data.get("leads", {})
        for lead in leads.get("add", []):
            name = lead.get("name", "Без названия")
            price = lead.get("price", "0")

            text = (
                f"<b>Новая сделка!</b>\n\n"
                f"<b>Название:</b> {name}\n"
                f"<b>Сумма:</b> {price} руб."
            )

            send_telegram(text)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
