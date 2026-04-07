import os
import random
import time
import uuid
import difflib
from collections import Counter
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

# ===== قاعدة البيانات (آمنة تماماً ولا تحذف البيانات) =====
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

def get_all_alliances(chat_id):
    """جلب جميع التحالفات في شات معين"""
    return list(alliances_col.find({"chat_id": chat_id}))

# ===== ثابت: حد الذهب الأقصى =====
GOLD_CAP = 200_000_000

def cap_gold(country):
    """قص الذهب للحد الأعلى بعد أي زيادة"""
    if country.get("ذهب", 0) > GOLD_CAP:
        country["ذهب"] = GOLD_CAP
    return country

# ===== ثابت: مدة الدرع =====
SHIELD_DURATION = 3600  # 1 ساعة

# ===== المباني غير القابلة للتكرار =====
NON_STACKABLE_BUILDINGS = {"دفاع جوي", "مركز بحوث", "مستشفى عسكري", "جهاز استخبارات", "منشأة نووية"}

# ===== البيانات الأساسية =====
UNITS = {
    "جندي": {"قوة": 5, "سعر": 250, "نوع": "مشاة"},
    "مقاتل": {"قوة": 12, "سعر": 750, "نوع": "مشاة"},
    "قناص": {"قوة": 20, "سعر": 1500, "نوع": "مشاة"},
    "كوماندوز": {"قوة": 35, "سعر": 2500, "نوع": "مشاة"},
    "قوات خاصة": {"قوة": 50, "سعر": 4000, "نوع": "مشاة"},
    "فرقة النخبة": {"قوة": 70, "سعر": 6000, "نوع": "مشاة"},
    "جيب مسلح": {"قوة": 5, "سعر": 1000, "نوع": "مدرعات"},
    "مدرعة BTR": {"قوة": 15, "سعر": 2500, "نوع": "مدرعات"},
    "دبابة T-72": {"قوة": 35, "سعر": 5000, "نوع": "مدرعات"},
    "دبابة T-90": {"قوة": 50, "سعر": 9000, "نوع": "مدرعات"},
    "دبابة Abrams": {"قوة": 70, "سعر": 12500, "نوع": "مدرعات"},
    "دبابة Leopard": {"قوة": 75, "سعر": 14000, "نوع": "مدرعات"},
    "دبابة Merkava": {"قوة": 80, "سعر": 16000, "نوع": "مدرعات"},
    "مدمرة AS-21": {"قوة": 100, "سعر": 25000, "نوع": "مدرعات"},
    # === أسلحة جديدة: مدرعات ===
    "BMPT Terminator": {"قوة": 90, "سعر": 20000, "نوع": "مدرعات"},
    "Bradley": {"قوة": 55, "سعر": 10000, "نوع": "مدرعات"},
    "Type 99": {"قوة": 78, "سعر": 15000, "نوع": "مدرعات"},
    # === جوي ===
    "مسيّرة": {"قوة": 10, "سعر": 4000, "نوع": "جوي"},
    "Apache": {"قوة": 30, "سعر": 10000, "نوع": "جوي"},
    "MiG-29": {"قوة": 45, "سعر": 15000, "نوع": "جوي"},
    "F-16": {"قوة": 60, "سعر": 20000, "نوع": "جوي"},
    "Su-35": {"قوة": 70, "سعر": 25000, "نوع": "جوي"},
    "F-22": {"قوة": 85, "سعر": 35000, "نوع": "جوي"},
    "F-35": {"قوة": 90, "سعر": 45000, "نوع": "جوي"},
    "B-2 Spirit": {"قوة": 110, "سعر": 75000, "نوع": "جوي"},
    "B-52": {"قوة": 120, "سعر": 90000, "نوع": "جوي"},
    # === أسلحة جديدة: جوي ===
    "A-10 Warthog": {"قوة": 65, "سعر": 22000, "نوع": "جوي"},
    "Su-57": {"قوة": 88, "سعر": 40000, "نوع": "جوي"},
    "F-15": {"قوة": 75, "سعر": 30000, "نوع": "جوي"},
    # === صواريخ ===
    "Grad": {"قوة": 100, "سعر": 15000, "نوع": "صواريخ"},
    "كروز": {"قوة": 200, "سعر": 37500, "نوع": "صواريخ"},
    "Scud": {"قوة": 275, "سعر": 62500, "نوع": "صواريخ"},
    "باتريوت": {"قوة": 60, "سعر": 15000, "نوع": "دفاع"},
    "Iskander": {"قوة": 375, "سعر": 100000, "نوع": "صواريخ"},
    "Tomahawk": {"قوة": 425, "سعر": 150000, "نوع": "صواريخ"},
    "ICBM": {"قوة": 500, "سعر": 250000, "نوع": "صواريخ"},
    "Kinzhal": {"قوة": 575, "سعر": 325000, "نوع": "صواريخ"},
    # === أسلحة جديدة: صواريخ ===
    "MLRS": {"قوة": 225, "سعر": 50000, "نوع": "صواريخ"},
    "Iskander-M": {"قوة": 425, "سعر": 125000, "نوع": "صواريخ"},
    # === نووي ===
    "كيميائي": {"قوة": 130, "سعر": 100000, "نوع": "نووي"},
    "نووي تكتيكي": {"قوة": 200, "سعر": 250000, "نوع": "نووي"},
    "قنبلة نووية": {"قوة": 500, "سعر": 500000, "نوع": "نووي"},
    # === وحدات دفاع جوي/صاروخي جديدة ===
    "Stinger": {"قوة": 15, "سعر": 5000, "نوع": "دفاع_جوي"},
    "NASAMS": {"قوة": 35, "سعر": 12000, "نوع": "دفاع_جوي"},
    "S-300": {"قوة": 55, "سعر": 25000, "نوع": "دفاع_جوي"},
    "S-400": {"قوة": 75, "سعر": 40000, "نوع": "دفاع_جوي"},
    "THAAD": {"قوة": 90, "سعر": 60000, "نوع": "دفاع_جوي"},
    "Arrow 3": {"قوة": 95, "سعر": 70000, "نوع": "دفاع_جوي"},
    "S-500": {"قوة": 110, "سعر": 90000, "نوع": "دفاع_جوي"},
}

BUILDINGS = {
    "حقل نفط": {"دخل": 200, "سعر": 10000, "وصف": "ينتج 200 ذهب/ساعة 🛢️"},
    "مصنع أسلحة": {"دخل": 150, "سعر": 7500, "وصف": "ينتج 150 ذهب/ساعة 🏭"},
    "أراضي زراعية": {"دخل": 100, "سعر": 5000, "وصف": "ينتج 100 ذهب/ساعة 🌾"},
    "دفاع جوي": {"دخل": 0, "سعر": 15000, "وصف": "يصد 40% من الطائرات 🛡️"},
    "مركز بحوث": {"دخل": 0, "سعر": 20000, "وصف": "يطور قدرات جيشك 🔬"},
    "مستشفى عسكري": {"دخل": 0, "سعر": 12500, "وصف": "يشفي 20% من الجنود 🏥"},
    "جهاز استخبارات": {"دخل": 0, "سعر": 17500, "وصف": "يتيح التجسس على الدول 🕵️"},
    "قاعدة صواريخ": {"دخل": 0, "سعر": 25000, "وصف": "يزيد قوة صواريخك 20% 🚀"},
    "منشأة نووية": {"دخل": 0, "سعر": 150000, "وصف": "تفتح الأسلحة النووية ☢️"},
}

# ===== نظام الفهم الذكي للأسماء (Fuzzy Matching) =====
# أسماء بديلة شائعة للوحدات (اختصارات / كتابة إنجليزية / أخطاء شائعة)
UNIT_ALIASES = {
    "abrams": "دبابة Abrams", "ابرامز": "دبابة Abrams",
    "leopard": "دبابة Leopard", "ليوبارد": "دبابة Leopard",
    "merkava": "دبابة Merkava", "ميركافا": "دبابة Merkava",
    "t72": "دبابة T-72", "t-72": "دبابة T-72",
    "t90": "دبابة T-90", "t-90": "دبابة T-90",
    "type99": "Type 99", "تايب99": "Type 99",
    "btr": "مدرعة BTR",
    "bradley": "Bradley", "برادلي": "Bradley",
    "terminator": "BMPT Terminator", "bmpt": "BMPT Terminator",
    "f16": "F-16", "f-16": "F-16", "اف16": "F-16",
    "f15": "F-15", "f-15": "F-15", "اف15": "F-15",
    "f22": "F-22", "f-22": "F-22", "اف22": "F-22",
    "f35": "F-35", "f-35": "F-35", "اف35": "F-35",
    "su35": "Su-35", "su-35": "Su-35", "سو35": "Su-35",
    "su57": "Su-57", "su-57": "Su-57", "سو57": "Su-57",
    "mig29": "MiG-29", "mig-29": "MiG-29", "ميغ29": "MiG-29",
    "a10": "A-10 Warthog", "a-10": "A-10 Warthog", "warthog": "A-10 Warthog",
    "b2": "B-2 Spirit", "b-2": "B-2 Spirit",
    "b52": "B-52", "b-52": "B-52",
    "apache": "Apache", "اباتشي": "Apache",
    "grad": "Grad", "غراد": "Grad",
    "scud": "Scud", "سكود": "Scud",
    "icbm": "ICBM",
    "mlrs": "MLRS",
    "iskander": "Iskander", "اسكندر": "Iskander",
    "iskander-m": "Iskander-M", "اسكندرم": "Iskander-M",
    "tomahawk": "Tomahawk", "توماهوك": "Tomahawk",
    "kinzhal": "Kinzhal", "كينجال": "Kinzhal", "كنجال": "Kinzhal",
    "patriot": "باتريوت", "باتريوت": "باتريوت",
    "stinger": "Stinger", "ستينغر": "Stinger",
    "nasams": "NASAMS",
    "s300": "S-300", "s-300": "S-300", "اس300": "S-300",
    "s400": "S-400", "s-400": "S-400", "اس400": "S-400",
    "s500": "S-500", "s-500": "S-500", "اس500": "S-500",
    "thaad": "THAAD", "ثاد": "THAAD",
    "arrow3": "Arrow 3", "arrow": "Arrow 3", "ارو3": "Arrow 3",
    "دبابه": "دبابة T-72", "دبابة": "دبابة T-72",
    "مسيرة": "مسيّرة", "مسيره": "مسيّرة", "درون": "مسيّرة",
}

def fuzzy_find_unit(name):
    """البحث الذكي عن اسم الوحدة"""
    # 1. تطابق دقيق
    if name in UNITS:
        return name
    # 2. تطابق بدون حساسية لحالة الأحرف
    name_lower = name.lower().strip()
    for unit_name in UNITS:
        if unit_name.lower() == name_lower:
            return unit_name
    # 3. بحث في الأسماء البديلة
    if name_lower in UNIT_ALIASES:
        return UNIT_ALIASES[name_lower]
    # 4. بحث بدون شرطات ومسافات
    name_clean = name_lower.replace("-", "").replace(" ", "")
    for alias, real_name in UNIT_ALIASES.items():
        if alias.replace("-", "").replace(" ", "") == name_clean:
            return real_name
    # 5. difflib fuzzy matching على أسماء UNITS
    all_names = list(UNITS.keys()) + list(UNIT_ALIASES.keys())
    matches = difflib.get_close_matches(name_lower, [n.lower() for n in all_names], n=1, cutoff=0.55)
    if matches:
        matched_lower = matches[0]
        for n in all_names:
            if n.lower() == matched_lower:
                if n in UNITS:
                    return n
                elif n in UNIT_ALIASES:
                    return UNIT_ALIASES[n]
                break
    # 6. لم يتم العثور
    return None

def fuzzy_find_building(name):
    """البحث الذكي عن اسم المبنى"""
    if name in BUILDINGS:
        return name
    name_lower = name.lower().strip()
    for b_name in BUILDINGS:
        if b_name.lower() == name_lower:
            return b_name
    matches = difflib.get_close_matches(name_lower, [n.lower() for n in BUILDINGS.keys()], n=1, cutoff=0.55)
    if matches:
        for n in BUILDINGS:
            if n.lower() == matches[0]:
                return n
    return None

def format_buildings_summary(buildings):
    """عرض المباني بشكل مضغوط: المبنى × العدد"""
    if not buildings:
        return "  لا توجد مباني بعد"
    if isinstance(buildings, dict):
        items = [(name, count) for name, count in buildings.items() if count]
    else:
        items = [(name, count) for name, count in Counter(buildings).items() if count]
    if not items:
        return "  لا توجد مباني بعد"
    return "\n".join(f"  • {name} × {count}" for name, count in items)


def notify_attack_text(attacker_name, weapon_label, amount=None, damage=None):
    lines = [
        "🚨 تم الهجوم عليك!",
        "",
        f"👤 المهاجم: {attacker_name}",
        f"🎯 النوع: {weapon_label}",
    ]
    if amount is not None:
        lines.append(f"📦 العدد: {amount}")
    if damage is not None:
        lines.append(f"💥 الضرر: {damage}")
    return "\n".join(lines)


async def send_attack_notification(bot, chat_id, target_name, attacker_name, weapon_label, amount=None, damage=None, prefer_alliance=False):
    """إرسال إشعار للهجوم إلى الدولة أو التحالف المستهدف."""
    if not prefer_alliance:
        target_country = get_country_by_name(target_name)
        if target_country and target_country.get("user_id"):
            try:
                await bot.send_message(
                    chat_id=target_country["user_id"],
                    text=notify_attack_text(attacker_name, weapon_label, amount=amount, damage=damage)
                )
            except:
                pass
            return

    target_alliance = load_alliance(chat_id, target_name)
    if not target_alliance:
        return

    for member_name in target_alliance.get("أعضاء", []):
        member = get_country_by_name(member_name)
        if member and member.get("user_id"):
            try:
                await bot.send_message(
                    chat_id=member["user_id"],
                    text=notify_attack_text(attacker_name, weapon_label, amount=amount, damage=damage)
                )
            except:
                pass

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

def calc_air_defense_power(units_dict):
    """حساب قوة الدفاع الجوي من الوحدات"""
    return sum(UNITS[u]["قوة"] * c for u, c in units_dict.items() if u in UNITS and UNITS[u]["نوع"] == "دفاع_جوي")

def calc_nuke_intercept_chance(defender):
    """حساب احتمال صد النووي بناء على الدفاع الجوي"""
    ad_power = calc_air_defense_power(defender.get("وحدات", {}))
    has_building = "دفاع جوي" in defender.get("مباني", [])
    # كل 100 قوة دفاع جوي = 5% صد, حد أقصى 70%
    chance = min(0.70, ad_power * 0.0005)
    if has_building:
        chance += 0.10
    return min(0.80, chance)

