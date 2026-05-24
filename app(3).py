import json
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app, origins="*", allow_headers=["Content-Type"], methods=["GET","POST","DELETE","OPTIONS"])

DATA_FILE = "school_data.json"
TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "school26")

# ==================== БД ====================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "homework": {}, "schedule": {}, "announcements": {}, "files": {}, "stars": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
    for key in ["users", "homework", "schedule", "announcements", "files", "stars"]:
        if key not in d:
            d[key] = {}
    return d

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== МІНІ АПП ====================
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ==================== РЕЄСТРАЦІЯ / ЛОГІН ====================
@app.route('/api/register', methods=['POST'])
def register():
    body = request.json
    user_id = str(body.get('user_id', ''))
    if not user_id:
        return jsonify({"ok": False, "error": "no user_id"}), 400

    data = load_data()
    role = body.get('role', 'student')

    if role == 'teacher':
        if body.get('password') != TEACHER_PASSWORD:
            return jsonify({"ok": False, "error": "wrong_password"}), 403

    data["users"][user_id] = {
        "name": body.get('name', ''),
        "surname": body.get('surname', ''),
        "class": body.get('class', '').upper(),
        "role": role,
        "tg_username": body.get('tg_username', '')
    }
    save_data(data)
    return jsonify({"ok": True, "user": data["users"][user_id]})

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    data = load_data()
    user = data["users"].get(str(user_id))
    if not user:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "user": user})

# ==================== ДЗ ====================
@app.route('/api/homework/<cls>', methods=['GET'])
def get_homework(cls):
    data = load_data()
    hw = data["homework"].get(cls.upper(), [])
    return jsonify({"ok": True, "homework": hw})

@app.route('/api/homework', methods=['POST'])
def add_homework():
    body = request.json
    user_id = str(body.get('user_id', ''))
    data = load_data()
    user = data["users"].get(user_id, {})
    if user.get('role') != 'teacher':
        return jsonify({"ok": False, "error": "not_teacher"}), 403

    cls = body.get('class', '').upper()
    if cls not in data["homework"]:
        data["homework"][cls] = []

    entry = {
        "subject": body.get('subject', ''),
        "text": body.get('text', ''),
        "day": body.get('day', ''),
        "date": datetime.now().strftime("%d.%m.%Y"),
        "teacher": f"{user.get('name','')} {user.get('surname','')}".strip()
    }
    data["homework"][cls].append(entry)
    save_data(data)
    return jsonify({"ok": True, "entry": entry})

@app.route('/api/homework/<cls>/<int:idx>', methods=['DELETE'])
def delete_homework(cls, idx):
    user_id = str(request.args.get('user_id', ''))
    data = load_data()
    user = data["users"].get(user_id, {})
    if user.get('role') != 'teacher':
        return jsonify({"ok": False, "error": "not_teacher"}), 403

    cls = cls.upper()
    if cls in data["homework"] and idx < len(data["homework"][cls]):
        data["homework"][cls].pop(idx)
        save_data(data)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "not_found"}), 404

# ==================== РОЗКЛАД ====================
@app.route('/api/schedule/<cls>', methods=['GET'])
def get_schedule(cls):
    data = load_data()
    schedule = data["schedule"].get(cls.upper(), {})
    return jsonify({"ok": True, "schedule": schedule})

@app.route('/api/schedule', methods=['POST'])
def set_schedule():
    body = request.json
    user_id = str(body.get('user_id', ''))
    data = load_data()
    user = data["users"].get(user_id, {})
    if user.get('role') != 'teacher':
        return jsonify({"ok": False, "error": "not_teacher"}), 403

    cls = body.get('class', '').upper()
    day = body.get('day', '')
    lessons = body.get('lessons', [])

    if cls not in data["schedule"]:
        data["schedule"][cls] = {}
    data["schedule"][cls][day] = lessons
    save_data(data)
    return jsonify({"ok": True})

# ==================== ОГОЛОШЕННЯ ====================
@app.route('/api/announcements/<cls>', methods=['GET'])
def get_announcements(cls):
    data = load_data()
    items = data["announcements"].get(cls.upper(), [])
    all_items = data["announcements"].get("ВСІ", [])
    combined = items + all_items
    combined.sort(key=lambda x: x.get('date', ''), reverse=True)
    return jsonify({"ok": True, "announcements": combined[-20:]})

@app.route('/api/announcements', methods=['POST'])
def add_announcement():
    body = request.json
    user_id = str(body.get('user_id', ''))
    data = load_data()
    user = data["users"].get(user_id, {})
    if user.get('role') != 'teacher':
        return jsonify({"ok": False, "error": "not_teacher"}), 403

    cls = body.get('class', 'ВСІ').upper()
    if cls not in data["announcements"]:
        data["announcements"][cls] = []

    entry = {
        "title": body.get('title', 'Оголошення'),
        "text": body.get('text', ''),
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "teacher": f"{user.get('name','')} {user.get('surname','')}".strip()
    }
    data["announcements"][cls].append(entry)
    save_data(data)
    return jsonify({"ok": True, "entry": entry})

