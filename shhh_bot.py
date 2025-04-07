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
import re  # 💅 Обязательно не забудь импорт вверху файла, если его ещё нет
import matplotlib.pyplot as plt
from telegram.ext import ConversationHandler
import csv
from datetime import datetime
import json
import random

ADMIN_ID = 272340476  # ← твой Telegram ID
user_18_confirmed = set()  # ← добавь сюда

def generate_discount_code():
    date_part = datetime.now().strftime("%d%m%y")
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
CATEGORY_SLUGS = {
    "мастурбаторы": "masturbatory",
    "насадки": "nasadki",
    "кольца": "rings",
    "тренажеры для него": "sport",
    "куколки": "dolls",
    "вибраторы": "vibrators",
    "фалоимитаторы": "dildos",
    "для клитора": "for-clits",
    "тренажеры для нее": "gym",
    "вибропули": "vibro-bullets",
    "куклы": "man-dolls",
    "страпоны": "strapons",
    "фистинг": "big-sizes",
    "для двоих": "for-two",
    "мебель": "furniture",
    "плаги": "anal-plugs",
    "с вибрацией": "anal-vibration",
    "классические": "classic-condoms",
    "супертонкие": "super-thin",
    "рельефные": "textured",
    "ароматизированные": "flavored",
    "большие": "big-size",
    "бады": "bio",
    "пролонгаторы": "prolongators",
    "попперсы": "poppers",
    "возбудители для него": "stimulants-for-him",
    "возбудители для нее": "stimulants-for-her",
    "сужающие": "constricting",
    "для орального секса": "for-oral-sex",
    "с феромонами": "with-pheromones",
    "гигиена": "hygiene",
    "водная": "water-lubes",
    "силиконовая": "silicone-lubes",
    "гибридная": "hybrid",
    "масла": "massage-oils",
    "анальная": "anal-lubes",
    "оральная": "oral-lubes",
    "шарики": "balls-lubes",
    "жидкие вибраторы": "liquid-vibrators",
    "комплект": "set-lingerine",
    "бдсм": "bdsm",
    "сетка": "net",
    "кожа винил латекс": "leather-vinyl-latex",
    "костюмы": "role-playing-costumes",
    "трусики чулочки": "panties-stockings",
    "мужское": "underwear-for-him",
    "подарки": "presents",
    "белье": "all-lingerine",
    "презервативы": "all-condoms",
    "средства": "all-funds",
    "смазки": "all-lubes",
    "для него": "all-for-mans",
    "для нее": "all-for-womans",
    "для пар": "all-for-couples",
    "анал": "all-for-anal"
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
            # 🧃 Хардкодим категорию для попперсов (если что-то пошло не так)
            if cat_id == "285205905532":
                category_map[cat_id] = ["попперсы", "средства"]
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

# 🔍 Поиск товаров по названию и описанию
def search_products_by_query(query):
    results = []
    query_lower = query.lower()
    for offer in offers_list:
        name = offer.findtext("name", "").lower()
        desc = offer.findtext("description", "").lower()
        if query_lower in name or query_lower in desc:
            results.append(offer)
    return results

def get_matching_offers(subcategory):
    matched = []
    subcategory = subcategory.lower()

    # 🧠 Мапинг в случае нестандартных названий
    if subcategory == "без вибрации":
        subcategory = "плаги"
    elif subcategory == "тренажеры для него":
        subcategory = "тренажеры для него"
    elif subcategory == "тренажеры для нее":
        subcategory = "тренажеры для нее"
    elif subcategory == "мужское":
        subcategory = "белье"

    for offer in offers_list:
        cat_id = offer.findtext("categoryId")
        if not cat_id or cat_id not in category_map:
            continue

        offer_cats = category_map[cat_id]
        if subcategory in offer_cats:
            if offer.findtext("url") is not None:
                matched.append(offer)

    # 🌐 Получаем slug-ссылку на категорию
    slug = CATEGORY_SLUGS.get(subcategory, "")
    return matched, slug



async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Если пользователь не подтвердил возраст — сначала проверка 18+
    if user_id not in user_18_confirmed:
        keyboard = [
            [
                InlineKeyboardButton("🔞 Да, мне есть 18", callback_data="age_yes"),
                InlineKeyboardButton("❌ Нет, мне нет 18", callback_data="age_no"),
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text("Этот бот только для взрослых (18+). Подтверди возраст:", reply_markup=markup)
        elif update.callback_query:
            await update.callback_query.message.reply_text("Этот бот только для взрослых (18+). Подтверди возраст:", reply_markup=markup)
        return  # ← ОЧЕНЬ ВАЖНО! Останавливаем здесь, пока не подтвердит возраст

    # Если возраст подтверждён, но пол ещё не выбран — спрашиваем пол
    if "gender" not in context.user_data:
        keyboard = [
            [InlineKeyboardButton("👦 Мальчик", callback_data="gender_boy")],
            [InlineKeyboardButton("👧 Девочка", callback_data="gender_girl")],
            [InlineKeyboardButton("🚁 Боевой вертолет", callback_data="gender_heli")]
        ]
        await update.message.reply_text(
            "Выбери, кто ты сегодня 😏",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Всё подтверждено — можно сразу в меню
    await gender_callback(update, context)


    gender = context.user_data.get("gender", "boy")
    if gender == "girl":
        nickname = "киска"
    elif gender == "heli":
        nickname = "вертолётик"
    else:
        nickname = "котик"

    reply_kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🏠 Меню"), KeyboardButton("🎲 Мне повезёт!"), KeyboardButton("🧠 Фетиш дня")],
            [KeyboardButton("📖 Квест"), KeyboardButton("📚 Истории от подписчиков"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("📲 Написать нам"), KeyboardButton("ℹ️ О нас"), KeyboardButton("🌐 Перейти на сайт")],
            [KeyboardButton("📞 Наши контакты")]
        ],
        resize_keyboard=True
    )
    await update.message.reply_text("Выбери, что хочешь сделать дальше 😘", reply_markup=reply_kb)



    if update.message:
        await update.message.reply_text(
            f"Привет, {nickname} 😘 Я помогу тебе выбрать что-то интересное... Вот что у нас есть:",
            reply_markup=reply_kb
        )
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🍑 Выбери категорию 🍑", reply_markup=markup)

    elif update.callback_query:
        await update.callback_query.message.reply_text(
            f"Привет, {nickname} 😘 Я помогу тебе выбрать что-то интересное... Вот что у нас есть:",
            reply_markup=reply_kb
        )
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
        markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text("🍑 Выбери категорию 🍑", reply_markup=markup)




async def gender_callback(update: Update, context: CallbackContext):
    nickname = get_user_nickname(context)

    # 🔘 Сочная клавиатура
    reply_kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🏠 Меню"), KeyboardButton("🎲 Мне повезёт!"), KeyboardButton("🧠 Фетиш дня")],
            [KeyboardButton("📖 Квест"), KeyboardButton("📚 Истории от подписчиков"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("📲 Написать нам"), KeyboardButton("ℹ️ О нас"), KeyboardButton("🌐 Перейти на сайт")],
            [KeyboardButton("📞 Наши контакты")]
        ],
        resize_keyboard=True
    )

    if update.message:
        await update.message.reply_text(
            "Выбери, что хочешь сделать дальше 😘",
            reply_markup=reply_kb
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "Выбери, что хочешь сделать дальше 😘",
            reply_markup=reply_kb
        )

    await update.message.reply_text("Выбери, что хочешь сделать дальше 😘", reply_markup=reply_kb)


    await query.message.reply_text(
        f"Вот что у нас есть, {nickname} 🍑",
        reply_markup=reply_kb
    )

    keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
    markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Выбери категорию", reply_markup=markup)



def get_user_nickname(context: CallbackContext) -> str:
    gender = context.user_data.get("gender", "boy")
    if gender == "girl":
        return "киска"
    elif gender == "heli":
        return "вертолётик"
    return "котик"

async def show_subcategories(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    main_cat = query.data.split("_", 1)[1]
    log_action(update.effective_user, f"открыл категорию: {main_cat}")
    subcats = CATEGORY_STRUCTURE.get(main_cat, [])

    # 🎁 Если категория "Подарки", сразу показываем товары
    if main_cat.lower() == "подарки":
        context.user_data["main_cat"] = main_cat
        context.user_data["sub_cat"] = main_cat
        matched_offers, _ = get_matching_offers(main_cat)
        context.user_data["offers"] = matched_offers
        
        if isinstance(matched_offers, tuple):
            matched_offers = matched_offers[0]

        if not matched_offers:
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="go_home")],
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
            [InlineKeyboardButton("🔙 Назад", callback_data="go_home")]
        ]
        await query.message.reply_text("Вот твои подарочки 🎁😉", reply_markup=InlineKeyboardMarkup(followup_keyboard))
        return

    if not subcats:
        context.user_data["main_cat"] = main_cat
        context.user_data["sub_cat"] = main_cat
        await show_products(update, context)
        return

    keyboard = [[InlineKeyboardButton(sub.title(), callback_data=f"sub_{main_cat}_{sub}")] for sub in subcats]
    keyboard.append([InlineKeyboardButton("🔝 В начало", callback_data="go_home")])
    markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"Выбери подкатегорию для *{main_cat}*", reply_markup=markup, parse_mode="Markdown")