def update_resources(country):
    now = time.time()
    elapsed = (now - country.get("آخر تحديث", now)) / 3600
    country["ذهب"] = country.get("ذهب", 0) + int(calc_income(country) * elapsed)
    country["آخر تحديث"] = now
    # تقليص أي درع أطول من ساعة
    if country.get("حماية حتى", 0) > now + SHIELD_DURATION:
        country["حماية حتى"] = now + SHIELD_DURATION
    cap_gold(country)
    return country

def is_protected(country):
    return time.time() < country.get("حماية حتى", 0)

def get_level(victories):
    if victories >= 30: return "👑 قوة عظمى"
    if victories >= 15: return "⭐⭐ قوة كبرى"
    if victories >= 5: return "⭐ قوة إقليمية"
    return "🪖 دولة ناشئة"

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

def calc_collective_defense(chat_id, defender_name):
    """نظام الدفاع الجماعي: إذا المدافع ضمن تحالف، يتم احتساب قوة جميع الأعضاء +20%"""
    alliance = get_country_alliance(chat_id, defender_name)
    if not alliance:
        return None, 0
    total_power, _ = calc_alliance_power(chat_id, alliance)
    # زيادة الدفاع بنسبة 20%
    boosted = int(total_power * 1.2)
    return alliance, boosted

# ===== تتبع اللاعبين في كل قروب =====
# نستخدم مجموعة بيانات في الذاكرة + نحفظ في context لتتبع من هو في أي قروب
chat_members_cache = {}  # {chat_id: {user_id: country_name, ...}}

def track_player_in_chat(chat_id, user_id, country_name):
    """تتبع اللاعب في هذا القروب"""
    if chat_id not in chat_members_cache:
        chat_members_cache[chat_id] = {}
    chat_members_cache[chat_id][user_id] = country_name

def get_chat_players(chat_id):
    """جلب قائمة اللاعبين في قروب معين"""
    return chat_members_cache.get(chat_id, {})

# ===== لوحات الأزرار =====
def main_menu_keyboard(user_id=None):
    """إنشاء لوحة الأزرار الرئيسية مع ربط user_id"""
    suffix = f"|{user_id}" if user_id else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 دولتي", callback_data=f"my_country{suffix}"),
         InlineKeyboardButton("💰 خزينتي", callback_data=f"treasury{suffix}")],
        [InlineKeyboardButton("🪖 جيشي", callback_data=f"my_army{suffix}"),
         InlineKeyboardButton("🛒 الأسواق", callback_data=f"markets{suffix}")],
        [InlineKeyboardButton("🏆 الترتيب", callback_data=f"ranking{suffix}"),
         InlineKeyboardButton("⚔️ الحرب", callback_data=f"war_menu{suffix}")],
        [InlineKeyboardButton("🤝 التحالف", callback_data=f"alliance_menu{suffix}"),
         InlineKeyboardButton("🏛️ الأيديولوجيات", callback_data=f"ideologies{suffix}")],
        [InlineKeyboardButton("🏗️ المباني", callback_data=f"buildings_info{suffix}"),
         InlineKeyboardButton("🏦 البنك", callback_data=f"bank{suffix}")],
        [InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self{suffix}")],
    ])

def action_keyboard(back=None, user_id=None):
    suffix = f"|{user_id}" if user_id else ""
    row = []
    if back:
        row.append(InlineKeyboardButton("🔙 رجوع", callback_data=f"{back}{suffix}"))
    row.append(InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self{suffix}"))
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
        [InlineKeyboardButton("📘 التحالف والحرب", callback_data="alliance_war_info")],
    ])

def markets_keyboard(user_id=None):
    suffix = f"|{user_id}" if user_id else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 المشاة", callback_data=f"market_infantry{suffix}"),
         InlineKeyboardButton("🚗 المدرعات", callback_data=f"market_armor{suffix}")],
        [InlineKeyboardButton("✈️ سلاح الجو", callback_data=f"market_air{suffix}"),
         InlineKeyboardButton("🚀 الصواريخ", callback_data=f"market_missiles{suffix}")],
        [InlineKeyboardButton("🛡️ الدفاع الجوي", callback_data=f"market_air_defense{suffix}"),
         InlineKeyboardButton("🏗️ المباني", callback_data=f"market_buildings{suffix}")],
        [InlineKeyboardButton("🛡️ شراء حماية", callback_data=f"buy_protection{suffix}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"main_menu{suffix}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self{suffix}")],
    ])

def war_keyboard(user_id=None):
    suffix = f"|{user_id}" if user_id else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ قائمة الهجوم", callback_data=f"attack_list_0{suffix}")],
        [InlineKeyboardButton("🔥 هجوم تحالف", callback_data=f"alliance_attack_list_0{suffix}")],
        [InlineKeyboardButton("🚀 إطلاق صاروخ", callback_data=f"how_to_missile{suffix}")],
        [InlineKeyboardButton("☢️ ضربة نووية", callback_data=f"how_to_nuke{suffix}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"main_menu{suffix}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self{suffix}")],
    ])

def alliance_menu_keyboard(user_id=None):
    suffix = f"|{user_id}" if user_id else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁️ تحالفي", callback_data=f"my_alliance{suffix}")],
        [InlineKeyboardButton("⚔️ جيش التحالف", callback_data=f"alliance_army{suffix}")],
        [InlineKeyboardButton("📢 أمر التحالف", callback_data=f"alliance_order{suffix}")],
        [InlineKeyboardButton("📩 طلبات الانضمام", callback_data=f"join_requests_list{suffix}")],
        [InlineKeyboardButton("🚫 طرد عضو", callback_data=f"kick_member_list_0{suffix}")],
        [InlineKeyboardButton("💰 إرسال ذهب للتحالف", callback_data=f"how_to_send_gold{suffix}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"main_menu{suffix}"),
         InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self{suffix}")],
    ])

