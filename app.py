import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="接続リカバリー", layout="centered")
st.title("システム接続：最終解決モード")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 全シートを一度に読み込む（これが一番エラーが起きにくい方法です）
    st.info("スプレッドシートの全データをスキャン中...")
    all_df = conn.read(ttl=0) 
    
    # 1枚目のシート（設定用）を取得
    conf_df = conn.read(worksheet=0, ttl=0)
    st.success("1枚目のシートの読み込みに成功しました。")

    # 【重要】2枚目のシート取得に失敗する場合の予備策
    try:
        df = conn.read(worksheet=1, ttl=0)
        st.success("2枚目のシートの読み込みに成功しました。")
    except:
        st.warning("2枚目のシートが見つからないため、1枚目のシート内にデータを探します。")
        df = all_df.copy()

    # 団体名の取得（E列2行目）
    group_name = "団体"
    if conf_df.shape[1] >= 5:
        group_name = str(conf_df.iloc[0, 4])

    st.balloons()
    st.success(f"接続完了！ 団体名：{group_name}")
    st.divider()
    st.info("このまま本来の『会計システム』の全機能を表示するための準備が整いました。")
    
except Exception as e:
    st.error("❌ 読み込みエラーが発生しました")
    st.code(f"エラー詳細: {e}")
    st.write("スプレッドシート側の右下にあるタブを、『Config』『Data』の順に並べ直して、再度リロードしてください。")
