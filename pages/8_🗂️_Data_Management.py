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
st.header(f":blue[Reporte Extensivo de Completación y Producción en Vaca Muerta]")
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
# df_merged_final = df_merged_final[df_merged_final['id_base_fractura_adjiv'].notna()] 

# Check the dataframe info and columns
print(df_merged_final.info())
print(df_merged_final.columns)

# -----------------------------------------------

# Only keep VMUT as the target formation and filter for SHALE resource type
df_merged_VMUT = df_merged_final[
    (df_merged_final['formprod'] == 'VMUT') & (df_merged_final['sub_tipo_recurso'] == 'SHALE')
]

# ================================================
# NUEVAS COLUMNAS — se calculan una sola vez acá
# y se reutilizan en todo lo que sigue
# ================================================

df_merged_final['prod_total']     = df_merged_final['Np'].fillna(0) + df_merged_final['Gp'].fillna(0)
df_merged_final['sin_datos_frac'] = df_merged_final['id_base_fractura_adjiv'].isna()
df_merged_final['anio_inicio']    = pd.to_datetime(df_merged_final['date']).dt.year

# Score de calidad por pozo (0–100): completitud de los 3 campos críticos de fractura
campos_criticos = ['longitud_rama_horizontal_m', 'cantidad_fracturas', 'arena_total_tn']
df_merged_final['score_calidad'] = (
    df_merged_final[campos_criticos].notna().sum(axis=1) / len(campos_criticos) * 100
).round(1)

# ------------------------------------------------
st.subheader("Diagnóstico de Calidad de Datos por Empresa", divider="blue")

st.info("""
Esta sección muestra dónde faltan datos de fractura en los pozos más relevantes 
de Vaca Muerta.

El foco está en producción, no en cantidad de pozos, para evidenciar qué empresas 
tienen información crítica incompleta que puede afectar análisis y rankings.
""")

# ================================================
# NUEVO: KPIs GLOBALES
# ================================================

_df_dedup         = df_merged_final.drop_duplicates('sigla')
total_pozos_g     = _df_dedup['sigla'].nunique()
pozos_sin_frac_g  = int(_df_dedup['sin_datos_frac'].sum())
prod_total_g      = df_merged_final['prod_total'].sum()
prod_sin_frac_g   = df_merged_final[df_merged_final['sin_datos_frac']]['prod_total'].sum()
pct_prod_g        = prod_sin_frac_g / prod_total_g * 100 if prod_total_g else 0
score_medio_g     = _df_dedup['score_calidad'].mean()

st.subheader("Resumen Global", divider="grey")
_c1, _c2, _c3, _c4, _c5 = st.columns(5)
_c1.metric("Total Pozos",         f"{total_pozos_g:,}")
_c2.metric("Sin Datos Fractura",  f"{pozos_sin_frac_g:,}",
           delta=f"-{pozos_sin_frac_g/total_pozos_g*100:.1f}% del total", delta_color="inverse")
_c3.metric("Producción Total",    f"{prod_total_g:,.0f}")
_c4.metric("Prod. sin Fractura",  f"{prod_sin_frac_g:,.0f}",
           delta=f"-{pct_prod_g:.1f}% del total", delta_color="inverse")
_c5.metric("Score Calidad Medio", f"{score_medio_g:.1f} / 100")

st.divider()

# ==============================
# 📈 Ranking Data Management por Impacto de Datos Faltantes
# ==============================
st.subheader("Ranking Data Management: Impacto por Producción sin Datos de Fractura")

df_dm = df_merged_final.copy()

# Ranking por empresa — cálculo seguro sin lambda sobre df externo
_sin_frac_stats = (
    df_dm[df_dm['sin_datos_frac']]
    .groupby('empresaNEW')
    .agg(prod_sin_frac=('prod_total', 'sum'), pozos_sin_frac=('sigla', 'nunique'))
    .reset_index()
)
ranking_dm = (
    df_dm.groupby('empresaNEW')
    .agg(prod_total=('prod_total', 'sum'), pozos_total=('sigla', 'nunique'))
    .reset_index()
    .merge(_sin_frac_stats, on='empresaNEW', how='left')
)
ranking_dm[['prod_sin_frac', 'pozos_sin_frac']] = ranking_dm[['prod_sin_frac', 'pozos_sin_frac']].fillna(0)

