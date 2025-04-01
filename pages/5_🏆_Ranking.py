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
st.header(f":blue[Ranking y Records]")
image = Image.open('Vaca Muerta rig.png')
st.sidebar.image(image)

# Filter out rows where TEF is zero for calculating metrics
data_filtered = data_sorted[(data_sorted['tef'] > 0)]

# Find the latest date in the dataset
latest_date = data_filtered['date'].max()

from dateutil.relativedelta import relativedelta

# Find the latest date in the dataset
latest_date_non_official = data_filtered['date'].max()

# Subtract 1 month from the latest date
latest_date = latest_date_non_official - relativedelta(months=1)

print(latest_date)

# Filter the dataset to include only rows from the latest date
latest_data = data_filtered[data_filtered['date'] == latest_date]


# ------------------------ DATA CLEANING ------------------------

@st.cache_data
# Load and preprocess the fracture data
def load_and_sort_data_frac(dataset_url):
    df_frac = pd.read_csv(dataset_url)
    return df_frac

# URL of the fracture dataset
dataset_frac_url = "http://datos.energia.gob.ar/dataset/71fa2e84-0316-4a1b-af68-7f35e41f58d7/resource/2280ad92-6ed3-403e-a095-50139863ab0d/download/datos-de-fractura-de-pozos-de-hidrocarburos-adjunto-iv-actualizacin-diaria.csv"

# Load the fracture data
df_frac = load_and_sort_data_frac(dataset_frac_url)


# Create a new column for the total amount of arena (sum of national and imported arena)
df_frac['arena_total_tn'] = df_frac['arena_bombeada_nacional_tn'] + df_frac['arena_bombeada_importada_tn']

# Apply the cut-off conditions:
# longitud_rama_horizontal_m > 100
# cantidad_fracturas > 6
# arena_total_tn > 100
df_frac = df_frac[
    (df_frac['longitud_rama_horizontal_m'] > 100) &
    (df_frac['cantidad_fracturas'] > 6) &
    (df_frac['arena_total_tn'] > 100)
]

# Check the filtered data
print(df_frac.info())

# Define the columns to check for outliers (now using 'arena_total_tn' as the total arena)
columns_to_check = [
    'longitud_rama_horizontal_m',
    'cantidad_fracturas',
    'arena_total_tn',
]

# ------------------------ Fluido segun McCain ------------------------

st.sidebar.caption("")

st.sidebar.caption("Nota: Para excluir los pozos clasificados como 'Otro tipo', \
se crea una nueva columna que utiliza la definición de fluido basada \
en el criterio de GOR según McCain. Esto permite reclasificar estos pozos como \
'Gasíferos' o 'Petrolíferos' de manera más precisa")

image = Image.open('McCain.png')
st.sidebar.image(image)

# Step 1: Create a Pivot Table with Cumulated Values
pivot_table = data_filtered.pivot_table(
    values=['Np', 'Gp', 'Wp'],
    index=['sigla'],
    aggfunc={'Np': 'max', 'Gp': 'max', 'Wp': 'max'}
)

print(pivot_table.info())

# Step 2: Create a New DataFrame with GOR
cum_df = pivot_table.reset_index()
cum_df['GOR'] = (cum_df['Gp'] / cum_df['Np']) * 1000
cum_df['GOR'] = cum_df['GOR'].fillna(100000)  # Handle NaN values

# Step 3: Add a new column "Fluido McCain" based on conditions
cum_df['Fluido McCain'] = cum_df.apply(
    lambda row: 'Gasífero' if row['Np'] == 0 or row['GOR'] > 3000 else 'Petrolífero',
    axis=1
)

# Step 4: Ensure `tipopozo` is unique for each `sigla` and merge it
tipopozo_unique = data_filtered[['sigla', 'tipopozo']].drop_duplicates(subset=['sigla'])
cum_df = cum_df.merge(tipopozo_unique, on='sigla', how='left')

