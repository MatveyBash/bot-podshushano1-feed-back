import telebot
from telebot import types

# Настройки бота
TOKEN = '7800950778:AAHGhD9DlZYV0iaxZRVZSMR1Ultw81qtz38'
bot = telebot.TeleBot(TOKEN)

# Администраторы и их темы (ID: [темы])
ADMINS = {
    1616523146: ['Разработчик/Владелец⚠️'],
    5683628958: ['Глав. Админ⛔'],
    6172742677: ['Менеджер🧐']  # Новый администратор для общих вопросов
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

            bot.send_message(user_id, f"Вы закрыли обращение пользователя ID: {client_id}")
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
            bot.send_message(admin_id, f"Пользователь ID: {user_id} закрыл обращение.")

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
                                 f"📨 НОВОЕ ОБРАЩЕНИЕ\n\n"
                                 f"👤 Пользователь ID: {user_id}\n"
                                 f"🏷 Тема: '{topic}'\n"
                                 f"💬 Сообщение: {message.text}\n\n"
                                 f"Для ответа просто напишите сообщение в этот чат.")
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
                # Отправляем сообщение администратору с ID пользователя
                if message.content_type == 'text':
                    bot.send_message(admin_id, f"👤 Пользователь ID: {user_id}\n💬 {message.text}")
                elif message.content_type == 'photo':
                    bot.send_photo(admin_id, message.photo[-1].file_id,
                                   caption=f"👤 Пользователь ID: {user_id}\n💬 {message.caption if message.caption else ''}")
                elif message.content_type == 'video':
                    bot.send_video(admin_id, message.video.file_id,
                                   caption=f"👤 Пользователь ID: {user_id}\n💬 {message.caption if message.caption else ''}")
                elif message.content_type == 'document':
                    bot.send_document(admin_id, message.document.file_id,
                                      caption=f"👤 Пользователь ID: {user_id}\n💬 {message.caption if message.caption else ''}")
            else:
                bot.send_message(user_id,
                                 "Администратор пока не назначен. Ожидайте или закройте обращение командой /close")


# Обработка сообщений от администраторов
@bot.message_handler(func=lambda m: m.from_user.id in ADMINS)
def handle_admin_message(message):
    admin_id = message.from_user.id

    # Если администратор отвечает на сообщение пользователя
    if message.reply_to_message and 'Пользователь ID:' in message.reply_to_message.text:
        try:
            # Извлекаем ID пользователя из текста сообщения
            text_lines = message.reply_to_message.text.split('\n')
            user_id = None
            for line in text_lines:
                if 'Пользователь ID:' in line:
                    user_id = int(line.split('Пользователь ID:')[1].strip())
                    break

            if user_id and user_id in user_requests:
                # Отправляем сообщение пользователю
                if message.content_type == 'text':
                    bot.send_message(user_id, f"👨‍💼 Администратор:\n{message.text}")
                elif message.content_type == 'photo':
                    bot.send_photo(user_id, message.photo[-1].file_id,
                                   caption=f"👨‍💼 Администратор:\n{message.caption if message.caption else ''}")
                elif message.content_type == 'video':
                    bot.send_video(user_id, message.video.file_id,
                                   caption=f"👨‍💼 Администратор:\n{message.caption if message.caption else ''}")
                elif message.content_type == 'document':
                    bot.send_document(user_id, message.document.file_id,
                                      caption=f"👨‍💼 Администратор:\n{message.caption if message.caption else ''}")

                # Сохраняем сообщение в историю
                user_requests[user_id]['messages'].append(f"Admin: {message.text}")
            else:
                bot.send_message(admin_id, "❌ Обращение уже закрыто или пользователь не найден.")
        except Exception as e:
            bot.send_message(admin_id, f"❌ Не удалось обработать сообщение: {str(e)}")

    # Команда для проверки активных обращений
    elif message.text == '/active':
        if admin_id in admin_requests:
            user_id = admin_requests[admin_id]
            bot.send_message(admin_id, f"✅ У вас активное обращение от пользователя ID: {user_id}")
        else:
            bot.send_message(admin_id, "ℹ️ У вас нет активных обращений.")

    # Если администратор просто пишет сообщение (не ответ)
    elif admin_id in admin_requests:
        user_id = admin_requests[admin_id]
        if user_id in user_requests:
            # Отправляем сообщение пользователю
            if message.content_type == 'text':
                bot.send_message(user_id, f"👨‍💼 Администратор:\n{message.text}")
            elif message.content_type == 'photo':
                bot.send_photo(user_id, message.photo[-1].file_id,
                               caption=f"👨‍💼 Администратор:\n{message.caption if message.caption else ''}")
            elif message.content_type == 'video':
                bot.send_video(user_id, message.video.file_id,
                               caption=f"👨‍💼 Администратор:\n{message.caption if message.caption else ''}")
            elif message.content_type == 'document':
                bot.send_document(user_id, message.document.file_id,
                                  caption=f"👨‍💼 Администратор:\n{message.caption if message.caption else ''}")

            # Сохраняем сообщение в историю
            user_requests[user_id]['messages'].append(f"Admin: {message.text}")
        else:
            bot.send_message(admin_id, "❌ Обращение уже закрыто.")
    else:
        bot.send_message(admin_id, "ℹ️ У вас нет активных обращений. Ожидайте новых обращений.")


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
    print("Администраторы будут видеть ID пользователей в сообщениях")
    bot.polling(none_stop=True)

