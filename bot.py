import os
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")

countries = {}

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
    "دفاع جوي": {"دخل": 0, "سعر": 3000, "وصف": "يصد 40% من الطائرات المهاجمة 🛡️"},
    "مركز بحوث": {"دخل": 0, "سعر": 4000, "وصف": "يطور قدرات جيشك العسكرية 🔬"},
    "مستشفى عسكري": {"دخل": 0, "سعر": 2500, "وصف": "يشفي 20% من الجنود بعد المعارك 🏥"},
    "جهاز استخبارات": {"دخل": 0, "سعر": 3500, "وصف": "يتيح التجسس على الدول الأخرى 🕵️"},
    "قاعدة صواريخ": {"دخل": 0, "سعر": 5000, "وصف": "يزيد قوة صواريخك 20% 🚀"},
    "منشأة نووية": {"دخل": 0, "سعر": 30000, "وصف": "تفتح الأسلحة النووية ☢️"},
}

IDEOLOGIES = {
    "شيوعي": {"رمز": "🔴", "وصف": "جيش أقوى +20%\nاقتصاد أبطأ -10%\nمناسب للمهاجمين"},
    "رأسمالي": {"رمز": "🔵", "وصف": "اقتصاد أسرع +20%\nجيش أضعف -10%\nمناسب لبناء الثروة"},
    "ديكتاتوري": {"رمز": "⚫", "وصف": "هجوم أقوى +30%\nالتحالفات صعبة\nمناسب للفاتحين"},
    "ملكي": {"رمز": "🟡", "وصف": "متوازن تماماً\nمزايا دبلوماسية خاصة\nمناسب للجميع"},
}

def get_country(chat_id, user_id):
    return countries.get(chat_id, {}).get(user_id)

def get_country_by_name(chat_id, name):
    for uid, c in countries.get(chat_id, {}).items():
        if c["اسم"].lower() == name.lower():
            return uid, c
    return None, None

def calc_income(country):
    return sum(BUILDINGS[b]["دخل"] for b in country["مباني"] if b in BUILDINGS)

def calc_power(units_dict):
    return sum(UNITS[u]["قوة"] * c for u, c in units_dict.items() if u in UNITS)

def update_resources(country):
    now = time.time()
    elapsed = (now - country["آخر تحديث"]) / 3600
    country["ذهب"] += int(calc_income(country) * elapsed)
    country["آخر تحديث"] = now

def is_protected(country):
    return time.time() < country.get("حماية حتى", 0)

def get_level(victories):
    if victories >= 30: return "👑 قوة عظمى"
    if victories >= 15: return "⭐⭐ قوة كبرى"
    if victories >= 5: return "⭐ قوة إقليمية"
    return "🪖 دولة ناشئة"

def get_name(user):
    return f"[{user.first_name}](tg://user?id={user.id})"

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

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌍 دولتي", callback_data="my_country"),
            InlineKeyboardButton("💰 خزينتي", callback_data="treasury"),
        ],
        [
            InlineKeyboardButton("🪖 جيشي", callback_data="my_army"),
            InlineKeyboardButton("📋 مهماتي", callback_data="missions"),
        ],
        [
            InlineKeyboardButton("🛒 الأسواق", callback_data="markets"),
            InlineKeyboardButton("🏆 الترتيب", callback_data="ranking"),
        ],
        [
            InlineKeyboardButton("⚔️ الحرب", callback_data="war_menu"),
            InlineKeyboardButton("🤝 الدبلوماسية", callback_data="diplomacy_menu"),
        ],
        [
            InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data="ideologies"),
            InlineKeyboardButton("🏗️ المباني", callback_data="buildings_info"),
        ],
    ])

def markets_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪖 المشاة", callback_data="market_infantry"),
            InlineKeyboardButton("🚗 المدرعات", callback_data="market_armor"),
        ],
        [
            InlineKeyboardButton("✈️ سلاح الجو", callback_data="market_air"),
            InlineKeyboardButton("🚀 الصواريخ", callback_data="market_missiles"),
        ],
        [
            InlineKeyboardButton("🏗️ المباني", callback_data="market_buildings"),
            InlineKeyboardButton("🛡️ شراء حماية", callback_data="buy_protection"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ])

def war_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ كيفية الهجوم", callback_data="how_to_attack")],
        [InlineKeyboardButton("🚀 كيفية إطلاق صاروخ", callback_data="how_to_missile")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ])

