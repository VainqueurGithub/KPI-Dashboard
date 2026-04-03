#- Importing useful libraries
import streamlit as st
import pandas as pd
from streamlit_card import card
from streamlit_extras.metric_cards import style_metric_cards
import plotly.express as px
import altair as alt
from datetime import date
import smtplib
from email.message import EmailMessage
import ssl
from login import init_auth, require_login
from core.connection import st_connection, psy_try_connect
import os
import uuid
import requests

UPLOAD_FOLDER = "static/proof"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # creates folder if it doesn’t exist


if 'st_conn' not in st.session_state:
    pass
init_auth()
require_login()

       
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if 'conn' not in st.session_state:
    st.session_state.conn = psy_try_connect()
    
# Setting page configuration
st.set_page_config(
    page_title="Grievance dashbord",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)
#-------------------------------
# FUNCTIONS
#-------------------------------

@st.dialog("View document details", width='medium')
def preview_document(preview_path):

    if preview_path.lower().endswith((".png", ".jpg", ".jpeg")):
        try:
            st.image(preview_path)
        except Exception as e:
            st.error(f"Image file not fund: {e}")
    elif preview_path.lower().endswith(".pdf"):
        try:
            st.pdf(preview_path)
        except Exception as e:
            st.error(f"PDF file not fund: {e}")
        
 
# Emoji or HTML icons for PDF / Image
def file_icon(file_path):
    if not isinstance(file_path, str):
        return "❓"  # fallback if file_path is not a string
    file_path = file_path.lower()
    if file_path.endswith((".png", ".jpg", ".jpeg")):
        return "🖼️"
    elif file_path.endswith(".pdf"):
        return "📄"
    else:
        return "❓"

def save_file(uploaded_file):
    BASE_URL = UPLOAD_FOLDER+"/"
    ext = uploaded_file.name.split(".")[-1]
    unique_name = f"{uuid.uuid4()}.{ext}"
    
    file_path = os.path.join(UPLOAD_FOLDER, unique_name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return BASE_URL+unique_name


# Insert resolution into database
def save_resolution(id_user, resolution, resolution_date, status, id_complaint, response_image_link, response_pdf_link):
    conn = st.session_state.conn
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO redd_project.resolutions
                    (id_user, resolution, resolution_date, status, id_complaint, response_image_link, response_pdf_link)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (id_user, resolution, resolution_date, status, id_complaint, response_image_link, response_pdf_link))
    conn.commit()
    
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
    return psy_try_connect()
    
conn = st_connection()

