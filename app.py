import streamlit as st
import requests
import urllib.parse
import time

st.set_page_config(page_title="図書館ハンター", layout="centered")

CALIL_APPKEY = st.secrets["CALIL_APPKEY"]
RAKUTEN_APP_ID = st.secrets["RAKUTEN_APP_ID"]

LIBRARIES = {
    "江東区図書館": "Tokyo_Koto",
    "中央区図書館": "Tokyo_Chuo",
    "墨田区図書館": "Tokyo_Sumida",
    "文京区図書館": "Tokyo_Bunkyo",
    "江戸川区図書館": "Tokyo_Edogawa",
}

st.title("📚 図書館ハンター")
st.caption("楽天Booksで候補表示 → 図書館在庫確認 → メルカリ検索")

def search_books(query):
    url = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"

    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": st.secrets["RAKUTEN_ACCESS_KEY"],
        "title": query,
        "format": "json",
        "hits": 10,
    }

    headers = {
        "Referer": "https://todoyasu-git-library-hunter-app-x7hxk6.streamlit.app/"
    }

    r = requests.get(url, params=params, headers=headers, timeout=15)

    if r.status_code != 200:
        st.error(f"楽天APIエラー本文: {r.text}")

    r.raise_for_status()
    data = r.json()
    return [x["Item"] for x in data.get("Items", [])]

def check_library(isbn):
    url = "https://api.calil.jp/check"
    params = {
        "appkey": CALIL_APPKEY,
        "isbn": isbn,
        "systemid": ",".join(LIBRARIES.values()),
        "format": "json",
        "callback": "",
    }

    data = {}
    for _ in range(6):
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("continue") == 0:
            return data
        time.sleep(2)
    return data

query = st.text_input("書籍名を入力", placeholder="例：るるぶ高知")

if query:
    try:
        books = search_books(query)

        if not books:
            st.warning("候補が見つかりませんでした。")
        else:
            labels = []
            for b in books:
                title = b.get("title", "タイトル不明")
                author = b.get("author", "")
                publisher = b.get("publisherName", "")
                sales_date = b.get("salesDate", "")
                labels.append(f"{title} / {author} / {publisher} / {sales_date}")

            selected_label = st.selectbox("候補から選択してください", labels)
            selected = books[labels.index(selected_label)]

            title = selected.get("title", "")
            author = selected.get("author", "")
            publisher = selected.get("publisherName", "")
            isbn = selected.get("isbn", "")
            image_url = selected.get("largeImageUrl") or selected.get("mediumImageUrl")
            item_url = selected.get("itemUrl", "")

            if image_url:
                st.image(image_url, width=160)

            st.subheader(title)
            st.write(f"著者: {author}")
            st.write(f"出版社: {publisher}")
            st.write(f"ISBN: {isbn}")

            if item_url:
                st.link_button("📘 楽天Booksで確認", item_url)

            mercari_keyword = urllib.parse.quote(f"{title} {author}")
            mercari_url = f"https://jp.mercari.com/search?keyword={mercari_keyword}"
            st.link_button("🛒 メルカリで探す", mercari_url)

            if isbn:
                st.divider()
                st.write("📖 図書館在庫確認中...")

                result = check_library(isbn)
                target = result.get("books", {}).get(isbn, {})

                for name, sid in LIBRARIES.items():
                    st.write(f"### {name}")

                    lib = target.get(sid)
                    if not lib:
                        st.write("蔵書情報なし")
                        continue

                    libkey = lib.get("libkey", {})
                    if libkey:
                        for branch, status in libkey.items():
                            st.write(f"- {branch}: {status}")
                    else:
                        st.write("貸出状況取得不可")
            else:
                st.info("ISBNが見つからないため図書館検索できません。")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
