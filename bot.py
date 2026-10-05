from dotenv import load_dotenv
import os
import sqlite3

from datetime import datetime, date, timedelta, time

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)


# =========================
# DATABASE
# =========================

def init_db():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            task TEXT,
            important TEXT,
            deadline TEXT,
            completed INTEGER DEFAULT 0,
            reminder_sent INTEGER DEFAULT 0
        )
    """)

    try:
        cursor.execute(
            "ALTER TABLE tasks ADD COLUMN completed INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE tasks ADD COLUMN reminder_sent INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# =========================
# TOKEN
# =========================

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")


# =========================
# STATES
# =========================

CATEGORY, TASK, IMPORTANT, DEADLINE, DEADLINE_DATE = range(5)


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        ["➕ Topshiriq qo‘shish"],
        ["📋 Topshiriqlar"]
    ]

    await update.message.reply_text(
        "🎓 Student Task Bot\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


# =========================
# ADD TASK
# =========================

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📚 Fan nomini yoki kategoriyani yozing:\n\n"
        "Masalan: Matematika, Informatika, Shaxsiy"
    )

    return CATEGORY


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["category"] = update.message.text

    await update.message.reply_text(
        "📝 Vazifa nomini yozing:"
    )

    return TASK


async def get_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["task"] = update.message.text

    keyboard = [
        ["🔴 Muhim", "⚪ Oddiy"]
    ]

    await update.message.reply_text(
        "Muhimligini belgilang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

    return IMPORTANT


async def get_important(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["important"] = update.message.text

    keyboard = [
        ["📅 Ha", "❌ Yo‘q"]
    ]

    await update.message.reply_text(
        "Deadline bormi?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

    return DEADLINE


async def get_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):

    answer = update.message.text

    if answer == "📅 Ha":

        await update.message.reply_text(
            "📅 Deadline sanasini yozing:\n\n"
            "Masalan: 05.10.2026"
        )

        return DEADLINE_DATE

    context.user_data["deadline"] = "Belgilanmagan"

    await save_task(update, context)

    return ConversationHandler.END


async def get_deadline_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    deadline = update.message.text

    try:
        datetime.strptime(deadline, "%d.%m.%Y")
    except ValueError:

        await update.message.reply_text(
            "❌ Sana formati noto‘g‘ri.\n\n"
            "Masalan: 05.10.2026"
        )

        return DEADLINE_DATE

    context.user_data["deadline"] = deadline

    await save_task(update, context)

    return ConversationHandler.END


# =========================
# SAVE TASK
# =========================

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    category = context.user_data.get("category")
    task = context.user_data.get("task")
    important = context.user_data.get("important")
    deadline = context.user_data.get("deadline")

    user_id = update.effective_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (
            user_id,
            category,
            task,
            important,
            deadline,
            reminder_sent
        )
        VALUES (?, ?, ?, ?, ?, 0)
    """, (
        user_id,
        category,
        task,
        important,
        deadline
    ))

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Topshiriq saqlandi!\n\n"
        f"📚 {category}\n"
        f"📝 {task}\n"
        f"{important}\n"
        f"📅 {deadline}"
    )


# =========================
# CANCEL
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "❌ Topshiriq qo‘shish bekor qilindi."
    )

    return ConversationHandler.END


