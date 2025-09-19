import random
import pandas as pd
import streamlit as st
import time
from datetime import datetime, timedelta, timezone
import io

# ---- TZ (Asia/Tokyo) ----
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    JST = ZoneInfo("Asia/Tokyo")
except Exception:
    JST = timezone(timedelta(hours=9))  # フォールバック
with col2:
    st.markdown("2025-9-31まで利用可能")
# ==== ファイルアップロード ====
uploaded_file = st.file_uploader("単語リスト（CSV, UTF-8推奨）をアップロードしてください", type=["csv"])
    st.markdown("2025-9-31まで利用可能")

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
if "phase" not in ss: ss.phase = "menu"   # menu / quiz / feedback / done / finished
if "start_time" not in ss: ss.start_time = time.time()
if "history" not in ss: ss.history = []   # [{単語, 結果, 出題形式}]
if "show_save_ui" not in ss: ss.show_save_ui = False
if "user_name" not in ss: ss.user_name = ""
if "quiz_type" not in ss: ss.quiz_type = None
if "last_outcome" not in ss: ss.last_outcome = None
if "q_index" not in ss: ss.q_index = 0    # 問題ごとの一意キー
if "question" not in ss: ss.question = None  # {'id', 'answer_type', 'correct', 'options', 'word'}

# ==== ユーティリティ ====
def answer_type_for(quiz_type: str) -> str:
    """出題形式から答えるべき型を決める"""
    if quiz_type == "単語→意味":
        return "meaning"
    # それ以外（①③④）は単語を答える
    return "word"

def make_choices_once(correct_item: dict, df: pd.DataFrame, answer_type="word"):
    """この問題用の選択肢を一度だけ生成（正解を必ず含む4択）"""
    if answer_type == "meaning":
        correct = correct_item["意味"]
        # 同じ単語の意味は除外
        pool = df[df["単語"] != correct_item["単語"]]["意味"].tolist()
    else:
        correct = correct_item["単語"]
        pool = df[df["単語"] != correct_item["単語"]]["単語"].tolist()

    # 誤答を3つ作る（不足時は重複許容）
    wrongs = random.sample(pool, 3) if len(pool) >= 3 else random.choices(pool, k=3)
    choices = wrongs + [correct]
    random.shuffle(choices)
    return correct, choices

def set_question_state():
    """問題開始時に一度だけ選択肢と正解をセッションに固定"""
    if not ss.current:
        return
    ss.q_index += 1
    a_type = answer_type_for(ss.quiz_type)
    correct, options = make_choices_once(ss.current, df, a_type)
    ss.question = {
        "id": ss.q_index,
        "answer_type": a_type,
        "correct": correct,           # 表示上の正解テキスト（単語または意味）
        "options": options,           # この問題中は固定
        "word": ss.current["単語"],   # 単語名（履歴用）
    }

def next_question():
    if not ss.remaining:
        ss.current = None
        ss.phase = "done"
        ss.question = None
        return
    ss.current = random.choice(ss.remaining)
    ss.phase = "quiz"
    ss.last_outcome = None
    set_question_state()  # ← 選択肢を固定

def reset_quiz():
    ss.remaining = df.to_dict("records")
    ss.current = None
    ss.phase = "menu"
    ss.start_time = time.time()
    ss.last_outcome = None
    ss.question = None
    # 履歴は保持（累積）

def prepare_csv():
    # 日本時間のタイムスタンプでファイル名作成
    timestamp = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
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
    if st.button("開始", key="start_btn"):
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
        if st.button("もう一回", key="again_btn"):
            reset_quiz()
            st.rerun()
    with col2:
        if st.button("終了", key="finish_btn"):
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
            mime="text/csv",
            key="download_btn"
        )

# ==== 出題 ====
if ss.phase == "quiz" and ss.current and ss.question:
    current = ss.current
    q = ss.question
    word = current["単語"]

    # 表示部
    if ss.quiz_type == "意味→単語":
        st.subheader(f"意味: {current['意味']}")

    elif ss.quiz_type == "単語→意味":
        st.subheader(f"単語: {word}")

    elif ss.quiz_type == "空所英文＋和訳→単語":
        st.subheader(current["例文"].replace(word, "____"))
        # 和訳は置換しない。スタイルのみ変更（大きめ＆グレー）
        st.markdown(f"<p style='color:gray; font-size:18px; margin-top:-6px;'>{current['和訳']}</p>", unsafe_allow_html=True)

    elif ss.quiz_type == "空所英文→単語":
        st.subheader(current["例文"].replace(word, "____"))

    # 回答（縦ボタン固定：この問題中は選択肢テキストと順序が変わらない）
    st.write("選択肢から答えを選んでください")
    for i, opt in enumerate(q["options"]):
        if st.button(opt, key=f"opt_{q['id']}_{i}"):
            if opt == q["correct"]:
                ss.last_outcome = ("正解", q["correct"])
                # 正解時のみ、その単語を残リストから除外
                ss.remaining = [r for r in ss.remaining if r != current]
            else:
                ss.last_outcome = ("不正解", q["correct"])
            # 履歴（累積）
            ss.history.append({"単語": q["word"], "結果": ss.last_outcome[0], "出題形式": ss.quiz_type})
            ss.phase = "feedback"
            st.rerun()

# ==== フィードバック ====
if ss.phase == "feedback" and ss.last_outcome:
    status, correct_label = ss.last_outcome
    if status == "正解":
        st.success(f"正解！ {correct_label}")
    else:
        st.error(f"不正解… 正解は {correct_label}")
    if st.button("次の問題へ", key="next_btn"):
        ss.question = None  # 次の問題で新しい選択肢を作る
        next_question()
        st.rerun()



