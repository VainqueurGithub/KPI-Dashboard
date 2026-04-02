import streamlit as st

conn = st.connection("postgresql", type='sql')

def init_auth():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None


def validate_login(username, email):
    result = conn.query( """ SELECT 1 FROM redd_project.grievance_user WHERE user_id = :user_id AND email = :email
    LIMIT 1
    """,
    params={
        "user_id": username,
        "email": email
    })
    return not result.empty


def require_login():
    if st.session_state.logged_in:
        return

    @st.dialog("🔐 Login Required")
    def login_dialog():
        username = st.text_input("Username")
        email = st.text_input("Email")

        if st.button("Login"):
            try:
                if validate_login(username, email):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login successful ✅")
                    st.rerun()
                else:
                    st.error("Invalid credentials ❌")
            except Exception as e:
                st.error(f"Check your database connection or VPN : {e}")
    login_dialog()
    st.stop()