# % incompleto
ranking_dm['pct_incompleto'] = (ranking_dm['prod_sin_frac'] / ranking_dm['prod_total']) * 100

# Ordenar por impacto absoluto
ranking_dm = ranking_dm.sort_values('prod_sin_frac', ascending=False)

# Formatear números con separadores de miles
ranking_dm['prod_total_fmt']     = ranking_dm['prod_total'].map('{:,.0f}'.format)
ranking_dm['prod_sin_frac_fmt']  = ranking_dm['prod_sin_frac'].map('{:,.0f}'.format)
ranking_dm['pct_incompleto_fmt'] = ranking_dm['pct_incompleto'].map('{:.1f}%'.format)
ranking_dm['pozos_sin_frac_fmt'] = ranking_dm['pozos_sin_frac'].astype(int).map('{:,}'.format)

# Mostrar tabla limpia en Streamlit — ahora con columna extra de pozos sin fractura
st.dataframe(
    ranking_dm[['empresaNEW', 'prod_total_fmt', 'prod_sin_frac_fmt', 'pct_incompleto_fmt', 'pozos_sin_frac_fmt']].rename(columns={
        'empresaNEW':          'Empresa',
        'prod_total_fmt':      'Prod. Total',
        'prod_sin_frac_fmt':   'Prod. sin Fractura',
        'pct_incompleto_fmt':  '% Incompleto',
        'pozos_sin_frac_fmt':  'Pozos sin Fractura',
    }),
    use_container_width=True,
    hide_index=True,
)

# ================================================
# NUEVO: Bubble chart — reemplaza el bar simple
# 3 dimensiones: prod total / % incompleto / volumen en riesgo
# ================================================

fig_dm = px.scatter(
    ranking_dm,
    x='pct_incompleto',
    y='prod_total',
    size='prod_sin_frac',
    size_max=60,
    color='pct_incompleto',
    color_continuous_scale='RdYlGn_r',
    range_color=[0, 100],
    hover_name='empresaNEW',
    hover_data={
        'prod_total':     ':,.0f',
        'prod_sin_frac':  ':,.0f',
        'pct_incompleto': ':.1f',
        'pozos_total':    True,
        'pozos_sin_frac': True,
    },
    text='empresaNEW',
    title='Mapa de Riesgo: Producción Total vs % Datos Incompletos',
    labels={
        'pct_incompleto': '% Producción sin datos de fractura',
        'prod_total':     'Producción Total',
        'prod_sin_frac':  'Prod. sin datos de fractura',
    },
)
fig_dm.update_traces(
    textposition='top center',
    textfont=dict(size=10),
    marker=dict(line=dict(width=1, color='white')),
)
fig_dm.update_layout(
    template='plotly_white',
    xaxis_title='% Producción sin datos de fractura',
    yaxis_title='Producción Total',
    yaxis_tickformat=',',
    coloraxis_colorbar=dict(title='% Incompleto', ticksuffix='%'),
)
fig_dm.add_vline(x=50, line_dash='dash', line_color='orange',
                 annotation_text='50% umbral', annotation_position='top right')
fig_dm.add_vline(x=80, line_dash='dash', line_color='red',
                 annotation_text='80% crítico', annotation_position='top right')
st.plotly_chart(fig_dm, use_container_width=True)

# ================================================
# NUEVO: Heatmap temporal — empresa × año
# ================================================

st.subheader("Evolución Temporal de Datos Incompletos por Empresa", divider="grey")
st.caption("Porcentaje de pozos sin datos de fractura por empresa y año. Verde = completo. Rojo = crítico.")

