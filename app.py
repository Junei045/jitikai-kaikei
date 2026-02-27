import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="自治会会計システム", layout="centered")

# --- 修正：URLを極限までシンプルに定義 ---
ID = "1GGAWdo33zjrgdbwe5HBDaBNgc7UIr5s66iY_G7x15dg"

@st.cache_data(ttl=60)
def load_data(gid):
    # format=csv を先に持ってくることでエラーを回避しやすくします
    url = f"https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

try:
    # 1. 実績データの読み込み（左から1番目：gid=0）
    df_raw = load_data(0)
    
    # 2. 設定用シートの読み込み（左から2番目：gid=172856967）
    conf_df = load_data(172856967)

    # --- 以下、データ処理（変更なし） ---
    if not df_raw.empty:
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
        df["金額"] = df["金額"].apply(clean_num if 'clean_num' in globals() else lambda x: int(str(x).replace(',','')) if pd.notna(x) else 0)
        
        group_name = str(conf_df.iloc[0, 4]) if conf_df.shape[1] >= 5 else "自治会会計"
        
        st.title(f"📊 {group_name}")
        tab1, tab2, tab3 = st.tabs(["📊 予算・残高", "📅 月次集計", "📄 決算報告書"])
        # (中身の表示処理は前回のコードを継承してください)
        st.success("データの読み込みに成功しました！")
        st.write(df.head()) # 確認用に数行表示

except Exception as e:
    st.error(f"読み込み失敗。URL構成を確認中...\n\n詳細: {e}")
