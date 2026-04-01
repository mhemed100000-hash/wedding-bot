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
    "أكبر نايم بالكروب وما عنده خبر 😴",
    "بطل التفليس والديون 💸",
    "رئيس جمعية الوجع والزعل 😤",
    "أكثر واحد بيحكي وما بيعمل شي 🗣️",
    "بطل الأكل وما بيدفع 🍔",
    "أمير الكذب والتمثيل 🎭",
    "الوحيد اللي بيقرأ رسائلك وما بيرد 📵",
    "بطل الغياب بدون إشعار مسبق 👻",
    "رئيس نادي الفاشلين الرسمي 🏆",
    "أكثر واحد بيزعج وبيتظاهر إنه بريء 😇",
    "سلطان الوقاحة والثقل 👑",
    "الشخص اللي كل الكروب تعبان منه 😂",
]

secrets = [
    "بيغني بالحمام وبيتخيل إنه نجم عالمي وهو بس صوته مثل القطط 🎤😂",
    "بيكذب إنه مشغول وهو قاعد يتفرج على ريلز من الصبح 📱",
    "بياكل أكل أصحابه ولما بيحكوه بيقول والله ما كنت جايع 🍕😏",
    "بيحكي على كل الناس من وراهم وقدامهم بيضحك معهم 😂",
    "بيحط ألارم الساعة 6 الصبح وبيطفيه وبينام لـ 12 😴",
    "بيشتري أشياء ما بيحتاجها وبعدين بيزعل على غلاء المعيشة 🛍️",
    "بيقول آخر رسالة وبعدين بيرسل روايات كاملة 💬😂",
    "بينسى اسم الناس ولما بيسألوه بيقول يسلم هالوجه 😬",
    "بيتظاهر إنه دايت وبعدين بياكل أكثر من الكل بالخفا 🍔",
    "بيحكي إنه تعبان ومريض لما بده يتهرب من الشغل 🤒😂",
    "بيكذب على أهله وين راح وبعدين بتطلع الحقيقة 😅",
    "بيسأل السعر وبعدين بيقول بفكر فيه وما بيرجع أبداً 😂",
]

win_comments = [
    "هزمه وهو نايم يا جماعة، يعني مو رجال من الأساس 😂",
    "الفائز بالقوة والوجاهة والثاني راح يبكي على أمه 😭",
    "نتيجة حاسمة، الخاسر يروح يغير مهنته 😂",
    "الفائز بلا منازع والخاسر يستاهل أكثر 😏",
    "هزمه بنظرة وحدة، يعني ما كان في مبارزة أصلاً 👁️",
    "الفائز واضح من أول شوفة، والثاني ما كان عنده أمل 😂",
    "هزمه وهو مو مدري شو صار، المسكين 😅",
    "الأقوى بلا نقاش والثاني يروح يتدرب من جديد 💪",
    "فاز فوزاً ساحقاً والخاسر يتمنى ما شارك 😂",
    "الفائز بالإجماع والخاسر بالإجماع كمان 😏",
]

naswanji_comments = {
    (90, 100): [
        "يا زلمة هاد محترف! بيشتغل 24 ساعة بدون إجازة 😂",
        "هاد ما بيتركها تمشي قبل ما ياخد رقمها وانستغرامها وسناباتها 😏",
        "الأسطورة بنفسه! الكل بيتعلم منه 🏆",
        "هاد خطر على الكروب كله، حذار منه 😂",
    ],
    (70, 89): [
        "مو بطال! بس لازم يتدرب أكثر ليوصل للقمة 😂",
        "هاد شاطر بس بده شغل أكثر على نفسه 😏",
        "فوق المتوسط بكتير، الأهل خايفين منه 😅",
        "بيحاول جاهداً وبيوصل أحياناً 😂",
    ],
    (50, 69): [
        "متوسط متل الطالع والنازل، مرة بيحاول ومرة بيكسل 😅",
        "نص نص، يعني موهبته موجودة بس كسلان 😏",
        "ما هو سيء بس ما هو منيح، يعني عادي متل عادته 😂",
        "بيحاول بس النتايج مخيبة للآمال 😅",
    ],
    (30, 49): [
        "ضعيف الأداء، بده دورات تدريبية 😂",
        "الناس ما بتلتفت عليه وهو مو عارف ليش 😏",
        "بيحاول يكون نسونجي بس الدنيا مو معه 😅",
        "أقل من المتوسط بكتير، يا حظه 😂",
    ],
    (0, 29): [
        "هاد ما عنده أي موهبة بهالمجال خلص 😂",
        "الناس بتهرب منه مو بتقرب 😏",
        "يا أخي روح اشتغل بمجال ثاني 😂",
        "صفر على الشمال، والأسوأ إنه مو مدري 😅",
    ],
}

def get_name(user):
    return f"[{user.first_name}](tg://user?id={user.id})"

