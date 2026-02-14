import streamlit as st
import pandas as pd
import numpy as np
import time
from streamlit_card import card
from streamlit_extras.metric_cards import style_metric_cards
import plotly.express as px
import altair as alt
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import pydeck as pdk
from shapely.geometry import mapping



st.set_page_config(
    page_title="Community conservation program KPI",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)


def example(assoc_numb, work_clos, members, beneficiaires, males, females, students, earthling_fam):
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)

    col1.metric(label="Associations", value=assoc_numb)
    col2.metric(label="Working Closely", value=work_clos)
    col3.metric(label="Members", value=members)
    col5.metric(label="Males", value=males)
    col6.metric(label="Females", value=females)
    col4.metric(label="Beneficiaires", value=beneficiaires)
    col7.metric(label="Students", value=students)
    col8.metric(label="Earthling Family", value=earthling_fam)

    style_metric_cards()


# Initialize connection.
conn = st.connection("postgresql", type="sql")

# Queries
query_bg = conn.query('SELECT * FROM prog_coco.group_beneficiaire;', ttl="10m")
query_eleve_ft = conn.query('SELECT * FROM prog_coco.eleve_fterien;', ttl="10m")
query_ft_cfcl = conn.query('SELECT * FROM prog_coco.cfcl_fterien_v;', ttl="10m")
query_livestock_seed = conn.query('SELECT * FROM prog_coco.livestock_seed', ttl="10m")
df_association = query_bg[query_bg['status']=='association']

association_number = query_bg[query_bg['status']=='association'].shape[0]
work_clos = query_bg[(query_bg['status']=='association') & (query_bg['proche_dfgf']==True)].shape[0]
members = (df_association['homme'].sum()) +(df_association['femme'].sum())
beneficiaires = query_bg.shape[0]
males = df_association['homme'].sum()
females = df_association['femme'].sum()
eleves = query_eleve_ft['students'].sum()
earthing_fam = query_eleve_ft['earthling_family'].shape[0]
gender_df = pd.DataFrame({
   'gender' : ["Men", "Women"],
   'count':[df_association['homme'].sum(), df_association['femme'].sum()]
})

example(association_number, work_clos, members, beneficiaires,males,
        females,eleves,earthing_fam)

col_bar_chat, col_pie_chart1, col_pie_chart2 = st.columns(3)
# -------------------------
# Calculate KPI counts
# -------------------------
# Count TRUE and FALSE in working_closely
kpi = df_association["proche_dfgf"].value_counts().rename(index={True:"Working Closely", False:"Not Working Closely"})

# -------------------------
# Bar Chart
# -------------------------

with col_bar_chat:
    st.write("Association Working Closely vs Not with DFGF")
    st.bar_chart(kpi)

# -------------------------
# Pie Chart
# -------------------------
with col_pie_chart1:
    pie_df = kpi.reset_index()
    pie_df.columns = ["category", "count"]
    fig = px.pie(pie_df, names="category", values="count", hole=0)
    st.plotly_chart(fig, use_container_width=True)

with col_pie_chart2:
    fig = px.pie(gender_df, names="gender", values="count", hole=0)
    st.plotly_chart(fig, use_container_width=True)

col_tab1, col_tab2 = st.columns([2,3])

with col_tab1:
    query_eleve_ft

with col_tab2:
    query_ft_cfcl

st.title("Livestock villager impact")
st.subheader("💰 Income vs Investment Dashboard with Multi-Crop Filter")

# --- Assume df has columns ---
# beneficiaire, speculation, total_price_produce, total_price_invest, year_production

# Fill NULLs
query_livestock_seed[["total_price_produce", "total_price_invest"]] = query_livestock_seed[["total_price_produce", "total_price_invest"]].fillna(0)

# --- Interactive filters ---
years = query_livestock_seed["year_production"].sort_values().unique()
speculations = query_livestock_seed["speculation"].sort_values().unique()

selected_year = st.selectbox("Select Year:", options=years)

# Multi-select for crops
selected_speculations = st.multiselect(
    "Select Crop(s) (Speculation):",
    options=speculations,
    default=list(speculations)  # default = all crops selected
)

# --- Filter dataframe ---
filtered_df = query_livestock_seed[
    (query_livestock_seed["year_production"] == selected_year) &
    (query_livestock_seed["speculation"].isin(selected_speculations))
]

# --- Aggregate per beneficiary ---
impact = filtered_df.groupby("beneficiaire").agg({
    "total_price_produce": "sum",
    "total_price_invest": "sum"
}).reset_index()

