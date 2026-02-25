import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. 接続
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # シートを1枚だけ読み込む（これで400エラーを回避）
    all_df = conn.read(worksheet=0, ttl=0)
    
    # 団体名（E列2行目）
    group_name = str(all_df.iloc[0, 4]) if all_df.shape[1] >= 5 else "会計システム"
    st.title(group_name)

    # 設定データの抽出（A〜D列）
    INCOME_ITEMS = all_df.iloc[:, 0].dropna().tolist()
    EXPENSE_ITEMS = all_df.iloc[:, 1].dropna().tolist()
    BUDGET_INCOME = dict(zip(all_df.iloc[:, 0].dropna(), all_df.iloc[:, 2].dropna()))
    BUDGET_EXPENSE = dict(zip(all_df.iloc[:, 1].dropna(), all_df.iloc[:, 3].dropna()))

    # 実績データの抽出（G〜L列 / インデックスでいうと 6〜11）
    if all_df.shape[1] >= 12:
        df = all_df.iloc[:, 6:12].dropna(how='all')
        df.columns = ["日付", "区分", "方法", "科目", "金額", "備考"]
    else:
        df = pd.DataFrame(columns=["日付", "区分", "方法", "科目", "金額", "備考"])

except Exception as e:
    st.error(f"読み込みエラー: {e}")
    st.stop()

# 以降の入力・保存・計算処理
# 保存時は「all_df」のG列以降を更新するように処理します
# (中略：タブ表示などのロジック)

with st.sidebar:
    st.write("1枚のシートで管理中")
