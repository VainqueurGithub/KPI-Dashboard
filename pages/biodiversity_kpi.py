from core.connection import psy_connection, st_connection
import streamlit as st

# Get the connection object
conn = st_connection()

if st.session_state.st_conn:
    st.write("Database is connected ✅")
    # Example query
    # df = conn.query("SELECT * FROM my_table;", ttl=0)
    # st.dataframe(df)
else:
    pass
