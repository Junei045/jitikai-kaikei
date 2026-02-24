import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. 接続と読み込み（エラー回避のために最初に実行）
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    conf_df = conn.read(worksheet=0, ttl=0)
    try:
        df = conn.read(worksheet=1, ttl=0)
    except:
        df = conf_df.copy()

    # 団体名の取得
    if "団体名" in conf_df.columns:
        group_name = str(conf_df["団体名"].iloc[0])
    elif conf_df.shape[1] >= 5:
        group_name = str(conf_df.iloc[0, 4])
    else:
        group_name = "会計管理システム"

except Exception as e:
    group_name = "会計管理システム"

# 2. ページ設定
st.set_page_config(page_title=group_name, layout="centered")
st.title(group_name)

# 3. リスト作成（ここがズレていた場所です）
try:
    INCOME_ITEMS = conf_df["収入科目"].dropna().tolist()
    EXPENSE_ITEMS = conf_df["支出科目"].dropna().tolist()
    BUDGET_INCOME = dict(zip(conf_df["収入科目"].dropna(), conf_df["収入予算"].dropna()))
    BUDGET_EXPENSE = dict(zip(conf_df["支出科目"].dropna(), conf_df["支出予算"].dropna()))
except Exception as e:
    st.error(f"スプレッドシートの列名を確認してください: {e}")
    st.stop()

# --- 以降、入力・計算処理（昨日までのものと同じ） ---
# （続きはまた次回にしましょう！）
