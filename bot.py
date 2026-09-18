import json
import random
import telebot
from telebot import types

TOKEN = "8894500930:AAFwjspDTRM-149x3rHr1ZxLz1uy8u3aI_w"
QUESTIONS_PER_EXAM = 100
MAX_MULTI = 5

with open("questions.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)["questions"]

bot = telebot.TeleBot(TOKEN)
users = {}


def build_exam():
    pool = random.sample(ALL_QUESTIONS, min(QUESTIONS_PER_EXAM, len(ALL_QUESTIONS)))
    exam = []
    for q in pool:
        variants = list(enumerate(q["a"], start=1))
        random.shuffle(variants)
        new_options = [v[1] for v in variants]
        if q["type"] == "single":
            correct_text = q["a"][q["c"] - 1]
            new_c = new_options.index(correct_text) + 1
        else:
            correct_texts = [q["a"][i - 1] for i in q["c"]]
            new_c = [new_options.index(t) + 1 for t in correct_texts]
        exam.append({"id": q["id"], "type": q["type"], "q": q["q"],
                     "a": new_options, "c": new_c,
                     "src": q.get("src", "")})
    return exam


def send_question(chat_id):
    u = users.get(chat_id)
    if not u:
        return
    if u["idx"] >= len(u["exam"]):
        return finish_exam(chat_id)

    q = u["exam"][u["idx"]]
    markup = types.InlineKeyboardMarkup()

    if q["type"] == "single":
        for i, ans in enumerate(q["a"], 1):
            markup.add(types.InlineKeyboardButton(f"{i}. {ans}", callback_data=f"s|{i}"))
        text = f"❓ Вопрос {u['idx']+1}/{len(u['exam'])}\n\n{q['q']}"
    else:
        for i, ans in enumerate(q["a"], 1):
            prefix = "☑️ " if i in u.get("picked", []) else ""
            markup.add(types.InlineKeyboardButton(f"{prefix}{i}. {ans}", callback_data=f"m|{i}"))
        markup.add(types.InlineKeyboardButton("✅ Готово", callback_data="done"))
        text = f"❓ Вопрос {u['idx']+1}/{len(u['exam'])} (несколько)\n\n{q['q']}"

    bot.send_message(chat_id, text, reply_markup=markup)


def finish_exam(chat_id):
    u = users[chat_id]
    total = len(u["exam"])
    score = u["score"]
    percent = round(score / total * 100) if total else 0

    text = f"🏁 Экзамен завершён!\n\n✅ Правильных: {score} из {total}\n📊 Результат: {percent}%\n"
    wrong = [a for a in u["answers"] if not a["ok"]]
    if wrong:
        text += f"\n— РАЗБОР ОШИБОК ({len(wrong)}) —\n"
        for i, w in enumerate(wrong, 1):
            ua = ", ".join(map(str, w["user"]))
            ca = ", ".join(map(str, w["correct"]))
            text += f"\n❌ {i}) {w['q']['q']}\nВаш ответ: {ua}\nПравильно: {ca}\n📖 {w['q']['src']}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Новый экзамен")
    bot.send_message(chat_id, text[:4000], reply_markup=markup)


@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Начать экзамен")
    bot.send_message(message.chat.id,
        "🚂 Экзамен проводника пассажирского вагона\n\n"
        "В базе 360 вопросов.\n"
        "Каждый экзамен — 100 случайных вопросов.",
        reply_markup=markup)


@bot.message_handler(func=lambda m: m.text in ["📝 Начать экзамен", "📝 Новый экзамен"])
def new_exam(message):
    cid = message.chat.id
    users[cid] = {"exam": build_exam(), "idx": 0, "score": 0, "answers": [], "picked": []}
    bot.send_message(cid, "Начинаем! Удачи 🍀")
    send_question(cid)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    cid = call.message.chat.id
    u = users.get(cid)
    if not u:
        return
    q = u["exam"][u["idx"]]
    d = call.data

    if d.startswith("s|"):
        ch = int(d.split("|")[1])
        cor = q["c"]
        ok = ch == cor
        if ok:
            u["score"] += 1
            bot.answer_callback_query(call.id, "✅ Верно!")
        else:
            bot.answer_callback_query(call.id, f"❌ Неверно. Правильный: {cor}")
        u["answers"].append({"q": q, "ok": ok, "user": [ch], "correct": [cor]})
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        u["idx"] += 1
        u["picked"] = []
        send_question(cid)
        return

    if d.startswith("m|"):
        n = int(d.split("|")[1])
        picked = u.setdefault("picked", [])
        if n in picked:
            picked.remove(n)
        elif len(picked) < MAX_MULTI:
            picked.append(n)
        else:
            bot.answer_callback_query(call.id, f"Макс {MAX_MULTI}")
            return
        markup = types.InlineKeyboardMarkup()
        for i, ans in enumerate(q["a"], 1):
            prefix = "☑️ " if i in picked else ""
            markup.add(types.InlineKeyboardButton(f"{prefix}{i}. {ans}", callback_data=f"m|{i}"))
        markup.add(types.InlineKeyboardButton("✅ Готово", callback_data="done"))
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=markup)
        return

    if d == "done":
        picked = sorted(u.get("picked", []))
        if not picked:
            bot.answer_callback_query(call.id, "Выберите вариант")
            return
        cor = sorted(q["c"])
        ok = picked == cor
        if ok:
            u["score"] += 1
            bot.answer_callback_query(call.id, "✅ Верно!")
        else:
            bot.answer_callback_query(call.id, f"❌ Правильные: {', '.join(map(str, cor))}")
        u["answers"].append({"q": q, "ok": ok, "user": picked, "correct": cor})
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        u["idx"] += 1
        u["picked"] = []
        send_question(cid)
        return


print("Бот запущен...")
bot.infinity_polling()
