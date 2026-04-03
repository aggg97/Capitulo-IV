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


#Verificamos si los datos ya fueron cargados en la Main Page
if 'df' in st.session_state:
    # Recuperamos los datos de la memoria sin esperar un segundo
    data_sorted = st.session_state['df']
    data_sorted['date'] = pd.to_datetime(data_sorted['anio'].astype(str) + '-' + data_sorted['mes'].astype(str) + '-1')
    data_sorted['gas_rate'] = data_sorted['prod_gas'] / data_sorted['tef']
    data_sorted['oil_rate'] = data_sorted['prod_pet'] / data_sorted['tef']
    data_sorted = data_sorted.sort_values(by=['sigla', 'date'], ascending=True)
    
    st.info("Utilizando datos recuperados de la memoria.")
    
else:
    st.warning("⚠️ No se han cargado los datos. Por favor, vuelve a la Página Principal.")


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
cum_df['tipopozoNEW'] = cum_df.apply( lambda 
row: row['Fluido McCain'] if row['tipopozo'] == 'Otro tipo' else row['tipopozo'], axis=1 )

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
#df_merged_final = df_merged_final[df_merged_final['id_base_fractura_adjiv'].notna()] 

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
    max_etapas=('cantidad_fracturas', 'max')
).reset_index()

# Round the max_lenght to 0 decimal places
company_statistics['max_etapas'] = company_statistics['max_etapas'].round(0)

# Sort by start_year and max_lenght to get the top 3 sigla per year
company_statistics_sorted = company_statistics.sort_values(['start_year', 'max_etapas'], ascending=[True, False])

# Select the top 3 sigla for each year based on max_lenght
top_max_etapas = company_statistics_sorted.groupby('start_year').head(3)

# Create data for the table with the year appearing only once for each start_year
data_for_max_etapas_table = []
previous_year = None
for _, row in top_max_etapas.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "  # Use blank for repeated years
    data_for_max_etapas_table.append([year_value, row['sigla'], row['empresaNEW'], row['max_etapas']])
    previous_year = row['start_year']

# Convert to a dataframe
df_max_etapas = pd.DataFrame(data_for_max_etapas_table, columns=["Campaña", "Sigla", "Empresa", "Máxima Cantidad de Etapas"])

# Display the DataFrame in Streamlit
st.write("**Top 3 Pozos con Máxima Cantidad de Etapas**")
# Display the dataframe in Streamlit
st.dataframe(df_max_etapas,use_container_width=True,hide_index=True)

# Aggregate the data to calculate avg length for each empresaNEW and start_year
company_statistics_avg = df_merged_VMUT_filtered.groupby(['start_year', 'empresaNEW']).agg(
    avg_etapas=('cantidad_fracturas', 'median')
).reset_index()

# Round the avg_lenght to 0 decimal places
company_statistics_avg['avg_etapas'] = company_statistics_avg['avg_etapas'].round(0)

# Sort by start_year and avg_lenght to get the top 3 empresasNEW per year
company_statistics_sorted_avg = company_statistics_avg.sort_values(['start_year', 'avg_etapas'], ascending=[True, False])

# Select the top 3 empresasNEW for each year based on avg_lenght
top_avg_etapas = company_statistics_sorted_avg.groupby('start_year').head(3)

# Create data for the table with the year appearing only once for each start_year
data_for_avg_etapas_table = []
previous_year = None
for _, row in top_avg_etapas.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "  # Use blank for repeated years
    data_for_avg_etapas_table.append([year_value, row['empresaNEW'], row['avg_etapas']])
    previous_year = row['start_year']

# Convert to a dataframe
df_avg_etapas = pd.DataFrame(data_for_avg_etapas_table, columns=["Campaña", "Empresa", "P50 Cantidad de Etapas"])

