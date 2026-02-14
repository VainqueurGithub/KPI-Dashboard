#- Importing useful libraries
import streamlit as st
import pandas as pd
from streamlit_card import card
from streamlit_extras.metric_cards import style_metric_cards
import plotly.express as px
import altair as alt
from streamlit_folium import st_folium
from shapely.geometry import mapping
from datetime import datetime,date
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from streamlit.components.v1 import html
import ssl
from twilio.rest import Client

# Setting page configuration
st.set_page_config(
    page_title="Grievance dashbord",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)
#-------------------------------
# FUNCTIONS
#-------------------------------

# Insert resolution into database
def save_resolution(grievance_id, responder_name, response_text, date_response, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO redd_project.resolutions
        (grievance_id, resolved_by, resolution_text, date_resolved, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (grievance_id, responder_name, response_text, date_response, status))
    conn.commit()
    cur.close()

#Send email notification
def send_email(sender, password, receiver, smtp_server, smtp_port, html_content, subject):
    try:
        msg = EmailMessage()
        msg["To"] = receiver
        msg["From"] = sender
        msg["Subject"] = subject
        # Plain-text fallback
        msg.set_content("This email contains HTML content. Please use an HTML-compatible email client.")

        # HTML version
        msg.add_alternative(html_content, subtype="html")
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender, password)
            server.send_message(msg)
    except Exception as e:
        print("Email error:", e)
#Build in the HTML email notification
def build_email_html(notification_html,responder_name,grievance_ref,village,status,resolution_text,project_name):
    with open(notification_html, "r", encoding="utf-8") as f:
        html_template = f.read()

    return html_template.format(
        responder_name=responder_name,
        grievance_ref=grievance_ref,
        village=village,
        status=status,
        resolution_text=resolution_text,
        project_name=project_name,
    )

################################
# --- INITIALIZE CONNECTION ---#
################################
# Cache the connection so it's reused
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="10.5.2.130",
        port="5432",
        database="dianfossey",
        user="vainqueur",
        password="BWLCMmpdva@10",
        cursor_factory=RealDictCursor
    )
conn = st.connection("postgresql", type='sql')

grievances = conn.query( "SELECT *  FROM redd_project.grievances as g", ttl="10m")
resolutions = conn.query( "SELECT grievance_date,date_resolved,resolution_days,g.status,urgency_level," \
"village  FROM redd_project.grievances as g " \
"LEFT JOIN redd_project.resolutions as s ON s.grievance_id=g.grievance_id", ttl="10m")
user_profile = conn.query("SELECT user_id,role_user,gu.email as email,id_personne,nom,prenom " \
"FROM redd_project.grievance_user as gu JOIN ressources_humaines.employe e ON gu.user_id=e.id_personne", ttl="10m")
# Side option

######################
#--- SUB MENU -------#
######################
submenu = st.sidebar.selectbox(
    "GRM Monitoring",
    ["Dashboard", "Active grievances", "Notifications Log"]
)

grievances['year'] = grievances['grievance_date'].dt.year
resolutions['year'] = grievances['grievance_date'].dt.year
df_villag_gr = grievances[['village', 'urgency_level']]
villages = df_villag_gr['village']
villages.loc[-1] = ''
villages.index = villages.index + 1  # shifting index
villages.sort_index(inplace=True) 

if submenu=="Dashboard":
    chart_type = st.sidebar.radio(
        "Select chart type",
        ["Total grievance by village", "By severity (stacked)"]
    )
    reporting_year = st.sidebar.selectbox("Reporting year:",options=grievances['year'].unique())
    reporting_village = st.sidebar.selectbox("Reporting village:",options=villages.unique())
    # Filter by year
    grievances = grievances.loc[grievances['year']==reporting_year]
    resolutions = resolutions.loc[resolutions['year']==reporting_year]
    # Filter by village
    if reporting_village!='':
        grievances = grievances.loc[grievances['village']==reporting_village]
        resolutions = resolutions.loc[resolutions['village']==reporting_village]