# Step 5: Create the 'tipopozoNEW' column based on the 'tipopozo' and 'Fluido McCain'
cum_df['tipopozoNEW'] = cum_df.apply(
    lambda row: row['Fluido McCain'] if row['tipopozo'] == 'Otro tipo' else row['tipopozo'],
    axis=1
)

# Step 6: Calculate WOR and WGR
cum_df['WOR'] = cum_df['Wp'] / cum_df['Np']
cum_df['WOR'] = cum_df['WOR'].fillna(100000)  # Handle NaN values
cum_df['WGR'] = (cum_df['Wp'] / cum_df['Gp']) * 1000
cum_df['WGR'] = cum_df['WGR'].fillna(100000)  # Handle NaN values

# Step 7: Create the final table with the desired columns
cum_df = cum_df[['sigla', 'WGR', 'WOR', 'GOR', 'Fluido McCain', 'tipopozoNEW']]

# Step 8: Merge `tipopozoNEW` back into `data_filtered`
data_filtered = data_filtered.merge(
    cum_df[['sigla', 'tipopozoNEW']],
    on='sigla',
    how='left'
)

# Display the updated data_filtered
print(data_filtered.columns)
print(cum_df.columns)

# -----------------------------------------------

# Merge the dataframes on 'sigla'
df_merged = pd.merge(
    df_frac,
    cum_df,
    on='sigla',
    how='outer'
).drop_duplicates()

print(df_merged.info())

# --- Tabla consolidada por siglas para usar en reporte ---------

# Calculate additional metrics and create the new DataFrame
def create_summary_dataframe(data_filtered):
    # Calculate Qo peak and Qg peak (maximum oil and gas rates)
    data_filtered['Qo_peak'] = data_filtered[['sigla','oil_rate']].groupby('sigla').transform('max') 
    data_filtered['Qg_peak'] = data_filtered[['sigla','gas_rate']].groupby('sigla').transform('max') 
    
    # Determine the starting year for each well
    data_filtered['start_year'] = data_filtered.groupby('sigla')['anio'].transform('min')

    # Calculate EUR at 30, 90, and 180 days based on dates
    def calculate_eur(group):
        group = group.sort_values('date')  # Ensure the data is sorted by date
        
        # Get the start date for the group
        start_date = group['date'].iloc[0]
        
        # Define target dates
        target_dates = {
            'EUR_30': start_date + relativedelta(days=30),
            'EUR_90': start_date + relativedelta(days=90),
            'EUR_180': start_date + relativedelta(days=180)
        }
        
        # Initialize EUR columns
        for key, target_date in target_dates.items():
            group[key] = group.loc[
                group['date'] <= target_date,
                'Np' if group['tipopozoNEW'].iloc[0] == 'Petrolífero' else 'Gp'
            ].max()
        
        return group

    data_filtered = data_filtered.groupby('sigla', group_keys=False).apply(calculate_eur)
    
    # Create the new DataFrame with selected columns
    summary_df = data_filtered.groupby('sigla').agg({
        'date': 'first',
        'start_year': 'first',
        'empresaNEW': 'first',
        'formprod': 'first',
        'sub_tipo_recurso': 'first',
        'Np': 'max',
        'Gp': 'max',
        'Wp': 'max',
        'Qo_peak': 'max',
        'Qg_peak': 'max',
        'EUR_30': 'max',
        'EUR_90': 'max',
        'EUR_180': 'max'
    }).reset_index()
    
    return summary_df

# Generate the summary DataFrame
summary_df = create_summary_dataframe(data_filtered)


print(summary_df.info())
print(summary_df.columns)

# -----------------------------------------------

# Merge the dataframes on 'sigla'
df_merged_final = pd.merge(
    df_merged,
    summary_df,
    on='sigla',
    how='outer'
).drop_duplicates()

# Filter out rows where 'id_base_fractura_adjiv' is null
df_merged_final = df_merged_final[df_merged_final['id_base_fractura_adjiv'].notna()] 

