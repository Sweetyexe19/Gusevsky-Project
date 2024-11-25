import telebot
from telebot import types
import json
import uuid
import logging
import sqlite3
from config import token, ADMIN_IDS

bot = telebot.TeleBot(token)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных
def init_db():
    """Инициализация базы данных."""
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    # Создаем таблицу продуктов, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            price REAL,
            photo_id TEXT,
            quantity INTEGER
        )
    ''')
    conn.commit()
    conn.close()


init_db()  # Инициализируем базу данных

# Добавление товара в базу данных
def add_product_to_db(name, description, price, photo_id, quantity):
    try:
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        product_id = str(uuid.uuid4())  # Генерация уникального ID для товара
        cursor.execute('''
            INSERT INTO products (id, name, description, price, photo_id, quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (product_id, name, description, price, photo_id, quantity))
        conn.commit()
        conn.close()
        logger.info(f"Товар '{name}' добавлен в базу данных.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении товара в базу данных: {e}")


# Загрузка всех товаров из базы данных
def load_products():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return products


# Основное меню
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Товары🛍', callback_data='btn1')
    btn3 = types.InlineKeyboardButton('Саппорт🤝', callback_data='btn3')

    markup.add(btn1)
    markup.add(btn3)

    # Кнопка для админов (будет показана только админу)
    if message.from_user.id in ADMIN_IDS:
        btn_admin = types.InlineKeyboardButton('Админ-панель🔧', callback_data='admin_panel')
        markup.add(btn_admin)

    bot.send_message(message.chat.id, 'Привет, ты в моем магазине!', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'btn3')
def support(call):
    bot.send_message(call.message.chat.id, 'Если нужна помощь с ботом - Ваш Текст')

# Админская панель
@bot.callback_query_handler(func=lambda call: call.data == 'admin_panel')
def admin_panel(call):
    if call.from_user.id in ADMIN_IDS:
        markup = types.InlineKeyboardMarkup()
        btn_add = types.InlineKeyboardButton('Добавить товар', callback_data='add_product')
        btn_delete = types.InlineKeyboardButton('Удалить товар', callback_data='delete_product')
        btn_view = types.InlineKeyboardButton('Посмотреть товары', callback_data='view_products')
        btn_back = types.InlineKeyboardButton('Назад', callback_data='back_to_menu')
        markup.add(btn_add, btn_delete, btn_view, btn_back)

        bot.send_message(call.message.chat.id, "Админ-панель:\nВыберите действие:", reply_markup=markup)


# Возврат в главное меню
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_menu')
def back_to_menu(call):
    start(call.message)


# Добавление товара
@bot.callback_query_handler(func=lambda call: call.data == 'add_product')
def add_product(call):
    if call.from_user.id in ADMIN_IDS:
        bot.send_message(call.message.chat.id, "Отправьте название товара.")
        bot.register_next_step_handler(call.message, process_product_name)


def process_product_name(message):
    product_name = message.text
    bot.send_message(message.chat.id, "Отправьте описание товара.")
    bot.register_next_step_handler(message, process_product_description, product_name)


def process_product_description(message, product_name):
    product_description = message.text
    bot.send_message(message.chat.id, "Отправьте фото товара.")
    bot.register_next_step_handler(message, process_product_photo, product_name, product_description)


def process_product_photo(message, product_name, product_description):
    if message.photo:
        photo_id = message.photo[-1].file_id  # Берем самое большое изображение
        bot.send_message(message.chat.id, "Отправьте цену товара.")
        bot.register_next_step_handler(message, process_product_price, product_name, product_description, photo_id)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте фото товара.")
        bot.register_next_step_handler(message, process_product_photo, product_name, product_description)


def process_product_price(message, product_name, product_description, photo_id):
    try:
        product_price = float(message.text)  # Преобразуем текст в число
        bot.send_message(message.chat.id, "Отправьте количество товара на складе.")
        bot.register_next_step_handler(message, process_product_quantity, product_name, product_description, photo_id, product_price)
    except ValueError:
        bot.send_message(message.chat.id, "Цена должна быть числом. Попробуйте снова.")
        bot.register_next_step_handler(message, process_product_price, product_name, product_description, photo_id)


def process_product_quantity(message, product_name, product_description, photo_id, product_price):
    try:
        product_quantity = int(message.text)  # Преобразуем текст в число
        add_product_to_db(product_name, product_description, product_price, photo_id, product_quantity)
        bot.send_message(message.chat.id, f"Товар '{product_name}' добавлен!")
        start(message)  # Возвращаем в главное меню
    except ValueError:
        bot.send_message(message.chat.id, "Количество товара должно быть целым числом. Попробуйте снова.")
        bot.register_next_step_handler(message, process_product_quantity, product_name, product_description, photo_id, product_price)


# Удаление товара с подтверждением
@bot.callback_query_handler(func=lambda call: call.data == 'delete_product')
def delete_product(call):
    if call.from_user.id in ADMIN_IDS:
        products = load_products()
        if products:
            markup = types.InlineKeyboardMarkup()
            for product in products:
                markup.add(
                    types.InlineKeyboardButton(f"Удалить {product[1]}", callback_data=f"confirm_delete_{product[0]}"))
            markup.add(types.InlineKeyboardButton("Назад", callback_data="back_to_admin"))
            bot.send_message(call.message.chat.id, "Выберите товар для удаления:", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "Товары не найдены.")
            admin_panel(call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_'))
def confirm_delete_product(call):
    if call.from_user.id in ADMIN_IDS:
        product_id = call.data[len('confirm_delete_'):]

        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        cursor.execute(''' DELETE FROM products WHERE id = ? ''', (product_id,))
        conn.commit()
        conn.close()

        bot.send_message(call.message.chat.id, "Товар удален!")
        admin_panel(call.message)


# Просмотр товаров
@bot.callback_query_handler(func=lambda call: call.data == 'view_products')
def view_products(call):
    if call.from_user.id in ADMIN_IDS:
        products = load_products()
        if products:
            for product in products:
                bot.send_photo(call.message.chat.id, product[4],
                               caption=f"Товар: {product[1]}\nОписание: {product[2]}\nЦена: {product[3]}₽\nКоличество: {product[5]}")
        else:
            bot.send_message(call.message.chat.id, "Товары не найдены.")
        admin_panel(call)  # Возвращаем в админ панель


# Основные кнопки для пользователей
@bot.callback_query_handler(func=lambda call: call.data == 'btn1')  # Товары
def show_products(call):
    products = load_products()
    markup = types.InlineKeyboardMarkup()
    for product in products:
        btn = types.InlineKeyboardButton(f"🔧 {product[1]}", callback_data=f"product_{product[1]}")
        markup.add(btn)
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back_to_menu'))  # Кнопка назад
    bot.send_message(call.message.chat.id, "Выберите товар:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
def show_product_details(call):
    product_name = call.data[len("product_"):]
    products = load_products()
    for product in products:
        if product[1] == product_name:
            bot.send_photo(call.message.chat.id, product[4],
                           caption=f"Товар: {product[1]}\nОписание: {product[2]}\nЦена: {product[3]}₽\nКоличество: {product[5]}")


if __name__ == '__main__':
    bot.polling(none_stop=True)
