import streamlit as st
import pandas as pd
import plotly.express as px

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="TLV - Dashboard Ejecutivo",
    layout="wide"
)

st.title("📊 TLV | Dashboard Ejecutivo de Concesiones")

# ─────────────────────────────────────────
# CARGA AUTOMÁTICA DEL EXCEL DEL REPOSITORIO
# ─────────────────────────────────────────
EXCEL_FILE = "dashboard_televia.xlsx"

try:
    df = pd.read_excel(EXCEL_FILE)

except Exception as e:
    st.error("❌ No se pudo cargar el archivo Excel.")
    st.write(e)
    st.stop()

# ─────────────────────────────────────────
# LIMPIEZA COLUMNAS
# ─────────────────────────────────────────
df.columns = (
    df.columns
    .str.strip()
    .str.replace("\n", " ", regex=False)
    .str.replace("\xa0", " ", regex=False)
)

# ─────────────────────────────────────────
# DETECTAR COLUMNA CONCESIÓN
# ─────────────────────────────────────────
concesion_col = [c for c in df.columns if "conces" in c.lower()]

if len(concesion_col) == 0:
    st.error("❌ No se encontró columna de concesión")
    st.write(df.columns.tolist())
    st.stop()

concesion_col = concesion_col[0]

# ─────────────────────────────────────────
# DETECTAR COLUMNAS NUMÉRICAS
# ─────────────────────────────────────────
exclude = [concesion_col]

q_cols = [
    c for c in df.columns
    if c not in exclude
    and pd.api.types.is_numeric_dtype(df[c])
]

if len(q_cols) < 3:
    st.error("❌ No se detectaron preguntas numéricas válidas")
    st.write(q_cols)
    st.stop()

# ─────────────────────────────────────────
# SCORE GLOBAL
# ─────────────────────────────────────────
df["Score"] = df[q_cols].mean(axis=1)

# ─────────────────────────────────────────
# SEMÁFORO
# ─────────────────────────────────────────
def sem(x):
    if x >= 8:
        return "🟢 Alto"
    elif x >= 6.5:
        return "🟡 Medio"
    else:
        return "🔴 Crítico"

df["Semaforo"] = df["Score"].apply(sem)

# ─────────────────────────────────────────
# KPIs EJECUTIVOS
# ─────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

global_score = df["Score"].mean()

rank = (
    df.groupby(concesion_col)["Score"]
    .mean()
    .sort_values()
)

col1.metric(
    "Score Global",
    round(global_score, 2)
)

col2.metric(
    "Mejor Concesión",
    rank.idxmax()
)

col3.metric(
    "Concesión en Riesgo",
    rank.idxmin()
)

col4.metric(
    "Total Respuestas",
    len(df)
)

st.divider()

# ─────────────────────────────────────────
# INSIGHT EJECUTIVO
# ─────────────────────────────────────────
st.subheader("🧠 Insight Ejecutivo")

best_dim = df[q_cols].mean().idxmax()
worst_dim = df[q_cols].mean().idxmin()

st.info(f"""
• Fortaleza principal: {best_dim}  
• Área crítica: {worst_dim}  
• Concesión con mayor riesgo: {rank.idxmin()}  
• Concesión mejor evaluada: {rank.idxmax()}
""")

st.divider()

# ─────────────────────────────────────────
# RANKING CONCESIONES
# ─────────────────────────────────────────
st.subheader("🏢 Ranking de Concesiones")

rank_df = (
    df.groupby(concesion_col)["Score"]
    .mean()
    .reset_index()
    .sort_values("Score", ascending=False)
)

fig = px.bar(
    rank_df,
    x=concesion_col,
    y="Score",
    color="Score",
    text_auto=".2f",
    color_continuous_scale="RdYlGn"
)

fig.update_layout(
    xaxis_title="",
    yaxis_title="Score",
    height=500
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ─────────────────────────────────────────
# PERFORMANCE POR PREGUNTA
# ─────────────────────────────────────────
st.subheader("📊 Desempeño por Dimensión / Pregunta")

q_df = (
    df[q_cols]
    .mean()
    .reset_index()
)

q_df.columns = ["Pregunta", "Score"]

q_df = q_df.sort_values("Score")

fig2 = px.bar(
    q_df,
    x="Score",
    y="Pregunta",
    orientation="h",
    color="Score",
    text_auto=".2f",
    color_continuous_scale="RdYlGn"
)

fig2.update_layout(
    height=700,
    xaxis_title="Score",
    yaxis_title=""
)

st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────
# TABLA DETALLADA
# ─────────────────────────────────────────
with st.expander("📋 Ver datos completos"):
    st.dataframe(df, use_container_width=True)
