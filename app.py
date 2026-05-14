import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="TLV | Decision Dashboard", layout="wide")

st.title("📊 TLV | Decision Dashboard (Nivel Ejecutivo)")

uploaded_file = st.file_uploader("Sube Excel TLV", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\xa0", " ")

    # ─────────────────────────────────────────
    # DETECCIÓN ROBUSTA DE CONCESIÓN
    # ─────────────────────────────────────────
    concesion_col = [c for c in df.columns if "conces" in c.lower()]
    if not concesion_col:
        st.error("No se encontró columna de concesión")
        st.stop()

    concesion_col = concesion_col[0]

    # ─────────────────────────────────────────
    # PREGUNTAS NUMÉRICAS
    # ─────────────────────────────────────────
    q_cols = [
        c for c in df.columns
        if c != concesion_col and pd.api.types.is_numeric_dtype(df[c])
    ]

    if len(q_cols) < 3:
        st.error("No hay suficientes variables numéricas")
        st.stop()

    # ─────────────────────────────────────────
    # SCORES
    # ─────────────────────────────────────────
    df["Score_Global"] = df[q_cols].mean(axis=1)

    conc = df.groupby(concesion_col)["Score_Global"].mean().sort_values(ascending=False)

    global_score = df["Score_Global"].mean()
    best = conc.idxmax()
    worst = conc.idxmin()

    # ─────────────────────────────────────────
    # CAPA 1: ESTADO GENERAL
    # ─────────────────────────────────────────
    st.subheader("🧭 Estado del Sistema")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Score Global", round(global_score, 2))
    c2.metric("Mejor Concesión", best)
    c3.metric("Concesión Crítica", worst)
    c4.metric("Total Respuestas", len(df))

    st.divider()

    # ─────────────────────────────────────────
    # CAPA 2: DIAGNÓSTICO (NO DESCRIPTIVO, PROBLEMÁTICO)
    # ─────────────────────────────────────────
    st.subheader("⚠ Diagnóstico Ejecutivo")

    worst_score = conc.min()
    best_score = conc.max()
    spread = best_score - worst_score

    # lógica de riesgo (IMPORTANTE)
    if global_score >= 8:
        health = "🟢 Sistema estable"
    elif global_score >= 6.5:
        health = "🟡 Sistema en tensión"
    else:
        health = "🔴 Sistema crítico"

    st.info(f"""
    Estado general: {health}

    • Brecha entre concesiones: {round(spread,2)} puntos  
    • Riesgo principal: desigualdad operativa entre concesiones  
    • Concesión con peor desempeño: {worst} ({round(worst_score,2)})  
    • Concesión dominante: {best} ({round(best_score,2)})  
    """)

    st.divider()

    # ─────────────────────────────────────────
    # CAPA 3: ACCIONES (LO MÁS IMPORTANTE)
    # ─────────────────────────────────────────
    st.subheader("🎯 Acciones Recomendadas")

    actions = []

    if worst_score < 6.5:
        actions.append("🔴 Intervención inmediata en concesión crítica (operación + financiero)")

    if spread > 2:
        actions.append("🟡 Homologar procesos entre concesiones (alta variabilidad detectada)")

    if global_score < 7.5:
        actions.append("🟡 Revisión de estrategia de servicio integral")

    actions.append("🟢 Mantener prácticas de concesión líder como benchmark interno")

    for a in actions:
        st.write(a)

    st.divider()

    # ─────────────────────────────────────────
    # VISUAL 1: RANKING EJECUTIVO
    # ─────────────────────────────────────────
    st.subheader("🏢 Ranking de Concesiones")

    rank_df = conc.reset_index()
    rank_df.columns = ["Concesión", "Score"]

    fig = px.bar(
        rank_df,
        x="Concesión",
        y="Score",
        text_auto=True,
        color="Score",
        color_continuous_scale=["red", "yellow", "green"]
    )

    st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────────────────
    # VISUAL 2: DISTRIBUCIÓN DE RIESGO
    # ─────────────────────────────────────────
    st.subheader("📉 Distribución de Riesgo")

    df["Riesgo"] = pd.cut(
        df["Score_Global"],
        bins=[0, 6.5, 7.9, 10],
        labels=["Crítico", "Medio", "Alto"]
    )

    risk_df = df["Riesgo"].value_counts().reset_index()
    risk_df.columns = ["Nivel", "Cantidad"]

    fig2 = px.pie(risk_df, names="Nivel", values="Cantidad")
    st.plotly_chart(fig2, use_container_width=True)

    # ─────────────────────────────────────────
    # DETALLE SOLO BAJO DEMANDA
    # ─────────────────────────────────────────
    with st.expander("📊 Ver dataset completo"):
        st.dataframe(df)

else:
    st.warning("Sube tu archivo Excel TLV para generar el dashboard")
