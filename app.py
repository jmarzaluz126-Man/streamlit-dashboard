import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Concesiones", layout="wide")

st.title("📊 Dashboard Ejecutivo - Encuesta Concesiones")

# ─────────────────────────────────────────────
# 1. CARGA DE ARCHIVO
# ─────────────────────────────────────────────
uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    st.subheader("Vista previa de datos")
    st.dataframe(df.head())

    # ─────────────────────────────────────────────
    # 2. LIMPIEZA BÁSICA (ajustable a tu Excel)
    # ─────────────────────────────────────────────
    df = df.dropna(how="all")

    # Detectar columnas clave de forma flexible
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if len(numeric_cols) == 0:
        st.error("No se detectaron columnas numéricas para análisis.")
        st.stop()

    # Score promedio general
    df["Score_Promedio"] = df[numeric_cols].mean(axis=1)

    # ─────────────────────────────────────────────
    # 3. KPIs PRINCIPALES
    # ─────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    col1.metric("Score Promedio Global", round(df["Score_Promedio"].mean(), 2))
    col2.metric("Máximo Score", round(df["Score_Promedio"].max(), 2))
    col3.metric("Mínimo Score", round(df["Score_Promedio"].min(), 2))

    st.divider()

    # ─────────────────────────────────────────────
    # 4. FILTRO SIMPLE
    # ─────────────────────────────────────────────
    if "Concesion" in df.columns:
        concesiones = df["Concesion"].dropna().unique()
        filtro = st.multiselect("Filtrar concesiones", concesiones, default=concesiones)
        df = df[df["Concesion"].isin(filtro)]

    # ─────────────────────────────────────────────
    # 5. GRÁFICO 1: DISTRIBUCIÓN
    # ─────────────────────────────────────────────
    st.subheader("📈 Distribución de Scores")

    fig1 = px.histogram(df, x="Score_Promedio", nbins=20)
    st.plotly_chart(fig1, use_container_width=True)

    # ─────────────────────────────────────────────
    # 6. GRÁFICO 2: POR CONCESIÓN
    # ─────────────────────────────────────────────
    if "Concesion" in df.columns:
        st.subheader("🏢 Score por Concesión")

        df_group = df.groupby("Concesion")["Score_Promedio"].mean().reset_index()

        fig2 = px.bar(
            df_group,
            x="Concesion",
            y="Score_Promedio",
            color="Score_Promedio",
            text_auto=True
        )

        st.plotly_chart(fig2, use_container_width=True)

    # ─────────────────────────────────────────────
    # 7. TABLA FINAL
    # ─────────────────────────────────────────────
    st.subheader("📋 Datos procesados")

    st.dataframe(df)

else:
    st.info("Sube un archivo Excel para comenzar el análisis.")