# =========================
# TASK MENU — 5 TA TUGMA
# =========================

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        ["⏳ Bajarilmagan"],
        ["📅 Bugungi"],
        ["⚠️ Muddati yaqin (3 kun)"],
        ["✅ Bajarilgan"],
        ["📋 Hammasi"]
    ]

    await update.message.reply_text(
        "📋 Topshiriqlarni tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


# =========================
# FILTERS
# =========================

async def show_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await show_tasks(update, completed=0)


async def show_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await show_tasks(update, completed=1)


async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await show_tasks(update, completed=None)


# =========================
# BUGUNGI
# =========================

async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, category, task, important, deadline, completed
        FROM tasks
        WHERE user_id = ?
        AND completed = 0
        AND deadline != 'Belgilanmagan'
    """, (user_id,))

    rows = cursor.fetchall()

    conn.close()

    today = date.today()

    today_rows = []

    for row in rows:

        try:
            deadline_date = datetime.strptime(
                row[4],
                "%d.%m.%Y"
            ).date()

            if deadline_date == today:
                today_rows.append(row)

        except ValueError:
            pass

    await send_task_list(
        update,
        today_rows,
        "📅 Bugungi topshiriqlar"
    )


# =========================
# MUDDATI YAQIN — 3 KUN
# =========================

async def show_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, category, task, important, deadline, completed
        FROM tasks
        WHERE user_id = ?
        AND completed = 0
        AND deadline != 'Belgilanmagan'
    """, (user_id,))

    rows = cursor.fetchall()

    conn.close()

    today = date.today()
    end_date = today + timedelta(days=3)

    upcoming_rows = []

    for row in rows:

        try:
            deadline_date = datetime.strptime(
                row[4],
                "%d.%m.%Y"
            ).date()

            if today <= deadline_date <= end_date:
                upcoming_rows.append(row)

        except ValueError:
            pass

    upcoming_rows.sort(
        key=lambda row: datetime.strptime(
            row[4],
            "%d.%m.%Y"
        ).date()
    )

    await send_task_list(
        update,
        upcoming_rows,
        "⚠️ Muddati yaqin topshiriqlar (3 kun)"
    )


# =========================
# SHOW TASKS
# =========================

async def show_tasks(update: Update, completed=None):

    user_id = update.effective_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    if completed is None:

        cursor.execute("""
            SELECT id, category, task, important, deadline, completed
            FROM tasks
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,))

    else:

        cursor.execute("""
            SELECT id, category, task, important, deadline, completed
            FROM tasks
            WHERE user_id = ?
            AND completed = ?
            ORDER BY id DESC
        """, (user_id, completed))

    rows = cursor.fetchall()

    conn.close()

    await send_task_list(
        update,
        rows,
        "📋 Topshiriqlar"
    )


# =========================
# SEND TASK LIST
# =========================

async def send_task_list(update, rows, title):

    if not rows:

        await update.message.reply_text(
            f"{title}\n\n"
            "📋 Bu bo‘limda topshiriqlar yo‘q."
        )

        return

    await update.message.reply_text(title)

    for row in rows:

        task_id, category, task, important, deadline, is_completed = row

        if is_completed:
            status = "✅ Bajarilgan"
        else:
            status = "⏳ Bajarilmagan"

        text = (
            f"#{task_id}\n"
            f"📚 {category}\n"
            f"📝 {task}\n"
            f"{important}\n"
            f"📅 {deadline}\n"
            f"{status}"
        )

        buttons = []

        if not is_completed:

            buttons.append(
                InlineKeyboardButton(
                    "✅ Bajarildi",
                    callback_data=f"done_{task_id}"
                )
            )

        buttons.append(
            InlineKeyboardButton(
                "✏️ Tahrirlash",
                callback_data=f"edit_{task_id}"
            )
        )

        buttons.append(
            InlineKeyboardButton(
                "🗑 O‘chirish",
                callback_data=f"delete_{task_id}"
            )
        )

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([buttons])
        )


# =========================
# MARK AS DONE
# =========================

async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    task_id = int(
        query.data.split("_")[1]
    )

    user_id = query.from_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET completed = 1
        WHERE id = ?
        AND user_id = ?
    """, (
        task_id,
        user_id
    ))

    conn.commit()
    conn.close()

    await query.edit_message_text(
        "✅ Topshiriq bajarildi!"
    )


# =========================
# DELETE TASK
# =========================

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    task_id = int(
        query.data.split("_")[1]
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "🗑 Ha, o‘chirish",
                callback_data=f"confirm_delete_{task_id}"
            ),
            InlineKeyboardButton(
                "❌ Bekor qilish",
                callback_data=f"cancel_delete_{task_id}"
            )
        ]
    ]

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    task_id = int(
        query.data.split("_")[2]
    )

    user_id = query.from_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM tasks
        WHERE id = ?
        AND user_id = ?
    """, (
        task_id,
        user_id
    ))

    conn.commit()
    conn.close()

    await query.edit_message_text(
        "🗑 Topshiriq o‘chirildi."
    )


async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    task_id = int(
        query.data.split("_")[2]
    )

    user_id = query.from_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, category, task, important, deadline, completed
        FROM tasks
        WHERE id = ?
        AND user_id = ?
    """, (
        task_id,
        user_id
    ))

    row = cursor.fetchone()

    conn.close()

    if not row:

        await query.edit_message_text(
            "❌ Topshiriq topilmadi."
        )

        return

    await show_task_from_callback(query, row)


