import os
import random
import time
import uuid
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, ContextTypes, filters
from pymongo import MongoClient

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["throne_of_shadows"]
countries_col = db["countries"]   # بدون chat_id — عالمية
alliances_col = db["alliances"]   # مع chat_id — داخلية
votes_col = db["votes"]

# ===== قاعدة البيانات =====
def load_country(user_id):
    return countries_col.find_one({"user_id": user_id})

def save_country(country):
    countries_col.update_one(
        {"user_id": country["user_id"]},
        {"$set": country}, upsert=True
    )

def get_country_by_name(name):
    return countries_col.find_one({"اسم": {"$regex": f"^{name}$", "$options": "i"}})

def get_all_countries():
    return list(countries_col.find())

def load_alliance(chat_id, name):
    return alliances_col.find_one({"chat_id": chat_id, "اسم": {"$regex": f"^{name}$", "$options": "i"}})

def save_alliance(alliance):
    alliances_col.update_one(
        {"chat_id": alliance["chat_id"], "اسم": alliance["اسم"]},
        {"$set": alliance}, upsert=True
    )

def get_country_alliance(chat_id, country_name):
    return alliances_col.find_one({"chat_id": chat_id, "أعضاء": country_name})

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

def calc_alliance_power(chat_id, alliance):
    total = 0
    combined_units = {}
    for member_name in alliance.get("أعضاء", []):
        member = get_country_by_name(member_name)
        if member:
            for unit, count in member.get("وحدات", {}).items():
                combined_units[unit] = combined_units.get(unit, 0) + count
            total += calc_power(member.get("وحدات", {}))
    return total, combined_units

# ===== لوحات الأزرار =====
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 دولتي", callback_data="my_country"),
         InlineKeyboardButton("💰 خزينتي", callback_data="treasury")],
        [InlineKeyboardButton("🪖 جيشي", callback_data="my_army"),
         InlineKeyboardButton("📋 مهماتي", callback_data="missions")],
        [InlineKeyboardButton("🛒 الأسواق", callback_data="markets"),
         InlineKeyboardButton("🏆 الترتيب", callback_data="ranking")],
        [InlineKeyboardButton("⚔️ الحرب", callback_data="war_menu"),
         InlineKeyboardButton("🤝 التحالف", callback_data="alliance_menu")],
        [InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data="ideologies"),
         InlineKeyboardButton("🏗️ المباني", callback_data="buildings_info")],
        [InlineKeyboardButton("🏦 البنك", callback_data="bank"),
         InlineKeyboardButton("🗑️ حذف", callback_data="del_self")],
    ])

def action_keyboard(back=None):
    row = []
    if back:
        row.append(InlineKeyboardButton("🔙 رجوع", callback_data=back))
    row.append(InlineKeyboardButton("🗑️ حذف", callback_data="del_self"))
    return InlineKeyboardMarkup([row])

def private_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 كيف تلعب؟", callback_data="how_to_play")],
        [InlineKeyboardButton("⚔️ الأوامر الكاملة", callback_data="all_commands")],
        [InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data="ideologies_private")],
        [InlineKeyboardButton("🏗️ المباني وفوائدها", callback_data="buildings_private")],
        [InlineKeyboardButton("🚀 الأسلحة والوحدات", callback_data="weapons_info")],
        [InlineKeyboardButton("🏦 نظام البنك", callback_data="bank_info")],
        [InlineKeyboardButton("🤝 نظام التحالفات", callback_data="alliance_info")],
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
        [InlineKeyboardButton("⚔️ هجوم فردي", callback_data="how_to_attack")],
        [InlineKeyboardButton("🔥 هجوم تحالف", callback_data="how_to_alliance_attack")],
        [InlineKeyboardButton("🚀 إطلاق صاروخ", callback_data="how_to_missile")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"),
         InlineKeyboardButton("🗑️ حذف", callback_data="del_self")],
    ])

