import os
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, ContextTypes, filters
from pymongo import MongoClient

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")

# ===== قاعدة البيانات =====
client = MongoClient(MONGO_URI)
db = client["throne_of_shadows"]
countries_col = db["countries"]

def load_country(chat_id, user_id):
    return countries_col.find_one({"chat_id": chat_id, "user_id": user_id})

def save_country(country):
    countries_col.update_one(
        {"chat_id": country["chat_id"], "user_id": country["user_id"]},
        {"$set": country},
        upsert=True
    )

def get_country_by_name(chat_id, name):
    return countries_col.find_one({"chat_id": chat_id, "اسم": {"$regex": f"^{name}$", "$options": "i"}})

def get_all_countries(chat_id):
    return list(countries_col.find({"chat_id": chat_id}))

# ===== البيانات =====
UNITS = {
    "جندي": {"قوة": 5, "سعر": 50, "نوع": "مشاة"},
    "مقاتل": {"قوة": 12, "سعر": 150, "نوع": "مشاة"},
    "قناص": {"قوة": 20, "سعر": 300, "نوع": "مشاة"},
    "كوماندوز": {"قوة": 35, "سعر": 500, "نوع": "مشاة"},
    "قوات خاصة": {"قوة": 50, "سعر": 800, "نوع": "مشاة"},
    "فرقة النخبة": {"قوة": 70, "سعر": 1200, "نوع": "مشاة"},
    "جيب مسلح": {"قوة": 5, "سعر": 200, "نوع": "مدرعات"},
    "مدرعة BTR": {"قوة": 15, "سعر": 500, "نوع": "مدرعات"},
    "دبابة T-72": {"قوة": 35, "سعر": 1000, "نوع": "مدرعات"},
    "دبابة T-90": {"قوة": 50, "سعر": 1800, "نوع": "مدرعات"},
    "دبابة Abrams": {"قوة": 70, "سعر": 2500, "نوع": "مدرعات"},
    "دبابة Leopard": {"قوة": 75, "سعر": 2800, "نوع": "مدرعات"},
    "دبابة Merkava": {"قوة": 80, "سعر": 3200, "نوع": "مدرعات"},
    "مدمرة AS-21": {"قوة": 100, "سعر": 5000, "نوع": "مدرعات"},
    "مسيّرة": {"قوة": 10, "سعر": 800, "نوع": "جوي"},
    "Apache": {"قوة": 30, "سعر": 2000, "نوع": "جوي"},
    "MiG-29": {"قوة": 45, "سعر": 3000, "نوع": "جوي"},
    "F-16": {"قوة": 60, "سعر": 4000, "نوع": "جوي"},
    "Su-35": {"قوة": 70, "سعر": 5000, "نوع": "جوي"},
    "F-22": {"قوة": 85, "سعر": 7000, "نوع": "جوي"},
    "F-35": {"قوة": 90, "سعر": 9000, "نوع": "جوي"},
    "B-2 Spirit": {"قوة": 110, "سعر": 15000, "نوع": "جوي"},
    "B-52": {"قوة": 120, "سعر": 18000, "نوع": "جوي"},
    "Grad": {"قوة": 20, "سعر": 600, "نوع": "صواريخ"},
    "كروز": {"قوة": 40, "سعر": 1500, "نوع": "صواريخ"},
    "Scud": {"قوة": 55, "سعر": 2500, "نوع": "صواريخ"},
    "باتريوت": {"قوة": 60, "سعر": 3000, "نوع": "دفاع"},
    "Iskander": {"قوة": 75, "سعر": 4000, "نوع": "صواريخ"},
    "Tomahawk": {"قوة": 85, "سعر": 6000, "نوع": "صواريخ"},
    "ICBM": {"قوة": 100, "سعر": 10000, "نوع": "صواريخ"},
    "كيميائي": {"قوة": 130, "سعر": 20000, "نوع": "نووي"},
    "نووي تكتيكي": {"قوة": 200, "سعر": 50000, "نوع": "نووي"},
    "قنبلة نووية": {"قوة": 500, "سعر": 100000, "نوع": "نووي"},
}

BUILDINGS = {
    "حقل نفط": {"دخل": 200, "سعر": 2000, "وصف": "ينتج 200 ذهب/ساعة 🛢️"},
    "مصنع أسلحة": {"دخل": 150, "سعر": 1500, "وصف": "ينتج 150 ذهب/ساعة 🏭"},
    "أراضي زراعية": {"دخل": 100, "سعر": 1000, "وصف": "ينتج 100 ذهب/ساعة 🌾"},
    "دفاع جوي": {"دخل": 0, "سعر": 3000, "وصف": "يصد 40% من الطائرات 🛡️"},
    "مركز بحوث": {"دخل": 0, "سعر": 4000, "وصف": "يطور قدرات جيشك 🔬"},
    "مستشفى عسكري": {"دخل": 0, "سعر": 2500, "وصف": "يشفي 20% من الجنود 🏥"},
    "جهاز استخبارات": {"دخل": 0, "سعر": 3500, "وصف": "يتيح التجسس على الدول 🕵️"},
    "قاعدة صواريخ": {"دخل": 0, "سعر": 5000, "وصف": "يزيد قوة صواريخك 20% 🚀"},
    "منشأة نووية": {"دخل": 0, "سعر": 30000, "وصف": "تفتح الأسلحة النووية ☢️"},
}

IDEOLOGIES = {
    "شيوعي": {"رمز": "🔴", "وصف": "جيش أقوى +20%\nاقتصاد أبطأ -10%\nمناسب للمهاجمين"},
    "رأسمالي": {"رمز": "🔵", "وصف": "اقتصاد أسرع +20%\nجيش أضعف -10%\nمناسب لبناء الثروة"},
    "ديكتاتوري": {"رمز": "⚫", "وصف": "هجوم أقوى +30%\nالتحالفات صعبة\nمناسب للفاتحين"},
    "ملكي": {"رمز": "🟡", "وصف": "متوازن تماماً\nمزايا دبلوماسية خاصة\nمناسب للجميع"},
}

