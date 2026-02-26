import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 接続
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_num(v):
    if pd.isna(v) or str(v).lower() == "nan" or str(v).strip() == "":
        return 0
    try:
        s = str(v).replace(',', '').replace('円', '').replace(' ', '').replace('　', '')
        return int(float(s))
    except:
        return 0

try:
    # 修正：一番左のタブ（インデックス0）を実績データとして読み込む
    all_df = conn.read(worksheet=0, ttl=0)
    
    # 修正：左から二番目のタブ（インデックス1）を団体名や予算設定として読み込む
    # ※もし「設定」シートが左から三番目ならここを 2 に変えてください
    conf_df = conn.read(worksheet=1, ttl=0)
    
    group_name = str(conf_df.iloc[0, 4]) if conf_df.shape[1] >= 5 else "会計システム"
    BUDGET_INCOME = {str(k).strip(): clean_num(v) for k, v in zip(conf_df.iloc[:, 0], conf_df.iloc[:, 2]) if pd.notna(k) and str(k) != "nan"}
    BUDGET_EXPENSE = {str(k).strip(): clean_num(v) for k, v in zip(conf_df.iloc[:, 1], conf_df.iloc[:, 3]) if pd.notna(k) and str(k) != "nan"}

    # データ抽出（列構成は前回の通り：タイムスタンプ, 日付, 区分, 方法, 収入科目, 支出科目, 金額, 備考, 領収書）
    if not all_df.empty:
        df_raw = all_df.copy()
        raw_cols = ["タイムスタンプ", "日付", "区分", "方法", "収入科目", "支出科目", "金額", "備考", "領収書"]
        # 実際に取得できた列数に合わせて調整
        df_raw.columns = raw_cols[:len(df_raw.columns)]
        
        df_raw["日付"] = pd.to_datetime(df_raw["日付"], errors='coerce')
        df_raw = df_raw.dropna(subset=["日付"])
        
        def get_subject(row):
            inc = str(row.get("収入科目", "")).strip()
            exp = str(row.get("支出科目", "")).strip()
            if inc and inc != "nan" and inc != "None": return inc
            if exp and exp != "nan" and exp != "None": return exp
            return "未分類"

        df_raw["科目"] = df_raw.apply(get_subject, axis=1)
        df = df_raw[["日付", "区分", "方法", "科目", "金額", "備考", "領収書"]].copy()
        df["金額"] = df["金額"].apply(clean_num)
    else:
        df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考", "領収書"])

except Exception as e:
    st.error(f"読み込みエラー: {e}")
    st.stop()

# --- 以降の表示設定は変更なし ---
st.set_page_config(page_title=group_name, layout="centered")
st.title(f"📊 {group_name}")

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
        df['年月'] = df['日付'].dt.strftime('%Y-%m')
        m_list = sorted(df['年月'].unique(), reverse=True)
        if m_list:
            sel_m = st.selectbox("集計月を選択", m_list)
            m_disp = df[df['年月'] == sel_m][["日付", "方法", "科目", "金額", "備考", "領収書"]].sort_values("日付").copy()
            m_disp["日付"] = m_disp["日付"].dt.strftime('%Y-%m-%d')
            m_disp.index = range(1, len(m_disp) + 1)
            st.table(m_disp.style.format({"金額": "{:,}"}))
        else:
            st.info("データがありません。")

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
    st.table(get_rep(BUDGET_INCOME, "収入").style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))
    st.write("#### 【支出の部】")
    st.table(get_rep(BUDGET_EXPENSE, "支出").style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))


