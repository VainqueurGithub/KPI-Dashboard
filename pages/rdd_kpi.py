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
    page_title="REDD program KPI",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

focal_list = [
    "Poor environmental management",
    "Poor agricultural productivity",
    "Poor education quality",
    "Poor quality of healthcare",
    "Increasing great ape populations",
    "Reduced deforestation and forest degradation",
    "Sustainable exploitation of wildlife"
]

key_result_list = {
    "Poor environmental management": [
        "Reduced forest conversion for agriculture",
        "Reduced artisanal mining",
        "Reduced hunting"
    ],
    "Poor agricultural productivity": [
        "Improvement of agriculture and livestock production"
    ],
    "Poor education quality": [
        "Well trained and motivated teachers",
        "Well constructed and equipped schools",
        "Improved school attendance by pupils"
    ],
    "Poor quality of healthcare": [
        "Improved access to healthcare",
        "Better healthcare standards"
    ],
    "Increasing great ape populations": [
        "Great apes rarely hunted for food",
        "Great apes experience improved population viability"
    ],
    "Reduced deforestation and forest degradation": [
        "Reduced encroachment of forest for agriculture"
    ],
    "Sustainable exploitation of wildlife": [
        "Lower rates of wildlife harvesting for food",
        "Reduced hunting for profit"
    ]
}

import re

def expand_range(range_string):
    start, end = range_string.replace("(", "").replace(")", "").split("-")

    prefix_start = re.match(r"[A-Za-z]+", start).group()
    num_start = int(re.search(r"\d+", start).group())
    num_end = int(re.search(r"\d+", end).group())
    pad = len(re.search(r"\d+", start).group())

    return [f"{prefix_start}{i:0{pad}d}" for i in range(num_start, num_end+1)]

kpi_map = {
    "Reduced forest conversion for agriculture": expand_range("SIA001-SIA010"),
    "Reduced artisanal mining": expand_range("SIA011-SIA017"),
    "Reduced hunting": expand_range("SIA018-SIA021"),

    "Well trained and motivated teachers": expand_range("SIA022-SIA024"),
    "Well constructed and equipped schools": expand_range("SIA025-SIA029"),
    "Improved school attendance by pupils": expand_range("SIA030-SIA034"),
    "Improvement of agriculture and livestock production":expand_range("SIA035-SIA038"),
    "Improved access to healthcare": expand_range("SIA039-SIA043"),
    "Better healthcare standards": expand_range("SIA044-SIA050"),

    "Lower rates of wildlife harvesting for food": expand_range("B001-B011"),
    "Reduced hunting for profit": expand_range("B012-B026"),

    "Reduced encroachment of forest for agriculture": expand_range("B027-B027"),

    "Great apes rarely hunted for food": expand_range("B028-B029"),
    "Great apes experience improved population viability": expand_range("B030-B034")
}

# Initialize connection.
conn = st.connection("postgresql", type="sql")

#Queries
# Training
training_bg = conn.query('SELECT * FROM prog_coco.formation;', ttl="10m")
SIA001_qr = training_bg[
    (training_bg['mis_a_jour_agent'] == 1) &
    (training_bg['programme'].isin(['Agriculture', 'Apiculture', 'Elevage', 'Pisciculture']))
]
SIA001 = SIA001_qr['homme'].sum() + SIA001_qr['femme'].sum()
SIA002 = training_bg[(training_bg['association']==1) & (training_bg['programme'].isin(['Agriculture','Elevage']))].shape[0]
SIA003 = 0

#Awareness campaign
awareness_bg = conn.query('SELECT * FROM prog_coco.emission_sensibilisation;', ttl="10m")
SIA004_qr = awareness_bg[(awareness_bg['programme']=='Code forestier') | awareness_bg['programme']=='Lois environnementales']
SIA004 = SIA004_qr['nombre_personne_sensibilise'].sum()
SIA005 = 0
SIA006 = 0
SIA007 = 0
SIA008 = 0
SIA009 = 0
SIA010 = 0
SIA011 = 0
SIA012 = 0
SIA013 = 0
SIA014 = 0
SIA015 = 0
SIA016 = 0
SIA017 = 0
SIA018 = 0
SIA019 = 0
SIA020 = 0
SIA021 = 0
SIA022 = 0
SIA023 = 0
SIA024 = 0
SIA025 = 0
SIA026 = 0
SIA027 = 0
SIA028 = 0
SIA029 = 0
SIA030 = 0
SIA031 = 0
SIA032 = 0
SIA033 = 0
SIA034 = 0
SIA035 = 0
SIA036 = 0
SIA037 = 0
SIA038 = 0
SIA039 = 0
SIA040 = 0
SIA041 = 0
SIA042 = 0
SIA043 = 0
SIA044 = 0
SIA045 = 0
SIA046 = 0
SIA047 = 0
SIA048 = 0
SIA049 = 0
B001 = 0
B002 = 0
B003 = 0
B004 = 0
B005 = 0
B006 = 0
B007 = 0
B008 = 0
B009 = 0
B010 = 0
B011 = 0
B012 = 0
B013 = 0
B014 = 0
B015 = 0
B016 = 0
B017 = 0
B018 = 0
B019 = 0
B020 = 0
B021 = 0
B022 = 0
B023 = 0
B024 = 0
B025 = 0
B026 = 0
B027 = 0
B028 = 0
B029 = 0
B030 = 0
B031 = 0
B032 = 0
B033 = 0
B034 = 0
B035 = 0
B036 = 0
B037 = 0
B038 = 0
B039 = 0
B040 = 0

