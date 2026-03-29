import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# #Load and sort the data
# @st.cache_data
# def load_and_sort_data(dataset_url):
#     df = pd.read_csv(dataset_url, usecols=COLUMNS)
#     df['date'] = pd.to_datetime(df['anio'].astype(str) + '-' + df['mes'].astype(str) + '-1')
#     df['gas_rate'] = df['prod_gas'] / df['tef']
#     df['oil_rate'] = df['prod_pet'] / df['tef']
#     data_sorted = df.sort_values(by=['sigla', 'fecha_data'], ascending=True)
#     return data_sorted

# #URL of the dataset
# dataset_url = "http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv"

# #Load and sort the data using the cached function
# data_sorted = load_and_sort_data(dataset_url)


#Verificamos si los datos ya fueron cargados en la Main Page
if 'df' in st.session_state:
    # Recuperamos los datos de la memoria sin esperar un segundo
    data_sorted = st.session_state['df']
    data_sorted['date'] = pd.to_datetime(df['anio'].astype(str) + '-' + df['mes'].astype(str) + '-1')
    data_sorted['gas_rate'] = data_sorted['prod_gas'] / df['tef']
    data_sorted['oil_rate'] = data_sorted['prod_pet'] / df['tef']
    data_sorted = df.sort_values(by=['sigla', 'fecha_data'], ascending=True)
    
    st.info("Utilizando datos recuperados de la memoria.")
    
else:
    st.warning("⚠️ No se han cargado los datos. Por favor, vuelve a la Página Principal.")


# Add a new column "Fecha" by combining year and month
data_sorted['date'] = pd.to_datetime(data_sorted['anio'].astype(str) + '-' + data_sorted['mes'].astype(str) + '-1')
# Convert the "Fecha" column to datetime format
data_sorted['date'] = pd.to_datetime(data_sorted['date'])

st.title(f":blue[Capítulo IV Dataset - Producción No Convencional]")

image = Image.open('Vaca Muerta rig.png')
st.sidebar.image(image)
st.sidebar.title("Por favor filtrar aquí: ")

# Create a multiselect widget for 'tipo pozo'
# soon... type fluid classification by GOR (McCain)
tipos_pozo = data_sorted['tipopozo'].unique()
selected_tipos_pozo = st.sidebar.multiselect("Seleccionar tipo de pozo:", tipos_pozo)

# Create a dropdown list for 'empresa'
empresas = data_sorted['empresa'].unique()
selected_empresa = st.sidebar.selectbox("Seleccionar operadora:", empresas)

# Filter data based on selected 'tipo pozo' and 'empresa'
matching_data = data_sorted[
    (data_sorted['tipopozo'].isin(selected_tipos_pozo)) &
    (data_sorted['empresa'] == selected_empresa)
]

# Get unique 'sigla' values based on selected 'empresa' and 'tipo pozo'
siglas_for_selected_empresa = matching_data['sigla'].unique()

# Create a dropdown list for 'sigla'
selected_sigla = st.sidebar.selectbox("Seleccionar sigla del pozo", siglas_for_selected_empresa)

# Filter data for matching 'empresa' and 'sigla'
matching_data = data_sorted[
    (data_sorted['empresa'] == selected_empresa) &
    (data_sorted['sigla'] == selected_sigla)
]

# Calculate gas rate for the filtered data
matching_data['gas_rate'] = matching_data['prod_gas'] / matching_data['tef']

# Calculate oil rate and water rate for the filtered data
matching_data['oil_rate'] = matching_data['prod_pet'] / matching_data['tef']
matching_data['water_rate'] = matching_data['prod_agua'] / matching_data['tef']

# Calculate cumulative Gp, Np, and Wp for the selected well
matching_data['cumulative_gas'] = matching_data['Gp']
matching_data['cumulative_oil'] = matching_data['Np']
matching_data['cumulative_water'] = matching_data.groupby('sigla')['prod_agua'].cumsum()

# Create a counter column for x-axis
matching_data['counter'] = range(1, len(matching_data) + 1)

# Filter data for matching 'tipo pozo'
matching_tipo_pozo_data = data_sorted[data_sorted['tipopozo'].isin(selected_tipos_pozo)]

# Calculate maximum values below 1,000,000 for gas, oil, and water rates
max_gas_rate = matching_data[matching_data['gas_rate'] <= 1000000]['gas_rate'].max()
max_oil_rate = matching_data[matching_data['oil_rate'] <= 1000000]['oil_rate'].max()
max_water_rate = matching_data[matching_data['water_rate'] <= 1000000]['water_rate'].max()