###########################
# --- PERFORM QUERIES ----#
###########################
# CARDS METRICS QUERIES
nbre_grievance = grievances['grievance_id'].nunique()
total_resolved = grievances.loc[grievances['status']=='Resolved', 'grievance_id'].nunique()
perc_resolved = round((total_resolved/nbre_grievance)*100)
high_urgency = grievances.loc[grievances['urgency_type']=='High', 'grievance_id'].nunique()
is_open = grievances.loc[grievances['status']=='Open', 'grievance_id'].nunique()
under_invest = grievances.loc[grievances['status']=='Under Investigation', 'grievance_id'].nunique()
avg_time = round(grievances['resolution_days'].sum()/total_resolved)
# PIE CHART TOTAL SUBMISSION BY CLASSIFICATION & GENDER
complainant_gender = pd.DataFrame({
    'gender':['Male', 'Female'],
    'count':[grievances.loc[grievances['complainant_gender']=='Male', 'grievance_id'].nunique(), grievances.loc[grievances['complainant_gender']=='Female', 'grievance_id'].nunique()]
})

complaint_category = pd.DataFrame({
    'classification' :['Safeguards & Human Rights', 'Project Implementation & Benefit sharing', 'Illigal Activity',
                           'Land and resource use, rights or restrictions', 'Positive Feedback, Suggestions, Questions',
                           'Financial Management & Fraud', 'Staff Misconduct'],
    'values' :[grievances.loc[grievances['category']=='Project Implementation and Benefit sharing', 'grievance_id'].nunique(),
               grievances.loc[grievances['category']=='Land and resource use and rights or restrictions', 'grievance_id'].nunique(),
               grievances.loc[grievances['category']=='Positive Feedback or Suggestions or Questions', 'grievance_id'].nunique(),
               grievances.loc[grievances['category']=='Illegal Activity', 'grievance_id'].nunique(),
               grievances.loc[grievances['category']=='Safeguards and Human Rights', 'grievance_id'].nunique(),
               grievances.loc[grievances['category']=='Staff Misconduct', 'grievance_id'].nunique(),
               grievances.loc[grievances['category']=='Financial Management and Fraud', 'grievance_id'].nunique()]
})

#PLOT BAR GRIEVANCES BY SEVERITY AND URGENCY
complaint_severity = pd.DataFrame({
    'urgency':[0,1,2,3,4],
    'count': [grievances.loc[grievances['urgency_level']=='Positive feedback or Suggestions or Questions', 'grievance_id'].nunique(),
              grievances.loc[grievances['urgency_level']=='Request for assistance or minor complaint', 'grievance_id'].nunique(),
              grievances.loc[grievances['urgency_level']=='Dissatisfaction with project activities or staff or operations', 'grievance_id'].nunique(),
              grievances.loc[grievances['urgency_level']=='Serious allegations in relation to action or inaction or verbal abuse or theft', 'grievance_id'].nunique(),
              grievances.loc[grievances['urgency_level']=='Alleged human rights violations - high safety risk', 'grievance_id'].nunique()
              ]
})

#PLOT BAR GRIEVANCES BY VILLAGE
df_village = grievances[['village', 'urgency_level']]
    
  
urgency_dict = {'Dissatisfaction with project activities or staff or operations':2, 
                'Alleged human rights violations - high safety risk':4,
                'Request for assistance or minor complaint':1,
                'Positive feedback or Suggestions or Questions':0,
                'Serious allegations in relation to action or inaction or verbal abuse or theft':3}
df_village['urgency_level'] = df_village['urgency_level'].map(urgency_dict)


######################
# --- KPIs cards --- #
######################

def cards(nbre_grievance, perc_resolved, avg_time, high_urgency, is_open, under_invest):
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(label="Total grievances received", value=nbre_grievance)
    col2.metric(label="% resolved", value=perc_resolved)
    col3.metric(label="Average resolution day", value=avg_time)
    col4.metric(label="High-urgency cases", value=high_urgency)
    col5.metric(label="Open", value=is_open)
    col6.metric(label="Under investigation", value=under_invest)

    style_metric_cards()