# --- Calculate KPIs ---
total_income = impact["total_price_produce"].sum()
total_investment = impact["total_price_invest"].sum()
roi_percent = (total_income / total_investment * 100) if total_investment > 0 else 0

# --- Display KPIs ---
kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
kpi_col1.metric("Total Income (USD)", f"${total_income:,.0f}")
kpi_col2.metric("Total Investment (USD)", f"${total_investment:,.0f}")
kpi_col3.metric("ROI (%)", f"{roi_percent:.1f}%", delta=(total_income-total_investment))

# --- Prepare data for dual-bar chart ---
impact_melt = impact.melt(
    id_vars="beneficiaire",
    value_vars=["total_price_produce", "total_price_invest"],
    var_name="Type",
    value_name="Amount"
)

# --- Custom colors ---
color_scale = alt.Scale(domain=["total_price_produce", "total_price_invest"],
                        range=["#2ca02c", "#ff7f0e"])  # green=income, orange=investment

# --- Bar chart ---
chart = alt.Chart(impact_melt).mark_bar().encode(
    x=alt.X("beneficiaire:N", title="Beneficiary"),
    y=alt.Y("Amount:Q", title="USD"),
    color=alt.Color("Type:N", scale=color_scale, legend=alt.Legend(title="KPI")),
    xOffset="Type:N",
    tooltip=["beneficiaire", "Type", "Amount"]
).properties(height=400)

# --- Layout ---
col1, col2 = st.columns([2,1])
with col1:
    st.subheader(f"Income vs Investment ({selected_year})")
    st.altair_chart(chart, use_container_width=True)

with col2:
    st.subheader("Summary")
    st.write(f"Filtered for Year: **{selected_year}**")
    st.write(f"Selected Crop(s): **{', '.join(selected_speculations) if selected_speculations else 'None'}**")
    st.write("Green bars = Income, Orange bars = Investment")






st.subheader("🌱 Seed Distributed → Production Correlation")

# --- Assume df has columns ---
# beneficiaire, speculation, qte_distribue, qte_produit_kg, year_production

# Fill NULLs
query_livestock_seed[["quantity_distributed", "quantity_produced"]] = query_livestock_seed[["quantity_distributed", "quantity_produced"]].fillna(0)


# --- Filter dataframe ---
filtered_df = query_livestock_seed[
    (query_livestock_seed["year_production"] == selected_year) &
    (query_livestock_seed["speculation"].isin(selected_speculations))
]

# --- Optional: check if filtered_df is empty ---
if filtered_df.empty:
    st.warning("No data available for the selected year/crops.")
else:
    # --- Scatter plot ---
    chart = alt.Chart(filtered_df).mark_circle(size=80).encode(
        x=alt.X("quantity_distributed:Q", title="Quantity Distributed (kg)"),
        y=alt.Y("quantity_produced:Q", title="Quantity Produced (kg)"),
        color="speculation:N",
        tooltip=["beneficiaire", "speculation", "quantity_distributed", "quantity_produced"]
    ).properties(height=400)


    # --- Optional: Add regression line ---
    reg_line = chart.transform_regression(
        "quantity_distributed", "quantity_produced", groupby=["speculation"]
    ).mark_line()
    st.altair_chart(chart + reg_line, use_container_width=True)





st.subheader("🌾 Food Security & Efficiency")
# Fill NULLs
cols_to_fill = ["quantity_seeded", "quantity_produced", "quantity_consumed",
                "quantity_sold", "total_price_invest", "total_price_produce"]
query_livestock_seed[cols_to_fill] = query_livestock_seed[cols_to_fill].fillna(0)


# --- Filter dataframe ---
filtered_df = query_livestock_seed[
    (query_livestock_seed["year_production"] == selected_year) &
    (query_livestock_seed["speculation"].isin(selected_speculations))
]

if filtered_df.empty:
    st.warning("No data available for the selected year/crops.")
