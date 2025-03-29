import logging
import xml.etree.ElementTree as ET
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
import os
import random
import datetime
import string
import asyncio
ADMIN_ID = 272340476  # ← твой Telegram ID

def generate_discount_code():
    date_part = datetime.datetime.now().strftime("%d%m%y")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{date_part}-{random_part}"

# Загрузка переменных
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YML_FILE = "yml 2903.yml"

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Структура категорий и подкатегорий
CATEGORY_STRUCTURE = {
    "Для него": ["мастурбаторы", "насадки", "кольца", "куколки", "тренажеры для него"],
    "Для нее": ["вибраторы", "фалоимитаторы", "для клитора", "вибропули", "куклы", "тренажеры для нее"],
    "Для пар": ["страпоны", "фистинг", "для двоих", "мебель"],
    "Анал": ["плаги", "с вибрацией"],
    "Презервативы": ["классические", "супертонкие", "рельефные", "ароматизированные", "большие"],
    "Средства": ["бады", "пролонгаторы", "попперсы", "возбудители для него", "возбудители для нее", "сужающие", "для орального секса", "с феромонами", "гигиена"],
    "Смазки": ["водная", "силиконовая", "гибридная", "масла", "анальная", "оральная", "шарики", "жидкие вибраторы"],
    "Белье": ["комплект", "бдсм", "сетка", "кожа винил латекс", "костюмы", "трусики чулочки", "мужское"],
    "Подарки": []
}

category_map = {}
offers_list = []

def load_yml():
    global category_map, offers_list
    try:
        tree = ET.parse(YML_FILE)
        root = tree.getroot()
        categories = root.findall(".//category")
        offers_list[:] = root.findall(".//offer")
        category_map.clear()
        for cat in categories:
            cat_id = cat.attrib.get("id")
            name = cat.text.strip().lower()
            category_map[cat_id] = [x.strip() for x in name.split(";")]
    except Exception as e:
        logger.error(f"Ошибка загрузки YML: {e}")
        category_map.clear()
        offers_list.clear()
def load_stories():
    try:
        with open("stories.txt", "r", encoding="utf-8") as f:
            stories = f.read().split("\n\n")  # Каждая история через два переноса строки
        return [story.strip() for story in stories if story.strip()]
    except Exception as e:
        logger.error(f"Ошибка загрузки stories.txt: {e}")
        return []

def get_matching_offers(subcategory):
    matched = []
    subcategory = subcategory.lower()

    # Привязка "без вибрации" к плагам
    if subcategory == "без вибрации":
        subcategory = "плаги"  # Меняем подкатегорию на плаги

    # Привязка "Тренажеры для него" и "Тренажеры для нее"
    if subcategory == "тренажеры для него":
        subcategory = "тренажеры для него"  # Для "Для него"
    elif subcategory == "тренажеры для нее":
        subcategory = "тренажеры для нее"  # Для "Для нее"

    # Привязка "Мужское" в категорию "Белье"
    if subcategory == "мужское":
        subcategory = "белье"  # Относим к белью
    
    # Поиск совпадений для подкатегорий
    for offer in offers_list:
        cat_id = offer.findtext("categoryId")
        if not cat_id or cat_id not in category_map:
            continue
        offer_cats = category_map[cat_id]
        if subcategory in offer_cats:
            matched.append(offer)
    return matched

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
    markup = InlineKeyboardMarkup(keyboard)
    reply_kb = ReplyKeyboardMarkup(
    [[KeyboardButton("🏠 Меню"), KeyboardButton("📲 Написать нам")],
     [KeyboardButton("🌐 Перейти на сайт"), KeyboardButton("ℹ️ О нас"), KeyboardButton("📞 Наши контакты")],
     [KeyboardButton("🎲 Мне повезёт!")],
     [KeyboardButton("📚 Истории от подписчиков")]],
    resize_keyboard=True
)


    if update.message:
        await update.message.reply_text("Привет! Выбери категорию 🍑", reply_markup=markup)
        await update.message.reply_text("👇", reply_markup=reply_kb)
    elif update.callback_query:
        await update.callback_query.message.edit_text("Привет! Выбери категорию 🍑", reply_markup=markup)