async def get_members(context, chat_id, exclude_id=None):
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        members = [m.user for m in admins if not m.user.is_bot]
        if exclude_id:
            members = [m for m in members if m.id != exclude_id]
        return members
    except:
        return []

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_name = get_name(user)

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
            f"مبروك عليكم! 🎉",
            parse_mode="Markdown"
        )

    elif text == "طلقني":
        if chat_id in weddings and user.id in weddings[chat_id]:
            partner_name = weddings[chat_id].pop(user.id)
            responses = [
                f"💔 يiii طلاق!\n\n{user_name} طلّق {partner_name}\n\nيسلم هالإيد اللي وقّعت 😂",
                f"💔 انتهى الحفل!\n\n{user_name} رمى {partner_name} زبالة 🗑️\n\nالله يعوض بأحسن منك 😏",
                f"💔 آخ آخ!\n\n{user_name} طلّق {partner_name}\n\nيا خسارة الفرح اللي دفعناه 😂",
                f"💔 تفضيت!\n\n{user_name} خلص من {partner_name}\n\nما دام الراحة أهم 😅",
            ]
            await update.message.reply_text(random.choice(responses), parse_mode="Markdown")
        else:
            responses = [
                "😂 يا زلمة أنت مو متزوج أصلاً، شو بدك تطلق؟",
                "😏 وين العروس؟ اتزوج أول بعدين طلّق!",
                "😂 ما عندك مرا تطلقها يا حظك!",
            ]
            await update.message.reply_text(random.choice(responses))

    elif text == "المتزوجون":
        if chat_id not in weddings or not weddings[chat_id]:
            responses = [
                "😂 ما في حدا اتجرأ يتزوج بهالكروب، كلكم خايفين!",
                "💔 كروب عوانس وعزاب، ما في متزوجين!",
                "😏 ولا زوج ولا زوجة، كلكم لحالكم يا مساكين!",
            ]
            await update.message.reply_text(random.choice(responses))
            return
        msg = "📜 سجل المتزوجين اللي جرّبوا حظهم:\n\n"
        for i, (uid, partner) in enumerate(weddings[chat_id].items(), 1):
            msg += f"{i}. 💍 {partner}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "حظي":
        luck = random.randint(0, 100)
        if luck >= 80:
            comment = "ما توقعنا هيك، بس تمتع لأنه مو كل يوم 😏"
        elif luck >= 50:
            comment = "عادي متل عادتك، لا كتير ولا قليل 😑"
        elif luck >= 20:
            comment = "حظك زبالة اليوم، ابقى بالبيت وما تتحرك 😂"
        else:
            comment = "والله يا حبيبي حظك أسوأ من حظنا فيك 😂"
        await update.message.reply_text(
            f"🍀 حظ {user_name} اليوم:\n\n"
            f"{'█' * (luck // 10)}{'░' * (10 - luck // 10)} {luck}%\n\n"
            f"{comment}",
            parse_mode="Markdown"
        )

    elif text == "القاضي":
        members = await get_members(context, chat_id)
        if not members:
            await update.message.reply_text("❌ أعطني صلاحية مشرف يا زلمة!")
            return
        chosen = random.choice(members)
        title = random.choice(titles)
        intros = [
            "القاضي حكم وما في استئناف 👨‍⚖️",
            "الحكم صدر وكلمة الفصل قيلت 🔨",
            "بعد تداول ومداولة وتفكير عميق 🤔",
        ]
        await update.message.reply_text(
            f"👨‍⚖️ {random.choice(intros)}:\n\n"
            f"{get_name(chosen)}\n"
            f"هو/هي {title}\n\n"
            f"وهاد مو قابل للنقاش! 😂",
            parse_mode="Markdown"
        )

    elif text == "اعترف":
        members = await get_members(context, chat_id, user.id)
        if not members:
            await update.message.reply_text("❌ أعطني صلاحية مشرف!")
            return
        chosen = random.choice(members)
        secret = random.choice(secrets)
        intros = [
            "وصلنا خبر من مصدر موثوق 🕵️",
            "الاستخبارات كشفت سر خطير 😏",
            "مصدر مجهول أفاد بما يلي 👀",
        ]
        await update.message.reply_text(
            f"😏 {random.choice(intros)}:\n\n"
            f"{user_name} يعترف إن {get_name(chosen)}\n"
            f"{secret}\n\n"
            f"وهاد موثق ومو قابل للنفي 😂",
            parse_mode="Markdown"
        )

    elif text == "من الأقوى":
        members = await get_members(context, chat_id)
        if len(members) < 2:
            await update.message.reply_text("❌ ما في أعضاء كافيين للمبارزة!")
            return
        p1, p2 = random.sample(members, 2)
        winner = random.choice([p1, p2])
        loser = p2 if winner == p1 else p1
        comment = random.choice(win_comments)
        await update.message.reply_text(
            f"⚔️ مبارزة بلا رحمة!\n\n"
            f"{get_name(p1)} 🆚 {get_name(p2)}\n\n"
            f"🏆 الفائز: {get_name(winner)}\n"
            f"💀 الخاسر: {get_name(loser)}\n\n"
            f"{comment}",
            parse_mode="Markdown"
        )

    elif text == "نردي":
        dice = random.randint(1, 6)
        faces = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        if dice == 6:
            comment = "6! يا زلمة حظك منيح اليوم، استغله قبل ما يروح 😂"
        elif dice >= 4:
            comment = "مش بطال، بس ما تفرح كتير 😏"
        elif dice == 3:
            comment = "3 يعني نص نص، متل حظك بالحياة 😅"
        else:
            comment = f"{dice} بس؟ يعني حظك أسوأ من توقعاتنا 😂"
        await update.message.reply_text(
            f"🎲 {user_name} رمى النرد:\n\n"
            f"{faces[dice-1]}\n\n"
            f"{comment}",
            parse_mode="Markdown"
        )

    elif text == "نسونجي":
        members = await get_members(context, chat_id)
        if not members:
            await update.message.reply_text("❌ أعطني صلاحية مشرف!")
            return
        chosen = random.choice(members)
        percentage = random.randint(0, 100)

        for (low, high), comments in naswanji_comments.items():
            if low <= percentage <= high:
                comment = random.choice(comments)
                break

        await update.message.reply_text(
            f"💘 تقرير النسوانجية الرسمي!\n\n"
            f"الشخص: {get_name(chosen)}\n\n"
            f"{'█' * (percentage // 10)}{'░' * (10 - percentage // 10)} {percentage}%\n\n"
            f"{comment}",
            parse_mode="Markdown"
        )

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ البوت يعمل!")
    application.run_polling()