async def show_products(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    _, main_cat, sub_cat = query.data.split("_", 2)
    log_action(update.effective_user, f"открыл подкатегорию: {sub_cat}")


    # Если категория "Подарки" (нет подкатегорий)
    if main_cat == "Подарки":
        matched_offers = get_matching_offers(main_cat)
    else:
        matched_offers, _ = get_matching_offers(sub_cat)

    context.user_data["offers"] = matched_offers

    # Если товаров нет
    if not matched_offers:
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data=f"main_{main_cat}")],
            [InlineKeyboardButton("🔝 В начало", callback_data="go_home")],
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
            [InlineKeyboardButton("🔝 В начало", callback_data="go_home")]
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
            [InlineKeyboardButton("🔙 Назад", callback_data="go_home")],
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
            [InlineKeyboardButton("🔙 Назад", callback_data="go_home")],
        ]
        await query.message.reply_text(
            "Вот и всё в этой подкатегории 💦",
            reply_markup=InlineKeyboardMarkup(final_keyboard)
        )
    else:
        # ЗАКОНЧИЛИ РАЗЬЕБ КНОПКИ НАЗАД И В НАЧАЛО!!!
        # Ещё не все товары показаны, снова даём кнопку «Показать ещё 5»
        followup_keyboard = [
            [InlineKeyboardButton("Показать ещё 5", callback_data="load_more")],
            [InlineKeyboardButton("🔗 Перейти на сайт", url="https://shhh.kz")],
            [InlineKeyboardButton("🔙 Назад", callback_data="go_home")],
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
            [InlineKeyboardButton("🔝 В начало", callback_data="go_home")],
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
        [InlineKeyboardButton("🔝 В начало", callback_data="go_home")]
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
    if offer is None:
        await query.message.reply_text("Упс, описание не найдено 🙈")
        return


    # Берём полное описание из поля <description>
    desc = offer.findtext("description", "Описание отсутствует")
    desc = desc.replace("<br>", "\n").replace("<br >", "\n").replace("<br />", "\n")
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

async def handle_start_button(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    log_action(update.effective_user, "нажал кнопку 🟢 Старт")

    if user_id not in user_18_confirmed:
        keyboard = [
            [
                InlineKeyboardButton("🔞 Да, мне есть 18", callback_data="age_yes"),
                InlineKeyboardButton("❌ Нет, мне нет 18", callback_data="age_no"),
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Этот бот только для взрослых (18+). Подтверди возраст:", reply_markup=markup)
        return

    # если уже подтвержден 18+ — сразу к полу
    await ask_gender(update, context)
    
async def ask_gender(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("👦 Мальчик", callback_data="gender_boy")],
        [InlineKeyboardButton("👧 Девочка", callback_data="gender_girl")],
        [InlineKeyboardButton("🚁 Боевой вертолет", callback_data="gender_heli")]
    ]

    if update.message:
        await update.message.reply_text(
            "Выбери, кто ты сегодня 😏",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            "Выбери, кто ты сегодня 😏",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        
async def story_command(update: Update, context: CallbackContext) -> None:
    stories = load_stories()
    log_action(update.effective_user, "открыл 📚 Истории от подписчиков")
    if not stories:
        await update.message.reply_text("Ой, похоже, истории пока сбежали! 🙈")
        return

    used = context.user_data.get("used_stories", set())

    # Выбираем только те, что ещё не показывались
    unused_stories = [s for i, s in enumerate(stories) if i not in used]

    if not unused_stories:
        context.user_data["used_stories"] = set()
        nickname = get_user_nickname(context)
        await update.message.reply_text(f"{nickname}, ты уже прочитал(а) все истории 😘 Обновляем список...")
        unused_stories = stories.copy()

    # Случайно выбираем одну из неиспользованных
    chosen_story = random.choice(unused_stories)
    index = stories.index(chosen_story)
    context.user_data.setdefault("used_stories", set()).add(index)

    await update.message.reply_text(f"{chosen_story}")

async def show_search_results(update: Update, context: CallbackContext):
    results = context.user_data.get("search_results", [])
    offset = context.user_data.get("search_offset", 0)
    chunk = results[offset:offset+3]

    if not chunk:
        await update.message.reply_text("👀 Больше ничего не нашла… Но ты можешь поискать ещё 😉")
        return

    for offer in chunk:
        await send_offer(context, update.effective_chat.id, offer)

    context.user_data["search_offset"] = offset + 3

    if context.user_data["search_offset"] < len(results):
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Показать ещё", callback_data="search_more")]
        ])
        await update.message.reply_text("💦 Хочешь ещё? Я покажу…", reply_markup=markup)

async def fallback_to_support(update: Update, context: CallbackContext):
    txt = update.message.text.lower()

    if any(keyword in txt for keyword in ["меню", "написать", "сайт"]):
        return  # Уже обрабатывается в основной логике

    await update.message.reply_text(
        "🔔 Кажется, ты хочешь что-то обсудить... \n"
        "Выбери, с кем ты хочешь пообщаться 😘",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👠 Хозяйка Полина", url="https://t.me/+77772992962")],
            [InlineKeyboardButton("🖤 Госпожа Виктория", url="https://t.me/+77472992962")],
            [InlineKeyboardButton("🧠 Профессор", url="https://t.me/+77011001650")]
        ])
    )

