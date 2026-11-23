import asyncio
import html
import json
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ---------------------------------------------------------------- config

def load_env(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
REVIEWS_URL = os.environ.get("REVIEWS_URL", "https://t.me/your_reviews_channel")

DATA_DIR = Path(os.environ.get("DATA_DIR", "."))
USERS_FILE = DATA_DIR / "users.json"
PRODUCTS_FILE = DATA_DIR / "products.json"

# ---------------------------------------------------------------- storage

def read_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user(uid: int) -> dict:
    return read_json(USERS_FILE, {}).get(str(uid), {"lang": "ru", "adult": False})


def save_user(uid: int, **fields):
    users = read_json(USERS_FILE, {})
    u = users.get(str(uid), {"lang": "ru", "adult": False})
    u.update(fields)
    users[str(uid)] = u
    write_json(USERS_FILE, users)


def get_products() -> dict:
    return read_json(PRODUCTS_FILE, {"next_id": 1, "items": []})


def lang_of(uid: int) -> str:
    return get_user(uid).get("lang", "ru")

# ---------------------------------------------------------------- texts

T = {
    "ru": {
        "age_q": "🔞 Бот предназначен только для лиц старше 18 лет.\nВам уже есть 18?",
        "age_yes": "Да, мне 18+",
        "age_no": "Нет",
        "age_denied": "К сожалению, доступ закрыт.",
        "choose": "✨ <b>Выберите опцию</b>",
        "b_stock": "📦 Актуальное наличие",
        "b_order": "🛒 Оформление заказа",
        "b_lang": "🌐 Выбор языка",
        "b_reviews": "⭐ Посмотреть отзывы",
        "b_review": "✍️ Оставить отзыв",
        "b_admin": "💬 Связь с администратором",
        "back": "⬅️ В меню",
        "stock_title": "📦 <b>Актуальное наличие</b>",
        "in_stock": "✅ <b>В наличии:</b>",
        "soon": "⏳ <b>Скоро в наличии:</b>",
        "none": "— пока пусто",
        "order_pick": "🛒 Выберите товар:",
        "order_empty": "Сейчас нет товаров в наличии. Загляните позже!",
        "order_date": "📅 Выбрано: <b>{name}</b>\n\nНа какую <b>дату</b> назначить встречу? (например, 25.11)",
        "order_time": "🕒 Во сколько? (например, 18:30)",
        "order_place": "📍 Укажите <b>место встречи</b>:",
        "order_confirm": "Проверьте заказ:\n\n🧴 {name}\n📅 {date}\n🕒 {time}\n📍 {place}",
        "b_confirm": "✅ Подтвердить",
        "b_cancel": "❌ Отмена",
        "order_sent": "✅ Заказ отправлен! Администратор подтвердит встречу в ближайшее время.",
        "order_ok": "✅ Администратор подтвердил ваш заказ ({name}, {date} {time}).",
        "order_no": "❌ К сожалению, администратор не смог подтвердить заказ ({name}). Свяжитесь с ним через меню.",
        "cancelled": "Отменено.",
        "review_ask": "✍️ Напишите ваш отзыв одним сообщением:",
        "review_thanks": "Спасибо за отзыв! 🙏",
        "contact_on": "💬 Запрос отправлен. Администратор скоро ответит прямо здесь.\nМожете писать сообщения — они дойдут до него.",
        "contact_fwd": "Отправлено ✅",
        "from_admin": "💬 <b>Администратор:</b>\n{text}",
        "lang_pick": "🌐 Выберите язык:",
        "lang_set": "Язык изменён ✅",
        "text_only": "Пожалуйста, отправьте текст.",
    },
    "uk": {
        "age_q": "🔞 Бот призначений лише для осіб старше 18 років.\nВам вже є 18?",
        "age_yes": "Так, мені 18+",
        "age_no": "Ні",
        "age_denied": "На жаль, доступ закрито.",
        "choose": "✨ <b>Оберіть опцію</b>",
        "b_stock": "📦 Актуальна наявність",
        "b_order": "🛒 Оформлення замовлення",
        "b_lang": "🌐 Вибір мови",
        "b_reviews": "⭐ Переглянути відгуки",
        "b_review": "✍️ Залишити відгук",
        "b_admin": "💬 Зв'язок з адміністратором",
        "back": "⬅️ В меню",
        "stock_title": "📦 <b>Актуальна наявність</b>",
        "in_stock": "✅ <b>В наявності:</b>",
        "soon": "⏳ <b>Незабаром у наявності:</b>",
        "none": "— поки порожньо",
        "order_pick": "🛒 Оберіть товар:",
        "order_empty": "Зараз немає товарів у наявності. Загляньте пізніше!",
        "order_date": "📅 Обрано: <b>{name}</b>\n\nНа яку <b>дату</b> призначити зустріч? (наприклад, 25.11)",
        "order_time": "🕒 О котрій? (наприклад, 18:30)",
        "order_place": "📍 Вкажіть <b>місце зустрічі</b>:",
        "order_confirm": "Перевірте замовлення:\n\n🧴 {name}\n📅 {date}\n🕒 {time}\n📍 {place}",
        "b_confirm": "✅ Підтвердити",
        "b_cancel": "❌ Скасувати",
        "order_sent": "✅ Замовлення надіслано! Адміністратор незабаром підтвердить зустріч.",
        "order_ok": "✅ Адміністратор підтвердив ваше замовлення ({name}, {date} {time}).",
        "order_no": "❌ На жаль, адміністратор не зміг підтвердити замовлення ({name}). Зв'яжіться з ним через меню.",
        "cancelled": "Скасовано.",
        "review_ask": "✍️ Напишіть ваш відгук одним повідомленням:",
        "review_thanks": "Дякуємо за відгук! 🙏",
        "contact_on": "💬 Запит надіслано. Адміністратор скоро відповість прямо тут.\nМожете писати повідомлення — вони дійдуть до нього.",
        "contact_fwd": "Надіслано ✅",
        "from_admin": "💬 <b>Адміністратор:</b>\n{text}",
        "lang_pick": "🌐 Оберіть мову:",
        "lang_set": "Мову змінено ✅",
        "text_only": "Будь ласка, надішліть текст.",
    },
    "en": {
        "age_q": "🔞 This bot is for adults only (18+).\nAre you 18 or older?",
        "age_yes": "Yes, I'm 18+",
        "age_no": "No",
        "age_denied": "Sorry, access denied.",
        "choose": "✨ <b>Choose an option</b>",
        "b_stock": "📦 Current stock",
        "b_order": "🛒 Place an order",
        "b_lang": "🌐 Language",
        "b_reviews": "⭐ Read reviews",
        "b_review": "✍️ Leave a review",
        "b_admin": "💬 Contact administrator",
        "back": "⬅️ Menu",
        "stock_title": "📦 <b>Current stock</b>",
        "in_stock": "✅ <b>In stock:</b>",
        "soon": "⏳ <b>Coming soon:</b>",
        "none": "— nothing yet",
        "order_pick": "🛒 Choose a product:",
        "order_empty": "Nothing is in stock right now. Please check back later!",
        "order_date": "📅 Selected: <b>{name}</b>\n\nWhich <b>date</b> for the meeting? (e.g. 25.11)",
        "order_time": "🕒 What time? (e.g. 18:30)",
        "order_place": "📍 Enter the <b>meeting place</b>:",
        "order_confirm": "Check your order:\n\n🧴 {name}\n📅 {date}\n🕒 {time}\n📍 {place}",
        "b_confirm": "✅ Confirm",
        "b_cancel": "❌ Cancel",
        "order_sent": "✅ Order sent! The administrator will confirm the meeting soon.",
        "order_ok": "✅ The administrator confirmed your order ({name}, {date} {time}).",
        "order_no": "❌ Sorry, the administrator couldn't confirm your order ({name}). Please contact them via the menu.",
        "cancelled": "Cancelled.",
        "review_ask": "✍️ Write your review in one message:",
        "review_thanks": "Thanks for your review! 🙏",
        "contact_on": "💬 Request sent. The administrator will reply right here.\nYou can write messages — they'll be delivered.",
        "contact_fwd": "Sent ✅",
        "from_admin": "💬 <b>Administrator:</b>\n{text}",
        "lang_pick": "🌐 Choose language:",
        "lang_set": "Language changed ✅",
        "text_only": "Please send text.",
    },
}


def t(uid: int, key: str, **kw) -> str:
    s = T[lang_of(uid)][key]
    return s.format(**kw) if kw else s

# ---------------------------------------------------------------- keyboards

def main_menu(uid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(uid, "b_stock"), callback_data="m:stock")
    kb.button(text=t(uid, "b_order"), callback_data="m:order")
    kb.button(text=t(uid, "b_lang"), callback_data="m:lang")
    kb.button(text=t(uid, "b_reviews"), url=REVIEWS_URL)
    kb.button(text=t(uid, "b_review"), callback_data="m:review")
    kb.button(text=t(uid, "b_admin"), callback_data="m:contact")
    kb.adjust(1, 1, 1, 1, 1, 1)
    return kb.as_markup()


def back_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(uid, "back"), callback_data="m:home")]]
    )

