import json
import random
import telebot
from telebot import types

TOKEN = "8894500930:AAGrYc-NXKLK_J18hM4JeVUKkTgQ9HlGXZw"
QUESTIONS_PER_EXAM = 50
MAX_MULTI = 5

# Загружаем обе базы
with open("questions.json", "r", encoding="utf-8") as f:
    MAIN_QUESTIONS = json.load(f)["questions"]

try:
    with open("questions_983.json", "r", encoding="utf-8") as f:
        REG983_QUESTIONS = json.load(f)["questions"]
except FileNotFoundError:
    REG983_QUESTIONS = []

bot = telebot.TeleBot(TOKEN)
users = {}


def build_exam(pool_all):
    pool = random.sample(pool_all, min(QUESTIONS_PER_EXAM, len(pool_all)))
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
        exam.append({
            "id": q.get("id", 0),
            "type": q.get("type", "single"),
            "q": q.get("q", ""),
            "a": new_options,
            "c": new_c,
            "src": q.get("src", ""),
            "expl": q.get("expl", ""),
            "img": q.get("img", "")
        })
    return exam


def send_question(chat_id):
    u = users.get(chat_id)
    if not u:
        return
    if u["idx"] >= len(u["exam"]):
        return finish_exam(chat_id)

    q = u["exam"][u["idx"]]
    markup = types.InlineKeyboardMarkup()
    options_text = "\n".join(f"{i}. {ans}" for i, ans in enumerate(q["a"], 1))

    if q["type"] == "single":
        buttons = [
            types.InlineKeyboardButton(str(i), callback_data=f"s|{i}")
            for i in range(1, len(q["a"]) + 1)] ,
        markup.row(*buttons)
        header = f"❓ Вопрос {u['idx']+1}/{len(u['exam'])}\n\n{q['q']}\n\n{options_text}"
    else:
        for i in range(1, len(q["a"]) + 1):
            prefix = "☑️" if i in u.get("picked", []) else "⬜"
            markup.add(types.InlineKeyboardButton(f"{prefix} {i}", callback_data=f"m|{i}"))
        markup.add(types.InlineKeyboardButton("✅ Готово", callback_data="done"))
        header = f"❓ Вопрос {u['idx']+1}/{len(u['exam'])} (несколько)\n\n{q['q']}\n\n{options_text}"

    # Если есть картинка — отправляем фото с подписью
    if q.get("img"):
        try:
            bot.send_photo(chat_id, q["img"], caption=header[:1000], reply_markup=markup)
            return
        except Exception:
            pass  # если картинка не загрузилась — отправляем текст
    bot.send_message(chat_id, header, reply_markup=markup)


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
            q = w["q"]
            text += f"\n❌ Вопрос {i}\n"
            text += f"📋 {q['q']}\n"
            text += "── Варианты ──\n"
            for num, ans in enumerate(q["a"], 1):
                text += f"{num}. {ans}\n"
            user_nums = ", ".join(map(str, w["user"]))
            user_texts = "; ".join(q["a"][n - 1] for n in w["user"])
            text += f"\n🟥 Ваш ответ: {user_nums}\n{user_texts}\n\n"
            cor_nums = ", ".join(map(str, w["correct"]))
            cor_texts = "; ".join(q["a"][n - 1] for n in w["correct"])
            text += f"🟩 Правильно: {cor_nums}\n{cor_texts}\n"
            text += f"📖 Источник: {q.get('src', '')}\n"
            if q.get("expl"):
                text += f"\n📚 Пояснение: {q['expl']}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Основной экзамен")
    if REG983_QUESTIONS:
        markup.add("📕 Регламент 983НЗ")
    bot.send_message(chat_id, text[:4000], reply_markup=markup)


@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Основной экзамен")
    if REG983_QUESTIONS:
        markup.add("📕 Регламент 983НЗ")
    bot.send_message(
        message.chat.id,
        "🚂 Экзамен проводника пассажирского вагона\n\n"
        "Доступны два экзамена:\n"
        "📝 Основной — 1060 вопросов\n"
        "📕 Регламент 983НЗ — регламент нестандартных ситуаций",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text == "📝 Основной экзамен")
def exam_main(message):
    cid = message.chat.id
    users[cid] = {"exam": build_exam(MAIN_QUESTIONS), "idx": 0, "score": 0, "answers": [], "picked": []}
    bot.send_message(cid, "Начинаем основной экзамен! Удачи 🍀")
    send_question(cid)


@bot.message_handler(func=lambda m: m.text == "📕 Регламент 983НЗ")
def exam_983(message):
    if not REG983_QUESTIONS:
        bot.send_message(message.chat.id, "⚠️ База 983НЗ ещё не загружена.")
        return
    cid = message.chat.id
    users[cid] = {"exam": build_exam(REG983_QUESTIONS), "idx": 0, "score": 0, "answers": [], "picked": []}
    bot.send_message(cid, "Начинаем экзамен по Регламенту 983НЗ! Удачи 🍀")
    send_question(cid)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    try:
        cid = call.message.chat.id
        u = users.get(cid)
        if not u:
            bot.answer_callback_query(call.id, "Начните экзамен заново")
            return
        q = u["exam"][u["idx"]]
        d = call.data

        if d.startswith("s|"):
            ch = int(d.split("|")[1])
            cor = q["c"]
            ok = ch == cor
            # Всплывающее окно с пояснением
            if ok:
                text = "✅ Верно!"
            else:
                text = f"❌ Неверно. Правильный: {cor}"
            if q.get("expl"):
                text += f"\n\n📚 {q['expl'][:200]}"
            bot.answer_callback_query(call.id, text[:200])
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
            for i in range(1, len(q["a"]) + 1):
                prefix = "☑️" if i in picked else "⬜"
                markup.add(types.InlineKeyboardButton(f"{prefix} {i}", callback_data=f"m|{i}"))
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
                text = "✅ Верно!"
            else:
                text = f"❌ Правильные: {', '.join(map(str, cor))}"
            if q.get("expl"):
                text += f"\n\n📚 {q['expl'][:200]}"
            bot.answer_callback_query(call.id, text[:200])
            u["answers"].append({"q": q, "ok": ok, "user": picked, "correct": cor})
            bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
            u["idx"] += 1
            u["picked"] = []
            send_question(cid)
            return
    except Exception as e:
        print(f"ОШИБКА: {e}")


print("Бот запущен...")
bot.infinity_polling()
