import os
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = 8541159331
TOIII_ID = 8575179469
HAMSI_ID = 1884302694

weddings = {}

poems = [
    "يا من سكنتِ الروح قبل اللقاء، كنتِ القصيدة قبل أن أعرف الكلام",
    "أنتِ الربيع الذي لا يرحل، والنور الذي يسكن العيون",
    "لو كان الجمال يُباع ما اشتريت سواكِ، ولو كان الحب يُعاد ما اخترت غيرك",
    "عيناكِ بحر وأنا الغريق، وما أجمل أن أغرق فيكِ",
    "أنتِ الكلمة التي بحثت عنها في كل قصيدة ولم أجدها إلا فيكِ",
    "قلبي قبل أن يراكِ كان يمشي، بعد أن رآكِ صار يطير",
    "من قال إن الجنة بعيدة؟ أنا أراها في ابتسامتكِ",
    "كل النجوم في السماء تحسدني لأنكِ اخترتِني",
]

omar_lines = [
    "أنت عمري اللي ابتدى بيك، وبعدك عمري ما له معنى",
    "حبيبي يا نور عيني، يا ساكن في قلبي وعقلي",
    "تملّيني، وعنيكي في عيني، وروحك روحي",
    "أنا عشقت وبقيت أعشق، وحبك يا حبيبي ما بيكفي",
    "لو كانت الدنيا بإيدي، كنت هداهالك يا قلبي",
]

titles = [
    "ملك الكروب 👑",
    "أكثر شخص نعسان 😴",
    "نجم اليوم ⭐",
    "الشخص الأكثر تفكيراً 🤔",
    "بطل الكروب 🏆",
    "الأكثر ضحكاً 😂",
    "الأذكى في الكروب 🧠",
    "الأكثر كسلاً 😪",
]

secrets = [
    "يحب يغني بصوت عالي لما يكون لحاله 🎤",
    "يضحك على نكته مرتين، مرة لما يسمعها ومرة لما يفهمها 😂",
    "ينام وهو يفكر بالأكل 🍕",
    "يتظاهر إنه مشغول وهو بس يتصفح تيك توك 📱",
    "يحب يرقص لما ما أحد يشوفه 💃",
    "يكذب إنه بخير وهو ما بخير 😅",
    "يحفظ أغاني ويغنيها بالحمام 🚿",
]

async def get_members(context, chat_id, exclude_id=None):
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        members = [m.user for m in admins if not m.user.is_bot]
        if exclude_id:
            members = [m for m in members if m.id != exclude_id]
        return members
    except:
        return []

def get_name(user):
    return f"@{user.username}" if user.username else user.first_name

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_name = get_name(user)

    # ===== زوجني =====
    if text == "زوجني":
        if user.id == OWNER_ID:
            partner_name = "Judy 👸"
            poem = random.choice(poems)
        elif user.id == TOIII_ID:
            partner_name = "طارق 🤵"
            poem = random.choice(poems)
        elif user.id == HAMSI_ID:
            partner_name = "كاتي 👸"
            poem = random.choice(omar_lines)
        else:
            members = await get_members(context, chat_id, user.id)
            if not members:
                await update.message.reply_text("❌ أعطني صلاحية مشرف!")
                return
            partner = random.choice(members)
            partner_name = get_name(partner)
            poem = random.choice(poems)

        if chat_id not in weddings:
            weddings[chat_id] = {}
        weddings[chat_id][user.id] = partner_name

        await update.message.reply_text(
            f"💍 تم الزواج! 💍\n\n"
            f"🤵 {user_name}\n"
            f"👰 {partner_name}\n\n"
            f"❝ {poem} ❞\n\n"
            f"مبروك عليكم! 🎉"
        )

    # ===== طلقني =====
    elif text == "طلقني":
        if chat_id in weddings and user.id in weddings[chat_id]:
            partner_name = weddings[chat_id].pop(user.id)
            await update.message.reply_text(
                f"💔 تم الطلاق!\n\n"
                f"{user_name} طلّق {partner_name}\n\n"
                f"الله يعوض بالأحسن 😢"
            )
        else:
            await update.message.reply_text("❌ أنت مو متزوج أصلاً! 😄")

    # ===== المتزوجون =====
    elif text == "المتزوجون":
        if chat_id not in weddings or not weddings[chat_id]:
            await update.message.reply_text("💔 ما في متزوجين بعد!")
            return
        msg = "📜 سجل المتزوجين:\n\n"
        for i, (uid, partner) in enumerate(weddings[chat_id].items(), 1):
            msg += f"{i}. 💍 {partner}\n"
        await update.message.reply_text(msg)

    # ===== حظي =====
    elif text == "حظي":
        luck = random.randint(0, 100)
        if luck >= 80:
            comment = "يوم رائع ينتظرك! 🌟"
        elif luck >= 50:
            comment = "يوم عادي، بس ما يخيب الأمل 😊"
        elif luck >= 20:
            comment = "خل تكون حذر اليوم 😅"
        else:
            comment = "ابقى بالبيت اليوم 😂"
        await update.message.reply_text(
            f"🍀 حظ {user_name} اليوم:\n\n"
            f"{'█' * (luck // 10)}{'░' * (10 - luck // 10)} {luck}%\n\n"
            f"{comment}"
        )

    # ===== القاضي =====
    elif text == "القاضي":
        members = await get_members(context, chat_id)
        if not members:
            await update.message.reply_text("❌ أعطني صلاحية مشرف!")
            return
        chosen = random.choice(members)
        title = random.choice(titles)
        await update.message.reply_text(
            f"👨‍⚖️ القاضي يحكم:\n\n"
            f"{get_name(chosen)} هو/هي {title} 🎉"
        )

    # ===== اعترف =====
    elif text == "اعترف":
        members = await get_members(context, chat_id, user.id)
        if not members:
            await update.message.reply_text("❌ أعطني صلاحية مشرف!")
            return
        chosen = random.choice(members)
        secret = random.choice(secrets)
        await update.message.reply_text(
            f"😏 اعتراف خطير!\n\n"
            f"{user_name} يعترف إن {get_name(chosen)}\n"
            f"{secret}"
        )

    # ===== من الأقوى =====
    elif text == "من الأقوى":
        members = await get_members(context, chat_id)
        if len(members) < 2:
            await update.message.reply_text("❌ ما في أعضاء كافيين!")
            return
        p1, p2 = random.sample(members, 2)
        winner = random.choice([p1, p2])
        await update.message.reply_text(
            f"💪 مبارزة!\n\n"
            f"{get_name(p1)} ⚔️ {get_name(p2)}\n\n"
            f"🏆 الفائز: {get_name(winner)}!"
        )

    # ===== نردي =====
    elif text == "نردي":
        dice = random.randint(1, 6)
        faces = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        if dice == 6:
            comment = "حظ رائع! 🎉"
        elif dice >= 4:
            comment = "مش بطال! 😊"
        else:
            comment = "حاول مرة ثانية 😅"
        await update.message.reply_text(
            f"🎲 {user_name} رمى النرد:\n\n"
            f"{faces[dice-1]} — {comment}"
        )

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ البوت يعمل!")
    application.run_polling()
