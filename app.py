import streamlit as st
import pandas as pd
import numpy as np
import time

# DEFINES PAGES
rdd_page = st.Page("pages/rdd_kpi.py", title='REDD+')
coco_page = st.Page("pages/coco_kpi.py", title='COCO KPI')
gorilla_page = st.Page("pages/gorilla_kpi.py", title='GORILLA KPI')
biodiversity_page = st.Page("pages/biodiversity_kpi.py", title='BIODIVERSITY KPI')
grievance_page = st.Page("pages/grievance_dashbord.py", title='GRM Monitoring')

# Set up navigation
pg = st.navigation([rdd_page, coco_page, gorilla_page, biodiversity_page, grievance_page])

# Run the selected page
pg.run()