# Check the dataframe info and columns
print(df_merged_final.info())
print(df_merged_final.columns)

# -----------------------------------------------

# Only keep VMUT as the target formation and filter for SHALE resource type
df_merged_VMUT = df_merged_final[
    (df_merged_final['formprod'] == 'VMUT') & (df_merged_final['sub_tipo_recurso'] == 'SHALE')
]

# ----------------------- Pivot Tables + Plots ------------

# --------------------

st.subheader("Ranking de Mayor Actividad por Empresa", divider="blue")

# Get the current and previous years
current_year = int(df_merged_VMUT['start_year'].max())
previous_year = int(current_year - 1)

# Create a Streamlit selectbox for year selection
selected_year = st.selectbox("Seleccionar Año (Anterior o Actual)", [current_year, previous_year])

# Filter the dataset based on the selected year
filtered_data = df_merged_VMUT[df_merged_VMUT['start_year'] == selected_year]

# Count wells per company and well type
wells_per_company_type = filtered_data.groupby(['empresaNEW', 'tipopozoNEW'])['sigla'].nunique().reset_index()
wells_per_company_type.columns = ['empresaNEW', 'tipopozoNEW', 'well_count']

# Separate the data into two DataFrames: one for Petrolífero and one for Gasífero
wells_petrolifero = wells_per_company_type[wells_per_company_type['tipopozoNEW'] == 'Petrolífero']
wells_gasifero = wells_per_company_type[wells_per_company_type['tipopozoNEW'] == 'Gasífero']

# Get the top 10 companies for Petrolífero wells
top_petrolifero_companies = wells_petrolifero.groupby('empresaNEW')['well_count'].sum().nlargest(10).index
wells_petrolifero_top_10 = wells_petrolifero[wells_petrolifero['empresaNEW'].isin(top_petrolifero_companies)]

# Get the top 10 companies for Gasífero wells
top_gasifero_companies = wells_gasifero.groupby('empresaNEW')['well_count'].sum().nlargest(10).index
wells_gasifero_top_10 = wells_gasifero[wells_gasifero['empresaNEW'].isin(top_gasifero_companies)]

# Plot for Petrolífero wells (top 10 companies) with horizontal bars
fig_petrolifero = px.bar(
    wells_petrolifero_top_10,
    x='well_count',
    y='empresaNEW',
    title=f'Pozos Petrolíferos por Empresa (Año {selected_year})',
    labels={'empresaNEW': 'Empresa', 'well_count': 'Número de Pozos'},
    color='empresaNEW',
    color_discrete_sequence=px.colors.qualitative.Set1,
    orientation='h',
    text='well_count'
)

# Update layout for Petrolífero plot
fig_petrolifero.update_layout(
    xaxis_title='Número de Pozos',
    yaxis_title='Empresa',
    template='plotly_white'
)

# Show the Petrolífero plot in Streamlit
st.plotly_chart(fig_petrolifero, use_container_width=True)

# Plot for Gasífero wells (top 10 companies) with horizontal bars
fig_gasifero = px.bar(
    wells_gasifero_top_10,
    x='well_count',
    y='empresaNEW',
    title=f'Pozos Gasíferos por Empresa (Año {selected_year})',
    labels={'empresaNEW': 'Empresa', 'well_count': 'Número de Pozos'},
    color='empresaNEW',
    color_discrete_sequence=px.colors.qualitative.Set1,
    orientation='h',
    text='well_count'
)

# Update layout for Gasífero plot
fig_gasifero.update_layout(
    xaxis_title='Número de Pozos',
    yaxis_title='Empresa',
    template='plotly_white'
)

# Show the Gasífero plot in Streamlit
st.plotly_chart(fig_gasifero, use_container_width=True)

# -----------------------------
# Remove rows where longitud_rama_horizontal_m is zero and drop duplicates based on 'sigla'
df_merged_VMUT_filtered = df_merged_VMUT[df_merged_VMUT['longitud_rama_horizontal_m'] > 0].drop_duplicates(subset='sigla')
# -----------------------------