# ---------------------------------------------------------------- states

class Order(StatesGroup):
    date = State()
    time = State()
    place = State()


class Review(StatesGroup):
    text = State()


class Contact(StatesGroup):
    chat = State()


class AdminReply(StatesGroup):
    text = State()


dp = Dispatcher(storage=MemoryStorage())


def esc(s: str) -> str:
    return html.escape(s or "")


def who(user) -> str:
    name = esc(user.full_name)
    uname = f" (@{user.username})" if user.username else ""
    return f'<a href="tg://user?id={user.id}">{name}</a>{uname} · <code>{user.id}</code>'


async def show_menu(target, uid: int, edit: bool = False):
    text, kb = t(uid, "choose"), main_menu(uid)
    if edit and isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except Exception:
            await target.message.answer(text, reply_markup=kb)
    else:
        msg = target.message if isinstance(target, CallbackQuery) else target
        await msg.answer(text, reply_markup=kb)

# ---------------------------------------------------------------- start / age

@dp.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    if not get_user(uid).get("adult"):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=T["ru"]["age_yes"], callback_data="age:yes"),
            InlineKeyboardButton(text=T["ru"]["age_no"], callback_data="age:no"),
        ]])
        await m.answer(T["ru"]["age_q"], reply_markup=kb)
        return
    await show_menu(m, uid)


