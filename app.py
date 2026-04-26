import time
import urllib.parse
from typing import Dict, List, Optional

import requests
import streamlit as st

# ============================================================
# 図書館ハンター iPhone版 設定欄
# ============================================================
import streamlit as st

CALIL_APPKEY = st.secrets["CALIL_APPKEY"]

# 検索対象の図書館システムID
# ※カーリルの systemid は自治体・システム単位です。
# もし動かない場合は、カーリルAPIの library/search で正確なsystemidを確認してください。
TARGET_SYSTEMS = {
    "江東区図書館": "Tokyo_Koto",
    "中央区図書館": "Tokyo_Chuo",
    "墨田区図書館": "Tokyo_Sumida",
    "文京区図書館": "Tokyo_Bunkyo",
    "江戸川区図書館": "Tokyo_Edogawa",
}

MAX_BOOK_CANDIDATES = 8
CALIL_POLL_SECONDS = 2
CALIL_MAX_POLLS = 8

# ============================================================
# 画面設定 iPhone向け
# ============================================================
st.set_page_config(
    page_title="図書館ハンター",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .block-container {
        padding-top: 1.0rem;
        padding-left: 1.0rem;
        padding-right: 1.0rem;
        max-width: 720px;
    }
    h1 {
        font-size: 2.0rem !important;
        line-height: 1.2 !important;
        margin-bottom: 0.2rem !important;
    }
    h2, h3 {
        margin-top: 1.1rem !important;
    }
    div[data-testid="stTextInput"] input {
        font-size: 1.2rem !important;
        padding: 0.85rem !important;
        border-radius: 12px !important;
    }
    div.stButton > button,
    div[data-testid="stLinkButton"] a {
        width: 100%;
        min-height: 3.2rem;
        font-size: 1.08rem !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
    }
    .book-card {
        border: 1px solid #ddd;
        border-radius: 16px;
        padding: 0.9rem;
        margin-bottom: 0.8rem;
        background: #fff;
        box-shadow: 0 1px 5px rgba(0,0,0,0.06);
    }
    .book-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }
    .book-meta {
        font-size: 0.92rem;
        color: #555;
        line-height: 1.45;
    }
    .library-ok {
        font-weight: 800;
    }
    .small-note {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# Utility functions
# ============================================================

def normalize_isbn(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit() or ch.upper() == "X")


def search_google_books(query: str, max_results: int = MAX_BOOK_CANDIDATES) -> List[Dict]:
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": max_results,
        "printType": "books",
        "langRestrict": "ja",
    }
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    data = r.json()
    books = []
    for item in data.get("items", []):
        info = item.get("volumeInfo", {})
        identifiers = info.get("industryIdentifiers", [])
        isbn13 = None
        isbn10 = None
        for ident in identifiers:
            if ident.get("type") == "ISBN_13":
                isbn13 = normalize_isbn(ident.get("identifier", ""))
            elif ident.get("type") == "ISBN_10":
                isbn10 = normalize_isbn(ident.get("identifier", ""))
        isbn = isbn13 or isbn10
        if not isbn:
            continue
        books.append(
            {
                "title": info.get("title", "タイトル不明"),
                "authors": ", ".join(info.get("authors", [])),
                "publisher": info.get("publisher", ""),
                "publishedDate": info.get("publishedDate", ""),
                "isbn": isbn,
                "thumbnail": info.get("imageLinks", {}).get("thumbnail", ""),
                "previewLink": info.get("previewLink", ""),
            }
        )
    return books


def build_mercari_url(book: Dict) -> str:
    keyword = f"{book.get('title', '')} {book.get('authors', '')}".strip()
    return "https://jp.mercari.com/search?keyword=" + urllib.parse.quote(keyword)


def build_amazon_url(book: Dict) -> str:
    keyword = book.get("isbn") or f"{book.get('title', '')} {book.get('authors', '')}"
    return "https://www.amazon.co.jp/s?k=" + urllib.parse.quote(keyword)


def check_calil(isbn: str) -> Optional[Dict]:
    if not CALIL_APPKEY or CALIL_APPKEY == "PASTE_YOUR_CALIL_APPKEY_HERE":
        st.error("app.py 冒頭の CALIL_APPKEY にカーリルのアプリケーションキーを入れてください。")
        return None

    systemids = ",".join(TARGET_SYSTEMS.values())
    params = {
        "appkey": CALIL_APPKEY,
        "isbn": isbn,
        "systemid": systemids,
        "format": "json",
        "callback": "no",
    }
    url = "https://api.calil.jp/check"

    session = None
    data = None
    for i in range(CALIL_MAX_POLLS):
        if session:
            params = {
                "appkey": CALIL_APPKEY,
                "session": session,
                "format": "json",
                "callback": "no",
            }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        session = data.get("session", session)
        if data.get("continue") == 0:
            return data
        time.sleep(CALIL_POLL_SECONDS)

    return data