async def show_subcategories(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    main_cat = query.data.split("_", 1)[1]
    subcats = CATEGORY_STRUCTURE.get(main_cat, [])

    # 🎁 Если категория "Подарки", сразу показываем товары
    if main_cat.lower() == "подарки":
        context.user_data["main_cat"] = main_cat
        context.user_data["sub_cat"] = main_cat
        matched_offers = get_matching_offers(main_cat)
        context.user_data["offers"] = matched_offers

        if not matched_offers:
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="start")],
                [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                "🫣 Подарков пока нет, но скоро обязательно появятся!",
                reply_markup=markup
            )
            return

        for offer in matched_offers[:5]:
            await send_offer(context, query.message.chat_id, offer)

        followup_keyboard = [
            [InlineKeyboardButton("🛒 Показать все подарки", callback_data="load_all")],
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start")]
        ]
        await query.message.reply_text("Вот твои подарочки 🎁😉", reply_markup=InlineKeyboardMarkup(followup_keyboard))
        return

    if not subcats:
        context.user_data["main_cat"] = main_cat
        context.user_data["sub_cat"] = main_cat
        await show_products(update, context)
        return

    keyboard = [[InlineKeyboardButton(sub.title(), callback_data=f"sub_{main_cat}_{sub}")] for sub in subcats]
    keyboard.append([InlineKeyboardButton("🔝 В начало", callback_data="start")])
    markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"Выбери подкатегорию для *{main_cat}*", reply_markup=markup, parse_mode="Markdown")



async def show_products(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    _, main_cat, sub_cat = query.data.split("_", 2)

    # Если категория "Подарки" (нет подкатегорий)
    if main_cat == "Подарки":
        matched_offers = get_matching_offers(main_cat)
    else:
        matched_offers = get_matching_offers(sub_cat)

    context.user_data["offers"] = matched_offers

    # Если товаров нет
    if not matched_offers:
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data=f"main_{main_cat}")],
            [InlineKeyboardButton("🔝 В начало", callback_data="start")],
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"🫣 Товары в подкатегории *{sub_cat.title()}* не найдены.\n\n"
            "Но мы можем поискать кое-что другое 😉",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return

    # Начальный offset = 0 (сколько товаров уже показали)
    context.user_data["offers_offset"] = 0

    # Если товаров <= 5 — показываем все сразу и не даём кнопку
    if len(matched_offers) <= 5:
        for offer in matched_offers:
            await send_offer(context, query.message.chat_id, offer)

        final_keyboard = [
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"main_{main_cat}")],
            [InlineKeyboardButton("🔝 В начало", callback_data="start")]
        ]
        await query.message.reply_text(
            "Вот все товары в этой подкатегории 💦",
            reply_markup=InlineKeyboardMarkup(final_keyboard)
        )
        return
    else:
        # Если товаров > 5
        for offer in matched_offers[:5]:
            await send_offer(context, query.message.chat_id, offer)

        # Запоминаем, что мы показали 5 товаров
        context.user_data["offers_offset"] = 5

        # Вот сама кнопка "Показать ещё 5"
        followup_keyboard = [
            [InlineKeyboardButton("Показать ещё 5", callback_data="load_more")],
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start")],
        ]

        # Отправляем сообщение с кнопкой
        await query.message.reply_text(
            "Это только начало... Хочешь ещё? 😏",
            reply_markup=InlineKeyboardMarkup(followup_keyboard)
        )