# Round the maximum rates to one decimal place
max_gas_rate_rounded = round(max_gas_rate, 1)
max_oil_rate_rounded = round(max_oil_rate, 1)
max_water_rate_rounded = round(max_water_rate, 1)

st.header(selected_sigla)
col1, col2, col3 = st.columns(3)
col1.metric(label=f":red[Caudal Máximo de Gas (km3/d)]", value=max_gas_rate_rounded)
col2.metric(label=f":green[Caudal Máximo de Petróleo (m3/d)]", value=max_oil_rate_rounded)
col3.metric(label=f":blue[Caudal Máximo de Agua (m3/d)]", value=max_water_rate_rounded)

# Plot gas rate using Plotly with 'date' as x-axis
gas_rate_fig = go.Figure()

gas_rate_fig.add_trace(
    go.Scatter(
        x=matching_data['date'],  
        y=matching_data['gas_rate'],
        mode='lines+markers',
        name='Gas Rate',
        line=dict(color='red')
    )
)

gas_rate_fig.update_layout(
    title=f"Historia de Producción de Gas del pozo: {selected_sigla}",
    xaxis_title="Fecha",  
    yaxis_title="Caudal de Gas (km3/d)"
)
gas_rate_fig.update_yaxes(range=[0, None])
st.plotly_chart(gas_rate_fig)

# Plot oil rate using Plotly with 'date' as x-axis
oil_rate_fig = go.Figure()

oil_rate_fig.add_trace(
    go.Scatter(
        x=matching_data['date'],  
        y=matching_data['oil_rate'],
        mode='lines+markers',
        name='Oil Rate',
        line=dict(color='green')
    )
)

oil_rate_fig.update_layout(
    title=f"Historia de Producción de Petróleo del pozo: {selected_sigla}",
    xaxis_title="Fecha",  
    yaxis_title="Caudal de Petróleo (m3/d)"
)
oil_rate_fig.update_yaxes(rangemode='tozero')
st.plotly_chart(oil_rate_fig)

# Plot water rate using Plotly with 'date' as x-axis
water_rate_fig = go.Figure()

water_rate_fig.add_trace(
    go.Scatter(
        x=matching_data['date'],  
        y=matching_data['water_rate'],
        mode='lines+markers',
        name='Water Rate',
        line=dict(color='blue')
    )
)

water_rate_fig.update_layout(
    title=f"Historia de Producción de Agua del pozo: {selected_sigla}",
    xaxis_title="Fecha",  
    yaxis_title="Caudal de Agua (m3/d)"
)
water_rate_fig.update_yaxes(range=[0, None])
st.plotly_chart(water_rate_fig)

# Define the function to prepare the DataFrame for download
def prepare_dataframe_for_download(data):
    renamed_columns = {
        'sigla': 'Sigla',
        'date': 'Fecha',
        'oil_rate': 'Caudal de petróleo (m3/d)',
        'gas_rate': 'Caudal de gas(m3/d)',
        'water_rate': 'Caudal de agua (m3/d)',
        'Np': 'Acumulada de Petróleo (m3)',
        'Gp': 'Acumulada de Gas (m3)',
        'Wp': 'Acumulada de Agua (m3)',
        'tef': 'TEF',
        'tipoextraccion': 'Tipo de Extracción',
        'tipopozo': 'Tipo de Pozo',
        'empresa': 'Empresa',
        'formacion': 'Formación',
        'areayacimiento': 'Área yacimiento',
    }
    # Rename the columns
    data_renamed = data.rename(columns=renamed_columns)
    return data_renamed

# Prepare the data for download
matching_data_renamed = prepare_dataframe_for_download(matching_data)

# Display the data table with renamed columns
st.write(matching_data_renamed)

# Define the function to convert DataFrame to CSV
@st.cache
def convert_dataframe_to_csv(data):
    # Convert DataFrame to CSV and encode it as utf-8
    csv = data.to_csv(index=False).encode('utf-8')
    return csv

# Call the function to convert DataFrame to CSV
csv_data = convert_dataframe_to_csv(matching_data_renamed)

# Add a button to download the CSV file
if st.button(f"Descargar tabla como archivo CSV"):
    st.download_button(
        label="Descargar CSV",
        data=csv_data,
        file_name=f'{selected_sigla}.csv',
        mime='text/csv',
    )