else:
    # --- Assume df is already filtered for year/crops ---
    # Columns: quantity_seeded, quantity_produced, quantity_consumed, quantity_sold, total_price_invest, total_price_produce

    # Fill NULLs
    cols_to_fill = ["quantity_seeded", "quantity_produced", "quantity_consumed",
                "quantity_sold", "total_price_invest", "total_price_produce"]
    query_livestock_seed[cols_to_fill] = query_livestock_seed[cols_to_fill].fillna(0)

    # --- Aggregate summary ---
    total_seeded = query_livestock_seed["quantity_seeded"].sum()
    total_produced = query_livestock_seed["quantity_produced"].sum()
    total_consumed = query_livestock_seed["quantity_consumed"].sum()
    total_sold = query_livestock_seed["quantity_sold"].sum()
    total_income = query_livestock_seed["total_price_produce"].sum()
    total_investment = query_livestock_seed["total_price_invest"].sum()

    avg_food_retention = (total_consumed / total_produced) if total_produced>0 else 0
    avg_seed_efficiency = (total_produced / total_seeded) if total_seeded>0 else 0
    avg_sale_efficiency = (total_sold / total_produced) if total_produced>0 else 0
    avg_roi = (total_income / total_investment) if total_investment>0 else 0

    # --- Display as metrics in one row ---
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Seeded (kg)", f"{total_seeded:,.0f}")
    col2.metric("Total Produced (kg)", f"{total_produced:,.0f}")
    col3.metric("Total Consumed (kg)", f"{total_consumed:,.0f}")
    col4.metric("Total Sold (kg)", f"{total_sold:,.0f}")
    col5.metric("Avg Food Retention", f"{avg_food_retention:.2f}")

    # --- Optional: narrative below the metrics ---
    st.markdown(f"""
          This year {int(selected_year)}, villagers **planted {total_seeded:,.0f} kg of {', '.join(selected_speculations)}**, producing **{total_produced:,.0f} kg of crops**.  
        Out of this, **{total_consumed:,.0f} kg were consumed locally**, and **{total_sold:,.0f} kg were sold**, generating a total income of **{total_income:,.0f} (USD)** from an investment of **{total_investment:,.0f} (USD)**.  

        The **average food retention ratio** is **{avg_food_retention:.2f}**, the **average seed-to-production efficiency** is **{avg_seed_efficiency:.2f}**, the **average sale efficiency** is **{avg_sale_efficiency:.2f}**, and the **average return on investment (ROI)** is **{avg_roi:.2f}**, showing the efficiency and impact of the program on household food security.
    """)



















    # --- Food Security Indicators ---
    food_df = filtered_df.groupby("beneficiaire").agg({
        "quantity_consumed":"sum",
        "quantity_produced":"sum"
    }).reset_index()
    
    food_df["food_retention_ratio"] = food_df["quantity_consumed"] / food_df["quantity_produced"]
    
    col1, col2 = st.columns(2)
    
    # Bar chart: Food Retention Ratio
    fig1 = px.bar(food_df, x="beneficiaire", y="food_retention_ratio",
                  title="Food Retention Ratio per Beneficiary",
                  labels={"food_retention_ratio":"Consumed / Produced"})
    col1.plotly_chart(fig1, use_container_width=True)
    
    # Pie chart: Total Consumed vs Total Sold
    pie_df = pd.DataFrame({
        "Category":["Consumed", "Sold"],
        "Kg":[filtered_df["quantity_consumed"].sum(), filtered_df["quantity_sold"].sum()]
    })
    fig2 = px.pie(pie_df, names="Category", values="Kg", hole=0.4, title="Overall Food Distribution")
    col2.plotly_chart(fig2, use_container_width=True)
    
    # --- Efficiency Indicators ---
    eff_df = filtered_df.groupby("beneficiaire").agg({
        "quantity_seeded":"sum",
        "quantity_produced":"sum",
        "quantity_sold":"sum",
        "total_price_invest":"sum",
        "total_price_produce":"sum"
    }).reset_index()
    
    eff_df["seed_efficiency"] = eff_df["quantity_produced"] / eff_df["quantity_seeded"]
    eff_df["sale_efficiency"] = eff_df["quantity_sold"] / eff_df["quantity_produced"]
    eff_df["roi"] = eff_df["total_price_produce"] / eff_df["total_price_invest"]
    
    col3, col4, col5 = st.columns(3)
    
    fig3 = px.bar(eff_df, x="beneficiaire", y="seed_efficiency",
                  title="Seed-to-Production Efficiency per Beneficiary")
    col3.plotly_chart(fig3, use_container_width=True)
    
    fig4 = px.bar(eff_df, x="beneficiaire", y="sale_efficiency",
                  title="Production-to-Sale Efficiency per Beneficiary")
    col4.plotly_chart(fig4, use_container_width=True)
    
    fig5 = px.bar(eff_df, x="beneficiaire", y="roi",
                  title="ROI (Income / Investment) per Beneficiary")
    col5.plotly_chart(fig5, use_container_width=True)


try:
    gdf = gpd.read_file("static/map/NCA_RDCongo.shp")
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
        m = folium.Map(location=[gdf.geometry.centroid.y.mean(),gdf.geometry.centroid.x.mean()],zoom_start=6, width='100%')
        folium.GeoJson(gdf).add_to(m)
        st_folium(m, width='20%', height=800)

except Exception as e:
    st.error(f"Error: {e}")































