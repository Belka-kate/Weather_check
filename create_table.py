import sqlite3

# Устанавливаем соединение с базой данных
connection = sqlite3.connect('my_database.db')
cursor = connection.cursor()

# Создаем таблицу Users
cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
user INTEGER PRIMARY KEY,
username TEXT,
city TEXT,
interval INTEGER
)
''')

# Сохраняем изменения и закрываем соединение
connection.commit()
connection.close()