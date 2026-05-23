import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ==================== НАЛАШТУВАННЯ ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")  # URL міні аппу на Railway
TEACHER_PASSWORD = "school26"
CREATOR_USERNAME = "@aquaee"
DATA_FILE = "school_data.json"

DAYS = ["mon", "tue", "wed", "thu", "fri"]
DAYS_UA = {"mon": "Пн", "tue": "Вт", "wed": "Ср", "thu": "Чт", "fri": "Пт"}
DAYS_FULL = {"mon": "Понеділок", "tue": "Вівторок", "wed": "Середа", "thu": "Четвер", "fri": "П'ятниця"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== СТАНИ ====================
(
    REGISTER_NAME, REGISTER_SURNAME, REGISTER_CLASS,
    CHOOSE_ROLE, TEACHER_PASSWORD_INPUT,
    ADD_HW_SUBJECT, ADD_HW_CLASS, ADD_HW_TEXT, ADD_HW_DAY,
    ADD_SCHEDULE_DAY, ADD_SCHEDULE_CLASS, ADD_SCHEDULE_TEXT,
    ADD_ANNOUNCE_CLASS, ADD_ANNOUNCE_TEXT,
    ADD_FILE_CLASS, ADD_FILE_SUBJECT, ADD_FILE_LINK,
    ADD_STARS_CLASS, ADD_STARS_NAME, ADD_STARS_COUNT, ADD_STARS_REASON,
) = range(21)

# ==================== БД ====================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "homework": {}, "schedule": {}, "announcements": {}, "files": {}, "stars": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
    for key in ["homework", "schedule", "announcements", "files", "stars"]:
        if key not in d:
            d[key] = {}
    return d

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== СТАРТ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id in data["users"]:
        # Вже зареєстрований — показуємо меню
        user = data["users"][user_id]
        if user.get("role") == "teacher":
            await show_teacher_menu(update, context)
        else:
            await show_student_menu(update, context)
        return ConversationHandler.END

    # Новий юзер — просимо зареєструватися через міні апп
    from telegram import WebAppInfo
    keyboard = []
    if WEBAPP_URL:
        keyboard.append([InlineKeyboardButton("📱 Зареєструватися", web_app=WebAppInfo(url=WEBAPP_URL))])

    await update.message.reply_text(
        "🏫 *Ласкаво просимо до Шкільного помічника!*\n\n"
        "📚 Домашні завдання\n"
        "📅 Розклад уроків\n"
        "📢 Оголошення\n"
        "📎 Матеріали до уроків\n"
        "🏆 Досягнення учнів\n\n"
        "Для початку — натисни кнопку нижче і зареєструйся через додаток 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ==================== МЕНЮ УЧНЯ ====================
async def show_student_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})

    from telegram import WebAppInfo
    keyboard = []
    if WEBAPP_URL:
        keyboard.append([InlineKeyboardButton("🚀 Відкрити додаток", web_app=WebAppInfo(url=WEBAPP_URL))])
    keyboard += [
        [InlineKeyboardButton("📚 Домашні завдання", callback_data="view_hw")],
        [InlineKeyboardButton("📅 Розклад", callback_data="view_schedule")],
        [InlineKeyboardButton("📢 Оголошення", callback_data="view_announce")],
        [InlineKeyboardButton("📎 Матеріали", callback_data="view_files")],
        [InlineKeyboardButton("🏆 Досягнення", callback_data="view_stars")],
        [InlineKeyboardButton("👤 Профіль", callback_data="my_profile"),
         InlineKeyboardButton("ℹ️ Про бота", callback_data="about")],
    ]
    text = (
        f"🏫 *Шкільний помічник*\n\n"
        f"Привіт, *{user.get('name', '')}*! 👋\n"
        f"Клас: *{user.get('class', '')}*\n\n"
        "Що хочеш зробити?"
    )
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== МЕНЮ ВЧИТЕЛЯ ====================
async def show_teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    keyboard = [
        [InlineKeyboardButton("📚 Додати ДЗ", callback_data="add_hw"),
         InlineKeyboardButton("📋 Всі ДЗ", callback_data="view_all_hw")],
        [InlineKeyboardButton("📅 Розклад", callback_data="manage_schedule")],
        [InlineKeyboardButton("📢 Оголошення", callback_data="add_announce")],
        [InlineKeyboardButton("📎 Додати матеріал", callback_data="add_file")],
        [InlineKeyboardButton("🏆 Видати зірку", callback_data="add_stars")],
        [InlineKeyboardButton("🗑️ Видалити ДЗ", callback_data="delete_hw")],
        [InlineKeyboardButton("👤 Профіль", callback_data="my_profile"),
         InlineKeyboardButton("ℹ️ Про бота", callback_data="about")],
    ]
    text = (
        f"🏫 *Панель вчителя*\n\n"
        f"Привіт, *{user.get('name', '')}* 👨‍🏫\n\n"
        "Що хочеш зробити?"
    )
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== ДОМАШНІ ЗАВДАННЯ ====================
async def view_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    student_class = user.get("class", "")
    hw_list = data["homework"].get(student_class, [])
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    if not hw_list:
        await query.edit_message_text(
            f"📚 *Домашні завдання — {student_class}*\n\n📭 Завдань немає.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        return
    text = f"📚 *Домашні завдання — клас {student_class}*\n\n"
    for i, hw in enumerate(hw_list, 1):
        day_str = f" ({DAYS_FULL.get(hw.get('day',''), '')})" if hw.get('day') else ""
        text += f"*{i}. {hw['subject']}*{day_str}\n📝 {hw['text']}\n📅 {hw['date']} | 👨‍🏫 {hw['teacher']}\n\n"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def add_hw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ *Додати ДЗ*\n\nВведи назву *предмету*:",
        parse_mode="Markdown"
    )
    return ADD_HW_SUBJECT