# Display the DataFrame in Streamlit
st.write("**Top 3 Empresas con Máxima Cantidad de Etapas por Pozo**")
# Display the dataframe in Streamlit
st.dataframe(df_avg_etapas,use_container_width=True,hide_index=True)


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
df_max_lenght = pd.DataFrame(data_for_max_lenght_table, columns=["Campaña", "Sigla", "Empresa", "Máxima Longitud de Rama (metros)"])

st.write("**Top 3 Pozos con Mayor Longitud de Rama**")
st.dataframe(df_max_lenght, use_container_width=True,hide_index=True)



import plotly.graph_objects as go

# Aggregate the data to calculate avg length for each empresaNEW and start_year
company_statistics_avg = df_merged_VMUT_filtered.groupby(['start_year', 'empresaNEW']).agg(
    avg_lenght=('longitud_rama_horizontal_m', 'median')
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
df_avg_lenght = pd.DataFrame(data_for_avg_lenght_table, columns=["Campaña", "Empresa", "P50 Longitud de Rama (metros)"])

st.write("**Top 3 Empresa con Máxima Longitud de Rama por Pozo**")
st.dataframe(df_avg_lenght, use_container_width=True,hide_index=True)



#------------------------------------

import streamlit as st
import pandas as pd

st.subheader("Ranking según Caudales Pico", divider="blue")

# -------------------- Petrolífero Pozos --------------------
grouped_petrolifero = df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Petrolífero'].groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg({
    'Qo_peak': 'max',
    'longitud_rama_horizontal_m': 'median',
    'cantidad_fracturas': 'median',
    'arena_bombeada_nacional_tn': 'sum',
    'arena_bombeada_importada_tn': 'sum'
}).reset_index()

grouped_petrolifero['fracspacing'] = grouped_petrolifero['longitud_rama_horizontal_m'] / grouped_petrolifero['cantidad_fracturas']
grouped_petrolifero['agente_etapa'] = (
    grouped_petrolifero['arena_bombeada_nacional_tn'] + grouped_petrolifero['arena_bombeada_importada_tn']
) / grouped_petrolifero['cantidad_fracturas']

grouped_petrolifero_sorted = grouped_petrolifero.sort_values(['start_year', 'Qo_peak'], ascending=[True, False])
top_petrolifero = grouped_petrolifero_sorted.groupby('start_year').head(3)

# Format Table
data_petrolifero_table = []
previous_year = None
for _, row in top_petrolifero.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    data_petrolifero_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Caudal Pico de Petróleo (m3/d)': int(row['Qo_peak']),
        'Cantidad de Fracturas': (
            int(row['cantidad_fracturas']) 
            if pd.notna(row['cantidad_fracturas']) and row['cantidad_fracturas'] > 0 
            else None
            ),
        'Fracspacing (m/etapa)': (
            int(row['fracspacing']) 
            if pd.notna(row['fracspacing']) and row['fracspacing'] > 0 
            else None
            ),
        'Agente de Sosten por Etapa (tn/etapa)': (
            int(row['agente_etapa']) 
            if pd.notna(row['agente_etapa']) and row['agente_etapa'] > 0 
            else None
            )
    })
    previous_year = row['start_year']

df_petrolifero_final = pd.DataFrame(data_petrolifero_table)
st.write("**Tipo Petrolífero: Top 3 Pozos con Mayor Caudal Pico**")
st.dataframe(df_petrolifero_final, use_container_width=True,hide_index=True)

# -------------------- Gasífero Pozos --------------------
grouped_gasifero = df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Gasífero'].groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg({
    'Qg_peak': 'max',
    'longitud_rama_horizontal_m': 'median',
    'cantidad_fracturas': 'median',
    'arena_bombeada_nacional_tn': 'sum',
    'arena_bombeada_importada_tn': 'sum'
}).reset_index()

grouped_gasifero['fracspacing'] = grouped_gasifero['longitud_rama_horizontal_m'] / grouped_gasifero['cantidad_fracturas']
grouped_gasifero['agente_etapa'] = (
    grouped_gasifero['arena_bombeada_nacional_tn'] + grouped_gasifero['arena_bombeada_importada_tn']
) / grouped_gasifero['cantidad_fracturas']

