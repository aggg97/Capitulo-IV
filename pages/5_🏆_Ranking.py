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

# ── Helper reutilizable ──────────────────────────────────────────────────────
def style_ranking_table(df, year_col="Campaña"):
    """
    Recibe un DataFrame con el año real en cada fila (int).
    Devuelve un Styler donde el año se muestra en gris claro cuando
    es igual al de la fila anterior, simulando el efecto 'sin repetir'
    pero sin romper el ordenamiento interactivo de Streamlit.
    """
    def dim_repeated_years(col):
        styles = []
        prev = None
        for val in col:
            if val == prev:
                styles.append("color: #cccccc")   # gris claro = "vacío visual"
            else:
                styles.append("color: inherit; font-weight: bold")
            prev = val
        return styles

    return (
        df.style
        .apply(dim_repeated_years, subset=[year_col])
        .format({year_col: "{:.0f}"})           # sin decimales en el año
    )
# ────────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# A partir de acá reemplazás toda la lógica de construcción de tablas.
# El cambio clave: year_value SIEMPRE es el año real (int), nunca " ".
# ══════════════════════════════════════════════════════════════════════════════

# ── Filtro base ──────────────────────────────────────────────────────────────
df_merged_VMUT_filtered = df_merged_VMUT[
    df_merged_VMUT['longitud_rama_horizontal_m'] > 0
].drop_duplicates(subset='sigla')


# ════════════════════════════════════════════════════════════════════════════
st.subheader("Ranking según Cantidad de Etapas", divider="blue")

# ── Pozos ────────────────────────────────────────────────────────────────────
company_statistics = (
    df_merged_VMUT_filtered
    .groupby(['start_year', 'empresaNEW', 'sigla'])
    .agg(max_etapas=('cantidad_fracturas', 'max'))
    .reset_index()
)
company_statistics['max_etapas'] = company_statistics['max_etapas'].round(0).astype(int)

