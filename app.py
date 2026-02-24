import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="接続テスト", layout="centered")
st.title("システム接続 最終チェック")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 【重要】名前（"Config"）ではなく、番号（0）で指定します
    st.info("ステップ1: 1番目のシート（設定用）を読み込み中...")
    conf_df = conn.read(worksheet=0, ttl=0) 
    st.success("1番目のシートの読み込みに成功！")

    # 【重要】名前（"Data"）ではなく、番号（1）で指定します
    st.info("ステップ2: 2番目のシート（実績用）を読み込み中...")
    df = conn.read(worksheet=1, ttl=0)
    st.success("2番目のシートの読み込みに成功！")

    # 団体名の表示テスト（E列2行目）
    group_name = str(conf_df.iloc[0, 4])
    st.balloons()
    st.success(f"確認完了！団体名：{group_name}")
    st.write("これが表示されれば、もうエラーは出ません。")

except Exception as e:
    st.error("❌ まだエラーが出ます")
    st.code(f"内容: {e}")
    st.info("もし400エラーが出る場合は、スプレッドシートのURL(ID)を再度Secretsで確認してください。")