async def add_hw_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hw_subject"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Предмет: *{context.user_data['hw_subject']}*\n\nДля якого *класу*? _(9А, 10Б...)_:",
        parse_mode="Markdown"
    )
    return ADD_HW_CLASS

async def add_hw_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hw_class"] = update.message.text.strip().upper()
    keyboard = [[
        InlineKeyboardButton("Пн", callback_data="hwday_mon"),
        InlineKeyboardButton("Вт", callback_data="hwday_tue"),
        InlineKeyboardButton("Ср", callback_data="hwday_wed"),
        InlineKeyboardButton("Чт", callback_data="hwday_thu"),
        InlineKeyboardButton("Пт", callback_data="hwday_fri"),
    ]]
    await update.message.reply_text(
        f"✅ Клас: *{context.user_data['hw_class']}*\n\nНа який день завдання?",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return ADD_HW_DAY

async def add_hw_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["hw_day"] = query.data.replace("hwday_", "")
    day_name = DAYS_FULL.get(context.user_data["hw_day"], "")
    await query.edit_message_text(
        f"✅ День: *{day_name}*\n\nВведи *текст завдання*:",
        parse_mode="Markdown"
    )
    return ADD_HW_TEXT

async def add_hw_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    hw_class = context.user_data["hw_class"]
    if hw_class not in data["homework"]:
        data["homework"][hw_class] = []
    hw_entry = {
        "subject": context.user_data["hw_subject"],
        "text": update.message.text.strip(),
        "day": context.user_data.get("hw_day", ""),
        "date": datetime.now().strftime("%d.%m.%Y"),
        "teacher": f"{user.get('name', '')} {user.get('surname', '')}",
    }
    data["homework"][hw_class].append(hw_entry)
    save_data(data)

    # Надіслати сповіщення учням класу
    day_name = DAYS_FULL.get(hw_entry["day"], "")
    notif_text = (
        f"🔔 *Нове ДЗ для класу {hw_class}!*\n\n"
        f"📚 {hw_entry['subject']} ({day_name})\n"
        f"📝 {hw_entry['text']}"
    )
    count = 0
    for uid, u in data["users"].items():
        if u.get("class") == hw_class and u.get("role") == "student":
            try:
                await context.bot.send_message(chat_id=int(uid), text=notif_text, parse_mode="Markdown")
                count += 1
            except:
                pass

    await update.message.reply_text(
        f"✅ *ДЗ додано!*\n\n📚 {hw_entry['subject']} — {hw_class}\n📝 {hw_entry['text']}\n\n"
        f"🔔 Сповіщено учнів: {count}",
        parse_mode="Markdown"
    )
    await show_teacher_menu(update, context)
    return ConversationHandler.END

async def view_all_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    if not any(data["homework"].values()):
        await query.edit_message_text("📋 *Всі ДЗ*\n\n📭 Завдань немає.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return
    text = "📋 *Всі домашні завдання*\n\n"
    for cls, hw_list in data["homework"].items():
        if hw_list:
            text += f"🏫 *Клас {cls}:*\n"
            for hw in hw_list:
                text += f"  • {hw['subject']}: {hw['text'][:40]}{'...' if len(hw['text'])>40 else ''}\n"
            text += "\n"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def delete_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    keyboard = []
    for cls, hw_list in data["homework"].items():
        for i, hw in enumerate(hw_list):
            keyboard.append([InlineKeyboardButton(f"❌ {cls} | {hw['subject']} ({hw['date']})", callback_data=f"del_{cls}_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    text = "🗑️ *Оберіть завдання для видалення:*" if len(keyboard) > 1 else "🗑️ Немає завдань."
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_", 2)
    cls, idx = parts[1], int(parts[2])
    data = load_data()
    if cls in data["homework"] and idx < len(data["homework"][cls]):
        removed = data["homework"][cls].pop(idx)
        save_data(data)
        await query.edit_message_text(f"✅ ДЗ *{removed['subject']}* для *{cls}* видалено!", parse_mode="Markdown")
    await show_teacher_menu(update, context, edit=False)

# ==================== РОЗКЛАД ====================
async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    student_class = user.get("class", "")
    today_idx = datetime.now().weekday()
    current_day = DAYS[today_idx] if today_idx < 5 else "mon"
    context.user_data["schedule_class"] = student_class
    await show_schedule_day(query, context, student_class, current_day)

async def show_schedule_day(query, context, student_class, day):
    data = load_data()
    schedule = data["schedule"].get(student_class, {}).get(day, "")
    keyboard = [[
        InlineKeyboardButton("Пн", callback_data="sday_mon"),
        InlineKeyboardButton("Вт", callback_data="sday_tue"),
        InlineKeyboardButton("Ср", callback_data="sday_wed"),
        InlineKeyboardButton("Чт", callback_data="sday_thu"),
        InlineKeyboardButton("Пт", callback_data="sday_fri"),
    ], [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    day_name = DAYS_FULL.get(day, "")
    text = f"📅 *Розклад — {student_class} — {day_name}*\n\n"
    text += schedule if schedule else "📭 Розклад ще не додано."
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def switch_schedule_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    day = query.data.replace("sday_", "")
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    student_class = user.get("class", "")
    await show_schedule_day(query, context, student_class, day)

async def manage_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📅 *Керування розкладом*\n\nВведи *клас* для якого додаєш розклад _(9А, 10Б...)_:",
        parse_mode="Markdown"
    )
    return ADD_SCHEDULE_CLASS

async def add_schedule_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sched_class"] = update.message.text.strip().upper()
    keyboard = [[
        InlineKeyboardButton("Пн", callback_data="schedday_mon"),
        InlineKeyboardButton("Вт", callback_data="schedday_tue"),
        InlineKeyboardButton("Ср", callback_data="schedday_wed"),
        InlineKeyboardButton("Чт", callback_data="schedday_thu"),
        InlineKeyboardButton("Пт", callback_data="schedday_fri"),
    ]]
    await update.message.reply_text(
        f"✅ Клас: *{context.user_data['sched_class']}*\n\nОбери день:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return ADD_SCHEDULE_DAY

async def add_schedule_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["sched_day"] = query.data.replace("schedday_", "")
    day_name = DAYS_FULL.get(context.user_data["sched_day"], "")
    await query.edit_message_text(
        f"✅ День: *{day_name}*\n\n"
        "Введи розклад у такому форматі:\n"
        "```\n1. 8:00 Математика (каб. 21)\n2. 8:45 Фізика (каб. 14)\n```",
        parse_mode="Markdown"
    )
    return ADD_SCHEDULE_TEXT

async def add_schedule_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    cls = context.user_data["sched_class"]
    day = context.user_data["sched_day"]
    if cls not in data["schedule"]:
        data["schedule"][cls] = {}
    data["schedule"][cls][day] = update.message.text.strip()
    save_data(data)
    day_name = DAYS_FULL.get(day, "")
    await update.message.reply_text(
        f"✅ *Розклад збережено!*\n🏫 Клас: *{cls}* | 📅 {day_name}",
        parse_mode="Markdown"
    )
    await show_teacher_menu(update, context)
    return ConversationHandler.END

# ==================== ОГОЛОШЕННЯ ====================
async def add_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 *Нове оголошення*\n\nДля якого *класу*? _(або напиши_ `всі` _для всіх)_:",
        parse_mode="Markdown"
    )
    return ADD_ANNOUNCE_CLASS

async def add_announce_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ann_class"] = update.message.text.strip().upper()
    await update.message.reply_text(
        f"✅ Клас: *{context.user_data['ann_class']}*\n\nВведи текст *оголошення*:",
        parse_mode="Markdown"
    )
    return ADD_ANNOUNCE_TEXT

async def add_announce_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    ann_class = context.user_data["ann_class"]
    ann_text = update.message.text.strip()
    entry = {
        "text": ann_text,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "teacher": f"{user.get('name','')} {user.get('surname','')}"
    }
    if ann_class not in data["announcements"]:
        data["announcements"][ann_class] = []
    data["announcements"][ann_class].append(entry)
    save_data(data)

    # Сповіщення учням
    notif = f"📢 *Оголошення для {ann_class}*\n\n{ann_text}\n\n👨‍🏫 {entry['teacher']}"
    count = 0
    for uid, u in data["users"].items():
        if u.get("role") == "student" and (ann_class == "ВСІ" or u.get("class") == ann_class):
            try:
                await context.bot.send_message(chat_id=int(uid), text=notif, parse_mode="Markdown")
                count += 1
            except:
                pass

    await update.message.reply_text(
        f"✅ *Оголошення відправлено!*\n🔔 Отримали учнів: {count}",
        parse_mode="Markdown"
    )
    await show_teacher_menu(update, context)
    return ConversationHandler.END

async def view_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    student_class = user.get("class", "")
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]

    text = "📢 *Оголошення*\n\n"
    found = False
    for cls in [student_class, "ВСІ"]:
        items = data["announcements"].get(cls, [])
        for ann in items[-5:]:
            text += f"📌 *{ann['date']}*\n{ann['text']}\n👨‍🏫 {ann['teacher']}\n\n"
            found = True
    if not found:
        text += "📭 Оголошень немає."
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== МАТЕРІАЛИ ====================
async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📎 *Додати матеріал*\n\nДля якого *класу*?:",
        parse_mode="Markdown"
    )
    return ADD_FILE_CLASS

async def add_file_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["file_class"] = update.message.text.strip().upper()
    await update.message.reply_text("✅ Введи назву *предмету*:", parse_mode="Markdown")
    return ADD_FILE_SUBJECT

async def add_file_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["file_subject"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Предмет: *{context.user_data['file_subject']}*\n\nВстав *посилання* на матеріал:",
        parse_mode="Markdown"
    )
    return ADD_FILE_LINK

async def add_file_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    cls = context.user_data["file_class"]
    if cls not in data["files"]:
        data["files"][cls] = []
    entry = {
        "subject": context.user_data["file_subject"],
        "link": update.message.text.strip(),
        "date": datetime.now().strftime("%d.%m.%Y")
    }
    data["files"][cls].append(entry)
    save_data(data)
    await update.message.reply_text(
        f"✅ *Матеріал додано!*\n📚 {entry['subject']} — {cls}",
        parse_mode="Markdown"
    )
    await show_teacher_menu(update, context)
    return ConversationHandler.END

async def view_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    student_class = user.get("class", "")
    files = data["files"].get(student_class, [])
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    if not files:
        await query.edit_message_text(
            f"📎 *Матеріали — {student_class}*\n\n📭 Матеріалів немає.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        return
    text = f"📎 *Матеріали — {student_class}*\n\n"
    for f in files:
        text += f"📚 *{f['subject']}*\n🔗 {f['link']}\n📅 {f['date']}\n\n"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== ЗІРКИ / ДОСЯГНЕННЯ ====================
async def add_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏆 *Видати зірку учню*\n\nВведи *клас* учня:",
        parse_mode="Markdown"
    )
    return ADD_STARS_CLASS

async def add_stars_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["star_class"] = update.message.text.strip().upper()
    await update.message.reply_text("✅ Введи *ім'я та прізвище* учня:", parse_mode="Markdown")
    return ADD_STARS_NAME

async def add_stars_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["star_name"] = update.message.text.strip()
    await update.message.reply_text("⭐ Скільки зірок видати? _(1-5)_:", parse_mode="Markdown")
    return ADD_STARS_COUNT

async def add_stars_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
        count = max(1, min(5, count))
    except:
        count = 1
    context.user_data["star_count"] = count
    await update.message.reply_text("📝 За що видаєш зірку? _(причина)_:", parse_mode="Markdown")
    return ADD_STARS_REASON

async def add_stars_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    cls = context.user_data["star_class"]
    if cls not in data["stars"]:
        data["stars"][cls] = []
    stars_str = "⭐" * context.user_data["star_count"]
    entry = {
        "name": context.user_data["star_name"],
        "stars": context.user_data["star_count"],
        "reason": update.message.text.strip(),
        "date": datetime.now().strftime("%d.%m.%Y")
    }
    data["stars"][cls].append(entry)
    save_data(data)

    # Сповіщення учню якщо є
    notif = f"🏆 *Вітаємо!*\n\nТи отримав {stars_str}\nЗа: {entry['reason']}"
    for uid, u in data["users"].items():
        full_name = f"{u.get('name','')} {u.get('surname','')}".strip()
        if u.get("class") == cls and context.user_data["star_name"].lower() in full_name.lower():
            try:
                await context.bot.send_message(chat_id=int(uid), text=notif, parse_mode="Markdown")
            except:
                pass

    await update.message.reply_text(
        f"✅ *Зірку видано!*\n\n👤 {entry['name']}\n{stars_str}\n📝 {entry['reason']}",
        parse_mode="Markdown"
    )
    await show_teacher_menu(update, context)
    return ConversationHandler.END

async def view_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    student_class = user.get("class", "")
    stars_list = data["stars"].get(student_class, [])
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    if not stars_list:
        await query.edit_message_text(
            f"🏆 *Досягнення — {student_class}*\n\n📭 Досягнень ще немає.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        return
    text = f"🏆 *Досягнення — {student_class}*\n\n"
    for s in stars_list[-10:]:
        stars_str = "⭐" * s["stars"]
        text += f"{stars_str} *{s['name']}*\n📝 {s['reason']}\n📅 {s['date']}\n\n"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== ПРОФІЛЬ / ПРО БОТА ====================
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    role_emoji = "👨‍🏫" if user.get("role") == "teacher" else "🎒"
    role_text = "Вчитель" if user.get("role") == "teacher" else "Учень"
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(
        f"👤 *Мій профіль*\n\n"
        f"📛 {user.get('name','')} {user.get('surname','')}\n"
        f"🏫 Клас: *{user.get('class','—')}*\n"
        f"{role_emoji} Роль: *{role_text}*",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(
        "ℹ️ *Про бота*\n\n"
        "🏫 *Шкільний помічник* — бот для учнів та вчителів школи №26, Луцьк\n\n"
        "📚 Домашні завдання\n"
        "📅 Розклад уроків\n"
        "📢 Оголошення\n"
        "📎 Матеріали до уроків\n"
        "🏆 Досягнення учнів\n\n"
        f"👨‍💻 Розробник: {CREATOR_USERNAME}",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    if user.get("role") == "teacher":
        await show_teacher_menu(update, context, edit=True)
    else:
        await show_student_menu(update, context, edit=True)

# ==================== ЗАПУСК ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ADD_HW_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_hw_subject)],
            ADD_HW_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_hw_class)],
            ADD_HW_DAY: [CallbackQueryHandler(add_hw_day, pattern="^hwday_")],
            ADD_HW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_hw_text)],
            ADD_SCHEDULE_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_schedule_class)],
            ADD_SCHEDULE_DAY: [CallbackQueryHandler(add_schedule_day, pattern="^schedday_")],
            ADD_SCHEDULE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_schedule_text)],
            ADD_ANNOUNCE_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_announce_class)],
            ADD_ANNOUNCE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_announce_text)],
            ADD_FILE_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_class)],
            ADD_FILE_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_subject)],
            ADD_FILE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_link)],
            ADD_STARS_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_stars_class)],
            ADD_STARS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_stars_name)],
            ADD_STARS_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_stars_count)],
            ADD_STARS_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_stars_reason)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(view_hw, pattern="^view_hw$"))
    app.add_handler(CallbackQueryHandler(view_all_hw, pattern="^view_all_hw$"))
    app.add_handler(CallbackQueryHandler(add_hw_start, pattern="^add_hw$"))
    app.add_handler(CallbackQueryHandler(delete_hw, pattern="^delete_hw$"))
    app.add_handler(CallbackQueryHandler(confirm_delete, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(view_schedule, pattern="^view_schedule$"))
    app.add_handler(CallbackQueryHandler(switch_schedule_day, pattern="^sday_"))
    app.add_handler(CallbackQueryHandler(manage_schedule, pattern="^manage_schedule$"))
    app.add_handler(CallbackQueryHandler(add_announce, pattern="^add_announce$"))
    app.add_handler(CallbackQueryHandler(view_announce, pattern="^view_announce$"))
    app.add_handler(CallbackQueryHandler(add_file, pattern="^add_file$"))
    app.add_handler(CallbackQueryHandler(view_files, pattern="^view_files$"))
    app.add_handler(CallbackQueryHandler(add_stars, pattern="^add_stars$"))
    app.add_handler(CallbackQueryHandler(view_stars, pattern="^view_stars$"))
    app.add_handler(CallbackQueryHandler(my_profile, pattern="^my_profile$"))
    app.add_handler(CallbackQueryHandler(about, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))

    print("🏫 Шкільний помічник запущено!")
    print(f"👨‍💻 Розробник: {CREATOR_USERNAME}")
    app.run_polling()

if __name__ == "__main__":
    main()