def parse_callback_data(data):
    """فصل callback_data إلى (الأمر, user_id المالك)"""
    if "|" in data:
        parts = data.rsplit("|", 1)
        try:
            return parts[0], int(parts[1])
        except ValueError:
            return data, None
    return data, None

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
            f"👇 استكشف اللعبة:",
            parse_mode="Markdown",
            reply_markup=private_menu_keyboard()
        )
    else:
        # تتبع اللاعب في القروب
        country = load_country(user.id)
        if country:
            track_player_in_chat(update.effective_chat.id, user.id, country["اسم"])
        await update.message.reply_text(
            f"🌑 *عرش الظلال — Throne of Shadows* 🌑\n\n"
            f"مرحباً بكم في أعظم لعبة حرب! ⚔️\n\n"
            f"🌍 *دولتك عالمية — نفس الدولة في كل الكروبات!*\n\n"
            f"🏳️ للبدء اكتب:\n`انشاء دولة [اسم دولتك]`\n\n"
            f"📋 للأوامر اكتب: `مساعدة`\n\n"
            f"👇 أو استخدم الأزرار:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(user.id)
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # تتبع اللاعب في القروب
    if update.effective_chat.type != "private":
        country = load_country(user.id)
        if country:
            track_player_in_chat(update.effective_chat.id, user.id, country["اسم"])
    await update.message.reply_text(
        "🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(user.id)
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    raw_data = query.data

    # فصل الأمر عن user_id المالك
    data, owner_id = parse_callback_data(raw_data)

    # === نظام أمان الأزرار ===
    # الأزرار المفتوحة للجميع (تصويت + طلبات الانضمام)
    if data.startswith("vote_yes_") or data.startswith("vote_no_") or data.startswith("join_accept_") or data.startswith("join_reject_"):
        pass  # يتم التحقق لاحقاً داخل منطق التصويت/الانضمام
    elif owner_id is not None and owner_id != user.id:
        await query.answer("❌ هذا الزر ليس لك", show_alert=True)
        return

    await query.answer()
    uid = user.id  # المستخدم الحالي

    # تتبع اللاعب في القروب
    if query.message.chat.type != "private":
        country_track = load_country(uid)
        if country_track:
            track_player_in_chat(chat_id, uid, country_track["اسم"])

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
            parse_mode="Markdown", reply_markup=main_menu_keyboard(uid)
        )
        return

    back_private_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_private"), InlineKeyboardButton("🗑️ حذف", callback_data="del_self")]])
    back_main_kb = action_keyboard("main_menu", uid)
    back_markets_kb = action_keyboard("markets", uid)
    back_war_kb = action_keyboard("war_menu", uid)
    back_alliance_kb = action_keyboard("alliance_menu", uid)

    if data == "how_to_play":
        await query.edit_message_text(
            "📖 *كيف تلعب عرش الظلال؟*\n━━━━━━━━━━━━━━━\n\n"
            "1️⃣ *أنشئ دولتك:*\n`انشاء دولة [الاسم]`\n\n"
            "2️⃣ *ابنِ اقتصادك:*\n`بناء حقل نفط` 🛢️\n\n"
            "3️⃣ *استثمر في البنك:*\n`استثمار مالي` 🏦\n\n"
            "4️⃣ *هاجم الدول:*\n`هاجم [اسم الدولة]` ⚔️\n\n"
            "5️⃣ *التحالفات:*\n`انشاء تحالف [الاسم]` 🤝",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "all_commands":
        await query.edit_message_text(
            "⚔️ *الأوامر الكاملة*\n━━━━━━━━━━━━━━━\n\n"
            "🏳️ `انشاء دولة [الاسم]`\n"
            "🛒 `اشتري [الوحدة] [العدد]`\n"
            "🏗️ `بناء [المبنى]`\n"
            "🏦 `استثمار مالي` (كل 10 دقائق)\n"
            "⚔️ `هاجم [اسم الدولة]`\n"
            "🔥 `هجوم تحالف [الهدف]`\n"
            "☢️ `نووي [اسم الدولة]`\n"
            "🤝 `انشاء تحالف [الاسم]`\n"
            "📩 `طلب انضمام [اسم التحالف]`\n"
            "📢 `امر تحالف [الرسالة]`\n"
            "🎖️ `ترقية [اسم الدولة] [الرتبة]` (للقائد الأعلى)\n"
            "🗑️ `حذف دولتي` (حذف دولتك)\n\n"
            "والكثير من الأوامر عبر الأزرار!",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "ideologies_private":
        msg = "🏛️ *الأيديولوجيات المتاحة*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in IDEOLOGIES.items():
            msg += f"{d['رمز']} *{name}*\n{d['وصف']}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_private_kb)
        return

    if data == "buildings_private":
        msg = "🏗️ *المباني وفوائدها*\n━━━━━━━━━━━━━━━\n\n"
        for name, d in BUILDINGS.items():
            stackable = "🔁 قابل للتكرار" if name not in NON_STACKABLE_BUILDINGS else "1️⃣ مرة واحدة"
            msg += f"• *{name}* ({stackable})\n  {d['وصف']} | 💰{d['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_private_kb)
        return

    if data == "weapons_info":
        msg = "🚀 *أسلحة ووحدات جيشك تزيد من قوتك الهجومية والدفاعية* ⚔️"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_private_kb)
        return

    if data == "bank_info":
        await query.edit_message_text(
            "🏦 *نظام البنك والاستثمار*\n━━━━━━━━━━━━━━━\n\n"
            "💡 *كيف يعمل؟*\n"
            "استثمر كل نقودك دفعة واحدة كل 10 دقائق!\n\n"
            "📌 *الأمر:*\n`استثمار مالي`\n\n"
            "⚡ نسبة الربح: *مضمونة من 50% إلى 200%*\nلا يوجد خسارة أبداً!",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "alliance_info":
        await query.edit_message_text(
            "🤝 *نظام التحالفات والرتب*\n━━━━━━━━━━━━━━━\n\n"
            "👑 *القائد الأعلى:* يملك كافة الصلاحيات.\n"
            "⭐ *جنرال:* يقود الحروب.\n"
            "🎖️ *عميد:* ضابط في التحالف.\n"
            "🪖 *جندي:* عضو أساسي يشارك بالجيش.\n\n"
            "📌 لمنح الرتبة (للقائد فقط):\n`ترقية [اسم الدولة] [الرتبة]`",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    # === قسم جديد: التحالف والحرب ===
    if data == "alliance_war_info":
        await query.edit_message_text(
            "📘 *التحالف والحرب*\n━━━━━━━━━━━━━━━\n\n"
            "📩 *للانضمام لتحالف:*\n`طلب انضمام [اسم التحالف]`\n"
            "• الطلب يُرسل للقائد الأعلى\n"
            "• القائد يقبل أو يرفض عبر الأزرار\n\n"
            "📢 *أمر التحالف (للقائد فقط):*\n`امر تحالف [الرسالة]`\n"
            "• يُرسل لجميع أعضاء التحالف\n\n"
            "⚔️ *هجوم التحالف:*\n"
            "• يتم عبر تصويت القيادة العليا\n"
            "• الشروط: موافقة القائد أو 5 أصوات\n\n"
            "🔥 *قائمة الهجوم:*\n"
            "• تظهر فقط الدول في نفس القروب\n\n"
            "📌 *صلاحيات القائد الأعلى:*\n"
            "✔️ إرسال أوامر التحالف\n"
            "✔️ قبول/رفض طلبات الانضمام\n"
            "✔️ بدء التصويت للحرب",
            parse_mode="Markdown", reply_markup=back_private_kb
        )
        return

    if data == "my_country":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!\n\nاكتب: `انشاء دولة [الاسم]`", parse_mode="Markdown", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        protection = ""
        if is_protected(country):
            remaining = max(1, int((country["حماية حتى"] - time.time()) / 60))
            protection = f"\n🛡️ محمي لمدة {remaining} دقيقة"
        alliance = get_country_alliance(chat_id, country["اسم"])
        alliance_text = f"🤝 التحالف: {alliance['اسم']}" if alliance else "🤝 لا ينتمي لتحالف"
        ad_power = calc_air_defense_power(country.get("وحدات", {}))
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
            f"🛡️ الدفاع الجوي: {ad_power:,}\n"
            f"🏆 انتصارات: {country.get('انتصارات', 0)}\n"
            f"💀 هزائم: {country.get('خسائر', 0)}"
            f"{protection}",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "my_army":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        units_text = "\n".join(f"  • {u}: {c}" for u, c in country.get("وحدات", {}).items() if c > 0) or "  لا يوجد جيش بعد"
        buildings_text = format_buildings_summary(country.get("مباني", []))
        await query.edit_message_text(
            f"⚔️ *جيش {country['اسم']}* ⚔️\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💪 القوة: {calc_power(country.get('وحدات', {})):,}\n"
            f"🛡️ الدفاع الجوي: {calc_air_defense_power(country.get('وحدات', {})):,}\n\n"
            f"🪖 *الوحدات:*\n{units_text}\n\n"
            f"🏗️ *المباني:*\n{buildings_text}",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "treasury":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        income = calc_income(country)
        last_invest = country.get("آخر استثمار", 0)
        time_left = max(0, 600 - (time.time() - last_invest))
        invest_status = "✅ جاهز!" if time_left == 0 else f"⏳ بعد {int(time_left/60)} دقيقة"
        await query.edit_message_text(
            f"💰 *خزينة {country['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💎 الذهب: *{country.get('ذهب', 0):,}*\n"
            f"🏦 أرباح البنك: *{country.get('بنك', 0):,}*\n"
            f"📈 الدخل/ساعة: *+{income}*\n\n"
            f"🏦 حالة الاستثمار: {invest_status}\n"
            f"💡 `استثمار مالي` لاستثمار ذهبك!",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
        return

    if data == "bank":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        country = update_resources(country)
        save_country(country)
        last_invest = country.get("آخر استثمار", 0)
        time_left = max(0, 600 - (time.time() - last_invest))
        status = "✅ جاهز للاستثمار!" if time_left == 0 else f"⏳ متاح بعد {int(time_left/60)} دقيقة و{int(time_left%60)} ثانية"
        await query.edit_message_text(
            f"🏦 *بنك {country['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 الذهب المتاح: *{country.get('ذهب', 0):,}*\n"
            f"🏦 إجمالي الأرباح: *{country.get('بنك', 0):,}*\n\n"
            f"📊 *حالة الاستثمار:*\n{status}\n\n"
            f"💡 *الأمر:* `استثمار مالي`\n\n"
            f"⚡ نسبة الربح مضمونة 100%: تضاف أرباح بين 50% إلى 200%!",
            parse_mode="Markdown", reply_markup=back_main_kb
        )
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
        await query.edit_message_text("🛒 *الأسواق العسكرية*\n\nاختر:", parse_mode="Markdown", reply_markup=markets_keyboard(uid))
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
        msg = "🚀 *سوق الصواريخ والنووي*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] in ["صواريخ", "دفاع", "نووي"]:
                icon = "☢️" if d["نوع"] == "نووي" else "🛡️" if d["نوع"] == "دفاع" else "🚀"
                msg += f"{icon} *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "market_air_defense":
        msg = "🛡️ *سوق الدفاع الجوي والصاروخي*\n━━━━━━━━━━━━━━━\n`اشتري [الوحدة] [العدد]`\n\n"
        for name, d in UNITS.items():
            if d["نوع"] == "دفاع_جوي":
                msg += f"🛡️ *{name}* — ⚔️{d['قوة']} | 💰{d['سعر']:,}\n"
        msg += "\n📌 تقلل الهجوم الجوي وتزيد فرصة صد الصواريخ والنووي"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "market_buildings":
        msg = "🏗️ *سوق المباني*\n━━━━━━━━━━━━━━━\n`بناء [المبنى]`\n\n"
        for name, d in BUILDINGS.items():
            stackable = "🔁" if name not in NON_STACKABLE_BUILDINGS else "1️⃣"
            msg += f"• {stackable} *{name}*\n  {d['وصف']} | 💰{d['سعر']:,}\n\n"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_markets_kb)
        return

    if data == "buy_protection":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_markets_kb)
            return
        country = update_resources(country)
        if country.get("ذهب", 0) < 5000:
            await query.edit_message_text(f"❌ لا يوجد ذهب كافٍ!\nتحتاج: 💰5,000\nرصيدك: 💰{country.get('ذهب', 0):,}", reply_markup=back_markets_kb)
            return
        country["ذهب"] -= 5000
        # الدرع دائماً ساعة واحدة فقط
        country["حماية حتى"] = time.time() + SHIELD_DURATION
        cap_gold(country)
        save_country(country)
        await query.edit_message_text("🛡️ *تم شراء الحماية!*\n\nأنت محمي لمدة ساعة واحدة! 💪", parse_mode="Markdown", reply_markup=back_main_kb)
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
            stackable = "🔁 قابل للتكرار" if name not in NON_STACKABLE_BUILDINGS else "1️⃣ مرة واحدة"
            msg += f"• *{name}* ({stackable})\n  {d['وصف']}\n  💰 {d['سعر']:,}\n\n"
        msg += "━━━━━━━━━━━━━━━\n`بناء [اسم المبنى]`"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_main_kb)
        return

    if data == "war_menu":
        await query.edit_message_text("⚔️ *قائمة الحرب*\n\nاختر:", parse_mode="Markdown", reply_markup=war_keyboard(uid))
        return

    # === قائمة الهجوم مع pagination — تعرض فقط دول نفس القروب ===
    if data.startswith("attack_list_"):
        page = int(data.split("_")[2]) if data.split("_")[2].isdigit() else 0
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_war_kb)
            return
        # جلب اللاعبين في نفس القروب فقط
        chat_players = get_chat_players(chat_id)
        targets = []
        for p_uid, p_name in chat_players.items():
            if p_uid == uid:
                continue  # استبعاد اللاعب نفسه
            p_country = load_country(p_uid)
            if p_country:
                targets.append(p_country)
        # إذا لم يتم العثور على لاعبين في الكاش، نبحث في كل الدول كـ fallback
        if not targets:
            all_c = get_all_countries()
            targets = [c for c in all_c if c["user_id"] != uid]
        # ترتيب حسب القوة
        targets.sort(key=lambda x: calc_power(x.get("وحدات", {})), reverse=True)
        per_page = 5
        total_pages = max(1, (len(targets) + per_page - 1) // per_page)
        page = min(page, total_pages - 1)
        start = page * per_page
        page_targets = targets[start:start + per_page]
        buttons = []
        for t in page_targets:
            power = calc_power(t.get("وحدات", {}))
            protected = "🛡️" if is_protected(t) else ""
            btn_text = f"{protected}{t['اسم']} ⚔️{power:,}"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"atk_{t['user_id']}|{uid}")])
        # أزرار التنقل
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"attack_list_{page-1}|{uid}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data=f"noop|{uid}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️ التالي", callback_data=f"attack_list_{page+1}|{uid}"))
        buttons.append(nav_row)
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"war_menu|{uid}"), InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self|{uid}")])
        header = "⚔️ *اختر دولة للهجوم عليها*\n━━━━━━━━━━━━━━━\n"
        if chat_players:
            header += f"🏘️ دول هذا القروب | الصفحة {page+1}/{total_pages}\n\n🛡️ = محمي"
        else:
            header += f"🌍 جميع الدول | الصفحة {page+1}/{total_pages}\n\n🛡️ = محمي"
        await query.edit_message_text(
            header,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data == "noop":
        return

    # === هجوم مباشر من القائمة ===
    if data.startswith("atk_"):
        target_uid = int(data.split("_")[1])
        attacker = load_country(uid)
        if not attacker:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_war_kb)
            return
        defender = load_country(target_uid)
        if not defender:
            await query.edit_message_text("❌ هذه الدولة لم تعد موجودة!", reply_markup=back_war_kb)
            return
        if is_protected(defender):
            remaining = max(1, int((defender["حماية حتى"] - time.time()) / 60))
            await query.edit_message_text(f"🛡️ *{defender['اسم']}* محمية لمدة {remaining} دقيقة!", parse_mode="Markdown", reply_markup=back_war_kb)
            return
        attacker = update_resources(attacker)
        defender = update_resources(defender)
        target_name = defender["اسم"]
        
        # === حساب الدفاع الجماعي ===
        def_alliance, collective_def = calc_collective_defense(chat_id, target_name)
        if def_alliance and collective_def > 0:
            defense_power = collective_def * random.uniform(0.7, 1.3)
            defense_note = f"🛡️ دفاع تحالف *{def_alliance['اسم']}* الجماعي! (+20%)\nقوة التحالف: {collective_def:,}"
        else:
            defense_power = calc_power(defender.get("وحدات", {})) * random.uniform(0.7, 1.3)
            defense_note = ""
        
        attack_power = calc_power(attacker.get("وحدات", {})) * random.uniform(0.7, 1.3)
        
        # تأثير الدفاع الجوي (مبنى + وحدات)
        if "دفاع جوي" in defender.get("مباني", []):
            air_power = sum(UNITS[u]["قوة"] * c for u, c in attacker.get("وحدات", {}).items() if u in UNITS and UNITS[u]["نوع"] == "جوي")
            attack_power -= air_power * 0.4
        ad_reduction = calc_air_defense_power(defender.get("وحدات", {})) * 0.3
        air_attack = sum(UNITS[u]["قوة"] * c for u, c in attacker.get("وحدات", {}).items() if u in UNITS and UNITS[u]["نوع"] == "جوي")
        attack_power -= min(ad_reduction, air_attack * 0.5)
        
        if attacker.get("نظام") == "ديكتاتوري": attack_power *= 1.3
        if attacker.get("نظام") == "شيوعي": attack_power *= 1.2
        if defender.get("نظام") == "شيوعي": defense_power *= 1.2
        
        # حساب خسائر الطرفين
        att_losses_pct = 0
        def_losses_pct = 0
        
        if attack_power > defense_power:
            stolen_gold = int(defender.get("ذهب", 0) * 0.3)
            attacker["ذهب"] = attacker.get("ذهب", 0) + stolen_gold
            defender["ذهب"] = max(0, defender.get("ذهب", 0) - stolen_gold)
            attacker["انتصارات"] = attacker.get("انتصارات", 0) + 1
            defender["خسائر"] = defender.get("خسائر", 0) + 1
            att_losses_pct = 20
            def_losses_pct = 40
            # إذا يملك مستشفى عسكري يقلل الخسائر
            if "مستشفى عسكري" in attacker.get("مباني", []):
                att_losses_pct = max(5, att_losses_pct - 10)
            if "مستشفى عسكري" in defender.get("مباني", []):
                def_losses_pct = max(10, def_losses_pct - 10)
            for unit in attacker.get("وحدات", {}): attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * (1 - att_losses_pct/100))
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * (1 - def_losses_pct/100))
            # درع بعد المعركة
            defender["حماية حتى"] = time.time() + SHIELD_DURATION
            cap_gold(attacker)
            save_country(attacker)
            save_country(defender)
            await query.edit_message_text(
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🏳️ المدافع: *{target_name}*\n"
                f"{defense_note}\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏆 *{attacker['اسم']} انتصر!*\n\n"
                f"📊 *تقرير المعركة:*\n"
                f"💰 غنائم: {stolen_gold:,} ذهب\n"
                f"💀 خسائر المهاجم: {att_losses_pct}%\n"
                f"💀 خسائر المدافع: {def_losses_pct}%\n"
                f"🛡️ المدافع محمي لمدة ساعة",
                parse_mode="Markdown", reply_markup=main_menu_keyboard(uid)
            )
        else:
            attacker["خسائر"] = attacker.get("خسائر", 0) + 1
            defender["انتصارات"] = defender.get("انتصارات", 0) + 1
            att_losses_pct = 50
            def_losses_pct = 15
            if "مستشفى عسكري" in attacker.get("مباني", []):
                att_losses_pct = max(20, att_losses_pct - 10)
            if "مستشفى عسكري" in defender.get("مباني", []):
                def_losses_pct = max(5, def_losses_pct - 10)
            for unit in attacker.get("وحدات", {}): attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * (1 - att_losses_pct/100))
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * (1 - def_losses_pct/100))
            defender["حماية حتى"] = time.time() + SHIELD_DURATION
            save_country(attacker)
            save_country(defender)
            await query.edit_message_text(
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🏳️ المدافع: *{target_name}*\n"
                f"{defense_note}\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🛡️ *{target_name}* صدّ الهجوم!\n\n"
                f"📊 *تقرير المعركة:*\n"
                f"💀 خسائر المهاجم: {att_losses_pct}%\n"
                f"💀 خسائر المدافع: {def_losses_pct}%",
                parse_mode="Markdown", reply_markup=main_menu_keyboard(uid)
            )
        return

    # === قائمة هجوم التحالف — عرض التحالفات الموجودة ===
    if data.startswith("alliance_attack_list_"):
        page = int(data.split("_")[3]) if len(data.split("_")) > 3 and data.split("_")[3].isdigit() else 0
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_war_kb)
            return
        my_alliance = get_country_alliance(chat_id, country["اسم"])
        if not my_alliance:
            await query.edit_message_text("❌ أنت لست في أي تحالف في هذا القروب!", reply_markup=back_war_kb)
            return
        # فقط القائد والجنرالات يمكنهم بدء هجوم تحالف
        if country["اسم"] != my_alliance.get("قائد") and country["اسم"] not in my_alliance.get("جنرالات", []):
            await query.edit_message_text("🚫 *القائد الأعلى والجنرالات فقط* يمكنهم بدء هجوم التحالف!", parse_mode="Markdown", reply_markup=back_war_kb)
            return
        # جلب كل التحالفات في هذا القروب (باستثناء تحالفنا)
        all_alliances_in_chat = get_all_alliances(chat_id)
        target_alliances = [a for a in all_alliances_in_chat if a["اسم"] != my_alliance["اسم"]]
        if not target_alliances:
            await query.edit_message_text("❌ لا توجد تحالفات أخرى في هذا القروب!", reply_markup=back_war_kb)
            return
        # حفظ القائمة مؤقتاً في context.user_data
        if "aa_targets" not in context.user_data:
            context.user_data["aa_targets"] = {}
        context.user_data["aa_targets"][str(chat_id)] = [a["اسم"] for a in target_alliances]
        per_page = 5
        total_pages = max(1, (len(target_alliances) + per_page - 1) // per_page)
        page = min(page, total_pages - 1)
        start = page * per_page
        page_alliances = target_alliances[start:start + per_page]
        buttons = []
        for idx, a in enumerate(page_alliances):
            a_power, _ = calc_alliance_power(chat_id, a)
            btn_text = f"⚔️ {a['اسم']} | 👑 {a.get('قائد', '?')} | 💪{a_power:,}"
            real_idx = start + idx  # الترتيب الحقيقي في القائمة الكاملة
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"aat_{real_idx}|{uid}")])
        # أزرار التنقل
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"alliance_attack_list_{page-1}|{uid}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data=f"noop|{uid}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️ التالي", callback_data=f"alliance_attack_list_{page+1}|{uid}"))
        buttons.append(nav_row)
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"war_menu|{uid}"), InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self|{uid}")])
        await query.edit_message_text(
            f"🔥 *اختر تحالف للهجوم عليه*\n━━━━━━━━━━━━━━━\n"
            f"⚔️ تحالفك: *{my_alliance['اسم']}*\n"
            f"الصفحة {page+1}/{total_pages}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # === بدء هجوم تحالف على تحالف مختار (بالـ index) ===
    if data.startswith("aat_"):
        target_idx = int(data.split("_")[1])
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_war_kb)
            return
        my_alliance = get_country_alliance(chat_id, country["اسم"])
        if not my_alliance:
            await query.edit_message_text("❌ أنت لست في أي تحالف!", reply_markup=back_war_kb)
            return
        if country["اسم"] != my_alliance.get("قائد") and country["اسم"] not in my_alliance.get("جنرالات", []):
            await query.edit_message_text("🚫 *القائد الأعلى والجنرالات فقط* يمكنهم بدء هجوم التحالف!", parse_mode="Markdown", reply_markup=back_war_kb)
            return
        # جلب اسم التحالف المستهدف من القائمة المحفوظة
        aa_targets = context.user_data.get("aa_targets", {}).get(str(chat_id), [])
        if target_idx >= len(aa_targets):
            # fallback: إعادة جلب القائمة
            all_alliances_in_chat = get_all_alliances(chat_id)
            aa_targets = [a["اسم"] for a in all_alliances_in_chat if a["اسم"] != my_alliance["اسم"]]
            if target_idx >= len(aa_targets):
                await query.edit_message_text("❌ هذا التحالف لم يعد موجوداً!", reply_markup=back_war_kb)
                return
        target_alliance_name = aa_targets[target_idx]
        target_alliance = load_alliance(chat_id, target_alliance_name)
        if not target_alliance:
            await query.edit_message_text("❌ هذا التحالف لم يعد موجوداً!", reply_markup=back_war_kb)
            return
        # إنشاء تصويت
        vote_id = str(uuid.uuid4())[:8]
        # === إصلاح: إذا كان الطالب هو القائد يُسجَّل صوته مباشرة ===
        is_requester_leader = country["اسم"].strip() == my_alliance.get("قائد", "").strip()
        initial_yes = [country["اسم"]] if is_requester_leader else []
        initial_voted = [country["اسم"]] if is_requester_leader else []
        vote_doc = {
            "vote_id": vote_id, "chat_id": chat_id,
            "alliance": my_alliance["اسم"], "هدف": target_alliance_name,
            "هدف_نوع": "تحالف",
            "طالب": country["اسم"],
            "أصوات_نعم": initial_yes, "أصوات_لا": [], "صوّت": initial_voted,
            "انتهى": False, "وقت": time.time()
        }
        votes_col.insert_one(vote_doc)
        leaders = [my_alliance.get("قائد", "")] + my_alliance.get("جنرالات", [])
        leaders_text = ", ".join(l for l in leaders if l)
        leader_note = "\n✅ *القائد الأعلى وافق — سيُنفَّذ الهجوم فوراً!*" if is_requester_leader else ""
        vote_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ موافق", callback_data=f"vote_yes_{vote_id}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"vote_no_{vote_id}")],
            [InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self|{uid}")]
        ])
        await query.edit_message_text(
            f"🔥 *طلب هجوم تحالف عسكري!*\n━━━━━━━━━━━━━━━\n"
            f"⚔️ التحالف المهاجم: *{my_alliance['اسم']}*\n"
            f"🎯 التحالف المستهدف: *{target_alliance_name}*\n"
            f"👑 قائد الهدف: *{target_alliance.get('قائد', '?')}*\n"
            f"📢 طالب الهجوم: *{country['اسم']}*\n\n"
            f"👑 المصوتون (القيادة العليا): {leaders_text}\n\n"
            f"📌 *شروط الموافقة:*\n"
            f"✔️ موافقة القائد الأعلى → هجوم فوري\n"
            f"✔️ أو 5 أصوات موافقة → هجوم{leader_note}\n\n"
            f"⏰ مدة التصويت: 5 دقائق\n👇 يرجى من القيادة التصويت الآن:",
            parse_mode="Markdown",
            reply_markup=vote_keyboard
        )
        # === إذا القائد هو الطالب ننفذ الهجوم فوراً ===
        if is_requester_leader:
            votes_col.update_one({"vote_id": vote_id}, {"$set": {"انتهى": True}})
            await context.bot.send_message(chat_id,
                f"⚡ *هجوم فوري!*\n👑 القائد الأعلى وافق!\n\n🎯 الهدف: *{target_alliance_name}*\n\n⏳ جارٍ تنفيذ الهجوم...",
                parse_mode="Markdown"
            )
            vote_doc_final = votes_col.find_one({"vote_id": vote_id})
            await do_alliance_attack(context.bot, vote_doc_final, chat_id)
        else:
            context.job_queue.run_once(
                execute_alliance_attack, 300,
                data={"vote_id": vote_id, "chat_id": chat_id, "target": target_alliance_name, "alliance_name": my_alliance["اسم"]},
                name=f"vote_{vote_id}"
            )
        return

    if data == "how_to_missile":
        await query.edit_message_text(
            "🚀 *إطلاق الصواريخ*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `اطلق صاروخ [النوع] على [اسم الدولة] [العدد اختياري]`\n\n"
            "• كل صاروخ له قوة مختلفة حسب النوع 🔥\n"
            "• الأسلحة النووية والكيميائية تدمر 80% من الجيش تقريباً ☢️\n"
            "• وحدات الدفاع الجوي تزيد فرصة صد الصواريخ",
            parse_mode="Markdown", reply_markup=back_war_kb
        )
        return

    if data == "how_to_nuke":
        await query.edit_message_text(
            "☢️ *الضربة النووية*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب: `نووي [اسم الدولة]`\n\n"
            "📌 *الشروط:*\n"
            "• تحتاج منشأة نووية\n"
            "• تحتاج سلاح نووي واحد على الأقل\n"
            "• cooldown: 6 ساعات\n"
            "• خصم 30% من ذهبك\n"
            "• قوة الهجوم ×1.5\n\n"
            "⚠️ الدفاع الجوي يمكن أن يصد النووي!",
            parse_mode="Markdown", reply_markup=back_war_kb
        )
        return

    if data == "alliance_menu":
        await query.edit_message_text("🤝 *قائمة التحالف*\n\nاختر:", parse_mode="Markdown", reply_markup=alliance_menu_keyboard(uid))
        return

    # === أمر التحالف (للقائد فقط) ===
    if data == "alliance_order":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await query.edit_message_text("❌ أنت لست في أي تحالف!", reply_markup=back_alliance_kb)
            return
        if country["اسم"] != alliance.get("قائد"):
            await query.edit_message_text("🚫 *فقط القائد الأعلى* يمكنه إرسال أوامر التحالف!", parse_mode="Markdown", reply_markup=back_alliance_kb)
            return
        await query.edit_message_text(
            "📢 *أمر التحالف*\n━━━━━━━━━━━━━━━\n\n"
            "اكتب الأمر التالي لإرسال رسالة لجميع الأعضاء:\n\n"
            "`امر تحالف [رسالتك هنا]`\n\n"
            "📌 مثال:\n`امر تحالف استعدوا للحرب خلال ساعة!`",
            parse_mode="Markdown", reply_markup=back_alliance_kb
        )
        return

    if data == "my_alliance":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await query.edit_message_text(
                "❌ أنت لست في أي تحالف في هذا الكروب!\n\n"
                "لإنشاء تحالف: `انشاء تحالف [الاسم]`\n"
                "للانضمام: `طلب انضمام [الاسم]`",
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
                if m_name == alliance.get("قائد"):
                    role = "👑 القائد الأعلى"
                elif m_name in alliance.get("جنرالات", []):
                    role = "⭐ جنرال"
                elif m_name in alliance.get("عمداء", []):
                    role = "🎖️ عميد"
                else:
                    role = "🪖 جندي"
                members_text += f"  {role} | {m_name} — ⚔️{p:,}\n"
        await query.edit_message_text(
            f"🤝 *تحالف {alliance['اسم']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👑 القائد الأعلى: {alliance.get('قائد', 'غير محدد')}\n"
            f"👥 الأعضاء: {len(alliance.get('أعضاء', []))}\n"
            f"⚔️ القوة الإجمالية: {total_power:,}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🪖 *الأعضاء والرتب:*\n{members_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 للترقية (للقائد فقط):\n`ترقية [الاسم] [الرتبة]`",
            parse_mode="Markdown", reply_markup=back_alliance_kb
        )
        return

    if data == "alliance_army":
        country = load_country(uid)
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

    # === عرض طلبات الانضمام المعلقة (للقائد فقط) ===
    if data == "join_requests_list":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await query.edit_message_text("❌ أنت لست في أي تحالف!", reply_markup=back_alliance_kb)
            return
        if country["اسم"] != alliance.get("قائد"):
            await query.edit_message_text("🚫 *فقط القائد الأعلى* يمكنه رؤية طلبات الانضمام!", parse_mode="Markdown", reply_markup=back_alliance_kb)
            return
        # جلب الطلبات المعلقة لهذا التحالف في هذا القروب
        pending = list(db["join_requests"].find({
            "chat_id": chat_id,
            "تحالف": alliance["اسم"],
            "تم_المعالجة": False
        }))
        if not pending:
            await query.edit_message_text(
                f"📩 *طلبات الانضمام — {alliance['اسم']}*\n\n"
                "✅ لا توجد طلبات انضمام معلقة حالياً.",
                parse_mode="Markdown", reply_markup=back_alliance_kb
            )
            return
        msg = f"📩 *طلبات الانضمام — {alliance['اسم']}*\n━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for req in pending:
            applicant = get_country_by_name(req["اسم_الدولة"])
            power = calc_power(applicant.get("وحدات", {})) if applicant else 0
            level = get_level(applicant.get("انتصارات", 0)) if applicant else "غير معروف"
            msg += f"🏳️ *{req['اسم_الدولة']}*\n   ⚔️ {power:,} | {level}\n\n"
            buttons.append([
                InlineKeyboardButton(f"✅ قبول {req['اسم_الدولة']}", callback_data=f"join_accept_{req['request_id']}"),
                InlineKeyboardButton(f"❌ رفض", callback_data=f"join_reject_{req['request_id']}")
            ])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"alliance_menu|{uid}")])
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # === قائمة طرد الأعضاء (للقائد فقط) ===
    if data.startswith("kick_member_list_"):
        page = int(data.split("_")[3]) if len(data.split("_")) > 3 and data.split("_")[3].isdigit() else 0
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await query.edit_message_text("❌ أنت لست في أي تحالف!", reply_markup=back_alliance_kb)
            return
        if country["اسم"] != alliance.get("قائد"):
            await query.edit_message_text("🚫 *فقط القائد الأعلى* يمكنه طرد الأعضاء!", parse_mode="Markdown", reply_markup=back_alliance_kb)
            return
        # قائمة الأعضاء (بدون القائد نفسه)
        members = [m for m in alliance.get("أعضاء", []) if m != alliance.get("قائد")]
        if not members:
            await query.edit_message_text("❌ لا يوجد أعضاء لطردهم! أنت الوحيد في التحالف.", reply_markup=back_alliance_kb)
            return
        # حفظ القائمة مؤقتاً
        if "kick_targets" not in context.user_data:
            context.user_data["kick_targets"] = {}
        context.user_data["kick_targets"][str(chat_id)] = members
        per_page = 5
        total_pages = max(1, (len(members) + per_page - 1) // per_page)
        page = min(page, total_pages - 1)
        start = page * per_page
        page_members = members[start:start + per_page]
        buttons = []
        for idx, m_name in enumerate(page_members):
            m = get_country_by_name(m_name)
            power = calc_power(m.get("وحدات", {})) if m else 0
            if m_name in alliance.get("جنرالات", []):
                role = "⭐"
            elif m_name in alliance.get("عمداء", []):
                role = "🎖️"
            else:
                role = "🪖"
            btn_text = f"{role} {m_name} ⚔️{power:,}"
            real_idx = start + idx
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"kc_{real_idx}|{uid}")])
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"kick_member_list_{page-1}|{uid}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data=f"noop|{uid}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️ التالي", callback_data=f"kick_member_list_{page+1}|{uid}"))
        buttons.append(nav_row)
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"alliance_menu|{uid}"), InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self|{uid}")])
        await query.edit_message_text(
            f"🚫 *طرد عضو من التحالف*\n━━━━━━━━━━━━━━━\n"
            f"🤝 التحالف: *{alliance['اسم']}*\n"
            f"الصفحة {page+1}/{total_pages}\n\n"
            f"⚠️ اختر العضو الذي تريد طرده:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # === تأكيد طرد عضو (بالـ index) ===
    if data.startswith("kc_"):
        target_idx = int(data.split("_")[1])
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance or country["اسم"] != alliance.get("قائد"):
            await query.edit_message_text("🚫 فقط القائد الأعلى!", reply_markup=back_alliance_kb)
            return
        # جلب اسم العضو من القائمة المحفوظة
        kick_targets = context.user_data.get("kick_targets", {}).get(str(chat_id), [])
        if target_idx >= len(kick_targets):
            members = [m for m in alliance.get("أعضاء", []) if m != alliance.get("قائد")]
            if target_idx >= len(members):
                await query.edit_message_text("❌ هذا العضو لم يعد في التحالف!", reply_markup=back_alliance_kb)
                return
            kick_targets = members
        target_name = kick_targets[target_idx]
        if target_name not in alliance.get("أعضاء", []):
            await query.edit_message_text("❌ هذا العضو لم يعد في التحالف!", reply_markup=back_alliance_kb)
            return
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد الطرد", callback_data=f"kd_{target_idx}|{uid}"),
             InlineKeyboardButton("❌ إلغاء", callback_data=f"alliance_menu|{uid}")]
        ])
        await query.edit_message_text(
            f"⚠️ *هل تريد طرد {target_name}؟*\n\n"
            f"🤝 التحالف: *{alliance['اسم']}*\n"
            f"🚫 العضو: *{target_name}*\n\n"
            f"❗ سيتم إزالته من التحالف فوراً!",
            parse_mode="Markdown", reply_markup=confirm_kb
        )
        return

    # === تنفيذ الطرد (بالـ index) ===
    if data.startswith("kd_"):
        target_idx = int(data.split("_")[1])
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_alliance_kb)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance or country["اسم"] != alliance.get("قائد"):
            await query.edit_message_text("🚫 فقط القائد الأعلى!", reply_markup=back_alliance_kb)
            return
        kick_targets = context.user_data.get("kick_targets", {}).get(str(chat_id), [])
        if target_idx >= len(kick_targets):
            members = [m for m in alliance.get("أعضاء", []) if m != alliance.get("قائد")]
            if target_idx >= len(members):
                await query.edit_message_text("❌ هذا العضو لم يعد في التحالف!", reply_markup=back_alliance_kb)
                return
            kick_targets = members
        target_name = kick_targets[target_idx]
        if target_name not in alliance.get("أعضاء", []):
            await query.edit_message_text("❌ هذا العضو لم يعد في التحالف!", reply_markup=back_alliance_kb)
            return
        if target_name == alliance.get("قائد"):
            await query.edit_message_text("❌ لا يمكنك طرد نفسك!", reply_markup=back_alliance_kb)
            return
        # تنفيذ الطرد
        alliance["أعضاء"].remove(target_name)
        if target_name in alliance.get("جنرالات", []):
            alliance["جنرالات"].remove(target_name)
        if target_name in alliance.get("عمداء", []):
            alliance["عمداء"].remove(target_name)
        save_alliance(alliance)
        await query.edit_message_text(
            f"🚫 *تم طرد {target_name}!*\n\n"
            f"🤝 التحالف: *{alliance['اسم']}*\n"
            f"👥 الأعضاء المتبقين: {len(alliance['أعضاء'])}",
            parse_mode="Markdown", reply_markup=alliance_menu_keyboard(uid)
        )
        # إعلام في القروب
        try:
            await context.bot.send_message(chat_id,
                f"🚫 *{target_name}* تم طرده من تحالف *{alliance['اسم']}* بأمر من القائد *{country['اسم']}*!",
                parse_mode="Markdown"
            )
        except:
            pass
        return

    # === تأكيد حذف الدولة ===
    if data == "confirm_delete_country":
        country = load_country(uid)
        if not country:
            await query.edit_message_text("❌ ليس لديك دولة!", reply_markup=back_main_kb)
            return
        # حذف من التحالفات
        all_alliances = list(alliances_col.find({"أعضاء": country["اسم"]}))
        for alliance in all_alliances:
            alliance["أعضاء"].remove(country["اسم"])
            if country["اسم"] in alliance.get("جنرالات", []):
                alliance["جنرالات"].remove(country["اسم"])
            if country["اسم"] in alliance.get("عمداء", []):
                alliance["عمداء"].remove(country["اسم"])
            if len(alliance["أعضاء"]) == 0:
                alliances_col.delete_one({"_id": alliance["_id"]})
            else:
                if alliance.get("قائد") == country["اسم"] and alliance["أعضاء"]:
                    alliance["قائد"] = alliance["أعضاء"][0]
                save_alliance(alliance)
        # حذف الدولة
        countries_col.delete_one({"user_id": uid})
        await query.edit_message_text(
            "🗑️ *تم حذف دولتك بنجاح!*\n\n"
            "يمكنك إنشاء دولة جديدة:\n`انشاء دولة [الاسم]`",
            parse_mode="Markdown"
        )
        return

    if data == "cancel_delete_country":
        await query.edit_message_text("✅ تم إلغاء الحذف.", reply_markup=main_menu_keyboard(uid))
        return

    # === نظام التصويت المحسّن: القائد يوافق = هجوم فوري أو 5 أصوات ===
    if data.startswith("vote_yes_") or data.startswith("vote_no_"):
        vote_type = "yes" if data.startswith("vote_yes_") else "no"
        vote_id = data.split("_", 2)[2]
        vote = votes_col.find_one({"vote_id": vote_id})
        if not vote:
            await query.answer("❌ انتهت مدة التصويت!", show_alert=True)
            return
        if vote.get("انتهى"):
            await query.answer("❌ انتهى التصويت بالفعل!", show_alert=True)
            return
        country = load_country(uid)
        if not country:
            await query.answer("❌ ليس لديك دولة!", show_alert=True)
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance or alliance["اسم"] != vote["alliance"]:
            await query.answer("❌ لست في هذا التحالف!", show_alert=True)
            return
        # فقط القائد والجنرالات يصوتون
        if country["اسم"] != alliance.get("قائد") and country["اسم"] not in alliance.get("جنرالات", []):
            await query.answer("❌ التصويت مسموح للقائد الأعلى والجنرالات فقط!", show_alert=True)
            return
        if country["اسم"] in vote.get("صوّت", []):
            await query.answer("✅ لقد صوّتت بالفعل!", show_alert=True)
            return
        update_field = "أصوات_نعم" if vote_type == "yes" else "أصوات_لا"
        votes_col.update_one({"vote_id": vote_id}, {
            "$push": {"صوّت": country["اسم"], update_field: country["اسم"]}
        })
        await query.answer(f"✅ تم تسجيل صوتك كقائد عسكري!")
        
        # === التحقق من شروط الهجوم الفوري ===
        # إعادة تحميل التصويت بعد التحديث
        vote = votes_col.find_one({"vote_id": vote_id})
        yes_count = len(vote.get("أصوات_نعم", []))
        # === إصلاح: مقارنة الأسماء بعد strip() لتفادي المسافات الخفية ===
        alliance_leader = alliance.get("قائد", "").strip()
        is_leader_voted_yes = any(v.strip() == alliance_leader for v in vote.get("أصوات_نعم", []))
        
        # شرط 1: القائد وافق → هجوم فوري
        # شرط 2: 5 أصوات موافقة → هجوم فوري
        if is_leader_voted_yes or yes_count >= 5:
            # إلغاء الجوب المجدول
            current_jobs = context.job_queue.get_jobs_by_name(f"vote_{vote_id}")
            for job in current_jobs:
                job.schedule_removal()
            # تنفيذ الهجوم فوراً
            votes_col.update_one({"vote_id": vote_id}, {"$set": {"انتهى": True}})
            reason = "👑 القائد الأعلى وافق!" if is_leader_voted_yes else f"✅ تم جمع {yes_count} أصوات موافقة!"
            # إرسال رسالة إعلان ثم تنفيذ الهجوم
            await context.bot.send_message(chat_id,
                f"⚡ *هجوم فوري!*\n{reason}\n\n🎯 الهدف: *{vote['هدف']}*\n\n⏳ جارٍ تنفيذ الهجوم...",
                parse_mode="Markdown"
            )
            # تنفيذ الهجوم مباشرة
            await do_alliance_attack(context.bot, vote, chat_id)
        return

    # === معالجة طلبات الانضمام (قبول/رفض من القائد) ===
    if data.startswith("join_accept_") or data.startswith("join_reject_"):
        action = "accept" if data.startswith("join_accept_") else "reject"
        request_id = data.split("_", 2)[2]
        # البحث عن الطلب في قاعدة البيانات
        join_request = db["join_requests"].find_one({"request_id": request_id})
        if not join_request:
            await query.answer("❌ هذا الطلب لم يعد موجوداً!", show_alert=True)
            return
        if join_request.get("تم_المعالجة"):
            await query.answer("❌ تم معالجة هذا الطلب مسبقاً!", show_alert=True)
            return
        # التحقق أن المستجيب هو القائد
        alliance = load_alliance(join_request["chat_id"], join_request["تحالف"])
        if not alliance:
            await query.answer("❌ التحالف لم يعد موجوداً!", show_alert=True)
            return
        responder_country = load_country(uid)
        if not responder_country or responder_country["اسم"] != alliance.get("قائد"):
            await query.answer("❌ فقط القائد الأعلى يمكنه قبول أو رفض الطلبات!", show_alert=True)
            return
        
        applicant_country = get_country_by_name(join_request["اسم_الدولة"])
        if action == "accept":
            if not applicant_country:
                await query.answer("❌ دولة المتقدم لم تعد موجودة!", show_alert=True)
                db["join_requests"].update_one({"request_id": request_id}, {"$set": {"تم_المعالجة": True}})
                return
            # التحقق أن اللاعب ليس في تحالف آخر
            existing = get_country_alliance(join_request["chat_id"], join_request["اسم_الدولة"])
            if existing:
                await query.edit_message_text(f"❌ *{join_request['اسم_الدولة']}* انضم لتحالف آخر بالفعل!", parse_mode="Markdown")
                db["join_requests"].update_one({"request_id": request_id}, {"$set": {"تم_المعالجة": True}})
                return
            alliance["أعضاء"].append(join_request["اسم_الدولة"])
            save_alliance(alliance)
            db["join_requests"].update_one({"request_id": request_id}, {"$set": {"تم_المعالجة": True}})
            await query.edit_message_text(
                f"✅ *تم قبول {join_request['اسم_الدولة']}!*\n\n"
                f"🤝 انضم إلى تحالف *{alliance['اسم']}*\n"
                f"👥 عدد الأعضاء الآن: {len(alliance['أعضاء'])}",
                parse_mode="Markdown"
            )
            # إعلام المتقدم
            try:
                await context.bot.send_message(join_request["chat_id"],
                    f"🎉 *{join_request['اسم_الدولة']}*، تم قبولك في تحالف *{alliance['اسم']}*! 🤝",
                    parse_mode="Markdown"
                )
            except:
                pass
        else:
            db["join_requests"].update_one({"request_id": request_id}, {"$set": {"تم_المعالجة": True}})
            await query.edit_message_text(
                f"❌ *تم رفض طلب {join_request['اسم_الدولة']}*\n\nللانضمام لتحالف *{alliance['اسم']}*",
                parse_mode="Markdown"
            )
            # إعلام المتقدم
            try:
                await context.bot.send_message(join_request["chat_id"],
                    f"❌ *{join_request['اسم_الدولة']}*، للأسف تم رفض طلب انضمامك لتحالف *{alliance['اسم']}*",
                    parse_mode="Markdown"
                )
            except:
                pass
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.effective_chat.type == "private":
        return

    text = update.message.text.strip()
    user = update.effective_user
    chat_id = update.effective_chat.id
    uid = user.id

    # === تتبع اللاعب في القروب ===
    country_track = load_country(uid)
    if country_track:
        track_player_in_chat(chat_id, uid, country_track["اسم"])

    # === تتبع رسائل البوت لكل مستخدم ===
    if "bot_msgs" not in context.user_data:
        context.user_data["bot_msgs"] = {}
    # مفتاح فريد لكل شات (لدعم مجموعات متعددة)
    chat_key = str(chat_id)
    if chat_key not in context.user_data["bot_msgs"]:
        context.user_data["bot_msgs"][chat_key] = []

    async def reply(msg, keyboard=None):
        if keyboard is None:
            keyboard = action_keyboard("main_menu", uid)
        sent = await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)
        # حفظ message_id للرسالة المرسلة
        context.user_data["bot_msgs"][chat_key].append(sent.message_id)
        # الاحتفاظ بآخر 50 رسالة فقط لتوفير الذاكرة
        if len(context.user_data["bot_msgs"][chat_key]) > 50:
            context.user_data["bot_msgs"][chat_key] = context.user_data["bot_msgs"][chat_key][-50:]
        return sent

    async def cleanup_bot_messages():
        """حذف جميع رسائل البوت السابقة لهذا المستخدم في هذا الشات"""
        old_msgs = context.user_data["bot_msgs"].get(chat_key, [])
        for msg_id in old_msgs:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except:
                pass  # الرسالة قد تكون محذوفة مسبقاً أو قديمة جداً
        context.user_data["bot_msgs"][chat_key] = []

    if text in ["مساعدة", "/help"]:
        # حذف رسائل البوت السابقة قبل إرسال رسالة جديدة نظيفة
        await cleanup_bot_messages()
        await reply("🌑 *عرش الظلال* 🌑\n\nاختر ما تريد:", main_menu_keyboard(uid))
        return

    if text.startswith("انشاء دولة "):
        parts = text.split(" ", 2)
        country_name = parts[2].strip() if len(parts) > 2 else ""
        if not country_name:
            await reply("❌ اكتب اسم دولتك!\nمثال: `انشاء دولة المملكة الظلامية`")
            return
        if load_country(uid):
            await reply("❌ لديك دولة بالفعل!", main_menu_keyboard(uid))
            return
        if get_country_by_name(country_name):
            await reply("❌ هذا الاسم مأخوذ!")
            return
        new_country = {
            "user_id": uid,
            "اسم": country_name,
            "مالك": user.first_name,
            "ذهب": 1000, "بنك": 0, "آخر استثمار": 0,
            "وحدات": {}, "مباني": [],
            "انتصارات": 0, "خسائر": 0,
            "نظام": None, "آخر تحديث": time.time(),
            "حماية حتى": time.time() + SHIELD_DURATION,
        }
        save_country(new_country)
        # تتبع اللاعب في القروب
        track_player_in_chat(chat_id, uid, country_name)
        await reply(
            f"🌑 *تم إنشاء دولتك بنجاح!* 🌑\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏳️ الدولة: *{country_name}*\n"
            f"👤 الحاكم: {user.first_name}\n"
            f"💰 الرصيد: 1,000 ذهب\n"
            f"🌍 دولتك عالمية في كل الكروبات!\n\n"
            f"🛡️ *محمي لمدة ساعة واحدة!*\n\n"
            f"👇 استخدم الأزرار للتنقل:",
            main_menu_keyboard(uid)
        )
        return

    # === اختيار نظام ===
    if text.startswith("اختر نظام "):
        parts = text.split(" ", 2)
        system_name = parts[2].strip() if len(parts) > 2 else ""
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        if system_name not in IDEOLOGIES:
            await reply(f"❌ النظام `{system_name}` غير موجود!\nالمتاح: " + "، ".join(IDEOLOGIES.keys()))
            return
        country["نظام"] = system_name
        save_country(country)
        info = IDEOLOGIES[system_name]
        await reply(f"{info['رمز']} *تم اختيار نظام {system_name}!*\n\n{info['وصف']}", main_menu_keyboard(uid))
        return

    if text.startswith("اشتري "):
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        if text == "اشتري حماية":
            if country.get("ذهب", 0) < 5000:
                await reply(f"❌ لا يوجد ذهب كافٍ!\nتحتاج: 💰5,000\nرصيدك: 💰{country.get('ذهب', 0):,}")
                return
            country["ذهب"] -= 5000
            country["حماية حتى"] = time.time() + SHIELD_DURATION
            cap_gold(country)
            save_country(country)
            await reply("🛡️ *تم شراء الحماية!*\nأنت محمي لمدة ساعة واحدة! 💪", main_menu_keyboard(uid))
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
        # === فهم ذكي للأسماء (Fuzzy Matching) ===
        matched_unit = fuzzy_find_unit(unit_name)
        if not matched_unit:
            await reply(f"❌ لم يتم العثور على الوحدة `{unit_name}`!\n\n💡 جرّب كتابة الاسم بشكل مختلف أو استخدم الأسواق 🛒", reply_markup=main_menu_keyboard(uid))
            return
        if matched_unit != unit_name:
            # إعلام اللاعب بالتصحيح
            unit_name = matched_unit
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
        cap_gold(country)
        save_country(country)
        await reply(f"✅ *تم الشراء!*\n\n🪖 {unit_name} × {count}\n💰 التكلفة: {total_cost:,}\n💰 المتبقي: {country['ذهب']:,}", main_menu_keyboard(uid))
        return

    if text.startswith("بناء "):
        parts = text.split(" ", 1)
        building_name = parts[1].strip() if len(parts) > 1 else ""
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        # === فهم ذكي لاسم المبنى ===
        matched_building = fuzzy_find_building(building_name)
        if not matched_building:
            await reply(f"❌ المبنى `{building_name}` غير موجود!\n\n💡 استخدم 🏗️ المباني لمعرفة الأسماء الصحيحة")
            return
        building_name = matched_building
        # التحقق من المباني غير القابلة للتكرار
        if building_name in NON_STACKABLE_BUILDINGS and building_name in country.get("مباني", []):
            await reply(f"❌ لا يمكنك بناء *{building_name}* مرة أخرى!\nهذا المبنى يُبنى مرة واحدة فقط.")
            return
        d = BUILDINGS[building_name]
        if country.get("ذهب", 0) < d["سعر"]:
            await reply(f"❌ لا يوجد ذهب كافٍ!\nالتكلفة: 💰{d['سعر']:,}\nرصيدك: 💰{country.get('ذهب', 0):,}")
            return
        country["ذهب"] -= d["سعر"]
        if "مباني" not in country: country["مباني"] = []
        country["مباني"].append(building_name)
        cap_gold(country)
        save_country(country)
        await reply(f"🏗️ *تم البناء!*\n\n🏛️ {building_name}\n📌 {d['وصف']}\n💰 المتبقي: {country['ذهب']:,}", main_menu_keyboard(uid))
        return

    if text == "استثمار مالي":
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        country = update_resources(country)
        now = time.time()
        
        time_left = 600 - (now - country.get("آخر استثمار", 0))
        if time_left > 0:
            await reply(f"⏳ انتظر {int(time_left/60)} دقيقة و{int(time_left%60)} ثانية للاستثمار مجدداً 🕐")
            return
            
        amount = country.get("ذهب", 0)
        if amount <= 0:
            await reply("❌ ليس لديك ذهب للاستثمار!")
            return
            
        rate = random.uniform(0.50, 2.00) 
        profit_amount = int(amount * rate)
        
        country["ذهب"] += profit_amount
        country["بنك"] = country.get("بنك", 0) + profit_amount
        country["آخر استثمار"] = now
        cap_gold(country)
        save_country(country)
        
        rate_percent = int(rate * 100)
        await reply(
            f"🏦 *نتائج الاستثمار المالي المضمون!*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 رأس المال المستثمر: {amount:,}\n"
            f"📈 نسبة الربح الصافية: *+{rate_percent}%*\n"
            f"💎 الأرباح المضافة: *+{profit_amount:,} ذهب*\n\n"
            f"💰 رصيدك الكلي الآن: *{country['ذهب']:,}*\n\n"
            f"⏰ الاستثمار القادم متاح بعد 10 دقائق!",
            main_menu_keyboard(uid)
        )
        return

    if text.startswith("هاجم "):
        parts = text.split(" ", 1)
        target_name = parts[1].strip() if len(parts) > 1 else ""
        attacker = load_country(uid)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        defender = get_country_by_name(target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if defender["user_id"] == uid:
            await reply("❌ لا يمكنك مهاجمة نفسك! 😂")
            return
        if is_protected(defender):
            remaining = max(1, int((defender["حماية حتى"] - time.time()) / 60))
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} دقيقة!")
            return
        attacker = update_resources(attacker)
        defender = update_resources(defender)
        
        # === حساب الدفاع الجماعي ===
        def_alliance, collective_def = calc_collective_defense(chat_id, target_name)
        if def_alliance and collective_def > 0:
            defense_power = collective_def * random.uniform(0.7, 1.3)
            defense_note = f"🛡️ دفاع تحالف *{def_alliance['اسم']}* الجماعي! (+20%)\nقوة التحالف: {collective_def:,}"
        else:
            defense_power = calc_power(defender.get("وحدات", {})) * random.uniform(0.7, 1.3)
            defense_note = ""
        
        attack_power = calc_power(attacker.get("وحدات", {})) * random.uniform(0.7, 1.3)
        if "دفاع جوي" in defender.get("مباني", []):
            air_power = sum(UNITS[u]["قوة"] * c for u, c in attacker.get("وحدات", {}).items() if u in UNITS and UNITS[u]["نوع"] == "جوي")
            attack_power -= air_power * 0.4
        # تأثير وحدات الدفاع الجوي
        ad_reduction = calc_air_defense_power(defender.get("وحدات", {})) * 0.3
        air_attack = sum(UNITS[u]["قوة"] * c for u, c in attacker.get("وحدات", {}).items() if u in UNITS and UNITS[u]["نوع"] == "جوي")
        attack_power -= min(ad_reduction, air_attack * 0.5)
        
        if attacker.get("نظام") == "ديكتاتوري": attack_power *= 1.3
        if attacker.get("نظام") == "شيوعي": attack_power *= 1.2
        if defender.get("نظام") == "شيوعي": defense_power *= 1.2

        if attack_power > defense_power:
            stolen_gold = int(defender.get("ذهب", 0) * 0.3)
            attacker["ذهب"] = attacker.get("ذهب", 0) + stolen_gold
            defender["ذهب"] = max(0, defender.get("ذهب", 0) - stolen_gold)
            attacker["انتصارات"] = attacker.get("انتصارات", 0) + 1
            defender["خسائر"] = defender.get("خسائر", 0) + 1
            att_loss = 20
            def_loss = 40
            if "مستشفى عسكري" in attacker.get("مباني", []):
                att_loss = max(5, att_loss - 10)
            if "مستشفى عسكري" in defender.get("مباني", []):
                def_loss = max(10, def_loss - 10)
            for unit in attacker.get("وحدات", {}): attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * (1 - att_loss/100))
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * (1 - def_loss/100))
            defender["حماية حتى"] = time.time() + SHIELD_DURATION
            cap_gold(attacker)
            save_country(attacker)
            save_country(defender)
            try:
                await send_attack_notification(context.bot, chat_id, target_name, attacker["اسم"], "هجوم عادي", damage=int(defense_power))
            except:
                pass
            await reply(
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🏳️ المدافع: *{target_name}*\n"
                f"{defense_note}\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏆 *{attacker['اسم']} انتصر!*\n\n"
                f"📊 *تقرير المعركة:*\n"
                f"💰 غنائم: {stolen_gold:,} ذهب\n"
                f"💀 خسائر المهاجم: {att_loss}%\n"
                f"💀 خسائر المدافع: {def_loss}%\n"
                f"🛡️ المدافع محمي لمدة ساعة",
                main_menu_keyboard(uid)
            )
        else:
            attacker["خسائر"] = attacker.get("خسائر", 0) + 1
            defender["انتصارات"] = defender.get("انتصارات", 0) + 1
            att_loss = 50
            def_loss = 15
            if "مستشفى عسكري" in attacker.get("مباني", []):
                att_loss = max(20, att_loss - 10)
            if "مستشفى عسكري" in defender.get("مباني", []):
                def_loss = max(5, def_loss - 10)
            for unit in attacker.get("وحدات", {}): attacker["وحدات"][unit] = int(attacker["وحدات"][unit] * (1 - att_loss/100))
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * (1 - def_loss/100))
            defender["حماية حتى"] = time.time() + SHIELD_DURATION
            save_country(attacker)
            save_country(defender)
            try:
                await send_attack_notification(context.bot, chat_id, target_name, attacker["اسم"], "هجوم عادي", damage=int(defense_power))
            except:
                pass
            await reply(
                f"⚔️ *نتيجة المعركة* ⚔️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🏳️ المدافع: *{target_name}*\n"
                f"{defense_note}\n\n"
                f"🔥 قوة الهجوم: {int(attack_power):,}\n🛡️ قوة الدفاع: {int(defense_power):,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🛡️ *{target_name}* صدّ الهجوم!\n\n"
                f"📊 *تقرير المعركة:*\n"
                f"💀 خسائر المهاجم: {att_loss}%\n"
                f"💀 خسائر المدافع: {def_loss}%",
                main_menu_keyboard(uid)
            )
        return

    # === نظام النووي ===
    if text.startswith("نووي "):
        parts = text.split(" ", 1)
        target_name = parts[1].strip() if len(parts) > 1 else ""
        attacker = load_country(uid)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        if "منشأة نووية" not in attacker.get("مباني", []):
            await reply("❌ تحتاج *منشأة نووية* أولاً! ☢️")
            return
        # التحقق من امتلاك سلاح نووي
        nuke_units = {u: c for u, c in attacker.get("وحدات", {}).items() if u in UNITS and UNITS[u]["نوع"] == "نووي" and c > 0}
        if not nuke_units:
            await reply("❌ لا تملك أي سلاح نووي!\nاشتري: كيميائي / نووي تكتيكي / قنبلة نووية")
            return
        # cooldown 6 ساعات
        now = time.time()
        last_nuke = attacker.get("آخر_نووي", 0)
        nuke_cd = 6 * 3600
        if now - last_nuke < nuke_cd:
            remaining = int((nuke_cd - (now - last_nuke)) / 60)
            await reply(f"⏳ الضربة النووية غير جاهزة!\nمتبقي: {remaining} دقيقة")
            return
        defender = get_country_by_name(target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if defender["user_id"] == uid:
            await reply("❌ لا يمكنك ضرب نفسك نووياً! 😂")
            return
        if is_protected(defender):
            remaining = max(1, int((defender["حماية حتى"] - time.time()) / 60))
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} دقيقة!")
            return
        attacker = update_resources(attacker)
        defender = update_resources(defender)
        # خصم 30% من ذهب المهاجم
        gold_cost = int(attacker.get("ذهب", 0) * 0.30)
        attacker["ذهب"] = max(0, attacker.get("ذهب", 0) - gold_cost)
        # استهلاك وحدة نووية واحدة (الأقوى)
        best_nuke = max(nuke_units.keys(), key=lambda u: UNITS[u]["قوة"])
        attacker["وحدات"][best_nuke] -= 1
        if attacker["وحدات"][best_nuke] <= 0:
            del attacker["وحدات"][best_nuke]
        attacker["آخر_نووي"] = now
        # احتمال الصد بناء على الدفاع الجوي
        intercept_chance = calc_nuke_intercept_chance(defender)
        intercepted = random.random() < intercept_chance
        if intercepted:
            cap_gold(attacker)
            save_country(attacker)
            try:
                await send_attack_notification(context.bot, chat_id, target_name, attacker["اسم"], "نووي", amount=1, damage=0)
            except:
                pass
            await reply(
                f"☢️ *ضربة نووية — تم الصد!* 🛡️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🎯 الهدف: *{target_name}*\n"
                f"🚀 السلاح: *{best_nuke}*\n\n"
                f"🛡️ دفاعات *{target_name}* الجوية صدّت الضربة!\n"
                f"📊 فرصة الصد كانت: {int(intercept_chance*100)}%\n\n"
                f"💰 خسرت: {gold_cost:,} ذهب\n"
                f"💣 خسرت: 1× {best_nuke}",
                main_menu_keyboard(uid)
            )
            return
        # النووي نجح — قوة ×1.5
        nuke_power = UNITS[best_nuke]["قوة"] * 1.5
        # تدمير 80% من جيش المدافع
        for unit in defender.get("وحدات", {}):
            defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.2)
        # تدمير مبنى عشوائي
        destroyed_building = ""
        if defender.get("مباني"):
            destroyed_building = random.choice(defender["مباني"])
            defender["مباني"].remove(destroyed_building)
        # سرقة 40% ذهب
        stolen = int(defender.get("ذهب", 0) * 0.4)
        attacker["ذهب"] += stolen
        defender["ذهب"] = max(0, defender.get("ذهب", 0) - stolen)
        defender["حماية حتى"] = time.time() + SHIELD_DURATION
        attacker["انتصارات"] = attacker.get("انتصارات", 0) + 1
        defender["خسائر"] = defender.get("خسائر", 0) + 1
        cap_gold(attacker)
        save_country(attacker)
        save_country(defender)
        try:
            await send_attack_notification(context.bot, chat_id, target_name, attacker["اسم"], "نووي", amount=1, damage=int(nuke_power))
        except:
            pass
        building_text = f"\n🏗️ مبنى مدمر: {destroyed_building}" if destroyed_building else ""
        await reply(
            f"☢️ *ضربة نووية ناجحة!* ☢️\n━━━━━━━━━━━━━━━\n"
            f"🏴 المهاجم: *{attacker['اسم']}*\n🎯 الهدف: *{target_name}*\n"
            f"🚀 السلاح: *{best_nuke}* (قوة ×1.5 = {int(nuke_power)})\n\n"
            f"📊 *تقرير الضربة:*\n"
            f"💀 دمار جيش المدافع: 80%{building_text}\n"
            f"💰 غنائم: {stolen:,} ذهب\n"
            f"💰 تكلفة الهجوم: {gold_cost:,} ذهب\n"
            f"🛡️ المدافع محمي لمدة ساعة\n"
            f"⏰ النووي القادم بعد 6 ساعات",
            main_menu_keyboard(uid)
        )
        return

    if text.startswith("اطلق صاروخ "):
        parts = text.split(" ", 1)[1].split()
        if len(parts) < 3:
            await reply("❌ الاستخدام: `اطلق صاروخ [النوع] على [الدولة] [العدد اختياري]`")
            return

        if "على" in parts:
            sep_idx = parts.index("على")
        elif "علي" in parts:
            sep_idx = parts.index("علي")
        else:
            await reply("❌ اكتب: `اطلق صاروخ [النوع] على [الدولة] [العدد اختياري]`")
            return

        missile_name = " ".join(parts[:sep_idx]).strip()
        tail = parts[sep_idx + 1:]
        if not missile_name or not tail:
            await reply("❌ اكتب: `اطلق صاروخ [النوع] على [الدولة] [العدد اختياري]`")
            return

        amount = 1
        if tail[-1].isdigit():
            amount = int(tail[-1])
            target_name = " ".join(tail[:-1]).strip()
        else:
            target_name = " ".join(tail).strip()

        if amount <= 0:
            await reply("❌ العدد يجب أن يكون أكبر من صفر!")
            return

        attacker = load_country(uid)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return

        missile_type = fuzzy_find_unit(missile_name)
        if not missile_type:
            await reply(f"❌ نوع الصاروخ `{missile_name}` غير موجود!")
            return
        missile_data = UNITS[missile_type]
        if missile_data["نوع"] != "صواريخ":
            await reply("❌ هذا ليس صاروخاً!")
            return

        defender = get_country_by_name(target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if defender["user_id"] == uid:
            await reply("❌ لا يمكنك مهاجمة نفسك!")
            return
        if is_protected(defender):
            remaining = max(1, int((defender["حماية حتى"] - time.time()) / 60))
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} دقيقة!")
            return

        attacker = update_resources(attacker)
        now_hour = int(time.time() // 3600)
        if attacker.get("آخر_ساعة_صواريخ") != now_hour:
            attacker["آخر_ساعة_صواريخ"] = now_hour
            attacker["صواريخ_هذه_الساعة"] = 0

        if attacker.get("صواريخ_هذه_الساعة", 0) + amount > 100:
            remaining = 100 - attacker.get("صواريخ_هذه_الساعة", 0)
            await reply(f"⏳ الحد الأقصى هو 100 صاروخ في الساعة.\nالمتاح الآن: {remaining}")
            return

        if attacker.get("وحدات", {}).get(missile_type, 0) < amount:
            await reply(f"❌ لا تملك هذه الكمية من *{missile_type}*!")
            return

        attacker["وحدات"][missile_type] -= amount
        attacker["صواريخ_هذه_الساعة"] = attacker.get("صواريخ_هذه_الساعة", 0) + amount

        air_def = calc_air_defense_power(defender.get("وحدات", {}))
        defense_boost = 1.0
        if "دفاع جوي" in defender.get("مباني", []):
            defense_boost += 0.10
        if "قاعدة صواريخ" in defender.get("مباني", []):
            defense_boost += 0.05

        base_intercept = min(0.90, (air_def / (air_def + 800)) * defense_boost)
        intercepted = 0
        for _ in range(amount):
            if random.random() < base_intercept:
                intercepted += 1

        hit_count = amount - intercepted
        damage = int(hit_count * missile_data["قوة"])
        if defender.get("نظام") == "عسكري":
            damage = int(damage * 0.95)

        save_country(attacker)
        save_country(defender)
        try:
            await send_attack_notification(context.bot, chat_id, target_name, attacker["اسم"], "صاروخ", amount=amount, damage=damage)
        except:
            pass

        await reply(
            f"🚀 *إطلاق صاروخي*\n━━━━━━━━━━━━━━━\n"
            f"🎯 الهدف: *{target_name}*\n"
            f"🧨 النوع: *{missile_type}*\n"
            f"📦 الكمية: {amount}\n"
            f"🛡️ تم اعتراض: {intercepted}\n"
            f"💥 وصل: {hit_count}\n"
            f"💣 الضرر النهائي: {damage}",
            main_menu_keyboard(uid)
        )
        return

    if text.startswith("كيميائي "):
        target_name = text.split(" ", 1)[1].strip()
        attacker = load_country(uid)
        if not attacker:
            await reply("❌ ليس لديك دولة!")
            return
        if "منشأة نووية" not in attacker.get("مباني", []):
            await reply("❌ تحتاج *منشأة نووية* أولاً! ☢️")
            return

        if attacker.get("وحدات", {}).get("كيميائي", 0) < 1:
            await reply("❌ لا تملك سلاح كيميائي!")
            return

        now = time.time()
        last_nuke = attacker.get("آخر_نووي", 0)
        nuke_cd = 6 * 3600
        if now - last_nuke < nuke_cd:
            remaining = int((nuke_cd - (now - last_nuke)) / 60)
            await reply(f"⏳ الضربة غير جاهزة!\nمتبقي: {remaining} دقيقة")
            return

        defender = get_country_by_name(target_name)
        if not defender:
            await reply(f"❌ لا توجد دولة باسم `{target_name}`!")
            return
        if defender["user_id"] == uid:
            await reply("❌ لا يمكنك ضرب نفسك! 😂")
            return
        if is_protected(defender):
            remaining = max(1, int((defender["حماية حتى"] - time.time()) / 60))
            await reply(f"🛡️ *{target_name}* محمية لمدة {remaining} دقيقة!")
            return

        attacker = update_resources(attacker)
        defender = update_resources(defender)

        gold_cost = int(attacker.get("ذهب", 0) * 0.10)
        attacker["ذهب"] = max(0, attacker.get("ذهب", 0) - gold_cost)

        attacker["وحدات"]["كيميائي"] -= 1
        if attacker["وحدات"]["كيميائي"] <= 0:
            del attacker["وحدات"]["كيميائي"]
        attacker["آخر_نووي"] = now

        intercept_chance = calc_nuke_intercept_chance(defender)
        intercepted = random.random() < intercept_chance
        if intercepted:
            cap_gold(attacker)
            save_country(attacker)
            try:
                await send_attack_notification(context.bot, chat_id, target_name, attacker["اسم"], "كيميائي", amount=1, damage=0)
            except:
                pass
            await reply(
                f"☢️ *السلاح الكيميائي — تم الصد!* 🛡️\n━━━━━━━━━━━━━━━\n"
                f"🏴 المهاجم: *{attacker['اسم']}*\n🎯 الهدف: *{target_name}*\n\n"
                f"🛡️ دفاعات *{target_name}* الجوية صدّت الضربة!\n"
                f"📊 فرصة الصد كانت: {int(intercept_chance*100)}%\n\n"
                f"💰 خسرت: {gold_cost:,} ذهب\n"
                f"💣 خسرت: 1× كيميائي",
                main_menu_keyboard(uid)
            )
            return

        chem_power = UNITS["كيميائي"]["قوة"] * 1.5
        for unit in defender.get("وحدات", {}):
            defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.2)

        destroyed_building = ""
        if defender.get("مباني"):
            destroyed_building = random.choice(defender["مباني"])
            defender["مباني"].remove(destroyed_building)

        stolen = int(defender.get("ذهب", 0) * 0.4)
        attacker["ذهب"] += stolen
        defender["ذهب"] = max(0, defender.get("ذهب", 0) - stolen)
        defender["حماية حتى"] = time.time() + SHIELD_DURATION
        attacker["انتصارات"] = attacker.get("انتصارات", 0) + 1
        defender["خسائر"] = defender.get("خسائر", 0) + 1
        cap_gold(attacker)
        save_country(attacker)
        save_country(defender)
        try:
            await send_attack_notification(context.bot, chat_id, target_name, attacker["اسم"], "كيميائي", amount=1, damage=int(chem_power))
        except:
            pass
        building_text = f"\n🏗️ مبنى مدمر: {destroyed_building}" if destroyed_building else ""
        await reply(
            f"☢️ *ضربة كيميائية ناجحة!* ☢️\n━━━━━━━━━━━━━━━\n"
            f"🏴 المهاجم: *{attacker['اسم']}*\n🎯 الهدف: *{target_name}*\n"
            f"🚀 السلاح: *كيميائي* (قوة ×1.5 = {int(chem_power)})\n\n"
            f"📊 *تقرير الضربة:*\n"
            f"💀 دمار جيش المدافع: 80%{building_text}\n"
            f"💰 غنائم: {stolen:,} ذهب\n"
            f"💰 تكلفة الهجوم: {gold_cost:,} ذهب\n"
            f"🛡️ المدافع محمي لمدة ساعة\n"
            f"⏰ الهجوم التالي بعد 6 ساعات",
            main_menu_keyboard(uid)
        )
        return


    if text.startswith("انشاء تحالف "):
        parts = text.split(" ", 2)
        alliance_name = parts[2].strip() if len(parts) > 2 else ""
        country = load_country(uid)
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
            "قائد": country["اسم"],
            "جنرالات": [],
            "عمداء": [],
            "أعضاء": [country["اسم"]],
        }
        save_alliance(new_alliance)
        await reply(
            f"🤝 *تم إنشاء التحالف!*\n\n"
            f"⚔️ اسم التحالف: *{alliance_name}*\n"
            f"👑 القائد الأعلى: *{country['اسم']}*\n\n"
            f"للانضمام: `طلب انضمام {alliance_name}`",
            main_menu_keyboard(uid)
        )
        return

    if text.startswith("ترقية "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            await reply("❌ الاستخدام الصحيح: `ترقية [اسم الدولة] [الرتبة]`\nالرتب المتاحة: (جنرال، عميد، جندي)")
            return
        target_name = parts[1].strip()
        new_rank = parts[2].strip()
        country = load_country(uid)
        
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
            
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في تحالف!")
            return
            
        if country["اسم"] != alliance.get("قائد"):
            await reply("🚫 عذراً، فقط *القائد الأعلى* يمكنه منح الرتب!")
            return
            
        if new_rank not in ["جنرال", "عميد", "جندي"]:
            await reply("❌ الرتب المتاحة فقط هي: (جنرال، عميد، جندي)")
            return
            
        if target_name not in alliance.get("أعضاء", []):
            await reply(f"❌ الدولة `{target_name}` ليست عضواً في تحالفك!")
            return
            
        if target_name == alliance.get("قائد"):
            await reply("❌ لا يمكنك تغيير رتبة القائد الأعلى!")
            return

        if target_name in alliance.get("جنرالات", []):
            alliance["جنرالات"].remove(target_name)
        if target_name in alliance.get("عمداء", []):
            alliance["عمداء"].remove(target_name)

        if new_rank == "جنرال":
            if "جنرالات" not in alliance: alliance["جنرالات"] = []
            alliance["جنرالات"].append(target_name)
        elif new_rank == "عميد":
            if "عمداء" not in alliance: alliance["عمداء"] = []
            alliance["عمداء"].append(target_name)
            
        save_alliance(alliance)
        await reply(f"🎖️ تم ترقية الدولة *{target_name}* بنجاح إلى رتبة: *{new_rank}*!", main_menu_keyboard(uid))
        return

    # === نظام طلب الانضمام الجديد ===
    if text.startswith("طلب انضمام "):
        parts = text.split(" ", 2)
        alliance_name = parts[2].strip() if len(parts) > 2 else ""
        country = load_country(uid)
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
        # التحقق أنه لم يرسل طلب سابق
        existing_request = db["join_requests"].find_one({
            "chat_id": chat_id,
            "اسم_الدولة": country["اسم"],
            "تحالف": alliance["اسم"],
            "تم_المعالجة": False
        })
        if existing_request:
            await reply("⏳ لديك طلب انضمام قائم بالفعل! انتظر رد القائد.")
            return
        # إنشاء طلب انضمام
        request_id = str(uuid.uuid4())[:8]
        join_doc = {
            "request_id": request_id,
            "chat_id": chat_id,
            "user_id": uid,
            "اسم_الدولة": country["اسم"],
            "تحالف": alliance["اسم"],
            "تم_المعالجة": False,
            "وقت": time.time()
        }
        db["join_requests"].insert_one(join_doc)
        # إرسال الطلب في القروب مع أزرار للقائد
        leader_country = get_country_by_name(alliance.get("قائد", ""))
        leader_uid = leader_country["user_id"] if leader_country else None
        join_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ قبول", callback_data=f"join_accept_{request_id}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"join_reject_{request_id}")]
        ])
        power = calc_power(country.get("وحدات", {}))
        await reply(
            f"📩 *طلب انضمام جديد!*\n━━━━━━━━━━━━━━━\n"
            f"🏳️ الدولة: *{country['اسم']}*\n"
            f"⚔️ القوة: {power:,}\n"
            f"🎖️ المستوى: {get_level(country.get('انتصارات', 0))}\n\n"
            f"🤝 يريد الانضمام لتحالف: *{alliance['اسم']}*\n\n"
            f"👑 *{alliance.get('قائد', '?')}*، هل تقبل؟",
            join_keyboard
        )
        return

    # === هجوم تحالف عبر النص (نحتفظ بالأمر القديم كـ fallback) ===
    if text.startswith("هجوم تحالف "):
        parts = text.split(" ", 2)
        target_name = parts[2].strip() if len(parts) > 2 else ""
        attacker_country = load_country(uid)
        if not attacker_country:
            await reply("❌ ليس لديك دولة!")
            return
        attacker_alliance = get_country_alliance(chat_id, attacker_country["اسم"])
        if not attacker_alliance:
            await reply("❌ أنت لست في أي تحالف في هذا الكروب!")
            return
        
        if attacker_country["اسم"] != attacker_alliance.get("قائد") and attacker_country["اسم"] not in attacker_alliance.get("جنرالات", []):
            await reply("🚫 *القائد الأعلى والجنرالات فقط* يمكنهم طلب وتفعيل هجوم التحالف!")
            return
            
        vote_id = str(uuid.uuid4())[:8]
        # === إصلاح: تحديد نوع الهدف (دولة أو تحالف) وإضافة هدف_نوع ===
        target_alliance_obj = load_alliance(chat_id, target_name)
        target_type = "تحالف" if target_alliance_obj else "دولة"
        # === إصلاح: إذا كان الطالب هو القائد يُسجَّل صوته مباشرة ===
        is_requester_leader = attacker_country["اسم"].strip() == attacker_alliance.get("قائد", "").strip()
        initial_yes = [attacker_country["اسم"]] if is_requester_leader else []
        initial_voted = [attacker_country["اسم"]] if is_requester_leader else []
        vote_doc = {
            "vote_id": vote_id, "chat_id": chat_id,
            "alliance": attacker_alliance["اسم"], "هدف": target_name,
            "هدف_نوع": target_type,
            "طالب": attacker_country["اسم"],
            "أصوات_نعم": initial_yes, "أصوات_لا": [], "صوّت": initial_voted,
            "انتهى": False, "وقت": time.time()
        }
        votes_col.insert_one(vote_doc)
        leaders = [attacker_alliance.get("قائد", "")] + attacker_alliance.get("جنرالات", [])
        leaders_text = ", ".join(l for l in leaders if l)
        leader_note = "\n✅ *القائد الأعلى وافق — سيُنفَّذ الهجوم فوراً عند الضغط على موافق!*" if is_requester_leader else ""
        vote_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ موافق", callback_data=f"vote_yes_{vote_id}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"vote_no_{vote_id}")],
            [InlineKeyboardButton("🗑️ حذف", callback_data=f"del_self|{uid}")]
        ])
        await reply(
            f"🔥 *طلب هجوم تحالف عسكري!*\n━━━━━━━━━━━━━━━\n"
            f"⚔️ التحالف: *{attacker_alliance['اسم']}*\n"
            f"🎯 الهدف: *{target_name}* ({'تحالف' if target_type == 'تحالف' else 'دولة'})\n"
            f"📢 طالب الهجوم: *{attacker_country['اسم']}*\n\n"
            f"👑 المصوتون (القيادة العليا): {leaders_text}\n\n"
            f"📌 *شروط الموافقة:*\n"
            f"✔️ موافقة القائد الأعلى → هجوم فوري\n"
            f"✔️ أو 5 أصوات موافقة → هجوم{leader_note}\n\n"
            f"⏰ مدة التصويت: 5 دقائق\n👇 يرجى من القيادة التصويت الآن:",
            vote_keyboard
        )
        # === إذا القائد هو الطالب ننفذ الهجوم فوراً بدون انتظار ===
        if is_requester_leader:
            votes_col.update_one({"vote_id": vote_id}, {"$set": {"انتهى": True}})
            await context.bot.send_message(chat_id,
                f"⚡ *هجوم فوري!*\n👑 القائد الأعلى وافق!\n\n🎯 الهدف: *{target_name}*\n\n⏳ جارٍ تنفيذ الهجوم...",
                parse_mode="Markdown"
            )
            vote_doc_final = votes_col.find_one({"vote_id": vote_id})
            await do_alliance_attack(context.bot, vote_doc_final, chat_id)
        else:
            context.job_queue.run_once(
                execute_alliance_attack, 300,
                data={"vote_id": vote_id, "chat_id": chat_id, "target": target_name, "alliance_name": attacker_alliance["اسم"]},
                name=f"vote_{vote_id}"
            )
        return

    # === أمر التحالف (نص) ===
    if text.startswith("امر تحالف ") or text.startswith("أمر تحالف "):
        order_text = text.split(" ", 2)[2].strip() if len(text.split(" ", 2)) > 2 else ""
        if not order_text:
            await reply("❌ اكتب رسالتك بعد الأمر!\nمثال: `امر تحالف استعدوا للحرب!`")
            return
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في أي تحالف!")
            return
        # فقط القائد يمكنه إرسال الأوامر
        if country["اسم"] != alliance.get("قائد"):
            await reply("🚫 *فقط القائد الأعلى* يمكنه إرسال أوامر التحالف!")
            return
        # إرسال الرسالة في القروب
        members_mention = ", ".join(alliance.get("أعضاء", []))
        await reply(
            f"📢 *أمر من القائد الأعلى!*\n━━━━━━━━━━━━━━━\n"
            f"🤝 التحالف: *{alliance['اسم']}*\n"
            f"👑 القائد: *{country['اسم']}*\n\n"
            f"📋 *الأمر:*\n{order_text}\n\n"
            f"👥 *الأعضاء:* {members_mention}",
            main_menu_keyboard(uid)
        )
        return

    if text.startswith("انضم تحالف "):
        # نوجه اللاعب لاستخدام النظام الجديد
        parts = text.split(" ", 2)
        alliance_name = parts[2].strip() if len(parts) > 2 else ""
        await reply(
            f"📌 *تم تحديث نظام الانضمام!*\n\n"
            f"الآن يتم الانضمام عبر طلب يوافق عليه القائد:\n\n"
            f"`طلب انضمام {alliance_name}`",
            main_menu_keyboard(uid)
        )
        return

    # === طرد عضو بالنص (للقائد فقط) ===
    if text.startswith("طرد "):
        parts = text.split(" ", 1)
        target_name = parts[1].strip() if len(parts) > 1 else ""
        if not target_name:
            await reply("❌ اكتب اسم الدولة!\nمثال: `طرد اسم الدولة`")
            return
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في أي تحالف!")
            return
        if country["اسم"] != alliance.get("قائد"):
            await reply("🚫 *فقط القائد الأعلى* يمكنه طرد الأعضاء!")
            return
        if target_name not in alliance.get("أعضاء", []):
            await reply(f"❌ الدولة `{target_name}` ليست عضواً في تحالفك!")
            return
        if target_name == alliance.get("قائد"):
            await reply("❌ لا يمكنك طرد نفسك!")
            return
        # تنفيذ الطرد
        alliance["أعضاء"].remove(target_name)
        if target_name in alliance.get("جنرالات", []):
            alliance["جنرالات"].remove(target_name)
        if target_name in alliance.get("عمداء", []):
            alliance["عمداء"].remove(target_name)
        save_alliance(alliance)
        await reply(
            f"🚫 *تم طرد {target_name}!*\n\n"
            f"🤝 التحالف: *{alliance['اسم']}*\n"
            f"👥 الأعضاء المتبقين: {len(alliance['أعضاء'])}",
            main_menu_keyboard(uid)
        )
        return

    if text in ["اغادر التحالف", "غادر التحالف", "خروج من التحالف", "مغادرة التحالف"]:

        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في أي تحالف!")
            return
        if country["اسم"] == alliance["قائد"] and len(alliance["أعضاء"]) > 1:
            await reply("❌ لا يمكنك المغادرة وأنت القائد الأعلى!\nقم بحل التحالف أو نقل القيادة.")
            return
        alliance["أعضاء"].remove(country["اسم"])
        if country["اسم"] in alliance.get("جنرالات", []):
            alliance["جنرالات"].remove(country["اسم"])
        if country["اسم"] in alliance.get("عمداء", []):
            alliance["عمداء"].remove(country["اسم"])
            
        if len(alliance["أعضاء"]) == 0:
            alliances_col.delete_one({"chat_id": chat_id, "اسم": alliance["اسم"]})
        else:
            save_alliance(alliance)
        await reply(f"🚪 *غادرت تحالف {alliance['اسم']}!*", main_menu_keyboard(uid))
        return

    if text in ["حل التحالف", "حذف التحالف"]:
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        alliance = get_country_alliance(chat_id, country["اسم"])
        if not alliance:
            await reply("❌ أنت لست في أي تحالف!")
            return
        if country["اسم"] != alliance.get("قائد"):
            await reply("🚫 فقط القائد الأعلى يمكنه حل التحالف!")
            return
        alliances_col.delete_one({"chat_id": chat_id, "اسم": alliance["اسم"]})
        await reply(f"🗑️ *تم حل تحالف {alliance['اسم']}!*", main_menu_keyboard(uid))
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
        my_country = load_country(uid)
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
        cap_gold(my_country)
        cap_gold(target)
        save_country(my_country)
        save_country(target)
        await reply(
            f"💰 *تم إرسال الذهب!*\n\nمن: *{my_country['اسم']}*\nإلى: *{target_name}*\nالمبلغ: 💰{amount:,}",
            main_menu_keyboard(uid)
        )
        return

    # === حذف الدولة ===
    if text == "حذف دولتي":
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد حذف", callback_data=f"confirm_delete_country|{uid}"),
             InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_delete_country|{uid}")]
        ])
        await reply(
            f"⚠️ *هل أنت متأكد من حذف دولتك؟*\n\n"
            f"🏳️ الدولة: *{country['اسم']}*\n"
            f"💰 الذهب: {country.get('ذهب', 0):,}\n"
            f"⚔️ القوة: {calc_power(country.get('وحدات', {})):,}\n\n"
            f"❗ هذا الإجراء لا يمكن التراجع عنه!",
            confirm_kb
        )
        return

    if text == "تأكيد حذف":
        country = load_country(uid)
        if not country:
            await reply("❌ ليس لديك دولة!")
            return
        # حذف من التحالفات
        all_alliances = list(alliances_col.find({"أعضاء": country["اسم"]}))
        for alliance in all_alliances:
            alliance["أعضاء"].remove(country["اسم"])
            if country["اسم"] in alliance.get("جنرالات", []):
                alliance["جنرالات"].remove(country["اسم"])
            if country["اسم"] in alliance.get("عمداء", []):
                alliance["عمداء"].remove(country["اسم"])
            if len(alliance["أعضاء"]) == 0:
                alliances_col.delete_one({"_id": alliance["_id"]})
            else:
                if alliance.get("قائد") == country["اسم"] and alliance["أعضاء"]:
                    alliance["قائد"] = alliance["أعضاء"][0]
                save_alliance(alliance)
        countries_col.delete_one({"user_id": uid})
        await reply(
            "🗑️ *تم حذف دولتك بنجاح!*\n\n"
            "يمكنك إنشاء دولة جديدة:\n`انشاء دولة [الاسم]`"
        )
        return

