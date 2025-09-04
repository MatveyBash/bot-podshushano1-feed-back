import telebot
from telebot import types

# Настройки бота
TOKEN = '7800950778:AAHGhD9DlZYV0iaxZRVZSMR1Ultw81qtz38'
bot = telebot.TeleBot(TOKEN)

# Администраторы и их темы (ID: [темы])
ADMINS = {
    1616523146: ['Баги⚠️'],
    5683628958: ['Жалобы/обращение/апеляция⛔'],
    6172742677: ['Вопросы🤔']  # Новый администратор для общих вопросов
}

# Словари для хранения данных
user_states = {}  # Текущее состояние пользователя
user_requests = {}  # Активные обращения пользователей
admin_requests = {}  # Распределенные обращения к админам


# Клавиатура с темами
def get_topics_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    topics = set()
    for admin_topics in ADMINS.values():
        topics.update(admin_topics)
    for topic in sorted(topics):  # Сортируем темы для удобства
        keyboard.add(types.KeyboardButton(topic))
    keyboard.add(types.KeyboardButton("Общие вопросы"))  # Явно добавляем общие вопросы
    return keyboard


# Команда старт
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id in ADMINS:
        bot.send_message(user_id, "Вы администратор. Ожидайте обращений.")
        return

    user_states[user_id] = 'choosing_topic'
    bot.send_message(user_id,
                     "Привет.👋Это тех поддержка подслушано😶‍🌫️\nВыбери тему обращения:",
                     reply_markup=get_topics_keyboard())


# Команда close
@bot.message_handler(commands=['close'])
def close_chat(message):
    user_id = message.from_user.id

    # Если команду отправил администратор
    if user_id in ADMINS:
        if user_id in admin_requests:
            client_id = admin_requests[user_id]
            bot.send_message(client_id,
                             "Администратор закрыл обращение. Если у вас есть другие вопросы, нажмите /start")

            # Очищаем данные
            user_states.pop(client_id, None)
            user_requests.pop(client_id, None)
            admin_requests.pop(user_id, None)

            bot.send_message(user_id, f"Вы закрыли обращение пользователя {client_id}")
        else:
            bot.send_message(user_id, "У вас нет активных обращений.")

    # Если команду отправил пользователь
    elif user_id in user_requests:
        admin_id = None
        for aid, uid in admin_requests.items():
            if uid == user_id:
                admin_id = aid
                break

        if admin_id:
            bot.send_message(admin_id, f"Пользователь {user_id} закрыл обращение.")

        # Очищаем данные
        user_states.pop(user_id, None)
        user_requests.pop(user_id, None)
        if admin_id:
            admin_requests.pop(admin_id, None)

        bot.send_message(user_id, "Вы закрыли обращение. Для нового обращения нажмите /start",
                         reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(user_id, "У вас нет активных обращений.")


# Обработка сообщений от пользователей
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id not in ADMINS)
def handle_user_message(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, 'choosing_topic')

    if state == 'choosing_topic':
        if message.text in [topic for topics in ADMINS.values() for topic in topics]:
            user_states[user_id] = 'in_chat'
            topic = message.text
            user_requests[user_id] = {
                'topic': topic,
                'messages': [message.text]
            }

            # Находим подходящего админа
            admin_id = find_admin_for_topic(topic)
            if admin_id:
                admin_requests[admin_id] = user_id
                bot.send_message(admin_id,
                                 f"Новое обращение по теме '{topic}'\nПользователь: {user_id}\nТекст: {message.text}")
                bot.send_message(user_id, "Ваше обращение принято✅. Администратор ответит вам в ближайшее время.",
                                 reply_markup=types.ReplyKeyboardRemove())
            else:
                bot.send_message(user_id, "Сейчас нет свободных администраторов. Попробуйте позже.")
                user_states.pop(user_id, None)
        else:
            bot.send_message(user_id, "Пожалуйста, выберите тему из предложенных.")

    elif state == 'in_chat':
        if user_id in user_requests:
            admin_id = None
            for aid, uid in admin_requests.items():
                if uid == user_id:
                    admin_id = aid
                    break

            if admin_id:
                user_requests[user_id]['messages'].append(message.text)
                bot.send_message(admin_id, f"Пользователь {user_id}: {message.text}")
            else:
                bot.send_message(user_id,
                                 "Администратор пока не назначен. Ожидайте или закройте обращение командой /close")


# Обработка сообщений от администраторов
@bot.message_handler(func=lambda m: m.from_user.id in ADMINS)
def handle_admin_message(message):
    admin_id = message.from_user.id

    if message.reply_to_message and 'Пользователь:' in message.reply_to_message.text:
        try:
            user_id = int(message.reply_to_message.text.split('Пользователь:')[1].split('\n')[0].strip())

            if user_id in user_requests:
                bot.send_message(user_id, f"Администратор: {message.text}")
                user_requests[user_id]['messages'].append(f"Admin: {message.text}")
            else:
                bot.send_message(admin_id, "Обращение уже закрыто.")
        except:
            bot.send_message(admin_id, "Не удалось обработать сообщение.")
    elif message.text == '/active':
        # Команда для проверки активных обращений
        if admin_id in admin_requests:
            user_id = admin_requests[admin_id]
            bot.send_message(admin_id, f"У вас активное обращение от пользователя {user_id}")
        else:
            bot.send_message(admin_id, "У вас нет активных обращений.")
    else:
        bot.send_message(admin_id, "Отвечайте на сообщения пользователей, чтобы направить им ответ.")


# Функция поиска администратора по теме
def find_admin_for_topic(topic):
    # Сначала ищем администратора, который специализируется на этой теме
    for admin_id, topics in ADMINS.items():
        if topic in topics and admin_id not in admin_requests:
            return admin_id

    # Если не нашли, ищем администратора с "Общими вопросами"
    for admin_id, topics in ADMINS.items():
        if 'Общие вопросы' in topics and admin_id not in admin_requests:
            return admin_id

    return None


# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)


# Запуск бота
while True:
    try:
        bot.polling(none_stop=True)
    except:
        continue