def diplomacy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 كيفية التحالف", callback_data="how_to_alliance")],
        [InlineKeyboardButton("😈 كيفية الخيانة", callback_data="how_to_betray")],
        [InlineKeyboardButton("💰 كيفية المساعدة", callback_data="how_to_help")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ])

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat_id
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            "🌑 *عرش الظلال — Throne of Shadows* 🌑\n\nاختر ما تريد:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    if data == "my_country":
        country = get_country(chat_id, user.id)
        if not country:
            await query.edit_message_text(
                "❌ ليس لديك دولة!\n\nاكتب: `أنشئ دولة [الاسم]` للبدء",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
            )
            return
        update_resources(country)
        level = get_level(country["انتصارات"])
        income = calc_income(country)
        power = calc_power(country["وحدات"])
        protection = ""
        if is_protected(country):
            remaining = int((country["حماية حتى"] - time.time()) / 3600)
            protection = f"\n🛡️ محمي لمدة {remaining} ساعة"

        await query.edit_message_text(
            f"🌑 *{country['اسم']}* 🌑\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 الحاكم: {user.first_name}\n"
            f"🎖️ المستوى: {level}\n"
            f"🏛️ النظام: {country.get('نظام', 'لم يُختر بعد')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 الذهب: {country['ذهب']:,}\n"
            f"📈 الدخل: +{income}/ساعة\n"
            f"⚔️ القوة العسكرية: {power}\n"
            f"🏆 انتصارات: {country['انتصارات']}\n"
            f"💀 هزائم: {country['خسائر']}\n"
            f"🤝 تحالفات: {', '.join(country['تحالفات']) or 'لا يوجد'}"
            f"{protection}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
        )
        return

    if data == "my_army":
        country = get_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
            return
        units_text = "\n".join(f"  • {u}: {c}" for u, c in country["وحدات"].items() if c > 0) or "  لا يوجد جيش بعد"
        buildings_text = "\n".join(f"  • {b}" for b in country["مباني"]) or "  لا توجد مباني بعد"
        power = calc_power(country["وحدات"])
        await query.edit_message_text(
            f"⚔️ *جيش {country['اسم']}* ⚔️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💪 القوة الإجمالية: {power}\n\n"
            f"🪖 *الوحدات العسكرية:*\n{units_text}\n\n"
            f"🏗️ *المباني:*\n{buildings_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
        )
        return

    if data == "treasury":
        country = get_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
            return
        update_resources(country)
        income = calc_income(country)
        await query.edit_message_text(
            f"💰 *خزينة {country['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💎 الذهب الحالي: *{country['ذهب']:,}*\n"
            f"📈 الدخل/ساعة: *+{income}*\n"
            f"📊 الدخل اليومي: *+{income * 24}*\n\n"
            f"💡 ابنِ المزيد من المباني لزيادة دخلك!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
        )
        return

    if data == "missions":
        country = get_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
            return
        today = datetime.now().date().isoformat()
        if country.get("آخر مهمات") != today:
            country["مهمات"] = generate_daily_missions()
            country["آخر مهمات"] = today
        msg = "📋 *مهماتك اليومية*\n━━━━━━━━━━━━━━━\n\n"
        for i, mission in enumerate(country["مهمات"], 1):
            status = "✅" if mission.get("مكتملة") else "⏳"
            msg += f"{status} {i}. {mission['نص']}\n   🏆 المكافأة: 💰{mission['مكافأة']}\n\n"
        msg += "💡 أكمل المهمات اليومية للحصول على مكافآت!"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
        return

    if data == "ranking":
        if not countries.get(chat_id):
            await query.edit_message_text("❌ لا توجد دول بعد!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
            return
        sorted_c = sorted(countries[chat_id].values(), key=lambda x: (x["انتصارات"], calc_power(x["وحدات"])), reverse=True)
        msg = "🏆 *أقوى دول عرش الظلال* 🏆\n━━━━━━━━━━━━━━━\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, c in enumerate(sorted_c[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            msg += f"{medal} *{c['اسم']}*\n   {get_level(c['انتصارات'])} | ⚔️{calc_power(c['وحدات'])} | 🏆{c['انتصارات']}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
        return

    if data == "markets":
        await query.edit_message_text(
            "🛒 *الأسواق العسكرية*\n\nاختر نوع السلاح:",
            parse_mode="Markdown",
            reply_markup=markets_keyboard()
        )
        return

    if data == "market_infantry":
        msg = "🪖 *سوق المشاة*\n━━━━━━━━━━━━━━━\n"
        msg += "الأمر: `اشتري [الوحدة] [العدد]`\n\n"
        for name, data_u in UNITS.items():
            if data_u["نوع"] == "مشاة":
                msg += f"• *{name}*\n  ⚔️ القوة: {data_u['قوة']} | 💰 السعر: {data_u['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]]))
        return

    if data == "market_armor":
        msg = "🚗 *سوق المدرعات*\n━━━━━━━━━━━━━━━\n"
        msg += "الأمر: `اشتري [الوحدة] [العدد]`\n\n"
        for name, data_u in UNITS.items():
            if data_u["نوع"] == "مدرعات":
                msg += f"• *{name}*\n  ⚔️ القوة: {data_u['قوة']} | 💰 السعر: {data_u['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]]))
        return

    if data == "market_air":
        msg = "✈️ *سوق سلاح الجو*\n━━━━━━━━━━━━━━━\n"
        msg += "الأمر: `اشتري [الوحدة] [العدد]`\n\n"
        for name, data_u in UNITS.items():
            if data_u["نوع"] == "جوي":
                msg += f"• *{name}*\n  ⚔️ القوة: {data_u['قوة']} | 💰 السعر: {data_u['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]]))
        return

    if data == "market_missiles":
        msg = "🚀 *سوق الصواريخ والرؤوس الحربية*\n━━━━━━━━━━━━━━━\n"
        msg += "الأمر: `اشتري [الوحدة] [العدد]`\n\n"
        for name, data_u in UNITS.items():
            if data_u["نوع"] in ["صواريخ", "دفاع", "نووي"]:
                icon = "☢️" if data_u["نوع"] == "نووي" else "🛡️" if data_u["نوع"] == "دفاع" else "🚀"
                msg += f"{icon} *{name}*\n  ⚔️ القوة: {data_u['قوة']} | 💰 السعر: {data_u['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]]))
        return

    if data == "market_buildings":
        msg = "🏗️ *سوق المباني*\n━━━━━━━━━━━━━━━\n"
        msg += "الأمر: `بناء [المبنى]`\n\n"
        for name, data_b in BUILDINGS.items():
            msg += f"• *{name}*\n  {data_b['وصف']} | 💰 {data_b['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]]))
        return

    if data == "buy_protection":
        country = get_country(chat_id, user.id)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]]))
            return
        update_resources(country)
        if country["ذهب"] < 5000:
            await query.edit_message_text(
                f"❌ لا يوجد ذهب كافٍ!\nتحتاج: 💰5,000\nرصيدك: 💰{country['ذهب']:,}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]])
            )
            return
        country["ذهب"] -= 5000
        country["حماية حتى"] = time.time() + 43200
        await query.edit_message_text(
            "🛡️ *تم شراء الحماية!*\n\nأنت محمي لمدة 12 ساعة إضافية 💪",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="markets")]])
        )
        return

    if data == "ideologies":
        msg = "🏛️ *الأيديولوجيات المتاحة*\n━━━━━━━━━━━━━━━\n\n"
        for name, data_i in IDEOLOGIES.items():
            msg += f"{data_i['رمز']} *{name}*\n{data_i['وصف']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "للاختيار اكتب:\n`اختر نظام [الاسم]`\nمثال: `اختر نظام ملكي`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
        return

    if data == "buildings_info":
        msg = "🏗️ *المباني وفوائدها*\n━━━━━━━━━━━━━━━\n\n"
        for name, data_b in BUILDINGS.items():
            msg += f"• *{name}*\n  {data_b['وصف']}\n  💰 التكلفة: {data_b['سعر']:,}\n\n"
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "للبناء اكتب:\n`بناء [اسم المبنى]`\nمثال: `بناء حقل نفط`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
        return

    if data == "war_menu":
        await query.edit_message_text(
            "⚔️ *قائمة الحرب*\n\nاختر:",
            parse_mode="Markdown",
            reply_markup=war_keyboard()
        )
        return

    if data == "how_to_attack":
        await query.edit_message_text(
            "⚔️ *كيفية الهجوم*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب:\n`هاجم [اسم الدولة]`\n\n"
            "📌 مثال:\n`هاجم المملكة الظلامية`\n\n"
            "⚠️ *ملاحظات:*\n"
            "• لا يمكن مهاجمة الدول المحمية\n"
            "• الفائز يأخذ 30% من ذهب الخاسر\n"
            "• المهاجم الفائز يخسر 20% من جيشه\n"
            "• المهاجم الخاسر يخسر 50% من جيشه",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="war_menu")]])
        )
        return

    if data == "how_to_missile":
        await query.edit_message_text(
            "🚀 *كيفية إطلاق الصواريخ*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب:\n`اطلق صاروخ [النوع] على [اسم الدولة]`\n\n"
            "📌 مثال:\n`اطلق صاروخ Tomahawk على المملكة`\n\n"
            "⚠️ *ملاحظات:*\n"
            "• الصواريخ العادية تدمر مبنى عشوائي\n"
            "• الأسلحة النووية تدمر 80% من الجيش\n"
            "• تحتاج منشأة نووية للأسلحة النووية ☢️",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="war_menu")]])
        )
        return

    if data == "diplomacy_menu":
        await query.edit_message_text(
            "🤝 *قائمة الدبلوماسية*\n\nاختر:",
            parse_mode="Markdown",
            reply_markup=diplomacy_keyboard()
        )
        return

    if data == "how_to_alliance":
        await query.edit_message_text(
            "🤝 *كيفية التحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب:\n`تحالف مع [اسم الدولة]`\n\n"
            "📌 مثال:\n`تحالف مع المملكة الظلامية`\n\n"
            "✅ الحلفاء لا يهاجمون بعضهم",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="diplomacy_menu")]])
        )
        return

    if data == "how_to_betray":
        await query.edit_message_text(
            "😈 *كيفية خيانة التحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب:\n`خن [اسم الدولة]`\n\n"
            "📌 مثال:\n`خن المملكة الظلامية`\n\n"
            "⚠️ احذر من الانتقام! 😂",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="diplomacy_menu")]])
        )
        return

    if data == "how_to_help":
        await query.edit_message_text(
            "💰 *كيفية إرسال المساعدة*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب:\n`ساعد [اسم الدولة] [المبلغ]`\n\n"
            "📌 مثال:\n`ساعد المملكة الظلامية 500`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="diplomacy_menu")]])
        )
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "⚠️ هذه اللعبة تعمل في المجموعات فقط!\nأضفني لمجموعة وأعطني صلاحية مشرف 🎮"
        )
        return

    text = update.message.text.strip()
    user = update.effective_user
    chat_id = update.effective_chat.id

    # مساعدة - مع أزرار
    if text in ["مساعدة", "/start", "/help"]:
        await update.message.reply_text(
            "🌑 *عرش الظلال — Throne of Shadows* 🌑\n\n"
            "مرحباً بك في أعظم لعبة حرب! ⚔️\n\n"
            "🏳️ للبدء اكتب:\n`أنشئ دولة [اسم دولتك]`\n\n"
            "ثم استخدم الأزرار أدناه للتنقل 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # إنشاء دولة
    if text.startswith("أنشئ دولة "):
        country_name = text[9:].strip()
        if not country_name:
            await update.message.reply_text("❌ اكتب اسم دولتك!\nمثال: `أنشئ دولة المملكة الظلامية`", parse_mode="Markdown")
            return
        if chat_id not in countries:
            countries[chat_id] = {}
        if user.id in countries[chat_id]:
            await update.message.reply_text("❌ لديك دولة بالفعل!\n\nاضغط على *دولتي* لرؤيتها 👇", parse_mode="Markdown", reply_markup=main_menu_keyboard())
            return
        for uid, c in countries[chat_id].items():
            if c["اسم"].lower() == country_name.lower():
                await update.message.reply_text("❌ هذا الاسم مأخوذ! اختر اسماً آخر.")
                return

        countries[chat_id][user.id] = {
            "اسم": country_name,
            "مالك": user.first_name,
            "مالك_id": user.id,
            "ذهب": 1000,
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
        protection_end = datetime.now() + timedelta(hours=24)
        await update.message.reply_text(
            f"🌑 *تم إنشاء دولتك بنجاح!* 🌑\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏳️ اسم الدولة: *{country_name}*\n"
            f"👤 الحاكم: {user.first_name}\n"
            f"💰 الرصيد الابتدائي: 1,000 ذهب\n\n"
            f"🛡️ *أنت محمي من أي هجوم لمدة 24 ساعة!*\n"
            f"⏰ الحماية تنتهي: {protection_end.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"💡 استغل الوقت لبناء جيشك واقتصادك!\n\n"
            f"👇 استخدم الأزرار للتنقل:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # اختيار النظام
    if text.startswith("اختر نظام "):
        ideology = text[10:].strip()
        country = get_country(chat_id, user.id)
        if not country:
            await update.message.reply_text("❌ ليس لديك دولة! اكتب `أنشئ دولة [الاسم]`", parse_mode="Markdown")
            return
        if ideology not in IDEOLOGIES:
            msg = "❌ الأيديولوجيات المتاحة:\n\n"
            for name, data_i in IDEOLOGIES.items():
                msg += f"{data_i['رمز']} *{name}*\n{data_i['وصف']}\n\n"
            msg += "مثال: `اختر نظام ملكي`"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return
        country["نظام"] = ideology
        await update.message.reply_text(
            f"✅ تم اختيار النظام *{ideology}* {IDEOLOGIES[ideology]['رمز']}\n\n{IDEOLOGIES[ideology]['وصف']}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # شراء وحدات
    if text.startswith("اشتري "):
        country = get_country(chat_id, user.id)
        if not country:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return
        update_resources(country)

        parts = text[6:].strip().rsplit(" ", 1)
        if len(parts) != 2:
            await update.message.reply_text("❌ الأمر الصحيح:\n`اشتري [الوحدة] [العدد]`\nمثال: `اشتري F-16 5`", parse_mode="Markdown")
            return

        unit_name, count_str = parts
        try:
            count = int(count_str)
            if count <= 0: raise ValueError
        except:
            await update.message.reply_text("❌ العدد يجب أن يكون رقماً موجباً!")
            return

        if unit_name not in UNITS:
            await update.message.reply_text(
                f"❌ الوحدة `{unit_name}` غير موجودة!\n\nاضغط على *الأسواق* لرؤية الوحدات المتاحة 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
            return

        unit_data = UNITS[unit_name]
        if unit_data["نوع"] == "نووي" and "منشأة نووية" not in country["مباني"]:
            await update.message.reply_text("❌ تحتاج بناء *منشأة نووية* أولاً! ☢️", parse_mode="Markdown")
            return

        total_cost = unit_data["سعر"] * count
        if country["ذهب"] < total_cost:
            await update.message.reply_text(
                f"❌ لا يوجد ذهب كافٍ!\n"
                f"التكلفة: 💰{total_cost:,}\n"
                f"رصيدك: 💰{country['ذهب']:,}"
            )
            return

        country["ذهب"] -= total_cost
        country["وحدات"][unit_name] = country["وحدات"].get(unit_name, 0) + count
        await update.message.reply_text(
            f"✅ *تم الشراء بنجاح!*\n\n"
            f"🪖 {unit_name} × {count}\n"
            f"💰 التكلفة: {total_cost:,}\n"
            f"💰 الرصيد المتبقي: {country['ذهب']:,}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # بناء مبنى — تم تغيير الأمر من "بني" إلى "بناء"
    if text.startswith("بناء "):
        country = get_country(chat_id, user.id)
        if not country:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return
        update_resources(country)
        building_name = text[5:].strip()
        if building_name not in BUILDINGS:
            await update.message.reply_text(
                f"❌ المبنى `{building_name}` غير موجود!\n\nاضغط على *المباني* لرؤية المتاح 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
            return

        data_b = BUILDINGS[building_name]
        if country["ذهب"] < data_b["سعر"]:
            await update.message.reply_text(
                f"❌ لا يوجد ذهب كافٍ!\n"
                f"التكلفة: 💰{data_b['سعر']:,}\n"
                f"رصيدك: 💰{country['ذهب']:,}"
            )
            return

        country["ذهب"] -= data_b["سعر"]
        country["مباني"].append(building_name)
        await update.message.reply_text(
            f"🏗️ *تم البناء بنجاح!*\n\n"
            f"🏛️ {building_name}\n"
            f"📌 {data_b['وصف']}\n"
            f"💰 الرصيد المتبقي: {country['ذهب']:,}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # هجوم
    if text.startswith("هاجم "):
        attacker = get_country(chat_id, user.id)
        if not attacker:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return

        target_name = text[5:].strip()
        defender_id, defender = get_country_by_name(chat_id, target_name)

        if not defender:
            await update.message.reply_text(f"❌ لا توجد دولة باسم `{target_name}`!", parse_mode="Markdown")
            return
        if defender_id == user.id:
            await update.message.reply_text("❌ لا يمكنك مهاجمة نفسك! 😂")
            return
        if is_protected(defender):
            remaining = int((defender["حماية حتى"] - time.time()) / 3600)
            await update.message.reply_text(f"🛡️ *{target_name}* محمية لمدة {remaining} ساعة أخرى!", parse_mode="Markdown")
            return

        update_resources(attacker)
        update_resources(defender)

        attack_power = calc_power(attacker["وحدات"]) * random.uniform(0.7, 1.3)
        defense_power = calc_power(defender["وحدات"]) * random.uniform(0.7, 1.3)

        if "دفاع جوي" in defender["مباني"]:
            air_power = sum(UNITS[u]["قوة"] * c for u, c in attacker["وحدات"].items() if u in UNITS and UNITS[u]["نوع"] == "جوي")
            attack_power -= air_power * 0.4

        if attacker.get("نظام") == "ديكتاتوري": attack_power *= 1.3
        if attacker.get("نظام") == "شيوعي": attack_power *= 1.2
        if defender.get("نظام") == "شيوعي": defense_power *= 1.2

        if attack_power > defense_power:
            stolen_gold = int(defender["ذهب"] * 0.3)
            attacker["ذهب"] += stolen_gold
            defender["ذهب"] -= stolen_gold
            attacker["انتصارات"] += 1
            defender["خسائر"] += 1
            for unit in attacker["وحدات"]: attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * 0.8)
            for unit in defender["وحدات"]: defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.6)

            await update.message.reply_text(
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
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            attacker["خسائر"] += 1
            defender["انتصارات"] += 1
            for unit in attacker["وحدات"]: attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * 0.5)
            for unit in defender["وحدات"]: defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.85)

            await update.message.reply_text(
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
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        return

    # إطلاق صاروخ
    if text.startswith("اطلق صاروخ "):
        parts = text[11:].split(" على ")
        if len(parts) != 2:
            await update.message.reply_text("❌ الأمر الصحيح:\n`اطلق صاروخ [النوع] على [اسم الدولة]`", parse_mode="Markdown")
            return

        missile_name, target_name = parts[0].strip(), parts[1].strip()
        attacker = get_country(chat_id, user.id)
        if not attacker:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return

        if attacker["وحدات"].get(missile_name, 0) <= 0:
            await update.message.reply_text(f"❌ ليس لديك *{missile_name}*! اشتري أولاً.", parse_mode="Markdown")
            return

        defender_id, defender = get_country_by_name(chat_id, target_name)
        if not defender:
            await update.message.reply_text(f"❌ لا توجد دولة باسم `{target_name}`!", parse_mode="Markdown")
            return
        if is_protected(defender):
            remaining = int((defender["حماية حتى"] - time.time()) / 3600)
            await update.message.reply_text(f"🛡️ *{target_name}* محمية لمدة {remaining} ساعة!", parse_mode="Markdown")
            return

        missile_data = UNITS[missile_name]
        attacker["وحدات"][missile_name] -= 1

        if missile_data["نوع"] == "نووي":
            for unit in defender["وحدات"]:
                defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.2)
            stolen_gold = int(defender["ذهب"] * 0.5)
            attacker["ذهب"] += stolen_gold
            defender["ذهب"] -= stolen_gold
            await update.message.reply_text(
                f"☢️ *ضربة نووية مدمرة!* ☢️\n\n"
                f"🚀 *{missile_name}* أُطلق على *{target_name}*!\n"
                f"💥 80% من جيشهم دُمر!\n"
                f"💰 ذهب مسروق: {stolen_gold:,}\n\n"
                f"⚠️ *تحذير: كل الدول ستعلن الحرب عليك!*",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            if defender["مباني"]:
                destroyed = random.choice(defender["مباني"])
                defender["مباني"].remove(destroyed)
                await update.message.reply_text(
                    f"🚀 *ضربة صاروخية!*\n\n"
                    f"🎯 *{missile_name}* ضرب *{target_name}*\n"
                    f"💥 تم تدمير: *{destroyed}*",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"🚀 *ضربة صاروخية!*\n\n"
                    f"🎯 *{missile_name}* ضرب *{target_name}*\n"
                    f"💥 لا توجد مباني للتدمير!",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
        return

    # تحالف
    if text.startswith("تحالف مع "):
        target_name = text[9:].strip()
        my_country = get_country(chat_id, user.id)
        if not my_country:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return
        _, target = get_country_by_name(chat_id, target_name)
        if not target:
            await update.message.reply_text(f"❌ لا توجد دولة باسم `{target_name}`!", parse_mode="Markdown")
            return
        if target_name in my_country["تحالفات"]:
            await update.message.reply_text(f"❌ أنت متحالف مع *{target_name}* بالفعل!", parse_mode="Markdown")
            return
        my_country["تحالفات"].append(target_name)
        if my_country["اسم"] not in target["تحالفات"]:
            target["تحالفات"].append(my_country["اسم"])
        await update.message.reply_text(
            f"🤝 *تم التحالف!*\n\n*{my_country['اسم']}* 🤝 *{target_name}*\n\nأنتم الآن حلفاء! 💪",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # خيانة
    if text.startswith("خن "):
        target_name = text[3:].strip()
        my_country = get_country(chat_id, user.id)
        if not my_country:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return
        if target_name not in my_country["تحالفات"]:
            await update.message.reply_text(f"❌ أنت لست متحالفاً مع *{target_name}*!", parse_mode="Markdown")
            return
        my_country["تحالفات"].remove(target_name)
        _, target = get_country_by_name(chat_id, target_name)
        if target and my_country["اسم"] in target["تحالفات"]:
            target["تحالفات"].remove(my_country["اسم"])
        await update.message.reply_text(
            f"😈 *خيانة التحالف!*\n\n*{my_country['اسم']}* خان *{target_name}*!\n\n⚠️ احذر من الانتقام! 😂",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # مساعدة مالية
    if text.startswith("ساعد "):
        parts = text[5:].strip().rsplit(" ", 1)
        if len(parts) != 2:
            await update.message.reply_text("❌ الأمر:\n`ساعد [اسم الدولة] [المبلغ]`", parse_mode="Markdown")
            return
        target_name, amount_str = parts
        try:
            amount = int(amount_str)
            if amount <= 0: raise ValueError
        except:
            await update.message.reply_text("❌ المبلغ يجب أن يكون رقماً موجباً!")
            return
        my_country = get_country(chat_id, user.id)
        if not my_country:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return
        update_resources(my_country)
        if my_country["ذهب"] < amount:
            await update.message.reply_text(f"❌ لا يوجد ذهب كافٍ! رصيدك: 💰{my_country['ذهب']:,}")
            return
        _, target = get_country_by_name(chat_id, target_name)
        if not target:
            await update.message.reply_text(f"❌ لا توجد دولة باسم `{target_name}`!", parse_mode="Markdown")
            return
        my_country["ذهب"] -= amount
        target["ذهب"] += amount
        await update.message.reply_text(
            f"💰 *تم إرسال المساعدة!*\n\nمن: *{my_country['اسم']}*\nإلى: *{target_name}*\nالمبلغ: 💰{amount:,}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # تجسس
    if text.startswith("جاسوس "):
        target_name = text[7:].strip()
        my_country = get_country(chat_id, user.id)
        if not my_country:
            await update.message.reply_text("❌ ليس لديك دولة!")
            return
        if "جهاز استخبارات" not in my_country["مباني"]:
            await update.message.reply_text("❌ تحتاج بناء *جهاز استخبارات* أولاً!\n`بناء جهاز استخبارات`", parse_mode="Markdown")
            return
        _, target = get_country_by_name(chat_id, target_name)
        if not target:
            await update.message.reply_text(f"❌ لا توجد دولة باسم `{target_name}`!", parse_mode="Markdown")
            return
        update_resources(target)
        power = calc_power(target["وحدات"])
        units_text = "\n".join(f"  • {u}: {c}" for u, c in target["وحدات"].items() if c > 0) or "  لا يوجد جيش"
        await update.message.reply_text(
            f"🕵️ *تقرير استخباراتي سري* 🕵️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🎯 الهدف: *{target_name}*\n"
            f"💰 الذهب التقريبي: ~{target['ذهب'] // 100 * 100:,}\n"
            f"⚔️ القوة العسكرية: {power:,}\n"
            f"🏆 الانتصارات: {target['انتصارات']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🪖 *تشكيلة الجيش:*\n{units_text}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT, handle_text))
    print("✅ عرش الظلال يعمل! 🌑")
    application.run_polling()
