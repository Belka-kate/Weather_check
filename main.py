import sqlite3
import requests
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TELEGRAM_TOKEN = '7385675604:AAHLmM0lR3vnHlLaCvlcF7HmovGaqnM_dMg'
WEATHERAPI_KEY = 'cf98e1d7b5954f21be3153900241210'


# Устанавливаем соединение с базой данных
def connect_db():
    return sqlite3.connect('my_database.db')

# Функция для создания таблицы Users, если она не существует
def create_table():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            city TEXT,
            interval INTEGER
        )
    ''')
    connection.commit()
    connection.close()

# Функция для получения погоды
def get_weather(city):
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHERAPI_KEY}&q={city}&aqi=no"
    response = requests.get(url)
    if response.status_code == 200:
        print("Ok")
        return response.json()
    else:
        print("something is wrong")
        return None

active_timers = {}

# Функция для добавления пользователя в базу данных
def add_user(user_id, city, interval):
    connection = connect_db()
    cursor = connection.cursor()
    try:
        cursor.execute('INSERT INTO Users (user_id, city, interval) VALUES (?, ?, ?)', (user_id, city, interval))
    except sqlite3.IntegrityError:
        print("Пользователь уже существует:", user_id)
    finally:
        connection.commit()
        connection.close()

# Функция для обновления пользователя
def update_user(user_id, city=None, interval=None):
    connection = connect_db()
    cursor = connection.cursor()
    if city:
        cursor.execute('UPDATE Users SET city = ? WHERE user_id = ?', (city, user_id))
    if interval is not None:
        cursor.execute('UPDATE Users SET interval = ? WHERE user_id = ?', (interval, user_id))
    connection.commit()
    connection.close()

# Функция для получения пользователя
def get_user(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM Users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    connection.close()
    return user

# Команда старт
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Пожалуйста, введите название города, для которого хотите получить погоду.")

# Установка города
def set_city(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    city = update.message.text
    weather = get_weather(city)
    if weather:
        update_user(user_id, city=city, interval=None)  # Устанавливаем город, интервал оставляем пустым
        ask_for_interval(update)  # Запрашиваем интервал после установки города
    else:
        update.message.reply_text("Город не найден, попробуйте еще раз.")

# Основное меню
def main_menu(update: Update):
    reply_keyboard = [['Сменить город', 'Сменить интервал']]
    update.message.reply_text(
        "Вы можете поменять город или интервал получения сообщений через клавиатуру",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

# Запрос интервала
def ask_for_interval(update: Update):
    reply_keyboard = [['1 минута', '1 час'], ['12 часов', '1 день']]
    update.message.reply_text(
        "Выберите интервал обновления сообщений:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

# Обработка ответов от пользователя
def handle_reply(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = get_user(user_id)

    if user is None:
        add_user(user_id, city=None, interval=None)
        update.message.reply_text("Пожалуйста, введите название города.")

    elif update.message.text == 'Сменить город':
        update.message.reply_text("Пожалуйста, введите новое название города.")
    elif update.message.text == 'Сменить интервал':
        ask_for_interval(update)
    elif update.message.text in ['1 минута', '1 час', '12 часов', '1 день']:
        interval_map = {
            '1 минута': 60,
            '1 час': 3600,
            '12 часов': 43200,
            '1 день': 86400
        }
        interval = interval_map[update.message.text]
        update_user(user_id, interval=interval)
        update.message.reply_text(f"Интервал обновления установлен на {update.message.text}.")
        send_weather_update(update.message, user_id)
        main_menu(update)
    else:
        set_city(update, context)

# Отправка обновлений погоды
def send_weather_update(message, user_id):
    user = get_user(user_id)
    if user:
        city = user[2]
        weather = get_weather(city)
        if weather:
            temp = weather['current']['temp_c']
            description = weather['current']['condition']['text']
            msg = f"Обновление погоды в {city.title()}: {temp}°C, {description}."
            message.reply_text(msg)

            interval = user[3]

            # Останавливаем предыдущий таймер, если он существует
            timer = active_timers.get(user_id)
            if timer is not None:
                timer.cancel()

            # Создаем и запускаем новый таймер
            new_timer = threading.Timer(interval, send_weather_update, args=[message, user_id])
            new_timer.start()
            active_timers[user_id] = new_timer

# Основная функция для запуска бота
def main():
    create_table()  # Создаем таблицу при запуске бота
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_reply))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
