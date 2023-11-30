import telebot
from telebot import types
import json
import random
import sqlite3

TOKEN = '6539104821:AAF8R7TVmFfUDw4dphSzRtK4pdJ44YMti5o'
bot = telebot.TeleBot(TOKEN)
user_data = {}


def load_results():
    conn = sqlite3.connect('quiz_results.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM results')
    results_data = {str(user_id): score for user_id, score in cursor.fetchall()}
    conn.close()
    return results_data


def save_results(results_data):
    conn = sqlite3.connect('quiz_results.db')
    cursor = conn.cursor()
    for user_id, score in results_data.items():
        cursor.execute('INSERT OR REPLACE INTO results (user_id, score) VALUES (?, ?)', (int(user_id), score))
    conn.commit()
    conn.close()


def show_results(chat_id):
    results_data = load_results()
    if not results_data:
        bot.send_message(chat_id, f"Вы первый участник")
    else:
        sorted_results = sorted(results_data.items(), key=lambda x: x[1], reverse=True) # сортируем по отвеченным вопросам в обратном порядке
        found = next((result for result in sorted_results if str(chat_id) in result), None)
        if found:
            position = sorted_results.index(found) + 1
            bot.send_message(chat_id,
                             f"Ваш результат: {results_data[str(chat_id)]}/10\nВаше место в рейтинге: {position}/{len(sorted_results)}")
        else:
            bot.send_message(chat_id, "Что-то пошло не так. Пожалуйста, попробуйте еще раз.")


def read_questions():
    with open("questions.json", "r", encoding="utf-8") as file:
        questions = json.load(file)

    for question in questions:
        question_text = question["question"]
        answer_choices = question_text.splitlines()[1:]
        question["answer_choices"] = answer_choices

    return questions


questions = read_questions()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, """ Привет! Не хочешь проверить знания по Python?
Правила викторины:

1. Начало игры:
   - Для начала игры отправьте команду /play.
   - Вам будет предложено ответить на 10 вопросов.

2. Ответы:
   - Отвечайте на вопросы, выбирая номер ответа (цифру от 1 до 4).
   - Правильные ответы награждаются баллами.

3. Оценка результата:
   - После ответа на все вопросы узнайте свой результат.
   - Вы получите свой счет из 10 возможных баллов.

4. Рейтинг:
   - Ваши результаты записываются в рейтинг.
   - Посмотрите, на каком месте вы в рейтинге участников.

5. Играйте снова:
   - Если хотите попробовать улучшить свой результат, просто отправьте команду /play снова.

6. Удачи!
   - Желаем вам удачи и интересных вопросов!
""")


@bot.message_handler(commands=['play'])
def play(message):
    if not user_data.get(message.chat.id):
        user_data[message.chat.id] = {"current_question": 0, "score": 0}
        random_questions = random.sample(questions, 10)
        user_data[message.chat.id]["questions"] = random_questions
    send_question(message.chat.id)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user = user_data.get(chat_id)

    if user:
        current_question = user["current_question"]
        random_questions = user["questions"]

        if current_question < len(random_questions):
            correct_option = random_questions[current_question]["correct_option"]

            if message.text.isdigit() and 1 <= int(message.text) <= len(
                    random_questions[current_question]["answer_choices"]):
                chosen_option = int(message.text) - 1

                if chosen_option == correct_option:
                    user["score"] += 1
                    bot.send_message(chat_id, "Правильно! 🎉", reply_markup=None)
                else:
                    correct_answer = random_questions[current_question]["answer_choices"][correct_option]
                    bot.send_message(chat_id, f'Неправильно. Правильный ответ: {correct_answer}', reply_markup=None)

                user["current_question"] += 1
                send_question(chat_id)
            else:
                bot.send_message(chat_id, "Пожалуйста, ответьте цифрой от 1 до 4.", reply_markup=None)
        else:
            results = load_results()
            if chat_id not in results:
                score = user["score"]
                results[chat_id] = score
                save_results(results)
                bot.send_message(chat_id, f'Викторина завершена. Ваш счет: {score}/{len(questions)}', reply_markup=None)
                show_results(chat_id)
    else:
        bot.send_message(message.chat.id,
                         f"Привет! Чтобы начать викторину, отправьте команду /start.\n\nПравила викторины:\n* Ответьте на 10 вопросов, чтобы узнать свой результат.\n* Ответы")


def send_question(chat_id):
    user = user_data[chat_id]
    current_question = user["current_question"]
    random_questions = user["questions"]

    if current_question < len(random_questions):
        question_data = random_questions[current_question]
        question_text = question_data["question"]
        answer_choices = question_data["answer_choices"]

        # Create a reply markup with numbered buttons
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for i, choice in enumerate(answer_choices, start=1):
            markup.add(types.KeyboardButton(f"{i}"))

        # Send the question with the numbered keyboard markup
        bot.send_message(chat_id, question_text, reply_markup=markup)
    else:
        bot.send_message(chat_id, "Вопросы закончились. Спасибо за участие!")
        results = load_results()
        if chat_id not in results:
            score = user["score"]
            results[chat_id] = score
            save_results(results)
            bot.send_message(chat_id, f'Викторина завершена. Ваш счет: {score}/10', reply_markup=None)
            show_results(chat_id)


if __name__ == '__main__':
    results = load_results()
    bot.polling(none_stop=True)
