import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import plotly.express as px

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
    
    st.info("Utilizando datos recuperados de la memoria (Session State).")
    
else:
    st.warning("⚠️ No se han cargado los datos. Por favor, vuelve a la Página Principal.")
    
    # El link para regresar
    st.page_link("main.py", label="Ir a la Página Principal para cargar datos", icon="🏠")

# Sidebar filters
st.header(f":blue[Análisis de Producción No Convencional]")
image = Image.open('Vaca Muerta rig.png')
st.sidebar.image(image)
st.sidebar.title("Por favor filtrar aquí:")

# Selectbox for companies
selected_company = st.sidebar.selectbox(
    "Seleccione la empresa",
    options=data_sorted['empresa'].unique()
)

# Filter data based on selected company
company_data = data_sorted[data_sorted['empresa'] == selected_company]

# Summarize production data by field area
summary_df = company_data.groupby(['areayacimiento', 'date']).agg(
    total_gas_rate=('gas_rate', 'sum'),
    total_oil_rate=('oil_rate', 'sum')
).reset_index()

# Plot total oil production by field area over time using stacked area plot
oil_rate_fig = go.Figure()

color_palette = px.colors.qualitative.Set3  # Use a distinct color palette

for i, area in enumerate(summary_df['areayacimiento'].unique()):
    area_data = summary_df[summary_df['areayacimiento'] == area]
    oil_rate_fig.add_trace(
        go.Scatter(
            x=area_data['date'],
            y=area_data['total_oil_rate'],
            mode='lines',
            name=f'{area} - Oil Rate',
            stackgroup='one',  # This line makes it a stacked area plot
            line=dict(color=color_palette[i % len(color_palette)]),
            hovertemplate='Fecha: %{x}<br>Caudal de Petróleo: %{y:.2f} m3/d'
        )
    )

oil_rate_fig.update_layout(
    title="Producción Total de Petróleo por Área de Yacimiento",
    xaxis_title="Fecha",
    yaxis_title="Caudal de Petróleo (m3/d)",
    hovermode='x unified',
    legend_title="Área de Yacimiento"
)

# Display the oil production plot
st.plotly_chart(oil_rate_fig, use_container_width=True)

# Plot total gas production by field area over time using stacked area plot
gas_rate_fig = go.Figure()

for i, area in enumerate(summary_df['areayacimiento'].unique()):
    area_data = summary_df[summary_df['areayacimiento'] == area]
    gas_rate_fig.add_trace(
        go.Scatter(
            x=area_data['date'],
            y=area_data['total_gas_rate'],
            mode='lines',
            name=f'{area} - Gas Rate',
            stackgroup='one',  # This line makes it a stacked area plot
            line=dict(color=color_palette[i % len(color_palette)]),
            hovertemplate='Fecha: %{x}<br>Caudal de Gas: %{y:.2f} km3/d'
        )
    )

gas_rate_fig.update_layout(
    title="Producción Total de Gas por Área de Yacimiento",
    xaxis_title="Fecha",
    yaxis_title="Caudal de Gas (km3/d)",
    hovermode='x unified',
    legend_title="Área de Yacimiento"
)

# Display the gas production plot
st.plotly_chart(gas_rate_fig, use_container_width=True)

# Selectbox for areas based on selected company
selected_area = st.selectbox(
    "Seleccione el área de yacimiento",
    options=company_data['areayacimiento'].unique()
)

# Number input for year selection
selected_year = st.number_input('Ingrese el año', min_value=int(data_sorted['anio'].min()), max_value=int(data_sorted['anio'].max()), value=int(data_sorted['anio'].max()), step=1)

# Filter data based on selected area and year
area_year_data = company_data[(company_data['areayacimiento'] == selected_area) & (company_data['anio'] == selected_year)]

# Identify top 10 wells for oil and gas based on the highest production rates in the selected year
top_10_oil_wells = area_year_data.sort_values(by='oil_rate', ascending=False).head(10)['sigla'].unique()
top_10_gas_wells = area_year_data.sort_values(by='gas_rate', ascending=False).head(10)['sigla'].unique()

# Filter data for the top 10 wells since the beginning of the oldest well
top_10_oil_data = company_data[company_data['sigla'].isin(top_10_oil_wells)]
top_10_gas_data = company_data[company_data['sigla'].isin(top_10_gas_wells)]

# Get the oldest date for the top 10 oil wells
oldest_oil_date = top_10_oil_data['date'].min()
top_10_oil_data = top_10_oil_data[top_10_oil_data['date'] >= oldest_oil_date]

# Get the oldest date for the top 10 gas wells
oldest_gas_date = top_10_gas_data['date'].min()
top_10_gas_data = top_10_gas_data[top_10_gas_data['date'] >= oldest_gas_date]

# Plot top 10 wells production profile for oil
top_oil_fig = go.Figure()

for i, well in enumerate(top_10_oil_wells):
    well_data = top_10_oil_data[top_10_oil_data['sigla'] == well]
    top_oil_fig.add_trace(
        go.Scatter(
            x=well_data['date'],
            y=well_data['oil_rate'],
            mode='lines+markers',
            name=f'{well} - Oil Rate',
            line=dict(color=color_palette[i % len(color_palette)]),
            hovertemplate='Fecha: %{x}<br>Caudal de Petróleo: %{y:.2f} m3/d'
        )
    )

top_oil_fig.update_layout(
    title=f"Top 10 Pozos por Perfil de Producción de Petróleo desde {oldest_oil_date.year}",
    xaxis_title="Fecha",
    yaxis_title="Caudal de Petróleo (m3/d)",
    hovermode='x unified',
    legend_title="Pozos"
)

# Display the top 10 wells oil production plot
st.plotly_chart(top_oil_fig, use_container_width=True)

# Plot top 10 wells production profile for gas
top_gas_fig = go.Figure()

for i, well in enumerate(top_10_gas_wells):
    well_data = top_10_gas_data[top_10_gas_data['sigla'] == well]
    top_gas_fig.add_trace(
        go.Scatter(
            x=well_data['date'],
            y=well_data['gas_rate'],
            mode='lines+markers',
            name=f'{well} - Gas Rate',
            line=dict(color=color_palette[i % len(color_palette)]),
            hovertemplate='Fecha: %{x}<br>Caudal de Gas: %{y:.2f} km3/d'
        )
    )

top_gas_fig.update_layout(
    title=f"Top 10 Pozos por Perfil de Producción de Gas desde {oldest_gas_date.year}",
    xaxis_title="Fecha",
    yaxis_title="Caudal de Gas (km3/d)",
    hovermode='x unified',
    legend_title="Pozos"
)

# Display the top 10 wells gas production plot
st.plotly_chart(top_gas_fig, use_container_width=True)