# 💬 Обработчик текста: команды, поиск, рандом и прочее
async def text_handler(update: Update, context: CallbackContext) -> None:
    txt = update.message.text.lower()

    # 💬 Поиск по названию и описанию
import re  # 💦 Добавь один раз в начало файла, если ещё не добавлен!

# 💬 Обработка запроса после "поиск"
async def text_handler(update: Update, context: CallbackContext) -> None:
    txt = update.message.text.lower()

    # 💬 Обработка запроса после "поиск"
    if context.user_data.get("awaiting_search"):
        context.user_data["awaiting_search"] = False
        search_query = txt.strip().lower()
        pattern = r'\b' + re.escape(search_query)

        matched_offers = []
        for offer in offers_list:
            name = offer.findtext("name", "").lower()
            desc = offer.findtext("description", "").lower()

            if re.search(pattern, name) or re.search(pattern, desc):
                matched_offers.append(offer)

        if not matched_offers:
            await update.message.reply_text("😔 Увы, я ничего не нашла по твоему запросу...")
            return

        context.user_data["search_results"] = matched_offers
        context.user_data["search_offset"] = 0
        await show_search_results(update, context)
        return

    # 👉 Остальная логика text_handler ниже...

    # 💬 Команда "поиск"
    if "поиск" in txt:
        await update.message.reply_text("🔎 Напиши слово или фразу, и я найду тебе самые сочные игрушки 😘")
        context.user_data["awaiting_search"] = True
        return

    # 💬 История-квест
    elif "квест" in txt or "история" in txt:
        await run_quest_start(update, context)

    # 💬 Истории от подписчиков
    elif "истории" in txt:
        await story_command(update, context)

    # 💬 Мне повезёт
    elif "мне повезёт" in txt:
        await handle_lucky(update, context)

    # 💬 Меню
    elif "меню" in txt:
        log_action(update.effective_user, "нажал 🏠 Меню")
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
        markup = InlineKeyboardMarkup(keyboard)
        nickname = get_user_nickname(context)
        await update.message.reply_text(
            f"Привет, {nickname}! Вот категории 😘",
            reply_markup=markup
        )

    # 💬 Контакты
    elif "контакт" in txt:
        log_action(update.effective_user, "нажал 📞 Наши контакты")
        await update.message.reply_text(
            "<b>📞 Телефон / WhatsApp / Telegram:</b>\n"
            "+77772992962\n"
            "+77472992962\n\n"
            "<b>📸 Instagram:</b> <a href='https://www.instagram.com/shhhshopkz/'>@shhhshopkz</a>\n"
            "<b>🎵 TikTok:</b> <a href='https://www.tiktok.com/@shhh.kz'>@shhh.kz</a>\n"
            "<b>🌐 Сайт:</b> <a href='https://shhh.kz/'>shhh.kz</a>\n\n"
            "<b>📍 Адрес:</b> Жамбыла 180е, Алматы\n"
            "🕙 10:00–22:00 ежедневно",
            parse_mode="HTML"
        )

    # 💬 Сайт
    elif "сайт" in txt:
        log_action(update.effective_user, "нажал 🌐 Перейти на сайт")
        await update.message.reply_text(
            "💻 Наш сайт:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Перейти на сайт", url="https://shhh.kz")]
            ])
        )
    elif "написать" in txt:
        log_action(update.effective_user, "нажал 📲 Написать нам")

        # 🧠 Профессор
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo="https://raw.githubusercontent.com/Grehovskiy/media/main/proff.jpg",
            caption=(
                "🧠 <b>Профессор</b>\n"
                "Кибер-учёный с руками из титана и мозгом, как у вибратора 5-го поколения 🤓\n\n"
                "«Добро пожаловать в лабораторию удовольствий.\n"
                "Я могу объяснить тебе всё...\n"
                "Но гораздо интереснее — показать 😏»"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Написать Профессору", url="https://t.me/+77011001650")]
            ])
        )
                # 👠 Хозяйка
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo="https://raw.githubusercontent.com/Grehovskiy/media/main/saler.jpg",
            caption=(
                "👠 <b>Хозяйка</b>\n"
                "Уверенная, соблазнительная и знает всё про твои желания 😏\n\n"
                "«Привет, котик. Хочешь я покажу тебе свои... лучшие товары?» 😘"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Написать Продавщице", url="https://t.me/+77772992962")]
            ])
        )

        # 💋 Ассистентка
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo="https://raw.githubusercontent.com/Grehovskiy/media/main/asist.jpg",
            caption=(
                "💋 <b>Ассистентка</b>\n"
                "Нежная, внимательная и эмпатичная. Всё подберёт со вкусом 💫\n\n"
                "«Привет, солнышко. Я рядом, чтобы подобрать тебе то, о чём ты даже не решался мечтать...» 🌸"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Написать Ассистентке", url="https://t.me/+77472992962")]
            ])
        )




        # 🧠 Профессор
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id='-1002463724882',
            message_id=109
        )
        await update.message.reply_text(
            "🧠 Профессор\n"
            "Кибер-учёный с руками из титана и мозгом как у вибратора 5-го поколения 🤓",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Написать Профессору", url="https://t.me/+77011001650")]
            ])
        )




    # 💬 О нас
    elif "о нас" in txt:
        await update.message.reply_text("Мы – не просто магазин. Мы создаём пространство для ваших самых сокровенных желаний 😘")

    # 💬 Подарки, товары, купить
    elif "подарки" in txt or "товары" in txt or "купить" in txt:
        matched_offers = get_matching_offers(txt)
        if matched_offers:
            for offer in matched_offers:
                name = offer.findtext("name", "Без названия")
                price = offer.findtext("price", "Не указана")
                url = offer.findtext("url", "https://shhh.kz")
                description = offer.findtext("description", "Описание отсутствует")

                await update.message.reply_text(
                    f"🔥 <b>{name}</b>\n💸 Цена: {price} KZT\n\n{description}\n\n🔗 <a href='{url}'>Перейти к товару</a>",
                    parse_mode="HTML"
                )
        else:
            await update.message.reply_text("Извините, товаров по вашему запросу не найдено 😔")

    # 💬 Остальное
    else:
        nickname = get_user_nickname(context)
        await update.message.reply_text(
            f"🔔 Кажется, {nickname}, ты хочешь что-то обсудить.\n"
            f"Выбери, с кем пофлиртовать 😘",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👠 Хозяйка", url="https://t.me/+77772992962")],
                [InlineKeyboardButton("🖤 Ассистентка", url="https://t.me/+77472992962")],
                [InlineKeyboardButton("🧠 Профессор", url="https://t.me/+77011001650")]
            ])
        )