@dp.callback_query(F.data.startswith("age:"))
async def age(c: CallbackQuery):
    if c.data == "age:yes":
        save_user(c.from_user.id, adult=True)
        await show_menu(c, c.from_user.id, edit=True)
    else:
        await c.message.edit_text(T["ru"]["age_denied"])
    await c.answer()


@dp.callback_query(F.data == "m:home")
async def home(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_menu(c, c.from_user.id, edit=True)
    await c.answer()

# ---------------------------------------------------------------- stock

@dp.callback_query(F.data == "m:stock")
async def stock(c: CallbackQuery):
    uid = c.from_user.id
    items = get_products()["items"]
    ins = [i for i in items if i["status"] == "in_stock"]
    soon = [i for i in items if i["status"] == "soon"]

    def fmt(i):
        price = f" — {esc(str(i['price']))}" if i.get("price") else ""
        return f"• {esc(i['name'])}{price}"

    text = f"{t(uid, 'stock_title')}\n\n{t(uid, 'in_stock')}\n"
    text += "\n".join(fmt(i) for i in ins) if ins else t(uid, "none")
    text += f"\n\n{t(uid, 'soon')}\n"
    text += "\n".join(f"• {esc(i['name'])}" for i in soon) if soon else t(uid, "none")
    await c.message.edit_text(text, reply_markup=back_kb(uid))
    await c.answer()

# ---------------------------------------------------------------- language

@dp.callback_query(F.data == "m:lang")
async def lang_menu(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="l:ru")],
        [InlineKeyboardButton(text="🇺🇦 Українська", callback_data="l:uk")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="l:en")],
    ])
    await c.message.edit_text(t(c.from_user.id, "lang_pick"), reply_markup=kb)
    await c.answer()


@dp.callback_query(F.data.startswith("l:"))
async def lang_set(c: CallbackQuery):
    save_user(c.from_user.id, lang=c.data.split(":")[1])
    await c.answer(t(c.from_user.id, "lang_set"))
    await show_menu(c, c.from_user.id, edit=True)

# ---------------------------------------------------------------- order