async def load_more(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Берём список товаров, который мы сохранили в user_data в show_products
    matched_offers = context.user_data.get("offers", [])
    # Берём текущий offset, который хранит, сколько товаров мы уже показали
    offset = context.user_data.get("offers_offset", 0)

    # Если вдруг нет товаров или мы уже показали все, выведем сообщение
    if not matched_offers or offset >= len(matched_offers):
        await query.message.reply_text("Тут уже пусто 🙈")
        return

    # Показываем следующие 5 товаров
    new_offset = offset + 5
    for offer in matched_offers[offset:new_offset]:
        await send_offer(context, query.message.chat_id, offer)

    # Обновляем offset, теперь мы показали ещё 5
    context.user_data["offers_offset"] = new_offset

    # Если после обновления offset мы дошли до конца
    if new_offset >= len(matched_offers):
        final_keyboard = [
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start")],
        ]
        await query.message.reply_text(
            "Вот и всё в этой подкатегории 💦",
            reply_markup=InlineKeyboardMarkup(final_keyboard)
        )
    else:
        # Ещё не все товары показаны, снова даём кнопку «Показать ещё 5»
        followup_keyboard = [
            [InlineKeyboardButton("Показать ещё 5", callback_data="load_more")],
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start")],
        ]
        await query.message.reply_text(
            "Продолжим? 😏",
            reply_markup=InlineKeyboardMarkup(followup_keyboard)
        )




async def show_all_products(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    # Теперь берём товары начиная с 6-го
    offers = context.user_data.get("offers", [])[5:]
    main_cat = context.user_data.get("main_cat", "")
    sub_cat = context.user_data.get("sub_cat", main_cat)

    if not offers:
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data=f"main_{main_cat}")],
            [InlineKeyboardButton("🔝 В начало", callback_data="start")],
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")]
        ]
        await query.message.reply_text(
            "В этой категории больше нет товаров 🫣\n\nНо мы можем поискать тебе что-то новенькое 😏",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    for offer in offers:
        await send_offer(context, query.message.chat_id, offer)

    final_keyboard = [
        [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"main_{main_cat}")],
        [InlineKeyboardButton("🔝 В начало", callback_data="start")]
    ]
    await query.message.reply_text("Вот и всё, что у нас есть в этой категории 💦", reply_markup=InlineKeyboardMarkup(final_keyboard))


async def send_offer(context: CallbackContext, chat_id, offer):
    # Забираем ID оффера из атрибута <offer id="...">
    offer_id = offer.attrib.get("id", "unknown")

    name = offer.findtext("name", "Без названия")
    price = offer.findtext("price", "Не указана")
    img = offer.findtext("picture")
    url = offer.findtext("url", "https://shhh.kz")

    # Вместо полного описания даём коротенький текст:
    caption = (
        f"🔥 <b>{name}</b>\n"
        f"💸 Цена: {price} KZT\n\n"
        "Нажми «Подробнее», чтобы увидеть описание."
    )

    # Две кнопки: «Подробнее» (с callback_data) и «В магазин»
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("Подробнее", callback_data=f"details_{offer_id}"),
        InlineKeyboardButton("В магазин", url=url)
    ]])

    if img:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=img,
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=markup
        )

