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
    data = request.json or {}

    # Обработка сделок
    leads = data.get("leads", {})

    # Новая сделка или смена статуса
    for action in ["add", "status", "update"]:
        for lead in leads.get(action, []):
            name = lead.get("name", "Без названия")
            price = lead.get("price", 0)
            status_id = lead.get("status_id", "")
            pipeline_id = lead.get("pipeline_id", "")
            responsible = lead.get("responsible_user_id", "")

            if action == "add":
                emoji = "NEW"
                action_text = "Новая сделка"
            elif action == "status":
                emoji = "UPD"
                action_text = "Смена статуса"
            else:
                emoji = "EDIT"
                action_text = "Изменение"

            text = (
                f"<b>[{emoji}] {action_text}</b>\n\n"
                f"<b>Сделка:</b> {name}\n"
                f"<b>Сумма:</b> {price} руб."
            )

            send_telegram(text)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