grouped_gasifero_sorted = grouped_gasifero.sort_values(['start_year', 'Qg_peak'], ascending=[True, False])
top_gasifero = grouped_gasifero_sorted.groupby('start_year').head(3)

# Format Table
data_gasifero_table = []
previous_year = None
for _, row in top_gasifero.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    data_gasifero_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Caudal Pico de Gas (km3/d)': int(row['Qg_peak']),
        'Cantidad de Fracturas': (
            int(row['cantidad_fracturas']) 
            if pd.notna(row['cantidad_fracturas']) and row['cantidad_fracturas'] > 0 
            else None
            ),
        'Fracspacing (m/etapa)': (
            int(row['fracspacing']) 
            if pd.notna(row['fracspacing']) and row['fracspacing'] > 0 
            else None
            ),
        'Agente de Sosten por Etapa (tn/etapa)': (
            int(row['agente_etapa']) 
            if pd.notna(row['agente_etapa']) and row['agente_etapa'] > 0 
            else None
            )
    })
    previous_year = row['start_year']

df_gasifero_final = pd.DataFrame(data_gasifero_table)
st.write("**Tipo Gasífero: Top 3 Pozos con Mayor Caudal Pico**")
st.dataframe(df_gasifero_final, use_container_width=True,hide_index=True)

# -------------------- Empresas: Promedios --------------------

# --- Petrolífero ---
grouped_petro_emp = df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Petrolífero'].groupby(
    ['start_year', 'empresaNEW']
).agg({
    'Qo_peak': 'median',
    'cantidad_fracturas': 'median'
}).reset_index()

# Ordenar y sacar Top 3 por año
top3_petro_emp = grouped_petro_emp.sort_values(['start_year', 'Qo_peak'], ascending=[True, False]).groupby('start_year').head(3)

# Lógica para no repetir el año en la visualización
data_petro_final = []
last_year = None

for _, row in top3_petro_emp.iterrows():
    current_year = str(int(row['start_year']))
    # Si el año es el mismo que el anterior, lo dejamos en blanco
    display_year = current_year if current_year != last_year else ""
    
    data_petro_final.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Caudal Pico (m3/d)': round(row['Qo_peak'], 0)
    })
    last_year = current_year

st.write("**Top 3 Empresas con Mayores Caudales Pico de Petróleo**")
st.dataframe(pd.DataFrame(data_petro_final), use_container_width=True, hide_index=True)


# --- Gasífero ---
grouped_gas_emp = df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Gasífero'].groupby(
    ['start_year', 'empresaNEW']
).agg({
    'Qg_peak': 'median',
    'cantidad_fracturas': 'median'
}).reset_index()

# Ordenar y sacar Top 3 por año
top3_gas_emp = grouped_gas_emp.sort_values(['start_year', 'Qg_peak'], ascending=[True, False]).groupby('start_year').head(3)

# Lógica para no repetir el año en la visualización
data_gas_final = []
last_year = None

for _, row in top3_gas_emp.iterrows():
    current_year = str(int(row['start_year']))
    # Si el año es el mismo que el anterior, lo dejamos en blanco
    display_year = current_year if current_year != last_year else ""
    
    data_gas_final.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Caudal Pico (km3/d)': round(row['Qg_peak'], 0)
    
    })
    last_year = current_year

st.write("**Top 3 Empresas con Mayores Caudales Pico de Gas**")
st.dataframe(pd.DataFrame(data_gas_final), use_container_width=True, hide_index=True)



# -------------------- Arena Bombeada --------------------

st.subheader("Ranking según Arena Bombeada", divider="blue")


df_clean = df_merged_VMUT[
    (df_merged_VMUT['start_year'] >= 2012) & 
    (df_merged_VMUT['arena_total_tn'] > 0) & 
    (df_merged_VMUT['arena_total_tn'].notna())
].copy()