async def age_verification_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "age_yes":
        user_18_confirmed.add(user_id)
        log_action(update.effective_user, "подтвердил возраст 18+")
        await ask_gender(query, context)
    else:
        await query.edit_message_text("Ой... тогда тебе сюда пока нельзя 🙈 Возвращайся, когда созреешь 🍑")

def log_action(user, action):
    with open("analytics.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user.id,
            user.username or "без username",
            action
        ])

async def fetish_of_the_day(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    nickname = get_user_nickname(context)

    try:
        with open("fetishes.json", "r", encoding="utf-8") as f:
            fetishes = json.load(f)
    except Exception as e:
        await update.message.reply_text("Ой... не могу найти свои извращения 😢")
        return

    fetishes_with_products = [f for f in fetishes if f.get("products") and len(f["products"]) > 0]

    if not fetishes_with_products:
        await update.message.reply_text("Ой... не могу найти ни одного фетиша с товаром 😢")
        return

    now = datetime.now()
    last_time = context.bot_data.get("fetish_last_time")
    if not last_time or last_time.date() != now.date():
        chosen = random.choice(fetishes_with_products)
        context.bot_data["fetish_of_the_day"] = chosen
        context.bot_data["fetish_last_time"] = now
    else:
        chosen = context.bot_data.get("fetish_of_the_day")
        if not chosen or not chosen.get("products"):
            chosen = random.choice(fetishes_with_products)
            context.bot_data["fetish_of_the_day"] = chosen
            context.bot_data["fetish_last_time"] = now

    title = chosen["title"]
    desc = chosen["description"]
    product = chosen["products"][0]

    name = product["name"]
    img = product.get("img", "")
    full_url = product.get("url", "https://shhh.kz")
    
    # 💥 Обрезаем до категории: всё до /tproduct/
    if "/tproduct/" in full_url:
        category_url = full_url.split("/tproduct/")[0] + "/"
    else:
        category_url = full_url  # fallback

    caption = f"🧠 <b>{title}</b>\n\n{desc}\n\n🔥 <b>{name}</b>"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Перейти к категории", url=category_url)]
    ])

    if img:
        await update.message.reply_photo(
            photo=img,
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        await update.message.reply_text(caption, parse_mode="HTML", reply_markup=markup)

    await update.message.reply_text("❤️‍🔥 Завтра будет новый фетиш... 😈")



# 💰 Обработка "Мне повезёт"
async def handle_lucky(update: Update, context: CallbackContext):
    now = datetime.now()
    log_action(update.effective_user, "нажал 🎲 Мне повезёт")
    last_used_time = context.user_data.get("last_used_time")

    if last_used_time:
        elapsed = (now - last_used_time).total_seconds()
        if elapsed < 1800:
            remaining = 1800 - elapsed
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)

            nickname = get_user_nickname(context)
            await update.message.reply_text(
                f"⏳ Подожди, {nickname}, предыдущая скидка ещё действует!\n"
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

    # 🔔 Уведомляем админа
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
        context.user_data["active_discount"] = None
        end_time = datetime.now().strftime('%d-%m-%Y %H:%M')
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"❌ Скидка <code>{code}</code> аннулирована.\n🕑 {end_time}",
            parse_mode="HTML"
        )

    asyncio.create_task(discount_timer(context, update.message.chat_id, discount_code))