pivot_temporal = (
    df_dm.groupby(['empresaNEW', 'anio_inicio'])['sin_datos_frac']
    .mean()
    .mul(100)
    .round(1)
    .unstack(fill_value=None)
)
# Ordenar: empresas con más datos faltantes arriba
pivot_temporal = pivot_temporal.loc[
    pivot_temporal.mean(axis=1).sort_values(ascending=False).index
]

fig_heat = go.Figure(data=go.Heatmap(
    z=pivot_temporal.values,
    x=pivot_temporal.columns.astype(str).tolist(),
    y=pivot_temporal.index.tolist(),
    colorscale='RdYlGn_r',
    zmin=0,
    zmax=100,
    text=pivot_temporal.applymap(lambda v: f"{v:.0f}%" if pd.notna(v) else "N/D").values,
    texttemplate='%{text}',
    textfont=dict(size=10),
    hoverongaps=False,
    colorbar=dict(title='% Incompleto', ticksuffix='%'),
))
fig_heat.update_layout(
    template='plotly_white',
    title='% Pozos sin Datos de Fractura — Empresa × Año',
    xaxis_title='Año',
    yaxis_title='Empresa',
    height=max(350, 30 * len(pivot_temporal)),
)
st.plotly_chart(fig_heat, use_container_width=True)

# ================================================
# NUEVO: Score de calidad por formación
# ================================================

st.subheader("Score de Calidad de Datos por Formación", divider="grey")
st.caption("Score promedio (0–100) según completitud de: longitud de rama, cantidad de fracturas y arena total.")

score_form = (
    df_merged_final.groupby('formprod')
    .agg(score_medio=('score_calidad', 'mean'), pozos=('sigla', 'nunique'))
    .reset_index()
    .sort_values('score_medio', ascending=True)
)
score_form['score_medio'] = score_form['score_medio'].round(1)
score_form['color'] = score_form['score_medio'].apply(
    lambda s: '#1E8449' if s >= 70 else ('#F39C12' if s >= 40 else '#C0392B')
)

fig_score = go.Figure(go.Bar(
    x=score_form['score_medio'],
    y=score_form['formprod'],
    orientation='h',
    text=score_form['score_medio'].astype(str) + ' pts',
    textposition='outside',
    marker_color=score_form['color'],
    customdata=score_form['pozos'],
    hovertemplate='<b>%{y}</b><br>Score: %{x:.1f}<br>Pozos: %{customdata}<extra></extra>',
))
fig_score.update_layout(
    template='plotly_white',
    title='Score de Calidad Promedio por Formación',
    xaxis_title='Score de Calidad (0–100)',
    yaxis_title='Formación',
    xaxis_range=[0, 115],
    height=max(300, 35 * len(score_form)),
)
fig_score.add_vline(x=70, line_dash='dot', line_color='#1E8449',
                    annotation_text='Umbral aceptable (70)', annotation_position='top right')
fig_score.add_vline(x=40, line_dash='dot', line_color='#C0392B',
                    annotation_text='Umbral crítico (40)', annotation_position='bottom right')
st.plotly_chart(fig_score, use_container_width=True)


# ==============================
# 🔍 ANÁLISIS POR EMPRESA
# ==============================

empresa_objetivo = st.selectbox(
    "Seleccionar Empresa",
    sorted(df_merged_final['empresaNEW'].dropna().unique())
)

df_emp = df_merged_final.drop_duplicates('sigla').copy()

df_emp = df_emp[df_emp['empresaNEW'] == empresa_objetivo]

# Métricas
total_pozos    = df_emp['sigla'].nunique()
pozos_sin_frac = df_emp['sin_datos_frac'].sum()
pct            = (pozos_sin_frac / total_pozos) * 100 if total_pozos > 0 else 0
prod_emp       = df_emp['prod_total'].sum()
prod_sin_emp   = df_emp[df_emp['sin_datos_frac']]['prod_total'].sum()
pct_prod_emp   = (prod_sin_emp / prod_emp * 100) if prod_emp > 0 else 0
score_emp      = df_emp['score_calidad'].mean()