kpi_values = {
    "SIA001": SIA001,
    "SIA002": SIA002,
    "SIA003": SIA003,
    "SIA004": SIA004,
    "SIA005": SIA005,
    "SIA006": SIA006,
    "SIA007": SIA007,
    "SIA008": SIA008,
    "SIA009": SIA009,
    "SIA010": SIA010,
    "SIA011": SIA011,
    "SIA012": SIA012,
    "SIA013": SIA013,
    "SIA014": SIA014,
    "SIA015": SIA015,
    "SIA016": SIA016,
    "SIA017": SIA017,
    "SIA018": SIA018,
    "SIA019": SIA019,
    "SIA020": SIA020,
    "SIA021": SIA021,
    "SIA022": SIA022,
    "SIA023": SIA023,
    "SIA024": SIA024,
    "SIA025": SIA025,
    "SIA026": SIA026,
    "SIA027": SIA027,
    "SIA028": SIA028,
    "SIA029": SIA029,
    "SIA030": SIA030,
    "SIA031": SIA031,
    "SIA032": SIA032,
    "SIA033": SIA033,
    "SIA034": SIA034,
    "SIA035": SIA035,
    "SIA036": SIA036,
    "SIA037": SIA037,
    "SIA038": SIA038,
    "SIA039": SIA039,
    "SIA040": SIA040,
    "SIA041": SIA041,
    "SIA042": SIA042,
    "SIA043": SIA043,
    "SIA044": SIA044,
    "SIA045": SIA045,
    "SIA046": SIA046,
    "SIA047": SIA047,
    "SIA048": SIA048,
    "SIA049": SIA049,
    "B001": B001,
    "B002": B002,
    "B003": B003,
    "B004": B004,
    "B005": B005,
    "B006": B006,
    "B007": B007,
    "B008": B008,
    "B009": B009,
    "B010": B010,
    "B011": B011,
    "B012": B012,
    "B013": B013,
    "B014": B014,
    "B015": B015,
    "B016": B016,
    "B017": B017,
    "B018": B018,
    "B019": B019,
    "B020": B020,
    "B021": B021,
    "B022": B022,
    "B023": B023,
    "B024": B024,
    "B025": B025,
    "B026": B026,
    "B027": B027,
    "B028": B028,
    "B029": B029,
    "B030": B030,
    "B031": B031,
    "B032": B032,
    "B033": B033,
    "B034": B034,
    "B035": B035,
    "B036": B036,
    "B037": B037,
    "B038": B038,
    "B039": B039,
    "B040": B040,
}


