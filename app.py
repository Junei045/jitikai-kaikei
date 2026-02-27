import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="自治会会計システム", layout="centered")

# --- あなたが発行した「ウェブに公開」用のURL ---
# 末尾の gid=... でシートを切り替えます
BASE_PUB_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRJ0ZkfG3SjQdboU2tq7_MtjgvtyJYV-ricOWWYqH3I-TROjxed2AhajgOofq17Y3-Cdd327S2RdG6h/pub?output=csv"

def clean_num(v):
    if pd.isna(v) or str(v).lower() == "nan" or str(v).strip() == "":
        return 0
    try:
        s = str(v).replace(',', '').replace('円', '').replace(' ', '').replace('　', '')
        return int(float(s))
    except:
        return 0

try:
    # 1. 実績データの読み込み（通常、何も指定しないと一番左のシートが読み込まれます）
    df_raw = pd.read_csv(BASE_PUB_URL)
    
    # 2. 設定用シートの読み込み（gidを指定。もしエラーならBASE_PUB_URL単体で試します）
    # ※ウェブに公開で「ドキュメント全体」を選択していれば、末尾に &gid=... で切り替え可能です
    try:
        conf_df = pd.read_csv(f"{BASE_PUB_URL}&gid=172856967")
    except:
        conf_df = df_raw # 予備策

    if not df_raw.empty:
        # 列名の強制設定
        raw_cols = ["タイムスタンプ", "日付", "区分", "方法", "収入科目", "支出科目", "金額", "備考", "領収書"]
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
        
        # 設定情報
        group_name = str(conf_df.iloc[0, 4]) if conf_df.shape[1] >= 5 else "自治会会計"
        BUDGET_INCOME = {str(k).strip(): clean_num(v) for k, v in zip(conf_df.iloc[:, 0], conf_df.iloc[:, 2]) if pd.notna(k) and str(k) != "nan"}
        BUDGET_EXPENSE = {str(k).strip(): clean_num(v) for k, v in zip(conf_df.iloc[:, 1], conf_df.iloc[:, 3]) if pd.notna(k) and str(k) != "nan"}

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
            
            # 予算進捗の表示
            col_i, col_e = st.columns(2)
            with col_i:
                st.write("#### 【収入】")
                actual_inc = df[df["区分"] == "収入"].groupby("科目")["金額"].sum()
                for k, v in BUDGET_INCOME.items():
                    act = actual_inc.get(k, 0)
                    st.caption(f"{k}: {int(act):,} / {int(v):,}")
                    if v > 0: st.progress(min(float(act/v), 1.0))
            with col_e:
                st.write("#### 【支出】")
                actual_exp = df[df["区分"] == "支出"].groupby("科目")["金額"].sum()
                for k, v in BUDGET_EXPENSE.items():
                    act = actual_exp.get(k, 0)
                    st.caption(f"{k}: {int(act):,} / {int(v):,}")
                    if v > 0: st.progress(min(float(act/v), 1.0))

        with tab2:
            st.subheader("月次集計")
            df['年月'] = df['日付'].dt.strftime('%Y-%m')
            m_list = sorted(df['年月'].unique(), reverse=True)
            if m_list:
                sel_m = st.selectbox("集計月", m_list)
                m_disp = df[df['年月'] == sel_m][["日付", "方法", "科目", "金額", "備考", "領収書"]].sort_values("日付")
                m_disp["日付"] = m_disp["日付"].dt.strftime('%Y-%m-%d')
                st.table(m_disp.style.format({"金額": "{:,}"}))

        with tab3:
            st.subheader("決算報告書")
            def get_rep(b_dict, cat):
                data = []
                actual_sum = df[df["区分"] == cat].groupby("科目")["金額"].sum()
                for k, v in b_dict.items():
                    a = actual_sum.get(str(k).strip(), 0)
                    data.append({"科目": k, "予算額": int(v), "決算額": int(a), "差異": int(a-v if cat=="収入" else v-a)})
                return pd.DataFrame(data)
            st.write("#### 【収入の部】")
            st.table(get_rep(BUDGET_INCOME, "収入").style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))
            st.write("#### 【支出の部】")
            st.table(get_rep(BUDGET_EXPENSE, "支出").style.format({"予算額": "{:,}", "決算額": "{:,}", "差異": "{:,}"}))

except Exception as e:
    st.error(f"読み込み失敗。URL構成を確認中...\n\n詳細: {e}")