@dp.callback_query(F.data == "m:order")
async def order_start(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    await state.clear()
    ins = [i for i in get_products()["items"] if i["status"] == "in_stock"]
    if not ins:
        await c.message.edit_text(t(uid, "order_empty"), reply_markup=back_kb(uid))
        await c.answer()
        return
    kb = InlineKeyboardBuilder()
    for i in ins:
        price = f" — {i['price']}" if i.get("price") else ""
        kb.button(text=f"{i['name']}{price}", callback_data=f"p:{i['id']}")
    kb.button(text=t(uid, "back"), callback_data="m:home")
    kb.adjust(1)
    await c.message.edit_text(t(uid, "order_pick"), reply_markup=kb.as_markup())
    await c.answer()


@dp.callback_query(F.data.startswith("p:"))
async def order_pick(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    pid = int(c.data.split(":")[1])
    item = next((i for i in get_products()["items"] if i["id"] == pid and i["status"] == "in_stock"), None)
    if not item:
        await c.answer("—", show_alert=True)
        return
    await state.update_data(name=item["name"])
    await state.set_state(Order.date)
    await c.message.edit_text(t(uid, "order_date", name=esc(item["name"])), reply_markup=back_kb(uid))
    await c.answer()


@dp.message(Order.date, F.text)
async def order_date(m: Message, state: FSMContext):
    await state.update_data(date=m.text.strip()[:50])
    await state.set_state(Order.time)
    await m.answer(t(m.from_user.id, "order_time"), reply_markup=back_kb(m.from_user.id))


@dp.message(Order.time, F.text)
async def order_time(m: Message, state: FSMContext):
    await state.update_data(time=m.text.strip()[:50])
    await state.set_state(Order.place)
    await m.answer(t(m.from_user.id, "order_place"), reply_markup=back_kb(m.from_user.id))


@dp.message(Order.place, F.text)
async def order_place(m: Message, state: FSMContext):
    uid = m.from_user.id
    await state.update_data(place=m.text.strip()[:200])
    d = await state.get_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(uid, "b_confirm"), callback_data="o:yes"),
        InlineKeyboardButton(text=t(uid, "b_cancel"), callback_data="m:home"),
    ]])
    await m.answer(
        t(uid, "order_confirm", name=esc(d["name"]), date=esc(d["date"]),
          time=esc(d["time"]), place=esc(d["place"])),
        reply_markup=kb,
    )


@dp.callback_query(F.data == "o:yes")
async def order_confirm(c: CallbackQuery, state: FSMContext, bot: Bot):
    uid = c.from_user.id
    d = await state.get_data()
    if not d.get("name") or not d.get("place"):
        await c.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"a:ok:{uid}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"a:no:{uid}"),
    ], [
        InlineKeyboardButton(text="💬 Написать клиенту", callback_data=f"a:re:{uid}"),
    ]])
    await bot.send_message(
        ADMIN_ID,
        f"🛒 <b>Новый заказ</b>\n\n👤 {who(c.from_user)}\n"
        f"🧴 {esc(d['name'])}\n📅 {esc(d['date'])}\n🕒 {esc(d['time'])}\n📍 {esc(d['place'])}",
        reply_markup=kb,
    )
    # keep order data in admin-side message for accept/decline
    users = read_json(DATA_DIR / "last_orders.json", {})
    users[str(uid)] = {"name": d["name"], "date": d["date"], "time": d["time"]}
    write_json(DATA_DIR / "last_orders.json", users)
    await state.clear()
    await c.message.edit_text(t(uid, "order_sent"), reply_markup=back_kb(uid))
    await c.answer()


@dp.callback_query(F.data.startswith("a:"), F.from_user.id == ADMIN_ID)
async def admin_order_action(c: CallbackQuery, bot: Bot, state: FSMContext):
    _, action, uid_s = c.data.split(":")
    uid = int(uid_s)
    if action == "re":
        await state.set_state(AdminReply.text)
        await state.update_data(target=uid)
        await c.message.answer(f"✍️ Напишите сообщение для клиента <code>{uid}</code> (одним сообщением):")
        await c.answer()
        return
    o = read_json(DATA_DIR / "last_orders.json", {}).get(uid_s, {"name": "", "date": "", "time": ""})
    key = "order_ok" if action == "ok" else "order_no"
    try:
        await bot.send_message(uid, t(uid, key, name=esc(o["name"]), date=esc(o["date"]), time=esc(o["time"])))
    except Exception:
        pass
    mark = "✅ Принят" if action == "ok" else "❌ Отклонён"
    await c.message.edit_text(c.message.html_text + f"\n\n<b>{mark}</b>")
    await c.answer()

# ---------------------------------------------------------------- reviews

@dp.callback_query(F.data == "m:review")
async def review_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(Review.text)
    await c.message.edit_text(t(c.from_user.id, "review_ask"), reply_markup=back_kb(c.from_user.id))
    await c.answer()


@dp.message(Review.text, F.text)
async def review_got(m: Message, state: FSMContext, bot: Bot):
    uid = m.from_user.id
    await bot.send_message(ADMIN_ID, f"⭐ <b>Новый отзыв</b>\n\n👤 {who(m.from_user)}\n\n{esc(m.text)}")
    await state.clear()
    await m.answer(t(uid, "review_thanks"), reply_markup=main_menu(uid))

