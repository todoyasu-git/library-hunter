import streamlit as st
import urllib.parse

st.set_page_config(page_title="図書館ハンター", layout="centered")

st.title("📚 図書館ハンター")
st.caption("書名を入れて、カーリル検索・メルカリ検索・図書館ログインを一発で開く簡易版")

query = st.text_input("書籍名を入力", placeholder="例：ファクトフルネス")

if query:
    encoded = urllib.parse.quote(query)

    calil_url = f"https://calil.jp/search?q={encoded}"
    mercari_url = f"https://jp.mercari.com/search?keyword={encoded}"

    st.subheader(query)

    st.link_button("📚 カーリルで図書館検索", calil_url)
    st.link_button("🛒 メルカリで探す", mercari_url)

    st.divider()
    st.write("### 図書館ログイン")

    st.link_button(
        "🔐 江東区図書館にログイン",
        "https://www.koto-lib.tokyo.jp/opw/OPW/OPWLOGINTIME.CSP?DB=LIB"
    )

    st.caption("iPhoneのパスワード自動入力を使えば、貸出カード番号とパスワードをFace IDで入力できます。")