async def show_details(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Получаем offer_id из callback_data, которая выглядит как "details_XXX"
    data = query.data
    offer_id = data.split("_", 1)[1]

    # Ищем нужный <offer> в offers_list (глобальная переменная или загруженная в load_yml)
    global offers_list
    offer = None
    for off in offers_list:
        if off.attrib.get("id") == offer_id:
            offer = off
            break

    # Если вдруг не нашли
    if not offer:
        await query.message.reply_text("Упс, описание не найдено 🙈")
        return

    # Берём полное описание из поля <description>
    desc = offer.findtext("description", "Описание отсутствует")
    name = offer.findtext("name", "Без названия")
    price = offer.findtext("price", "Не указана")
    url = offer.findtext("url", "https://shhh.kz")

    # Формируем новый caption, уже с описанием
    new_caption = (
        f"🔥 <b>{name}</b>\n"
        f"💸 Цена: {price} KZT\n\n"
        f"{desc}"
    )

    # Можно оставить только кнопку "В магазин" (либо дополнительные)
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("В магазин", url=url)
    ]])

    # Редактируем ту же фотку (тот же message), добавляя описание
    try:
        await query.message.edit_caption(
            caption=new_caption,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        # Если не удалось редактировать (слишком длинный текст или что-то ещё),
        # отправим новое сообщение
        await query.message.reply_text(f"Ошибка редактирования: {e}")


        
async def story_command(update: Update, context: CallbackContext) -> None:
    stories = load_stories()
    if not stories:
        await update.message.reply_text("Ой, похоже, истории пока сбежали! 🙈")
        return
    story = random.choice(stories)
    await update.message.reply_text(f"{story}")

async def text_handler(update: Update, context: CallbackContext) -> None:
    txt = update.message.text.lower()

    if "меню" in txt:
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Привет! Вот категории 😘", reply_markup=markup)

    elif "написать" in txt:
        await update.message.reply_text("📲 Выбери Telegram-номер:", reply_markup=InlineKeyboardMarkup([ 
            [InlineKeyboardButton("+77772992962", url="https://t.me/+77772992962")],
            [InlineKeyboardButton("+77472992962", url="https://t.me/+77472992962")],
            [InlineKeyboardButton("+77011001650", url="https://t.me/+77011001650")]
        ]))

    elif "сайт" in txt:
        await update.message.reply_text("💻 Наш сайт:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти на сайт", url="https://shhh.kz")]
        ]))

    elif "контакт" in txt:
        await update.message.reply_text(
        "<b>📞 Телефон / WhatsApp / Telegram:</b>\n"
        "+77772992962\n"
        "+77472992962\n\n"
        "<b>📸 Instagram:</b> <a href='https://www.instagram.com/shhhshopkz/?igsh=ZjYxc2hjaDI4MTI4#'>@shhhshopkz</a>\n"
        "<b>🎵 TikTok:</b> <a href='https://www.tiktok.com/@shhh.kz?_t=ZM-8uBBZXV9OK5&_r=1'>@shhh.kz</a>\n"
        "<b>🌐 Сайт:</b> <a href='https://shhh.kz/'>shhh.kz</a>\n\n"
        "<b>📍 Адрес:</b> <a href='https://go.2gis.com/HsMDg'>Жамбыла 180е, Алматы</a>\n"
        "🕙 10:00–22:00 ежедневно",
        parse_mode="HTML"
    )

    elif "истории" in txt:
        stories = load_stories()
        if not stories:
            await update.message.reply_text("Ой, истории пока приодеваются 😘")
        else:
            story = random.choice(stories)
            await update.message.reply_text(f"{story}")


    elif "о нас" in txt:
        await update.message.reply_text("Мы не просто интим-магазин… мы воплощение ваших желаний 😘")


    elif "мне повезёт" in txt:
        now = datetime.datetime.now()
        last_used_time = context.user_data.get("last_used_time")

        if last_used_time:
            elapsed = (now - last_used_time).total_seconds()
            if elapsed < 1800:
                remaining = 1800 - elapsed
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)

                await update.message.reply_text(
                    f"⏳ Подожди, сладкий, предыдущая скидка ещё действует!\n"
                    f"⏱ Осталось {minutes} мин {seconds} сек 😘"
                )
                return

        if not offers_list:
            await update.message.reply_text("Ой, кажется, пока нет товаров в списке! 🙈")
            return

        random_offer = random.choice(offers_list)
        discount_code = generate_discount_code()
        context.user_data["last_used_time"] = now
        context.user_data["active_discount"] = discount_code

        name = random_offer.findtext("name", "Без названия")
        price = random_offer.findtext("price", "Не указана")
        desc = random_offer.findtext("description", "Описание отсутствует")
        img = random_offer.findtext("picture")
        url = random_offer.findtext("url", "https://shhh.kz")

        caption = (
            f"🔥 <b>{name}</b>\n"
            f"💸 Цена: {price} KZT\n\n"
            f"{desc}\n\n"
            f"🎟️ <b>СКИДКА 15%</b> (только 30 мин)\n"
            f"🔑 <code>{discount_code}</code> <i>(нажми чтобы скопировать)</i>"
        )

        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔥 ИСПОЛЬЗОВАТЬ СКИДКУ", url=url)]])

        if img:
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=img,
                caption=caption,
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=caption,
                reply_markup=markup,
                parse_mode="HTML"
            )

                # 🔔 Отправляем уведомление тебе лично
        notification = (
            f"📢 <b>Выдана новая скидка!</b>\n\n"
            f"🔑 Код: <code>{discount_code}</code>\n"
            f"📌 Товар: {name}\n"
            f"🕒 {now.strftime('%d-%m-%Y %H:%M')}"
        )

        await context.bot.send_message(chat_id=ADMIN_ID, text=notification, parse_mode="HTML")

        # ⏳ Таймер на 30 минут
        async def discount_timer(context: CallbackContext, chat_id, code):
            await asyncio.sleep(1800)
            end_time = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
            context.user_data["active_discount"] = None
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ Скидка <code>{code}</code> аннулирована.\n🕑 {end_time}",
                parse_mode="HTML"
            )

        asyncio.create_task(discount_timer(context, update.message.chat_id, discount_code))

def main():
    load_yml()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("story", story_command))
    app.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(show_subcategories, pattern="^main_.*"))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^sub_.*_.*"))
    app.add_handler(CallbackQueryHandler(show_all_products, pattern="^load_all$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(load_more, pattern="^load_more$"))
    app.add_handler(CallbackQueryHandler(show_details, pattern="^details_.*"))
    logger.info("Бот запущен 🎉")
    app.run_polling()

if __name__ == "__main__":
    main()