# -------------------- Arena Pozos --------------------

grouped_arena = df_clean.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg({
    'arena_total_tn': 'max',
    'cantidad_fracturas': 'median',
    'longitud_rama_horizontal_m': 'median'
}).reset_index()

grouped_arena_sorted = grouped_arena.sort_values(
    ['start_year', 'arena_total_tn'], ascending=[True, False]
)

top_arena = grouped_arena_sorted.groupby('start_year').head(3)

# -------------------- Format Table --------------------
data_arena_table = []
previous_year = None

for _, row in top_arena.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "

    data_arena_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Máxima Arena Bombeada (tn)': (
            int(row['arena_total_tn']) 
            if pd.notna(row['arena_total_tn']) and row['arena_total_tn'] > 0 
            else None
        )
    })

    previous_year = row['start_year']

df_arena_final = pd.DataFrame(data_arena_table)

st.write("**Top 3 Pozos con Máxima Arena Bombeada**")
st.dataframe(df_arena_final, use_container_width=True,hide_index=True)

# -------------------- Empresas: Arena Promedio --------------------

grouped_emp_arena = df_clean.groupby(
    ['start_year', 'empresaNEW']
).agg({
    'arena_total_tn': 'median',
    'cantidad_fracturas': 'median'
}).reset_index()

top_emp_arena = (
    grouped_emp_arena
    .sort_values(['start_year', 'arena_total_tn'], ascending=[True, False])
    .groupby('start_year')
    .head(3)
)

# Format
data_emp_arena = []
last_year = None

for _, row in top_emp_arena.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""

    data_emp_arena.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Arena Bombeada (tn)': (
            int(row['arena_total_tn']) 
            if pd.notna(row['arena_total_tn']) and row['arena_total_tn'] > 0 
            else None
        )
    })

    last_year = current_year

st.write("**Top 3 Empresas con Máxima Arena Bombeada por Pozo**")
st.dataframe(pd.DataFrame(data_emp_arena), use_container_width=True, hide_index=True)

#--------------
st.subheader("Ranking según Fracspacing", divider="blue")

st.caption("Fracspacing = longitud_rama_horizontal_m / cantidad_fracturas")
st.caption("Fracspacing más agresivo = Menor Fracspacing")

# Calcular fracspacing de forma consistente para todos los pozos
# Usamos df_merged_VMUT_filtered que ya tiene un registro por sigla (drop_duplicates)
df_fracspacing_base = df_merged_VMUT_filtered.copy()
df_fracspacing_base['fracspacing'] = (
    df_fracspacing_base['longitud_rama_horizontal_m'] / df_fracspacing_base['cantidad_fracturas']
)

# Filtrar registros válidos (fracspacing > 0 y no nulo)
df_fracspacing_base = df_fracspacing_base[
    (df_fracspacing_base['fracspacing'].notna()) &
    (df_fracspacing_base['fracspacing'] > 0)
]

# -------------------- Petrolífero Pozos --------------------
df_petro_frac = df_fracspacing_base[df_fracspacing_base['tipopozoNEW'] == 'Petrolífero']

grouped_petrolifero = df_petro_frac.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg(
    fracspacing=('fracspacing', 'min')
).reset_index()

grouped_petrolifero_sorted = grouped_petrolifero.sort_values(
    ['start_year', 'fracspacing'], ascending=[True, True]
)
top_petrolifero = grouped_petrolifero_sorted.groupby('start_year').head(3)

data_petrolifero_table = []
previous_year = None
for _, row in top_petrolifero.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    data_petrolifero_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Mínimo Fracspacing (m)': int(row['fracspacing'])
    })
    previous_year = row['start_year']

df_petrolifero_final = pd.DataFrame(data_petrolifero_table)
st.write("**Tipo Petrolífero: Top 3 Pozos con Fracspacing más Agresivo**")
st.dataframe(df_petrolifero_final, use_container_width=True, hide_index=True)