descriptions = {
    "SIA001": "Agents de vulgarisation agricole formés dans la zone du projet",
    "SIA002": "Ateliers de formation sur les cultures ou l'élevage organisés dans la communauté",
    "SIA003": "Parcelles de démonstration de cultures ou d'élevage établies dans la communauté",
    "SIA004": "Membres de la communauté sensibilisés au Code forestier et aux lois environnementales connexes",
    "SIA005": "% Ménages adoptant des méthodes nouvelles ou améliorées d'agriculture ou d'élevage",
    "SIA006": "% Ménages avec une productivité agricole accrue et une plus grande diversification",
    "SIA007": "% Ménages disposant d'un excédent de production à vendre ou à stocker",
    "SIA008": "Personnes arrêtées pour exploitation forestière illégale",
    "SIA009": "% Ménages cultivant dans les forêts secondaires communales (communautaires??)",
    "SIA010": "Hectares de forêt perdus au profit de l'expansion agricole",
    "SIA011": "Membres de la communauté employés dans le cadre du projet REDD+",
    "SIA012": "Membres de la communauté formés à des compétences professionnelles",
    "SIA013": "Montant du capital d'amorçage disponible pour les activités de développement communautaire",
    "SIA014": "% Ménages dont les membres de la communauté tirent des revenus de sources non agricoles",
    "SIA015": "Revenu mensuel moyen en espèces du ménage",
    "SIA016": "Exploitants miniers artisanaux illégaux arrêtés dans la zone du projet",
    "SIA017": "Mines artisanales dans la zone du projet REDD+",
    "SIA018": "Réunions de sensibilisation organisées dans la communauté sur la viande de brousse et les sources alternatives de protéines",
    "SIA019": "% Ménages dépendant de la faune sauvage pour leurs protéines animales",
    "SIA020": "Chasseurs illegaux arrestés dans l'Aire du projet ",
    "SIA021": "Espèces d'animaux sauvages vendus sur les marchés locaux",
    "SIA022": "Membres de la communauté locale formés à l'enseignement",
    "SIA023": "Enseignants employés dans le cadre du projet",
    "SIA024": "Mean student: teacher ratio in local schools: Ratio moyen élèves/enseignants dans les écoles locales",
    "SIA025": "Ecoles construites ou rénovées",
    "SIA026": "Ecoles meublées et autres matériels pédagogiques",
    "SIA027": "Infrastructures scolaires construites, par exemple bureaux, toilettes, cuisines",
    "SIA028": "Etudiants utilisant les installations nouvellement construites",
    "SIA029": "Performance moyenne dans les écoles de la zone du projet",
    "SIA030": "Montant des revenus alloués aux bourses d'études",
    "SIA031": "Etudiants soutenus dans le cadre du programme d'éducation par projet",
    "SIA032": "% Enfants d'âge scolaire non scolarisés par ménage",
    "SIA033": "% Ménages avec des étudiants qui ont été soutenus dans le cadre du projet",
    "SIA034": "% Etudiants soutenus dans le cadre d'un emploi rémunéré",
    "SIA035": "Montant du capital d'amorçage destiné aux intrants agricoles",
    "SIA036": "% Ménages ayant reçu des intrants agricoles du projet",
    "SIA037": "Programmes d'échange agricole entrepris",
    "SIA038": "Mois pendant lesquels les ménages connaissent l'insécurité alimentaire",
    "SIA039": "Nombre de cliniques ou de dispensaires construits dans la zone du projet",
    "SIA040": "Type d'équipement acheté pour les cliniques",
    "SIA041": "Infrastructures liées à la santé construites, par exemple bureaux, toilettes, logements pour le personnel",
    "SIA042": "Patients qui utilisent les nouveaux cliniques construits",
    "SIA043": "Distance moyenne du ménage ou temps de trajet jusqu'au centre de santé le plus proche",
    "SIA044": "Travailleurs de la santé formés ou employés",
    "SIA045": "Puits forés dans la communauté",
    "SIA046": "Ratio moyen population/infirmière dans la communauté locale",
    "SIA047": "% Ménages ayant un meilleur accès à l'eau potable provenant de puits",
    "SIA048": "Agents WASH formés et employés",
    "SIA049": "Ateliers de formation WASH dans la communauté et les écoles",
    "SIA050": "Affections ou épidémies liées à l'EAH enregistrées dans les cliniques",
    "B001": "Des personnes participant à des ateliers sur l'élevage et l'aquaculture",
    "B002": "Ressources financières ou autres ressources transférées à la communauté pour l'élevage et l'aquaculture",
    "B003": "Animaux de chaque espèce d'élevage (mammifères et oiseaux) au début de chaque période de surveillance",
    "B004": "Naissances et décès parmi les mammifères et les oiseaux élevés dans un sous-échantillon d'agriculteurs",
    "B005": "Nombre moyen de litres de lait/œufs par jour et par femelle de chaque espèce élevée",
    "B006": "Kg de chaque espèce de poisson d'élevage au début et à la fin de chaque période de surveillance pour un sous-échantillon d'étangs",
    "B007": "Kg de poissons d'élevage de chaque espèce consommés au cours de chaque période de suivi pour un sous-échantillon d'étangs (le même que pour l'indicateur précédent)",
    "B008": "Ménages tirant des revenus de l'exploitation minière artisanale",
    "B009": "Consommation alimentaire et score nutritionnel",
    "B010": "Fréquence mensuelle moyenne de consommation d'animaux sauvages par ménage",
    "B011": "Jours consacrés à la chasse et à la pêche par foyer",
    "B012": "Activités génératrices de revenus durables soutenues par le projet",
    "B013": "Des ateliers sur les activités génératrices de revenus ont été organisés",
    "B014": "Participants aux ateliers sur les activités génératrices de revenus",
    "B015": "Activités génératrices de revenus proposées par le projet et poursuivies par la communauté",
    "B016": "Nombre moyen d'activités génératrices de revenus par ménage",
    "B017": "Score de changement perçu dans le revenu du ménage en raison d'activités alternatives génératrices de revenus",
    "B018": "Revenu mensuel généré par la pêche et la chasse",
    "B019": "Rangers embauchés et formés",
    "B020": "Des postes de surveillance construits",
    "B021": "Patrouilles de gardes forestiers entreprises, leur longueur et leur durée",
    "B022": "Programmes radiophoniques sur la conservation de la nature, clubs nature pour étudiants et toute autre activité visant à sensibiliser à la législation et à la durabilité de l'exploitation des ressources naturelles",
    "B023": "Proportion de ménages touchés par des activités de sensibilisation à l'environnement",
    "B024": "État d'avancement du plan d'aménagement du territoire",
    "B025": "Proportion des zones de chasse prévues délimitées",
    "B026": "Activités de chasse et de pêche illégales détectées lors des patrouilles",
    "B027": "Champs agricoles nouvellement ouverts",
    "B028": "Grands singes capturés ou tués par kilomètre de patrouille de gardes forestiers",
    "B029": "Abondance et tendances des populations de gorilles et de chimpanzés",
    "B030": "La taille (ha) des réserves communautaires déclarées",
    "B031": "Score de connectivité de Nkuba avec d'autres parcelles d'habitat de grands singes (par exemple, le parc national de Kahuzi Biega et le parc national de Maiko).",
    "B032": "Prévalence des aliments potentiels et des sites de couchage",
    "B033": "Coefficient de consanguinité des deux populations de grands singes du projet REDD+ de Nkuba",
    "B034": "Probabilité d'extinction d'ici 50 ans pour les populations de gorilles de Grauer et de chimpanzés de l'Est à Nkuba",
}

