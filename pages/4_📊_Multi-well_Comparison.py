import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

COLUMNS = [
    'sigla',  # atemporal
    'anio',  # temporal
    'mes',  # temporal
    'prod_pet',  # temporal
    'prod_gas',  # temporal
    'prod_agua',  # temporal
    'iny_gas',  # temporal
    'tef',  # temporal
    'tipoextraccion',  # atemporal
    'tipopozo',  # atemporal
    'empresa',  # atemporal
    'formacion',  # atemporal
    'areayacimiento',  # atemporal
    'fecha_data'  # temporal
]

COLUMNS_NAMES = [
    'Sigla',
    'Año',
    'Mes',
    'Producción de Petróleo (m3)',
    'Producción de Gas (km3)',
    'Producción de Agua (m3)',
    'Inyección de Gas (km3)',
    'TEF',
    'Tipo de Extracción',
    'Tipo de Pozo',
    'Empresa',
    'Formación',
    'Área yacimiento',
    'Fecha de Datos'
]

# Define palettes for Gas Rate and Gp, Oil Rate and Np, and Water Rate and Wp
gas_gp_palette = ['#FF0000', '#FFA07A', '#FA8072', '#E9967A', '#F08080', '#CD5C5C', '#DC143C', '#B22222', '#8B0000']
oil_np_palette = ['#008000', '#006400', '#90EE90', '#98FB98', '#8FBC8F', '#3CB371', '#2E8B57', '#808000', '#556B2F', '#6B8E23']
water_wp_palette = ['#0000FF', '#0000CD', '#00008B', '#000080', '#191970', '#7B68EE', '#6A5ACD', '#483D8B', '#B0E0E6', '#ADD8E6', '#87CEFA', '#87CEEB', '#00BFFF', '#B0C4DE', '#1E90FF', '#6495ED']

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


# Add a new column "date" by combining year and month
data_sorted['date'] = pd.to_datetime(data_sorted['anio'].astype(str) + '-' + data_sorted['mes'].astype(str) + '-1')
data_sorted['date'] = pd.to_datetime(data_sorted['date'])

# Create a Pivot Table to Calculate Maximum Oil and Gas Rates for Each Well
pivot_table = data_sorted.pivot_table(
    values=['gas_rate', 'oil_rate', 'water_rate'],
    index=['sigla'],
    aggfunc={'gas_rate': 'max', 'oil_rate': 'max', 'water_rate': 'max'}
)

# Step 2: Create a New DataFrame with Maximum Oil and Gas Rates
max_rates_df = pivot_table.reset_index()
max_rates_df['GOR'] = max_rates_df['gas_rate'] / max_rates_df['oil_rate']
max_rates_df['GOR'] = max_rates_df['GOR'].fillna(100000)

# Add a new column "Fluido McCain" based on conditions
max_rates_df['Fluido McCain'] = max_rates_df.apply(
    lambda row: 'Gas' if row['oil_rate'] == 0 or row['GOR'] > 3000 else 'Petróleo',
    axis=1
)

st.header(f":blue[Capítulo IV Dataset - Producción No Convencional]")
image = Image.open('Vaca Muerta rig.png')
st.sidebar.image(image)
st.sidebar.title("Por favor filtrar aquí: ")

# Create a dropdown list for "Fluido McCain"
selected_fluido = st.sidebar.selectbox("Seleccionar tipo de fluido según McCain:", max_rates_df['Fluido McCain'].unique())

# Create a multiselect list for 'sigla'
selected_sigla = st.sidebar.multiselect("Seleccionar siglas de los pozos a comparar", max_rates_df['sigla'])

# Filter data for matching 'sigla'
filtered_data = data_sorted[
    (data_sorted['sigla'].isin(selected_sigla))
]


# Plot gas rate using Plotly
gas_rate_fig = go.Figure()

for i, sigla in enumerate(selected_sigla):
    filtered_well_data = filtered_data[filtered_data['sigla'] == sigla]
    
    # Filter data to start when 'Np' is different from zero
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

gas_rate_fig.update_layout(
    title="Historia de Producción de Gas",
    xaxis_title="Meses",
    yaxis_title="Caudal de Gas (km3/d)",
)

# Display the gas rate Plotly figure in the Streamlit app
st.plotly_chart(gas_rate_fig)

# Define a list of specific colors for oil rate plots
oil_color_list = ['#008000', '#006400', '#90EE90', '#98FB98', '#8FBC8F', '#3CB371', '#2E8B57', '#808000', '#556B2F', '#6B8E23']

oil_rate_fig = go.Figure()

for i, sigla in enumerate(selected_sigla):
    filtered_well_data = filtered_data[filtered_data['sigla'] == sigla]
    
    # Filter data to start when 'Np' is different from zero
    filtered_well_data = filtered_well_data[filtered_well_data['Gp'] != 0]
    
    # Add a counter column to the filtered data
    filtered_well_data['counter'] = range(1, len(filtered_well_data) + 1)
    
    oil_rate_fig.add_trace(
        go.Scatter(
            x=filtered_well_data['counter'],  # Use the counter as x-axis
            y=filtered_well_data['oil_rate'],
            mode='lines+markers',
            name=f'Oil Rate - {sigla}',
            line=dict(color=oil_np_palette[i % len(oil_np_palette)]),  # Use the Oil Rate and Np palette
        )
    )