# -------------------- Petrolífero Empresas (P50) --------------------
p50_petro_emp = df_petro_frac.groupby(
    ['start_year', 'empresaNEW']
).agg(
    p50_fracspacing=('fracspacing', 'median')
).reset_index()

p50_petro_emp['p50_fracspacing'] = p50_petro_emp['p50_fracspacing'].round(0)

top3_petro_emp = (
    p50_petro_emp
    .sort_values(['start_year', 'p50_fracspacing'], ascending=[True, True])
    .groupby('start_year')
    .head(3)
)

data_petro_emp = []
last_year = None
for _, row in top3_petro_emp.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""
    data_petro_emp.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Fracspacing (m)': int(row['p50_fracspacing'])
    })
    last_year = current_year

st.write("**Top 3 Empresas con Fracspacing más Agresivo por Pozo de Petróleo**")
st.dataframe(pd.DataFrame(data_petro_emp), use_container_width=True, hide_index=True)


# -------------------- Gasífero Pozos --------------------
df_gas_frac = df_fracspacing_base[df_fracspacing_base['tipopozoNEW'] == 'Gasífero']

grouped_gasifero = df_gas_frac.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg(
    fracspacing=('fracspacing', 'min')
).reset_index()

grouped_gasifero_sorted = grouped_gasifero.sort_values(
    ['start_year', 'fracspacing'], ascending=[True, True]
)
top_gasifero = grouped_gasifero_sorted.groupby('start_year').head(3)

data_gasifero_table = []
previous_year = None
for _, row in top_gasifero.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    data_gasifero_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Fracspacing Mínimo (m)': int(row['fracspacing'])
    })
    previous_year = row['start_year']

df_gasifero_final = pd.DataFrame(data_gasifero_table)
st.write("**Tipo Gasífero: Top 3 Pozos con Fracspacing más Agresivo**")
st.dataframe(df_gasifero_final, use_container_width=True, hide_index=True)

# -------------------- Gasífero Empresas (P50) --------------------
p50_gas_emp = df_gas_frac.groupby(
    ['start_year', 'empresaNEW']
).agg(
    p50_fracspacing=('fracspacing', 'median')
).reset_index()

p50_gas_emp['p50_fracspacing'] = p50_gas_emp['p50_fracspacing'].round(0)

top3_gas_emp = (
    p50_gas_emp
    .sort_values(['start_year', 'p50_fracspacing'], ascending=[True, True])
    .groupby('start_year')
    .head(3)
)

data_gas_emp = []
last_year = None
for _, row in top3_gas_emp.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""
    data_gas_emp.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Fracspacing (m)': int(row['p50_fracspacing'])
    })
    last_year = current_year

st.write("**Top 3 Empresas con Fracspacing más Agresivo por Pozo de Gas**")
st.dataframe(pd.DataFrame(data_gas_emp), use_container_width=True, hide_index=True)

# -------------------- Prop x Etapa --------------------

st.subheader("Ranking según Propante por Etapa", divider="blue")

st.caption("Prop x Etapa = arena_total_tn / cantidad_fracturas")
st.caption("La cantidad de arena por etapa es otro indicador de agresividad en la completacion")

# Calcular propante por etapa
df_prop_base = df_merged_VMUT.copy()
df_prop_base['prop_x_etapa'] = (
    df_prop_base['arena_total_tn'] / df_prop_base['cantidad_fracturas']
)

# Filtrar valores válidos
df_prop_base = df_prop_base[
    (df_prop_base['prop_x_etapa'].notna()) &
    (df_prop_base['prop_x_etapa'] > 0)
]

# -------------------- Petrolífero Pozos --------------------
df_petro_prop = df_prop_base[df_prop_base['tipopozoNEW'] == 'Petrolífero']

grouped_petro = df_petro_prop.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg(
    prop_x_etapa_max=('prop_x_etapa', 'max')
).reset_index()

grouped_petro_sorted = grouped_petro.sort_values(
    ['start_year', 'prop_x_etapa_max'], ascending=[True, False]
)

