import plotly.graph_objects as go
import streamlit as st

st.subheader("Evolución del Fracspacing por Tipo de Pozo")

# Preparar estadísticas
stats_tipo = df_merged_VMUT.groupby(['start_year', 'tipopozoNEW']).agg(
    max_fracspacing=('fracspacing', 'max'),
    avg_fracspacing=('fracspacing', 'median')
).reset_index()

# Crear figura
fig = go.Figure()

for tipo in stats_tipo['tipopozoNEW'].unique():
    df_tipo = stats_tipo[stats_tipo['tipopozoNEW'] == tipo]

    # Línea P50 (mediana) → full
    fig.add_trace(go.Scatter(
        x=df_tipo['start_year'],
        y=df_tipo['avg_fracspacing'],
        mode='lines+markers',
        name=f'{tipo} P50',
        line=dict(color='green', width=3),
        marker=dict(size=8)
    ))

    # Línea MAX → dashed
    fig.add_trace(go.Scatter(
        x=df_tipo['start_year'],
        y=df_tipo['max_fracspacing'],
        mode='lines+markers',
        name=f'{tipo} Max',
        line=dict(color='green', width=3, dash='dot'),
        marker=dict(size=8)
    ))

    # Anotaciones P50
    for _, row in df_tipo.iterrows():
        fig.add_annotation(
            x=row['start_year'],
            y=row['avg_fracspacing'],
            text=f"{int(row['avg_fracspacing'])}",
            showarrow=False,
            yshift=-12,
            font=dict(color='green', size=10)
        )

    # Anotaciones MAX
    for _, row in df_tipo.iterrows():
        fig.add_annotation(
            x=row['start_year'],
            y=row['max_fracspacing'],
            text=f"{int(row['max_fracspacing'])}",
            showarrow=False,
            yshift=12,
            font=dict(color='green', size=10)
        )

# Layout
fig.update_layout(
    title="Fracspacing por Tipo de Pozo (Max y P50)",
    xaxis_title="Campaña",
    yaxis_title="Fracspacing (m/etapa)",
    legend_title="Indicador",
    template="plotly_white",
    hovermode="x unified"
)

# Mostrar en Streamlit
st.plotly_chart(fig, use_container_width=True)