unities = {
    "SIA001": "",
    "SIA002": "",
    "SIA003": "",
    "SIA004": "",
    "SIA005": "%",
    "SIA006": "%",
    "SIA007": "%",
    "SIA008": "",
    "SIA009": "%",
    "SIA010": "Ha",
    "SIA011": "",
    "SIA012": "",
    "SIA013": "USD",
    "SIA014": "%",
    "SIA015": "USD",
    "SIA016": "",
    "SIA017": "",
    "SIA018": "",
    "SIA019": "%",
    "SIA020": "",
    "SIA021": "",
    "SIA022": "",
    "SIA023": "",
    "SIA024": "",
    "SIA025": "",
    "SIA026": "",
    "SIA027": "",
    "SIA028": "",
    "SIA029": "",
    "SIA030": "USD",
    "SIA031": "",
    "SIA032": "",
    "SIA033": "",
    "SIA034": "",
    "SIA035": "USD",
    "SIA036": "%",
    "SIA037": "",
    "SIA038": "Mois",
    "SIA039": "",
    "SIA040": "",
    "SIA041": "",
    "SIA042": "Patients",
    "SIA043": "Km",
    "SIA044": "Travailleurs",
    "SIA045": "Puits",
    "SIA046": "",
    "SIA047": "%",
    "SIA048": "Agents",
    "SIA049": "Ateliers",
    "SIA050": "",
    "B001": "",
    "B002": "USD",
    "B003": "",
    "B004": "",
    "B005": "",
    "B006": "Kg",
    "B007": "Kg",
    "B008": "Ménages",
    "B009": "",
    "B010": "",
    "B011": "Jours",
    "B012": "",
    "B013": "Ateliers",
    "B014": "Participants",
    "B015": "Activités",
    "B016": "",
    "B017": "",
    "B018": "USD",
    "B019": "Rangers",
    "B020": "Postes",
    "B021": "",
    "B022": "",
    "B023": "",
    "B024": "",
    "B025": "",
    "B026": "",
    "B027": "",
    "B028": "",
    "B029": "",
    "B030": "Ha",
    "B031": "",
    "B032": "",
    "B033": "",
    "B034": "",
}

st.sidebar.header("Navigation")

selected_focal = st.sidebar.selectbox("Focal Issue", focal_list)
selected_kr = st.sidebar.selectbox("Key Result", key_result_list[selected_focal])
search = st.sidebar.text_input("Search KPI")
search_year = st.sidebar.text_input("Year of Reporting")

st.title(f"{selected_focal} → {selected_kr}")

kpis = kpi_map[selected_kr]

# Filter KPIs by search
if search:
    kpis = [k for k in kpis if search.lower() in k.lower()]

with st.expander("KPIs", expanded=True):

    for i in range(0, len(kpis), 3):
        cols = st.columns(3)

        for j, col in enumerate(cols):
            if i + j < len(kpis):
                kpi_code = kpis[i + j]

                value = kpi_values.get(kpi_code, 0)   # default value = 0
                delta = None  # or calculate depending on your logic

                col.metric(label=kpi_code, value=value, delta=delta, help=descriptions.get(kpi_code))
                