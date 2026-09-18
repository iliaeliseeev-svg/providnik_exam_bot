import telebot
from telebot import types

TOKEN = "8894500930:AAE4Ctoq4gnJZokghCLamALxCFblxiUF6P8"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать экзамен")
    bot.send_message(message.chat.id, "Привет! Нажми кнопку ниже.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Начать экзамен")
def exam(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ответ 1", callback_data="1"))
    markup.add(types.InlineKeyboardButton("Ответ 2", callback_data="2"))
    bot.send_message(message.chat.id, "Тестовый вопрос: 2 + 2 = ?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    if call.data == "1":
        bot.answer_callback_query(call.id, "❌ Неверно")
    else:
        bot.answer_callback_query(call.id, "✅ Верно!")

print("Бот запущен...")
bot.infinity_polling()