# ===== دوال مساعدة =====
def calc_income(country):
    return sum(BUILDINGS[b]["دخل"] for b in country.get("مباني", []) if b in BUILDINGS)

def calc_power(units_dict):
    return sum(UNITS[u]["قوة"] * c for u, c in units_dict.items() if u in UNITS)

def update_resources(country):
    now = time.time()
    elapsed = (now - country.get("آخر تحديث", now)) / 3600
    country["ذهب"] = country.get("ذهب", 0) + int(calc_income(country) * elapsed)
    country["آخر تحديث"] = now
    return country

def is_protected(country):
    return time.time() < country.get("حماية حتى", 0)

def get_level(victories):
    if victories >= 30: return "👑 قوة عظمى"
    if victories >= 15: return "⭐⭐ قوة كبرى"
    if victories >= 5: return "⭐ قوة إقليمية"
    return "🪖 دولة ناشئة"

def generate_daily_missions():
    all_missions = [
        {"نص": "⚔️ هاجم دولة واحدة اليوم", "مكافأة": 500},
        {"نص": "🏗️ ابنِ مبنى جديداً", "مكافأة": 300},
        {"نص": "🤝 تحالف مع دولة أخرى", "مكافأة": 200},
        {"نص": "🪖 اشتري 10 وحدات عسكرية", "مكافأة": 400},
        {"نص": "💰 اجمع 2000 ذهب", "مكافأة": 600},
        {"نص": "🕵️ تجسس على دولة أخرى", "مكافأة": 250},
    ]
    return random.sample(all_missions, 3)

# ===== لوحات الأزرار =====
def del_btn(msg_id=None):
    return InlineKeyboardButton("🗑️ حذف", callback_data=f"del_{msg_id}" if msg_id else "del_self")

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 دولتي", callback_data="my_country"),
         InlineKeyboardButton("💰 خزينتي", callback_data="treasury")],
        [InlineKeyboardButton("🪖 جيشي", callback_data="my_army"),
         InlineKeyboardButton("📋 مهماتي", callback_data="missions")],
        [InlineKeyboardButton("🛒 الأسواق", callback_data="markets"),
         InlineKeyboardButton("🏆 الترتيب", callback_data="ranking")],
        [InlineKeyboardButton("⚔️ الحرب", callback_data="war_menu"),
         InlineKeyboardButton("🤝 الدبلوماسية", callback_data="diplomacy_menu")],
        [InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data="ideologies"),
         InlineKeyboardButton("🏗️ المباني", callback_data="buildings_info")],
        [InlineKeyboardButton("🏦 البنك", callback_data="bank"),
         InlineKeyboardButton("🗑️ حذف", callback_data="del_self")],
    ])

def action_keyboard(back=None):
    buttons = []
    row = []
    if back:
        row.append(InlineKeyboardButton("🔙 رجوع", callback_data=back))
    row.append(InlineKeyboardButton("🗑️ حذف", callback_data="del_self"))
    buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def private_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 كيف تلعب؟", callback_data="how_to_play")],
        [InlineKeyboardButton("⚔️ الأوامر الكاملة", callback_data="all_commands")],
        [InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data="ideologies_private")],
        [InlineKeyboardButton("🏗️ المباني وفوائدها", callback_data="buildings_private")],
        [InlineKeyboardButton("🚀 الأسلحة والوحدات", callback_data="weapons_info")],
        [InlineKeyboardButton("🏦 نظام البنك", callback_data="bank_info")],
    ])

def markets_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 المشاة", callback_data="market_infantry"),
         InlineKeyboardButton("🚗 المدرعات", callback_data="market_armor")],
        [InlineKeyboardButton("✈️ سلاح الجو", callback_data="market_air"),
         InlineKeyboardButton("🚀 الصواريخ", callback_data="market_missiles")],
        [InlineKeyboardButton("🏗️ المباني", callback_data="market_buildings"),
         InlineKeyboardButton("🛡️ شراء حماية", callback_data="buy_protection")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"),
         InlineKeyboardButton("🗑️ حذف", callback_data="del_self")],
    ])

def war_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ كيفية الهجوم", callback_data="how_to_attack")],
        [InlineKeyboardButton("🚀 كيفية إطلاق صاروخ", callback_data="how_to_missile")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"),
         InlineKeyboardButton("🗑️ حذف", callback_data="del_self")],
    ])

def diplomacy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 كيفية التحالف", callback_data="how_to_alliance")],
        [InlineKeyboardButton("😈 كيفية الخيانة", callback_data="how_to_betray")],
        [InlineKeyboardButton("💰 كيفية المساعدة", callback_data="how_to_help")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"),
         InlineKeyboardButton("🗑️ حذف", callback_data="del_self")],
    ])