# KPIs — ampliado a 5 columnas
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Pozos",        total_pozos)
col2.metric("Sin Datos Fractura", int(pozos_sin_frac),
            delta=f"-{pct:.1f}%", delta_color="inverse")
col3.metric("% Incompleto",       f"{pct:.1f}%")
col4.metric("Prod. sin Fractura", f"{prod_sin_emp:,.0f}",
            delta=f"-{pct_prod_emp:.1f}% del total", delta_color="inverse")
col5.metric("Score Calidad",      f"{score_emp:.1f} / 100")

# -----------------------------
# 📊 Breakdown por tipo
# -----------------------------
resumen_tipo = (
    df_emp.groupby('tipopozoNEW')
    .agg(
        total=('sigla', 'count'),
        sin_frac=('sin_datos_frac', 'sum')
    )
    .reset_index()
)

resumen_tipo['pct'] = (resumen_tipo['sin_frac'] / resumen_tipo['total']) * 100
resumen_tipo['color'] = resumen_tipo['pct'].apply(
    lambda p: '#1E8449' if p < 40 else ('#F39C12' if p < 70 else '#C0392B')
)

fig_tipo = go.Figure(go.Bar(
    x=resumen_tipo['tipopozoNEW'],
    y=resumen_tipo['pct'],
    text=resumen_tipo['pct'].round(1).astype(str) + '%',
    textposition='outside',
    marker_color=resumen_tipo['color'],
    customdata=resumen_tipo[['total', 'sin_frac']].values,
    hovertemplate=(
        '<b>%{x}</b><br>% incompleto: %{y:.1f}%<br>'
        'Total: %{customdata[0]}<br>Sin fractura: %{customdata[1]}<extra></extra>'
    ),
))
fig_tipo.update_layout(
    template='plotly_white',
    title='Datos Incompletos por Tipo de Pozo',
    yaxis_title='% Incompleto',
    xaxis_title='Tipo de Pozo',
    yaxis_range=[0, 115],
)
st.plotly_chart(fig_tipo, use_container_width=True)

# ================================================
# NUEVO: Evolución temporal para la empresa seleccionada
# ================================================

st.markdown("#### Evolución Temporal de Completitud")

df_emp_full = df_merged_final[df_merged_final['empresaNEW'] == empresa_objetivo].copy()
evol_anio = (
    df_emp_full.groupby('anio_inicio')['sin_datos_frac']
    .agg(total='count', sin_frac='sum')
    .reset_index()
)
evol_anio['pct_incompleto'] = (evol_anio['sin_frac'] / evol_anio['total'] * 100).round(1)
evol_anio['pct_completo']   = 100 - evol_anio['pct_incompleto']

fig_evol = go.Figure()
fig_evol.add_trace(go.Bar(
    x=evol_anio['anio_inicio'], y=evol_anio['pct_completo'],
    name='Con datos', marker_color='#1E8449',
    hovertemplate='%{x}: %{y:.1f}% completo<extra></extra>',
))
fig_evol.add_trace(go.Bar(
    x=evol_anio['anio_inicio'], y=evol_anio['pct_incompleto'],
    name='Sin datos', marker_color='#C0392B',
    hovertemplate='%{x}: %{y:.1f}% incompleto<extra></extra>',
))
fig_evol.update_layout(
    template='plotly_white',
    title=f'Completitud de Datos de Fractura — {empresa_objetivo}',
    barmode='stack',
    yaxis_title='% Pozos',
    xaxis_title='Año de Inicio',
    yaxis_range=[0, 110],
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
)
st.plotly_chart(fig_evol, use_container_width=True)

# -----------------------------
# 🔍 Pozos problemáticos
# -----------------------------
with st.expander("Ver pozos sin datos de fractura"):
    st.dataframe(
        df_emp[df_emp['sin_datos_frac']]
        [['sigla', 'tipopozoNEW', 'formprod', 'score_calidad']]  # + score_calidad
        .sort_values('score_calidad')
        .head(20),
        use_container_width=True,
        hide_index=True,
    )
