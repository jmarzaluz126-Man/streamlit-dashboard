import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="TLV - Dashboard Ejecutivo", layout="wide")

st.title("📊 TLV | Dashboard Ejecutivo de Concesiones")

# ─────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────
uploaded_file = st.file_uploader("Sube archivo Excel TLV", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # limpiar columnas
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\xa0", " ")

    # detectar concesión
    concesion_col = [c for c in df.columns if "conces" in c.lower()]
    if len(concesion_col) == 0:
        st.error("No se encontró columna de concesión")
        st.write(df.columns)
        st.stop()

    concesion_col = concesion_col[0]

    # detectar preguntas numéricas
    exclude = [concesion_col]
    q_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]

    if len(q_cols) < 3:
        st.error("No se detectaron preguntas numéricas válidas")
        st.stop()

    # score global
    df["Score"] = df[q_cols].mean(axis=1)

    # semáforo
    def sem(x):
        if x >= 8: return "🟢 Alto"
        if x >= 6.5: return "🟡 Medio"
        return "🔴 Crítico"

    df["Semaforo"] = df["Score"].apply(sem)

    # ─────────────────────────────────────────
    # KPIs EJECUTIVOS (ARRIBA)
    # ─────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    global_score = df["Score"].mean()

    rank = df.groupby(concesion_col)["Score"].mean().sort_values()

    col1.metric("Score Global", round(global_score, 2))
    col2.metric("Mejor Concesión", rank.idxmax())
    col3.metric("Concesión en Riesgo", rank.idxmin())
    col4.metric("Total Respuestas", len(df))

    st.divider()

    # ─────────────────────────────────────────
    # INSIGHT EJECUTIVO (CLAVE)
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
    # RANKING CONCESIONES (VISUAL EJECUTIVO)
    # ─────────────────────────────────────────
    st.subheader("🏢 Ranking de Concesiones")

    rank_df = df.groupby(concesion_col)["Score"].mean().reset_index()
    rank_df = rank_df.sort_values("Score", ascending=False)

    fig = px.bar(
        rank_df,
        x=concesion_col,
        y="Score",
        color="Score",
        text_auto=True
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ─────────────────────────────────────────
    # PERFORMANCE POR PREGUNTA
    # ─────────────────────────────────────────
    st.subheader("📊 Desempeño por Dimensión / Pregunta")

    q_df = df[q_cols].mean().reset_index()
    q_df.columns = ["Pregunta", "Score"]
    q_df = q_df.sort_values("Score")

    fig2 = px.bar(
        q_df,
        x="Score",
        y="Pregunta",
        orientation="h",
        color="Score"
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ─────────────────────────────────────────
    # TABLA SOLO SI NECESARIA
    # ─────────────────────────────────────────
    with st.expander("📋 Ver datos completos"):
        st.dataframe(df)

else:
    st.info("Sube tu archivo Excel para iniciar el análisis TLV")