async def show_task_from_callback(query, row):

    task_id, category, task, important, deadline, is_completed = row

    if is_completed:
        status = "✅ Bajarilgan"
    else:
        status = "⏳ Bajarilmagan"

    text = (
        f"#{task_id}\n"
        f"📚 {category}\n"
        f"📝 {task}\n"
        f"{important}\n"
        f"📅 {deadline}\n"
        f"{status}"
    )

    buttons = []

    if not is_completed:

        buttons.append(
            InlineKeyboardButton(
                "✅ Bajarildi",
                callback_data=f"done_{task_id}"
            )
        )

    buttons.append(
        InlineKeyboardButton(
            "✏️ Tahrirlash",
            callback_data=f"edit_{task_id}"
        )
    )

    buttons.append(
        InlineKeyboardButton(
            "🗑 O‘chirish",
            callback_data=f"delete_{task_id}"
        )
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([buttons])
    )


# =========================
# EDIT TASK
# =========================

async def edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    task_id = int(
        query.data.split("_")[1]
    )

    user_id = query.from_user.id

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM tasks
        WHERE id = ?
        AND user_id = ?
    """, (
        task_id,
        user_id
    ))

    row = cursor.fetchone()

    conn.close()

    if not row:

        await query.edit_message_text(
            "❌ Topshiriq topilmadi."
        )

        return

    context.user_data["edit_task_id"] = task_id

    keyboard = [
        [
            InlineKeyboardButton(
                "📚 Fan",
                callback_data="edit_field_category"
            ),
            InlineKeyboardButton(
                "📝 Vazifa",
                callback_data="edit_field_task"
            )
        ],
        [
            InlineKeyboardButton(
                "🔴 Muhimlik",
                callback_data="edit_field_important"
            ),
            InlineKeyboardButton(
                "📅 Deadline",
                callback_data="edit_field_deadline"
            )
        ]
    ]

    await query.edit_message_text(
        "✏️ Qaysi ma’lumotni o‘zgartirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# SELECT EDIT FIELD
# =========================

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    field = query.data.replace(
        "edit_field_",
        ""
    )

    context.user_data["edit_field"] = field
    context.user_data["edit_waiting_date"] = False

    if field == "category":

        await query.message.reply_text(
            "📚 Yangi fan yoki kategoriya nomini yozing:"
        )

    elif field == "task":

        await query.message.reply_text(
            "📝 Yangi vazifa nomini yozing:"
        )

    elif field == "important":

        keyboard = [
            ["🔴 Muhim", "⚪ Oddiy"]
        ]

        await query.message.reply_text(
            "Muhimligini tanlang:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

    elif field == "deadline":

        keyboard = [
            ["📅 Deadline bor", "❌ Deadline yo‘q"]
        ]

        await query.message.reply_text(
            "Deadline holatini tanlang:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )


# =========================
# SAVE EDIT
# =========================

async def save_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    task_id = context.user_data.get("edit_task_id")
    field = context.user_data.get("edit_field")

    if not task_id or not field:
        return

    value = update.message.text

    if field == "deadline" and value == "📅 Deadline bor":

        context.user_data["edit_waiting_date"] = True

        await update.message.reply_text(
            "📅 Yangi deadline sanasini yozing:\n\n"
            "Masalan: 05.10.2026"
        )

        return

    if field == "deadline" and value == "❌ Deadline yo‘q":

        value = "Belgilanmagan"

    elif (
        field == "deadline"
        and context.user_data.get("edit_waiting_date")
    ):

        try:
            datetime.strptime(value, "%d.%m.%Y")
        except ValueError:

            await update.message.reply_text(
                "❌ Sana formati noto‘g‘ri.\n\n"
                "Masalan: 05.10.2026"
            )

            return

        context.user_data["edit_waiting_date"] = False

    user_id = update.effective_user.id

    allowed_fields = [
        "category",
        "task",
        "important",
        "deadline"
    ]

    if field not in allowed_fields:
        return

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    # Deadline o‘zgarganda yangi eslatmaga ruxsat beramiz
    if field == "deadline":

        cursor.execute("""
            UPDATE tasks
            SET deadline = ?,
                reminder_sent = 0
            WHERE id = ?
            AND user_id = ?
        """, (
            value,
            task_id,
            user_id
        ))

    else:

        cursor.execute(
            f"""
            UPDATE tasks
            SET {field} = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                value,
                task_id,
                user_id
            )
        )

    conn.commit()
    conn.close()

    context.user_data.pop("edit_task_id", None)
    context.user_data.pop("edit_field", None)
    context.user_data.pop("edit_waiting_date", None)

    await update.message.reply_text(
        "✅ Topshiriq muvaffaqiyatli tahrirlandi!"
    )


