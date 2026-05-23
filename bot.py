import logging
import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
BOT_TOKEN = "8552924365:AAGKRv-xHAhrXwNQBkV0gjTRGZV67DsAznQ"
ADMIN_IDS = [5260457019]   # <-- вставте свій ID
DATA_FILE = "data.json"
logging.basicConfig(level=logging.INFO)
(MAIN_MENU, CHOOSE_DAY, CHOOSE_TIME,
 ADMIN_PANEL, ADMIN_ADD_DAY, ADMIN_ADD_TIMES, ADMIN_DEL_SLOT) = range(7)
DAYS_ORDER = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"schedule": {}, "appointments": []}
def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
def get_schedule() -> dict:
    return load_data().get("schedule", {})
def get_appointments() -> list:
    return load_data().get("appointments", [])
def add_appointment(user_id, user_name, username, day, time):
    data = load_data()
    data["appointments"].append({
        "user_id": user_id,
        "name": user_name,
        "username": username,
        "day": day,
        "time": time,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
    if day in data["schedule"] and time in data["schedule"][day]:
        data["schedule"][day].remove(time)
        if not data["schedule"][day]:
            del data["schedule"][day]
    save_data(data)
def add_slots(day: str, times: list):
    data = load_data()
    existing = data["schedule"].get(day, [])
    for t in times:
        if t not in existing:
            existing.append(t)
    existing.sort()
    data["schedule"][day] = existing
    save_data(data)
def delete_slot(day: str, time: str):
    data = load_data()
    if day in data["schedule"] and time in data["schedule"][day]:
        data["schedule"][day].remove(time)
        if not data["schedule"][day]:
            del data["schedule"][day]
        save_data(data)
def remove_appointment(index: int):
    data = load_data()
    if 0 <= index < len(data["appointments"]):
        appt = data["appointments"].pop(index)
        day, time = appt["day"], appt["time"]
        existing = data["schedule"].get(day, [])
        if time not in existing:
            existing.append(time)
            existing.sort()
        data["schedule"][day] = existing
        save_data(data)
        return appt
    return None
def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS
def main_menu_kb(uid=None):
    rows = [
        [KeyboardButton("📅 Записатися на прийом")],
        [KeyboardButton("💰 Ціни"), KeyboardButton("❓ Питання")],
    ]
    if uid and is_admin(uid):
        rows.append([KeyboardButton("⚙️ Адмін-панель")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
def days_kb():
    s = get_schedule()
    avail = [d for d in DAYS_ORDER if d in s and s[d]]
    if not avail:
        return None
    rows = [[KeyboardButton(d) for d in avail[i:i+4]] for i in range(0, len(avail), 4)]
    rows.append([KeyboardButton("🔙 Назад")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
def times_kb(day: str):
    s = get_schedule()
    slots = sorted(s.get(day, []))
    btns = [KeyboardButton(t) for t in slots]
    rows = [btns[i:i+4] for i in range(0, len(btns), 4)]
    rows.append([KeyboardButton("🔙 Назад")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📋 Переглянути записи")],
        [KeyboardButton("➕ Додати час прийому"), KeyboardButton("🗑 Видалити слот")],
        [KeyboardButton("🔙 Головне меню")],
    ], resize_keyboard=True)
def admin_days_kb(for_delete=False):
    if for_delete:
        s = get_schedule()
        days = [d for d in DAYS_ORDER if d in s and s[d]]
    else:
        days = DAYS_ORDER
    rows = [[KeyboardButton(d) for d in days[i:i+4]] for i in range(0, len(days), 4)]
    rows.append([KeyboardButton("🔙 Назад")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text(
        f"👋 Вітаємо, *{u.first_name or 'пацієнте'}*!\n\n"
        "Ви звернулись до бота хірурга.\n"
        "Оберіть потрібний пункт меню 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(u.id),
    )
    return MAIN_MENU
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    u = update.effective_user
    if text == "📅 Записатися на прийом":
        kb = days_kb()
        if not kb:
            await update.message.reply_text(
                "😔 Наразі вільних місць немає.\nЗверніться за телефоном.",
                reply_markup=main_menu_kb(u.id),
            )
            return MAIN_MENU
        await update.message.reply_text("📆 Який день тижня Вам зручно?", reply_markup=kb)
        return CHOOSE_DAY
    elif text == "💰 Ціни":
        await update.message.reply_text(
            "💰 *Прайс-лист*\n\n"
            "• Первинна консультація — 500 грн\n"
            "• Повторна консультація — 300 грн\n"
            "• Перев'язка — 200 грн\n\n"
            "_Детальніше — по телефону._",
            parse_mode="Markdown",
            reply_markup=main_menu_kb(u.id),
        )
        return MAIN_MENU
    elif text == "❓ Питання":
        await update.message.reply_text(
            "❓ *Є питання?*\n\n"
            "Телефонуйте: +380 XX XXX XX XX",
            parse_mode="Markdown",
            reply_markup=main_menu_kb(u.id),
        )
        return MAIN_MENU
    elif text == "⚙️ Адмін-панель" and is_admin(u.id):
        await update.message.reply_text("⚙️ *Адмін-панель*", parse_mode="Markdown", reply_markup=admin_kb())
        return ADMIN_PANEL
    await update.message.reply_text("Скористайтесь кнопками меню 👇", reply_markup=main_menu_kb(u.id))
    return MAIN_MENU
async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    u = update.effective_user
    if text == "🔙 Назад":
        await update.message.reply_text("Головне меню:", reply_markup=main_menu_kb(u.id))
        return MAIN_MENU
    s = get_schedule()
    if text not in [d for d in DAYS_ORDER if d in s and s[d]]:
        await update.message.reply_text("Оберіть день з кнопок 👇", reply_markup=days_kb())
        return CHOOSE_DAY
    context.user_data["day"] = text
    await update.message.reply_text(
        f"✅ Добре, обираємо час на *{text}*.",
        parse_mode="Markdown",
        reply_markup=times_kb(text),
    )
    return CHOOSE_TIME
async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    u = update.effective_user
    day = context.user_data.get("day", "—")
    if text == "🔙 Назад":
        kb = days_kb()
        if kb:
            await update.message.reply_text("Який день тижня Вам зручно?", reply_markup=kb)
            return CHOOSE_DAY
        await update.message.reply_text("Головне меню:", reply_markup=main_menu_kb(u.id))
        return MAIN_MENU
    if text not in get_schedule().get(day, []):
        await update.message.reply_text("Оберіть час з кнопок 👇", reply_markup=times_kb(day))
        return CHOOSE_TIME
    name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Невідомо"
    uname = f"@{u.username}" if u.username else "немає"
    add_appointment(u.id, name, uname, day, text)
    await update.message.reply_text(
        "✅ *Все готово, зафіксували.*\n\nЧекаємо на Вас! 🏥",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(u.id),
    )
    return MAIN_MENU
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    u = update.effective_user
    if not is_admin(u.id):
        return MAIN_MENU
    if text == "🔙 Головне меню":
        await update.message.reply_text("Головне меню:", reply_markup=main_menu_kb(u.id))
        return MAIN_MENU
    elif text == "📋 Переглянути записи":
        appts = get_appointments()
        if not appts:
            await update.message.reply_text("📋 Записів поки немає.", reply_markup=admin_kb())
            return ADMIN_PANEL
        by_day = {}
        for i, a in enumerate(appts):
            by_day.setdefault(a["day"], []).append((i, a))
        lines = ["📋 *Всі записи:*\n"]
        for day in DAYS_ORDER:
            if day not in by_day:
                continue
            lines.append(f"*{day}:*")
            for idx, a in sorted(by_day[day], key=lambda x: x[1]["time"]):
                lines.append(f"  🕐 {a['time']} — {a['name']} ({a['username']}) \\[#{idx+1}\\]")
        lines.append("\n_Скасувати запис: /cancel\\_<номер>_\n_Приклад: /cancel\\_1_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=admin_kb())
        return ADMIN_PANEL
    elif text == "➕ Додати час прийому":
        await update.message.reply_text("📅 Виберіть день:", reply_markup=admin_days_kb(False))
        return ADMIN_ADD_DAY
    elif text == "🗑 Видалити слот":
        if not get_schedule():
            await update.message.reply_text("Розклад порожній.", reply_markup=admin_kb())
            return ADMIN_PANEL
        context.user_data.pop("del_day", None)
        await update.message.reply_text("📅 Виберіть день:", reply_markup=admin_days_kb(True))
        return ADMIN_DEL_SLOT
    return ADMIN_PANEL
async def admin_add_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Назад":
        await update.message.reply_text("Адмін-панель:", reply_markup=admin_kb())
        return ADMIN_PANEL
    if text not in DAYS_ORDER:
        await update.message.reply_text("Оберіть день з кнопок.", reply_markup=admin_days_kb())
        return ADMIN_ADD_DAY
    context.user_data["add_day"] = text
    await update.message.reply_text(
        f"⏰ Введіть час(и) для *{text}* через пробіл:\n"
        "Приклад: `09:00 09:30 10:00 14:30`",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]], resize_keyboard=True),
    )
    return ADMIN_ADD_TIMES
async def admin_add_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Назад":
        await update.message.reply_text("Виберіть день:", reply_markup=admin_days_kb())
        return ADMIN_ADD_DAY
    day = context.user_data.get("add_day")
    raw = text.replace(",", " ").split()
    valid, invalid = [], []
    for t in raw:
        try:
            datetime.strptime(t.strip(), "%H:%M")
            valid.append(t.strip())
        except ValueError:
            invalid.append(t.strip())
    if not valid:
        await update.message.reply_text("❌ Неправильний формат. Приклад: `09:30 10:00`", parse_mode="Markdown")
        return ADMIN_ADD_TIMES
    add_slots(day, valid)
    msg = f"✅ Додано до *{day}*: {', '.join(valid)}"
    if invalid:
        msg += f"\n⚠️ Пропущено (неправильний формат): {', '.join(invalid)}"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=admin_kb())
    return ADMIN_PANEL
async def admin_del_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    s = get_schedule()
    if text == "🔙 Назад":
        if "del_day" in context.user_data:
            context.user_data.pop("del_day")
            await update.message.reply_text("Виберіть день:", reply_markup=admin_days_kb(True))
        else:
            await update.message.reply_text("Адмін-панель:", reply_markup=admin_kb())
            return ADMIN_PANEL
        return ADMIN_DEL_SLOT
    if "del_day" not in context.user_data:
        avail = [d for d in DAYS_ORDER if d in s and s[d]]
        if text not in avail:
            await update.message.reply_text("Оберіть день з кнопок.", reply_markup=admin_days_kb(True))
            return ADMIN_DEL_SLOT
        context.user_data["del_day"] = text
        slots = sorted(s[text])
        kb = [[KeyboardButton(sl) for sl in slots[i:i+4]] for i in range(0, len(slots), 4)]
        kb.append([KeyboardButton("🔙 Назад")])
        await update.message.reply_text(
            f"🗑 Оберіть час для видалення з *{text}*:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        )
        return ADMIN_DEL_SLOT
    day = context.user_data["del_day"]
    if text not in s.get(day, []):
        await update.message.reply_text("Оберіть час з кнопок.")
        return ADMIN_DEL_SLOT
    delete_slot(day, text)
    context.user_data.pop("del_day", None)
    await update.message.reply_text(
        f"✅ Слот *{text}* у *{day}* видалено.",
        parse_mode="Markdown",
        reply_markup=admin_kb(),
    )
    return ADMIN_PANEL
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not is_admin(u.id):
        return
    try:
        idx = int(update.message.text.replace("/cancel_", "")) - 1
    except (ValueError, AttributeError):
        await update.message.reply_text("Формат: /cancel\\_<номер>", parse_mode="Markdown")
        return
    appt = remove_appointment(idx)
    if appt:
        await update.message.reply_text(
            f"✅ Запис #{idx+1} скасовано:\n"
            f"{appt['name']} ({appt['username']}) — {appt['day']} {appt['time']}\n"
            f"⟳ Слот повернуто у розклад.",
            reply_markup=admin_kb(),
        )
    else:
        await update.message.reply_text("❌ Запис не знайдено.", reply_markup=admin_kb())
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU:       [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            CHOOSE_DAY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_day)],
            CHOOSE_TIME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
            ADMIN_PANEL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel)],
            ADMIN_ADD_DAY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_day)],
            ADMIN_ADD_TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_times)],
            ADMIN_DEL_SLOT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_del_slot)],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(r"^/cancel_\d+$"), cancel_cmd),
        ],
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex(r"^/cancel_\d+$"), cancel_cmd))
    print("✅ Бот запущено!")
    app.run_polling()
if __name__ == "__main__":
    main()