# ===== أوامر البوت =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            f"🌑 *أهلاً {user.first_name}!* 🌑\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"مرحباً بك في *عرش الظلال*\n"
            f"⚔️ *Throne of Shadows* ⚔️\n\n"
            f"🎮 *عن اللعبة:*\n"
            f"لعبة حرب استراتيجية متكاملة!\n"
            f"أنشئ دولتك، ابنِ جيشك، وهاجم الدول\n"
            f"الأخرى لتصبح القوة العظمى! 💪\n\n"
            f"🔥 *مميزات اللعبة:*\n"
            f"• 🪖 أكثر من 30 وحدة عسكرية\n"
            f"• ✈️ سلاح جوي من F-16 حتى B-52\n"
            f"• ☢️ أسلحة نووية مدمرة\n"
            f"• 🤝 تحالفات وحروب مع اللاعبين\n"
            f"• 💰 نظام اقتصادي متكامل\n"
            f"• 🏦 بنك واستثمارات\n"
            f"• 🏛️ 4 أيديولوجيات مختلفة\n"
            f"• 📋 مهمات يومية ومكافآت\n"
            f"• 🛡️ نظام حماية للمبتدئين\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"➕ *أضفني لكروبك واستمتعوا بالحرب!* 🔥\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"👇 استكشف اللعبة:",
            parse_mode="Markdown",
            reply_markup=private_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            f"🌑 *عرش الظلال — Throne of Shadows* 🌑\n\n"
            f"مرحباً بكم في أعظم لعبة حرب! ⚔️\n\n"
            f"🏳️ للبدء اكتب:\n`انشاء دولة [اسم دولتك]`\n\n"
            f"📋 للأوامر اكتب: `مساعدة`\n\n"
            f"👇 أو استخدم الأزرار:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

