import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 接続
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_num(v):
    """数値を安全に変換（文字が混じっていても0にする）"""
    if pd.isna(v) or str(v).lower() == "nan" or str(v).strip() == "":
        return 0
    try:
        s = str(v).replace(',', '').replace('円', '').replace(' ', '').replace('　', '')
        return int(float(s))
    except:
        return 0

try:
    # データの読み込み
    all_df = conn.read(worksheet=0, ttl=0)
    
    # 団体名取得
    group_name = str(all_df.iloc[0, 4]) if all_df.shape[1] >= 5 else "会計システム"
    
    # 設定データの抽出
    BUDGET_INCOME = {str(k).strip(): clean_num(v) for k, v in zip(all_df.iloc[:, 0], all_df.iloc[:, 2]) if pd.notna(k) and str(k) != "nan"}
    BUDGET_EXPENSE = {str(k).strip(): clean_num(v) for k, v in zip(all_df.iloc[:, 1], all_df.iloc[:, 3]) if pd.notna(k) and str(k) != "nan"}

    # 実績データの抽出（G-L列）
    if all_df.shape[1] >= 12:
        df = all_df.iloc[:, 6:12].copy()
        df.columns = ["日付", "区分", "方法", "科目", "金額", "備考"]
        
        # 見出し「日付」という行が混じっていたら削除
        df = df[df["日付"].astype(str) != "日付"]
        # 日付または金額が空の行を削除
        df = df.dropna(subset=["日付", "金額"], how="all")
        
        # 【重要】日付のズレ対策：一度日付型に変換し、エラーはNaT（欠損）にする
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce')
        # 日付に変換できなかった行（変な文字など）を捨てる
        df = df.dropna(subset=["日付"])
        
        # 金額を数値化
        df["金額"] = df["金額"].apply(clean_num)
        df["科目"] = df["科目"].astype(str).str.strip()
    else:
        df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考"])

except Exception as e:
    st.error(f"読み込みエラー: {e}")
    st.stop()

# ページ設定
st.set_page_config(page_title=group_name, layout="centered")
st.title(f"📊 {group_name}")
st.caption("※データ入力・修正はスプレッドシートで行ってください。")

# タブ表示
tab1, tab2, tab3 = st.tabs(["📊 予算・残高", "📅 月次集計", "📄 決算報告書"])

with tab1:
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
        st.write("#### 【収入】")
        actual_inc = df[df["区分"] == "収入"].groupby("科目")["金額"].sum()
        for k, v in BUDGET_INCOME.items():
            act = actual_inc.get(k, 0)
            st.caption(f"{k}: {int(act):,} / {int(v):,}")
            st.progress(min(float(act/v), 1.0) if v > 0 else 0.0)
    with col_e:
        st.write("#### 【支出】")
        actual_exp = df[df["区分"] == "支出"].groupby("科目")["金額"].sum()
        for k, v in BUDGET_EXPENSE.items():
            act = actual_exp.get(k, 0)
            st.caption(f"{k}: {int(act):,} / {int(v):,}")
            st.progress(min(float(act/v), 1.0) if v > 0 else 0.0)

with tab2:
    st.subheader("月次集計")
    if not df.empty:
        # 年月でフィルタリング
        df['年月'] = df['日付'].dt.strftime('%Y-%m')
        m_list = sorted(df['年月'].unique(), reverse=True)
        if m_list:
            sel_m = st.selectbox("集計月を選択", m_list)
            m_disp = df[df['年月'] == sel_m][["日付", "方法", "科目", "金額", "備考"]].sort_values("日付").copy()
            # 表示用に日付を整形
            m_disp["日付"] = m_disp["日付"].dt.strftime('%Y-%m-%d')
            # 行番号を1から振る
            m_disp.index = range(1, len(m_disp) + 1)
            # 安全にカンマ表示（数値列のみ指定）
            st.table(m_disp.style.format({"金額": "{:,}"}))
        else:
            st.info("集計可能なデータがありません。")

with tab3:
    st.subheader("決算報告書")
    def get_rep(b_dict, cat):
        data = []
        actual_sum = df[df["区分"] == cat].groupby("科目")["金額"].sum()
        for k, v in b_dict.items():
            a = actual_sum.get(str(k).strip(), 0)
            data.append({"科目": k, "予算額": int(v), "決算額": int(a), "差異": int(a-v if cat=="収入" else v-a)})
        res_df = pd.DataFrame(data)
        if not res_df.empty:
            res_df.index = range(1, len(res_df) + 1)
        return res_df

    st.write("#### 【収入の部】")
    rep_inc = get_rep(BUDGET_INCOME, "収入")
    st.table(rep_inc.style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))
    
    st.write("#### 【支出の部】")
    rep_exp = get_rep(BUDGET_EXPENSE, "支出")
    st.table(rep_exp.style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))