top_max_etapas = (
    company_statistics
    .sort_values(['start_year', 'max_etapas'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)

df_max_etapas = top_max_etapas.rename(columns={
    'start_year': 'Campaña',
    'sigla': 'Sigla',
    'empresaNEW': 'Empresa',
    'max_etapas': 'Máxima Cantidad de Etapas'
})[['Campaña', 'Sigla', 'Empresa', 'Máxima Cantidad de Etapas']]

st.write("**Top 3 Pozos con Máxima Cantidad de Etapas**")
st.dataframe(style_ranking_table(df_max_etapas), use_container_width=True, hide_index=True)

# ── Empresas (P50) ───────────────────────────────────────────────────────────
company_p50_etapas = (
    df_merged_VMUT_filtered
    .groupby(['start_year', 'empresaNEW'])
    .agg(p50_etapas=('cantidad_fracturas', 'median'))
    .reset_index()
)
company_p50_etapas['p50_etapas'] = company_p50_etapas['p50_etapas'].round(0).astype(int)

top_p50_etapas = (
    company_p50_etapas
    .sort_values(['start_year', 'p50_etapas'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)

df_p50_etapas = top_p50_etapas.rename(columns={
    'start_year': 'Campaña',
    'empresaNEW': 'Empresa',
    'p50_etapas': 'P50 Cantidad de Etapas'
})[['Campaña', 'Empresa', 'P50 Cantidad de Etapas']]

st.write("**Top 3 Empresas con Mayor P50 de Cantidad de Etapas**")
st.dataframe(style_ranking_table(df_p50_etapas), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
st.subheader("Ranking según Longitud de Rama", divider="blue")

# ── Pozos ────────────────────────────────────────────────────────────────────
company_statistics = (
    df_merged_VMUT_filtered
    .groupby(['start_year', 'empresaNEW', 'sigla'])
    .agg(max_lenght=('longitud_rama_horizontal_m', 'max'))
    .reset_index()
)
company_statistics['max_lenght'] = company_statistics['max_lenght'].round(0).astype(int)

top_max_lenght = (
    company_statistics
    .sort_values(['start_year', 'max_lenght'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)

df_max_lenght = top_max_lenght.rename(columns={
    'start_year': 'Campaña',
    'sigla': 'Sigla',
    'empresaNEW': 'Empresa',
    'max_lenght': 'Máxima Longitud de Rama (m)'
})[['Campaña', 'Sigla', 'Empresa', 'Máxima Longitud de Rama (m)']]

st.write("**Top 3 Pozos con Mayor Longitud de Rama**")
st.dataframe(style_ranking_table(df_max_lenght), use_container_width=True, hide_index=True)

# ── Empresas (P50) ───────────────────────────────────────────────────────────
company_p50_lenght = (
    df_merged_VMUT_filtered
    .groupby(['start_year', 'empresaNEW'])
    .agg(p50_lenght=('longitud_rama_horizontal_m', 'median'))
    .reset_index()
)
company_p50_lenght['p50_lenght'] = company_p50_lenght['p50_lenght'].round(0).astype(int)

top_p50_lenght = (
    company_p50_lenght
    .sort_values(['start_year', 'p50_lenght'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)

df_p50_lenght = top_p50_lenght.rename(columns={
    'start_year': 'Campaña',
    'empresaNEW': 'Empresa',
    'p50_lenght': 'P50 Longitud de Rama (m)'
})[['Campaña', 'Empresa', 'P50 Longitud de Rama (m)']]

st.write("**Top 3 Empresas con Mayor P50 de Longitud de Rama**")
st.dataframe(style_ranking_table(df_p50_lenght), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
st.subheader("Ranking según Caudales Pico", divider="blue")

# ── Petrolífero Pozos ────────────────────────────────────────────────────────
grouped_petrolifero = (
    df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Petrolífero']
    .groupby(['start_year', 'sigla', 'empresaNEW'])
    .agg({
        'Qo_peak': 'max',
        'longitud_rama_horizontal_m': 'median',
        'cantidad_fracturas': 'median',
        'arena_bombeada_nacional_tn': 'sum',
        'arena_bombeada_importada_tn': 'sum'
    })
    .reset_index()
)
grouped_petrolifero['fracspacing'] = (
    grouped_petrolifero['longitud_rama_horizontal_m'] / grouped_petrolifero['cantidad_fracturas']
)
grouped_petrolifero['agente_etapa'] = (
    grouped_petrolifero['arena_bombeada_nacional_tn'] + grouped_petrolifero['arena_bombeada_importada_tn']
) / grouped_petrolifero['cantidad_fracturas']

top_petrolifero = (
    grouped_petrolifero
    .sort_values(['start_year', 'Qo_peak'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)

def safe_int(val):
    return int(val) if pd.notna(val) and val > 0 else None

df_petrolifero_final = pd.DataFrame([{
    'Campaña':                            int(row['start_year']),
    'Sigla':                              row['sigla'],
    'Empresa':                            row['empresaNEW'],
    'Caudal Pico de Petróleo (m3/d)':    safe_int(row['Qo_peak']),
    'Cantidad de Fracturas':              safe_int(row['cantidad_fracturas']),
    'Fracspacing (m/etapa)':              safe_int(row['fracspacing']),
    'Agente de Sosten por Etapa (tn/etapa)': safe_int(row['agente_etapa']),
} for _, row in top_petrolifero.iterrows()])

st.write("**Tipo Petrolífero: Top 3 Pozos con Mayor Caudal Pico**")
st.dataframe(style_ranking_table(df_petrolifero_final), use_container_width=True, hide_index=True)

# ── Gasífero Pozos ───────────────────────────────────────────────────────────
grouped_gasifero = (
    df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Gasífero']
    .groupby(['start_year', 'sigla', 'empresaNEW'])
    .agg({
        'Qg_peak': 'max',
        'longitud_rama_horizontal_m': 'median',
        'cantidad_fracturas': 'median',
        'arena_bombeada_nacional_tn': 'sum',
        'arena_bombeada_importada_tn': 'sum'
    })
    .reset_index()
)
grouped_gasifero['fracspacing'] = (
    grouped_gasifero['longitud_rama_horizontal_m'] / grouped_gasifero['cantidad_fracturas']
)
grouped_gasifero['agente_etapa'] = (
    grouped_gasifero['arena_bombeada_nacional_tn'] + grouped_gasifero['arena_bombeada_importada_tn']
) / grouped_gasifero['cantidad_fracturas']

top_gasifero = (
    grouped_gasifero
    .sort_values(['start_year', 'Qg_peak'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)

df_gasifero_final = pd.DataFrame([{
    'Campaña':                               int(row['start_year']),
    'Sigla':                                 row['sigla'],
    'Empresa':                               row['empresaNEW'],
    'Caudal Pico de Gas (km3/d)':           safe_int(row['Qg_peak']),
    'Cantidad de Fracturas':                 safe_int(row['cantidad_fracturas']),
    'Fracspacing (m/etapa)':                 safe_int(row['fracspacing']),
    'Agente de Sosten por Etapa (tn/etapa)': safe_int(row['agente_etapa']),
} for _, row in top_gasifero.iterrows()])

st.write("**Tipo Gasífero: Top 3 Pozos con Mayor Caudal Pico**")
st.dataframe(style_ranking_table(df_gasifero_final), use_container_width=True, hide_index=True)

# ── Empresas P50 Caudales ────────────────────────────────────────────────────
p50_petro_emp = (
    df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Petrolífero']
    .groupby(['start_year', 'empresaNEW'])
    .agg(p50_Qo=('Qo_peak', 'median'))
    .reset_index()
)
top3_petro_emp = (
    p50_petro_emp
    .sort_values(['start_year', 'p50_Qo'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_petro_emp = top3_petro_emp.rename(columns={
    'start_year': 'Campaña', 'empresaNEW': 'Empresa', 'p50_Qo': 'P50 Caudal Pico (m3/d)'
})
df_petro_emp['P50 Caudal Pico (m3/d)'] = df_petro_emp['P50 Caudal Pico (m3/d)'].round(0).astype(int)

st.write("**Top 3 Empresas con Mayor P50 de Caudal Pico de Petróleo**")
st.dataframe(style_ranking_table(df_petro_emp[['Campaña', 'Empresa', 'P50 Caudal Pico (m3/d)']]),
             use_container_width=True, hide_index=True)

p50_gas_emp = (
    df_merged_VMUT[df_merged_VMUT['tipopozoNEW'] == 'Gasífero']
    .groupby(['start_year', 'empresaNEW'])
    .agg(p50_Qg=('Qg_peak', 'median'))
    .reset_index()
)
top3_gas_emp = (
    p50_gas_emp
    .sort_values(['start_year', 'p50_Qg'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_gas_emp = top3_gas_emp.rename(columns={
    'start_year': 'Campaña', 'empresaNEW': 'Empresa', 'p50_Qg': 'P50 Caudal Pico (km3/d)'
})
df_gas_emp['P50 Caudal Pico (km3/d)'] = df_gas_emp['P50 Caudal Pico (km3/d)'].round(0).astype(int)

st.write("**Top 3 Empresas con Mayor P50 de Caudal Pico de Gas**")
st.dataframe(style_ranking_table(df_gas_emp[['Campaña', 'Empresa', 'P50 Caudal Pico (km3/d)']]),
             use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
st.subheader("Ranking según Arena Bombeada", divider="blue")

df_clean = df_merged_VMUT[
    (df_merged_VMUT['start_year'] >= 2012) &
    (df_merged_VMUT['arena_total_tn'] > 0) &
    (df_merged_VMUT['arena_total_tn'].notna())
].copy()

# ── Pozos ────────────────────────────────────────────────────────────────────
grouped_arena = (
    df_clean
    .groupby(['start_year', 'sigla', 'empresaNEW'])
    .agg(arena_total_tn=('arena_total_tn', 'max'))
    .reset_index()
)
top_arena = (
    grouped_arena
    .sort_values(['start_year', 'arena_total_tn'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_arena_final = top_arena.rename(columns={
    'start_year': 'Campaña', 'sigla': 'Sigla',
    'empresaNEW': 'Empresa', 'arena_total_tn': 'Máxima Arena Bombeada (tn)'
})
df_arena_final['Máxima Arena Bombeada (tn)'] = df_arena_final['Máxima Arena Bombeada (tn)'].round(0).astype(int)

st.write("**Top 3 Pozos con Máxima Arena Bombeada**")
st.dataframe(style_ranking_table(df_arena_final[['Campaña', 'Sigla', 'Empresa', 'Máxima Arena Bombeada (tn)']]),
             use_container_width=True, hide_index=True)

# ── Empresas (P50) ───────────────────────────────────────────────────────────
p50_emp_arena = (
    df_clean
    .groupby(['start_year', 'empresaNEW'])
    .agg(p50_arena=('arena_total_tn', 'median'))
    .reset_index()
)
top_emp_arena = (
    p50_emp_arena
    .sort_values(['start_year', 'p50_arena'], ascending=[True, False])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_emp_arena = top_emp_arena.rename(columns={
    'start_year': 'Campaña', 'empresaNEW': 'Empresa', 'p50_arena': 'P50 Arena Bombeada (tn)'
})
df_emp_arena['P50 Arena Bombeada (tn)'] = df_emp_arena['P50 Arena Bombeada (tn)'].round(0).astype(int)

st.write("**Top 3 Empresas con Mayor P50 de Arena Bombeada**")
st.dataframe(style_ranking_table(df_emp_arena[['Campaña', 'Empresa', 'P50 Arena Bombeada (tn)']]),
             use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
st.subheader("Ranking según Fracspacing", divider="blue")
st.caption("Fracspacing = longitud_rama_horizontal_m / cantidad_fracturas")
st.caption("Fracspacing más agresivo = Menor Fracspacing")

df_fracspacing_base = df_merged_VMUT_filtered.copy()
df_fracspacing_base['fracspacing'] = (
    df_fracspacing_base['longitud_rama_horizontal_m'] / df_fracspacing_base['cantidad_fracturas']
)
df_fracspacing_base = df_fracspacing_base[
    df_fracspacing_base['fracspacing'].notna() & (df_fracspacing_base['fracspacing'] > 0)
]

# ── Petrolífero Pozos ────────────────────────────────────────────────────────
df_petro_frac = df_fracspacing_base[df_fracspacing_base['tipopozoNEW'] == 'Petrolífero']

top_petro_frac = (
    df_petro_frac
    .groupby(['start_year', 'sigla', 'empresaNEW'])
    .agg(fracspacing=('fracspacing', 'min'))
    .reset_index()
    .sort_values(['start_year', 'fracspacing'], ascending=[True, True])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_petro_frac_final = top_petro_frac.rename(columns={
    'start_year': 'Campaña', 'sigla': 'Sigla',
    'empresaNEW': 'Empresa', 'fracspacing': 'Mínimo Fracspacing (m)'
})
df_petro_frac_final['Mínimo Fracspacing (m)'] = df_petro_frac_final['Mínimo Fracspacing (m)'].round(0).astype(int)

st.write("**Tipo Petrolífero: Top 3 Pozos con Fracspacing más Agresivo**")
st.dataframe(style_ranking_table(df_petro_frac_final[['Campaña', 'Sigla', 'Empresa', 'Mínimo Fracspacing (m)']]),
             use_container_width=True, hide_index=True)

# ── Petrolífero Empresas (P50) ───────────────────────────────────────────────
top3_petro_frac_emp = (
    df_petro_frac
    .groupby(['start_year', 'empresaNEW'])
    .agg(p50_fracspacing=('fracspacing', 'median'))
    .reset_index()
    .sort_values(['start_year', 'p50_fracspacing'], ascending=[True, True])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_petro_frac_emp = top3_petro_frac_emp.rename(columns={
    'start_year': 'Campaña', 'empresaNEW': 'Empresa', 'p50_fracspacing': 'P50 Fracspacing (m)'
})
df_petro_frac_emp['P50 Fracspacing (m)'] = df_petro_frac_emp['P50 Fracspacing (m)'].round(0).astype(int)

st.write("**Top 3 Empresas con Fracspacing más Agresivo - Petrolífero**")
st.dataframe(style_ranking_table(df_petro_frac_emp[['Campaña', 'Empresa', 'P50 Fracspacing (m)']]),
             use_container_width=True, hide_index=True)

# ── Gasífero Pozos ───────────────────────────────────────────────────────────
df_gas_frac = df_fracspacing_base[df_fracspacing_base['tipopozoNEW'] == 'Gasífero']

top_gas_frac = (
    df_gas_frac
    .groupby(['start_year', 'sigla', 'empresaNEW'])
    .agg(fracspacing=('fracspacing', 'min'))
    .reset_index()
    .sort_values(['start_year', 'fracspacing'], ascending=[True, True])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_gas_frac_final = top_gas_frac.rename(columns={
    'start_year': 'Campaña', 'sigla': 'Sigla',
    'empresaNEW': 'Empresa', 'fracspacing': 'Mínimo Fracspacing (m)'
})
df_gas_frac_final['Mínimo Fracspacing (m)'] = df_gas_frac_final['Mínimo Fracspacing (m)'].round(0).astype(int)

st.write("**Tipo Gasífero: Top 3 Pozos con Fracspacing más Agresivo**")
st.dataframe(style_ranking_table(df_gas_frac_final[['Campaña', 'Sigla', 'Empresa', 'Mínimo Fracspacing (m)']]),
             use_container_width=True, hide_index=True)

# ── Gasífero Empresas (P50) ──────────────────────────────────────────────────
top3_gas_frac_emp = (
    df_gas_frac
    .groupby(['start_year', 'empresaNEW'])
    .agg(p50_fracspacing=('fracspacing', 'median'))
    .reset_index()
    .sort_values(['start_year', 'p50_fracspacing'], ascending=[True, True])
    .groupby('start_year').head(3)
    .reset_index(drop=True)
)
df_gas_frac_emp = top3_gas_frac_emp.rename(columns={
    'start_year': 'Campaña', 'empresaNEW': 'Empresa', 'p50_fracspacing': 'P50 Fracspacing (m)'
})
df_gas_frac_emp['P50 Fracspacing (m)'] = df_gas_frac_emp['P50 Fracspacing (m)'].round(0).astype(int)

st.write("**Top 3 Empresas con Fracspacing más Agresivo - Gasífero**")
st.dataframe(style_ranking_table(df_gas_frac_emp[['Campaña', 'Empresa', 'P50 Fracspacing (m)']]),
             use_container_width=True, hide_index=True)
