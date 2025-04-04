import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

# Load and preprocess the production data
@st.cache_data
def load_and_sort_data(dataset_url):
    try:
        df = pd.read_csv(dataset_url, usecols=[
            'sigla', 'anio', 'mes', 'prod_pet', 'prod_gas', 'prod_agua',
            'tef', 'empresa', 'areayacimiento', 'coordenadax', 'coordenaday',
            'formprod', 'sub_tipo_recurso', 'tipopozo'
        ])
        df['date'] = pd.to_datetime(df['anio'].astype(str) + '-' + df['mes'].astype(str) + '-1')
        df['gas_rate'] = df['prod_gas'] / df['tef']
        df['oil_rate'] = df['prod_pet'] / df['tef']
        df['water_rate'] = df['prod_agua'] / df['tef']
        df['Np'] = df.groupby('sigla')['prod_pet'].cumsum()
        df['Gp'] = df.groupby('sigla')['prod_gas'].cumsum()
        df['Wp'] = df.groupby('sigla')['prod_agua'].cumsum()
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# URLs for datasets
dataset_url = "http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv"

# Load the production data
data_sorted = load_and_sort_data(dataset_url)

if data_sorted.empty:
    st.error("Failed to load production data.")
    st.stop()

# Replace company names in production data
replacement_dict = {
    'PAN AMERICAN ENERGY (SUCURSAL ARGENTINA) LLC': 'PAN AMERICAN ENERGY',
    'PAN AMERICAN ENERGY SL': 'PAN AMERICAN ENERGY',
    'VISTA ENERGY ARGENTINA SAU': 'VISTA',
    'Vista Oil & Gas Argentina SA': 'VISTA',
    'VISTA OIL & GAS ARGENTINA SAU': 'VISTA',
    'WINTERSHALL DE ARGENTINA S.A.': 'WINTERSHALL',
    'WINTERSHALL ENERGÍA S.A.': 'WINTERSHALL'
}
data_sorted['empresaNEW'] = data_sorted['empresa'].replace(replacement_dict)

# Sidebar filters
st.header(f":blue[Reporte de Producción No Convencional]")
image = Image.open('Vaca Muerta rig.png')
st.sidebar.image(image)

# Filter out rows where TEF is zero for calculating metrics
data_filtered = data_sorted[(data_sorted['tef'] > 0)]

# Find the latest date in the dataset
latest_date = data_filtered['date'].max()

st.write("Fecha de Alocación en Progreso: ", latest_date.date())

#------------------------------------------- RESULTADOS CON ULTIMOS DATOS 

import streamlit as st
import plotly.express as px

# Filtrar datos válidos
data_filtered = data_sorted[data_sorted['tef'] > 0]

# Fecha más reciente
latest_date = data_filtered['date'].max()

# Datos de esa fecha
latest_data = data_filtered[data_filtered['date'] == latest_date]

# Top 3 pozos por gas y por petróleo
top3_gas = latest_data.sort_values(by='gas_rate', ascending=False).head(3)
top3_oil = latest_data.sort_values(by='oil_rate', ascending=False).head(3)

st.header(f"📊 Watchlist – {latest_date.strftime('%B %Y')}")

# Métricas destacadas – Producción de Gas
st.subheader("🔝 Caudal de Gas")
cols_gas = st.columns(2)
for i, row in enumerate(top3_gas.itertuples()):
    cols_gas[i].metric(
        label=f"{row.sigla} ({row.empresaNEW})",
        value=f"{row.gas_rate:,.0f} m³/día"
    )

# Métricas destacadas – Producción de Petróleo
st.subheader("🔝 Caudal de Petróleo")
cols_oil = st.columns(2)
for i, row in enumerate(top3_oil.itertuples()):
    cols_oil[i].metric(
        label=f"{row.sigla} ({row.empresaNEW})",
        value=f"{row.oil_rate:,.0f} m³/día"
    )



#-------------------------------------------
