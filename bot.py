import os
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")

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

weddings = {}

async def zawejni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    try:
        chat_members = await context.bot.get_chat_administrators(chat_id)
        members = [m.user for m in chat_members if not m.user.is_bot and m.user.id != user.id]
    except:
        await update.message.reply_text("❌ أعطني صلاحية مشرف!")
        return

    if not members:
        await update.message.reply_text("❌ ما في أعضاء كافيين!")
        return

    partner = random.choice(members)
    poem = random.choice(poems)

    user_name = f"@{user.username}" if user.username else user.first_name
    partner_name = f"@{partner.username}" if partner.username else partner.first_name

    if chat_id not in weddings:
        weddings[chat_id] = []
    weddings[chat_id].append((user_name, partner_name))

    msg = (
        f"💍 تم الزواج! 💍\n\n"
        f"🤵 {user_name}\n"
        f"👰 {partner_name}\n\n"
        f"❝ {poem} ❞\n\n"
        f"مبروك عليكم! 🎉"
    )
    await update.message.reply_text(msg)

async def almutazawejoun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in weddings or not weddings[chat_id]:
        await update.message.reply_text("💔 ما في متزوجين بعد!")
        return

    msg = "📜 سجل المتزوجين:\n\n"
    for i, (a, b) in enumerate(weddings[chat_id], 1):
        msg += f"{i}. 🤵 {a} 💍 {b} 👰\n"
    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "زوجني":
        await zawejni(update, context)
    elif text == "المتزوجون":
        await almutazawejoun(update, context)

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ بوت الزواج يعمل!")
    application.run_polling()
