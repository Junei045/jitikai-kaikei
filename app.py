import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. 接続
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_num(v):
    if pd.isna(v) or str(v).lower() == "nan" or str(v).strip() == "":
        return 0.0
    try:
        s = str(v).replace(',', '').replace('円', '').replace(' ', '').replace('　', '')
        return float(s)
    except:
        return 0.0

try:
    # データの読み込み
    all_df = conn.read(worksheet=0, ttl=0)
    
    group_name = str(all_df.iloc[0, 4]) if all_df.shape[1] >= 5 else "会計システム"
    
    INCOME_ITEMS = all_df.iloc[:, 0].dropna().astype(str).tolist()
    EXPENSE_ITEMS = all_df.iloc[:, 1].dropna().astype(str).tolist()
    
    BUDGET_INCOME = {str(k).strip(): clean_num(v) for k, v in zip(all_df.iloc[:, 0], all_df.iloc[:, 2]) if pd.notna(k) and str(k) != "nan"}
    BUDGET_EXPENSE = {str(k).strip(): clean_num(v) for k, v in zip(all_df.iloc[:, 1], all_df.iloc[:, 3]) if pd.notna(k) and str(k) != "nan"}

    # 実績データの抽出（G-L列）
    if all_df.shape[1] >= 12:
        df = all_df.iloc[:, 6:12].copy()
        df.columns = ["日付", "区分", "方法", "科目", "金額", "備考"]
        df = df[df["日付"].astype(str) != "日付"]
        df = df.dropna(subset=["日付", "金額"], how="all")
        df["金額"] = df["金額"].apply(clean_num)
        df["科目"] = df["科目"].astype(str).str.strip()
    else:
        df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考"])

except Exception as e:
    st.error(f"読み込みエラー: {e}")
    st.stop()

st.set_page_config(page_title=group_name, layout="centered")
st.title(group_name)

if "tmp_amount" not in st.session_state:
    st.session_state.tmp_amount = 0

# タブ表示
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
                # 複雑な計算をせず、一番シンプルな「リストの追加」を試みます
                try:
                    # 1行のデータを作成（A-F列は空）
                    new_data = [None, None, None, None, None, None, 
                                date_val.strftime('%Y-%m-%d'), category_type, pay_method, item, amount, memo]
                    
                    # conn.update ではなく、もっとも原始的な「append」的な動作を期待して
                    # 既存の全データに1行足して、全体を「上書き」します
                    new_df = pd.DataFrame([new_data], columns=all_df.columns)
                    updated_all = pd.concat([all_df, new_df], ignore_index=True)
                    
                    # ここでエラーが出る場合は、ツール側の制限です
                    conn.update(worksheet=0, data=updated_all)
                    
                    st.success("保存に成功しました！")
                    st.session_state.tmp_amount = 0
                    st.rerun()
                except Exception as e:
                    st.error("⚠️ Googleのセキュリティ制限により、この接続方法では保存が許可されませんでした。")
                    st.info("解決には『サービスアカウント』の設定が必要ですが、まずはスプレッドシートに直接入力し、このアプリを『閲覧・集計専用』として使うことも可能です。")

# --- 2枚目以降の集計処理 ---
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
    # 予算進捗
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
        m_list = sorted(df['年月'].unique(), reverse=True)
        sel_m = st.selectbox("集計月を選択", m_list)
        m_disp = df[df['年月'] == sel_m][["日付", "方法", "科目", "金額", "備考"]].sort_values("日付")
        st.table(m_disp.style.format({"金額": "{:,.0f}"}))

with tab4:
    st.subheader("決算報告書")
    def get_rep(b_dict, cat):
        data = []
        actual_sum = df[df["区分"] == cat].groupby("科目")["金額"].sum()
        for k, v in b_dict.items():
            a = actual_sum.get(str(k).strip(), 0)
            # 予算・決算・差異をすべて整数(int)に変換してから入れる
            data.append({
                "科目": k, 
                "予算額": int(v), 
                "決算額": int(a), 
                "差異": int(a-v if cat=="収入" else v-a)
            })
        return pd.DataFrame(data)
    
    # style.format("{:,}") を style.format("{:,.0f}") または数値列指定に変更
    st.write("### 【収入の部】")
    res_inc = get_rep(BUDGET_INCOME, "収入")
    if not res_inc.empty:
        st.table(res_inc.style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))
    
    st.write("### 【支出の部】")
    res_exp = get_rep(BUDGET_EXPENSE, "支出")
    if not res_exp.empty:
        st.table(res_exp.style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))

with tab5:
    st.subheader("データの取り消し")
    if not df.empty:
        for i in reversed(df.index):
            row = df.loc[i]
            col_txt, col_btn = st.columns([4, 1])
            col_txt.write(f"{row['日付']} | {row['科目']} | {int(row['金額']):,}円")
            if col_btn.button("削除", key=f"del_{i}"):
                new_all_df = all_df.drop(i)
                conn.update(worksheet=0, data=new_all_df)
                st.success("削除しました")
                st.rerun()



