import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. 接続
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_num(v):
    """数値を安全に変換"""
    if pd.isna(v) or str(v).lower() == "nan" or str(v).strip() == "":
        return 0.0
    try:
        s = str(v).replace(',', '').replace('円', '').replace(' ', '').replace('　', '')
        return float(s)
    except:
        return 0.0

try:
    # シートを読み込む
    all_df = conn.read(worksheet=0, ttl=0)
    
    # 団体名取得
    group_name = str(all_df.iloc[0, 4]) if all_df.shape[1] >= 5 else "会計システム"
    
    # 設定データの抽出
    INCOME_ITEMS = all_df.iloc[:, 0].dropna().astype(str).tolist()
    EXPENSE_ITEMS = all_df.iloc[:, 1].dropna().astype(str).tolist()
    
    # 予算を数値に変換
    BUDGET_INCOME = {str(k).strip(): clean_num(v) for k, v in zip(all_df.iloc[:, 0], all_df.iloc[:, 2]) if pd.notna(k) and str(k) != "nan"}
    BUDGET_EXPENSE = {str(k).strip(): clean_num(v) for k, v in zip(all_df.iloc[:, 1], all_df.iloc[:, 3]) if pd.notna(k) and str(k) != "nan"}

    # 実績データの抽出（G列〜L列：インデックス6〜11）
    if all_df.shape[1] >= 12:
        df = all_df.iloc[:, 6:12].copy()
        df.columns = ["日付", "区分", "方法", "科目", "金額", "備考"]
        # 見出しと空行を除外
        df = df[df["日付"].astype(str) != "日付"]
        df = df.dropna(subset=["日付", "金額"], how="all")
        df["金額"] = df["金額"].apply(clean_num)
        df["科目"] = df["科目"].astype(str).str.strip()
    else:
        df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考"])

except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()

# 2. ページ設定
st.set_page_config(page_title=group_name, layout="centered")
st.title(group_name)

if "tmp_amount" not in st.session_state:
    st.session_state.tmp_amount = 0

# --- 3. タブ表示 ---
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
        date_val = st.date_input("日付", datetime.now())
        amount = st.number_input("金額（円）", min_value=0, step=1, value=st.session_state.tmp_amount)
        memo = st.text_input("備考")
        if st.form_submit_button("💾 保存する", use_container_width=True):
            if amount > 0:
                # 1行だけデータを作って追加保存（エラー回避策）
                new_row = [None]*6 + [date_val.strftime('%Y-%m-%d'), category_type, pay_method, item, amount, memo]
                # worksheet=0 の最後尾に追加
                conn.create(worksheet=0, data=[new_row])
                
                st.session_state.tmp_amount = 0
                st.success("保存しました！")
                st.rerun()

with tab2:
    st.subheader("現在の資産状況")
    c_in = df[(df["区分"] == "収入") & (df["方法"] == "現金")]["金額"].sum()
    c_out = df[(df["区分"] == "支出") & (df["方法"] == "現金")]["金額"].sum()
    b_in = df[(df["区分"] == "収入") & (df["方法"] == "銀行")]["金額"].sum()
    b_out = df[(df["区分"] == "支出") & (df["方法"] == "銀行")]["金額"].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("現金残高", f"{int(c_in - c_out):,}円")
    m2.metric("銀行残高", f"{int(b_in - b_out):,}円")
    m3.metric("総資産", f"{int((c_in + b_in) - (c_out + b_out)):,}円")
    
    st.divider()
    st.subheader("予算進捗")
    col_i, col_e = st.columns(2)
    with col_i:
        st.write("【収入】")
        actual_inc = df[df["区分"] == "収入"].groupby("科目")["金額"].sum()
        for k, v in BUDGET_INCOME.items():
            act = actual_inc.get(k, 0)
            st.caption(f"{k}: {int(act):,} / {int(v):,}")
            st.progress(min(float(act/v), 1.0) if v > 0 else 0.0)
    with col_e:
        st.write("【支出】")
        actual_exp = df[df["区分"] == "支出"].groupby("科目")["金額"].sum()
        for k, v in BUDGET_EXPENSE.items():
            act = actual_exp.get(k, 0)
            st.caption(f"{k}: {int(act):,} / {int(v):,}")
            st.progress(min(float(act/v), 1.0) if v > 0 else 0.0)

with tab3:
    st.subheader("月次集計")
    if not df.empty:
        df['年月'] = df['日付'].astype(str).str[:7]
        month_list = sorted(df['年月'].unique(), reverse=True)
        if month_list:
            sel_month = st.selectbox("集計月を選択", month_list)
            m_disp = df[df['年月'] == sel_month][["日付", "方法", "科目", "金額", "備考"]].sort_values("日付")
            st.table(m_disp.style.format({"金額": "{:,.0f}"}))

with tab4:
    st.subheader("決算報告書")
    def get_rep(b_dict, cat):
        data = []
        actual_sum = df[df["区分"] == cat].groupby("科目")["金額"].sum()
        for k, v in b_dict.items():
            a = actual_sum.get(str(k).strip(), 0)
            data.append({"科目": k, "予算額": int(v), "決算額": int(a), "差異": int(a-v if cat=="収入" else v-a)})
        return pd.DataFrame(data)
    
    st.write("### 【収入の部】")
    st.table(get_rep(BUDGET_INCOME, "収入").style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))
    st.write("### 【支出の部】")
    st.table(get_rep(BUDGET_EXPENSE, "支出").style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))

with tab5:
    st.subheader("データの取り消し")
    st.info("※データの削除はスプレッドシートから直接行ってください。")
