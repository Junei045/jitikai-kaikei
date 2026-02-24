import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定・接続 ---
st.set_page_config(page_title="団体会計システム", layout="centered")
st.markdown("<div id='linkto_top'></div>", unsafe_allow_html=True)
st.title("団体 会計管理システム")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 設定データと実績データの読み込み ---
try:
    # 設定シートから科目と予算を読み込む
    conf_df = conn.read(worksheet="設定", ttl=0)
    # 実績（出納帳）を読み込む
    df = conn.read(worksheet="シート1", ttl=0)
except Exception as e:
    st.error("スプレッドシートの読み込みに失敗しました。シート名が「設定」と「シート1」になっているか確認してください。")
    st.stop()

# 科目リストと予算辞書の作成
INCOME_ITEMS = conf_df["収入科目"].dropna().tolist()
EXPENSE_ITEMS = conf_df["支出科目"].dropna().tolist()

# 予算辞書の作成（科目名をキー、金額を値に）
BUDGET_INCOME = dict(zip(conf_df["収入科目"].dropna(), conf_df["収入予算"].dropna()))
BUDGET_EXPENSE = dict(zip(conf_df["支出科目"].dropna(), conf_df["支出予算"].dropna()))

if df.empty or "日付" not in df.columns:
    df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考"])

if "tmp_amount" not in st.session_state:
    st.session_state.tmp_amount = 0

# --- 3. タブの作成 ---
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
                conn.update(worksheet="シート1", data=updated_df)
                st.session_state.tmp_amount = 0
                st.success("保存しました！")
                st.rerun()
    st.markdown("<br><a href='#linkto_top' style='display: block; text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-decoration: none; color: #31333F;'>⬆️ ページトップへ戻る</a>", unsafe_allow_html=True)

with tab2:
    st.subheader("現在の資産状況")
    if not df.empty:
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        c_in = df[(df["区分"] == "収入") & (df["方法"] == "現金")]["金額"].sum()
        c_out = df[(df["区分"] == "支出") & (df["方法"] == "現金")]["金額"].sum()
        b_in = df[(df["区分"] == "収入") & (df["方法"] == "銀行")]["金額"].sum()
        b_out = df[(df["区分"] == "支出") & (df["方法"] == "銀行")]["金額"].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("現金残高", f"{c_in - c_out:,}円")
        m2.metric("銀行残高", f"{b_in - b_out:,}円")
        m3.metric("総資産", f"{(c_in + b_in) - (c_out + b_out):,}円")

        st.divider()
        st.subheader("予算の進捗状況")
        col_inc, col_exp = st.columns(2)
        with col_inc:
            st.write("【収入の部】")
            actual_inc = df[df["区分"] == "収入"].groupby("科目")["金額"].sum()
            for k, v in BUDGET_INCOME.items():
                act = actual_inc.get(k, 0)
                st.caption(f"{k}: {act:,} / {v:,}")
                st.progress(min(act/v, 1.0) if v > 0 else 0)
        with col_exp:
            st.write("【支出の部】")
            actual_exp = df[df["区分"] == "支出"].groupby("科目")["金額"].sum()
            for k, v in BUDGET_EXPENSE.items():
                act = actual_exp.get(k, 0)
                st.caption(f"{k}: {act:,} / {v:,}")
                st.progress(min(act/v, 1.0) if v > 0 else 0)
    st.markdown("<br><a href='#linkto_top' style='display: block; text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-decoration: none; color: #31333F;'>⬆️ ページトップへ戻る</a>", unsafe_allow_html=True)

with tab3:
    st.subheader("月ごとの収支状況")
    if not df.empty:
        df["日付"] = pd.to_datetime(df["日付"])
        df['年月'] = df['日付'].dt.strftime('%Y-%m')
        month_list = sorted(df['年月'].unique(), reverse=True)
        sel_month = st.selectbox("集計月を選択", month_list)
        m_df = df[df['年月'] == sel_month].copy()
        
        st.write(f"### {sel_month} の明細表")
        m_disp = m_df[["日付", "方法", "科目", "金額", "備考"]].sort_values("日付")
        m_disp["日付"] = m_disp["日付"].dt.strftime('%Y-%m-%d')
        total_row = pd.DataFrame([["", "", "【当月合計】", m_disp["金額"].sum(), ""]], columns=m_disp.columns)
        m_with_total = pd.concat([m_disp, total_row], ignore_index=True)
        st.table(m_with_total.style.format(lambda x: f"{x:,}" if isinstance(x, (int, float)) else x))
    st.markdown("<br><a href='#linkto_top' style='display: block; text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-decoration: none; color: #31333F;'>⬆️ ページトップへ戻る</a>", unsafe_allow_html=True)

with tab4:
    st.subheader("決算報告書")
    if not df.empty:
        def get_rep_with_total(b_dict, cat):
            data = []
            act = df[df["区分"] == cat].groupby("科目")["金額"].sum()
            for k, v in b_dict.items():
                a = act.get(k, 0)
                d = a - v if cat == "収入" else v - a
                data.append({"科目": k, "予算額": v, "決算額": a, "差異": d})
            rep_df = pd.DataFrame(data)
            t_budget = rep_df["予算額"].sum()
            t_actual = rep_df["決算額"].sum()
            t_diff = t_actual - t_budget if cat == "収入" else t_budget - t_actual
            total_row = pd.DataFrame([{"科目": "【合計】", "予算額": t_budget, "決算額": t_actual, "差異": t_diff}])
            return pd.concat([rep_df, total_row], ignore_index=True)

        st.write("### 【収入の部】")
        st.table(get_rep_with_total(BUDGET_INCOME, "収入").style.format("{:,}", subset=["予算額", "決算額", "差異"]))
        st.write("### 【支出の部】")
        st.table(get_rep_with_total(BUDGET_EXPENSE, "支出").style.format("{:,}", subset=["予算額", "決算額", "差異"]))
        
        final_bal = df[df["区分"] == "収入"]["金額"].sum() - df[df["区分"] == "支出"]["金額"].sum()
        st.success(f"#### 次年度繰越金合計： {final_bal:,}円")
    st.markdown("<br><a href='#linkto_top' style='display: block; text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-decoration: none; color: #31333F;'>⬆️ ページトップへ戻る</a>", unsafe_allow_html=True)

with tab5:
    st.subheader("データの取り消し")
    if not df.empty:
        disp_df = df.copy().sort_values("日付", ascending=False)
        for i, row in disp_df.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.write(f"{row['日付'].strftime('%m/%d')} | {row['方法']} | {row['科目']} | {int(row['金額']):,}円")
            if col2.button("🗑", key=f"del_{i}"):
                df = df.drop(i)
                conn.update(worksheet="シート1", data=df)
                st.rerun()
    st.markdown("<br><a href='#linkto_top' style='display: block; text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-decoration: none; color: #31333F;'>⬆️ ページトップへ戻る</a>", unsafe_allow_html=True)
