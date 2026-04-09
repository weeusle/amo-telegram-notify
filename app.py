import os
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
AMO_TOKEN = os.environ.get("AMO_TOKEN")
AMO_DOMAIN = os.environ.get("AMO_DOMAIN")

MSK = timezone(timedelta(hours=3))


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    })


def get_contact_telegram(lead_id):
    """Получает Telegram контакта, привязанного к сделке."""
    try:
        headers = {"Authorization": f"Bearer {AMO_TOKEN}"}
        base = f"https://{AMO_DOMAIN}.amocrm.ru/api/v4"

        # Получаем контакты сделки
        resp = requests.get(
            f"{base}/leads/{lead_id}",
            headers=headers,
            params={"with": "contacts"},
        )
        data = resp.json()

        contacts = (
            data.get("_embedded", {}).get("contacts", [])
        )
        if not contacts:
            return None

        contact_id = contacts[0].get("id")
        if not contact_id:
            return None

        # Получаем данные контакта
        resp2 = requests.get(
            f"{base}/contacts/{contact_id}",
            headers=headers,
        )
        contact = resp2.json()

        # Ищем поле Telegram среди кастомных полей
        for field in contact.get("custom_fields_values", []):
            name = field.get("field_name", "").lower()
            if "telegram" in name:
                values = field.get("values", [])
                if values:
                    return values[0].get("value", "")

        return None
    except Exception as e:
        print(f"Error getting contact: {e}")
        return None


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

        lead_id = params.get(f"leads[add][{i}][id]", "")
        name = params.get(f"leads[add][{i}][name]", "—")
        price = params.get(f"leads[add][{i}][price]", "0")
        date_create = params.get(f"leads[add][{i}][date_create]", "")

        # Форматируем дату
        date_str = "—"
        if date_create:
            try:
                dt = datetime.fromtimestamp(int(date_create), tz=MSK)
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                date_str = date_create

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

        # Получаем Telegram контакта через API
        tg_contact = get_contact_telegram(lead_id) if lead_id else None

        # Формируем сообщение
        lines = [
            "<b>Новая заявка!</b>",
            "",
            f"<b>Дата:</b> {date_str}",
            f"<b>Название:</b> {name}",
        ]

        if price and price != "0":
            lines.append(f"<b>Бюджет:</b> {price} руб.")

        # Кастомные поля (кроме служебных)
        skip_fields = {"_ym_uid", "_ym_counter"}
        for cf_name, cf_value in custom_fields.items():
            if cf_name not in skip_fields and cf_value:
                lines.append(f"<b>{cf_name}:</b> {cf_value}")

        # Telegram контакта
        if tg_contact:
            lines.append(f"\n<b>Telegram:</b> {tg_contact}")

        send_telegram("\n".join(lines))
        i += 1

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