top_petro = grouped_petro_sorted.groupby('start_year').head(3)

# Formato tabla
data_petro_table = []
previous_year = None

for _, row in top_petro.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    
    data_petro_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Prop x Etapa (tn/etapa)': round(row['prop_x_etapa_max'], 0)
    })
    
    previous_year = row['start_year']

df_petro_prop_final = pd.DataFrame(data_petro_table)

st.write("**Tipo Petrolífero: Top 3 Pozos con Mayor Propante por Etapa**")
st.dataframe(df_petro_prop_final, use_container_width=True, hide_index=True)


# -------------------- Gasífero Pozos --------------------
df_gas_prop = df_prop_base[df_prop_base['tipopozoNEW'] == 'Gasífero']

grouped_gas = df_gas_prop.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg(
    prop_x_etapa_max=('prop_x_etapa', 'max')
).reset_index()

grouped_gas_sorted = grouped_gas.sort_values(
    ['start_year', 'prop_x_etapa_max'], ascending=[True, False]
)

top_gas = grouped_gas_sorted.groupby('start_year').head(3)

# Formato tabla
data_gas_table = []
previous_year = None

for _, row in top_gas.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    
    data_gas_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Prop x Etapa (tn/etapa)': round(row['prop_x_etapa_max'], 0)
    })
    
    previous_year = row['start_year']

df_gas_prop_final = pd.DataFrame(data_gas_table)

st.write("**Tipo Gasífero: Top 3 Pozos con Mayor Propante por Etapa**")
st.dataframe(df_gas_prop_final, use_container_width=True, hide_index=True)

# -------------------- Empresas: Propante por Etapa (P50) --------------------


# Base (reutiliza si ya lo calculaste antes)
df_prop_emp = df_merged_VMUT.copy()
df_prop_emp['prop_x_etapa'] = (
    df_prop_emp['arena_total_tn'] / df_prop_emp['cantidad_fracturas']
)

# Filtrar valores válidos
df_prop_emp = df_prop_emp[
    (df_prop_emp['prop_x_etapa'].notna()) &
    (df_prop_emp['prop_x_etapa'] > 0)
]

# -------------------- Petrolífero Empresas --------------------
grouped_petro_emp = df_prop_emp[df_prop_emp['tipopozoNEW'] == 'Petrolífero'].groupby(
    ['start_year', 'empresaNEW']
).agg(
    prop_x_etapa=('prop_x_etapa', 'median')
).reset_index()

top3_petro_emp = (
    grouped_petro_emp
    .sort_values(['start_year', 'prop_x_etapa'], ascending=[True, False])
    .groupby('start_year')
    .head(3)
)

# Formato tabla
data_petro_emp = []
last_year = None

for _, row in top3_petro_emp.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""

    data_petro_emp.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Prop x Etapa (tn/etapa)': round(row['prop_x_etapa'], 0)
    })

    last_year = current_year

st.write("**Top 3 Empresas con Mayor Propante por Etapa por Pozo de Petróleo**")
st.dataframe(pd.DataFrame(data_petro_emp), use_container_width=True, hide_index=True)


# -------------------- Gasífero Empresas --------------------
grouped_gas_emp = df_prop_emp[df_prop_emp['tipopozoNEW'] == 'Gasífero'].groupby(
    ['start_year', 'empresaNEW']
).agg(
    prop_x_etapa=('prop_x_etapa', 'median')
).reset_index()

top3_gas_emp = (
    grouped_gas_emp
    .sort_values(['start_year', 'prop_x_etapa'], ascending=[True, False])
    .groupby('start_year')
    .head(3)
)

# Formato tabla
data_gas_emp = []
last_year = None

for _, row in top3_gas_emp.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""

    data_gas_emp.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Prop x Etapa (tn/etapa)': round(row['prop_x_etapa'], 0)
    })

    last_year = current_year

