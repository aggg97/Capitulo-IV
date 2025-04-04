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
st.header(f":blue[Watchlist Nuevos Pozos VM]")
image = Image.open('Vaca Muerta rig.png')
st.sidebar.image(image)

# Create a multiselect list for 'sigla'
selected_sigla = st.sidebar.multiselect("Seleccionar siglas de los pozos a comparar", data_sorted['sigla'].unique())

# Filter data for matching 'sigla'
filtered_data = data_sorted[
    (data_sorted['sigla'].isin(selected_sigla))
]

# Find highest gas and oil rates in the entire dataset
max_gas_rate = data_sorted['gas_rate'].max()
max_oil_rate = data_sorted['oil_rate'].max()

# Plot gas rate using Plotly
gas_rate_fig = go.Figure()

# Define colors for the plots
gas_gp_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

for i, sigla in enumerate(selected_sigla):
    filtered_well_data = filtered_data[filtered_data['sigla'] == sigla]
    
    # Filter data to start when 'Gp' is different from zero
    filtered_well_data = filtered_well_data[filtered_well_data['Gp'] != 0]
    
    # Add a counter column to the filtered data
    filtered_well_data['counter'] = range(1, len(filtered_well_data) + 1)
    
    gas_rate_fig.add_trace(
        go.Scatter(
            x=filtered_well_data['counter'],  # Use the counter as x-axis
            y=filtered_well_data['gas_rate'],
            mode='lines+markers',
            name=f'Gas Rate - {sigla}',
            line=dict(color=gas_gp_palette[i % len(gas_gp_palette)]),  # Use the Gas Rate and Gp palette
        )
    )

# Add a horizontal line for the highest gas rate
gas_rate_fig.add_trace(
    go.Scatter(
        x=[0, len(filtered_data)],  # X values for horizontal line
        y=[max_gas_rate, max_gas_rate],  # Y values for the highest gas rate
        mode='lines',
        name='Highest Gas Rate',
        line=dict(color='red', dash='dash')
    )
)

gas_rate_fig.update_layout(
    title="Historia de Producción de Gas",
    xaxis_title="Meses",
    yaxis_title="Caudal de Gas (m³/día)",
)

# Display the gas rate Plotly figure in the Streamlit app
st.plotly_chart(gas_rate_fig)

# Plot oil rate using Plotly
oil_rate_fig = go.Figure()

for i, sigla in enumerate(selected_sigla):
    filtered_well_data = filtered_data[filtered_data['sigla'] == sigla]
    
    # Filter data to start when 'Np' is different from zero
    filtered_well_data = filtered_well_data[filtered_well_data['Np'] != 0]
    
    # Add a counter column to the filtered data
    filtered_well_data['counter'] = range(1, len(filtered_well_data) + 1)
    
    oil_rate_fig.add_trace(
        go.Scatter(
            x=filtered_well_data['counter'],  # Use the counter as x-axis
            y=filtered_well_data['oil_rate'],
            mode='lines+markers',
            name=f'Oil Rate - {sigla}',
            line=dict(color=gas_gp_palette[i % len(gas_gp_palette)]),  # Use the same palette
        )
    )

# Add a horizontal line for the highest oil rate
oil_rate_fig.add_trace(
    go.Scatter(
        x=[0, len(filtered_data)],  # X values for horizontal line
        y=[max_oil_rate, max_oil_rate],  # Y values for the highest oil rate
        mode='lines',
        name='Highest Oil Rate',
        line=dict(color='blue', dash='dash')
    )
)

oil_rate_fig.update_layout(
    title="Historia de Producción de Petróleo",
    xaxis_title="Meses",
    yaxis_title="Caudal de Petróleo (m³/día)",
)

# Display the oil rate Plotly figure in the Streamlit app
st.plotly_chart(oil_rate_fig)
