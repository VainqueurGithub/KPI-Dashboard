# -------------------------
    # Load grievances
    # -------------------------
    df =conn.query("SELECT grievance_id, reference_no, category, urgency_level, status, grievance_description, village, entered_by FROM redd_project.grievances")

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
    grievance_id = st.selectbox("Select Grievance ID", filtered_df['grievance_id'])
    grievance_ref = filtered_df['reference_no'].loc[filtered_df['grievance_id']==grievance_id].iloc[0]
    grievance_village = filtered_df['village'].loc[filtered_df['grievance_id']==grievance_id].iloc[0]
    grievance_entered_by = filtered_df['entered_by'].loc[filtered_df['grievance_id']==grievance_id].iloc[0]
    # Show grievance details
    grievance = df[df['grievance_id'] == grievance_id].iloc[0]
    st.subheader(f"Grievance #{grievance_id}")
    st.write(f"**Category:** {grievance['category']}")
    st.write(f"**Urgency:** {grievance['urgency_level']}")
    st.write(f"**Status:** {grievance['status']}")
    st.write(f"**Village:** {grievance['village']}")
    st.write(f"**Description:** {grievance['grievance_description']}")

    # Load previous responses
    responses_df = conn.query(f"""
    SELECT resolved_by, resolution_text, date_resolved
    FROM redd_project.resolutions
    WHERE grievance_id = {grievance_id}
    ORDER BY date_resolved DESC
    """)

    st.subheader("Previous Responses")
    st.dataframe(responses_df)

    # -------------------------
    # Add a new response
    # -------------------------
    st.subheader("Add Response")
    with st.form("response_form"):
        responder_name = st.text_input("Responder Name")
        response_text = st.text_area("Response Text")
        date_response = st.date_input(label="Select a resolution date",value=date.today(),
            min_value=date(2000, 1, 1),
            help="Pick a date above 2000")
        status = st.selectbox("Status", ["Under Investigation","Resolved", "Open"])
        submit = st.form_submit_button("Submit Response")

    if submit:
        if response_text.strip() == "":
            st.warning("Response text cannot be empty!")
        else:
            try:
                receiver = user_profile.loc[user_profile['user_id']==grievance_entered_by]
                entered_by = receiver['prenom'] +" "+ receiver['nom']
                save_resolution(grievance_id, responder_name, response_text, date_response, status)
                st.success("Resolution recorded successfully!")
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