import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & THEMING
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TLV - Dashboard Ejecutivo",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={}
)

# Custom CSS for professional look
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #f8fafc;
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #2563eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Dividers */
    hr {
        margin: 2rem 0;
        border: 0;
        border-top: 2px solid #e2e8f0;
    }
    
    /* Headers */
    h1 {
        color: #1b2a4a;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #1b2a4a;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    h3 {
        color: #334155;
        font-weight: 500;
    }
    
    /* Info box */
    .stInfo {
        background-color: #f0f9ff;
        border-left: 4px solid #0284c7;
    }
    
    /* Success/Warning boxes */
    .stSuccess {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
    }
    
    .stWarning {
        background-color: #fffbeb;
        border-left: 4px solid #d97706;
    }
    
    .stError {
        background-color: #fef2f2;
        border-left: 4px solid #dc2626;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f1f5f9;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER BANNER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background: linear-gradient(135deg, #1b2a4a 0%, #2563eb 100%); 
            padding: 2rem; border-radius: 8px; margin-bottom: 2rem;">
    <h1 style="color: white; margin: 0;">📊 TeleVía | Dashboard Ejecutivo</h1>
    <p style="color: #cbd5e1; margin: 0.5rem 0 0 0; font-size: 0.95rem;">
        Encuesta de Satisfacción · Servicio Integral de Concesiones
    </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(file_path):
    """Carga el archivo Excel con manejo de errores"""
    try:
        df = pd.read_excel(file_path, sheet_name=0)
        return df
    except FileNotFoundError:
        st.error(f"❌ Archivo no encontrado: {file_path}")
        st.info("Asegúrate de que 'dashboard_televia.xlsx' esté en el directorio raíz.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {e}")
        st.stop()

EXCEL_FILE = "dashboard_televia.xlsx"
df_raw = load_data(EXCEL_FILE)
df = df_raw.copy()

# ─────────────────────────────────────────────────────────────────────────────
# PROCESAMIENTO DE DATOS
# ─────────────────────────────────────────────────────────────────────────────

# Limpiar nombres de columnas
df.columns = df.columns.str.strip()

# Detectar columna de concesión
concesion_col = "Concesion"
if concesion_col not in df.columns:
    st.error("❌ No se encontró la columna 'Concesion'")
    st.stop()

# Detectar columnas numéricas (preguntas de la encuesta)
numeric_cols = [
    'Eficiencia_operativa',
    'Tiempos_respuesta',
    'Precision_conciliaciones',
    'Facilidad_procesos',
    'Incobrables',
    'Monitoreo',
    'Comunicacion_eventos',
    'Dispersion_pagos',
    'Transparencia_reportes',
    'Acompanamiento_comercial',
    'Info_comercial',
    'Reuniones_mensuales',
    'Comunicacion_proactiva'
]

# Agregar la pregunta larga de BI con nombre corto
bi_col = [c for c in df.columns if '¿Qué tan funcional considera el reponte de BI' in c]
if bi_col:
    numeric_cols.insert(12, bi_col[0])

# Agregar pregunta de satisfacción general
sat_col = [c for c in df.columns if 'En general, ¿Qué tan satisfecho' in c]
if sat_col:
    numeric_cols.append(sat_col[0])

# Filtrar solo columnas que existan
q_cols = [c for c in numeric_cols if c in df.columns]

if len(q_cols) < 3:
    st.error("❌ No se detectaron preguntas numéricas válidas")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULOS BASE
# ─────────────────────────────────────────────────────────────────────────────

# Nombres legibles para las preguntas
question_labels = {
    'Eficiencia_operativa': 'Eficiencia Operativa',
    'Tiempos_respuesta': 'Tiempos de Respuesta',
    'Precision_conciliaciones': 'Precisión Conciliaciones',
    'Facilidad_procesos': 'Facilidad Procesos',
    'Incobrables': 'Gestión Incobrables',
    'Monitoreo': 'Monitoreo 24/7',
    'Comunicacion_eventos': 'Comunicación Incidencias',
    'Dispersion_pagos': 'Dispersión de Pagos',
    'Transparencia_reportes': 'Reportes Financieros',
    'Acompanamiento_comercial': 'Acompañamiento Comercial',
    'Info_comercial': 'Información Comercial',
    'Reuniones_mensuales': 'Reuniones Mensuales',
    'Comunicacion_proactiva': 'Comunicación Proactiva'
}

# Score promedio por respondente
df["Score_Promedio"] = df[q_cols].mean(axis=1)

def semaforo(x):
    """Retorna emoji y etiqueta según score"""
    if x >= 8.0:
        return "🟢", "Alto"
    elif x >= 6.5:
        return "🟡", "Medio"
    else:
        return "🔴", "Crítico"

df["Semaforo_Emoji"], df["Semaforo_Label"] = zip(*df["Score_Promedio"].apply(semaforo))

# Agregados por concesión
conc_stats = df.groupby(concesion_col).agg({
    "Score_Promedio": ["mean", "count", "std"]
}).round(2)
conc_stats.columns = ["Score", "Respondentes", "Desv_Est"]
conc_stats = conc_stats.reset_index()
conc_stats = conc_stats.sort_values("Score", ascending=False)
conc_stats["Ranking"] = range(1, len(conc_stats) + 1)

# Promedio global
global_score = df["Score_Promedio"].mean()
global_score_rounded = round(global_score, 2)

# Promedio por pregunta con nombres legibles
q_stats = []
for col in q_cols:
    label = question_labels.get(col, col.replace('_', ' ').title())
    score = df[col].mean()
    q_stats.append({"Pregunta": label, "Score": score})

q_stats = pd.DataFrame(q_stats).sort_values("Score", ascending=False).round(2)

# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICAS EJECUTIVAS (KPIs)
# ─────────────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    emoji_global, label_global = semaforo(global_score)
    st.metric(
        label="Score Global Promedio",
        value=f"{global_score_rounded}/10",
        delta=f"{emoji_global} {label_global}",
        delta_color="off"
    )

with col2:
    mejor_conc = conc_stats.iloc[0]
    st.metric(
        label="Mejor Concesión",
        value=mejor_conc[concesion_col][:25],
        delta=f"{round(mejor_conc['Score'], 2)}/10"
    )

with col3:
    peor_conc = conc_stats.iloc[-1]
    st.metric(
        label="Concesión en Riesgo",
        value=peor_conc[concesion_col][:25],
        delta=f"{round(peor_conc['Score'], 2)}/10",
        delta_color="inverse"
    )

with col4:
    st.metric(
        label="Total Respondentes",
        value=len(df),
        delta=f"{df[concesion_col].nunique()} concesiones"
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# INSIGHT EJECUTIVO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 🧠 Insight Ejecutivo")

col_insight1, col_insight2, col_insight3, col_insight4 = st.columns(4)

with col_insight1:
    best_q = q_stats.iloc[0]
    st.info(f"""
    **✅ Dimensión Mejor Evaluada**
    
    {best_q['Pregunta']}
    
    Score: {best_q['Score']:.2f}/10
    """)

with col_insight2:
    worst_q = q_stats.iloc[-1]
    st.error(f"""
    **⚠ Dimensión Más Crítica**
    
    {worst_q['Pregunta']}
    
    Score: {worst_q['Score']:.2f}/10
    """)

with col_insight3:
    delta_best = round(mejor_conc['Score'] - global_score, 2)
    st.success(f"""
    **🏆 Concesión Top Performer**
    
    {mejor_conc[concesion_col]}
    
    +{delta_best:.2f} vs promedio
    """)

with col_insight4:
    delta_worst = round(peor_conc['Score'] - global_score, 2)
    st.warning(f"""
    **🚨 Concesión Requiere Acción**
    
    {peor_conc[concesion_col]}
    
    {delta_worst:.2f} vs promedio
    """)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# RANKING DE CONCESIONES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📈 Ranking de Concesiones")

fig_ranking = px.bar(
    conc_stats,
    x=concesion_col,
    y="Score",
    color="Score",
    text="Score",
    color_continuous_scale="RdYlGn",
    range_color=[5, 10],
    hover_data={
        "Respondentes": True,
        "Desv_Est": ":.2f",
        "Ranking": True,
        "Score": ":.2f"
    }
)

fig_ranking.update_traces(
    texttemplate="<b>%{text:.2f}</b>",
    textposition="outside",
    marker=dict(line=dict(color="white", width=2))
)

fig_ranking.update_layout(
    xaxis_title="",
    yaxis_title="Score (1–10)",
    height=450,
    showlegend=False,
    hovermode="x unified",
    font=dict(size=11),
    plot_bgcolor="white",
    yaxis=dict(gridcolor="#e2e8f0"),
)

st.plotly_chart(fig_ranking, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TABLA COMPLETA DE DIMENSIONES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📊 Desempeño Global de Todas las Dimensiones")

# Agregar semáforos a la tabla
q_stats_display = q_stats.copy()
q_stats_display["Semáforo"] = q_stats_display["Score"].apply(
    lambda x: "🟢 Alto" if x >= 8.0 else ("🟡 Medio" if x >= 6.5 else "🔴 Crítico")
)

st.dataframe(
    q_stats_display[["Pregunta", "Score", "Semáforo"]].style.format({
        "Score": "{:.2f}"
    }).background_gradient(
        subset=["Score"],
        cmap="RdYlGn",
        vmin=5,
        vmax=10
    ),
    use_container_width=True,
    height=600
)

# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICO HORIZONTAL DE TODAS LAS DIMENSIONES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📈 Vista Gráfica de Todas las Dimensiones")

fig_all_dims = px.bar(
    q_stats_display.sort_values("Score"),
    x="Score",
    y="Pregunta",
    orientation="h",
    color="Score",
    text="Score",
    color_continuous_scale="RdYlGn",
    range_color=[5, 10],
    hover_data={"Score": ":.2f"},
    height=max(400, len(q_stats_display) * 25)
)

fig_all_dims.update_traces(
    texttemplate="<b>%{text:.2f}</b>",
    textposition="outside",
    marker=dict(line=dict(color="white", width=1))
)

fig_all_dims.update_layout(
    xaxis_title="Score (1–10)",
    yaxis_title="",
    showlegend=False,
    hovermode="y unified",
    font=dict(size=10),
    plot_bgcolor="white",
    xaxis=dict(gridcolor="#e2e8f0"),
)

st.plotly_chart(fig_all_dims, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MATRIZ DE CONCESIONES × PREGUNTAS (HEATMAP)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 🔥 Heatmap: Concesiones × Dimensiones")

# Crear matriz de scores por concesión y pregunta
heatmap_data = df.groupby(concesion_col)[q_cols].mean().round(2)
heatmap_data = heatmap_data.sort_values(by=q_cols[0] if len(q_cols) > 0 else None, ascending=False)

# Renombrar columnas para hacerlas más legibles
heatmap_data.columns = [question_labels.get(c, c.replace('_', ' ').title()) for c in heatmap_data.columns]

fig_heatmap = go.Figure(
    data=go.Heatmap(
        z=heatmap_data.values,
        x=[c[:20] + "..." if len(c) > 20 else c for c in heatmap_data.columns],
        y=heatmap_data.index,
        colorscale="RdYlGn",
        zmin=1,
        zmax=10,
        text=heatmap_data.values,
        texttemplate="<b>%{text:.1f}</b>",
        textfont={"size": 9},
        colorbar=dict(title="Score")
    )
)

fig_heatmap.update_layout(
    height=400 + len(heatmap_data) * 30,
    xaxis_title="",
    yaxis_title="Concesión",
    font=dict(size=10),
)

st.plotly_chart(fig_heatmap, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TABLA RESUMEN POR CONCESIÓN
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📋 Resumen por Concesión")

display_df = conc_stats[[concesion_col, "Ranking", "Score", "Respondentes", "Desv_Est"]].copy()
display_df.columns = ["Concesión", "Ranking", "Score", "Respondentes", "Desv. Est"]

st.dataframe(
    display_df.style.format({
        "Score": "{:.2f}",
        "Desv. Est": "{:.2f}"
    }).background_gradient(
        subset=["Score"],
        cmap="RdYlGn",
        vmin=5,
        vmax=10
    ),
    use_container_width=True,
    height=300
)

# ─────────────────────────────────────────────────────────────────────────────
# DATOS COMPLETOS (EXPANDIBLE)
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📖 Ver todos los datos detallados"):
    st.markdown("**Tabla completa de respuestas individuales**")
    
    # Preparar tabla para mostrar
    display_all = df[[concesion_col, "Cargo", "Score_Promedio", "Semaforo_Label"] + q_cols].copy()
    display_all.columns = [concesion_col, "Cargo", "Score Promedio", "Estado"] + [
        question_labels.get(c, c.replace('_', ' ').title()) for c in q_cols
    ]
    
    st.dataframe(
        display_all.style.format({
            "Score Promedio": "{:.2f}"
        }),
        use_container_width=True,
        height=600
    )

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()

st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 2rem;">
    <p><strong>Dashboard Ejecutivo TeleVía</strong> · Encuesta de Satisfacción del Servicio Integral</p>
    <p>Actualizado: """ + datetime.now().strftime("%d/%m/%Y %H:%M") + """</p>
    <p>📊 Metodología: Promedio simple de respuestas en escala 1–10 · Umbrales: Verde ≥8.0 | Amarillo 6.5–7.9 | Rojo <6.5</p>
</div>
""", unsafe_allow_html=True)