def alliance_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁️ تحالفي", callback_data="my_alliance")],
        [InlineKeyboardButton("⚔️ جيش التحالف", callback_data="alliance_army")],
        [InlineKeyboardButton("💰 إرسال ذهب للتحالف", callback_data="how_to_send_gold")],
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
            f"🌍 *دولتك عالمية!*\n"
            f"نفس الدولة في كل الكروبات!\n\n"
            f"🔥 *مميزات اللعبة:*\n"
            f"• 🪖 أكثر من 30 وحدة عسكرية\n"
            f"• ✈️ سلاح جوي من F-16 حتى B-52\n"
            f"• ☢️ أسلحة نووية مدمرة\n"
            f"• 🤝 تحالفات بجيش مشترك\n"
            f"• 🔥 حروب تحالف ضد تحالف\n"
            f"• 🛡️ دفاع تلقائي جماعي\n"
            f"• 🏦 بنك واستثمارات حتى 200%\n"
            f"• 💰 إرسال ذهب بين الحلفاء\n\n"
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
            f"🌍 *دولتك عالمية — نفس الدولة في كل الكروبات!*\n\n"
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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat_id
    data = query.data

    if data == "del_self":
        try:
            await query.message.delete()
        except:
            pass
        return

    if data == "back_private":
        await query.edit_message_text(
            "🌑 *عرش الظلال* ⚔️\n\n👇 استكشف اللعبة:",
            parse_mode="Markdown", reply_markup=private_menu_keyboard()
        )
        return

    if data == "main_menu":
        await query.edit_message_text(
            "🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )
        return

    back_private_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_private"), InlineKeyboardButton("🗑️ حذف", callback_data="del_self")]])
    back_main_kb = action_keyboard("main_menu")
    back_markets_kb = action_keyboard("markets")
    back_war_kb = action_keyboard("war_menu")
    back_alliance_kb = action_keyboard("alliance_menu")

    if data == "how_to_play":
        await query.edit_message_text(
            "📖 *كيف تلعب عرش الظلال؟*\n━━━━━━━━━━━━━━━\n\n"
            "1️⃣ *أضف البوت لمجموعتك كمشرف*\n\n"
            "2️⃣ *أنشئ دولتك:*\n`انشاء دولة [الاسم]`\n"
            "🌍 دولتك ستظهر في كل الكروبات!\n\n"
            "3️⃣ *اختر أيديولوجيتك:*\n`اختر نظام [شيوعي/رأسمالي/ديكتاتوري/ملكي]`\n\n"
            "4️⃣ *ابنِ اقتصادك:*\n`بناء حقل نفط` 🛢️\n\n"
            "5️⃣ *جهّز جيشك:*\n`اشتري F-16 5` ✈️\n\n"
            "6️⃣ *استثمر في البنك:*\n`استثمار مالي` 🏦\n\n"
            "7️⃣ *هاجم الدول:*\n`هاجم [اسم الدولة]` ⚔️\n\n"
            "8️⃣ *انضم لتحالف:*\n`انضم تحالف [الاسم]` 🤝\n\n"
            "━━━━━━━━━━━━━━━\n🏆 *الهدف:* كن القوة العظمى!",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "all_commands":
        await query.edit_message_text(
            "⚔️ *الأوامر الكاملة*\n━━━━━━━━━━━━━━━\n\n"
            "🏳️ *البداية:*\n"
            "`انشاء دولة [الاسم]`\n"
            "`اختر نظام [الاسم]`\n"
            "`تغيير اسم [الاسم الجديد]`\n\n"
            "📊 *المعلومات:*\n"
            "`دولتي` | `خزينتي` | `مهماتي` | `ترتيب`\n\n"
            "🛒 *الشراء:*\n"
            "`اشتري [الوحدة] [العدد]`\n"
            "`بناء [المبنى]`\n"
            "`اشتري حماية`\n\n"
            "🏦 *البنك:*\n"
            "`استثمار مالي` — يستثمر كل نقودك\n\n"
            "⚔️ *الحرب:*\n"
            "`هاجم [اسم الدولة]`\n"
            "`هجوم تحالف [اسم الدولة/التحالف]`\n"
            "`اطلق صاروخ [النوع] على [الدولة]`\n\n"
            "🤝 *التحالفات (داخل الكروب):*\n"
            "`انشاء تحالف [الاسم]`\n"
            "`انضم تحالف [الاسم]`\n"
            "`جيش تحالفي`\n"
            "`ارسل ذهب [اسم الدولة] [المبلغ]`\n"
            "`اغادر التحالف`\n\n"
            "🕵️ *الاستخبارات:*\n"
            "`جاسوس [اسم الدولة]`",
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
            "🪖 *المشاة:* جندي، مقاتل، قناص، كوماندوز، قوات خاصة، فرقة النخبة\n\n"
            "🚗 *المدرعات:* جيب مسلح، BTR، T-72، T-90، Abrams، Leopard، Merkava، AS-21\n\n"
            "✈️ *الجو:* مسيّرة، Apache، MiG-29، F-16، Su-35، F-22، F-35، B-2، B-52\n\n"
            "🚀 *الصواريخ:* Grad، كروز، Scud، باتريوت، Iskander، Tomahawk، ICBM\n\n"
            "☢️ *النووي:* كيميائي، نووي تكتيكي، قنبلة نووية\n"
            "_⚠️ تحتاج منشأة نووية أولاً_\n\n"
            "━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`"
        )
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_private_kb)
        return

    if data == "bank_info":
        await query.edit_message_text(
            "🏦 *نظام البنك والاستثمار*\n━━━━━━━━━━━━━━━\n\n"
            "💡 *كيف يعمل؟*\n"
            "استثمر كل نقودك دفعة واحدة كل ساعة!\n\n"
            "📌 *الأمر:*\n`استثمار مالي`\n\n"
            "⚡ نسبة الربح: 50% حتى 200% عشوائياً!\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 كلما كان رصيدك أكبر، ربحت أكثر!",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "alliance_info":
        await query.edit_message_text(
            "🤝 *نظام التحالفات*\n━━━━━━━━━━━━━━━\n\n"
            "⚠️ *التحالفات داخل كل كروب منفصلة*\n\n"
            "👑 *إنشاء تحالف:*\n`انشاء تحالف [الاسم]`\n\n"
            "➕ *الانضمام:*\n`انضم تحالف [الاسم]`\n\n"
            "⚔️ *هجوم جماعي:*\n`هجوم تحالف [الهدف]`\n"
            "القائد والجنرالات يصوتون!\n\n"
            "🛡️ *الدفاع تلقائي* عند مهاجمة أي عضو!\n\n"
            "💰 *إرسال ذهب:*\n`ارسل ذهب [اسم الدولة] [المبلغ]`\n\n"
            "🚪 *المغادرة:*\n`اغادر التحالف`",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "my_country":
        country = load_country(user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!\n\nاكتب: `انشاء دولة [الاسم]`", parse_mode="Markdown", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        protection = ""
        if is_protected(country):
            remaining = int((country["حماية حتى"] - time.time()) / 3600)
            protection = f"\n🛡️ محمي لمدة {remaining} ساعة"
        alliance = get_country_alliance(chat_id, country["اسم"])
        alliance_text = f"🤝 التحالف: {alliance['اسم']}" if alliance else "🤝 لا ينتمي لتحالف"
        await query.edit_message_text(
            f"🌑 *{country['اسم']}* 🌑\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 الحاكم: {user.first_name}\n"
            f"🎖️ المستوى: {get_level(country.get('انتصارات', 0))}\n"
            f"🏛️ النظام: {country.get('نظام', 'لم يُختر بعد')}\n"
            f"{alliance_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 الذهب: {country.get('ذهب', 0):,}\n"
            f"🏦 أرباح البنك: {country.get('بنك', 0):,}\n"
            f"📈 الدخل: +{calc_income(country)}/ساعة\n"
            f"⚔️ القوة: {calc_power(country.get('وحدات', {})):,}\n"
            f"🏆 انتصارات: {country.get('انتصارات', 0)}\n"
            f"💀 هزائم: {country.get('خسائر', 0)}"
            f"{protection}",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "my_army":
        country = load_country(user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        units_text = "\n".join(f"  • {u}: {c}" for u, c in country.get("وحدات", {}).items() if c > 0) or "  لا يوجد جيش بعد"
        buildings_text = "\n".join(f"  • {b}" for b in country.get("مباني", [])) or "  لا توجد مباني بعد"
        await query.edit_message_text(
            f"⚔️ *جيش {country['اسم']}* ⚔️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💪 القوة: {calc_power(country.get('وحدات', {})):,}\n\n"
            f"🪖 *الوحدات:*\n{units_text}\n\n"
            f"🏗️ *المباني:*\n{buildings_text}",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "treasury":
        country = load_country(user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        income = calc_income(country)
        last_invest = country.get("آخر استثمار", 0)
        time_left = max(0, 3600 - (time.time() - last_invest))
        invest_status = "✅ جاهز!" if time_left == 0 else f"⏳ بعد {int(time_left/60)} دقيقة"
        await query.edit_message_text(
            f"💰 *خزينة {country['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💎 الذهب: *{country.get('ذهب', 0):,}*\n"
            f"🏦 أرباح البنك: *{country.get('بنك', 0):,}*\n"
            f"📈 الدخل/ساعة: *+{income}*\n"
            f"📊 الدخل اليومي: *+{income * 24}*\n\n"
            f"🏦 حالة الاستثمار: {invest_status}\n"
            f"💡 `استثمار مالي` لاستثمار كل نقودك!",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "bank":
        country = load_country(user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        last_invest = country.get("آخر استثمار", 0)
        time_left = max(0, 3600 - (time.time() - last_invest))
        status = "✅ جاهز للاستثمار!" if time_left == 0 else f"⏳ متاح بعد {int(time_left/60)} دقيقة و{int(time_left%60)} ثانية"
        await query.edit_message_text(
            f"🏦 *بنك {country['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 الذهب المتاح: *{country.get('ذهب', 0):,}*\n"
            f"🏦 إجمالي الأرباح: *{country.get('بنك', 0):,}*\n\n"
            f"📊 *حالة الاستثمار:*\n{status}\n\n"
            f"💡 *الأمر:* `استثمار مالي`\n\n"
            f"⚡ نسبة الربح: 50% حتى 200% عشوائياً!",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "missions":
        country = load_country(user.id)
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
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "ranking":
        all_c = get_all_countries()
        if not all_c:
            await query.edit_message_text("❌ لا توجد دول بعد!", reply_markup=back_main_kb)
            return
        sorted_c = sorted(all_c, key=lambda x: (x.get("انتصارات", 0), calc_power(x.get("وحدات", {}))), reverse=True)
        msg = "🏆 *أقوى دول عرش الظلال* 🌍\n━━━━━━━━━━━━━━━\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, c in enumerate(sorted_c[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            msg += f"{medal} *{c['اسم']}*\n   {get_level(c.get('انتصارات', 0))} | ⚔️{calc_power(c.get('وحدات', {})):,} | 🏆{c.get('انتصارات', 0)}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "markets":
        await query.edit_message_text("🛒 *الأسواق العسكرية*\n\nاختر:", parse_mode="Markdown", reply_markup=markets_keyboard())
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
        country = load_country(user.id)
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
        await query.edit_message_text("🛡️ *تم شراء الحماية!*\n\nأنت محمي لمدة 12 ساعة! 💪", parse_mode="Markdown", reply_markup=back_main_kb)
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
            "⚔️ *الهجوم الفردي*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `هاجم [اسم الدولة]`\n\n"
            "🌍 يمكنك مهاجمة أي دولة في أي كروب!\n\n"
            "⚠️ *ملاحظات:*\n"
            "• لا يمكن مهاجمة الدول المحمية 🛡️\n"
            "• إذا كان المدافع في تحالف يدافع الكل!\n"
            "• الفائز يأخذ 30% من ذهب الخاسر 💰",
            parse_mode="Markdown", reply_markup=back_war_kb
        )
        return

    if data == "how_to_alliance_attack":
        await query.edit_message_text(
            "🔥 *هجوم التحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `هجوم تحالف [الهدف]`\n\n"
            "📌 *آلية التصويت:*\n"
            "• القائد والجنرالات يصوتون ✅ أو ❌\n"
            "• إذا وافق الأغلبية يتم الهجوم\n"
            "• مدة التصويت 5 دقائق\n\n"
            "⚡ *القوة = مجموع جيوش كل الأعضاء*",
            parse_mode="Markdown", reply_markup=back_war_kb
        )
        return

    if data == "how_to_missile":
        await query.edit_message_text(
            "🚀 *إطلاق الصواريخ*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `اطلق صاروخ [النوع] على [اسم الدولة]`\n\n"
            "• الصواريخ العادية تدمر مبنى عشوائي 🏗️\n"
            "• الأسلحة النووية تدمر 80% من الجيش ☢️",
            parse_mode="Markdown", reply_markup=back_war_kb
        )
        return

    if data == "alliance_menu":
        await query.edit_message_text("🤝 *قائمة التحالف*\n\nاختر:", parse_mode="Markdown", reply_markup=alliance_menu_keyboard())
        return

    if data == "my_alliance":
        country = load_country(user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await query.edit_message_text(
                "❌ أنت لست في أي تحالف في هذا الكروب!\n\n"
                "لإنشاء تحالف: `انشاء تحالف [الاسم]`\n"
                "للانضمام: `انضم تحالف [الاسم]`",
                parse_mode="Markdown", reply_markup=back_alliance_kb
            )
            return
        members_text = ""
        total_power = 0
        for m_name in alliance.get("أعضاء", []):
            m = get_country_by_name(m_name)
            if m:
                p = calc_power(m.get("وحدات", {}))
                total_power += p
                role = "👑" if m_name == alliance.get("قائد") else "⭐" if m_name in alliance.get("جنرالات", []) else "🪖"
                members_text += f"  {role} {m_name} — ⚔️{p:,}\n"
        await query.edit_message_text(
            f"🤝 *تحالف {alliance['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👑 القائد: {alliance.get('قائد', 'غير محدد')}\n"
            f"👥 الأعضاء: {len(alliance.get('أعضاء', []))}\n"
            f"⚔️ القوة الإجمالية: {total_power:,}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🪖 *الأعضاء:*\n{members_text}",
            parse_mode="Markdown", reply_markup=back_alliance_kb
        )
        return

    if data == "alliance_army":
        country = load_country(user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await query.edit_message_text("❌ أنت لست في أي تحالف!", reply_markup=back_alliance_kb)
            return
        total_power, combined_units = calc_alliance_power(chat_id, alliance)
        units_text = "\n".join(f"  • {u}: {c:,}" for u, c in combined_units.items() if c > 0) or "  لا يوجد جيش"
        await query.edit_message_text(
            f"⚔️ *جيش تحالف {alliance['اسم']}* ⚔️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💪 القوة الإجمالية: {total_power:,}\n\n"
            f"🪖 *الوحدات المجتمعة:*\n{units_text}",
            parse_mode="Markdown", reply_markup=back_alliance_kb
        )
        return

    if data == "how_to_send_gold":
        await query.edit_message_text(
            "💰 *إرسال ذهب للحلفاء*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `ارسل ذهب [اسم الدولة] [المبلغ]`\n\n"
            "📌 مثال: `ارسل ذهب المملكة 500`\n\n"
            "⚠️ يمكنك الإرسال لأعضاء تحالفك فقط!",
            parse_mode="Markdown", reply_markup=back_alliance_kb
        )
        return

    if data.startswith("vote_yes_") or data.startswith("vote_no_"):
        vote_type = "yes" if data.startswith("vote_yes_") else "no"
        vote_id = data.split("_", 2)[2]
        vote = votes_col.find_one({"vote_id": vote_id})
        if not vote:
            await query.answer("❌ انتهت مدة التصويت!", show_alert=True)
            return
        country = load_country(user.id)
        if not country:
            await query.answer("❌ ليس لديك دولة!", show_alert=True)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance or alliance["اسم"] != vote["alliance"]:
            await query.answer("❌ لست في هذا التحالف!", show_alert=True)
            return
        if country["اسم"] != alliance.get("قائد") and country["اسم"] not in alliance.get("جنرالات", []):
            await query.answer("❌ فقط القائد والجنرالات يصوتون!", show_alert=True)
            return
        if country["اسم"] in vote.get("صوّت", []):
            await query.answer("✅ لقد صوّتت بالفعل!", show_alert=True)
            return
        update_field = "أصوات_نعم" if vote_type == "yes" else "أصوات_لا"
        votes_col.update_one({"vote_id": vote_id}, {
            "$push": {"صوّت": country["اسم"], update_field: country["اسم"]}
        })
        await query.answer(f"✅ تم تسجيل صوتك {'✅' if vote_type == 'yes' else '❌'}!")
        return

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

    if text.startswith("انشاء دولة "):
        parts = text.split(" ", 2)
        country_name = parts[2].strip() if len(parts) > 2 else ""
        if not country_name:
            await reply("❌ اكتب اسم دولتك!\nمثال: `انشاء دولة المملكة الظلامية`")
            return
        if load_country(user.id):
            await reply("❌ لديك دولة بالفعل!", main_menu_keyboard())
            return
        if get_country_by_name(country_name):
            await reply("❌ هذا الاسم مأخوذ!")
            return
        new_country = {
            "user_id": user.id,
            "اسم": country_name,
            "مالك": user.first_name,
            "ذهب": 1000, "بنك": 0, "آخر استثمار": 0,
            "وحدات": {}, "مباني": [],
            "انتصارات": 0, "خسائر": 0,
            "نظام": None, "آخر تحديث": time.time(),
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
            f"💰 الرصيد: 1,000 ذهب\n"
            f"🌍 دولتك عالمية في كل الكروبات!\n\n"
            f"🛡️ *محمي لمدة 24 ساعة!*\n"
            f"⏰ حتى: {protection_end.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"👇 استخدم الأزرار للتنقل:",
            main_menu_keyboard()
        )
        return

    if text.startswith("تغيير اسم "):
        parts = text.split(" ", 2)
        new_name = parts[2].strip() if len(parts) > 2 else ""
        if not new_name:
            await reply("❌ اكتب الاسم الجديد!")
            return
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        if get_country_by_name(new_name):
            await reply("❌ هذا الاسم مأخوذ!")
            return
        old_name = country["اسم"]
        # تحديث الاسم في كل التحالفات
        for alliance in alliances_col.find({"أعضاء": old_name}):
            members = alliance.get("أعضاء", [])
            if old_name in members:
                members[members.index(old_name)] = new_name
            if alliance.get("قائد") == old_name:
                alliance["قائد"] = new_name
            generals = alliance.get("جنرالات", [])
            if old_name in generals:
                generals[generals.index(old_name)] = new_name
            alliance["أعضاء"] = members
            alliance["جنرالات"] = generals
            save_alliance(alliance)
        country["اسم"] = new_name
        save_country(country)
        await reply(f"✅ *تم تغيير اسم دولتك!*\n\n🏳️ الاسم الجديد: *{new_name}*", main_menu_keyboard())
        return

    if text.startswith("اختر نظام "):
        parts = text.split(" ", 2)
        ideology = parts[2].strip() if len(parts) > 2 else ""
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        if ideology not in IDEOLOGIES:
            msg = "❌ الأيديولوجيات:\n\n"
            for name, d in IDEOLOGIES.items():
                msg += f"{d['رمز']} *{name}*\n{d['وصف']}\n\n"
            await reply(msg)
            return
        country["نظام"] = ideology
        save_country(country)
        await reply(f"✅ تم اختيار *{ideology}* {IDEOLOGIES[ideology]['رمز']}\n\n{IDEOLOGIES[ideology]['وصف']}", main_menu_keyboard())
        return

    if text.startswith("اشتري "):
        country = load_country(user.id)
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
        parts = text.split(" ", 1)[1].rsplit(" ", 1)
        if len(parts) != 2:
            await reply("❌ `اشتري [الوحدة] [العدد]`")
            return
        unit_name, count_str = parts[0].strip(), parts[1].strip()
        try:
            count = int(count_str)
            if count <= 0: raise ValueError
        except:
            await reply("❌ العدد يجب أن يكون رقماً موجباً!")
            return
        if unit_name not in UNITS:
            await reply(f"❌ الوحدة `{unit_name}` غير موجودة!", reply_markup=main_menu_keyboard())
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
        if "وحدات" not in country: country["وحدات"] = {}
        country["وحدات"][unit_name] = country["وحدات"].get(unit_name, 0) + count
        save_country(country)
        await reply(f"✅ *تم الشراء!*\n\n🪖 {unit_name} × {count}\n💰 التكلفة: {total_cost:,}\n💰 المتبقي: {country['ذهب']:,}", main_menu_keyboard())
        return

    if text.startswith("بناء "):
        parts = text.split(" ", 1)
        building_name = parts[1].strip() if len(parts) > 1 else ""
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        if building_name not in BUILDINGS:
            await reply(f"❌ المبنى `{building_name}` غير موجود!")
            return
        d = BUILDINGS[building_name]
        if country.get("ذهب", 0) < d["سعر"]:
            await reply(f"❌ لا يوجد ذهب كافٍ!\nالتكلفة: 💰{d['سعر']:,}\nرصيدك: 💰{country.get('ذهب', 0):,}")
            return
        country["ذهب"] -= d["سعر"]
        if "مباني" not in country: country["مباني"] = []
        country["مباني"].append(building_name)
        save_country(country)
        await reply(f"🏗️ *تم البناء!*\n\n🏛️ {building_name}\n📌 {d['وصف']}\n💰 المتبقي: {country['ذهب']:,}", main_menu_keyboard())
        return

    if text == "استثمار مالي":
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        now = time.time()
        time_left = 3600 - (now - country.get("آخر استثمار", 0))
        if time_left > 0:
            await reply(f"⏳ انتظر {int(time_left/60)} دقيقة و{int(time_left%60)} ثانية 🕐")
            return
        amount = country.get("ذهب", 0)
        if amount <= 0:
            await reply("❌ ليس لديك ذهب للاستثمار!")
            return
        rate = random.uniform(0.50, 2.00)
        profit = int(amount * rate)
        country["ذهب"] = profit
        country["بنك"] = country.get("بنك", 0) + (profit - amount)
        country["آخر استثمار"] = now
        save_country(country)
        rate_percent = int(rate * 100)
        emoji = "🚀" if rate_percent >= 150 else "📈" if rate_percent >= 100 else "📊"
        await reply(
            f"🏦 *نتيجة الاستثمار المالي!*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 المبلغ المستثمر: {amount:,}\n"
            f"{emoji} نسبة الربح: *{rate_percent}%*\n"
            f"💎 العائد: *{profit:,} ذهب*\n"
            f"📈 الربح الصافي: *+{profit - amount:,}*\n\n"
            f"💰 رصيدك الآن: {country['ذهب']:,}\n\n"
            f"⏰ الاستثمار القادم بعد ساعة!",
            main_menu_keyboard()
        )
        return

    if text.startswith("هاجم "):
        parts = text.split(" ", 1)
        target_name = parts[1].strip() if len(parts) > 1 else ""
        attacker = load_country(user.id)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        defender = get_country_by_name(target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if defender["user_id"] == user.id:
            await reply("❌ لا يمكنك مهاجمة نفسك! 😂")
            return
        if is_protected(defender):
            remaining = int((defender["حماية حتى"] - time.time()) / 3600)
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} ساعة!")
            return
        attacker = update_resources(attacker)
        defender = update_resources(defender)
        def_alliance = get_country_alliance(chat_id, target_name)
        if def_alliance:
            alliance_power, _ = calc_alliance_power(chat_id, def_alliance)
            defense_power = alliance_power * random.uniform(0.7, 1.3)
            defense_note = f"🛡️ دفاع تحالف *{def_alliance['اسم']}* الجماعي!\nقوة التحالف: {alliance_power:,}"
        else:
            defense_power = calc_power(defender.get("وحدات", {})) * random.uniform(0.7, 1.3)
            defense_note = ""
        attack_power = calc_power(attacker.get("وحدات", {})) * random.uniform(0.7, 1.3)
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
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🏳️ المدافع: *{target_name}*\n"
                f"{defense_note}\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏆 *{attacker['اسم']} انتصر!*\n💰 ذهب مسروق: {stolen_gold:,}\n💀 خسائرك: 20%",
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
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🏳️ المدافع: *{target_name}*\n"
                f"{defense_note}\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🛡️ *{target_name}* صدّ الهجوم!\n💀 خسائرك: 50%\n😂 عودة للتدريب!",
                main_menu_keyboard()
            )
        return

    if text.startswith("هجوم تحالف "):
        parts = text.split(" ", 2)
        target_name = parts[2].strip() if len(parts) > 2 else ""
        attacker_country = load_country(user.id)
        if not attacker_country:
            await reply("❌ ليس لديك دولة!")
            return
        attacker_alliance = get_country_alliance(chat_id, attacker_country["اسم"])
        if not attacker_alliance:
            await reply("❌ أنت لست في أي تحالف في هذا الكروب!")
            return
        if attacker_country["اسم"] != attacker_alliance.get("قائد") and attacker_country["اسم"] not in attacker_alliance.get("جنرالات", []):
            await reply("❌ فقط القائد والجنرالات يمكنهم طلب هجوم التحالف!")
            return
        vote_id = str(uuid.uuid4())[:8]
        vote_doc = {
            "vote_id": vote_id, "chat_id": chat_id,
            "alliance": attacker_alliance["اسم"], "هدف": target_name,
            "طالب": attacker_country["اسم"],
            "أصوات_نعم": [], "أصوات_لا": [], "صوّت": [],
            "انتهى": False, "وقت": time.time()
        }
        votes_col.insert_one(vote_doc)
        leaders = [attacker_alliance.get("قائد", "")] + attacker_alliance.get("جنرالات", [])
        leaders_text = ", ".join(l for l in leaders if l)
        vote_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ موافق", callback_data=f"vote_yes_{vote_id}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"vote_no_{vote_id}")],
            [InlineKeyboardButton("🗑️ حذف", callback_data="del_self")]
        ])
        await reply(
            f"🔥 *طلب هجوم تحالف!*\n━━━━━━━━━━━━━━━\n"
            f"⚔️ التحالف: *{attacker_alliance['اسم']}*\n"
            f"🎯 الهدف: *{target_name}*\n"
            f"📢 طالب الهجوم: *{attacker_country['اسم']}*\n\n"
            f"👑 يصوت: {leaders_text}\n\n"
            f"⏰ مدة التصويت: 5 دقائق\n👇 صوّت الآن:",
            vote_keyboard
        )
        context.job_queue.run_once(
            execute_alliance_attack, 300,
            data={"vote_id": vote_id, "chat_id": chat_id, "target": target_name, "alliance_name": attacker_alliance["اسم"]},
            name=f"vote_{vote_id}"
        )
        return

    if text.startswith("اطلق صاروخ "):
        rest = text.split(" ", 2)[2] if len(text.split(" ", 2)) > 2 else ""
        parts = rest.split(" على ")
        if len(parts) != 2:
            await reply("❌ `اطلق صاروخ [النوع] على [اسم الدولة]`")
            return
        missile_name, target_name = parts[0].strip(), parts[1].strip()
        attacker = load_country(user.id)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        if attacker.get("وحدات", {}).get(missile_name, 0) <= 0:
            await reply(f"❌ ليس لديك *{missile_name}*!")
            return
        defender = get_country_by_name(target_name)
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
            save_country(attacker); save_country(defender)
            await reply(f"☢️ *ضربة نووية!* ☢️\n\n🚀 *{missile_name}* ضرب *{target_name}*!\n💥 80% من جيشهم دُمر!\n💰 مسروق: {stolen_gold:,}", main_menu_keyboard())
        else:
            if defender.get("مباني"):
                destroyed = random.choice(defender["مباني"])
                defender["مباني"].remove(destroyed)
                save_country(attacker); save_country(defender)
                await reply(f"🚀 *ضربة صاروخية!*\n\n🎯 *{missile_name}* ضرب *{target_name}*\n💥 تم تدمير: *{destroyed}*", main_menu_keyboard())
            else:
                save_country(attacker)
                await reply(f"🚀 *ضربة صاروخية!*\n\n🎯 *{missile_name}* ضرب *{target_name}*\n💥 لا توجد مباني!", main_menu_keyboard())
        return

    if text.startswith("انشاء تحالف "):
        parts = text.split(" ", 2)
        alliance_name = parts[2].strip() if len(parts) > 2 else ""
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        if get_country_alliance(chat_id, country["اسم"]):
            await reply("❌ أنت في تحالف بالفعل!")
            return
        if load_alliance(chat_id, alliance_name):
            await reply("❌ هذا الاسم مأخوذ!")
            return
        new_alliance = {
            "chat_id": chat_id, "اسم": alliance_name,
            "قائد": country["اسم"], "جنرالات": [],
            "أعضاء": [country["اسم"]],
        }
        save_alliance(new_alliance)
        await reply(
            f"🤝 *تم إنشاء التحالف!*\n\n"
            f"👑 اسم التحالف: *{alliance_name}*\n"
            f"🏳️ القائد: *{country['اسم']}*\n\n"
            f"للانضمام: `انضم تحالف {alliance_name}`",
            main_menu_keyboard()
        )
        return

    if text.startswith("انضم تحالف "):
        parts = text.split(" ", 2)
        alliance_name = parts[2].strip() if len(parts) > 2 else ""
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        if get_country_alliance(chat_id, country["اسم"]):
            await reply("❌ أنت في تحالف بالفعل!")
            return
        alliance = load_alliance(chat_id, alliance_name)
        if not alliance:
            await reply(f"❌ لا يوجد تحالف باسم `{alliance_name}`!")
            return
        alliance["أعضاء"].append(country["اسم"])
        save_alliance(alliance)
        await reply(
            f"✅ *انضممت لتحالف {alliance_name}!*\n\n"
            f"👑 القائد: *{alliance['قائد']}*\n"
            f"👥 عدد الأعضاء: {len(alliance['أعضاء'])}",
            main_menu_keyboard()
        )
        return

    if text == "اغادر التحالف":
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في أي تحالف!")
            return
        if country["اسم"] == alliance["قائد"] and len(alliance["أعضاء"]) > 1:
            await reply("❌ لا يمكنك المغادرة وأنت القائد!\nنقّل القيادة أولاً.")
            return
        alliance["أعضاء"].remove(country["اسم"])
        if country["اسم"] in alliance.get("جنرالات", []):
            alliance["جنرالات"].remove(country["اسم"])
        if len(alliance["أعضاء"]) == 0:
            alliances_col.delete_one({"chat_id": chat_id, "اسم": alliance["اسم"]})
        else:
            save_alliance(alliance)
        await reply(f"🚪 *غادرت تحالف {alliance['اسم']}!*", main_menu_keyboard())
        return

    if text == "جيش تحالفي":
        country = load_country(user.id)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في أي تحالف!")
            return
        total_power, combined_units = calc_alliance_power(chat_id, alliance)
        units_text = "\n".join(f"  • {u}: {c:,}" for u, c in combined_units.items() if c > 0) or "  لا يوجد جيش"
        await reply(
            f"⚔️ *جيش تحالف {alliance['اسم']}* ⚔️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💪 القوة الإجمالية: {total_power:,}\n\n"
            f"🪖 *الوحدات المجتمعة:*\n{units_text}",
            action_keyboard("main_menu")
        )
        return

    if text.startswith("ارسل ذهب "):
        rest = text.split(" ", 2)[2] if len(text.split(" ", 2)) > 2 else ""
        parts = rest.rsplit(" ", 1)
        if len(parts) != 2:
            await reply("❌ `ارسل ذهب [اسم الدولة] [المبلغ]`")
            return
        target_name, amount_str = parts[0].strip(), parts[1].strip()
        try:
            amount = int(amount_str)
            if amount <= 0: raise ValueError
        except:
            await reply("❌ المبلغ يجب أن يكون رقماً موجباً!")
            return
        my_country = load_country(user.id)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        my_alliance = get_country_alliance(chat_id, my_country["اسم"])
        if not my_alliance:
            await reply("❌ أنت لست في أي تحالف!")
            return
        target = get_country_by_name(target_name)
        if not target:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        target_alliance = get_country_alliance(chat_id, target_name)
        if not target_alliance or target_alliance["اسم"] != my_alliance["اسم"]:
            await reply("❌ يمكنك الإرسال لأعضاء تحالفك فقط!")
            return
        my_country = update_resources(my_country)
        if my_country.get("ذهب", 0) < amount:
            await reply(f"❌ لا يوجد ذهب كافٍ!\nرصيدك: 💰{my_country.get('ذهب', 0):,}")
            return
        my_country["ذهب"] -= amount
        target["ذهب"] = target.get("ذهب", 0) + amount
        save_country(my_country)
        save_country(target)
        await reply(
            f"💰 *تم إرسال الذهب!*\n\nمن: *{my_country['اسم']}*\nإلى: *{target_name}*\nالمبلغ: 💰{amount:,}",
            main_menu_keyboard()
        )
        return

    if text.startswith("جاسوس "):
        parts = text.split(" ", 1)
        target_name = parts[1].strip() if len(parts) > 1 else ""
        my_country = load_country(user.id)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        if "جهاز استخبارات" not in my_country.get("مباني", []):
            await reply("❌ تحتاج *جهاز استخبارات* أولاً!")
            return
        target = get_country_by_name(target_name)
        if not target:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        target = update_resources(target)
        save_country(target)
        units_text = "\n".join(f"  • {u}: {c}" for u, c in target.get("وحدات", {}).items() if c > 0) or "  لا يوجد جيش"
        alliance = get_country_alliance(chat_id, target_name)
        alliance_text = f"🤝 التحالف (هنا): {alliance['اسم']}" if alliance else "🤝 لا ينتمي لتحالف هنا"
        await reply(
            f"🕵️ *تقرير استخباراتي* 🕵️\n━━━━━━━━━━━━━━━\n"
            f"🎯 الهدف: *{target_name}*\n"
            f"💰 الذهب: ~{target.get('ذهب', 0) // 100 * 100:,}\n"
            f"⚔️ القوة: {calc_power(target.get('وحدات', {})):,}\n"
            f"🏆 الانتصارات: {target.get('انتصارات', 0)}\n"
            f"{alliance_text}\n━━━━━━━━━━━━━━━\n"
            f"🪖 *الجيش:*\n{units_text}",
            action_keyboard("main_menu")
        )
        return

async def execute_alliance_attack(context):
    data = context.job.data
    vote_id = data["vote_id"]
    chat_id = data["chat_id"]
    target_name = data["target"]
    alliance_name = data["alliance_name"]
    vote = votes_col.find_one({"vote_id": vote_id})
    if not vote or vote.get("انتهى"):
        return
    votes_col.update_one({"vote_id": vote_id}, {"$set": {"انتهى": True}})
    yes_votes = len(vote.get("أصوات_نعم", []))
    no_votes = len(vote.get("أصوات_لا", []))
    alliance = load_alliance(chat_id, alliance_name)
    if not alliance:
        return
    if yes_votes <= no_votes:
        await context.bot.send_message(chat_id,
            f"❌ *تم رفض هجوم التحالف!*\n\n✅ موافق: {yes_votes}\n❌ رافض: {no_votes}\n\nالأغلبية رفضت الهجوم على *{target_name}*",
            parse_mode="Markdown")
        return
    defender = get_country_by_name(target_name)
    def_alliance = get_country_alliance(chat_id, target_name)
    att_power, _ = calc_alliance_power(chat_id, alliance)
    if def_alliance:
        def_power, _ = calc_alliance_power(chat_id, def_alliance)
        def_note = f"🛡️ دفاع تحالف *{def_alliance['اسم']}*"
    elif defender:
        def_power = calc_power(defender.get("وحدات", {}))
        def_note = ""
    else:
        await context.bot.send_message(chat_id, f"❌ لا توجد دولة باسم *{target_name}*!", parse_mode="Markdown")
        return
    att_roll = att_power * random.uniform(0.7, 1.3)
    def_roll = def_power * random.uniform(0.7, 1.3)
    if att_roll > def_roll:
        total_stolen = 0
        if def_alliance:
            for m_name in def_alliance.get("أعضاء", []):
                m = get_country_by_name(m_name)
                if m:
                    stolen = int(m.get("ذهب", 0) * 0.3)
                    total_stolen += stolen
                    m["ذهب"] = max(0, m.get("ذهب", 0) - stolen)
                    for unit in m.get("وحدات", {}): m["وحدات"][unit] = int(m["وحدات"][unit] * 0.6)
                    save_country(m)
        elif defender:
            total_stolen = int(defender.get("ذهب", 0) * 0.3)
            defender["ذهب"] = max(0, defender.get("ذهب", 0) - total_stolen)
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.6)
            save_country(defender)
        gold_per = total_stolen // max(1, len(alliance.get("أعضاء", [])))
        for m_name in alliance.get("أعضاء", []):
            m = get_country_by_name(m_name)
            if m:
                m["ذهب"] = m.get("ذهب", 0) + gold_per
                m["انتصارات"] = m.get("انتصارات", 0) + 1
                for unit in m.get("وحدات", {}): m["وحدات"][unit] = int(m["وحدات"][unit] * 0.8)
                save_country(m)
        await context.bot.send_message(chat_id,
            f"🔥 *هجوم التحالف نجح!* 🔥\n━━━━━━━━━━━━━━━\n"
            f"⚔️ *{alliance_name}* هاجم *{target_name}*!\n{def_note}\n\n"
            f"🔥 قوة الهجوم: {int(att_roll):,}\n🛡️ قوة الدفاع: {int(def_roll):,}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏆 *{alliance_name} انتصر!*\n💰 إجمالي الذهب المسروق: {total_stolen:,}\n"
            f"💎 نصيب كل عضو: {gold_per:,}\n✅{yes_votes} | ❌{no_votes}",
            parse_mode="Markdown")
    else:
        for m_name in alliance.get("أعضاء", []):
            m = get_country_by_name(m_name)
            if m:
                m["خسائر"] = m.get("خسائر", 0) + 1
                for unit in m.get("وحدات", {}): m["وحدات"][unit] = int(m["وحدات"][unit] * 0.5)
                save_country(m)
        await context.bot.send_message(chat_id,
            f"💀 *هجوم التحالف فشل!* 💀\n━━━━━━━━━━━━━━━\n"
            f"⚔️ *{alliance_name}* هاجم *{target_name}*!\n{def_note}\n\n"
            f"🔥 قوة الهجوم: {int(att_roll):,}\n🛡️ قوة الدفاع: {int(def_roll):,}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"😂 *{target_name}* صدّ الهجوم!\n💀 كل الأعضاء خسروا 50% من جيوشهم!\n✅{yes_votes} | ❌{no_votes}",
            parse_mode="Markdown")

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
    print("✅ عرش الظلال يعمل! 🌍⚔️")
    application.run_polling()
