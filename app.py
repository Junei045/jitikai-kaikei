import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
# 予算データなどはそのまま維持
BUDGET_INCOME = {
    "会費": 500000, "寄付金": 50000, "補助金": 100000, "前年度繰越金": 200000, "その他収入": 10000
}
BUDGET_EXPENSE = {
    "事務費": 50000, "事業費": 200000, "防災費": 100000, "祭礼費": 300000, "慶弔費": 30000, "予備費": 20000
}

INCOME_ITEMS = list(BUDGET_INCOME.keys())
EXPENSE_ITEMS = list(BUDGET_EXPENSE.keys())

st.set_page_config(page_title="自治会会計システム", layout="centered")
st.markdown("<div id='linkto_top'></div>", unsafe_allow_html=True)
st.title("自治会 会計管理 (クラウド版)")

# --- 2. Googleスプレッドシートへの接続設定 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み
df = conn.read(ttl=0) # ttl=0で常に最新を読み込む
if df.empty:
    df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考"])

if "tmp_amount" not in st.session_state:
    st.session_state.tmp_amount = 0

# --- 3. タブの作成 (中身のロジックは以前と同じですが、保存先をconn.updateにします) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 入力", "📊 予算・残高", "📅 月次集計", "📄 決算報告書", "🗑 削除"])

with tab1:
    st.subheader("入出金の記録")
    col_type, col_method = st.columns(2)
    with col_type: category_type = st.radio("区分", ["支出", "収入"], horizontal=True)
    with col_method: pay_method = st.radio("取扱方法", ["現金", "銀行"], horizontal=True)
    items = EXPENSE_ITEMS if category_type == "支出" else INCOME_ITEMS
    item = st.selectbox("項目（科目）を選択", items)

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
        submitted = st.form_submit_button("💾 保存する", use_container_width=True)
        
        if submitted:
            if amount == 0:
                st.error("金額を入力してください。")
            else:
                new_row = pd.DataFrame([[str(date), category_type, pay_method, item, amount, memo]], 
                                       columns=["日付", "区分", "方法", "科目", "金額", "備考"])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                # スプレッドシートを更新
                conn.update(data=updated_df)
                st.session_state.tmp_amount = 0
                st.success("スプレッドシートに保存しました！")
                st.rerun()
    st.markdown("<br><a href='#linkto_top' style='display: block; text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-decoration: none; color: #31333F;'>⬆️ ページトップへ戻る</a>", unsafe_allow_html=True)

# --- 他のタブ (tab2-tab5) の集計ロジックは、読み込んだdfを使って以前と同様に記述 ---
# ※ スペースの都合上、集計ロジックは前の回答と同じものが入るとお考えください。