import pandas as pd
import streamlit as st

st.subheader("Ranking según Cantidad de Etapas", divider="blue")

# Aggregate the data to calculate max length for each sigla, empresaNEW, and start_year
company_statistics = df_merged_VMUT_filtered.groupby(['start_year', 'empresaNEW', 'sigla']).agg(
    max_lenght=('longitud_rama_horizontal_m', 'max')
).reset_index()

# Round the max_lenght to 0 decimal places
company_statistics['max_lenght'] = company_statistics['max_lenght'].round(0)

# Sort by start_year and max_lenght to get the top 3 sigla per year
company_statistics_sorted = company_statistics.sort_values(['start_year', 'max_lenght'], ascending=[True, False])

# Select the top 3 sigla for each year based on max_lenght
top_max_lenght = company_statistics_sorted.groupby('start_year').head(3)

# Create data for the table with the year appearing only once for each start_year
data_for_max_lenght_table = []
previous_year = None
for _, row in top_max_lenght.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "  # Use blank for repeated years
    data_for_max_lenght_table.append([year_value, row['sigla'], row['empresaNEW'], row['max_lenght']])
    previous_year = row['start_year']

# Convert to a dataframe
df_max_lenght = pd.DataFrame(data_for_max_lenght_table, columns=["Campaña", "Sigla", "Empresa", "Longitud de Rama Maxima (metros)"])

# Display the DataFrame in Streamlit
st.write("**Top 3 Pozos con Máxima Cantidad de Etapas**")
# Display the dataframe in Streamlit
st.dataframe(df_max_lenght,use_container_width=True)

# Aggregate the data to calculate avg length for each empresaNEW and start_year
company_statistics_avg = df_merged_VMUT_filtered.groupby(['start_year', 'empresaNEW']).agg(
    avg_lenght=('longitud_rama_horizontal_m', 'mean')
).reset_index()

# Round the avg_lenght to 0 decimal places
company_statistics_avg['avg_lenght'] = company_statistics_avg['avg_lenght'].round(0)

# Sort by start_year and avg_lenght to get the top 3 empresasNEW per year
company_statistics_sorted_avg = company_statistics_avg.sort_values(['start_year', 'avg_lenght'], ascending=[True, False])

# Select the top 3 empresasNEW for each year based on avg_lenght
top_avg_lenght = company_statistics_sorted_avg.groupby('start_year').head(3)

# Create data for the table with the year appearing only once for each start_year
data_for_avg_lenght_table = []
previous_year = None
for _, row in top_avg_lenght.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "  # Use blank for repeated years
    data_for_avg_lenght_table.append([year_value, row['empresaNEW'], row['avg_lenght']])
    previous_year = row['start_year']

# Convert to a dataframe
df_avg_lenght = pd.DataFrame(data_for_avg_lenght_table, columns=["Campaña", "Empresa", "Longitud de Rama Promedio (metros)"])

# Display the DataFrame in Streamlit
st.write("**Top 3 Empresa con Máxima Cantidad Promedio de Etapas**")
# Display the dataframe in Streamlit
st.dataframe(df_avg_lenght,use_container_width=True)


#----------

st.subheader("Ranking según Longitud de Rama", divider="blue")

# Aggregate the data to calculate max length for each sigla, empresaNEW, and start_year
company_statistics = df_merged_VMUT_filtered.groupby(['start_year', 'empresaNEW', 'sigla']).agg(
    max_lenght=('longitud_rama_horizontal_m', 'max')
).reset_index()

# Round the avg_lenght to 2 decimal places
company_statistics['max_lenght'] = company_statistics['max_lenght'].round(0)

# Sort by start_year and max_lenght to get the top 3 sigla per year
company_statistics_sorted = company_statistics.sort_values(['start_year', 'max_lenght'], ascending=[True, False])