# ===== معالج الأزرار =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat_id
    data = query.data

    # حذف الرسالة
    if data == "del_self" or data.startswith("del_"):
        try:
            await query.message.delete()
        except:
            pass
        return

    # رجوع للقائمة الخاصة
    if data == "back_private":
        await query.edit_message_text(
            "🌑 *عرش الظلال — Throne of Shadows* ⚔️\n\n👇 استكشف اللعبة:",
            parse_mode="Markdown",
            reply_markup=private_menu_keyboard()
        )
        return

    if data == "main_menu":
        await query.edit_message_text(
            "🌑 *عرش الظلال — Throne of Shadows* 🌑\n\nاختر ما تريد:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    back_private_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_private"), InlineKeyboardButton("🗑️ حذف", callback_data="del_self")]])
    back_main_kb = action_keyboard("main_menu")
    back_markets_kb = action_keyboard("markets")
    back_war_kb = action_keyboard("war_menu")
    back_diplomacy_kb = action_keyboard("diplomacy_menu")

    # ===== قائمة خاصة =====
    if data == "how_to_play":
        await query.edit_message_text(
            "📖 *كيف تلعب عرش الظلال؟*\n━━━━━━━━━━━━━━━\n\n"
            "1️⃣ *أضف البوت لمجموعتك كمشرف*\n\n"
            "2️⃣ *أنشئ دولتك:*\n`انشاء دولة [الاسم]`\n"
            "ستحصل على 1000 ذهب و24 ساعة حماية 🛡️\n\n"
            "3️⃣ *اختر أيديولوجيتك:*\n`اختر نظام [شيوعي/رأسمالي/ديكتاتوري/ملكي]`\n\n"
            "4️⃣ *ابنِ اقتصادك:*\n`بناء حقل نفط` 🛢️\n`بناء مصنع أسلحة` 🏭\n\n"
            "5️⃣ *جهّز جيشك:*\n`اشتري F-16 5` ✈️\n`اشتري دبابة Abrams 10` 🚗\n\n"
            "6️⃣ *استثمر في البنك:*\n`استثمار [المبلغ]` 🏦\n\n"
            "7️⃣ *هاجم الدول:*\n`هاجم [اسم الدولة]` ⚔️\n\n"
            "8️⃣ *تحالف مع الأقوياء:*\n`تحالف مع [اسم الدولة]` 🤝\n\n"
            "━━━━━━━━━━━━━━━\n🏆 *الهدف:* كن القوة العظمى!",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "all_commands":
        await query.edit_message_text(
            "⚔️ *الأوامر الكاملة*\n━━━━━━━━━━━━━━━\n\n"
            "🏳️ *البداية:*\n`انشاء دولة [الاسم]`\n`اختر نظام [الاسم]`\n\n"
            "📊 *المعلومات:*\n`دولتي` — معلومات دولتك\n`خزينتي` — رصيدك\n`مهماتي` — مهماتك اليومية\n`ترتيب` — أقوى الدول\n\n"
            "🛒 *الشراء:*\n`اشتري [الوحدة] [العدد]`\n`بناء [المبنى]`\n`اشتري حماية` — 12 ساعة 💰5000\n\n"
            "🏦 *البنك:*\n`استثمار [المبلغ]` — استثمر ذهبك\n\n"
            "⚔️ *الحرب:*\n`هاجم [اسم الدولة]`\n`اطلق صاروخ [النوع] على [الدولة]`\n\n"
            "🤝 *الدبلوماسية:*\n`تحالف مع [اسم الدولة]`\n`خن [اسم الدولة]`\n`ساعد [اسم الدولة] [مبلغ]`\n\n"
            "🕵️ *الاستخبارات:*\n`جاسوس [اسم الدولة]`",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "ideologies_private":
        msg = "🏛️ *الأيديولوجيات المتاحة*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in IDEOLOGIES.items():
            msg += f"{d['رمز']} *{name}*\n{d['وصف']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n`اختر نظام [الاسم]`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_private_kb)
        return

    if data == "buildings_private":
        msg = "🏗️ *المباني وفوائدها*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in BUILDINGS.items():
            msg += f"• *{name}*\n  {d['وصف']} | 💰{d['سعر']:,}\n\n"
        msg += "━━━━━━━━━━━━━━━\n`بناء [اسم المبنى]`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_private_kb)
        return

    if data == "weapons_info":
        msg = (
            "🚀 *أنواع الأسلحة*\n━━━━━━━━━━━━━━━\n\n"
            "🪖 *المشاة:*\nجندي، مقاتل، قناص، كوماندوز، قوات خاصة، فرقة النخبة\n\n"
            "🚗 *المدرعات:*\nجيب مسلح، BTR، T-72، T-90، Abrams، Leopard، Merkava، AS-21\n\n"
            "✈️ *سلاح الجو:*\nمسيّرة، Apache، MiG-29، F-16، Su-35، F-22، F-35، B-2، B-52\n\n"
            "🚀 *الصواريخ:*\nGrad، كروز، Scud، باتريوت، Iskander، Tomahawk، ICBM\n\n"
            "☢️ *النووي:*\nكيميائي، نووي تكتيكي، قنبلة نووية\n"
            "_⚠️ تحتاج منشأة نووية أولاً_\n\n"
            "━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`"
        )
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_private_kb)
        return

    if data == "bank_info":
        await query.edit_message_text(
            "🏦 *نظام البنك والاستثمار*\n━━━━━━━━━━━━━━━\n\n"
            "💡 *كيف يعمل البنك؟*\n"
            "استثمر ذهبك في البنك كل ساعة\n"
            "وستحصل على نسبة عشوائية تصل لـ 50%!\n\n"
            "📌 *الأمر:*\n`استثمار [المبلغ]`\n\n"
            "📌 *مثال:*\n`استثمار 1000`\n\n"
            "⏰ *يمكنك الاستثمار مرة كل ساعة فقط*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 كلما استثمرت أكثر، ربحت أكثر!",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    # ===== القائمة الرئيسية =====
    if data == "my_country":
        country = load_country(chat_id, user.id)
        if not country:
            await query.edit_message_text(
                "❌ ليس لديك دولة!\n\nاكتب: `انشاء دولة [الاسم]` للبدء",
                parse_mode="Markdown", reply_markup=back_main_kb
            )
            return
        country = update_resources(country)
        save_country(country)
        protection = ""
        if is_protected(country):
            remaining = int((country["حماية حتى"] - time.time()) / 3600)
            protection = f"\n🛡️ محمي لمدة {remaining} ساعة"
        await query.edit_message_text(
            f"🌑 *{country['اسم']}* 🌑\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 الحاكم: {user.first_name}\n"
            f"🎖️ المستوى: {get_level(country.get('انتصارات', 0))}\n"
            f"🏛️ النظام: {country.get('نظام', 'لم يُختر بعد')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 الذهب: {country.get('ذهب', 0):,}\n"
            f"🏦 رصيد البنك: {country.get('بنك', 0):,}\n"
            f"📈 الدخل: +{calc_income(country)}/ساعة\n"
            f"⚔️ القوة: {calc_power(country.get('وحدات', {})):,}\n"
            f"🏆 انتصارات: {country.get('انتصارات', 0)}\n"
            f"💀 هزائم: {country.get('خسائر', 0)}\n"
            f"🤝 تحالفات: {', '.join(country.get('تحالفات', [])) or 'لا يوجد'}"
            f"{protection}",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "my_army":
        country = load_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        units = country.get("وحدات", {})
        buildings = country.get("مباني", [])
        units_text = "\n".join(f"  • {u}: {c}" for u, c in units.items() if c > 0) or "  لا يوجد جيش بعد"
        buildings_text = "\n".join(f"  • {b}" for b in buildings) or "  لا توجد مباني بعد"
        await query.edit_message_text(
            f"⚔️ *جيش {country['اسم']}* ⚔️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💪 القوة الإجمالية: {calc_power(units):,}\n\n"
            f"🪖 *الوحدات:*\n{units_text}\n\n"
            f"🏗️ *المباني:*\n{buildings_text}",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "treasury":
        country = load_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        income = calc_income(country)
        await query.edit_message_text(
            f"💰 *خزينة {country['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💎 الذهب: *{country.get('ذهب', 0):,}*\n"
            f"🏦 رصيد البنك: *{country.get('بنك', 0):,}*\n"
            f"📈 الدخل/ساعة: *+{income}*\n"
            f"📊 الدخل اليومي: *+{income * 24}*\n\n"
            f"💡 استخدم `استثمار [المبلغ]` لتنمية ذهبك!",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "bank":
        country = load_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        last_invest = country.get("آخر استثمار", 0)
        now = time.time()
        time_left = max(0, 3600 - (now - last_invest))
        status = f"✅ جاهز للاستثمار!" if time_left == 0 else f"⏳ متاح بعد {int(time_left/60)} دقيقة"
        await query.edit_message_text(
            f"🏦 *بنك {country['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 الذهب المتاح: *{country.get('ذهب', 0):,}*\n"
            f"🏦 أرباح البنك: *{country.get('بنك', 0):,}*\n\n"
            f"📊 *حالة الاستثمار:*\n{status}\n\n"
            f"💡 *كيف تستثمر؟*\n"
            f"`استثمار [المبلغ]`\n"
            f"مثال: `استثمار 1000`\n\n"
            f"⚡ نسبة الربح: 1% حتى 50% عشوائياً!",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "missions":
        country = load_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        today = datetime.now().date().isoformat()
        if country.get("آخر مهمات") != today:
            country["مهمات"] = generate_daily_missions()
            country["آخر مهمات"] = today
            save_country(country)
        msg = "📋 *مهماتك اليومية*\n━━━━━━━━━━━━━━━\n\n"
        for i, m in enumerate(country.get("مهمات", []), 1):
            status = "✅" if m.get("مكتملة") else "⏳"
            msg += f"{status} {i}. {m['نص']}\n   🏆 مكافأة: 💰{m['مكافأة']}\n\n"
        msg += "💡 أكمل المهمات للحصول على مكافآت!"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "ranking":
        all_c = get_all_countries(chat_id)
        if not all_c:
            await query.edit_message_text("❌ لا توجد دول بعد!", reply_markup=back_main_kb)
            return
        sorted_c = sorted(all_c, key=lambda x: (x.get("انتصارات", 0), calc_power(x.get("وحدات", {}))), reverse=True)
        msg = "🏆 *أقوى دول عرش الظلال* 🏆\n━━━━━━━━━━━━━━━\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, c in enumerate(sorted_c[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            msg += f"{medal} *{c['اسم']}*\n   {get_level(c.get('انتصارات', 0))} | ⚔️{calc_power(c.get('وحدات', {})):,} | 🏆{c.get('انتصارات', 0)}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "markets":
        await query.edit_message_text("🛒 *الأسواق العسكرية*\n\nاختر نوع السلاح:", parse_mode="Markdown", reply_markup=markets_keyboard())
        return

    if data == "market_infantry":
        msg = "🪖 *سوق المشاة*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] == "مشاة":
                msg += f"• *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "market_armor":
        msg = "🚗 *سوق المدرعات*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] == "مدرعات":
                msg += f"• *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "market_air":
        msg = "✈️ *سوق سلاح الجو*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] == "جوي":
                msg += f"• *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "market_missiles":
        msg = "🚀 *سوق الصواريخ*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] in ["صواريخ", "دفاع", "نووي"]:
                icon = "☢️" if d["نوع"] == "نووي" else "🛡️" if d["نوع"] == "دفاع" else "🚀"
                msg += f"{icon} *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "market_buildings":
        msg = "🏗️ *سوق المباني*\n━━━━━━━━━━━━━━━\n`بناء [المبنى]`\n\n"
        for name, d in BUILDINGS.items():
            msg += f"• *{name}*\n  {d['وصف']} | 💰{d['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "buy_protection":
        country = load_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_markets_kb)
            return
        country = update_resources(country)
        if country.get("ذهب", 0) < 5000:
            await query.edit_message_text(f"❌ لا يوجد ذهب كافٍ!\nتحتاج: 💰5,000\nرصيدك: 💰{country.get('ذهب', 0):,}", reply_markup=back_markets_kb)
            return
        country["ذهب"] -= 5000
        country["حماية حتى"] = time.time() + 43200
        save_country(country)
        await query.edit_message_text("🛡️ *تم شراء الحماية!*\n\nأنت محمي لمدة 12 ساعة إضافية 💪", parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "ideologies":
        msg = "🏛️ *الأيديولوجيات*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in IDEOLOGIES.items():
            msg += f"{d['رمز']} *{name}*\n{d['وصف']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n`اختر نظام [الاسم]`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "buildings_info":
        msg = "🏗️ *المباني وفوائدها*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in BUILDINGS.items():
            msg += f"• *{name}*\n  {d['وصف']}\n  💰 {d['سعر']:,}\n\n"
        msg += "━━━━━━━━━━━━━━━\n`بناء [اسم المبنى]`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "war_menu":
        await query.edit_message_text("⚔️ *قائمة الحرب*\n\nاختر:", parse_mode="Markdown", reply_markup=war_keyboard())
        return

    if data == "how_to_attack":
        await query.edit_message_text(
            "⚔️ *كيفية الهجوم*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `هاجم [اسم الدولة]`\n\n"
            "📌 مثال: `هاجم المملكة الظلامية`\n\n"
            "⚠️ *ملاحظات:*\n"
            "• لا يمكن مهاجمة الدول المحمية 🛡️\n"
            "• الفائز يأخذ 30% من ذهب الخاسر 💰\n"
            "• المهاجم الفائز يخسر 20% من جيشه\n"
            "• المهاجم الخاسر يخسر 50% من جيشه",
            parse_mode="Markdown", reply_markup=back_war_kb
        )
        return

    if data == "how_to_missile":
        await query.edit_message_text(
            "🚀 *كيفية إطلاق الصواريخ*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `اطلق صاروخ [النوع] على [اسم الدولة]`\n\n"
            "📌 مثال: `اطلق صاروخ Tomahawk على المملكة`\n\n"
            "⚠️ *ملاحظات:*\n"
            "• الصواريخ العادية تدمر مبنى عشوائي 🏗️\n"
            "• الأسلحة النووية تدمر 80% من الجيش ☢️",
            parse_mode="Markdown", reply_markup=back_war_kb
        )
        return

    if data == "diplomacy_menu":
        await query.edit_message_text("🤝 *قائمة الدبلوماسية*\n\nاختر:", parse_mode="Markdown", reply_markup=diplomacy_keyboard())
        return

    if data == "how_to_alliance":
        await query.edit_message_text(
            "🤝 *كيفية التحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `تحالف مع [اسم الدولة]`\n\n"
            "📌 مثال: `تحالف مع المملكة الظلامية`\n\n"
            "✅ الحلفاء لا يهاجمون بعضهم",
            parse_mode="Markdown", reply_markup=back_diplomacy_kb
        )
        return

    if data == "how_to_betray":
        await query.edit_message_text(
            "😈 *كيفية خيانة التحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `خن [اسم الدولة]`\n\n"
            "📌 مثال: `خن المملكة الظلامية`\n\n"
            "⚠️ احذر من الانتقام! 😂",
            parse_mode="Markdown", reply_markup=back_diplomacy_kb
        )
        return

    if data == "how_to_help":
        await query.edit_message_text(
            "💰 *كيفية إرسال المساعدة*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `ساعد [اسم الدولة] [المبلغ]`\n\n"
            "📌 مثال: `ساعد المملكة الظلامية 500`",
            parse_mode="Markdown", reply_markup=back_diplomacy_kb
        )
        return

# ===== معالج النصوص =====
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.effective_chat.type == "private":
        return

    text = update.message.text.strip()
    user = update.effective_user
    chat_id = update.effective_chat.id

    async def reply(msg, keyboard=None):
        if keyboard is None:
            keyboard = action_keyboard("main_menu")
        return await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    if text in ["مساعدة", "/help"]:
        await reply("🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:", main_menu_keyboard())
        return

    # انشاء دولة
    if text.startswith("انشاء دولة "):
        country_name = text[11:].strip()
        if not country_name:
            await reply("❌ اكتب اسم دولتك!\nمثال: `انشاء دولة المملكة الظلامية`")
            return
        if load_country(chat_id, user.id):
            await reply("❌ لديك دولة بالفعل!", main_menu_keyboard())
            return
        if get_country_by_name(chat_id, country_name):
            await reply("❌ هذا الاسم مأخوذ! اختر اسماً آخر.")
            return

        new_country = {
            "chat_id": chat_id,
            "user_id": user.id,
            "اسم": country_name,
            "مالك": user.first_name,
            "ذهب": 1000,
            "بنك": 0,
            "آخر استثمار": 0,
            "وحدات": {},
            "مباني": [],
            "انتصارات": 0,
            "خسائر": 0,
            "تحالفات": [],
            "نظام": None,
            "آخر تحديث": time.time(),
            "حماية حتى": time.time() + 86400,
            "مهمات": generate_daily_missions(),
            "آخر مهمات": datetime.now().date().isoformat(),
        }
        save_country(new_country)
        protection_end = datetime.now() + timedelta(hours=24)
        await reply(
            f"🌑 *تم إنشاء دولتك بنجاح!* 🌑\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏳️ الدولة: *{country_name}*\n"
            f"👤 الحاكم: {user.first_name}\n"
            f"💰 الرصيد: 1,000 ذهب\n\n"
            f"🛡️ *محمي لمدة 24 ساعة!*\n"
            f"⏰ حتى: {protection_end.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"💡 اكتب `اختر نظام` لاختيار أيديولوجيتك\n\n"
            f"👇 استخدم الأزرار للتنقل:",
            main_menu_keyboard()
        )
        return

    # اختيار النظام
    if text.startswith("اختر نظام "):
        ideology = text[10:].strip()
        country = load_country(chat_id, user.id)
        if not country:
            await reply("❌ ليس لديك دولة! اكتب `انشاء دولة [الاسم]`")
            return
        if ideology not in IDEOLOGIES:
            msg = "❌ الأيديولوجيات المتاحة:\n\n"
            for name, d in IDEOLOGIES.items():
                msg += f"{d['رمز']} *{name}*\n{d['وصف']}\n\n"
            await reply(msg)
            return
        country["نظام"] = ideology
        save_country(country)
        await reply(f"✅ تم اختيار *{ideology}* {IDEOLOGIES[ideology]['رمز']}\n\n{IDEOLOGIES[ideology]['وصف']}", main_menu_keyboard())
        return

    # شراء وحدات
    if text.startswith("اشتري "):
        country = load_country(chat_id, user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)

        if text == "اشتري حماية":
            if country.get("ذهب", 0) < 5000:
                await reply(f"❌ لا يوجد ذهب كافٍ!\nتحتاج: 💰5,000\nرصيدك: 💰{country.get('ذهب', 0):,}")
                return
            country["ذهب"] -= 5000
            country["حماية حتى"] = time.time() + 43200
            save_country(country)
            await reply("🛡️ *تم شراء الحماية!*\nأنت محمي لمدة 12 ساعة! 💪", main_menu_keyboard())
            return

        parts = text[6:].strip().rsplit(" ", 1)
        if len(parts) != 2:
            await reply("❌ `اشتري [الوحدة] [العدد]`\nمثال: `اشتري F-16 5`")
            return
        unit_name, count_str = parts
        try:
            count = int(count_str)
            if count <= 0: raise ValueError
        except:
            await reply("❌ العدد يجب أن يكون رقماً موجباً!")
            return
        if unit_name not in UNITS:
            await reply(f"❌ الوحدة `{unit_name}` غير موجودة!\nاضغط *الأسواق* لرؤية الوحدات 👇", main_menu_keyboard())
            return
        unit_data = UNITS[unit_name]
        if unit_data["نوع"] == "نووي" and "منشأة نووية" not in country.get("مباني", []):
            await reply("❌ تحتاج *منشأة نووية* أولاً! ☢️")
            return
        total_cost = unit_data["سعر"] * count
        if country.get("ذهب", 0) < total_cost:
            await reply(f"❌ لا يوجد ذهب كافٍ!\nالتكلفة: 💰{total_cost:,}\nرصيدك: 💰{country.get('ذهب', 0):,}")
            return
        country["ذهب"] -= total_cost
        if "وحدات" not in country:
            country["وحدات"] = {}
        country["وحدات"][unit_name] = country["وحدات"].get(unit_name, 0) + count
        save_country(country)
        await reply(f"✅ *تم الشراء!*\n\n🪖 {unit_name} × {count}\n💰 التكلفة: {total_cost:,}\n💰 المتبقي: {country['ذهب']:,}", main_menu_keyboard())
        return

    # بناء مبنى
    if text.startswith("بناء "):
        country = load_country(chat_id, user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        building_name = text[5:].strip()
        if building_name not in BUILDINGS:
            await reply(f"❌ المبنى `{building_name}` غير موجود!\nاضغط *المباني* لرؤية المتاح 👇", main_menu_keyboard())
            return
        d = BUILDINGS[building_name]
        if country.get("ذهب", 0) < d["سعر"]:
            await reply(f"❌ لا يوجد ذهب كافٍ!\nالتكلفة: 💰{d['سعر']:,}\nرصيدك: 💰{country.get('ذهب', 0):,}")
            return
        country["ذهب"] -= d["سعر"]
        if "مباني" not in country:
            country["مباني"] = []
        country["مباني"].append(building_name)
        save_country(country)
        await reply(f"🏗️ *تم البناء!*\n\n🏛️ {building_name}\n📌 {d['وصف']}\n💰 المتبقي: {country['ذهب']:,}", main_menu_keyboard())
        return

    # استثمار
    if text.startswith("استثمار "):
        country = load_country(chat_id, user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)

        amount_str = text[8:].strip()
        try:
            amount = int(amount_str)
            if amount <= 0: raise ValueError
        except:
            await reply("❌ اكتب مبلغاً صحيحاً!\nمثال: `استثمار 1000`")
            return

        now = time.time()
        last_invest = country.get("آخر استثمار", 0)
        time_left = 3600 - (now - last_invest)

        if time_left > 0:
            minutes = int(time_left / 60)
            await reply(f"⏳ لا يمكنك الاستثمار الآن!\nانتظر {minutes} دقيقة أخرى 🕐")
            return

        if country.get("ذهب", 0) < amount:
            await reply(f"❌ لا يوجد ذهب كافٍ!\nرصيدك: 💰{country.get('ذهب', 0):,}")
            return

        # نسبة عشوائية 1% إلى 50%
        rate = random.uniform(0.01, 0.50)
        profit = int(amount * rate)

        country["ذهب"] = country.get("ذهب", 0) - amount + amount + profit
        country["بنك"] = country.get("بنك", 0) + profit
        country["آخر استثمار"] = now
        save_country(country)

        rate_percent = int(rate * 100)
        emoji = "🚀" if rate_percent >= 40 else "📈" if rate_percent >= 20 else "📊"

        await reply(
            f"🏦 *نتيجة الاستثمار!*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 المبلغ المستثمر: {amount:,}\n"
            f"{emoji} نسبة الربح: *{rate_percent}%*\n"
            f"💎 الربح: *+{profit:,} ذهب*\n\n"
            f"💰 رصيدك الآن: {country['ذهب']:,}\n"
            f"🏦 إجمالي أرباح البنك: {country['بنك']:,}\n\n"
            f"⏰ يمكنك الاستثمار مجدداً بعد ساعة!",
            main_menu_keyboard()
        )
        return

    # هجوم
    if text.startswith("هاجم "):
        attacker = load_country(chat_id, user.id)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        target_name = text[5:].strip()
        defender = get_country_by_name(chat_id, target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if defender["user_id"] == user.id:
            await reply("❌ لا يمكنك مهاجمة نفسك! 😂")
            return
        if is_protected(defender):
            remaining = int((defender["حماية حتى"] - time.time()) / 3600)
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} ساعة أخرى!")
            return

        attacker = update_resources(attacker)
        defender = update_resources(defender)

        attack_power = calc_power(attacker.get("وحدات", {})) * random.uniform(0.7, 1.3)
        defense_power = calc_power(defender.get("وحدات", {})) * random.uniform(0.7, 1.3)

        if "دفاع جوي" in defender.get("مباني", []):
            air_power = sum(UNITS[u]["قوة"] * c for u, c in attacker.get("وحدات", {}).items() if u in UNITS and UNITS[u]["نوع"] == "جوي")
            attack_power -= air_power * 0.4

        if attacker.get("نظام") == "ديكتاتوري": attack_power *= 1.3
        if attacker.get("نظام") == "شيوعي": attack_power *= 1.2
        if defender.get("نظام") == "شيوعي": defense_power *= 1.2

        if attack_power > defense_power:
            stolen_gold = int(defender.get("ذهب", 0) * 0.3)
            attacker["ذهب"] = attacker.get("ذهب", 0) + stolen_gold
            defender["ذهب"] = max(0, defender.get("ذهب", 0) - stolen_gold)
            attacker["انتصارات"] = attacker.get("انتصارات", 0) + 1
            defender["خسائر"] = defender.get("خسائر", 0) + 1
            for unit in attacker.get("وحدات", {}): attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * 0.8)
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.6)
            save_country(attacker)
            save_country(defender)
            await reply(
                f"⚔️ *نتيجة المعركة* ⚔️\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n"
                f"🏳️ المدافع: *{target_name}*\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n"
                f"🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏆 *{attacker['اسم']} انتصر!*\n"
                f"💰 ذهب مسروق: {stolen_gold:,}\n"
                f"💀 خسائرك: 20% من جيشك",
                main_menu_keyboard()
            )
        else:
            attacker["خسائر"] = attacker.get("خسائر", 0) + 1
            defender["انتصارات"] = defender.get("انتصارات", 0) + 1
            for unit in attacker.get("وحدات", {}): attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * 0.5)
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.85)
            save_country(attacker)
            save_country(defender)
            await reply(
                f"⚔️ *نتيجة المعركة* ⚔️\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n"
                f"🏳️ المدافع: *{target_name}*\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n"
                f"🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🛡️ *{target_name}* صدّ الهجوم!\n"
                f"💀 خسائرك: 50% من جيشك\n"
                f"😂 عودة للتدريب!",
                main_menu_keyboard()
            )
        return

    # إطلاق صاروخ
    if text.startswith("اطلق صاروخ "):
        parts = text[11:].split(" على ")
        if len(parts) != 2:
            await reply("❌ `اطلق صاروخ [النوع] على [اسم الدولة]`")
            return
        missile_name, target_name = parts[0].strip(), parts[1].strip()
        attacker = load_country(chat_id, user.id)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        if attacker.get("وحدات", {}).get(missile_name, 0) <= 0:
            await reply(f"❌ ليس لديك *{missile_name}*! اشتري أولاً.")
            return
        defender = get_country_by_name(chat_id, target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if is_protected(defender):
            remaining = int((defender["حماية حتى"] - time.time()) / 3600)
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} ساعة!")
            return
        missile_data = UNITS[missile_name]
        attacker["وحدات"][missile_name] -= 1
        if missile_data["نوع"] == "نووي":
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.2)
            stolen_gold = int(defender.get("ذهب", 0) * 0.5)
            attacker["ذهب"] = attacker.get("ذهب", 0) + stolen_gold
            defender["ذهب"] = max(0, defender.get("ذهب", 0) - stolen_gold)
            save_country(attacker)
            save_country(defender)
            await reply(f"☢️ *ضربة نووية مدمرة!* ☢️\n\n🚀 *{missile_name}* أُطلق على *{target_name}*!\n💥 80% من جيشهم دُمر!\n💰 ذهب مسروق: {stolen_gold:,}\n\n⚠️ *تحذير: كل الدول ستعلن الحرب عليك!*", main_menu_keyboard())
        else:
            if defender.get("مباني"):
                destroyed = random.choice(defender["مباني"])
                defender["مباني"].remove(destroyed)
                save_country(attacker)
                save_country(defender)
                await reply(f"🚀 *ضربة صاروخية!*\n\n🎯 *{missile_name}* ضرب *{target_name}*\n💥 تم تدمير: *{destroyed}*", main_menu_keyboard())
            else:
                save_country(attacker)
                await reply(f"🚀 *ضربة صاروخية!*\n\n🎯 *{missile_name}* ضرب *{target_name}*\n💥 لا توجد مباني للتدمير!", main_menu_keyboard())
        return

    # تحالف
    if text.startswith("تحالف مع "):
        target_name = text[9:].strip()
        my_country = load_country(chat_id, user.id)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        target = get_country_by_name(chat_id, target_name)
        if not target:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if target_name in my_country.get("تحالفات", []):
            await reply(f"❌ أنت متحالف مع *{target_name}* بالفعل!")
            return
        if "تحالفات" not in my_country: my_country["تحالفات"] = []
        if "تحالفات" not in target: target["تحالفات"] = []
        my_country["تحالفات"].append(target_name)
        if my_country["اسم"] not in target["تحالفات"]:
            target["تحالفات"].append(my_country["اسم"])
        save_country(my_country)
        save_country(target)
        await reply(f"🤝 *تم التحالف!*\n\n*{my_country['اسم']}* 🤝 *{target_name}*\n\nأنتم الآن حلفاء! 💪", main_menu_keyboard())
        return

    # خيانة
    if text.startswith("خن "):
        target_name = text[3:].strip()
        my_country = load_country(chat_id, user.id)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        if target_name not in my_country.get("تحالفات", []):
            await reply(f"❌ أنت لست متحالفاً مع *{target_name}*!")
            return
        my_country["تحالفات"].remove(target_name)
        target = get_country_by_name(chat_id, target_name)
        if target and my_country["اسم"] in target.get("تحالفات", []):
            target["تحالفات"].remove(my_country["اسم"])
            save_country(target)
        save_country(my_country)
        await reply(f"😈 *خيانة التحالف!*\n\n*{my_country['اسم']}* خان *{target_name}*!\n\n⚠️ احذر من الانتقام! 😂", main_menu_keyboard())
        return

    # مساعدة مالية
    if text.startswith("ساعد "):
        parts = text[5:].strip().rsplit(" ", 1)
        if len(parts) != 2:
            await reply("❌ `ساعد [اسم الدولة] [المبلغ]`")
            return
        target_name, amount_str = parts
        try:
            amount = int(amount_str)
            if amount <= 0: raise ValueError
        except:
            await reply("❌ المبلغ يجب أن يكون رقماً موجباً!")
            return
        my_country = load_country(chat_id, user.id)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        my_country = update_resources(my_country)
        if my_country.get("ذهب", 0) < amount:
            await reply(f"❌ لا يوجد ذهب كافٍ! رصيدك: 💰{my_country.get('ذهب', 0):,}")
            return
        target = get_country_by_name(chat_id, target_name)
        if not target:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        my_country["ذهب"] -= amount
        target["ذهب"] = target.get("ذهب", 0) + amount
        save_country(my_country)
        save_country(target)
        await reply(f"💰 *تم إرسال المساعدة!*\n\nمن: *{my_country['اسم']}*\nإلى: *{target_name}*\nالمبلغ: 💰{amount:,}", main_menu_keyboard())
        return

    # تجسس
    if text.startswith("جاسوس "):
        target_name = text[7:].strip()
        my_country = load_country(chat_id, user.id)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        if "جهاز استخبارات" not in my_country.get("مباني", []):
            await reply("❌ تحتاج *جهاز استخبارات* أولاً!\n`بناء جهاز استخبارات`")
            return
        target = get_country_by_name(chat_id, target_name)
        if not target:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        target = update_resources(target)
        save_country(target)
        units_text = "\n".join(f"  • {u}: {c}" for u, c in target.get("وحدات", {}).items() if c > 0) or "  لا يوجد جيش"
        await reply(
            f"🕵️ *تقرير استخباراتي سري* 🕵️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🎯 الهدف: *{target_name}*\n"
            f"💰 الذهب التقريبي: ~{target.get('ذهب', 0) // 100 * 100:,}\n"
            f"⚔️ القوة: {calc_power(target.get('وحدات', {})):,}\n"
            f"🏆 الانتصارات: {target.get('انتصارات', 0)}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🪖 *الجيش:*\n{units_text}",
            main_menu_keyboard()
        )
        return

# ===== تشغيل البوت =====
async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "🌑 تشغيل اللعبة"),
        BotCommand("help", "📋 الأوامر والمساعدة"),
    ])

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ عرش الظلال يعمل مع MongoDB! 🌑⚔️")
    application.run_polling()