oil_rate_fig.update_layout(
    title="Historia de Producción de Petróleo",
    xaxis_title="Meses",
    yaxis_title="Caudal de Petróleo (m3/d)",
)

# Display the oil rate Plotly figure in the Streamlit app
st.plotly_chart(oil_rate_fig)

# Define a list of specific colors for water rate plots
water_color_list = ['#0000FF', '#0000CD', '#00008B', '#000080', '#191970', '#7B68EE', '#6A5ACD', '#483D8B', '#B0E0E6', '#ADD8E6', '#87CEFA', '#87CEEB', '#00BFFF', '#B0C4DE', '#1E90FF', '#6495ED']

water_rate_fig = go.Figure()

for i, sigla in enumerate(selected_sigla):
    filtered_well_data = filtered_data[filtered_data['sigla'] == sigla]
    
    # Filter data to start when 'Np' is different from zero
    filtered_well_data = filtered_well_data[filtered_well_data['Gp'] != 0]
    
    # Add a counter column to the filtered data
    filtered_well_data['counter'] = range(1, len(filtered_well_data) + 1)
    
    water_rate_fig.add_trace(
        go.Scatter(
            x=filtered_well_data['counter'],  # Use the counter as x-axis
            y=filtered_well_data['water_rate'],
            mode='lines+markers',
            name=f'Water Rate - {sigla}',
            line=dict(color=water_wp_palette[i % len(water_wp_palette)]),  # Use the Water Rate and Wp palette
        )
    )

water_rate_fig.update_layout(
    title="Historia de Producción de Agua",
    xaxis_title="Meses",
    yaxis_title="Caudal de Agua (m3/d)",
)

# Display the water rate Plotly figure in the Streamlit app
st.plotly_chart(water_rate_fig)


if selected_fluido and selected_sigla:
    # Create separate figures for Gp, Np, and Wp
    gp_fig = go.Figure()
    np_fig = go.Figure()
    wp_fig = go.Figure()

    for i, sigla in enumerate(selected_sigla):
        filtered_well_data = filtered_data[filtered_data['sigla'] == sigla]

        # Filter data to start when 'Np' is different from zero
        filtered_well_data = filtered_well_data[filtered_well_data['Gp'] != 0]

        # Add a counter column to the filtered data
        filtered_well_data['counter'] = range(1, len(filtered_well_data) + 1)

        # Plot Np (oil_rate) vs cumulative oil production (Np)
        np_fig.add_trace(
            go.Scatter(
                x=filtered_well_data['Np'],  # Use cumulative oil production (Np) as x-axis
                y=filtered_well_data['oil_rate'],  # Use oil_rate as y-axis
                mode='lines+markers',
                name=f'Oil Rate - {sigla}',
                line=dict(color=oil_np_palette[i % len(oil_np_palette)]),  # Use the Oil Rate palette
            )
        )

        # Plot Gp (gas_rate) vs cumulative gas production (Gp)
        gp_fig.add_trace(
            go.Scatter(
                x=filtered_well_data['Gp'] / 1000, # Use cumulative gas production (Gp) as x-axis
                y=filtered_well_data['gas_rate'],  # Use gas_rate as y-axis
                mode='lines+markers',
                name=f'Gas Rate - {sigla}',
                line=dict(color=gas_gp_palette[i % len(gas_gp_palette)]),  # Use the Gas Rate palette
            )
        )

        # Plot Wp (water_rate) vs cumulative water production (Wp)
        wp_fig.add_trace(
            go.Scatter(
                x=filtered_well_data['Wp'],  # Use cumulative water production (Wp) as x-axis
                y=filtered_well_data['water_rate'],  # Use water_rate as y-axis
                mode='lines+markers',
                name=f'Water Rate - {sigla}',
                line=dict(color=water_wp_palette[i % len(water_wp_palette)]),  # Use the Water Rate palette
            )
        )

    # Update layout for Np (oil_rate) figure
    np_fig.update_layout(
        title="Acumulada de Petróleo (m3) vs Caudal de Petróleo (m3/d)",
        xaxis_title="Np (m3)",
        yaxis_title="Caudal de Petróleo (m3/d)",
    )

    # Update layout for Gp (gas_rate) figure
    gp_fig.update_layout(
        title="Acumulada de Gas (MMm3) vs Caudal de Gas (km3/d)",
        xaxis_title="Gp (MMm3)",
        yaxis_title="Caudal de Gas (km3/d)",
    )

    # Update layout for Wp (water_rate) figure
    wp_fig.update_layout(
        title="Acumulada de Agua (m3) vs Caudal de Agua (m3/d)",
        xaxis_title="Wp (m3)",
        yaxis_title="Caudal de Agua (m3/d)",
    )

    # Display the updated Plotly figures in the Streamlit app
    st.plotly_chart(np_fig)
    st.plotly_chart(gp_fig)
    st.plotly_chart(wp_fig)
else:
    # If Fluido McCain or sigla is not selected, display a message
    st.subheader("")
    st.write("")



