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
TEACHER_PASSWORD = "school26"  # Пароль для вчителів (можна змінити)
CREATOR_USERNAME = "@aquaee"
DATA_FILE = "school_data.json"

# ==================== СТАНИ ====================
(
    REGISTER_NAME, REGISTER_SURNAME, REGISTER_CLASS,
    CHOOSE_ROLE, TEACHER_PASSWORD_INPUT,
    TEACHER_MENU, ADD_HW_SUBJECT, ADD_HW_CLASS, ADD_HW_TEXT,
    STUDENT_MENU, VIEW_HW
) = range(11)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== БАЗА ДАНИХ (JSON файл) ====================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "homework": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== СТАРТ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    # Якщо вже зареєстрований — головне меню
    if user_id in data["users"]:
        user = data["users"][user_id]
        role = user.get("role", "student")
        if role == "teacher":
            await show_teacher_menu(update, context)
        else:
            await show_student_menu(update, context)
        return ConversationHandler.END

    await update.message.reply_text(
        "🏫 *Ласкаво просимо до Шкільного помічника!*\n\n"
        "Цей бот допоможе учням та вчителям:\n"
        "📚 Переглядати домашні завдання\n"
        "✏️ Додавати нові завдання (для вчителів)\n\n"
        "Для початку давай познайомимося!\n\n"
        "👤 Введи своє *ім'я*:",
        parse_mode="Markdown"
    )
    return REGISTER_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Чудово, *{context.user_data['name']}*!\n\n"
        "📝 Тепер введи своє *прізвище*:",
        parse_mode="Markdown"
    )
    return REGISTER_SURNAME

