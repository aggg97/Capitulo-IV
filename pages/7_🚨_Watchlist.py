import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

# Load and sort the data
# @st.cache_data
# def load_and_sort_data(dataset_url):
#     df = pd.read_csv(dataset_url, usecols=COLUMNS)
#     df['date'] = pd.to_datetime(df['anio'].astype(str) + '-' + df['mes'].astype(str) + '-1')
#     df['gas_rate'] = df['prod_gas'] / df['tef']
#     df['oil_rate'] = df['prod_pet'] / df['tef']
#     data_sorted = df.sort_values(by=['sigla', 'fecha_data'], ascending=True)
#     return data_sorted

# URL of the dataset
#dataset_url = "http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv"

# Load and sort the data using the cached function
#data_sorted = load_and_sort_data(dataset_url)


# Verificamos si los datos ya fueron cargados en la Main Page
if 'df' in st.session_state:
    # Recuperamos los datos de la memoria sin esperar un segundo
    data_sorted = st.session_state['df']
    
    st.info("Utilizando datos recuperados de la memoria.")
    
else:
    st.warning("⚠️ No se han cargado los datos. Por favor, vuelve a la Página Principal.")
    
    # El link para regresar
    st.page_link("main.py", label="Ir a la Página Principal para cargar datos", icon="🏠")

# Replace company names in production data
replacement_dict = {
    'PAN AMERICAN ENERGY (SUCURSAL ARGENTINA) LLC': 'PAN AMERICAN ENERGY',
    'PAN AMERICAN ENERGY SL': 'PAN AMERICAN ENERGY',
    'VISTA ENERGY ARGENTINA SAU': 'VISTA',
    'Vista Oil & Gas Argentina SA': 'VISTA',
    'VISTA OIL & GAS ARGENTINA SAU': 'VISTA',
    'WINTERSHALL DE ARGENTINA S.A.': 'WINTERSHALL',
    'WINTERSHALL ENERGÍA S.A.': 'WINTERSHALL',
    'PLUSPETROL S.A.': 'PLUSPETROL',
    'PLUSPETROL CUENCA NEUQUINA S.R.L.': 'PLUSPETROL'
}
data_sorted['empresaNEW'] = data_sorted['empresa'].replace(replacement_dict)

# Sidebar filters
st.header(f":blue[🚨 Watchlist - Nuevos Pozos en Vaca Muerta]")
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

# Top 5 pozos por gas y por petróleo
top_gas = latest_data.sort_values(by='gas_rate', ascending=False).head(5)
top_oil = latest_data.sort_values(by='oil_rate', ascending=False).head(5)



st.subheader("🔥 Ranking actual de los 5 pozos de gas más productivos de la Cuenca")



# Gráfico de Producción de Gas
fig_gas = px.bar(
    top_gas.sort_values(by='gas_rate'),
    y='sigla',
    x='gas_rate',
    color='empresaNEW',
    orientation='h',
    labels={'gas_rate': 'Producción de Gas (m³/día)', 'sigla': 'Pozo', 'empresaNEW': 'Empresa','areayacimiento':'Bloque'},
    text='gas_rate',
    hover_data=['empresaNEW', 'areayacimiento'],
)
fig_gas.update_traces(texttemplate='%{text:.2f}', textposition='inside')
fig_gas.update_layout(title='Producción de Gas (km3/d)',yaxis=dict(categoryorder='total ascending'),yaxis_title=None )

st.plotly_chart(fig_gas, use_container_width=True)


st.subheader("🔥 Ranking actual de los 5 pozos de petróleo más productivos de la Cuenca")

# Gráfico de Producción de Petróleo
fig_oil = px.bar(
    top_oil.sort_values(by='oil_rate'),
    y='sigla',
    x='oil_rate',
    color='empresaNEW',
    orientation='h',
    labels={'oil_rate': 'Producción de Petróleo (m³/día)', 'sigla': 'Pozo', 'empresaNEW': 'Empresa','areayacimiento':'Bloque'},
    text='oil_rate',
    hover_data=['empresaNEW', 'areayacimiento'],
)
fig_oil.update_traces(texttemplate='%{text:.2f}', textposition='inside')
fig_oil.update_layout(title='Producción de Petróleo (m3/d)',yaxis=dict(categoryorder='total ascending'),yaxis_title=None )

st.plotly_chart(fig_oil, use_container_width=True)

#-------------------------------------------

st.markdown('''
⚠️ **Nota:** Al evaluar la productividad en Vaca Muerta, es importante tener precaución con los pozos considerados "más productivos", únicamente por su caudal máximo.

El caudal máximo registrado suele estar influenciado por el *choke management*, así también como la interferencia de pozos en un mismo PAD. Este fenómeno está relacionado con el concepto del SRV *(Stimulated Rock Volume)*.

Por lo tanto, una evaluación más representativa de la productividad debería realizarse a nivel de PAD y no de manera individual por pozo.
''')