def summarize_library_status(calil_data: Dict) -> List[Dict]:
    results = []
    if not calil_data:
        return results

    books = calil_data.get("books", {})
    for _isbn, book_data in books.items():
        systems = book_data.items()
        for systemid, system_data in systems:
            name = next((k for k, v in TARGET_SYSTEMS.items() if v == systemid), systemid)
            status = system_data.get("status", "不明")
            reserveurl = system_data.get("reserveurl", "")
            libkeys = system_data.get("libkey", {}) or {}
            libraries_text = []
            has_available = False
            has_collection = False
            for branch, state in libkeys.items():
                has_collection = True
                libraries_text.append(f"{branch}: {state}")
                if "貸出可" in str(state) or "蔵書あり" in str(state) or "在庫" in str(state):
                    has_available = True
            results.append(
                {
                    "name": name,
                    "systemid": systemid,
                    "status": status,
                    "reserveurl": reserveurl,
                    "libraries": libraries_text,
                    "has_available": has_available,
                    "has_collection": has_collection,
                }
            )
    # 借りられそうなもの→蔵書あり→それ以外の順
    results.sort(key=lambda x: (not x["has_available"], not x["has_collection"], x["name"]))
    return results


# ============================================================
# Main UI
# ============================================================
st.title("📚 図書館ハンター")
st.caption("書名から候補を選び、5区図書館とメルカリを一発確認")

with st.expander("検索対象の図書館", expanded=False):
    for label, sid in TARGET_SYSTEMS.items():
        st.write(f"- {label}：`{sid}`")
    st.markdown("<div class='small-note'>systemid が違う場合は、この設定欄を書き換えます。</div>", unsafe_allow_html=True)

query = st.text_input("本のタイトルを入力", placeholder="例：失敗の本質")

if "books" not in st.session_state:
    st.session_state.books = []
if "selected_book" not in st.session_state:
    st.session_state.selected_book = None

if st.button("候補を探す", type="primary"):
    if not query.strip():
        st.warning("本のタイトルを入力してください。")
    else:
        with st.spinner("書籍候補を検索中..."):
            try:
                st.session_state.books = search_google_books(query.strip())
                st.session_state.selected_book = None
            except Exception as e:
                st.error(f"書籍検索でエラーが発生しました: {e}")

if st.session_state.books:
    st.subheader("候補から選ぶ")
    for idx, book in enumerate(st.session_state.books):
        with st.container():
            st.markdown("<div class='book-card'>", unsafe_allow_html=True)
            cols = st.columns([1, 3])
            with cols[0]:
                if book.get("thumbnail"):
                    st.image(book["thumbnail"], width=85)
                else:
                    st.write("📖")
            with cols[1]:
                st.markdown(f"<div class='book-title'>{book['title']}</div>", unsafe_allow_html=True)
                meta = " / ".join([x for x in [book.get("authors"), book.get("publisher"), book.get("publishedDate")] if x])
                st.markdown(f"<div class='book-meta'>{meta}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='book-meta'>ISBN: {book['isbn']}</div>", unsafe_allow_html=True)
                if st.button(f"この本で確認する", key=f"select_{idx}"):
                    st.session_state.selected_book = book
            st.markdown("</div>", unsafe_allow_html=True)

book = st.session_state.selected_book
if book:
    st.subheader("選択中の本")
    st.write(f"**{book['title']}**")
    if book.get("authors"):
        st.write(book["authors"])
    st.write(f"ISBN: `{book['isbn']}`")

    st.link_button("メルカリで見る", build_mercari_url(book))
    st.link_button("Amazonで確認", build_amazon_url(book))

    if st.button("5区図書館を確認", type="primary"):
        with st.spinner("カーリルで蔵書状況を確認中... 数秒かかることがあります"):
            try:
                calil_data = check_calil(book["isbn"])
                rows = summarize_library_status(calil_data or {})
                st.session_state.library_rows = rows
            except Exception as e:
                st.error(f"カーリル検索でエラーが発生しました: {e}")

if st.session_state.get("library_rows"):
    st.subheader("図書館の状況")
    for row in st.session_state.library_rows:
        icon = "✅" if row["has_available"] else ("📚" if row["has_collection"] else "—")
        st.markdown(f"### {icon} {row['name']}")
        st.write(f"状態: {row['status']}")
        if row["libraries"]:
            for item in row["libraries"][:12]:
                st.write(f"- {item}")
        else:
            st.write("蔵書情報なし、または確認できませんでした。")
        if row.get("reserveurl"):
            st.link_button(f"{row['name']}の予約・詳細ページを開く", row["reserveurl"])

st.markdown("---")
st.caption("iPhoneではSafariでこのページを開き、共有ボタン → ホーム画面に追加、でアプリ風に使えます。")
