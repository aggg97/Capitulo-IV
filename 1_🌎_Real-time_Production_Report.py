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

from dateutil.relativedelta import relativedelta

# Find the latest date in the dataset
latest_date_non_official = data_filtered['date'].max()

# Subtract 1 month from the latest date
latest_date = latest_date_non_official - relativedelta(months=1)

print(latest_date)

# Filter the dataset to include only rows from the latest date
latest_data = data_filtered[data_filtered['date'] == latest_date]

# Calculate total gas and oil rates for the latest date
total_gas_rate = latest_data['gas_rate'].sum() / 1000
total_oil_rate = latest_data['oil_rate'].sum() / 1000

# Convert oil rate to barrels per day (bpd)
oil_rate_bpd = total_oil_rate * 6.28981

# Round the total rates to one decimal place
total_gas_rate_rounded = round(total_gas_rate, 1)
total_oil_rate_rounded = round(total_oil_rate, 1)
oil_rate_bpd_rounded = round(oil_rate_bpd, 1)

print(total_gas_rate_rounded,total_oil_rate_rounded,oil_rate_bpd_rounded)

# Group and aggregate data for plotting
company_summary = data_filtered.groupby(['empresaNEW', 'date']).agg(
    total_gas_rate=('gas_rate', 'sum'),
    total_oil_rate=('oil_rate', 'sum')
).reset_index()

# Determine top 10 companies by total oil production
top_companies = company_summary.groupby('empresaNEW')['total_oil_rate'].sum().nlargest(10).index

# Aggregate data for top companies and "Others"
company_summary['empresaNEW'] = company_summary['empresaNEW'].apply(lambda x: x if x in top_companies else 'Otros')
company_summary_aggregated = company_summary.groupby(['empresaNEW', 'date']).agg(
    total_gas_rate=('total_gas_rate', 'sum'),
    total_oil_rate=('total_oil_rate', 'sum')
).reset_index()

# Count wells per company
well_count = data_filtered.groupby('empresaNEW')['sigla'].nunique().reset_index()
well_count.columns = ['empresaNEW', 'well_count']

# Determine top 10 companies by number of wells
top_wells_companies = well_count.nlargest(10, 'well_count')['empresaNEW']

# Filter well_count to include only top companies
well_count_top = well_count[well_count['empresaNEW'].isin(top_wells_companies)]

# Determine the starting year for each well
well_start_year = data_filtered.groupby('sigla')['anio'].min().reset_index()
well_start_year.columns = ['sigla', 'start_year']

# Merge the start year back to the original data
data_with_start_year = pd.merge(data_filtered, well_start_year, on='sigla')

# Group data by start year and date for stacked area plots
yearly_summary = data_with_start_year.groupby(['start_year', 'date']).agg(
    total_gas_rate=('gas_rate', 'sum'),
    total_oil_rate=('oil_rate', 'sum')
).reset_index()

# Filter out rows where cumulative gas and oil production are zero or less
yearly_summary = yearly_summary[(yearly_summary['total_gas_rate'] > 0) & (yearly_summary['total_oil_rate'] > 0)]

st.write("Fecha de Última Alocación Finalizada y Consolidada*: ", latest_date.date())
st.caption("*A mediados de cada mes se realiza el cierre oficial \
de los datos correspondientes al mes anterior. Para garantizar la \
precisión y evitar mostrar información incompleta o no consolidada, \
este reporte presenta únicamente los datos del mes anterior ya finalizados, \
completos y representativos.")
                 
# Display total gas rate and oil rate metrics
col1, col2, col3 = st.columns(3)
col1.metric(label=":red[Total Caudal de Gas (MMm³/d)]", value=total_gas_rate_rounded)
col2.metric(label=":green[Total Caudal de Petróleo (km³/d)]", value=total_oil_rate_rounded)
col3.metric(label=":green[Total Caudal de Petróleo (kbpd)]", value=oil_rate_bpd_rounded)

