import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

st.set_page_config(page_title="Dash", page_icon=":bar_chart:", layout="wide")

database_url = os.getenv("DATABASE_URL", "")

st.title("Hi Morten")
st.write("This placeholder will become the OpenClaw habit dashboard.")

status_label = "Configured" if database_url else "Running without database"

left, right = st.columns(2)

with left:
    st.metric("App status", "Running")

with right:
    st.metric("Database", status_label)

st.subheader("Preview")

sample = pd.DataFrame(
    [
        {"habit": "Morning review", "status": "planned"},
        {"habit": "Daily check-in", "status": "planned"},
        {"habit": "Weekly reflection", "status": "planned"},
    ]
)

st.dataframe(sample, use_container_width=True, hide_index=True)