if submenu=='Dashboard':
    #####################
    # --- Cards --------#
    #####################
    cards(nbre_grievance,perc_resolved,avg_time,high_urgency,is_open,under_invest)
    ###################
    # --- Charts --- #
    ###################
    pie_chart1, pie_chart2 = st.columns(2)
 
    # Create Total submission by classification pie figure

    with pie_chart1:
        fig = px.pie(
            complaint_category,
            values='values',
            names='classification',
            title='Total submission by classification',
            hole=0.4
        )

        fig.update_traces(textinfo='percent+label', pull=[0.1,0,0,0,0,0,0])
        fig.update_layout(legend_title_text = 'Classes', title_x=0.5)
        #Display the pie chart into streamlit app
        st.plotly_chart(fig, use_container_width=True)

    #---- Plot grievance submission by gender

    with pie_chart2:
        # Create Total submission by gender pie figure
        fig = px.pie(
            complainant_gender,
            values='count',
            names='gender',
            title='Total submission by gender',
            hole=0.4
        )

        fig.update_traces(textinfo='percent+label', pull=[0.1,0])
        fig.update_layout(legend_title_text = 'Genders', title_x=0.5)
        #Display the pie chart into streamlit app
        st.plotly_chart(fig, use_container_width=True)


    # Create Stackbart plot for severity

    df_severity = complaint_severity

    def map_severity(u):
        if u in [0,1]:
            return "Low"
        elif u == 2:
            return "Medium"
        elif u in [3,4]:
            return "High"
    
    df_severity['severity'] = df_severity["urgency"].apply(map_severity)
    ########################################
    #--- Calculate % of Total grievance ---#
    ########################################
    total = df_severity['count'].sum()
    df_severity['percent_total'] = (df_severity["count"]/total)*100

    ##################################
    #--- Order severity & urgency ---#
    ##################################
    severity_order = ["Low", "Medium", "High"]
    urgency_order = [0,1,2,3,4]
    df_severity['severity'] = pd.Categorical(
        df_severity['severity'], categories=severity_order, ordered=True
    )

    df_severity['urgency'] = pd.Categorical(
        df_severity['urgency'], categories=urgency_order, ordered=True
    )

    #######################################
    #--- Color mapping (risk gradient) ---#
    #######################################
    color_map = {
        0:"#1a9850",
        1:"#91cf60",
        2:"#fdae61",
        3:"#d73027",
        4:"#7f0000"
    }
    
    ########################################
    #----------------- Plot ---------------# 
    ########################################

    fig = px.bar(
        df_severity,
        x="severity",
        y="percent_total",
        color="urgency",
        color_discrete_map=color_map,
        text = df_severity["percent_total"].round(1).astype(str) + "%",
        labels={
            "severity": "severity Level",
            "percent_total": "Percentage of Total Grievances (%)",
            "urgency": "Urgency Score"
        },
        title = "Distribution of Grievances by Severity and Urgency (% of TOTAL)"
    )

    #################################
    #------- Layout tuning ---------#
    #################################
    fig.update_layout(
        barmode = "stack",
        yaxis = dict(range=[0,100]),
        xaxis = dict(categoryorder="array", categoryarray=severity_order),
        legend_title_text = "Urgency Level",
        template = "simple_white"
    )

    fig.update_traces(textposition="inside")
    fig.update_layout(legend_title_text = 'Grade', title_x=0.5)
    ######################################
    #-------- Streamlit Display ---------#
    ######################################
    st.plotly_chart(fig, use_container_width=True)

    ####################################################
    #----------------Grievance by Village -------------#
    ####################################################
    
    # --- Map urgency -> Severity

    df_village["severity"] = df_village["urgency_level"].apply(map_severity)
    severity_order = ["Low", "Medium", "High"]

    

    ######################################################## 
    #----- OPT 1: SIMPLE BAR: TOTAL PER VILLAGE -----------#
    ########################################################
    if chart_type == "Total grievance by village":
        village_counts = (
            df_village.groupby("village").size().reset_index(name="count").sort_values("count", ascending=False)
        )
        
        chart = alt.Chart(village_counts).mark_bar().encode(
            x=alt.X('village', sort='-y'),
            y='count',
            tooltip=['village', 'count']
        ).properties(title="Grievance by Village")
        fig = st.altair_chart(chart, use_container_width=True)
    ######################################################
    #------ OPT 2: STACKED BAR: VILLAGE * SEVERITY ------#
    ######################################################
    else:
        village_severity = (
            df_village.groupby(["village", "severity"]).size().reset_index(name="count")
        )

        fig = px.bar(
            village_severity,
            x="village",
            y="count",
            color = "severity",
            category_orders = {"severity": severity_order},
            color_discrete_map={
                "Low": "#91cf60",
                "Medium":"#fdae61",
                "High":"#d73027"
            },
            labels={
                "village": "Village",
                "count": "Number of Grievances",
                "severity": "Severity Level"
            },
            title="Grievance by Village and Severity"
        )

        fig.update_layout(
            barmode="stack",
            template = "simple_white",
            xaxis_tickangle = -45
        )

        # Display
        st.plotly_chart(fig, use_container_width=True)