st.write("**Top 3 Empresas con Mayor Propante por Etapa por Pozo de Gas**")
st.dataframe(pd.DataFrame(data_gas_emp), use_container_width=True, hide_index=True)


# -------------------- Minimos --------------------
# -------------------- Petrolífero Pozos --------------------
df_petro_prop = df_prop_base[df_prop_base['tipopozoNEW'] == 'Petrolífero']

grouped_petro = df_petro_prop.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg(
    prop_x_etapa_min=('prop_x_etapa', 'min')
).reset_index()

grouped_petro_sorted = grouped_petro.sort_values(
    ['start_year', 'prop_x_etapa_min'], ascending=[True, True]
)

top_petro = grouped_petro_sorted.groupby('start_year').head(3)

# Formato tabla
data_petro_table = []
previous_year = None

for _, row in top_petro.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    
    data_petro_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Prop x Etapa (tn/etapa)': round(row['prop_x_etapa_min'], 0)
    })
    
    previous_year = row['start_year']

df_petro_prop_final = pd.DataFrame(data_petro_table)

st.write("**Tipo Petrolífero: Top 3 Pozos con Menor Propante por Etapa**")
st.dataframe(df_petro_prop_final, use_container_width=True, hide_index=True)


# -------------------- Gasífero Pozos --------------------
df_gas_prop = df_prop_base[df_prop_base['tipopozoNEW'] == 'Gasífero']

grouped_gas = df_gas_prop.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg(
    prop_x_etapa_min=('prop_x_etapa', 'min')
).reset_index()

grouped_gas_sorted = grouped_gas.sort_values(
    ['start_year', 'prop_x_etapa_min'], ascending=[True, True]
)

top_gas = grouped_gas_sorted.groupby('start_year').head(3)

# Formato tabla
data_gas_table = []
previous_year = None

for _, row in top_gas.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "
    
    data_gas_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Prop x Etapa (tn/etapa)': round(row['prop_x_etapa_min'], 0)
    })
    
    previous_year = row['start_year']

df_gas_prop_final = pd.DataFrame(data_gas_table)

st.write("**Tipo Gasífero: Top 3 Pozos con Menor Propante por Etapa**")
st.dataframe(df_gas_prop_final, use_container_width=True, hide_index=True)

# -------------------- Empresas: Propante por Etapa (P50) --------------------

# Base (reutiliza si ya lo calculaste antes)
df_prop_emp = df_merged_VMUT.copy()
df_prop_emp['prop_x_etapa'] = (
    df_prop_emp['arena_total_tn'] / df_prop_emp['cantidad_fracturas']
)

# Filtrar valores válidos
df_prop_emp = df_prop_emp[
    (df_prop_emp['prop_x_etapa'].notna()) &
    (df_prop_emp['prop_x_etapa'] > 0)
]

# -------------------- Petrolífero Empresas --------------------
grouped_petro_emp = df_prop_emp[df_prop_emp['tipopozoNEW'] == 'Petrolífero'].groupby(
    ['start_year', 'empresaNEW']
).agg(
    prop_x_etapa=('prop_x_etapa', 'median')
).reset_index()

top3_petro_emp = (
    grouped_petro_emp
    .sort_values(['start_year', 'prop_x_etapa'], ascending=[True, True])
    .groupby('start_year')
    .head(3)
)

# Formato tabla
data_petro_emp = []
last_year = None

for _, row in top3_petro_emp.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""

    data_petro_emp.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Prop x Etapa (tn/etapa)': round(row['prop_x_etapa'], 0)
    })

    last_year = current_year

st.write("**Top 3 Empresas con Menor Propante por Etapa por Pozo de Petróleo**")
st.dataframe(pd.DataFrame(data_petro_emp), use_container_width=True, hide_index=True)


# -------------------- Gasífero Empresas --------------------
grouped_gas_emp = df_prop_emp[df_prop_emp['tipopozoNEW'] == 'Gasífero'].groupby(
    ['start_year', 'empresaNEW']
).agg(
    prop_x_etapa=('prop_x_etapa', 'median')
).reset_index()