# ---------------------------------------------------------------- contact admin

@dp.callback_query(F.data == "m:contact")
async def contact_start(c: CallbackQuery, state: FSMContext, bot: Bot):
    uid = c.from_user.id
    await state.set_state(Contact.chat)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Ответить", callback_data=f"a:re:{uid}")
    ]])
    await bot.send_message(ADMIN_ID, f"💬 <b>Клиент запросил связь</b>\n\n👤 {who(c.from_user)}", reply_markup=kb)
    await c.message.edit_text(t(uid, "contact_on"), reply_markup=back_kb(uid))
    await c.answer()


@dp.message(Contact.chat, F.text)
async def contact_msg(m: Message, bot: Bot):
    uid = m.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Ответить", callback_data=f"a:re:{uid}")
    ]])
    await bot.send_message(ADMIN_ID, f"✉️ {who(m.from_user)}:\n\n{esc(m.text)}", reply_markup=kb)
    await m.answer(t(uid, "contact_fwd"))


@dp.message(AdminReply.text, F.from_user.id == ADMIN_ID, F.text)
async def admin_reply(m: Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    target = d["target"]
    try:
        await bot.send_message(target, t(target, "from_admin", text=esc(m.text)))
        await m.answer("✅ Отправлено клиенту.")
    except Exception as e:
        await m.answer(f"⚠️ Не удалось отправить: {e}")
    await state.clear()

# ---------------------------------------------------------------- admin: stock management

@dp.message(Command("help_admin"), F.from_user.id == ADMIN_ID)
async def help_admin(m: Message):
    await m.answer(
        "<b>Управление наличием</b>\n\n"
        "/list — все товары с ID\n"
        "/add Название | цена — товар в наличии\n"
        "/soon Название — товар «скоро в наличии»\n"
        "/instock ID — перевести в «в наличии»\n"
        "/del ID — удалить товар"
    )


@dp.message(Command("list"), F.from_user.id == ADMIN_ID)
async def admin_list(m: Message):
    items = get_products()["items"]
    if not items:
        await m.answer("Список пуст. Добавьте: /add Название | цена")
        return
    lines = [
        f"{i['id']}. {'✅' if i['status'] == 'in_stock' else '⏳'} {esc(i['name'])}"
        f"{' — ' + esc(str(i['price'])) if i.get('price') else ''}"
        for i in items
    ]
    await m.answer("\n".join(lines))


def _add_item(name: str, price: str, status: str) -> int:
    data = get_products()
    pid = data["next_id"]
    data["next_id"] += 1
    data["items"].append({"id": pid, "name": name, "price": price, "status": status})
    write_json(PRODUCTS_FILE, data)
    return pid


@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def admin_add(m: Message):
    arg = (m.text or "").partition(" ")[2].strip()
    if not arg:
        await m.answer("Формат: /add Название | цена")
        return
    name, _, price = arg.partition("|")
    pid = _add_item(name.strip(), price.strip(), "in_stock")
    await m.answer(f"✅ Добавлено (ID {pid})")


@dp.message(Command("soon"), F.from_user.id == ADMIN_ID)
async def admin_soon(m: Message):
    name = (m.text or "").partition(" ")[2].strip()
    if not name:
        await m.answer("Формат: /soon Название")
        return
    pid = _add_item(name, "", "soon")
    await m.answer(f"⏳ Добавлено (ID {pid})")


@dp.message(Command("instock"), F.from_user.id == ADMIN_ID)
async def admin_instock(m: Message):
    arg = (m.text or "").partition(" ")[2].strip()
    data = get_products()
    for i in data["items"]:
        if arg.isdigit() and i["id"] == int(arg):
            i["status"] = "in_stock"
            write_json(PRODUCTS_FILE, data)
            await m.answer("✅ Теперь в наличии")
            return
    await m.answer("Не найдено. Формат: /instock ID")


@dp.message(Command("del"), F.from_user.id == ADMIN_ID)
async def admin_del(m: Message):
    arg = (m.text or "").partition(" ")[2].strip()
    data = get_products()
    before = len(data["items"])
    if arg.isdigit():
        data["items"] = [i for i in data["items"] if i["id"] != int(arg)]
    if len(data["items"]) < before:
        write_json(PRODUCTS_FILE, data)
        await m.answer("🗑 Удалено")
    else:
        await m.answer("Не найдено. Формат: /del ID")

# ---------------------------------------------------------------- run

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