##############################
# Responses Analysis plots
##############################    

    # Convert dates
    resolutions['grievance_date'] = pd.to_datetime(resolutions['grievance_date'])
    resolutions['date_resolved'] = pd.to_datetime(resolutions['date_resolved'])

    # Fill unresolved resolution_time_days with NaN
    resolutions['resolution_days'] = pd.to_numeric(resolutions['resolution_days'], errors='coerce')

    # --------------------------
    # 1. Histogram of resolution times
    # --------------------------
    fig_hist = px.histogram(
        resolutions[resolutions['status'] == 'Resolved'],
        x='resolution_days',
        nbins=20,
        title="Distribution of Resolution Time (Days)",
        labels={'resolution_days': 'Resolution Time (days)'},
        color='urgency_level',  # optional color by urgency
        barmode='overlay'
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # --------------------------
    # 2. Box plot by urgency
    # --------------------------
    fig_box = px.box(
        resolutions[resolutions['status'] == 'Resolved'],
        x='urgency_level',
        y='resolution_days',
        title="Resolution Time by Urgency Level",
        labels={'urgency_level': 'Urgency Level', 'resolution_days': 'Resolution Time (days)'},
        color='urgency_level'
    )
    st.plotly_chart(fig_box, use_container_width=True)

    # --------------------------
    # 3. Average resolution by village
    # --------------------------
    avg_village = resolutions[resolutions['status'] == 'Resolved'].groupby('village')['resolution_days'].mean().reset_index()

    fig_bar = px.bar(
        avg_village,
        x='village',
        y='resolution_days',
        title="Average Resolution Time by Village",
        labels={'resolution_days': 'Avg Resolution Time (days)'},
        color='resolution_days',
        color_continuous_scale='Viridis'
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --------------------------
    # 4. SLA compliance line chart (<=7 days)
    # --------------------------
    df_sorted = resolutions[resolutions['status'] == 'Resolved'].sort_values('date_resolved')
    df_sorted['SLA_met'] = df_sorted['resolution_days'] <= 7
    df_sorted['cum_SLA_percent'] = df_sorted['SLA_met'].cumsum() / range(1, len(df_sorted)+1) * 100

    fig_sla = px.line(
        df_sorted,
        x='date_resolved',
        y='cum_SLA_percent',
        title="Cumulative SLA Compliance Over Time",
        labels={'cum_SLA_percent': '% of Resolved ≤ 7 Days', 'date_resolved': 'Resolution Date'}
    )
    st.plotly_chart(fig_sla, use_container_width=True)

elif submenu=='Active grievances':
    st.session_state.clear()   # optional but recommended
    st.switch_page("pages/login.py")  # <-- this will redirect!
    