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

omardiaب_lines = [
    "أنت عمري اللي ابتدى بيك، وبعدك عمري ما له معنى",
    "حبيبي يا نور عيني، يا ساكن في قلبي وعقلي",
    "تملّيني، وعنيكي في عيني، وروحك روحي",
    "أنا عشقت وبقيت أعشق، وحبك يا حبيبي ما بيكفي",
    "لو كانت الدنيا بإيدي، كنت هداهالك يا قلبي",
]

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    chat_id = update.effective_chat.id

    if text == "زوجني":
        user_name = f"@{user.username}" if user.username else user.first_name

        if user.id == OWNER_ID:
            partner_name = "Judy 👸"
            poem = random.choice(poems)
        elif user.id == TOIII_ID:
            partner_name = "طارق 🤵"
            poem = random.choice(poems)
        elif user.id == HAMSI_ID:
            partner_name = "كاتي 👸"
            poem = random.choice(omardiaب_lines)
        else:
            try:
                admins = await context.bot.get_chat_administrators(chat_id)
                members = [m.user for m in admins if not m.user.is_bot and m.user.id != user.id]
                if not members:
                    await update.message.reply_text("❌ ما في أعضاء كافيين!")
                    return
                partner = random.choice(members)
                partner_name = f"@{partner.username}" if partner.username else partner.first_name
                poem = random.choice(poems)
            except:
                await update.message.reply_text("❌ أعطني صلاحية مشرف!")
                return

        if chat_id not in weddings:
            weddings[chat_id] = {}
        weddings[chat_id][user.id] = partner_name

        msg = (
            f"💍 تم الزواج! 💍\n\n"
            f"🤵 {user_name}\n"
            f"👰 {partner_name}\n\n"
            f"❝ {poem} ❞\n\n"
            f"مبروك عليكم! 🎉"
        )
        await update.message.reply_text(msg)

    elif text == "طلقني":
        user_name = f"@{user.username}" if user.username else user.first_name
        if chat_id in weddings and user.id in weddings[chat_id]:
            partner_name = weddings[chat_id].pop(user.id)
            await update.message.reply_text(
                f"💔 تم الطلاق!\n\n"
                f"{user_name} طلّق {partner_name}\n\n"
                f"الله يعوض بالأحسن 😢"
            )
        else:
            await update.message.reply_text("❌ أنت مو متزوج أصلاً! 😄")

    elif text == "المتزوجون":
        if chat_id not in weddings or not weddings[chat_id]:
            await update.message.reply_text("💔 ما في متزوجين بعد!")
            return
        msg = "📜 سجل المتزوجين:\n\n"
        for i, (uid, partner) in enumerate(weddings[chat_id].items(), 1):
            msg += f"{i}. 💍 {partner}\n"
        await update.message.reply_text(msg)

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ بوت الزواج يعمل!")
    application.run_polling()
