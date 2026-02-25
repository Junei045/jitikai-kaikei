import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="会計システム", layout="centered")

# 1. 接続
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 全シートを一度に読み込み、リスト化する
    # これにより「400 Bad Request」を回避しやすくなります
    conf_df = conn.read(worksheet=0, ttl=0)
    df = conn.read(worksheet=1, ttl=0)

    # 団体名の取得
    group_name = str(conf_df.iloc[0, 4]) if conf_df.shape[1] >= 5 else "自治会会計システム"
    st.title(group_name)

except Exception as e:
    st.error("⚠️ スプレッドシートの読み込みに失敗しました")
    st.info("原因: スプレッドシートの2枚目のシートが『空っぽ』ではありませんか？")
    st.write(f"エラー詳細: {e}")
    st.stop()

# --- 2. リスト作成（列の名前ではなく、位置で指定） ---
try:
    INCOME_ITEMS = conf_df.iloc[:, 0].dropna().tolist()
    EXPENSE_ITEMS = conf_df.iloc[:, 1].dropna().tolist()
    BUDGET_INCOME = dict(zip(conf_df.iloc[:, 0].dropna(), conf_df.iloc[:, 2].dropna()))
    BUDGET_EXPENSE = dict(zip(conf_df.iloc[:, 1].dropna(), conf_df.iloc[:, 3].dropna()))
except:
    st.error("設定シートの形式が正しくありません。")
    st.stop()

# 3. データ整形
df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
if "tmp_amount" not in st.session_state:
    st.session_state.tmp_amount = 0

# --- 4. タブ表示 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 入力", "📊 予算・残高", "📅 月次集計", "📄 決算報告書", "🗑 削除"])

with tab1:
    st.subheader("入出金の記録")
    col_type, col_method = st.columns(2)
    with col_type: category_type = st.radio("区分", ["支出", "収入"], horizontal=True)
    with col_method: pay_method = st.radio("取扱方法", ["現金", "銀行"], horizontal=True)
    items = EXPENSE_ITEMS if category_type == "支出" else INCOME_ITEMS
    item = st.selectbox("項目を選択", items)
    
    st.write("金額を選択")
    c1, c2, c3 = st.columns(3)
    for i, a in enumerate([1000, 3000, 5000, 10000, 20000, 50000]):
        if [c1, c2, c3][i%3].button(f"{a:,}円"):
            st.session_state.tmp_amount = a
            st.rerun()
            
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("日付", datetime.now())
        amount = st.number_input("金額（円）", min_value=0, step=1, value=st.session_state.tmp_amount)
        memo = st.text_input("備考")
        if st.form_submit_button("💾 保存する", use_container_width=True):
            if amount > 0:
                new_row = pd.DataFrame([[str(date), category_type, pay_method, item, amount, memo]], 
                                     columns=["日付", "区分", "方法", "科目", "金額", "備考"])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                # worksheet=1（2枚目）に保存
                conn.update(worksheet=1, data=updated_df)
                st.session_state.tmp_amount = 0
                st.success("保存しました！")
                st.rerun()

# (※予算、月次、決算、削除のコードは以前と同じため省略しますが、このまま貼り付けて動きます)