# =========================
# 🔔 REMINDER
# Deadline'ga 1 kun qolganda
# 06:00 da yuboriladi
# =========================

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):

    today = date.today()
    tomorrow = today + timedelta(days=1)

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, category, task, deadline
        FROM tasks
        WHERE completed = 0
        AND reminder_sent = 0
        AND deadline != 'Belgilanmagan'
    """)

    rows = cursor.fetchall()

    for row in rows:

        task_id, user_id, category, task, deadline = row

        try:
            deadline_date = datetime.strptime(
                deadline,
                "%d.%m.%Y"
            ).date()
        except ValueError:
            continue

        # Deadline ertaga bo‘lsa
        if deadline_date == tomorrow:

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "🔔 Eslatma!\n\n"
                        "⏰ Bu topshiriqning deadline'iga 1 kun qoldi.\n\n"
                        f"📚 {category}\n"
                        f"📝 {task}\n"
                        f"📅 Deadline: {deadline}"
                    )
                )

                cursor.execute("""
                    UPDATE tasks
                    SET reminder_sent = 1
                    WHERE id = ?
                """, (task_id,))

            except Exception as e:
                print(
                    f"Reminder yuborishda xato: {e}"
                )

    conn.commit()
    conn.close()


# =========================
# DATABASE INIT
# =========================

init_db()


# =========================
# APPLICATION
# =========================

app = Application.builder().token(TOKEN).build()


# =========================
# ADD TASK CONVERSATION
# =========================

conversation = ConversationHandler(

    entry_points=[
        MessageHandler(
            filters.Regex("^➕ Topshiriq qo‘shish$"),
            add_task
        )
    ],

    states={

        CATEGORY: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                get_category
            )
        ],

        TASK: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                get_task
            )
        ],

        IMPORTANT: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                get_important
            )
        ],

        DEADLINE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                get_deadline
            )
        ],

        DEADLINE_DATE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                get_deadline_date
            )
        ]
    },

    fallbacks=[
        CommandHandler(
            "cancel",
            cancel
        )
    ]
)


# =========================
# BASIC HANDLERS
# =========================

app.add_handler(
    CommandHandler(
        "start",
        start
    )
)

app.add_handler(conversation)


app.add_handler(
    MessageHandler(
        filters.Regex("^📋 Topshiriqlar$"),
        tasks
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^⏳ Bajarilmagan$"),
        show_pending
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^📅 Bugungi$"),
        show_today
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^⚠️ Muddati yaqin \\(3 kun\\)$"),
        show_upcoming
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^✅ Bajarilgan$"),
        show_completed
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^📋 Hammasi$"),
        show_all
    )
)


# =========================
# CALLBACK HANDLERS
# =========================

app.add_handler(
    CallbackQueryHandler(
        mark_done,
        pattern="^done_"
    )
)

app.add_handler(
    CallbackQueryHandler(
        delete_task,
        pattern="^delete_"
    )
)

app.add_handler(
    CallbackQueryHandler(
        confirm_delete,
        pattern="^confirm_delete_"
    )
)

app.add_handler(
    CallbackQueryHandler(
        cancel_delete,
        pattern="^cancel_delete_"
    )
)

app.add_handler(
    CallbackQueryHandler(
        edit_task,
        pattern="^edit_[0-9]+$"
    )
)

app.add_handler(
    CallbackQueryHandler(
        edit_field,
        pattern="^edit_field_"
    )
)


# =========================
# EDIT TEXT HANDLER
# =========================

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        save_edit
    )
)


# =========================
# 🔔 REMINDER JOB
# Har kuni 06:00 da tekshiradi
# =========================

app.job_queue.run_daily(
    send_reminders,
    time=time(hour=6, minute=0)
)


# =========================
# RUN BOT
# =========================

app.run_polling()
