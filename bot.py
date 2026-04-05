import os
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, ContextTypes, filters
from pymongo import MongoClient

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["throne_of_shadows"]
countries_col = db["countries"]
alliances_col = db["alliances"]

# ===== قاعدة البيانات =====
def load_country(chat_id, user_id):
    return countries_col.find_one({"chat_id": chat_id, "user_id": user_id})

def save_country(country):
    countries_col.update_one(
        {"chat_id": country["chat_id"], "user_id": country["user_id"]},
        {"$set": country}, upsert=True
    )

def get_country_by_name(chat_id, name):
    return countries_col.find_one({"chat_id": chat_id, "اسم": {"$regex": f"^{name}$", "$options": "i"}})

def get_all_countries(chat_id):
    return list(countries_col.find({"chat_id": chat_id}))

def load_alliance(chat_id, name):
    return alliances_col.find_one({"chat_id": chat_id, "اسم": {"$regex": f"^{name}$", "$options": "i"}})

def save_alliance(alliance):
    alliances_col.update_one(
        {"chat_id": alliance["chat_id"], "اسم": alliance["اسم"]},
        {"$set": alliance}, upsert=True
    )

def get_alliance_by_member(chat_id, country_name):
    return alliances_col.find_one({"chat_id": chat_id, "اعضاء.اسم": country_name})

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
    "شيوعي": {"رمز": "🔴", "وصف": "جيش أقوى +20%\nاقتصاد أبطأ -10%"},
    "رأسمالي": {"رمز": "🔵", "وصف": "اقتصاد أسرع +20%\nجيش أضعف -10%"},
    "ديكتاتوري": {"رمز": "⚫", "وصف": "هجوم أقوى +30%\nالتحالفات صعبة"},
    "ملكي": {"رمز": "🟡", "وصف": "متوازن تماماً\nمزايا دبلوماسية"},
}

ALLIANCE_RANKS = {
    "قائد": "👑 قائد",
    "جنرال": "⭐⭐⭐ جنرال",
    "عميد": "⭐⭐ عميد",
    "عضو": "🪖 عضو",
}

MISSIONS = [
    {"نص": "هاجم أي دولة", "نوع": "هجوم", "مكافأة": 500},
    {"نص": "ابنِ أي مبنى", "نوع": "بناء", "مكافأة": 300},
    {"نص": "اشتري 5 وحدات", "نوع": "شراء", "مكافأة": 400},
    {"نص": "استثمر في البنك", "نوع": "استثمار", "مكافأة": 250},
    {"نص": "تجسس على دولة", "نوع": "تجسس", "مكافأة": 300},
    {"نص": "اكسب معركة", "نوع": "انتصار", "مكافأة": 600},
]

def calc_income(country):
    return sum(BUILDINGS[b]["دخل"] for b in country.get("مباني", []) if b in BUILDINGS)

def calc_power(units_dict):
    return sum(UNITS[u]["قوة"] * c for u, c in units_dict.items() if u in UNITS)

def update_resources(country):
    now = time.time()
    elapsed = (now - country.get("آخر تحديث", now)) / 3600
    country["ذهب"] = country.get("ذهب", 0) + int(calc_income(country) * elapsed)
    country["آخر تحديث"] = now
    # منحة للاعبين القدامى - إذا لم يحصلوا على الرصيد الجديد
    if not country.get("حصل_على_منحة_5000") and country.get("ذهب", 0) < 5000:
        country["ذهب"] = country.get("ذهب", 0) + 4000
        country["حصل_على_منحة_5000"] = True
    return country

def is_protected(country):
    return time.time() < country.get("حماية حتى", 0)

def get_level(v):
    if v >= 30: return "👑 قوة عظمى"
    if v >= 15: return "⭐⭐ قوة كبرى"
    if v >= 5: return "⭐ قوة إقليمية"
    return "🪖 دولة ناشئة"

def generate_missions():
    return [dict(m, مكتملة=False) for m in random.sample(MISSIONS, 3)]

async def check_missions(country, mission_type, context, amount=1):
    """تحقق من المهام وأعط المكافأة فوراً"""
    missions = country.get("مهمات", [])
    completed_any = False
    total_reward = 0

    for m in missions:
        if not m.get("مكتملة") and m["نوع"] == mission_type:
            m["مكتملة"] = True
            total_reward += m["مكافأة"]
            completed_any = True

    if completed_any:
        country["ذهب"] = country.get("ذهب", 0) + total_reward
        save_country(country)
        try:
            await context.bot.send_message(
                chat_id=country["user_id"],
                text=f"🎉 *مهمة مكتملة!*\n\n"
                     f"✅ أكملت مهمة في لعبة عرش الظلال!\n"
                     f"💰 مكافأتك: *+{total_reward:,} ذهب*\n\n"
                     f"رصيدك الجديد: *{country['ذهب']:,}*",
                parse_mode="Markdown"
            )
        except:
            pass

# ===== لوحات الأزرار =====
def extract_uid(data):
    parts = data.rsplit("_", 1)
    if len(parts) == 2:
        try:
            return parts[0], int(parts[1])
        except:
            pass
    return data, None

def main_menu_keyboard(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 دولتي", callback_data=f"my_country_{uid}"),
         InlineKeyboardButton("💰 خزينتي", callback_data=f"treasury_{uid}")],
        [InlineKeyboardButton("🪖 جيشي", callback_data=f"my_army_{uid}"),
         InlineKeyboardButton("📋 مهماتي", callback_data=f"missions_{uid}")],
        [InlineKeyboardButton("🛒 الأسواق", callback_data=f"markets_{uid}"),
         InlineKeyboardButton("🏆 الترتيب", callback_data=f"ranking_{uid}")],
        [InlineKeyboardButton("⚔️ الحرب", callback_data=f"war_menu_{uid}"),
         InlineKeyboardButton("🤝 التحالفات", callback_data=f"alliance_menu_{uid}")],
        [InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data=f"ideologies_{uid}"),
         InlineKeyboardButton("🏗️ المباني", callback_data=f"buildings_info_{uid}")],
        [InlineKeyboardButton("🏦 البنك", callback_data=f"bank_{uid}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self_{uid}")],
    ])

