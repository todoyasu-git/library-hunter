import streamlit as st
import requests
import urllib.parse
import time

st.set_page_config(page_title="図書館ハンター", layout="centered")

# Secrets からAPIキー取得
CALIL_APPKEY = st.secrets["CALIL_APPKEY"]
GOOGLE_BOOKS_API_KEY = st.secrets["GOOGLE_BOOKS_API_KEY"]

# 対象図書館（カーリル systemid）
LIBRARIES = {
    "江東区図書館": "Tokyo_Koto",
    "中央区図書館": "Tokyo_Chuo",
    "墨田区図書館": "Tokyo_Sumida",
    "文京区図書館": "Tokyo_Bunkyo",
    "江戸川区図書館": "Tokyo_Edogawa",
}

st.title("📚 図書館ハンター")
st.caption("本屋で見つけた本を、図書館在庫とメルカリで即確認")

# -----------------------------
# Google Books検索
# -----------------------------
def search_books(query):
    url = "https://www.googleapis.com/books/v1/volumes"

    params = {
        "q": query,
        "maxResults": 8,
        "printType": "books",
        "langRestrict": "ja",
        "key": GOOGLE_BOOKS_API_KEY,
    }

    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()

    data = r.json()
    return data.get("items", [])


# -----------------------------
# カーリル検索
# -----------------------------
def check_library(isbn):
    systemids = ",".join(LIBRARIES.values())

    url = "https://api.calil.jp/check"

    params = {
        "appkey": CALIL_APPKEY,
        "isbn": isbn,
        "systemid": systemids,
        "format": "json",
        "callback": "",
    }

    for _ in range(6):
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        if data.get("continue") == 0:
            return data

        time.sleep(2)

    return data


# -----------------------------
# UI
# -----------------------------
query = st.text_input("書籍名を入力", placeholder="例：るるぶ高知")

if query:
    try:
        books = search_books(query)

        if not books:
            st.warning("候補が見つかりませんでした。")
        else:
            options = []

            for item in books:
                info = item["volumeInfo"]
                title = info.get("title", "タイトル不明")
                authors = ", ".join(info.get("authors", []))
                published = info.get("publishedDate", "")
                label = f"{title} / {authors} / {published}"
                options.append((label, item))

            selected_label = st.selectbox(
                "候補から選択してください",
                [x[0] for x in options]
            )

            selected = None
            for label, item in options:
                if label == selected_label:
                    selected = item
                    break

            if selected:
                info = selected["volumeInfo"]

                title = info.get("title", "")
                authors = ", ".join(info.get("authors", []))

                isbn = None
                for ident in info.get("industryIdentifiers", []):
                    if ident["type"] in ["ISBN_13", "ISBN_10"]:
                        isbn = ident["identifier"]
                        break

                st.subheader(title)
                st.write(authors)

                # メルカリリンク
                keyword = urllib.parse.quote(f"{title} {authors}")
                mercari_url = f"https://jp.mercari.com/search?keyword={keyword}"
                st.link_button("🛒 メルカリで探す", mercari_url)

                # 図書館検索
                if isbn:
                    st.divider()
                    st.write("📖 図書館在庫確認中...")

                    result = check_library(isbn)

                    books_data = result.get("books", {})
                    target = books_data.get(isbn, {})

                    for name, sid in LIBRARIES.items():
                        st.write(f"### {name}")

                        if sid not in target:
                            st.write("蔵書情報なし")
                            continue

                        lib = target[sid]

                        if "libkey" in lib and lib["libkey"]:
                            for branch, status in lib["libkey"].items():
                                st.write(f"- {branch}: {status}")
                        else:
                            st.write("貸出状況取得不可")

                else:
                    st.info("ISBNが見つからないため図書館検索できません。")

    except Exception as e:
        st.error(f"書籍検索でエラーが発生しました: {e}")