# ==================== МАТЕРІАЛИ ====================
@app.route('/api/files/<cls>', methods=['GET'])
def get_files(cls):
    data = load_data()
    files = data["files"].get(cls.upper(), [])
    return jsonify({"ok": True, "files": files})

@app.route('/api/files', methods=['POST'])
def add_file():
    body = request.json
    user_id = str(body.get('user_id', ''))
    data = load_data()
    user = data["users"].get(user_id, {})
    if user.get('role') != 'teacher':
        return jsonify({"ok": False, "error": "not_teacher"}), 403

    cls = body.get('class', '').upper()
    if cls not in data["files"]:
        data["files"][cls] = []

    entry = {
        "subject": body.get('subject', ''),
        "name": body.get('name', ''),
        "link": body.get('link', ''),
        "date": datetime.now().strftime("%d.%m.%Y")
    }
    data["files"][cls].append(entry)
    save_data(data)
    return jsonify({"ok": True, "entry": entry})

# ==================== ЗІРКИ ====================
@app.route('/api/stars/<cls>', methods=['GET'])
def get_stars(cls):
    data = load_data()
    stars = data["stars"].get(cls.upper(), [])
    return jsonify({"ok": True, "stars": stars})

@app.route('/api/stars', methods=['POST'])
def add_stars():
    body = request.json
    user_id = str(body.get('user_id', ''))
    data = load_data()
    user = data["users"].get(user_id, {})
    if user.get('role') != 'teacher':
        return jsonify({"ok": False, "error": "not_teacher"}), 403

    cls = body.get('class', '').upper()
    if cls not in data["stars"]:
        data["stars"][cls] = []

    entry = {
        "name": body.get('name', ''),
        "stars": int(body.get('stars', 1)),
        "reason": body.get('reason', ''),
        "date": datetime.now().strftime("%d.%m.%Y")
    }
    data["stars"][cls].append(entry)
    save_data(data)
    return jsonify({"ok": True, "entry": entry})

# ==================== СТАТИСТИКА ====================
@app.route('/api/stats/<cls>', methods=['GET'])
def get_stats(cls):
    data = load_data()
    cls = cls.upper()
    hw_count = len(data["homework"].get(cls, []))
    ann_count = len(data["announcements"].get(cls, [])) + len(data["announcements"].get("ВСІ", []))
    stars_total = sum(s["stars"] for s in data["stars"].get(cls, []))
    return jsonify({"ok": True, "hw": hw_count, "announcements": ann_count, "stars": stars_total})

# ==================== NZ.UA ЛОГІН (ДЕМО) ====================
@app.route('/api/nz_login', methods=['POST'])
def nz_login():
    body = request.json
    login = body.get('login', '').strip()
    password = body.get('password', '').strip()

    if not login or not password:
        return jsonify({"ok": False, "error": "empty"}), 400

    # ДЕМО режим — приймаємо будь-який логін/пароль
    # TODO: замінити на реальний Playwright парсер
    # Витягуємо ім'я з логіну
    name_parts = login.replace('_', ' ').replace('.', ' ').split()
    name = name_parts[0].capitalize() if name_parts else login

    return jsonify({
        "ok": True,
        "user": {
            "name": name,
            "surname": "",
            "class": "",
            "nz_login": login
        },
        "demo": True
    })

# ==================== ПІДТРИМКА ====================
import httpx

SUPPORT_BOT_TOKEN = os.environ.get("SUPPORT_BOT_TOKEN", "")
SUPPORT_CHAT_ID = os.environ.get("SUPPORT_CHAT_ID", "")  # твій особистий chat_id

@app.route('/api/support', methods=['POST'])
def send_support():
    body = request.json
    user_id = str(body.get('user_id', ''))
    message = body.get('message', '').strip()
    if not message:
        return jsonify({"ok": False, "error": "empty"}), 400

    data = load_data()
    user = data["users"].get(user_id, {})
    name = f"{user.get('name','')} {user.get('surname','')}".strip() or "Невідомий"
    cls = user.get('class', '—')

    tg_username = user.get('tg_username', '')
    user_link = f"@{tg_username}" if tg_username else f"ID: {user_id}"

    text = (
        f"📨 *Нове звернення до підтримки*\n\n"
        f"👤 *{name}*\n"
        f"🏫 Клас: {cls}\n"
        f"🔗 {user_link}\n\n"
        f"💬 *Повідомлення:*\n{message}"
    )

    if SUPPORT_BOT_TOKEN and SUPPORT_CHAT_ID:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{SUPPORT_BOT_TOKEN}/sendMessage",
                json={"chat_id": SUPPORT_CHAT_ID, "text": text, "parse_mode": "Markdown"},
                timeout=5
            )
        except Exception as e:
            print(f"Support send error: {e}")

    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
