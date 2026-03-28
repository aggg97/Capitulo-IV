import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PALETA Y CONFIGURACIÓN VISUAL COMPARTIDA
# ============================================================

COLORS = {
    "primary":    "#1B4F72",   # azul petróleo oscuro
    "accent":     "#E67E22",   # naranja energía
    "ok":         "#1E8449",   # verde completo
    "warn":       "#F39C12",   # amarillo advertencia
    "danger":     "#C0392B",   # rojo crítico
    "bg":         "#F4F6F9",
    "grid":       "#DDE1E7",
    "text_light": "#7F8C8D",
}

PLOTLY_TEMPLATE = "plotly_white"

LAYOUT_DEFAULTS = dict(
    template=PLOTLY_TEMPLATE,
    font=dict(family="'IBM Plex Sans', sans-serif", size=12, color="#2C3E50"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=60, b=40, l=40, r=20),
    coloraxis_colorbar=dict(
        outlinewidth=0,
        tickfont=dict(size=11),
    ),
)

def apply_layout(fig, **extra):
    """Aplica configuración estándar de layout a cualquier figura."""
    fig.update_layout(**LAYOUT_DEFAULTS, **extra)
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False)
    return fig


def format_num(n, decimals=0):
    """Formatea un número con separadores de miles."""
    fmt = f"{{:,.{decimals}f}}"
    return fmt.format(n)


# ============================================================
# PREPARACIÓN DE DATOS PARA DATA MANAGEMENT
# (recibe df_merged_final ya construido en el script principal)
# ============================================================

def prepare_dm_dataframe(df_merged_final: pd.DataFrame) -> pd.DataFrame:
    """
    A partir del dataframe consolidado, agrega las columnas necesarias
    para el módulo de Data Management sin tocar el resto del pipeline.
    """
    df = df_merged_final.copy()

    # Producción total combinada (petróleo + gas)
    df["prod_total"] = df["Np"].fillna(0) + df["Gp"].fillna(0)

    # Flag: sin datos de fractura
    df["sin_datos_frac"] = df["id_base_fractura_adjiv"].isna()

    # Campos críticos de fractura para score de calidad
    campos_criticos = ["longitud_rama_horizontal_m", "cantidad_fracturas", "arena_total_tn"]
    df["score_calidad"] = (
        df[campos_criticos].notna().sum(axis=1) / len(campos_criticos) * 100
    ).round(1)

    # Año de inicio para análisis temporal
    df["anio_inicio"] = pd.to_datetime(df["date"]).dt.year

    return df