# Select the top 3 sigla for each year based on max_lenght
top_max_lenght = company_statistics_sorted.groupby('start_year').head(3)  # Get the top 3 for each year

# Create data for the table with the year appearing only once for each start_year
data_for_max_lenght_table = []
previous_year = None
for _, row in top_max_lenght.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "  # Use blank for repeated years
    data_for_max_lenght_table.append([year_value, row['sigla'], row['empresaNEW'], row['max_lenght']])
    previous_year = row['start_year']

# Create Plotly Table for max_lenght
fig_max_lenght = go.Figure(data=[go.Table(
    header=dict(values=["Campaña", "Sigla", "Empresa", "Longitud de Rama Maxima (metros)"]),
    cells=dict(
        values=list(zip(*data_for_max_lenght_table)),  # Transpose the list to match columns
        fill_color=['white'] * len(data_for_max_lenght_table),  # Keep the default background
    )
)])

fig_max_lenght.update_layout(
    title="Top 3 Pozos anuales con Longitud de Rama Maxima",
    template="plotly_white"
)


# Convert to a dataframe
df_max_lenght = pd.DataFrame(data_for_max_lenght_table, columns=["Campaña", "Sigla", "Empresa", "Longitud de Rama Máxima (metros)"])

st.write("**Top 3 Pozos con Mayor Longitud de Rama**")
st.dataframe(df_max_lenght, use_container_width=True)



import plotly.graph_objects as go

# Aggregate the data to calculate avg length for each empresaNEW and start_year
company_statistics_avg = df_merged_VMUT_filtered.groupby(['start_year', 'empresaNEW']).agg(
    avg_lenght=('longitud_rama_horizontal_m', 'mean')
).reset_index()

# Round the avg_lenght to 2 decimal places
company_statistics_avg['avg_lenght'] = company_statistics_avg['avg_lenght'].round(0)

# Sort by start_year and avg_lenght to get the top 3 empresasNEW per year
company_statistics_sorted_avg = company_statistics_avg.sort_values(['start_year', 'avg_lenght'], ascending=[True, False])

# Select the top 3 empresasNEW for each year based on avg_lenght
top_avg_lenght = company_statistics_sorted_avg.groupby('start_year').head(3)  # Get the top 3 for each year

# Create data for the table with the year appearing only once for each start_year
data_for_avg_lenght_table = []
previous_year = None
for _, row in top_avg_lenght.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "  # Use blank for repeated years
    data_for_avg_lenght_table.append([year_value, row['empresaNEW'], row['avg_lenght']])
    previous_year = row['start_year']

# Convert to a dataframe
df_avg_lenght = pd.DataFrame(data_for_avg_lenght_table, columns=["Campaña", "Empresa", "Longitud de Rama Promedio (metros)"])

st.write("**Top 3 Empresa con Mayor Longitud de Rama Promedio**")
st.dataframe(df_avg_lenght, use_container_width=True)



#------------------------------------

st.subheader("Ranking según Caudales Pico", divider="blue")

# Process Data for Petrolífero
grouped_petrolifero = df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Petrolífero'].groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg({
    'Qo_peak': 'max',
    'longitud_rama_horizontal_m': 'mean',
    'cantidad_fracturas': 'mean',
    'arena_bombeada_nacional_tn': 'sum',
    'arena_bombeada_importada_tn': 'sum'
}).reset_index()

grouped_petrolifero['fracspacing'] = grouped_petrolifero['longitud_rama_horizontal_m'] / grouped_petrolifero['cantidad_fracturas']
grouped_petrolifero['agente_etapa'] = (
    grouped_petrolifero['arena_bombeada_nacional_tn'] + grouped_petrolifero['arena_bombeada_importada_tn']
) / grouped_petrolifero['cantidad_fracturas']

