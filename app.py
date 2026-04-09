import os
from urllib.parse import unquote
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


def parse_amo_form(raw_data):
    """Парсит URL-encoded данные от amoCRM."""
    params = {}
    for pair in raw_data.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[unquote(key)] = unquote(value).replace("+", " ")
    return params


@app.route("/", methods=["GET"])
def index():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True)
    params = parse_amo_form(raw)

    i = 0
    while True:
        name_key = f"leads[add][{i}][name]"
        if name_key not in params:
            break

        name = params.get(f"leads[add][{i}][name]", "—")
        price = params.get(f"leads[add][{i}][price]", "0")

        # Собираем кастомные поля
        custom_fields = {}
        j = 0
        while True:
            cf_name_key = f"leads[add][{i}][custom_fields][{j}][name]"
            if cf_name_key not in params:
                break
            cf_name = params[cf_name_key]
            cf_value = params.get(
                f"leads[add][{i}][custom_fields][{j}][values][0][value]", "—"
            )
            custom_fields[cf_name] = cf_value
            j += 1

        # Формируем сообщение
        lines = [
            "<b>Новая заявка!</b>",
            "",
            f"<b>Название:</b> {name}",
        ]

        if price and price != "0":
            lines.append(f"<b>Бюджет:</b> {price} руб.")

        # Добавляем кастомные поля (кроме служебных)
        skip_fields = {"_ym_uid", "_ym_counter"}
        for cf_name, cf_value in custom_fields.items():
            if cf_name not in skip_fields and cf_value:
                lines.append(f"<b>{cf_name}:</b> {cf_value}")

        send_telegram("\n".join(lines))
        i += 1

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