# ------------------------ PLOTS ------------------------

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Plot gas rate by company
fig_gas_company = px.area(
    company_summary_aggregated, 
    x='date', y='total_gas_rate', color='empresaNEW', 
    title="Caudal de Gas por Empresa"
)
fig_gas_company.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Caudal de Gas (km³/d)",
    legend_title="Empresa",
    legend=dict(
        orientation="h",  # Horizontal legend
        yanchor="top",  # Position the legend at the top
        y=-0.3,  # Position the legend further above the plot area
        xanchor="center",  # Center the legend horizontally
        x=0.5,  # Center the legend horizontally
        font=dict(size=10)  # Adjust font size to fit space
    ),
  
)

# Checkbox for logarithmic scale for gas
log_scale_gas = st.checkbox('Escala semilog Caudal de Gas')
st.caption("Nota: Activar la escala semilog facilita la detección rápida \
de tendencias lineales en los datos, permitiendo identificar patrones de \
crecimiento exponencial en la producción de manera más efectiva.")

# If the checkbox for log scale is selected, update y-axis to log scale
if log_scale_gas:
    fig_gas_company.update_layout(
        yaxis=dict(type='log',dtick=1)
    )

# Display the chart with the log scale adjustment (if applicable)
st.plotly_chart(fig_gas_company)

# Plot oil rate by company
fig_oil_company = px.area(
    company_summary_aggregated, 
    x='date', y='total_oil_rate', color='empresaNEW', 
    title="Caudal de Petróleo por Empresa"
)
fig_oil_company.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Caudal de Petróleo (m³/d)",
    legend_title="Empresa",
    legend=dict(
        orientation="h",  # Horizontal legend
        yanchor="top",  # Position the legend at the top
        y=-0.3,  # Position the legend further above the plot area
        xanchor="center",  # Center the legend horizontally
        x=0.5,  # Center the legend horizontally
        font=dict(size=10)  # Adjust font size to fit space
    )
)  

# Checkbox for logarithmic scale for oil
log_scale_oil = st.checkbox('Escala semilog Caudal de Petróleo')

# If the checkbox for log scale is selected, update y-axis to log scale
if log_scale_oil:
    fig_oil_company.update_layout(
        yaxis=dict(type='log',dtick=1)
    )

# Display the chart with the log scale adjustment (if applicable)
st.plotly_chart(fig_oil_company)

# Plot for gas rate by start year
fig_gas_year = px.area(
    yearly_summary, 
    x='date', y='total_gas_rate', color='start_year', 
    title="Caudal de Gas por Campaña"
)
fig_gas_year.update_layout(
    legend_title="Campaña",
    legend=dict(
        orientation="h",  # Horizontal legend
        yanchor="top",  # Position the legend at the top
        y=-0.3,  # Position the legend further above the plot area
        xanchor="center",  # Center the legend horizontally
        x=0.5,  # Center the legend horizontally
        font=dict(size=10)  # Adjust font size to fit space
    ),
    
    xaxis_title="Fecha",
    yaxis_title="Caudal de Gas (km³/d)"
    
)

# Plot for oil rate by start year
fig_oil_year = px.area(
    yearly_summary, 
    x='date', y='total_oil_rate', color='start_year', 
    title="Caudal de Petróleo por Campaña"
)
fig_oil_year.update_layout(
    legend_title="Campaña",
    legend=dict(
        orientation="h",  # Horizontal legend
        yanchor="top",  # Position the legend at the top
        y=-0.3,  # Position the legend further above the plot area
        xanchor="center",  # Center the legend horizontally
        x=0.5,  # Center the legend horizontally
        font=dict(size=10)  # Adjust font size to fit space
    ),
    
    xaxis_title="Fecha",
    yaxis_title="Caudal de Petróleo (m³/d)"
)

# Plot the charts
st.plotly_chart(fig_gas_year)
st.plotly_chart(fig_oil_year)