grouped_petrolifero = grouped_petrolifero.drop_duplicates(subset=['start_year', 'sigla'], keep='first')
grouped_petrolifero_sorted = grouped_petrolifero.sort_values(['start_year', 'Qo_peak'], ascending=[True, False])
top_petrolifero = grouped_petrolifero_sorted.groupby('start_year').head(3)

# Handle repeated years in Petrolífero table
data_petrolifero_table = []
previous_year = None
for _, row in top_petrolifero.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    data_petrolifero_table.append({
        'start_year': year_value,
        'sigla': row['sigla'],
        'empresaNEW': row['empresaNEW'],
        'Qo_peak': int(row['Qo_peak']),
        'cantidad_fracturas': int(row['cantidad_fracturas']),
        'fracspacing': int(row['fracspacing']),
        'agente_etapa': int(row['agente_etapa'])
    })
    previous_year = row['start_year']

# Process Data for Gasífero
grouped_gasifero = df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Gasífero'].groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg({
    'Qg_peak': 'max',
    'longitud_rama_horizontal_m': 'mean',
    'cantidad_fracturas': 'mean',
    'arena_bombeada_nacional_tn': 'sum',
    'arena_bombeada_importada_tn': 'sum'
}).reset_index()

grouped_gasifero['fracspacing'] = grouped_gasifero['longitud_rama_horizontal_m'] / grouped_gasifero['cantidad_fracturas']
grouped_gasifero['agente_etapa'] = (
    grouped_gasifero['arena_bombeada_nacional_tn'] + grouped_gasifero['arena_bombeada_importada_tn']
) / grouped_gasifero['cantidad_fracturas']

grouped_gasifero = grouped_gasifero.drop_duplicates(subset=['start_year', 'sigla'], keep='first')
grouped_gasifero_sorted = grouped_gasifero.sort_values(['start_year', 'Qg_peak'], ascending=[True, False])
top_gasifero = grouped_gasifero_sorted.groupby('start_year').head(3)

# Handle repeated years in Gasífero table
data_gasifero_table = []
previous_year = None
for _, row in top_gasifero.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    data_gasifero_table.append({
        'start_year': year_value,
        'sigla': row['sigla'],
        'empresaNEW': row['empresaNEW'],
        'Qg_peak': int(row['Qg_peak']),
        'cantidad_fracturas': int(row['cantidad_fracturas']),
        'fracspacing': int(row['fracspacing']),
        'agente_etapa': int(row['agente_etapa'])
    })
    previous_year = row['start_year']

# Convert to DataFrame for Petrolífero and Gasífero tables
df_petrolifero = pd.DataFrame(data_petrolifero_table)
df_gasifero = pd.DataFrame(data_gasifero_table)

# Rename columns for both DataFrames
df_petrolifero.rename(columns={
    'start_year': 'Campaña',
    'sigla': 'Sigla',
    'empresaNEW': 'Empresa',
    'Qo_peak': 'Caudal Pico de Petróleo (m3/d)',
    'cantidad_fracturas': 'Cantidad de Fracturas',
    'fracspacing': 'Fracspacing (m/fractura)',
    'agente_etapa': 'Agente de Sosten por Etapa (tn/fractura)'
}, inplace=True)

df_gasifero.rename(columns={
    'start_year': 'Campaña',
    'sigla': 'Sigla',
    'empresaNEW': 'Empresa',
    'Qg_peak': 'Caudal Pico de Gas (km3/d)',
    'cantidad_fracturas': 'Cantidad de Fracturas',
    'fracspacing': 'Fracspacing (m/etapa)',
    'agente_etapa': 'Agente de Sosten por Etapa (tn/etapa)'
}, inplace=True)


# Display tables using st.dataframe
st.write("**Tipo Petrolífero: Top 3 Pozos con Mayor Caudal Pico**")
st.dataframe(df_petrolifero, use_container_width=True)
st.write("**Tipo Gasífero: Top 3 Pozos con Mayor Caudal Pico**")
st.dataframe(df_gasifero, use_container_width=True)