async def show_analytics(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ Только для тебя, мой повелитель 😘")
        return

    try:
        from collections import Counter
        import datetime

        actions = []
        today_actions = []
        users_all = set()
        users_today = set()

        with open("analytics.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    actions.append(row)
                    user_id = row[1]
                    users_all.add(user_id)
                    try:
                        dt = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                        if dt.date() == datetime.datetime.now().date():
                            today_actions.append(row)
                            users_today.add(user_id)
                    except:
                        pass

        # 📊 График активности
        generate_activity_graph()
        with open("graph.png", "rb") as photo:
            await update.message.reply_photo(photo, caption="📊 График активности по часам")

        # 💦 Основная статистика
        total = len(actions)
        all_counter = Counter([a[3] for a in actions])
        today_counter = Counter([a[3] for a in today_actions])

        report = (
            "👥 <b>Уникальные пользователи:</b>\n"
            f"🗓 Сегодня: <b>{len(users_today)}</b>\n"
            f"📅 Всего за всё время: <b>{len(users_all)}</b>\n\n"
        )

        report += f"<b>💦 Всего впрысков: {total}</b>\n\n"

        report += "🏆 <b>Топ действий за всё время:</b>\n"
        for action, num in all_counter.most_common(10):
            report += f"👉 {action}: {num}\n"

        report += "\n📅 <b>Сегодняшняя активность:</b>\n"
        for action, num in today_counter.most_common(10):
            report += f"🔸 {action}: {num}\n"

        await update.message.reply_text(report, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"Ошибка в аналитике: {e}")



def generate_activity_graph(file="analytics.csv", output="graph.png"):
    import matplotlib.pyplot as plt
    from collections import Counter
    import datetime

    hours = []

    with open(file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 1:
                try:
                    dt = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    hours.append(dt.hour)
                except:
                    continue

    counter = Counter(hours)
    hours_sorted = sorted(counter.items())

    x = [f"{hour}:00" for hour, _ in hours_sorted]
    y = [count for _, count in hours_sorted]

    plt.figure(figsize=(10, 5))
    plt.bar(x, y)
    plt.xlabel("Часы")
    plt.ylabel("Количество действий")
    plt.title("Активность по часам")
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    
async def run_quest_start(update: Update, context: CallbackContext):
    try:
        with open("quests.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            quests = data.get("quests", [])

        buttons = []
        for quest in quests:
            quest_id = quest["id"]
            title = quest["title"]
            buttons.append([InlineKeyboardButton(title, callback_data=f"start_quest_{quest_id}")])

        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "💋 Выбери свою эротическую историю:",
            reply_markup=markup
        )

    except Exception as e:
        await update.message.reply_text(f"Ошибка загрузки квестов: {e}")

async def handle_quest_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    quest_id = query.data.replace("start_quest_", "")
    context.user_data["selected_quest_id"] = quest_id
    await show_quest_step(update, context, "start")
    
async def run_quest_step(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    step_id = query.data.replace("quest_step_", "")
    await show_quest_step(update, context, step_id)


# 💬 Отображение шага истории
async def show_quest_step(update: Update, context: CallbackContext, step_id: str):
    try:
        quest_id = context.user_data.get("selected_quest_id", "mansion")
        with open("quests.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            quest = next((q for q in data["quests"] if q["id"] == quest_id), None)
            if not quest:
                await update.effective_chat.send_message("Квест не найден 😢")
                return
            steps = quest["steps"]

        step = next((s for s in steps if s["id"] == step_id), None)
        if not step:
            await update.effective_chat.send_message("Куда-то не туда свернули 🙈")
            return

        if "product_id" in step:
            await update.effective_chat.send_message(step["text"])
            product_id = step["product_id"]
            offer = next((o for o in offers_list if o.attrib.get("id") == product_id), None)

            if offer:
                await send_offer(context, update.effective_chat.id, offer)
                discount_code = generate_discount_code()
                context.user_data["quest_discount"] = discount_code
                now = datetime.now()

                await update.effective_chat.send_message(
                    f"🎟️ <b>СКИДКА 10%</b> (только 30 мин)\n"
                    f"🔑 <code>{discount_code}</code> <i>(нажми чтобы скопировать)</i>",
                    parse_mode="HTML"
                )

                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"📢 Новая скидка по квесту!\n🔑 <code>{discount_code}</code>\n🕒 {now.strftime('%d-%m-%Y %H:%M')}",
                    parse_mode="HTML"
                )
            else:
                await update.effective_chat.send_message(step["text"] + "\n\n(А товарик потерялся... 😢)")
            return

        options = step.get("options", [])
        if options:
            keyboard = [
                [InlineKeyboardButton(opt["label"], callback_data=f"quest_step_{opt['next']}")]
                for opt in options
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.effective_chat.send_message(step["text"], reply_markup=markup)
        else:
            await update.effective_chat.send_message(step["text"])

    except Exception as e:
        await update.effective_chat.send_message(f"Ошибка в квесте: {e}")


        # 👉 Если обычный шаг с вариантами
        options = step.get("options", [])
        if options:
            keyboard = [
                [InlineKeyboardButton(opt["label"], callback_data=f"quest_step_{opt['next']}")]
                for opt in options
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.effective_chat.send_message(step["text"], reply_markup=markup)
        else:
            await update.effective_chat.send_message(step["text"])

    except Exception as e:
        print(f"❌ Ошибка в show_quest_step: {e}")
        await update.effective_chat.send_message("Ошибка загрузки квеста 😢")



# 💦 Показ результатов поиска по 3 за раз
async def show_search_results(update: Update, context: CallbackContext):
    results = context.user_data.get("search_results", [])
    offset = context.user_data.get("search_offset", 0)

    # 💬 Определим, куда слать сообщение
    message = update.message or update.callback_query.message

    if not results:
        await message.reply_text("😔 Пока ничего не нашла…")
        return

    for offer in results[offset:offset+3]:
        await send_offer(context, update.effective_chat.id, offer)

    context.user_data["search_offset"] = offset + 3

    if context.user_data["search_offset"] < len(results):
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Показать ещё", callback_data="search_more")]
        ])
        await message.reply_text("Хочешь ещё? 😏", reply_markup=markup)

# 💦 Обработчик кнопки "Показать ещё" в поиске
async def show_more_search_results(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await show_search_results(update, context)

    # Формируем кнопочки
    keyboard = [[InlineKeyboardButton(choice["text"], callback_data=f"quest_step_{choice['next_id']}")] for choice in step.get("choices", [])]
    markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message(step["text"], reply_markup=markup)

async def reload_yml_command(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ Ты не мой босс 😘")
        return

    try:
        load_yml()
        await update.message.reply_text("✅ YML-файл обновлён успешно!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при загрузке YML: {e}")

    # КОРРЕКТИРОВКА ЕБАНОЙ КНОПКИ В НАЧАЛО!
async def go_to_main_menu(update: Update, context: CallbackContext):
    nickname = get_user_nickname(context)
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            f"Привет, {nickname} 😘 Я помогу тебе выбрать что-то интересное... Вот что у нас есть:",
            reply_markup=markup
        )

async def handle_go_home(update: Update, context: CallbackContext):
    nickname = get_user_nickname(context)
    reply_kb = build_reply_keyboard()

    keyboard = [[InlineKeyboardButton(cat, callback_data=f"main_{cat}")] for cat in CATEGORY_STRUCTURE]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            f"Привет снова, {nickname} 😘 Вот наше горячее меню:",
            reply_markup=reply_kb
        )
        await update.callback_query.message.reply_text("🍑 Выбери категорию 🍑", reply_markup=markup)

def main():
    load_yml()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # 👠 Хэндлеры по порядку
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("story", story_command))
    app.add_handler(CallbackQueryHandler(gender_callback, pattern="^gender_"))
    app.add_handler(CallbackQueryHandler(age_verification_callback, pattern="^age_"))
    app.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(show_subcategories, pattern="^main_.*"))
    app.add_handler(CallbackQueryHandler(go_to_main_menu, pattern="^go_home$"))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^sub_.*_.*"))
    app.add_handler(CallbackQueryHandler(load_more, pattern="^load_more$"))
    app.add_handler(CallbackQueryHandler(show_all_products, pattern="^load_all$"))
    app.add_handler(CallbackQueryHandler(show_details, pattern="^details_.*"))
    app.add_handler(CallbackQueryHandler(show_search_results, pattern="^search_more$"))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🟢 Старт$"), handle_start_button))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🧠 Фетиш дня$"), fetish_of_the_day))
    app.add_handler(CommandHandler("quest", run_quest_start))
    app.add_handler(CallbackQueryHandler(handle_quest_selection, pattern=r"^start_quest_.*"))
    app.add_handler(CallbackQueryHandler(run_quest_step, pattern=r"^quest_step_.*"))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("(?i)^📖 квест$"), run_quest_start))
    app.add_handler(CallbackQueryHandler(handle_go_home, pattern="^go_home$"))
    app.add_handler(CommandHandler("reload_yml", reload_yml_command))
    app.add_handler(CommandHandler("stats", show_analytics))

    # 🔥 Основной обработчик текстов (твои условия: "меню", "написать", "сайт")
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Бот запущен 🎉")
    app.run_polling()

if __name__ == "__main__":
    main()
