import random
import pandas as pd
import streamlit as st
import time
from datetime import datetime, timedelta, timezone
import io

# ==== 日本時間のタイムゾーン ====
try:
    from zoneinfo import ZoneInfo
    JST = ZoneInfo("Asia/Tokyo")
except Exception:
    JST = timezone(timedelta(hours=9))

# ==== スタイル調整（スマホ対応） ====
st.markdown("""
<style>
h1, h2, h3, h4, h5, h6 {margin-top: 0.2em; margin-bottom: 0.2em;}
p, div, label {margin-top: 0.05em; margin-bottom: 0.05em; line-height: 1.1;}
button, .stButton>button {
    padding: 0.4em;
    margin: 0.05em 0;
    font-size:20px;
    width:100%;
}
.stTextInput>div>div>input {padding: 0.2em; font-size: 16px;}
</style>
""", unsafe_allow_html=True)

# ==== タイトル ====
st.markdown("<h1 style='font-size:22px;'>英単語４択クイズ（CSV版・スマホ対応）</h1>", unsafe_allow_html=True)

# ==== ファイルアップロード ====
uploaded_file = st.file_uploader("単語リスト（CSV, UTF-8推奨）をアップロードしてください  （利用期限25-9-30）", type=["csv"])

if uploaded_file is None:
    st.info("まずは CSV をアップロードしてください。")
    st.stop()

# ==== CSV読み込み ====
try:
    df = pd.read_csv(uploaded_file, encoding="utf-8")
except UnicodeDecodeError:
    df = pd.read_csv(uploaded_file, encoding="shift-jis")

required_cols = {"単語", "意味", "例文", "和訳"}
if not required_cols.issubset(df.columns):
    st.error("CSVには『単語』『意味』『例文』『和訳』列が必要です。")
    st.stop()

# ==== セッション初期化 ====
ss = st.session_state
if "remaining" not in ss: ss.remaining = df.to_dict("records")
if "current" not in ss: ss.current = None
if "phase" not in ss: ss.phase = "menu"
if "last_outcome" not in ss: ss.last_outcome = None
if "start_time" not in ss: ss.start_time = time.time()
if "history" not in ss: ss.history = []
if "show_save_ui" not in ss: ss.show_save_ui = False
if "user_name" not in ss: ss.user_name = ""
if "quiz_type" not in ss: ss.quiz_type = None
if "question" not in ss: ss.question = None  # 選択肢を固定するため

# ==== 選択肢生成 ====
def make_choices(correct_item, df, mode="word2meaning"):
    if mode == "word2meaning":
        correct = correct_item["意味"]
        pool = df[df["単語"] != correct_item["単語"]]["意味"].tolist()
    else:
        correct = correct_item["単語"]
        pool = df[df["意味"] != correct_item["意味"]]["単語"].tolist()
    wrongs = random.sample(pool, 3) if len(pool) >= 3 else random.choices(pool, k=3)
    # 正解は常に一番下
    choices = wrongs + [correct]
    return correct, choices

def next_question():
    if not ss.remaining:
        ss.current = None
        ss.phase = "done"
        return
    ss.current = random.choice(ss.remaining)
    ss.phase = "quiz"
    ss.last_outcome = None
    ss.question = None  # 新しい問題ではリセット

def reset_quiz():
    ss.remaining = df.to_dict("records")
    ss.current = None
    ss.phase = "menu"
    ss.last_outcome = None
    ss.start_time = time.time()
    ss.history = []
    ss.question = None

def prepare_csv():
    timestamp = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    filename = f"{ss.user_name}_{timestamp}.csv"
    elapsed = int(time.time() - ss.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    history_df = pd.DataFrame(ss.history, columns=["学習単語"])
    history_df["学習時間"] = f"{minutes}分{seconds}秒"
    csv_buffer = io.StringIO()
    history_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    csv_data = csv_buffer.getvalue().encode("utf-8-sig")
    return filename, csv_data

# ==== メニュー ====
if ss.phase == "menu":
    quiz_type = st.radio(
        "出題形式を選んでください",
        ["意味→単語", "単語→意味", "空所英文＋和訳→単語", "空所英文→単語"]
    )
    if st.button("開始"):
        ss.quiz_type = quiz_type
        next_question()
        st.rerun()

# ==== 全問終了 ====
if ss.phase == "done":
    st.success("全問終了！お疲れさまでした🎉")
    elapsed = int(time.time() - ss.start_time)
    st.info(f"所要時間: {elapsed//60}分 {elapsed%60}秒")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("もう一回"):
            reset_quiz()
            st.rerun()
    with col2:
        if st.button("終了"):
            ss.show_save_ui = True
            ss.phase = "finished"
            st.rerun()
    st.stop()

# ==== 終了後の保存UI ====
if ss.phase == "finished" and ss.show_save_ui:
    st.subheader("学習履歴の保存")
    ss.user_name = st.text_input("氏名を入力してください", value=ss.user_name)
    if ss.user_name:
        filename, csv_data = prepare_csv()
        st.download_button("📥 保存（ダウンロード）", csv_data, filename, "text/csv")

# ==== 出題 ====
if ss.phase == "quiz" and ss.current:
    current = ss.current
    word = current["単語"]

    # 問題文の表示
    if ss.quiz_type == "意味→単語":
        st.subheader(f"意味: {current['意味']}")
        if ss.question is None:
            correct, options = make_choices(current, df, mode="meaning2word")
            ss.question = {"correct": correct, "options": options, "word": word}

    elif ss.quiz_type == "単語→意味":
        st.subheader(f"単語: {word}")
        if ss.question is None:
            correct, options = make_choices(current, df, mode="word2meaning")
            ss.question = {"correct": correct, "options": options, "word": word}

    elif ss.quiz_type == "空所英文＋和訳→単語":
        st.subheader(current["例文"].replace(word, "____"))
        st.markdown(f"<p style='color:gray; font-size:16px;'>{current['和訳']}</p>", unsafe_allow_html=True)
        if ss.question is None:
            correct, options = make_choices(current, df, mode="meaning2word")
            ss.question = {"correct": correct, "options": options, "word": word}

    elif ss.quiz_type == "空所英文→単語":
        st.subheader(current["例文"].replace(word, "____"))
        if ss.question is None:
            correct, options = make_choices(current, df, mode="meaning2word")
            ss.question = {"correct": correct, "options": options, "word": word}

    # 選択肢表示
    st.write("選択肢から答えを選んでください")
    for opt in ss.question["options"]:
        if st.button(opt, key=f"opt_{len(ss.history)}_{opt}"):
            if opt == ss.question["correct"]:
                ss.last_outcome = ("正解", ss.question["correct"])
                ss.remaining = [q for q in ss.remaining if q != current]
            else:
                ss.last_outcome = ("不正解", ss.question["correct"])
            ss.history.append(word)
            ss.phase = "feedback"
            st.rerun()

# ==== フィードバック ====
if ss.phase == "feedback" and ss.last_outcome:
    status, correct_word = ss.last_outcome
    if status == "正解":
        st.success(f"正解！ {correct_word}")
    else:
        st.error(f"不正解… 正解は {correct_word}")
    time.sleep(2)  # 2秒表示
    next_question()
    st.rerun()
