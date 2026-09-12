"""
ArchitectAI - Streamlit Web UI
==============================

Müştəri üçün vizual interfeys.

İstifadə:
    streamlit run streamlit_app.py
"""

import streamlit as st

from app.core.refactor_engine import RefactorEngine


# ============================================================
# Səhifə Konfiqurasiyası
# ============================================================
st.set_page_config(
    page_title="ArchitectAI",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Nümunə Kod
# ============================================================
DEFAULT_CODE = '''import os
import sqlite3

password = "admin123"


def login(user_input):
    result = eval(user_input)
    os.system("ls " + user_input)
    return result


def get_user(user_id):
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()
'''


# ============================================================
# Session State
# ============================================================
if "result" not in st.session_state:
    st.session_state.result = None


# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.title("⚙️ Settings")

    model = st.selectbox(
        "LLM Model",
        ["qwen2.5:7b-16k", "qwen2.5:7b", "llama3.2:latest"],
        index=0,
        help="Local model used for refactoring",
    )

    st.markdown("---")
    st.markdown("### 🔒 Privacy")
    st.success("100% Local — No data leaves your machine")

    st.markdown("### 📊 Stats")
    st.caption(f"**Version:** 0.1.0")
    st.caption(f"**License:** MIT")
    st.caption(f"**Model:** {model}")

    st.markdown("---")
    st.markdown("### 🔗 Links")
    st.markdown("[GitHub](https://github.com/SrTural/architect-ai)")
    st.markdown("[LinkedIn](https://linkedin.com/in/dadashovvh)")


# ============================================================
# Başlıq
# ============================================================
st.title("🏛️ ArchitectAI")
st.markdown(
    "**Local-first AI-powered legacy code refactoring engine.**  "
    "Transforms insecure code into modern, secure architecture — 100% on-premise."
)
st.markdown("---")


# ============================================================
# Input Bölməsi
# ============================================================
st.subheader("📥 Input: Legacy Code")

col_input, col_button = st.columns([4, 1])

with col_input:
    code_input = st.text_area(
        "Paste your legacy Python code:",
        value=DEFAULT_CODE,
        height=300,
        label_visibility="collapsed",
    )

with col_button:
    st.markdown("### Actions")
    refactor_btn = st.button(
        "🚀 Refactor",
        type="primary",
        use_container_width=True,
    )
    clear_btn = st.button("🗑️ Clear", use_container_width=True)

    if clear_btn:
        st.session_state.result = None
        st.rerun()


# ============================================================
# Refactor Məntiqi
# ============================================================
if refactor_btn:
    if not code_input.strip():
        st.error("❌ Code cannot be empty.")
    else:
        with st.spinner("🤖 AI is refactoring your code..."):
            try:
                engine = RefactorEngine(model=model)
                result = engine.refactor(code_input)
                st.session_state.result = result
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.session_state.result = None


# ============================================================
# Nəticə Bölməsi
# ============================================================
if st.session_state.result:
    result = st.session_state.result

    # ==== Uğur Mesajı ====
    if result["valid_syntax"]:
        st.success(f"✅ Refactoring complete — {result['attempts']} attempt(s)")
    else:
        st.warning(f"⚠️ Syntax errors remained after {result['attempts']} attempt(s)")

    st.markdown("---")

    # ==== Statistika ====
    st.subheader("📈 Statistics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Valid Syntax",
        "✅ Yes" if result["valid_syntax"] else "❌ No",
    )
    m2.metric("Attempts", result["attempts"])
    m3.metric("Old Lines", len(result["old_code"].splitlines()))
    m4.metric("New Lines", len(result["new_code"].splitlines()))

    st.markdown("---")

    # ==== Əvvəl / Sonra ====
    st.subheader("📊 Before vs After")

    col_before, col_after = st.columns(2)

    with col_before:
        st.markdown("#### 🔴 Before (Legacy)")
        st.code(result["old_code"], language="python")

    with col_after:
        st.markdown("#### 🟢 After (AI-Refactored)")
        st.code(result["new_code"], language="python")

    st.markdown("---")

    # ==== Download ====
    col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
    with col_dl1:
        st.download_button(
            label="📥 Download .py",
            data=result["new_code"],
            file_name="refactored.py",
            mime="text/x-python",
            use_container_width=True,
        )
    with col_dl2:
        st.download_button(
            label="📥 Download .json",
            data=str(result),
            file_name="report.json",
            mime="application/json",
            use_container_width=True,
        )


# ============================================================
# Footer
# ============================================================
st.markdown("---")
st.caption(
    "🏛️ **ArchitectAI** • Local-first • Zero data exfiltration • MIT License • © 2026"
)