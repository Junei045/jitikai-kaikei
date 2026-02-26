import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 接続設定
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
    # 修正：シート名を名指しで読み込む。まずは実績データの「data」
    # もしエラーが出るならここを worksheet=0 に戻す
    all_df = conn.read(worksheet="data", ttl=0)
    
    # 次に「シート1」（予算設定などが入っている元のシート）
    conf_df = conn.read(worksheet="シート1", ttl=0)

    # データが取得できているかチェック
    if all_df is not None:
        df_raw = all_df.copy()
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
        
        group_name = str(conf_df.iloc[0, 4]) if conf_df.shape[1] >= 5 else "会計システム"
        BUDGET_INCOME = {str(k).strip(): clean_num(v) for k, v in zip(conf_df.iloc[:, 0], conf_df.iloc[:, 2]) if pd.notna(k) and str(k) != "nan"}
        BUDGET_EXPENSE = {str(k).strip(): clean_num(v) for k, v in zip(conf_df.iloc[:, 1], conf_df.iloc[:, 3]) if pd.notna(k) and str(k) != "nan"}
    else:
        st.error("データが読み込めませんでした。")
        st.stop()

except Exception as e:
    st.error(f"詳細なエラー報告: {e}")
    st.info("スプレッドシートのタブ名が『data』と『シート1』になっているか確認してください。")
    st.stop()

# --- 以降の表示コードは省略（表示部分は前回のまま） ---
st.set_page_config(page_title=group_name, layout="centered")
st.title(f"📊 {group_name}")
# ...（中略：tab1, tab2, tab3 の表示処理）
