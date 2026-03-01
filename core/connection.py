# db_connection.py
import streamlit as st
import streamlit.components.v1 as components
import psycopg2
from psycopg2.extras import RealDictCursor
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # go up from core/ to project root
img_path = os.path.join(BASE_DIR, "static", "logo", "connection_database_failed.jpeg")

@st.dialog("❌ Connection to database failed")
def show_db_popup():
    st.image(img_path, width=200)
    # Manual retry button
    if st.button("🔁 Reconnect"):
        try:
            st.session_state.psyc_conn = psy_try_connect()
            st.rerun()
        except Exception:
            st.session_state.psyc_conn = None

# ---------------------
# Psycopg2 Connection
# ---------------------
@st.cache_resource
def psy_try_connect(host="10.5.2.130", port="5432", database="dianfossey", 
                    user="vainqueur", password="BWLCMmpdva@10"):
    return psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        cursor_factory=RealDictCursor
    )

# ---------------------
# Streamlit Connection
# ---------------------
@st.cache_resource
def st_try_connect():
    """Attempt to connect to PostgreSQL and return the connection object."""
    with st.spinner("Connecting to database..."):
        conn = st.connection("postgresql", type="sql")
        conn.query("SELECT 1;", ttl=0)  # test query
    return conn


def st_connection():
    """Manage connection with auto-retry and UI feedback. Returns conn object or None."""
    
    # --- Auto-refresh to enable automatic retries ---
    # --- Initialize session state ---
    if "st_conn" not in st.session_state:
        st.session_state.st_conn = None

    if st.session_state.st_conn is None:
        try:
            st.session_state.st_conn = st_try_connect()
        except Exception:
            st.session_state.st_conn = None

    # --- UI Rendering ---
    if st.session_state.st_conn:
        return st.session_state.st_conn  # Return the active connection

    else:
        show_db_popup()
        st.stop()
    


# ---------------------
# Unified psycopg2 retry function
# ---------------------
def psy_connection():
    """
    Retry psycopg2 connection with popup and manual retry button.
    Returns psycopg2 connection object or None.
    """
    if "psyc_conn" not in st.session_state:
        st.session_state.psyc_conn = None
    
    if st.session_state.psyc_conn is None:
        try:
            st.session_state.psyc_conn = psy_try_connect()
        except Exception:
            st.session_state.psyc_conn = None

    if st.session_state.psyc_conn:
        return st.session_state.psyc_conn

    else:
        show_db_popup()
        st.stop()
        