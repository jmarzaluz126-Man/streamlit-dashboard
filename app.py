import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard TLV", layout="wide")

st.title("📊 Dashboard Ejecutivo TLV - Concesiones")

uploaded_file = st.file_uploader("Sube Excel TLV", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # ─────────────────────────────
    # VALIDACIÓN DE COLUMNAS
    # ─────────────────────────────
    required_cols = ["Concesion"]
    if "Concesion" not in df.columns:
        st.error("No existe columna 'Concesion'. Revisa tu Excel.")
        st.stop()

    # asumir preguntas = todas las columnas numéricas excepto metadata
    exclude = ["ID", "Concesion"]
    q_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]

    if len(q_cols) < 5:
        st.error("No se detectaron suficientes preguntas numéricas.")
        st.stop()

    # ─────────────────────────────
    # SCORE
    # ─────────────────────────────
    df["Score_Global"] = df[q_cols].mean(axis=1)

    def semaforo(x):
        if x >= 8: return "🟢"
        if x >= 6.5: return "🟡"
        return "🔴"

    df["Semaforo"] = df["Score_Global"].apply(semaforo)

    # ─────────────────────────────
    # KPIs
    # ─────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Score Global", round(df["Score_Global"].mean(), 2))
    col2.metric("Mejor Concesión", df.groupby("Concesion")["Score_Global"].mean().idxmax())
    col3.metric("Peor Concesión", df.groupby("Concesion")["Score_Global"].mean().idxmin())
    col4.metric("Total Respuestas", len(df))

    st.divider()

    # ─────────────────────────────
    # RANKING CONCESIONES
    # ─────────────────────────────
    st.subheader("🏢 Ranking de Concesiones")

    rank = df.groupby("Concesion")["Score_Global"].mean().reset_index()
    rank = rank.sort_values("Score_Global", ascending=False)

    fig = px.bar(
        rank,
        x="Concesion",
        y="Score_Global",
        text_auto=True,
        color="Score_Global"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────
    # HEATMAP SIMPLE
    # ─────────────────────────────
    st.subheader("🔥 Promedio por pregunta")

    q_mean = df[q_cols].mean().reset_index()
    q_mean.columns = ["Pregunta", "Score"]

    fig2 = px.bar(q_mean, x="Pregunta", y="Score", color="Score")
    st.plotly_chart(fig2, use_container_width=True)

    # ─────────────────────────────
    # TABLA
    # ─────────────────────────────
    st.subheader("📋 Datos")

    st.dataframe(df)

else:
    st.info("Sube tu archivo TLV para iniciar")
