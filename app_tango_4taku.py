import random
import pandas as pd
import streamlit as st
import time
from datetime import datetime
import io

st.title("英単語４択クイズ（CSV版・スマホ対応）")

# ==== ファイルアップロード ====
uploaded_file = st.file_uploader("単語リスト（CSV, UTF-8推奨）をアップロードしてください", type=["csv"])

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
if "start_time" not in ss: ss.start_time = time.time()
if "history" not in ss: ss.history = []
if "show_save_ui" not in ss: ss.show_save_ui = False
if "user_name" not in ss: ss.user_name = ""
if "quiz_type" not in ss: ss.quiz_type = None
if "last_outcome" not in ss: ss.last_outcome = None

# ==== 選択肢生成 ====
def make_choices(correct_item, df, answer_type="word"):
    if answer_type == "meaning":
        correct = correct_item["意味"]
        pool = df[df["単語"] != correct_item["単語"]]["意味"].tolist()
    else:  # answer_type == "word"
        correct = correct_item["単語"]
        pool = df[df["単語"] != correct_item["単語"]]["単語"].tolist()

    if len(pool) >= 3:
        wrongs = random.sample(pool, 3)
    else:
        wrongs = random.choices(pool, k=3)

    choices = wrongs + [correct]
    random.shuffle(choices)
    return correct, choices

def next_question():
    if not ss.remaining:
        ss.current = None
        ss.phase = "done"
        return
    ss.current = random.choice(ss.remaining)
    ss.phase = "quiz"
    ss.last_outcome = None

def reset_quiz():
    ss.remaining = df.to_dict("records")
    ss.current = None
    ss.phase = "menu"
    ss.start_time = time.time()

def prepare_csv():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ss.user_name}_{timestamp}.csv"
    elapsed = int(time.time() - ss.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    history_df = pd.DataFrame(ss.history)
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
    minutes = elapsed // 60
    seconds = elapsed % 60
    st.info(f"所要時間: {minutes}分 {seconds}秒")
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
        st.download_button(
            label="📥 保存（ダウンロード）",
            data=csv_data,
            file_name=filename,
            mime="text/csv"
        )

# ==== 出題 ====
if ss.phase == "quiz" and ss.current:
    current = ss.current
    word = current["単語"]

    if ss.quiz_type == "意味→単語":
        st.subheader(f"意味: {current['意味']}")
        correct, options = make_choices(current, df, answer_type="word")

    elif ss.quiz_type == "単語→意味":
        st.subheader(f"単語: {word}")
        correct, options = make_choices(current, df, answer_type="meaning")

    elif ss.quiz_type == "空所英文＋和訳→単語":
        st.subheader(current["例文"].replace(word, "____"))
        st.markdown(f"<p style='color:gray; font-size:18px;'>{current['和訳']}</p>", unsafe_allow_html=True)
        correct, options = make_choices(current, df, answer_type="word")

    elif ss.quiz_type == "空所英文→単語":
        st.subheader(current["例文"].replace(word, "____"))
        correct, options = make_choices(current, df, answer_type="word")

    # ==== 回答 ====
    st.write("選択肢から答えを選んでください")
    for opt in options:
        if st.button(opt, key=f"opt_{len(ss.history)}_{opt}"):
            if opt == correct:
                ss.last_outcome = ("正解", word)
                ss.remaining = [q for q in ss.remaining if q != current]
            else:
                ss.last_outcome = ("不正解", word)
            ss.history.append({"単語": word, "結果": ss.last_outcome[0], "出題形式": ss.quiz_type})
            ss.phase = "feedback"
            st.rerun()

# ==== フィードバック ====
if ss.phase == "feedback" and ss.last_outcome:
    status, word = ss.last_outcome
    if status == "正解":
        st.success(f"正解！ {word}")
    else:
        st.error(f"不正解… 正解は {word}")
    if st.button("次の問題へ"):
        next_question()
        st.rerun()
