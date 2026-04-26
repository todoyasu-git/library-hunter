import streamlit as st
import urllib.parse
import re

st.set_page_config(page_title="図書館ハンター", layout="centered")

st.title("📚 図書館ハンター")
st.caption("カーリル検索・メルカリ検索・図書館ログインを一発で開く簡易版")

query = st.text_input("書籍名を入力", placeholder="例：ファクトフルネス")

if query:
    encoded = urllib.parse.quote(query)

    calil_url = f"https://calil.jp/search?q={encoded}"
    mercari_url = f"https://jp.mercari.com/search?keyword={encoded}"

    st.subheader(query)

    st.link_button("📚 カーリルで図書館検索", calil_url)
    st.link_button("🛒 メルカリで探す（入力語）", mercari_url)

st.divider()
st.write("### ISBNでメルカリ検索")

calil_book_url = st.text_input(
    "カーリルの本ページURLを貼り付け",
    placeholder="例：https://calil.jp/book/4909679715"
)

if calil_book_url:
    match = re.search(r"calil\.jp/book/([0-9Xx\-]+)", calil_book_url)

    if match:
        isbn = match.group(1).replace("-", "")
        st.success(f"ISBNを検出しました: {isbn}")

        mercari_isbn_url = f"https://jp.mercari.com/search?keyword={urllib.parse.quote(isbn)}"
        st.link_button("🛒 メルカリでISBN検索", mercari_isbn_url)
    else:
        st.warning("カーリル本ページURLからISBNを読み取れませんでした。")

st.divider()
st.write("### 図書館ログイン")

st.link_button(
    "🔐 江東区図書館にログイン",
    "https://www.koto-lib.tokyo.jp/opw/OPW/OPWLOGINTIME.CSP?DB=LIB"
)

st.caption("iPhoneのパスワード自動入力を使えば、貸出カード番号とパスワードをFace IDで入力できます。")