async def get_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["surname"] = update.message.text.strip()
    await update.message.reply_text(
        "🏫 Введи свій *клас*\n"
        "_(наприклад: 9А, 10Б, 11В)_:",
        parse_mode="Markdown"
    )
    return REGISTER_CLASS

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["class"] = update.message.text.strip().upper()

    keyboard = [
        [InlineKeyboardButton("🎒 Я учень", callback_data="role_student")],
        [InlineKeyboardButton("👨‍🏫 Я вчитель", callback_data="role_teacher")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 *{context.user_data['name']} {context.user_data['surname']}*, клас *{context.user_data['class']}*\n\n"
        "Обери свою роль:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSE_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "role_student":
        # Зберігаємо як учня
        user_id = str(update.effective_user.id)
        data = load_data()
        data["users"][user_id] = {
            "name": context.user_data["name"],
            "surname": context.user_data["surname"],
            "class": context.user_data["class"],
            "role": "student"
        }
        save_data(data)

        await query.edit_message_text(
            f"✅ *Реєстрацію завершено!*\n\n"
            f"👤 {context.user_data['name']} {context.user_data['surname']}\n"
            f"🏫 Клас: {context.user_data['class']}\n"
            f"🎒 Роль: Учень\n\n"
            f"Вітаємо в Шкільному помічнику! 🎉",
            parse_mode="Markdown"
        )
        await show_student_menu(update, context, edit=False)
        return ConversationHandler.END

    elif query.data == "role_teacher":
        await query.edit_message_text(
            "🔐 *Доступ для вчителів*\n\n"
            "Введи пароль для вчителя:",
            parse_mode="Markdown"
        )
        return TEACHER_PASSWORD_INPUT

async def teacher_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered = update.message.text.strip()

    if entered == TEACHER_PASSWORD:
        user_id = str(update.effective_user.id)
        data = load_data()
        data["users"][user_id] = {
            "name": context.user_data["name"],
            "surname": context.user_data["surname"],
            "class": context.user_data.get("class", "—"),
            "role": "teacher"
        }
        save_data(data)

        await update.message.reply_text(
            f"✅ *Вітаємо, {context.user_data['name']} {context.user_data['surname']}!*\n\n"
            f"👨‍🏫 Роль: Вчитель\n\n"
            "Доступ надано! 🎉",
            parse_mode="Markdown"
        )
        await show_teacher_menu(update, context)
        return ConversationHandler.END
    else:
        keyboard = [[InlineKeyboardButton("🔙 Назад (стати учнем)", callback_data="back_to_student")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ *Невірний пароль!*\n\n"
            "Спробуй ще раз або повернись назад:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return TEACHER_PASSWORD_INPUT

async def back_to_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    data = load_data()
    data["users"][user_id] = {
        "name": context.user_data.get("name", ""),
        "surname": context.user_data.get("surname", ""),
        "class": context.user_data.get("class", ""),
        "role": "student"
    }
    save_data(data)

    await query.edit_message_text("✅ Зареєстровано як учень!")
    await show_student_menu(update, context, edit=False)
    return ConversationHandler.END

# ==================== МЕНЮ УЧНЯ ====================
async def show_student_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})

    keyboard = [
        [InlineKeyboardButton("📚 Домашні завдання", callback_data="view_hw")],
        [InlineKeyboardButton("👤 Мій профіль", callback_data="my_profile")],
        [InlineKeyboardButton("ℹ️ Про бота", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"🏫 *Шкільний помічник*\n\n"
        f"Привіт, *{user.get('name', '')}*! 👋\n"
        f"Клас: *{user.get('class', '')}*\n\n"
        "Що хочеш зробити?"
    )

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ==================== МЕНЮ ВЧИТЕЛЯ ====================
async def show_teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})

    keyboard = [
        [InlineKeyboardButton("➕ Додати ДЗ", callback_data="add_hw")],
        [InlineKeyboardButton("📋 Всі ДЗ", callback_data="view_all_hw")],
        [InlineKeyboardButton("🗑️ Видалити ДЗ", callback_data="delete_hw")],
        [InlineKeyboardButton("👤 Мій профіль", callback_data="my_profile")],
        [InlineKeyboardButton("ℹ️ Про бота", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"🏫 *Шкільний помічник — Панель вчителя*\n\n"
        f"Привіт, *{user.get('name', '')}* 👨‍🏫\n\n"
        "Що хочеш зробити?"
    )

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ==================== ДОМАШНІ ЗАВДАННЯ (УЧЕНЬ) ====================
async def view_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    data = load_data()
    user = data["users"].get(user_id, {})
    student_class = user.get("class", "")

    hw_list = data["homework"].get(student_class, [])

    if not hw_list:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await query.edit_message_text(
            f"📚 *Домашні завдання — {student_class}*\n\n"
            "📭 Наразі немає завдань для твого класу.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    text = f"📚 *Домашні завдання — клас {student_class}*\n\n"
    for i, hw in enumerate(hw_list, 1):
        text += (
            f"*{i}. {hw['subject']}*\n"
            f"📝 {hw['text']}\n"
            f"📅 Додано: {hw['date']}\n"
            f"👨‍🏫 {hw['teacher']}\n\n"
        )

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ==================== ДОДАТИ ДЗ (ВЧИТЕЛЬ) ====================
async def add_hw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ *Додати домашнє завдання*\n\n"
        "Введи назву *предмету*\n_(наприклад: Математика, Фізика, Хімія)_:",
        parse_mode="Markdown"
    )
    return ADD_HW_SUBJECT

async def add_hw_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hw_subject"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Предмет: *{context.user_data['hw_subject']}*\n\n"
        "🏫 Для якого *класу* це завдання?\n_(наприклад: 9А, 10Б)_:",
        parse_mode="Markdown"
    )
    return ADD_HW_CLASS

async def add_hw_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hw_class"] = update.message.text.strip().upper()
    await update.message.reply_text(
        f"✅ Клас: *{context.user_data['hw_class']}*\n\n"
        "📝 Тепер введи *текст завдання*:",
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
        "date": datetime.now().strftime("%d.%m.%Y"),
        "teacher": f"{user.get('name', '')} {user.get('surname', '')}",
        "id": len(data["homework"][hw_class]) + 1
    }
    data["homework"][hw_class].append(hw_entry)
    save_data(data)

    await update.message.reply_text(
        f"✅ *Завдання додано!*\n\n"
        f"📚 Предмет: *{hw_entry['subject']}*\n"
        f"🏫 Клас: *{hw_class}*\n"
        f"📝 {hw_entry['text']}\n"
        f"📅 {hw_entry['date']}",
        parse_mode="Markdown"
    )
    await show_teacher_menu(update, context)
    return ConversationHandler.END

# ==================== ПЕРЕГЛЯД ВСІХ ДЗ (ВЧИТЕЛЬ) ====================
async def view_all_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()

    if not data["homework"]:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        await query.edit_message_text(
            "📋 *Всі домашні завдання*\n\n"
            "📭 Завдань ще немає.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    text = "📋 *Всі домашні завдання*\n\n"
    for cls, hw_list in data["homework"].items():
        if hw_list:
            text += f"🏫 *Клас {cls}:*\n"
            for hw in hw_list:
                text += f"  • {hw['subject']}: {hw['text'][:50]}{'...' if len(hw['text']) > 50 else ''}\n"
            text += "\n"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ==================== ВИДАЛИТИ ДЗ ====================
async def delete_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    keyboard = []

    for cls, hw_list in data["homework"].items():
        for i, hw in enumerate(hw_list):
            btn_text = f"❌ {cls} | {hw['subject']} ({hw['date']})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"del_{cls}_{i}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])

    if len(keyboard) == 1:
        await query.edit_message_text(
            "🗑️ *Видалити завдання*\n\n"
            "Немає завдань для видалення.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            "🗑️ *Оберіть завдання для видалення:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 2)
    cls = parts[1]
    idx = int(parts[2])

    data = load_data()
    if cls in data["homework"] and idx < len(data["homework"][cls]):
        removed = data["homework"][cls].pop(idx)
        save_data(data)
        await query.edit_message_text(
            f"✅ Завдання *{removed['subject']}* для класу *{cls}* видалено!",
            parse_mode="Markdown"
        )
    await show_teacher_menu(update, context, edit=False)

# ==================== ПРОФІЛЬ ====================
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
        f"📛 Ім'я: *{user.get('name', '')} {user.get('surname', '')}*\n"
        f"🏫 Клас: *{user.get('class', '—')}*\n"
        f"{role_emoji} Роль: *{role_text}*\n\n"
        f"🆔 ID: `{user_id}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ==================== ПРО БОТА ====================
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    await query.edit_message_text(
        "ℹ️ *Про бота*\n\n"
        "🏫 *Шкільний помічник* — бот для учнів та вчителів школи №26\n\n"
        "📚 Функції:\n"
        "• Перегляд домашніх завдань\n"
        "• Додавання завдань (вчителі)\n"
        "• Зручний інтерфейс\n\n"
        f"👨‍💻 Розробник: {CREATOR_USERNAME}\n"
        "🏫 Школа №26, Луцьк",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ==================== НАЗАД ====================
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

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            REGISTER_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_surname)],
            REGISTER_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role, pattern="^role_")],
            TEACHER_PASSWORD_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_password_input),
                CallbackQueryHandler(back_to_student, pattern="^back_to_student$")
            ],
            ADD_HW_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_hw_subject)],
            ADD_HW_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_hw_class)],
            ADD_HW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_hw_text)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(view_hw, pattern="^view_hw$"))
    app.add_handler(CallbackQueryHandler(add_hw_start, pattern="^add_hw$"))
    app.add_handler(CallbackQueryHandler(view_all_hw, pattern="^view_all_hw$"))
    app.add_handler(CallbackQueryHandler(delete_hw, pattern="^delete_hw$"))
    app.add_handler(CallbackQueryHandler(confirm_delete, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(my_profile, pattern="^my_profile$"))
    app.add_handler(CallbackQueryHandler(about, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))

    print("🏫 Шкільний помічник запущено!")
    print(f"👨‍💻 Розробник: {CREATOR_USERNAME}")
    print(f"🔐 Пароль вчителя: {TEACHER_PASSWORD}")
    app.run_polling()

if __name__ == "__main__":
    main()