# === دالة تنفيذ هجوم التحالف (مشتركة بين التنفيذ الفوري والمجدول) ===
async def do_alliance_attack(bot, vote, chat_id):
    """تنفيذ هجوم التحالف بعد التصويت"""
    target_name = vote["هدف"]
    alliance_name = vote["alliance"]
    yes_votes = len(vote.get("أصوات_نعم", []))
    no_votes = len(vote.get("أصوات_لا", []))
    
    alliance = load_alliance(chat_id, alliance_name)
    if not alliance:
        return
    
    # التحقق هل الهدف تحالف أو دولة
    target_is_alliance = vote.get("هدف_نوع") == "تحالف"
    defender = None
    def_alliance_obj = None
    target_alliance = None
    
    if target_is_alliance:
        target_alliance = load_alliance(chat_id, target_name)
        if not target_alliance:
            await bot.send_message(chat_id, f"❌ التحالف *{target_name}* لم يعد موجوداً!", parse_mode="Markdown")
            return
        def_power, _ = calc_alliance_power(chat_id, target_alliance)
        def_note = f"🛡️ تحالف *{target_name}* بقوة: {def_power:,}"
    else:
        defender = get_country_by_name(target_name)
        # === دفاع جماعي ===
        def_alliance_obj, collective_def = calc_collective_defense(chat_id, target_name)
        if def_alliance_obj and collective_def > 0:
            def_power = collective_def
            def_note = f"🛡️ دفاع تحالف *{def_alliance_obj['اسم']}* الجماعي (+20%)"
        elif defender:
            def_power = calc_power(defender.get("وحدات", {}))
            def_note = ""
        else:
            await bot.send_message(chat_id, f"❌ لا توجد دولة باسم *{target_name}*!", parse_mode="Markdown")
            return
    
    att_power, _ = calc_alliance_power(chat_id, alliance)
    att_roll = att_power * random.uniform(0.7, 1.3)
    def_roll = def_power * random.uniform(0.7, 1.3)
    
    if att_roll > def_roll:
        total_stolen = 0
        if target_is_alliance:
            target_alliance = load_alliance(chat_id, target_name)
            for m_name in target_alliance.get("أعضاء", []):
                m = get_country_by_name(m_name)
                if m:
                    stolen = int(m.get("ذهب", 0) * 0.3)
                    total_stolen += stolen
                    m["ذهب"] = max(0, m.get("ذهب", 0) - stolen)
                    for unit in m.get("وحدات", {}): m["وحدات"][unit] = int(m["وحدات"][unit] * 0.6)
                    m["حماية حتى"] = time.time() + SHIELD_DURATION
                    save_country(m)
        elif def_alliance_obj:
            for m_name in def_alliance_obj.get("أعضاء", []):
                m = get_country_by_name(m_name)
                if m:
                    stolen = int(m.get("ذهب", 0) * 0.3)
                    total_stolen += stolen
                    m["ذهب"] = max(0, m.get("ذهب", 0) - stolen)
                    for unit in m.get("وحدات", {}): m["وحدات"][unit] = int(m["وحدات"][unit] * 0.6)
                    m["حماية حتى"] = time.time() + SHIELD_DURATION
                    save_country(m)
        elif defender:
            total_stolen = int(defender.get("ذهب", 0) * 0.3)
            defender["ذهب"] = max(0, defender.get("ذهب", 0) - total_stolen)
            for unit in defender.get("وحدات", {}): defender["وحدات"][unit] = int(defender["وحدات"][unit] * 0.6)
            defender["حماية حتى"] = time.time() + SHIELD_DURATION
            save_country(defender)
        
        gold_per = total_stolen // max(1, len(alliance.get("أعضاء", [])))
        for m_name in alliance.get("أعضاء", []):
            m = get_country_by_name(m_name)
            if m:
                m["ذهب"] = m.get("ذهب", 0) + gold_per
                m["انتصارات"] = m.get("انتصارات", 0) + 1
                for unit in m.get("وحدات", {}): m["وحدات"][unit] = int(m["وحدات"][unit] * 0.8)
                cap_gold(m)
                save_country(m)
        try:
            await send_attack_notification(bot, chat_id, target_name, alliance_name, "هجوم تحالف", prefer_alliance=target_is_alliance)
        except:
            pass
        await bot.send_message(chat_id,
            f"🔥 *هجوم التحالف نجح!* 🔥\n━━━━━━━━━━━━━━━\n"
            f"⚔️ *{alliance_name}* هاجم *{target_name}*!\n{def_note}\n\n"
            f"🔥 قوة الهجوم: {int(att_roll):,}\n🛡️ قوة الدفاع: {int(def_roll):,}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏆 *{alliance_name} انتصر!*\n\n"
            f"📊 *تقرير المعركة:*\n"
            f"💰 إجمالي الغنائم: {total_stolen:,}\n"
            f"💎 نصيب كل عضو: {gold_per:,}\n"
            f"💀 خسائر المهاجم: 20%\n💀 خسائر المدافع: 40%\n"
            f"✅{yes_votes} | ❌{no_votes}",
            parse_mode="Markdown")
    else:
        for m_name in alliance.get("أعضاء", []):
            m = get_country_by_name(m_name)
            if m:
                m["خسائر"] = m.get("خسائر", 0) + 1
                for unit in m.get("وحدات", {}): m["وحدات"][unit] = int(m["وحدات"][unit] * 0.5)
                save_country(m)
        try:
            await send_attack_notification(bot, chat_id, target_name, alliance_name, "هجوم تحالف", prefer_alliance=target_is_alliance)
        except:
            pass
        await bot.send_message(chat_id,
            f"💀 *هجوم التحالف فشل!* 💀\n━━━━━━━━━━━━━━━\n"
            f"⚔️ *{alliance_name}* هاجم *{target_name}*!\n{def_note}\n\n"
            f"🔥 قوة الهجوم: {int(att_roll):,}\n🛡️ قوة الدفاع: {int(def_roll):,}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🛡️ *{target_name}* صدّ الهجوم!\n\n"
            f"📊 *تقرير المعركة:*\n"
            f"💀 كل الأعضاء خسروا 50% من جيوشهم!\n"
            f"✅{yes_votes} | ❌{no_votes}",
            parse_mode="Markdown")

async def execute_alliance_attack(context):
    data = context.job.data
    vote_id = data["vote_id"]
    chat_id = data["chat_id"]
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
            f"❌ *تم رفض هجوم التحالف!*\n\n✅ موافق: {yes_votes}\n❌ رافض: {no_votes}\n\nالقيادة رفضت الهجوم على *{vote['هدف']}*",
            parse_mode="Markdown")
        return
    # تنفيذ الهجوم عبر الدالة المشتركة
    await do_alliance_attack(context.bot, vote, chat_id)

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
    print("✅ عرش الظلال يعمل بكل التعديلات الجديدة! 🌍⚔️")
    application.run_polling()