top3_gas_emp = (
    grouped_gas_emp
    .sort_values(['start_year', 'prop_x_etapa'], ascending=[True, True])
    .groupby('start_year')
    .head(3)
)

# Formato tabla
data_gas_emp = []
last_year = None

for _, row in top3_gas_emp.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""

    data_gas_emp.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Prop x Etapa (tn/etapa)': round(row['prop_x_etapa'], 0)
    })

    last_year = current_year

st.write("**Top 3 Empresas con Menor Propante por Etapa por Pozo de Gas**")
st.dataframe(pd.DataFrame(data_gas_emp), use_container_width=True, hide_index=True)

#--------------------------------------------

st.subheader("Ranking según Agente de Sosten por Volumen Inyectado", divider="blue")

# Step 1: Calculate AS x volumen inyectado (tn/1000m3) for each row
df_merged_VMUT['AS_x_volumen_inyectado'] = df_merged_VMUT['arena_total_tn'] / (df_merged_VMUT['agua_inyectada_m3'] / 1000)

df_clean = df_merged_VMUT[
    (df_merged_VMUT['start_year'] >= 2012) & 
    (df_merged_VMUT['AS_x_volumen_inyectado'] > 0) & 
    (df_merged_VMUT['AS_x_volumen_inyectado'].notna())
].copy()


# -------------------- Pozos --------------------

grouped_as = df_clean.groupby(
    ['start_year', 'sigla', 'empresaNEW']
).agg({
    'AS_x_volumen_inyectado': 'max'
}).reset_index()

grouped_as_sorted = grouped_as.sort_values(
    ['start_year', 'AS_x_volumen_inyectado'], ascending=[True, False]
)

top_as = grouped_arena_sorted.groupby('start_year').head(3)

# -------------------- Format Table --------------------
data_arena_table = []
previous_year = None

for _, row in top_arena.iterrows():
    year_value = int(row['start_year']) if row['start_year'] != previous_year else " "

    data_arena_table.append({
        'Campaña': year_value,
        'Sigla': row['sigla'],
        'Empresa': row['empresaNEW'],
        'Agente de Sosten por Vol Inyectado (tn/1000m3)': (
            int(row['AS_x_volumen_inyectado']) 
            if pd.notna(row['AS_x_volumen_inyectado']) and row['AS_x_volumen_inyectado'] > 0 
            else None
        )
    })

    previous_year = row['start_year']

df_arena_final = pd.DataFrame(data_arena_table)

st.write("**Top 3 Pozos con Mayor cc de Agente de Sosten por Volumen Inyectado**")
st.dataframe(df_arena_final, use_container_width=True,hide_index=True)

# -------------------- Empresas: Arena Promedio --------------------

grouped_emp_as = df_clean.groupby(
    ['start_year', 'empresaNEW']
).agg({
    'AS_x_volumen_inyectado': 'median',

}).reset_index()

top_emp_as= (
    grouped_emp_as
    .sort_values(['start_year', 'AS_x_volumen_inyectado'], ascending=[True, False])
    .groupby('start_year')
    .head(3)
)

# Format
data_emp_arena = []
last_year = None

for _, row in top_emp_arena.iterrows():
    current_year = str(int(row['start_year']))
    display_year = current_year if current_year != last_year else ""

    data_emp_arena.append({
        'Campaña': display_year,
        'Empresa': row['empresaNEW'],
        'P50 Agente de Sosten por Vol Inyectado (tn/1000m3)': (
            int(row['AS_x_volumen_inyectado']) 
            if pd.notna(row['AS_x_volumen_inyectado']) and row['AS_x_volumen_inyectado'] > 0 
            else None
        )
    })

    last_year = current_year

st.write("**Top 3 Empresas con Mayor cc de Agente de Sosten por Volumen Inyectado por Pozo**")
st.dataframe(pd.DataFrame(data_emp_as), use_container_width=True, hide_index=True)

