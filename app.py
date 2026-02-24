import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="診断モード", layout="centered")
st.title("システム接続 診断画面")

# 接続の試行
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 手順A: まずはシート名を指定せずに全体を触ってみる
    st.info("ステップ1: スプレッドシートへの接続を確認中...")
    raw_data = conn.read(ttl=0)
    st.success("スプレッドシートへの接続自体は成功しました！")

    # 手順B: Configシートの読み込み
    st.info("ステップ2: 'Config' シートを探しています...")
    conf_df = conn.read(worksheet="Config", ttl=0)
    st.success("'Config' シートの読み込みに成功しました！")

    # 手順C: Dataシートの読み込み
    st.info("ステップ3: 'Data' シートを探しています...")
    df = conn.read(worksheet="Data", ttl=0)
    st.success("'Data' シートの読み込みに成功しました！")

    # 団体名の表示テスト
    group_name = str(conf_df.iloc[0, 4])
    st.write(f"認識された団体名: {group_name}")
    st.balloons()
    st.success("すべての接続が正常です！このまま本来の機能を表示します...")

    # --- ここから本来のメインプログラムを動かす（簡易版） ---
    # (正常ならここから下のタブが表示されます)
    tab1, tab2 = st.tabs(["📝 入力", "📊 確認"])
    with tab1:
        st.write("ここに正常な入力画面が出ます。")

except Exception as e:
    st.error("❌ エラーが発生しました")
    st.warning(f"エラーの種類: {type(e).__name__}")
    st.code(f"エラーメッセージ: {e}")
    
    st.divider()
    st.subheader("💡 解決のためのチェックリスト")
    st.write("以下の3点を順番に見てください：")
    st.write("1. **SecretsのID**: `1GGAWdo33zjrgdbwe5HBDaBNgc7UIr5s66iY_G7x15dg` だけになっていますか？")
    st.write("2. **シート名**: スプレッドシートのタブはカタカナの『設定』ではなく、半角英字の **Config** になっていますか？")
    st.write("3. **共有設定**: スプレッドシート右上の共有ボタンで、**『編集者』** になっていますか？")
