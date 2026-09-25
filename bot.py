import asyncio, os, random, sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, TelegramObject, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_NEW_BOT_TOKEN_HERE")
ADMIN_IDS = {6982309853}
SIGNAL_PRICE = 500
REFERRAL_REWARD = 250

if BOT_TOKEN == "PASTE_NEW_BOT_TOKEN_HERE":
    raise RuntimeError("BOT_TOKEN Render Environment Variables ichiga qo'yilmagan.")

db = sqlite3.connect("bulldrop.db", check_same_thread=False)
cur = db.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, referred_by INTEGER)""")
cur.execute("""CREATE TABLE IF NOT EXISTS channels(
 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE)""")
cur.execute("""CREATE TABLE IF NOT EXISTS signals(
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, stars INTEGER, bombs INTEGER)""")
db.commit()

cur.execute("DELETE FROM channels WHERE LOWER(username)=LOWER('@A_ToolsX')")
db.commit()

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

def menu(uid):
    rows = [
        [KeyboardButton(text="📡 Signallar"), KeyboardButton(text="👥 Referal")],
        [KeyboardButton(text="💰 Balans"), KeyboardButton(text="👤 Profil")]
    ]
    if uid in ADMIN_IDS:
        rows.append([KeyboardButton(text="🛠 Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

async def check_sub(uid):
    if uid in ADMIN_IDS:
        return []
    cur.execute("SELECT username FROM channels ORDER BY id")
    missing = []
    for (ch,) in cur.fetchall():
        try:
            member = await bot.get_chat_member(ch, uid)
            if member.status in ("left", "kicked"):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return missing

async def sub_kb():
    cur.execute("SELECT username FROM channels ORDER BY id")
    rows = [[InlineKeyboardButton(text=f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")]
            for (ch,) in cur.fetchall()]
    rows.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def subscription_block(event):
    text = ("🔐 MAJBURIY OBUNA\n\n"
            "⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling.\n\n"
            "Obuna bo'lgach, «✅ Obunani tekshirish» tugmasini bosing.")
    if isinstance(event, Message):
        await event.answer(text, reply_markup=await sub_kb())
    elif isinstance(event, CallbackQuery):
        await event.answer("❌ Avval majburiy kanallarga obuna bo'ling!", show_alert=True)
        if event.message:
            await event.message.answer(text, reply_markup=await sub_kb())

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        if user is None or user.id in ADMIN_IDS:
            return await handler(event, data)
        if await check_sub(user.id):
            await subscription_block(event)
            return None
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

@dp.message(CommandStart())
async def start(m: Message):
    uid = m.from_user.id
    username = m.from_user.username or ""
    cur.execute("SELECT id FROM users WHERE id=?", (uid,))
    exists = cur.fetchone()
    ref = None
    parts = (m.text or "").split()
    if len(parts) > 1:
        try:
            ref = int(parts[1])
            if ref == uid: ref = None
        except ValueError: pass
    if not exists:
        cur.execute("INSERT INTO users(id,username,referred_by) VALUES(?,?,?)", (uid, username, ref))
        db.commit()
        if ref:
            cur.execute("UPDATE users SET balance=balance+? WHERE id=?", (REFERRAL_REWARD, ref))
            db.commit()
            try: await bot.send_message(ref, "🎉 Yangi referal! Hisobingizga +250 so'm berildi.")
            except Exception: pass
    if await check_sub(uid):
        await subscription_block(m)
        return
    await m.answer("🚀 BULLDROP SIGNAL botiga xush kelibsiz!", reply_markup=menu(uid))

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(c: CallbackQuery):
    missing = await check_sub(c.from_user.id)
    if missing:
        await c.answer("❌ Hali barcha majburiy kanallarga obuna bo'lmagansiz!", show_alert=True)
        return
    try: await c.message.delete()
    except Exception: pass
    await c.message.answer("✅ Obuna tasdiqlandi!\n\n🚀 Botdan to'liq foydalanishingiz mumkin.",
                            reply_markup=menu(c.from_user.id))
    await c.answer()

@dp.message(F.text == "📡 Signallar")
async def signals(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 5 ta signal", callback_data="signal_5_3")],
        [InlineKeyboardButton(text="⭐ 3 ta signal", callback_data="signal_3_6")],
        [InlineKeyboardButton(text="⭐ 2 ta signal", callback_data="signal_2_9")],
        [InlineKeyboardButton(text="⭐ 2 ta signal", callback_data="signal_2_12")],
        [InlineKeyboardButton(text="⭐ 1 ta signal", callback_data="signal_1_15")]])
    await m.answer("📡 SIGNAL TURINI TANLANG:\n\n💰 Narxi: 500 so'm", reply_markup=kb)

@dp.callback_query(F.data.startswith("signal_"))
async def select_signal(c: CallbackQuery):
    _, stars, bombs = c.data.split("_")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📡 SIGNAL OLISH — 500 so'm", callback_data=f"buy_{stars}_{bombs}")]])
    await c.message.edit_text(f"📡 Tanlangan signal:\n\n⭐ {stars} ta signal\n\n💰 Narxi: 500 so'm", reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: CallbackQuery):
    uid = c.from_user.id
    _, stars_s, bombs_s = c.data.split("_")
    stars, bombs = int(stars_s), int(bombs_s)
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    row = cur.fetchone()
    if not row:
        await c.answer("❌ Avval /start bosing.", show_alert=True); return
    balance = row[0]
    if balance < SIGNAL_PRICE:
        await c.answer("❌ Hisobingizda yetarli mablag' yo'q!", show_alert=True); return
    cur.execute("UPDATE users SET balance=balance-? WHERE id=?", (SIGNAL_PRICE, uid))
    cur.execute("INSERT INTO signals(user_id,stars,bombs) VALUES(?,?,?)", (uid, stars, bombs))
    db.commit()
    positions = set(random.sample(range(25), stars))
    rows = []
    for i in range(0,25,5):
        rows.append([InlineKeyboardButton(text=("⭐" if j in positions else "▫️"), callback_data="noop")
                     for j in range(i,i+5)])
    await c.message.edit_text(
        f"🎯 SIGNAL TAYYOR!\n\n⭐ {stars} ta signal\n\n💰 500 so'm yechildi.\n"
        f"💳 Qoldiq: {balance-SIGNAL_PRICE} so'm\n\n⚠️ Signal tasodifiy generatsiya qilindi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await c.answer()

@dp.callback_query(F.data == "noop")
async def noop(c: CallbackQuery): await c.answer()

@dp.message(F.text == "👥 Referal")
async def referral(m: Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    cur.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (m.from_user.id,))
    count = cur.fetchone()[0]
    await m.answer(f"👥 REFERAL\n\n👤 Referallar: {count} ta\n💰 1 referal: +250 so'm\n\n🔗 Havolangiz:\n{link}")

@dp.message(F.text == "💰 Balans")
async def balance(m: Message):
    cur.execute("SELECT balance FROM users WHERE id=?", (m.from_user.id,))
    row = cur.fetchone()
    await m.answer(f"💰 Balansingiz: {row[0] if row else 0} so'm")

@dp.message(F.text == "👤 Profil")
async def profile(m: Message):
    uid = m.from_user.id
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    row = cur.fetchone()
    bal = row[0] if row else 0
    cur.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (uid,))
    refs = cur.fetchone()[0]
    await m.answer(f"👤 PROFIL\n\n🆔 ID: {uid}\n💰 Balans: {bal} so'm\n👥 Referallar: {refs} ta")

@dp.message(F.text == "🛠 Admin panel")
async def admin(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📢 Kanallar", callback_data="channels")]])
    await m.answer("🛠 ADMIN PANEL\n\n📢 Kanal qo'shish: /addchannel @kanal\n🗑 Kanal o'chirish: /removechannel @kanal\n💰 Balans qo'shish: /addbalance USER_ID SUMMA", reply_markup=kb)

@dp.callback_query(F.data == "stats")
async def stats(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    cur.execute("SELECT COUNT(*) FROM users"); users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM signals"); sig = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(balance),0) FROM users"); money = cur.fetchone()[0]
    await c.message.answer(f"📊 STATISTIKA\n\n👤 Foydalanuvchilar: {users}\n📡 Signallar: {sig}\n💰 Balanslar jami: {money} so'm")
    await c.answer()

@dp.callback_query(F.data == "channels")
async def channels(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    cur.execute("SELECT username FROM channels ORDER BY id")
    data = cur.fetchall()
    text = "📢 MAJBURIY KANALLAR:\n\n" + ("\n".join("• "+x[0] for x in data) if data else "Hozircha kanal yo'q.")
    await c.message.answer(text+"\n\n➕ /addchannel @kanal\n🗑 /removechannel @kanal")
    await c.answer()

@dp.message(F.text.startswith("/addchannel"))
async def add_channel(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    parts=m.text.split(maxsplit=1)
    if len(parts)<2: await m.answer("Foydalanish: /addchannel @kanal"); return
    ch=parts[1].strip()
    if not ch.startswith("@"): ch="@"+ch
    if ch.lower()=="@atoolsx": await m.answer("❌ Bu kanal qo'shilmaydi."); return
    try:
        await bot.get_chat(ch)
        cur.execute("INSERT OR IGNORE INTO channels(username) VALUES(?)",(ch,)); db.commit()
        await m.answer(f"✅ Kanal qo'shildi: {ch}")
    except Exception:
        await m.answer("❌ Kanal topilmadi yoki bot kanalga kira olmayapti.\nBotni kanalga administrator qilib qo'ying.")

@dp.message(F.text.startswith("/removechannel"))
async def remove_channel(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    parts=m.text.split(maxsplit=1)
    if len(parts)<2: await m.answer("Foydalanish: /removechannel @kanal"); return
    ch=parts[1].strip()
    if not ch.startswith("@"): ch="@"+ch
    cur.execute("DELETE FROM channels WHERE LOWER(username)=LOWER(?)",(ch,)); db.commit()
    await m.answer(f"🗑️ Kanal o'chirildi: {ch}" if cur.rowcount else "❌ Kanal ro'yxatda yo'q.")

@dp.message(F.text.startswith("/addbalance"))
async def add_balance(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    parts=m.text.split()
    if len(parts)!=3: await m.answer("Foydalanish: /addbalance USER_ID SUMMA"); return
    try:
        uid, amount=int(parts[1]), int(parts[2])
        cur.execute("UPDATE users SET balance=balance+? WHERE id=?",(amount,uid)); db.commit()
        await m.answer("✅ Balans qo'shildi." if cur.rowcount else "❌ Foydalanuvchi topilmadi.")
    except ValueError: await m.answer("❌ ID yoki summa noto'g'ri.")

async def health(request): return web.Response(text="BULLDROP SIGNAL BOT OK")

async def start_web():
    app=web.Application()
    app.router.add_get("/",health); app.router.add_get("/health",health)
    runner=web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner,"0.0.0.0",int(os.environ.get("PORT","10000"))).start()

async def main():
    await start_web()
    await dp.start_polling(bot)

if __name__=="__main__": asyncio.run(main())
