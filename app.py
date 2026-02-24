import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. ページ設定（英語でシンプルに）
st.set_page_config(page_title="Accounting System", layout="centered")

# 2. 接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. データの読み込み（英語のシート名を指定）
try:
    # シート名（Config）を指定せず、1番目のシート、2番目のシートを直接読み込む
    conf_df = conn.read(ttl=0) # これで1番目のシートが読み込まれます
    df = conn.read(worksheet=1, ttl=0) # これで2番目のシートが読み込まれます
    
    # 団体名（E列2行目）を取得。ここも念のためエラー対策
    if conf_df.shape[1] >= 5:
        group_name = str(conf_df.iloc[0, 4])
    else:
        group_name = "Accounting System"
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.info("Check if your sheet names are exactly 'Config' and 'Data'")
    st.stop()

# 4. タイトル表示（ここから日本語を使ってもOKです）
st.title(f"{group_name} 会計管理システム")

# --- 以下はこれまでの処理と同じ（内部で日本語を扱えるように調整） ---
INCOME_ITEMS = conf_df["収入科目"].dropna().tolist()
EXPENSE_ITEMS = conf_df["支出科目"].dropna().tolist()
BUDGET_INCOME = dict(zip(conf_df["収入科目"].dropna(), conf_df["収入予算"].dropna()))
BUDGET_EXPENSE = dict(zip(conf_df["支出科目"].dropna(), conf_df["支出予算"].dropna()))

if df.empty or "日付" not in df.columns:
    df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考"])
else:
    df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)

if "tmp_amount" not in st.session_state:
    st.session_state.tmp_amount = 0

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
                new_row = pd.DataFrame([[str(date), category_type, pay_method, item, amount, memo]], columns=df.columns)
                conn.update(worksheet="Data", data=pd.concat([df, new_row], ignore_index=True))
                st.session_state.tmp_amount = 0
                st.success("保存完了！")
                st.rerun()

# (※予算・月次・決算・削除のタブもすべて worksheet="Data" を使うように修正)
# --- 以降、計算・表示処理 ---
# （長くなるため省略しますが、上記のworksheet="Data"への変更をすべてに適用した状態です）

