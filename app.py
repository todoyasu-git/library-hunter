import streamlit as st
import requests
import urllib.parse
import time
import xml.etree.ElementTree as ET

st.set_page_config(page_title="図書館ハンター", layout="centered")

CALIL_APPKEY = st.secrets["CALIL_APPKEY"]

LIBRARIES = {
    "江東区図書館": "Tokyo_Koto",
    "中央区図書館": "Tokyo_Chuo",
    "墨田区図書館": "Tokyo_Sumida",
    "文京区図書館": "Tokyo_Bunkyo",
    "江戸川区図書館": "Tokyo_Edogawa",
}

st.title("📚 図書館ハンター")
st.caption("国会図書館サーチで候補表示 → 図書館在庫確認 → メルカリ検索")


def search_books(query):
    url = "https://ndlsearch.ndl.go.jp/api/opensearch"
    params = {
        "title": query,
        "cnt": 10,
    }

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()

    root = ET.fromstring(r.content)

    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        creator = item.findtext("{http://purl.org/dc/elements/1.1/}creator") or ""
        publisher = item.findtext("{http://purl.org/dc/elements/1.1/}publisher") or ""
        date = item.findtext("{http://purl.org/dc/elements/1.1/}date") or ""

        isbn = ""
        for ident in item.findall("{http://purl.org/dc/elements/1.1/}identifier"):
            text = ident.text or ""
            clean = text.replace("ISBN", "").replace(":", "").replace("-", "").strip()
            if clean.isdigit() and len(clean) in [10, 13]:
                isbn = clean
                break

        link = item.findtext("link") or ""

        if title:
            items.append({
                "title": title,
                "creator": creator,
                "publisher": publisher,
                "date": date,
                "isbn": isbn,
                "link": link,
            })

    return items


def check_library(isbn):
    url = "https://api.calil.jp/check"

    params = {
        "appkey": CALIL_APPKEY,
        "isbn": isbn,
        "systemid": ",".join(LIBRARIES.values()),
        "format": "json",
    }

    data = {}

    for _ in range(8):
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()

        text = r.text.strip()

        if not text:
            time.sleep(2)
            continue

        try:
            data = r.json()
        except Exception:
            st.error("カーリルAPIからJSON以外の応答が返りました。")
            st.code(text[:500])
            return {}

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
                labels.append(
                    f"{b['title']} / {b['creator']} / {b['publisher']} / {b['date']}"
                )

            selected_label = st.selectbox("候補から選択してください", labels)
            selected = books[labels.index(selected_label)]

            title = selected["title"]
            creator = selected["creator"]
            publisher = selected["publisher"]
            date = selected["date"]
            isbn = selected["isbn"]
            link = selected["link"]

            st.subheader(title)

            if creator:
                st.write(f"著者: {creator}")
            if publisher:
                st.write(f"出版社: {publisher}")
            if date:
                st.write(f"出版年: {date}")
            if isbn:
                st.write(f"ISBN: {isbn}")

            if link:
                st.link_button("📘 国会図書館サーチで確認", link)

            mercari_keyword = urllib.parse.quote(f"{title} {creator}")
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