try:
    grievances = conn.query("SELECT *  FROM redd_project.grievances as g", ttl="2m")
    resolutions = conn.query("SELECT response_image_link, response_pdf_link, id_complaint,complaint_date,resolution,resolution_date,resolution_days,g.status,urgency_level,s.id," \
    "village  FROM redd_project.grievances as g " \
    "LEFT JOIN redd_project.resolutions as s ON s.id_complaint=g.reference_number", ttl="30s")
    user_profile = conn.query("SELECT user_id,role_user,gu.email as email,id_personne,nom,prenom " \
    "FROM redd_project.grievance_user as gu JOIN ressources_humaines.employe e ON gu.user_id=e.id_personne", ttl="2m")
    # Side option

    ######################
    #--- SUB MENU -------#
    ######################
    submenu = st.sidebar.selectbox(
        "GRM Monitoring",
        ["Dashboard", "Active grievances", "Notifications Log"]
    )

    grievances['year'] = pd.to_datetime(grievances['complaint_date']).dt.year
    resolutions['year'] = pd.to_datetime(grievances['complaint_date']).dt.year
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
        nbre_grievance = grievances['id'].nunique()
        total_resolved = grievances.loc[grievances['status']=='Resolved', 'id'].nunique()
        perc_resolved = round((total_resolved/nbre_grievance)*100)
        high_urgency = grievances.loc[grievances['urgency_type']=='High', 'id'].nunique()
        is_open = grievances.loc[grievances['status']=='Open', 'id'].nunique()
        under_invest = grievances.loc[grievances['status']=='Under Investigation', 'id'].nunique()
        if total_resolved==0:
            avg_time = "No grievance resolved yet"
        else:
            avg_time = round(grievances['resolution_days'].sum()/total_resolved)
        # PIE CHART TOTAL SUBMISSION BY CLASSIFICATION & GENDER & ACCUSED CATEGORY
        complainant_gender = pd.DataFrame({
            'gender':['Male', 'Female', 'Other'],
            'count':[grievances.loc[grievances['sex']=='Male', 'id'].nunique(), grievances.loc[grievances['sex']=='Female', 'id'].nunique(),
                     grievances.loc[grievances['sex']=='Other', 'id'].nunique()]
        })

        accused_category = pd.DataFrame({
            'category':['Staff', 'External', 'DFGF', 'Other'],
            'count':[grievances.loc[grievances['accused_category']=='Staff', 'id'].nunique(),
                     grievances.loc[grievances['accused_category']=='External', 'id'].nunique(),
                     grievances.loc[grievances['accused_category']=='DFGF', 'id'].nunique(),
                     grievances.loc[grievances['accused_category']=='Other', 'id'].nunique()]
        })

        method_complaint = pd.DataFrame({
            'method':['Suggestion Box', 'Verbal to Focal Point', 'Verbal to Mere Chief', 'Letter to Focal Point', 'Letter to Mere Chief'],
            'count':[grievances.loc[grievances['method_of_complaint']=='Suggestion Box', 'id'].nunique(),
                     grievances.loc[grievances['method_of_complaint']=='Verbal to Focal Point', 'id'].nunique(),
                     grievances.loc[grievances['method_of_complaint']=='Verbal to Mere Chief', 'id'].nunique(),
                     grievances.loc[grievances['method_of_complaint']=='Letter to Focal Point', 'id'].nunique(),
                     grievances.loc[grievances['method_of_complaint']=='Letter to Mere Chief', 'id'].nunique()]
        })

        complaint_category = pd.DataFrame({
            'classification' :['Safeguards & Human Rights', 'Project Implementation & Benefit sharing', 'Illigal Activity',
                                   'Land and resource use, rights or restrictions', 'Positive Feedback, Suggestions, Questions',
                                   'Financial Management & Fraud', 'Staff Misconduct'],
            'values' :[grievances.loc[grievances['category']=='Project Implementation and Benefit sharing', 'id'].nunique(),
                       grievances.loc[grievances['category']=='Land and resource use and rights or restrictions', 'id'].nunique(),
                       grievances.loc[grievances['category']=='Positive Feedback or Suggestions or Questions', 'id'].nunique(),
                       grievances.loc[grievances['category']=='Illegal Activity', 'id'].nunique(),
                       grievances.loc[grievances['category']=='Safeguards and Human Rights', 'id'].nunique(),
                       grievances.loc[grievances['category']=='Staff Misconduct', 'id'].nunique(),
                       grievances.loc[grievances['category']=='Financial Management and Fraud', 'id'].nunique()]
        })

        #PLOT BAR GRIEVANCES BY SEVERITY AND URGENCY
        complaint_severity = pd.DataFrame({
            'urgency':["Positive feedback, Suggestions or Questions",
                             "Request for assistance or minor complaint",
                             "Dissatisfaction with project activities, staff or operations",
                             "Serious allegations in relation to action or inaction, verbal abuse, theft",
                             "Alleged human rights violations - high safety risk"],
            'count': [grievances.loc[grievances['urgency_level']=='Positive feedback or Suggestions or Questions', 'id'].nunique(),
                      grievances.loc[grievances['urgency_level']=='Request for assistance or minor complaint', 'id'].nunique(),
                      grievances.loc[grievances['urgency_level']=='Dissatisfaction with project activities or staff or operations', 'id'].nunique(),
                      grievances.loc[grievances['urgency_level']=='Serious allegations in relation to action or inaction or verbal abuse or theft', 'id'].nunique(),
                      grievances.loc[grievances['urgency_level']=='Alleged human rights violations - high safety risk', 'id'].nunique()
                      ]
        })

        #PLOT BAR GRIEVANCES BY VILLAGE
        df_village = grievances[['village', 'urgency_level']]
    
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
                    title='Grievance by classification',
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
                    title='Grievance by gender',
                    hole=0.4
                )
    
                fig.update_traces(textinfo='percent+label', pull=[0.1,0])
                fig.update_layout(legend_title_text = 'Genders', title_x=0.5)
                #Display the pie chart into streamlit app
                st.plotly_chart(fig, use_container_width=True)

            pie_chart3, pie_chart4 = st.columns(2)
            # ---- Plot accused catogory ----- #
            with pie_chart3:
                fig = px.pie(
                    accused_category,
                    values='count',
                    names='category',
                    title='Grievance accused category',
                    hole=0.4
                )
    
                fig.update_traces(textinfo='percent+label', pull=[0.1,0,0,0])
                fig.update_layout(legend_title_text = 'Accused Category', title_x=0.5)
                #Display the pie chart into streamlit app
                st.plotly_chart(fig, use_container_width=True)
                
           # ---- Plot for method of submitting complaint ----#
            with pie_chart4:
                fig = px.pie(
                    method_complaint,
                    values='count',
                    names='method',
                    title='Grievance method of submission',
                    hole=0.4
                )
    
                fig.update_traces(textinfo='percent+label', pull=[0.1,0,0,0,0])
                fig.update_layout(legend_title_text = 'Method of submission', title_x=0.5)
                #Display the pie chart into streamlit app
                st.plotly_chart(fig, use_container_width=True)
           

            # Create Stackbart plot for severity

            df_severity = complaint_severity

            def map_severity(u):
                if u in ["Positive feedback, Suggestions or Questions","Request for assistance or minor complaint"]:
                    return "Low"
                elif u == "Dissatisfaction with project activities, staff or operations":
                    return "Medium"
                elif u in ["Serious allegations in relation to action or inaction, verbal abuse, theft","Alleged human rights violations - high safety risk"]:
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
            urgency_order = ["Positive feedback, Suggestions or Questions",
                             "Request for assistance or minor complaint",
                             "Dissatisfaction with project activities, staff or operations",
                             "Serious allegations in relation to action or inaction, verbal abuse, theft",
                             "Alleged human rights violations - high safety risk"]
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
                "Positive feedback, Suggestions or Questions":"#1a9850",
                "Request for assistance or minor complaint":"#91cf60",
                "Dissatisfaction with project activities, staff or operations":"#fdae61",
                "Serious allegations in relation to action or inaction, verbal abuse, theft":"#d73027",
                "Alleged human rights violations - high safety risk":"#7f0000"
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
                    df_village.groupby(["village", "urgency_level"]).size().reset_index(name="count")
                )
                fig = px.bar(
                    village_severity,
                    x="village",
                    y="count",
                    color = "urgency_level",
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
            resolutions['complaint_date'] = pd.to_datetime(resolutions['complaint_date'])
            resolutions['resolution_date'] = pd.to_datetime(resolutions['resolution_date'])

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
            df_sorted = resolutions[resolutions['status'] == 'Resolved'].sort_values('resolution_date')
            df_sorted['SLA_met'] = df_sorted['resolution_days'] <= 7
            df_sorted['cum_SLA_percent'] = df_sorted['SLA_met'].cumsum() / range(1, len(df_sorted)+1) * 100

            fig_sla = px.line(
                df_sorted,
                x='resolution_date',
                y='cum_SLA_percent',
                title="Cumulative Compliance Over Time",
                labels={'cum_SLA_percent': '% of Resolved ≤ 7 Days', 'date_resolved': 'Resolution Date'}
            )
            st.plotly_chart(fig_sla, use_container_width=True)

    elif submenu=='Active grievances':
        # -------------------------
        # Load grievances
        # -------------------------
        df =conn.query("SELECT id, reference_number, category, urgency_level, status, details, village, complaint_date, id_user, image_link  FROM redd_project.grievances")

        # Sidebar filters
        st.sidebar.title("Filter Grievances")
        status_filter = st.sidebar.selectbox("Status", options=["All"] + df['status'].unique().tolist())
        village_filter = st.sidebar.selectbox("Village", options=["All"] + df['village'].unique().tolist())

        filtered_df = df.copy()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]
        if village_filter != "All":
            filtered_df = filtered_df[filtered_df['village'] == village_filter]

        # Select a grievance
        grievance_id = st.selectbox("Select Grievance ID", filtered_df['id'])
        grievance_ref = filtered_df['reference_number'].loc[filtered_df['id']==grievance_id].iloc[0]
        grievance_village = filtered_df['village'].loc[filtered_df['id']==grievance_id].iloc[0]
        grievance_entered_by = filtered_df['id_user'].loc[filtered_df['id']==grievance_id].iloc[0]
        # Show grievance details
        grievance = df[df['id'] == grievance_id].iloc[0]
        st.subheader(f"Grievance #{grievance['reference_number']} Submitted on {grievance['complaint_date']}")
        st.write(f"**Category:** {grievance['category']}")
        st.write(f"**Urgency:** {grievance['urgency_level']}")
        st.write(f"**Status:** {grievance['status']}")
        st.write(f"**Village:** {grievance['village']}")
        st.write(f"**Description:** {grievance['details']}")
        if st.button("🖼️"):
            preview_document("https://dewiyatech.com/images-pdf-rgmd/"+grievance['image_link'].split('/')[7])

        responses_df = resolutions[resolutions['id_complaint'] == grievance_ref]
        st.subheader("Previous Responses")
        # Table header
        col1, col2, col3, col4, col5 = st.columns([1,1,3,1,1])
        col1.write("Image")
        col2.write("PDF")
        col3.write("Response")
        col4.write("Responded on")
        col5.write("Resolved after(days)")

        for idx, row in responses_df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([1,1,3,1,1])

            # Image icon + clickable
            img_link = row['response_image_link']
            if img_link:  # make sure not None
                if col1.button("🖼️", key=f"img{idx}"):
                    preview_document(img_link)
    
            # PDF icon + clickable
            pdf_link = row['response_pdf_link']
            if pdf_link:
                if col2.button("📄", key=f"pdf{idx}"):
                    preview_document(pdf_link)
                    
            col3.write(row['resolution'])
            col4.write(row['resolution_date'].date())
            col5.write(row['resolution_days'])

        # -------------------------
        # Add a new response
        # -------------------------
        st.subheader("Add Response")
        with st.form("response_form"):
            responder_name = st.text_input("Responder Name", value=st.session_state.username, disabled=True)
            response_text = st.text_area("Response Text")
            date_response = st.date_input(label="Select a resolution date",value=date.today(),
                min_value=date(2000, 1, 1),
                help="Pick a date above 2000")
            status = st.selectbox("Status", ["Under Investigation","Resolved", "Open"])
            uploaded_files = st.file_uploader("Upload a directory", accept_multiple_files=True, type=["jpg","png", "pdf"])
            submit = st.form_submit_button("Submit Response")
        if submit:
            if response_text.strip() == "":
                st.warning("Response text cannot be empty!")
            else:
                try:
                    receiver = user_profile.loc[user_profile['user_id']==grievance_entered_by]
                    entered_by = receiver['prenom'] +" "+ receiver['nom']

                    #Validate Upload
                    if uploaded_files:
                        if len(uploaded_files) > 2:
                            st.error("You can upload a maximum of 2 files: one image and one PDF.")
                        else:
                            image_file = None
                            pdf_file = None

                            for file in uploaded_files:
                                if file.type.startswith("image/"):
                                    image_url = save_file(file)
                                    image_file = image_url
                                elif file.type == "application/pdf":
                                    pdf_url = save_file(file)
                                    pdf_file = pdf_url

                            # Final validation
                            if image_file or pdf_file:
                                save_resolution(responder_name,response_text,date_response, status, grievance_ref,image_file,pdf_file)
                                st.success("Resolution recorded successfully!")
                            else:
                                st.warning("Please upload exactly one image and/or one PDF.")

                    # Response submitted notification
                    if status!='Resolved':
                        email_html = build_email_html("grievance_response_email_notification.html",entered_by.iloc[0], grievance_ref ,grievance_village, status, response_text, "NCA Project")
                        subject = "Your grievance has received a new response"
                        send_email(sender="grmsystemdfgf@gmail.com",
                               password="seou lmza jywc pxiy",
                               receiver=receiver['email'],
                               smtp_server="smtp.gmail.com",
                               smtp_port=465,
                               html_content= email_html,
                               subject= subject
                            )
                    else:
                        email_html = build_email_html("grievance_status_changed_to_resolved_email_notification.html",entered_by.iloc[0], grievance_ref ,grievance_village, status, response_text, "NCA Project")
                        subject = "Your grievance has been resolved"
                        send_email(sender="grmsystemdfgf@gmail.com",
                               password="seou lmza jywc pxiy",
                               receiver=receiver['email'],
                               smtp_server="smtp.gmail.com",
                               smtp_port=465,
                               html_content= email_html,
                               subject= subject
                            )
                except Exception as e:
                    st.error(f"Failed to submit resolution: {e}")

    if st.session_state.logged_in:
        logout = st.sidebar.button("Logout")
    if logout:
        st.session_state.clear()

except Exception as e:
    st.error(f" This the error: {e}")