def action_kb(uid, back=None):
    row = []
    if back:
        row.append(InlineKeyboardButton("🔙 رجوع", callback_data=f"{back}_{uid}"))
    row.append(InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self_{uid}"))
    return InlineKeyboardMarkup([row])

def markets_keyboard(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 المشاة", callback_data=f"market_infantry_{uid}"),
         InlineKeyboardButton("🚗 المدرعات", callback_data=f"market_armor_{uid}")],
        [InlineKeyboardButton("✈️ سلاح الجو", callback_data=f"market_air_{uid}"),
         InlineKeyboardButton("🚀 الصواريخ", callback_data=f"market_missiles_{uid}")],
        [InlineKeyboardButton("🏗️ المباني", callback_data=f"market_buildings_{uid}"),
         InlineKeyboardButton("🛡️ شراء حماية", callback_data=f"buy_protection_{uid}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"main_menu_{uid}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self_{uid}")],
    ])

def alliance_menu_keyboard(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏰 تحالفي", callback_data=f"my_alliance_{uid}")],
        [InlineKeyboardButton("➕ إنشاء تحالف", callback_data=f"create_alliance_info_{uid}")],
        [InlineKeyboardButton("📨 الانضمام لتحالف", callback_data=f"join_alliance_info_{uid}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"main_menu_{uid}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self_{uid}")],
    ])

def private_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 كيف تلعب؟", callback_data="how_to_play_priv")],
        [InlineKeyboardButton("⚔️ الأوامر الكاملة", callback_data="all_commands_priv")],
        [InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data="ideologies_priv")],
        [InlineKeyboardButton("🏗️ المباني وفوائدها", callback_data="buildings_priv")],
        [InlineKeyboardButton("🚀 الأسلحة والوحدات", callback_data="weapons_priv")],
        [InlineKeyboardButton("🏦 نظام البنك", callback_data="bank_priv")],
    ])

# ===== أوامر البوت =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
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
            f"• 🏰 تحالفات منظمة مع رتب\n"
            f"• 💰 نظام اقتصادي متكامل\n"
            f"• 🏦 بنك واستثمارات كل 10 دقائق\n"
            f"• 📋 مهمات يومية ومكافآت فورية\n"
            f"• 🔔 تنبيهات خاصة عند الهجوم\n\n"
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
            reply_markup=main_menu_keyboard(uid)
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        "🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(uid)
    )