def build_ranking_dm(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking por empresa: producción total vs producción sin datos de fractura."""

    def prod_sin_frac(x):
        return df.loc[x.index].loc[df.loc[x.index, "sin_datos_frac"], "prod_total"].sum()

    ranking = (
        df.groupby("empresaNEW")
        .agg(
            prod_total=("prod_total", "sum"),
            pozos_total=("sigla", "nunique"),
        )
        .reset_index()
    )

    # Calcular producción y pozos sin fractura de forma segura
    sin_frac_stats = (
        df[df["sin_datos_frac"]]
        .groupby("empresaNEW")
        .agg(
            prod_sin_frac=("prod_total", "sum"),
            pozos_sin_frac=("sigla", "nunique"),
        )
        .reset_index()
    )

    ranking = ranking.merge(sin_frac_stats, on="empresaNEW", how="left")
    ranking[["prod_sin_frac", "pozos_sin_frac"]] = ranking[
        ["prod_sin_frac", "pozos_sin_frac"]
    ].fillna(0)

    ranking["pct_prod_incompleto"] = (
        ranking["prod_sin_frac"] / ranking["prod_total"].replace(0, pd.NA) * 100
    ).fillna(0).round(1)

    ranking["pct_pozos_incompleto"] = (
        ranking["pozos_sin_frac"] / ranking["pozos_total"].replace(0, pd.NA) * 100
    ).fillna(0).round(1)

    ranking = ranking.sort_values("prod_sin_frac", ascending=False).reset_index(drop=True)
    return ranking


# ============================================================
# SECCIÓN PRINCIPAL: DATA MANAGEMENT
# ============================================================

def render_data_management(df_merged_final: pd.DataFrame):

    st.header("🗂️ Diagnóstico de Calidad de Datos por Empresa", divider="blue")

    st.info(
        "Esta sección evalúa la completitud de los datos de fractura en los pozos de "
        "Vaca Muerta. El análisis se centra en el **impacto productivo** de los datos "
        "faltantes, no solo en la cantidad de pozos, para identificar qué empresas "
        "presentan brechas críticas de información."
    )

    # --- Preparar datos ---
    df = prepare_dm_dataframe(df_merged_final)
    ranking_dm = build_ranking_dm(df)

    # ─────────────────────────────────────────────
    # KPIs GLOBALES
    # ─────────────────────────────────────────────
    st.subheader("📊 Resumen Global", divider="grey")

    total_pozos_g    = df["sigla"].nunique()
    pozos_sin_frac_g = df[df["sin_datos_frac"]]["sigla"].nunique()
    prod_total_g     = df["prod_total"].sum()
    prod_sin_frac_g  = df[df["sin_datos_frac"]]["prod_total"].sum()
    pct_prod_g       = prod_sin_frac_g / prod_total_g * 100 if prod_total_g else 0
    pct_pozos_g      = pozos_sin_frac_g / total_pozos_g * 100 if total_pozos_g else 0
    score_medio_g    = df["score_calidad"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Pozos",          format_num(total_pozos_g))
    c2.metric("Sin Datos Fractura",   format_num(pozos_sin_frac_g),
              delta=f"-{pct_pozos_g:.1f}% del total", delta_color="inverse")
    c3.metric("Producción Total",     format_num(prod_total_g))
    c4.metric("Prod. sin Fractura",   format_num(prod_sin_frac_g),
              delta=f"-{pct_prod_g:.1f}% del total", delta_color="inverse")
    c5.metric("Score Calidad Medio",  f"{score_medio_g:.1f} / 100")

    st.divider()

    # ─────────────────────────────────────────────
    # GRÁFICO 1 — Bubble Chart: producción vs % incompleto
    # ─────────────────────────────────────────────
    st.subheader("🔵 Mapa de Riesgo: Producción vs Completitud", divider="grey")
    st.caption(
        "Cada burbuja es una empresa. El tamaño refleja la **producción sin datos de "
        "fractura** (impacto absoluto). El color indica el **% incompleto** (riesgo relativo)."
    )

    fig_bubble = px.scatter(
        ranking_dm,
        x="pct_prod_incompleto",
        y="prod_total",
        size="prod_sin_frac",
        size_max=60,
        color="pct_prod_incompleto",
        color_continuous_scale="RdYlGn_r",
        range_color=[0, 100],
        hover_name="empresaNEW",
        hover_data={
            "prod_total":          ":,.0f",
            "prod_sin_frac":       ":,.0f",
            "pct_prod_incompleto": ":.1f",
            "pozos_total":         True,
            "pozos_sin_frac":      True,
        },
        text="empresaNEW",
        labels={
            "pct_prod_incompleto": "% Producción sin datos",
            "prod_total":          "Producción Total",
            "prod_sin_frac":       "Prod. sin datos de fractura",
        },
        title="Mapa de Riesgo por Empresa",
    )
    fig_bubble.update_traces(
        textposition="top center",
        textfont=dict(size=10),
        marker=dict(line=dict(width=1, color="white")),
    )
    fig_bubble = apply_layout(
        fig_bubble,
        xaxis_title="% Producción sin datos de fractura",
        yaxis_title="Producción Total (m³ o Mm³)",
        yaxis_tickformat=",",
        coloraxis_colorbar=dict(title="% Incompleto"),
    )

    # Líneas de referencia
    fig_bubble.add_vline(x=50, line_dash="dash", line_color=COLORS["warn"],
                         annotation_text="50% umbral", annotation_position="top right")
    fig_bubble.add_vline(x=80, line_dash="dash", line_color=COLORS["danger"],
                         annotation_text="80% crítico", annotation_position="top right")

    st.plotly_chart(fig_bubble, use_container_width=True)

    # ─────────────────────────────────────────────
    # GRÁFICO 2 — Heatmap temporal por empresa
    # ─────────────────────────────────────────────
    st.subheader("🗓️ Evolución Temporal de Datos Incompletos", divider="grey")
    st.caption(
        "Porcentaje de pozos **sin datos de fractura** por empresa y año. "
        "Verde = completitud alta. Rojo = brechas críticas."
    )

    pivot_temporal = (
        df.groupby(["empresaNEW", "anio_inicio"])["sin_datos_frac"]
        .mean()
        .mul(100)
        .round(1)
        .unstack(fill_value=None)
    )

    # Ordenar empresas por % medio (peor arriba)
    pivot_temporal = pivot_temporal.loc[
        pivot_temporal.mean(axis=1).sort_values(ascending=False).index
    ]

    # Anotaciones formateadas
    text_annotations = pivot_temporal.applymap(
        lambda v: f"{v:.0f}%" if pd.notna(v) else "N/D"
    ).values

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=pivot_temporal.values,
            x=pivot_temporal.columns.astype(str).tolist(),
            y=pivot_temporal.index.tolist(),
            colorscale="RdYlGn_r",
            zmin=0,
            zmax=100,
            text=text_annotations,
            texttemplate="%{text}",
            textfont=dict(size=10),
            hoverongaps=False,
            colorbar=dict(title="% Incompleto", ticksuffix="%"),
        )
    )
    fig_heat = apply_layout(
        fig_heat,
        title="% Pozos sin Datos de Fractura — Empresa × Año",
        xaxis_title="Año",
        yaxis_title="Empresa",
        xaxis=dict(side="bottom"),
        height=max(350, 30 * len(pivot_temporal)),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # ─────────────────────────────────────────────
    # GRÁFICO 3 — Score de calidad por formación
    # ─────────────────────────────────────────────
    st.subheader("🏗️ Calidad de Datos por Formación", divider="grey")
    st.caption(
        "Score promedio (0–100) basado en completitud de campos clave de fractura: "
        "longitud de rama horizontal, cantidad de fracturas y arena total."
    )

    score_form = (
        df.groupby("formprod")
        .agg(
            score_medio=("score_calidad", "mean"),
            pozos=("sigla", "nunique"),
        )
        .reset_index()
        .sort_values("score_medio", ascending=True)
    )
    score_form["score_medio"] = score_form["score_medio"].round(1)
    score_form["color"] = score_form["score_medio"].apply(
        lambda s: COLORS["ok"] if s >= 70 else (COLORS["warn"] if s >= 40 else COLORS["danger"])
    )
    score_form["label"] = score_form["score_medio"].astype(str) + " pts"

    fig_score = go.Figure(
        go.Bar(
            x=score_form["score_medio"],
            y=score_form["formprod"],
            orientation="h",
            text=score_form["label"],
            textposition="outside",
            marker_color=score_form["color"],
            customdata=score_form["pozos"],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Score: %{x:.1f}<br>"
                "Pozos: %{customdata}<extra></extra>"
            ),
        )
    )
    fig_score = apply_layout(
        fig_score,
        title="Score de Calidad Promedio por Formación",
        xaxis_title="Score de Calidad (0–100)",
        yaxis_title="Formación",
        xaxis_range=[0, 115],
        height=max(300, 35 * len(score_form)),
    )
    fig_score.add_vline(x=70, line_dash="dot", line_color=COLORS["ok"],
                        annotation_text="Umbral aceptable (70)", annotation_position="top right")
    fig_score.add_vline(x=40, line_dash="dot", line_color=COLORS["danger"],
                        annotation_text="Umbral crítico (40)", annotation_position="bottom right")
    st.plotly_chart(fig_score, use_container_width=True)

    # ─────────────────────────────────────────────
    # RANKING TABLA DETALLADA
    # ─────────────────────────────────────────────
    st.subheader("📋 Ranking Detallado por Empresa", divider="grey")

    ranking_display = ranking_dm.copy()
    ranking_display.insert(0, "#", range(1, len(ranking_display) + 1))
    ranking_display["prod_total"]    = ranking_display["prod_total"].map("{:,.0f}".format)
    ranking_display["prod_sin_frac"] = ranking_display["prod_sin_frac"].map("{:,.0f}".format)
    ranking_display["pozos_sin_frac"]= ranking_display["pozos_sin_frac"].astype(int)
    ranking_display["pct_prod_incompleto"] = ranking_display["pct_prod_incompleto"].map("{:.1f}%".format)
    ranking_display["pct_pozos_incompleto"]= ranking_display["pct_pozos_incompleto"].map("{:.1f}%".format)

    ranking_display = ranking_display.rename(columns={
        "empresaNEW":             "Empresa",
        "prod_total":             "Prod. Total",
        "prod_sin_frac":          "Prod. sin Fractura",
        "pct_prod_incompleto":    "% Prod. Incompleta",
        "pozos_total":            "Pozos Totales",
        "pozos_sin_frac":         "Pozos sin Fractura",
        "pct_pozos_incompleto":   "% Pozos Incompletos",
    })

    st.dataframe(
        ranking_display[[
            "#", "Empresa", "Prod. Total", "Prod. sin Fractura",
            "% Prod. Incompleta", "Pozos Totales", "Pozos sin Fractura", "% Pozos Incompletos"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    # ─────────────────────────────────────────────
    # ANÁLISIS POR EMPRESA (drill-down)
    # ─────────────────────────────────────────────
    st.subheader("🔍 Análisis por Empresa", divider="grey")

    empresa_objetivo = st.selectbox(
        "Seleccionar Empresa",
        sorted(df["empresaNEW"].dropna().unique()),
        key="dm_empresa_selectbox",
    )

    df_emp = df.drop_duplicates("sigla").copy()
    df_emp = df_emp[df_emp["empresaNEW"] == empresa_objetivo]

    total_pozos   = df_emp["sigla"].nunique()
    pozos_sin_frac = int(df_emp["sin_datos_frac"].sum())
    pct_pozos     = (pozos_sin_frac / total_pozos * 100) if total_pozos > 0 else 0
    prod_emp      = df_emp["prod_total"].sum()
    prod_sin_frac = df_emp[df_emp["sin_datos_frac"]]["prod_total"].sum()
    pct_prod      = (prod_sin_frac / prod_emp * 100) if prod_emp > 0 else 0
    score_emp     = df_emp["score_calidad"].mean()

    # KPIs empresa
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Pozos",         format_num(total_pozos))
    k2.metric("Sin Datos Fractura",  pozos_sin_frac,
              delta=f"-{pct_pozos:.1f}%", delta_color="inverse")
    k3.metric("Prod. Total",         format_num(prod_emp))
    k4.metric("Prod. sin Fractura",  format_num(prod_sin_frac),
              delta=f"-{pct_prod:.1f}%", delta_color="inverse")
    k5.metric("Score Calidad",       f"{score_emp:.1f} / 100")

    col_izq, col_der = st.columns(2)

    # — Breakdown por tipo de pozo
    with col_izq:
        resumen_tipo = (
            df_emp.groupby("tipopozoNEW")
            .agg(total=("sigla", "count"), sin_frac=("sin_datos_frac", "sum"))
            .reset_index()
        )
        resumen_tipo["pct"] = (resumen_tipo["sin_frac"] / resumen_tipo["total"] * 100).round(1)
        resumen_tipo["label"] = resumen_tipo["pct"].astype(str) + "%"
        resumen_tipo["color"] = resumen_tipo["pct"].apply(
            lambda p: COLORS["ok"] if p < 40 else (COLORS["warn"] if p < 70 else COLORS["danger"])
        )

        fig_tipo = go.Figure(
            go.Bar(
                x=resumen_tipo["tipopozoNEW"],
                y=resumen_tipo["pct"],
                text=resumen_tipo["label"],
                textposition="outside",
                marker_color=resumen_tipo["color"],
                customdata=resumen_tipo[["total", "sin_frac"]].values,
                hovertemplate=(
                    "<b>%{x}</b><br>% incompleto: %{y:.1f}%<br>"
                    "Total: %{customdata[0]}<br>Sin fractura: %{customdata[1]}<extra></extra>"
                ),
            )
        )
        fig_tipo = apply_layout(
            fig_tipo,
            title="% Incompleto por Tipo de Pozo",
            yaxis_title="% Incompleto",
            yaxis_range=[0, 115],
        )
        st.plotly_chart(fig_tipo, use_container_width=True)

    # — Score de calidad por campo (areayacimiento)
    with col_der:
        if "areayacimiento" in df_emp.columns:
            score_area = (
                df_emp.groupby("areayacimiento")["score_calidad"]
                .mean()
                .round(1)
                .reset_index()
                .sort_values("score_calidad", ascending=True)
            )
            score_area["color"] = score_area["score_calidad"].apply(
                lambda s: COLORS["ok"] if s >= 70 else (COLORS["warn"] if s >= 40 else COLORS["danger"])
            )

            fig_area = go.Figure(
                go.Bar(
                    x=score_area["score_calidad"],
                    y=score_area["areayacimiento"],
                    orientation="h",
                    text=score_area["score_calidad"].astype(str) + " pts",
                    textposition="outside",
                    marker_color=score_area["color"],
                )
            )
            fig_area = apply_layout(
                fig_area,
                title="Score de Calidad por Área/Yacimiento",
                xaxis_title="Score (0–100)",
                xaxis_range=[0, 115],
                height=max(280, 35 * len(score_area)),
            )
            st.plotly_chart(fig_area, use_container_width=True)

    # — Evolución temporal para la empresa seleccionada
    st.markdown("#### Evolución Temporal de Completitud")

    df_emp_full = df[df["empresaNEW"] == empresa_objetivo].copy()
    evol_anio = (
        df_emp_full.groupby("anio_inicio")["sin_datos_frac"]
        .agg(total="count", sin_frac="sum")
        .reset_index()
    )
    evol_anio["pct_incompleto"] = (evol_anio["sin_frac"] / evol_anio["total"] * 100).round(1)
    evol_anio["pct_completo"]   = 100 - evol_anio["pct_incompleto"]

    fig_evol = go.Figure()
    fig_evol.add_trace(go.Bar(
        x=evol_anio["anio_inicio"], y=evol_anio["pct_completo"],
        name="Con datos", marker_color=COLORS["ok"],
        hovertemplate="%{x}: %{y:.1f}% completo<extra></extra>",
    ))
    fig_evol.add_trace(go.Bar(
        x=evol_anio["anio_inicio"], y=evol_anio["pct_incompleto"],
        name="Sin datos", marker_color=COLORS["danger"],
        hovertemplate="%{x}: %{y:.1f}% incompleto<extra></extra>",
    ))
    fig_evol = apply_layout(
        fig_evol,
        title=f"Completitud de Datos de Fractura — {empresa_objetivo}",
        barmode="stack",
        yaxis_title="% Pozos",
        xaxis_title="Año de Inicio",
        yaxis_range=[0, 110],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_evol, use_container_width=True)

    # — Tabla de pozos problemáticos
    with st.expander("📄 Ver pozos sin datos de fractura"):
        cols_show = [c for c in ["sigla", "tipopozoNEW", "formprod", "areayacimiento",
                                  "score_calidad", "anio_inicio"] if c in df_emp.columns]
        st.dataframe(
            df_emp[df_emp["sin_datos_frac"]][cols_show]
            .sort_values("score_calidad")
            .head(50),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# PUNTO DE ENTRADA — llamar desde el script principal así:
#
#   from data_management_section import render_data_management
#   render_data_management(df_merged_final)
#
# ============================================================