# ===== معالج الأزرار =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    data = query.data

    # القائمة الخاصة
    private_actions = ["how_to_play_priv", "all_commands_priv", "ideologies_priv", "buildings_priv", "weapons_priv", "bank_priv", "back_private", "del_priv"]
    if data in private_actions:
        await query.answer()
        back_priv = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_private"), InlineKeyboardButton("🗑️ حذف", callback_data="del_priv")]])
        if data == "del_priv":
            try: await query.message.delete()
            except: pass
            return
        if data == "back_private":
            await query.edit_message_text("🌑 *عرش الظلال* ⚔️\n\n👇 استكشف اللعبة:", parse_mode="Markdown", reply_markup=private_menu_keyboard())
            return
        if data == "how_to_play_priv":
            await query.edit_message_text(
                "📖 *كيف تلعب؟*\n━━━━━━━━━━━━━━━\n\n"
                "1️⃣ أضف البوت لمجموعتك كمشرف\n\n"
                "2️⃣ `انشاء دولة [الاسم]`\n"
                "تحصل على 5000 ذهب و24 ساعة حماية\n\n"
                "3️⃣ `اختر نظام [الاسم]`\n\n"
                "4️⃣ `بناء حقل نفط` لزيادة الدخل\n\n"
                "5️⃣ `اشتري F-16 5` لبناء الجيش\n\n"
                "6️⃣ `استثمار 1000` كل 10 دقائق\n\n"
                "7️⃣ `هاجم [دولة]` لسرقة الذهب\n\n"
                "8️⃣ `انشئ تحالف [الاسم]` للتعاون\n\n"
                "━━━━━━━━━━━━━━━\n🏆 كن القوة العظمى!",
                parse_mode="Markdown", reply_markup=back_priv
            )
            return
        if data == "all_commands_priv":
            await query.edit_message_text(
                "⚔️ *الأوامر الكاملة*\n━━━━━━━━━━━━━━━\n\n"
                "🏳️ *دولتك:*\n`انشاء دولة [الاسم]`\n`اختر نظام [الاسم]`\n\n"
                "🛒 *الشراء:*\n`اشتري [الوحدة] [العدد]`\n`بناء [المبنى]`\n`اشتري حماية`\n\n"
                "🏦 *البنك:*\n`استثمار [المبلغ]` — كل 10 دقائق\n\n"
                "⚔️ *الحرب:*\n`هاجم [اسم الدولة]`\n`اطلق صاروخ [النوع] على [الدولة]`\n\n"
                "🏰 *التحالفات:*\n`انشئ تحالف [الاسم]`\n`انضم لتحالف [الاسم]`\n`غير اسم تحالفي [الاسم الجديد]`\n`رقّي [اسم الدولة] [الرتبة]`\n`طرد [اسم الدولة]`\n`غادر التحالف`\n\n"
                "🤝 *ثنائي:*\n`تحالف مع [دولة]`\n`خن [دولة]`\n`ساعد [دولة] [مبلغ]`\n\n"
                "🕵️ `جاسوس [دولة]`",
                parse_mode="Markdown", reply_markup=back_priv
            )
            return
        if data == "ideologies_priv":
            msg = "🏛️ *الأيديولوجيات*\n━━━━━━━━━━━━━━━\n\n"
            for name, d in IDEOLOGIES.items():
                msg += f"{d['رمز']} *{name}*\n{d['وصف']}\n\n"
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_priv)
            return
        if data == "buildings_priv":
            msg = "🏗️ *المباني*\n━━━━━━━━━━━━━━━\n\n"
            for name, d in BUILDINGS.items():
                msg += f"• *{name}*\n  {d['وصف']} | 💰{d['سعر']:,}\n\n"
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_priv)
            return
        if data == "weapons_priv":
            await query.edit_message_text(
                "🚀 *أنواع الأسلحة*\n━━━━━━━━━━━━━━━\n\n"
                "🪖 جندي، مقاتل، قناص، كوماندوز، قوات خاصة، فرقة النخبة\n\n"
                "🚗 جيب مسلح، BTR، T-72، T-90، Abrams، Leopard، Merkava، AS-21\n\n"
                "✈️ مسيّرة، Apache، MiG-29، F-16، Su-35، F-22، F-35، B-2، B-52\n\n"
                "🚀 Grad، كروز، Scud، باتريوت، Iskander، Tomahawk، ICBM\n\n"
                "☢️ كيميائي، نووي تكتيكي، قنبلة نووية\n"
                "_تحتاج منشأة نووية أولاً_",
                parse_mode="Markdown", reply_markup=back_priv
            )
            return
        if data == "bank_priv":
            await query.edit_message_text(
                "🏦 *نظام البنك*\n━━━━━━━━━━━━━━━\n\n"
                "استثمر ذهبك كل *10 دقائق* فقط!\n"
                "نسبة الربح: 1% حتى 50% عشوائياً 🎲\n\n"
                "`استثمار [المبلغ]`\nمثال: `استثمار 1000`\n\n"
                "💰 كلما استثمرت أكثر، ربحت أكثر!",
                parse_mode="Markdown", reply_markup=back_priv
            )
            return

    # استخراج الـ uid
    action, owner_uid = extract_uid(data)

    if action == "del_self":
        await query.answer()
        try: await query.message.delete()
        except: pass
        return

    if owner_uid and user.id != owner_uid:
        await query.answer("❌ هذه القائمة ليست لك!", show_alert=True)
        return

    await query.answer()
    uid = user.id

    if action == "main_menu":
        await query.edit_message_text("🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:", parse_mode="Markdown", reply_markup=main_menu_keyboard(uid))
        return

    if action == "my_country":
        country = load_country(chat_id, uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!\n\nاكتب: `انشاء دولة [الاسم]`", parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu"))
            return
        country = update_resources(country)
        save_country(country)
        protection = f"\n🛡️ محمي لمدة {int((country['حماية حتى'] - time.time()) / 3600)} ساعة" if is_protected(country) else ""
        alliance = get_alliance_by_member(chat_id, country["اسم"])
        alliance_text = f"🏰 {alliance['اسم']}" if alliance else "لا يوجد"
        await query.edit_message_text(
            f"🌑 *{country['اسم']}* 🌑\n━━━━━━━━━━━━━━━\n"
            f"👤 {user.first_name} | 🎖️ {get_level(country.get('انتصارات', 0))}\n"
            f"🏛️ {country.get('نظام', 'لم يُختر')} | 🏰 {alliance_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 الذهب: {country.get('ذهب', 0):,}\n"
            f"🏦 أرباح البنك: {country.get('بنك', 0):,}\n"
            f"📈 الدخل: +{calc_income(country)}/ساعة\n"
            f"⚔️ القوة: {calc_power(country.get('وحدات', {})):,}\n"
            f"🏆 انتصارات: {country.get('انتصارات', 0)} | 💀 هزائم: {country.get('خسائر', 0)}"
            f"{protection}",
            parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu")
        )
        return

    if action == "my_army":
        country = load_country(chat_id, uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=action_kb(uid, "main_menu"))
            return
        units_text = "\n".join(f"  • {u}: {c}" for u, c in country.get("وحدات", {}).items() if c > 0) or "  لا يوجد جيش بعد"
        buildings_text = "\n".join(f"  • {b}" for b in country.get("مباني", [])) or "  لا توجد مباني بعد"
        await query.edit_message_text(
            f"⚔️ *جيش {country['اسم']}*\n━━━━━━━━━━━━━━━\n"
            f"💪 القوة: {calc_power(country.get('وحدات', {})):,}\n\n"
            f"🪖 *الوحدات:*\n{units_text}\n\n🏗️ *المباني:*\n{buildings_text}",
            parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu")
        )
        return

    if action == "treasury":
        country = load_country(chat_id, uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=action_kb(uid, "main_menu"))
            return
        country = update_resources(country)
        save_country(country)
        income = calc_income(country)
        await query.edit_message_text(
            f"💰 *خزينة {country['اسم']}*\n━━━━━━━━━━━━━━━\n"
            f"💎 الذهب: *{country.get('ذهب', 0):,}*\n"
            f"🏦 أرباح البنك: *{country.get('بنك', 0):,}*\n"
            f"📈 الدخل/ساعة: *+{income}*\n"
            f"📊 الدخل اليومي: *+{income * 24}*",
            parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu")
        )
        return

    if action == "bank":
        country = load_country(chat_id, uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=action_kb(uid, "main_menu"))
            return
        country = update_resources(country)
        save_country(country)
        time_left = max(0, 600 - (time.time() - country.get("آخر استثمار", 0)))
        status = "✅ جاهز للاستثمار!" if time_left == 0 else f"⏳ متاح بعد {int(time_left/60)} دقيقة و{int(time_left%60)} ثانية"
        await query.edit_message_text(
            f"🏦 *بنك {country['اسم']}*\n━━━━━━━━━━━━━━━\n"
            f"💰 الذهب: *{country.get('ذهب', 0):,}*\n"
            f"🏦 إجمالي الأرباح: *{country.get('بنك', 0):,}*\n\n"
            f"📊 *حالة الاستثمار:*\n{status}\n\n"
            f"⚡ نسبة الربح: 1% حتى 50%!\n`استثمار [المبلغ]`",
            parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu")
        )
        return

    if action == "missions":
        country = load_country(chat_id, uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=action_kb(uid, "main_menu"))
            return
        today = datetime.now().date().isoformat()
        if country.get("آخر مهمات") != today:
            country["مهمات"] = generate_missions()
            country["آخر مهمات"] = today
            save_country(country)
        msg = "📋 *مهماتك اليومية*\n━━━━━━━━━━━━━━━\n\n"
        for i, m in enumerate(country.get("مهمات", []), 1):
            status = "✅ مكتملة" if m.get("مكتملة") else "⏳ قيد الانتظار"
            msg += f"{status}\n{i}. *{m['نص']}*\n   🏆 مكافأة: 💰{m['مكافأة']:,}\n\n"
        msg += "💡 المكافأة تصل لخاصك فوراً عند الإنجاز!"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu"))
        return

    if action == "ranking":
        all_c = get_all_countries(chat_id)
        if not all_c:
            await query.edit_message_text("❌ لا توجد دول بعد!", reply_markup=action_kb(uid, "main_menu"))
            return
        sorted_c = sorted(all_c, key=lambda x: (x.get("انتصارات", 0), calc_power(x.get("وحدات", {}))), reverse=True)
        msg = "🏆 *أقوى دول عرش الظلال* 🏆\n━━━━━━━━━━━━━━━\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, c in enumerate(sorted_c[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            msg += f"{medal} *{c['اسم']}*\n   {get_level(c.get('انتصارات', 0))} | ⚔️{calc_power(c.get('وحدات', {})):,} | 🏆{c.get('انتصارات', 0)}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu"))
        return

    if action == "markets":
        await query.edit_message_text("🛒 *الأسواق*\n\nاختر:", parse_mode="Markdown", reply_markup=markets_keyboard(uid))
        return

    if action == "market_infantry":
        msg = "🪖 *سوق المشاة*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] == "مشاة":
                msg += f"• *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "markets"))
        return

    if action == "market_armor":
        msg = "🚗 *سوق المدرعات*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] == "مدرعات":
                msg += f"• *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "markets"))
        return

    if action == "market_air":
        msg = "✈️ *سوق سلاح الجو*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] == "جوي":
                msg += f"• *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "markets"))
        return

    if action == "market_missiles":
        msg = "🚀 *سوق الصواريخ*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] in ["صواريخ", "دفاع", "نووي"]:
                icon = "☢️" if d["نوع"] == "نووي" else "🛡️" if d["نوع"] == "دفاع" else "🚀"
                msg += f"{icon} *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "markets"))
        return

    if action == "market_buildings":
        msg = "🏗️ *سوق المباني*\n━━━━━━━━━━━━━━━\n`بناء [المبنى]`\n\n"
        for name, d in BUILDINGS.items():
            msg += f"• *{name}*\n  {d['وصف']} | 💰{d['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "markets"))
        return

    if action == "buy_protection":
        country = load_country(chat_id, uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=action_kb(uid, "markets"))
            return
        country = update_resources(country)
        if country.get("ذهب", 0) < 5000:
            await query.edit_message_text(f"❌ تحتاج 💰5,000\nرصيدك: 💰{country.get('ذهب', 0):,}", reply_markup=action_kb(uid, "markets"))
            return
        country["ذهب"] -= 5000
        country["حماية حتى"] = time.time() + 43200
        save_country(country)
        await query.edit_message_text("🛡️ *تم شراء الحماية!*\n\nأنت محمي لمدة 12 ساعة! 💪", parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu"))
        return

    if action == "ideologies":
        msg = "🏛️ *الأيديولوجيات*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in IDEOLOGIES.items():
            msg += f"{d['رمز']} *{name}*\n{d['وصف']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n`اختر نظام [الاسم]`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu"))
        return

    if action == "buildings_info":
        msg = "🏗️ *المباني*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in BUILDINGS.items():
            msg += f"• *{name}*\n  {d['وصف']}\n  💰 {d['سعر']:,}\n\n"
        msg += "━━━━━━━━━━━━━━━\n`بناء [اسم المبنى]`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=action_kb(uid, "main_menu"))
        return

    if action == "war_menu":
        await query.edit_message_text(
            "⚔️ *الحرب*\n━━━━━━━━━━━━━━━\n\n"
            "🗡️ *هجوم:*\n`هاجم [اسم الدولة]`\n\n"
            "🚀 *صاروخ:*\n`اطلق صاروخ [النوع] على [الدولة]`\n\n"
            "⚠️ *ملاحظات:*\n"
            "• الفائز يأخذ 30% من ذهب الخاسر\n"
            "• الدول المحمية لا يمكن مهاجمتها\n"
            "• سيتلقى المهاجَم تنبيهاً خاصاً 🔔",
            parse_mode="Markdown",
            reply_markup=action_kb(uid, "main_menu")
        )
        return

    if action == "alliance_menu":
        await query.edit_message_text(
            "🏰 *قائمة التحالفات*\n\nاختر:",
            parse_mode="Markdown",
            reply_markup=alliance_menu_keyboard(uid)
        )
        return

    if action == "create_alliance_info":
        await query.edit_message_text(
            "🏰 *إنشاء تحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب في الكروب:\n`انشئ تحالف [الاسم]`\n\n"
            "📌 مثال:\n`انشئ تحالف تحالف الظلال`\n\n"
            "👑 ستكون القائد تلقائياً\n\n"
            "🎖️ *الرتب المتاحة:*\n"
            "👑 قائد — أعلى سلطة\n"
            "⭐⭐⭐ جنرال\n"
            "⭐⭐ عميد\n"
            "🪖 عضو",
            parse_mode="Markdown",
            reply_markup=action_kb(uid, "alliance_menu")
        )
        return

    if action == "join_alliance_info":
        await query.edit_message_text(
            "📨 *الانضمام لتحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب في الكروب:\n`انضم لتحالف [الاسم]`\n\n"
            "📌 مثال:\n`انضم لتحالف تحالف الظلال`",
            parse_mode="Markdown",
            reply_markup=action_kb(uid, "alliance_menu")
        )
        return

    if action == "my_alliance":
        country = load_country(chat_id, uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=action_kb(uid, "alliance_menu"))
            return
        alliance = get_alliance_by_member(chat_id, country["اسم"])
        if not alliance:
            await query.edit_message_text(
                "❌ أنت لست في تحالف!\n\n"
                "اكتب `انشئ تحالف [الاسم]` لإنشاء تحالف\n"
                "أو `انضم لتحالف [الاسم]` للانضمام",
                reply_markup=action_kb(uid, "alliance_menu")
            )
            return
        members_text = ""
        for m in alliance.get("اعضاء", []):
            rank = ALLIANCE_RANKS.get(m.get("رتبة", "عضو"), "🪖 عضو")
            members_text += f"  {rank}: {m['اسم']}\n"
        await query.edit_message_text(
            f"🏰 *تحالف {alliance['اسم']}*\n━━━━━━━━━━━━━━━\n\n"
            f"👑 القائد: {alliance.get('قائد', 'غير معروف')}\n"
            f"👥 الأعضاء: {len(alliance.get('اعضاء', []))}\n\n"
            f"*قائمة الأعضاء:*\n{members_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"*الأوامر:*\n"
            f"`غير اسم تحالفي [الاسم الجديد]`\n"
            f"`رقّي [اسم الدولة] [الرتبة]`\n"
            f"`طرد [اسم الدولة]`\n"
            f"`غادر التحالف`",
            parse_mode="Markdown",
            reply_markup=action_kb(uid, "alliance_menu")
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
    uid = user.id

    async def reply(msg, keyboard=None):
        if keyboard is None:
            keyboard = action_kb(uid, "main_menu")
        return await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    if text in ["مساعدة", "/help"]:
        await reply("🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:", main_menu_keyboard(uid))
        return

    # انشاء دولة
    if text.startswith("انشاء دولة "):
        country_name = text[11:].strip()
        if not country_name:
            await reply("❌ اكتب اسم دولتك!\nمثال: `انشاء دولة المملكة الظلامية`")
            return
        if load_country(chat_id, uid):
            await reply("❌ لديك دولة بالفعل!", main_menu_keyboard(uid))
            return
        if get_country_by_name(chat_id, country_name):
            await reply("❌ هذا الاسم مأخوذ!")
            return
        new_country = {
            "chat_id": chat_id, "user_id": uid,
            "اسم": country_name, "مالك": user.first_name,
            "ذهب": 5000, "بنك": 0, "آخر استثمار": 0,
            "وحدات": {}, "مباني": [],
            "انتصارات": 0, "خسائر": 0, "تحالفات": [],
            "نظام": None, "آخر تحديث": time.time(),
            "حماية حتى": time.time() + 86400,
            "مهمات": generate_missions(),
            "آخر مهمات": datetime.now().date().isoformat(),
        }
        save_country(new_country)
        protection_end = datetime.now() + timedelta(hours=24)
        await reply(
            f"🌑 *تم إنشاء دولتك!* 🌑\n━━━━━━━━━━━━━━━\n"
            f"🏳️ *{country_name}*\n👤 {user.first_name}\n"
            f"💰 الرصيد: 5,000 ذهب\n\n"
            f"🛡️ *محمي 24 ساعة!*\n⏰ حتى: {protection_end.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"💡 اكتب `اختر نظام` لاختيار أيديولوجيتك\n👇 استخدم الأزرار:",
            main_menu_keyboard(uid)
        )
        return

    # اختيار النظام
    if text.startswith("اختر نظام "):
        ideology = text[10:].strip()
        country = load_country(chat_id, uid)
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
        await reply(f"✅ تم اختيار *{ideology}* {IDEOLOGIES[ideology]['رمز']}", main_menu_keyboard(uid))
        return

    # شراء وحدات
    if text.startswith("اشتري "):
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        if text == "اشتري حماية":
            if country.get("ذهب", 0) < 5000:
                await reply(f"❌ تحتاج 💰5,000 | رصيدك: 💰{country.get('ذهب', 0):,}")
                return
            country["ذهب"] -= 5000
            country["حماية حتى"] = time.time() + 43200
            save_country(country)
            await reply("🛡️ *تم شراء الحماية 12 ساعة!*", main_menu_keyboard(uid))
            return
        parts = text[6:].strip().rsplit(" ", 1)
        if len(parts) != 2:
            await reply("❌ `اشتري [الوحدة] [العدد]`")
            return
        unit_name, count_str = parts
        try:
            count = int(count_str)
            if count <= 0: raise ValueError
        except:
            await reply("❌ العدد يجب أن يكون رقماً موجباً!")
            return
        if unit_name not in UNITS:
            await reply(f"❌ `{unit_name}` غير موجودة!", main_menu_keyboard(uid))
            return
        unit_data = UNITS[unit_name]
        if unit_data["نوع"] == "نووي" and "منشأة نووية" not in country.get("مباني", []):
            await reply("❌ تحتاج *منشأة نووية* أولاً! ☢️")
            return
        total_cost = unit_data["سعر"] * count
        if country.get("ذهب", 0) < total_cost:
            await reply(f"❌ التكلفة: 💰{total_cost:,} | رصيدك: 💰{country.get('ذهب', 0):,}")
            return
        country["ذهب"] -= total_cost
        if "وحدات" not in country: country["وحدات"] = {}
        country["وحدات"][unit_name] = country["وحدات"].get(unit_name, 0) + count
        save_country(country)
        # تحقق من مهمة الشراء
        await check_missions(country, "شراء", context, count)
        await reply(f"✅ *{unit_name} × {count}*\n💰 التكلفة: {total_cost:,} | المتبقي: {country['ذهب']:,}", main_menu_keyboard(uid))
        return

    # بناء
    if text.startswith("بناء "):
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        building_name = text[5:].strip()
        if building_name not in BUILDINGS:
            await reply(f"❌ `{building_name}` غير موجود!", main_menu_keyboard(uid))
            return
        d = BUILDINGS[building_name]
        if country.get("ذهب", 0) < d["سعر"]:
            await reply(f"❌ التكلفة: 💰{d['سعر']:,} | رصيدك: 💰{country.get('ذهب', 0):,}")
            return
        country["ذهب"] -= d["سعر"]
        if "مباني" not in country: country["مباني"] = []
        country["مباني"].append(building_name)
        save_country(country)
        await check_missions(country, "بناء", context)
        await reply(f"🏗️ *{building_name}* تم البناء!\n📌 {d['وصف']}\n💰 المتبقي: {country['ذهب']:,}", main_menu_keyboard(uid))
        return

    # استثمار
    if text.startswith("استثمار "):
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        try:
            amount = int(text[8:].strip())
            if amount <= 0: raise ValueError
        except:
            await reply("❌ مثال: `استثمار 1000`")
            return
        now = time.time()
        time_left = 600 - (now - country.get("آخر استثمار", 0))
        if time_left > 0:
            await reply(f"⏳ انتظر {int(time_left/60)} دقيقة و{int(time_left%60)} ثانية! 🕐")
            return
        if country.get("ذهب", 0) < amount:
            await reply(f"❌ رصيدك: 💰{country.get('ذهب', 0):,}")
            return
        rate = random.uniform(0.01, 0.50)
        profit = int(amount * rate)
        country["ذهب"] = country.get("ذهب", 0) + profit
        country["بنك"] = country.get("بنك", 0) + profit
        country["آخر استثمار"] = now
        save_country(country)
        await check_missions(country, "استثمار", context)
        rate_percent = int(rate * 100)
        emoji = "🚀" if rate_percent >= 40 else "📈" if rate_percent >= 20 else "📊"
        await reply(
            f"🏦 *نتيجة الاستثمار!*\n━━━━━━━━━━━━━━━\n"
            f"💰 المستثمر: {amount:,}\n"
            f"{emoji} الربح: *{rate_percent}%* = *+{profit:,}*\n\n"
            f"💰 رصيدك: {country['ذهب']:,}\n"
            f"⏰ التالي: بعد 10 دقائق",
            main_menu_keyboard(uid)
        )
        return

    # هجوم
    if text.startswith("هاجم "):
        attacker = load_country(chat_id, uid)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        target_name = text[5:].strip()
        defender = get_country_by_name(chat_id, target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if defender["user_id"] == uid:
            await reply("❌ لا يمكنك مهاجمة نفسك!")
            return
        if is_protected(defender):
            remaining = int((defender["حماية حتى"] - time.time()) / 3600)
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} ساعة!")
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

        # تنبيه المدافع
        try:
            await context.bot.send_message(
                chat_id=defender["user_id"],
                text=f"🚨 *تحذير! تعرضت للهجوم!* 🚨\n\n"
                     f"⚔️ *{attacker['اسم']}* هاجم *{defender['اسم']}*!\n"
                     f"🔥 قوة الهجوم: {int(attack_power):,}\n"
                     f"🛡️ قوة دفاعك: {int(defense_power):,}\n\n"
                     f"شاهد النتيجة في الكروب!",
                parse_mode="Markdown"
            )
        except:
            pass

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
            await check_missions(attacker, "هجوم", context)
            await check_missions(attacker, "انتصار", context)
            await reply(
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 *{attacker['اسم']}* 🆚 *{target_name}*\n\n"
                f"🔥 {int(attack_power):,} 🆚 🛡️ {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏆 *{attacker['اسم']} انتصر!*\n"
                f"💰 مسروق: {stolen_gold:,} | 💀 خسائرك: 20%",
                main_menu_keyboard(uid)
            )
        else:
            attacker["خسائر"] = attacker.get("خسائر", 0) + 1
            defender["انتصارات"] = defender.get("انتصارات", 0) + 1
            for unit in attacker.get("وحدات", {}): attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * 0.5)
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.85)
            save_country(attacker)
            save_country(defender)
            await check_missions(attacker, "هجوم", context)
            await reply(
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 *{attacker['اسم']}* 🆚 *{target_name}*\n\n"
                f"🔥 {int(attack_power):,} 🆚 🛡️ {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🛡️ *{target_name}* صدّ الهجوم!\n💀 خسائرك: 50% 😂",
                main_menu_keyboard(uid)
            )
        return

    # إطلاق صاروخ
    if text.startswith("اطلق صاروخ "):
        parts = text[11:].split(" على ")
        if len(parts) != 2:
            await reply("❌ `اطلق صاروخ [النوع] على [الدولة]`")
            return
        missile_name, target_name = parts[0].strip(), parts[1].strip()
        attacker = load_country(chat_id, uid)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        if attacker.get("وحدات", {}).get(missile_name, 0) <= 0:
            await reply(f"❌ ليس لديك *{missile_name}*!")
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

        # تنبيه المدافع
        try:
            await context.bot.send_message(
                chat_id=defender["user_id"],
                text=f"🚨 *هجوم صاروخي!* 🚨\n\n"
                     f"🚀 *{attacker['اسم']}* أطلق *{missile_name}* على دولتك!\n"
                     f"شاهد النتيجة في الكروب!",
                parse_mode="Markdown"
            )
        except:
            pass

        if missile_data["نوع"] == "نووي":
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.2)
            stolen_gold = int(defender.get("ذهب", 0) * 0.5)
            attacker["ذهب"] = attacker.get("ذهب", 0) + stolen_gold
            defender["ذهب"] = max(0, defender.get("ذهب", 0) - stolen_gold)
            save_country(attacker)
            save_country(defender)
            await reply(f"☢️ *ضربة نووية!*\n\n🚀 *{missile_name}* ضرب *{target_name}*!\n💥 80% دُمر! | 💰 مسروق: {stolen_gold:,}\n⚠️ كل الدول ستهاجمك!", main_menu_keyboard(uid))
        else:
            if defender.get("مباني"):
                destroyed = random.choice(defender["مباني"])
                defender["مباني"].remove(destroyed)
                save_country(attacker)
                save_country(defender)
                await reply(f"🚀 *ضربة صاروخية!*\n\n🎯 *{missile_name}* ضرب *{target_name}*\n💥 دُمر: *{destroyed}*", main_menu_keyboard(uid))
            else:
                save_country(attacker)
                await reply(f"🚀 *ضربة صاروخية!*\n\n🎯 *{missile_name}* ضرب *{target_name}*\n💥 لا توجد مباني!", main_menu_keyboard(uid))
        return

    # ===== التحالفات =====
    if text.startswith("انشئ تحالف "):
        alliance_name = text[11:].strip()
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        if get_alliance_by_member(chat_id, country["اسم"]):
            await reply("❌ أنت بالفعل في تحالف! اكتب `غادر التحالف` أولاً")
            return
        if load_alliance(chat_id, alliance_name):
            await reply("❌ هذا الاسم مأخوذ!")
            return
        new_alliance = {
            "chat_id": chat_id,
            "اسم": alliance_name,
            "قائد": country["اسم"],
            "اعضاء": [{"اسم": country["اسم"], "user_id": uid, "رتبة": "قائد"}],
            "تاريخ الإنشاء": datetime.now().isoformat(),
        }
        save_alliance(new_alliance)
        await reply(f"🏰 *تم إنشاء تحالف {alliance_name}!*\n\n👑 أنت القائد الآن!\n\nالأوامر المتاحة:\n`انضم لتحالف [الاسم]` — لدعوة الآخرين\n`رقّي [اسم الدولة] [الرتبة]` — لترقية الأعضاء\n`طرد [اسم الدولة]` — لطرد عضو", main_menu_keyboard(uid))
        return

    if text.startswith("انضم لتحالف "):
        alliance_name = text[12:].strip()
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        if get_alliance_by_member(chat_id, country["اسم"]):
            await reply("❌ أنت بالفعل في تحالف!")
            return
        alliance = load_alliance(chat_id, alliance_name)
        if not alliance:
            await reply(f"❌ لا يوجد تحالف باسم `{alliance_name}`!")
            return
        alliance["اعضاء"].append({"اسم": country["اسم"], "user_id": uid, "رتبة": "عضو"})
        save_alliance(alliance)
        await reply(f"✅ *انضممت لتحالف {alliance_name}!*\n\n🪖 رتبتك: عضو", main_menu_keyboard(uid))
        return

    if text.startswith("غير اسم تحالفي "):
        new_name = text[16:].strip()
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_alliance_by_member(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في تحالف!")
            return
        if alliance.get("قائد") != country["اسم"]:
            await reply("❌ فقط القائد يمكنه تغيير الاسم!")
            return
        if load_alliance(chat_id, new_name):
            await reply("❌ هذا الاسم مأخوذ!")
            return
        old_name = alliance["اسم"]
        alliances_col.update_one(
            {"chat_id": chat_id, "اسم": old_name},
            {"$set": {"اسم": new_name}}
        )
        await reply(f"✅ تم تغيير اسم التحالف من *{old_name}* إلى *{new_name}*!", main_menu_keyboard(uid))
        return

    if text.startswith("رقّي "):
        parts = text[5:].strip().rsplit(" ", 1)
        if len(parts) != 2:
            await reply("❌ `رقّي [اسم الدولة] [الرتبة]`\nالرتب: جنرال، عميد، عضو")
            return
        target_country_name, new_rank = parts
        if new_rank not in ["جنرال", "عميد", "عضو"]:
            await reply("❌ الرتب المتاحة: جنرال، عميد، عضو")
            return
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_alliance_by_member(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في تحالف!")
            return
        member_rank = next((m.get("رتبة") for m in alliance["اعضاء"] if m["اسم"] == country["اسم"]), None)
        if member_rank not in ["قائد", "جنرال"]:
            await reply("❌ فقط القائد والجنرال يمكنهم الترقية!")
            return
        member_found = False
        for m in alliance["اعضاء"]:
            if m["اسم"].lower() == target_country_name.lower():
                m["رتبة"] = new_rank
                member_found = True
                break
        if not member_found:
            await reply(f"❌ `{target_country_name}` ليس في تحالفك!")
            return
        save_alliance(alliance)
        await reply(f"✅ تم ترقية *{target_country_name}* إلى {ALLIANCE_RANKS.get(new_rank, new_rank)}!", main_menu_keyboard(uid))
        return

    if text.startswith("طرد "):
        target_country_name = text[4:].strip()
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_alliance_by_member(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في تحالف!")
            return
        member_rank = next((m.get("رتبة") for m in alliance["اعضاء"] if m["اسم"] == country["اسم"]), None)
        if member_rank not in ["قائد", "جنرال"]:
            await reply("❌ فقط القائد والجنرال يمكنهم الطرد!")
            return
        if target_country_name == country["اسم"]:
            await reply("❌ لا يمكنك طرد نفسك!")
            return
        target_member = next((m for m in alliance["اعضاء"] if m["اسم"].lower() == target_country_name.lower()), None)
        if not target_member:
            await reply(f"❌ `{target_country_name}` ليس في تحالفك!")
            return
        if target_member.get("رتبة") == "قائد":
            await reply("❌ لا يمكن طرد القائد!")
            return
        alliance["اعضاء"] = [m for m in alliance["اعضاء"] if m["اسم"].lower() != target_country_name.lower()]
        save_alliance(alliance)
        # تنبيه المطرود
        try:
            await context.bot.send_message(
                chat_id=target_member["user_id"],
                text=f"⚠️ *تم طردك من التحالف!*\n\n"
                     f"تم طردك من تحالف *{alliance['اسم']}*\n"
                     f"يمكنك الانضمام لتحالف آخر أو إنشاء تحالف جديد.",
                parse_mode="Markdown"
            )
        except:
            pass
        await reply(f"✅ تم طرد *{target_country_name}* من التحالف!", main_menu_keyboard(uid))
        return

    if text == "غادر التحالف":
        country = load_country(chat_id, uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_alliance_by_member(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في تحالف!")
            return
        if alliance.get("قائد") == country["اسم"] and len(alliance["اعضاء"]) > 1:
            await reply("❌ أنت القائد! رقّي شخصاً آخر قائداً أولاً أو أطرد الجميع.")
            return
        if len(alliance["اعضاء"]) <= 1:
            alliances_col.delete_one({"chat_id": chat_id, "اسم": alliance["اسم"]})
            await reply(f"✅ غادرت وتم حذف التحالف *{alliance['اسم']}*", main_menu_keyboard(uid))
        else:
            alliance["اعضاء"] = [m for m in alliance["اعضاء"] if m["اسم"] != country["اسم"]]
            save_alliance(alliance)
            await reply(f"✅ غادرت تحالف *{alliance['اسم']}*", main_menu_keyboard(uid))
        return

    # تحالف ثنائي
    if text.startswith("تحالف مع "):
        target_name = text[9:].strip()
        my_country = load_country(chat_id, uid)
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
        await reply(f"🤝 *{my_country['اسم']}* 🤝 *{target_name}*\n\nأنتم الآن حلفاء! 💪", main_menu_keyboard(uid))
        return

    if text.startswith("خن "):
        target_name = text[3:].strip()
        my_country = load_country(chat_id, uid)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        if target_name not in my_country.get("تحالفات", []):
            await reply(f"❌ لست متحالفاً مع *{target_name}*!")
            return
        my_country["تحالفات"].remove(target_name)
        target = get_country_by_name(chat_id, target_name)
        if target and my_country["اسم"] in target.get("تحالفات", []):
            target["تحالفات"].remove(my_country["اسم"])
            save_country(target)
        save_country(my_country)
        await reply(f"😈 *{my_country['اسم']}* خان *{target_name}*!\n⚠️ احذر من الانتقام!", main_menu_keyboard(uid))
        return

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
        my_country = load_country(chat_id, uid)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        my_country = update_resources(my_country)
        if my_country.get("ذهب", 0) < amount:
            await reply(f"❌ رصيدك: 💰{my_country.get('ذهب', 0):,}")
            return
        target = get_country_by_name(chat_id, target_name)
        if not target:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        my_country["ذهب"] -= amount
        target["ذهب"] = target.get("ذهب", 0) + amount
        save_country(my_country)
        save_country(target)
        await reply(f"💰 أرسلت *{amount:,}* لـ *{target_name}* ✅", main_menu_keyboard(uid))
        return

    if text.startswith("جاسوس "):
        target_name = text[7:].strip()
        my_country = load_country(chat_id, uid)
        if not my_country:
            await reply("❌ ليس لديك دولة!")
            return
        if "جهاز استخبارات" not in my_country.get("مباني", []):
            await reply("❌ تحتاج *جهاز استخبارات* أولاً!")
            return
        target = get_country_by_name(chat_id, target_name)
        if not target:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        target = update_resources(target)
        save_country(target)
        units_text = "\n".join(f"  • {u}: {c}" for u, c in target.get("وحدات", {}).items() if c > 0) or "  لا يوجد جيش"
        await check_missions(my_country, "تجسس", context)
        await reply(
            f"🕵️ *تقرير استخباراتي* 🕵️\n━━━━━━━━━━━━━━━\n"
            f"🎯 *{target_name}*\n"
            f"💰 الذهب: ~{target.get('ذهب', 0) // 100 * 100:,}\n"
            f"⚔️ القوة: {calc_power(target.get('وحدات', {})):,}\n"
            f"🏆 الانتصارات: {target.get('انتصارات', 0)}\n"
            f"━━━━━━━━━━━━━━━\n🪖 *الجيش:*\n{units_text}",
            main_menu_keyboard(uid)
        )
        return

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
    print("✅ عرش الظلال يعمل! 🌑⚔️")
    application.run_polling()
