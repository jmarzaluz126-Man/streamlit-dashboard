import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="TLV Decision Dashboard v3", layout="wide")

st.title("📊 TLV | Decision Dashboard v3")

uploaded_file = st.file_uploader("Sube Excel TLV", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\xa0", " ")

    # ─────────────────────────────────────────
    # DETECCIÓN DE CONCESIÓN
    # ─────────────────────────────────────────
    concesion_col = [c for c in df.columns if "conces" in c.lower()]
    if not concesion_col:
        st.error("No se encontró columna de concesión")
        st.stop()

    concesion_col = concesion_col[0]

    # ─────────────────────────────────────────
    # VARIABLES NUMÉRICAS
    # ─────────────────────────────────────────
    q_cols = [c for c in df.columns if c != concesion_col and pd.api.types.is_numeric_dtype(df[c])]

    if len(q_cols) < 3:
        st.error("Dataset insuficiente")
        st.stop()

    # ─────────────────────────────────────────
    # SCORE BASE
    # ─────────────────────────────────────────
    df["score"] = df[q_cols].mean(axis=1)

    conc = df.groupby(concesion_col)["score"].mean().sort_values(ascending=False)

    global_score = df["score"].mean()
    best = conc.idxmax()
    worst = conc.idxmin()

    spread = conc.max() - conc.min()

    # ─────────────────────────────────────────
    # CAPA 1: ESTADO DEL SISTEMA (REDUCIDO)
    # ─────────────────────────────────────────
    st.subheader("🧭 Estado del Sistema")

    c1, c2, c3 = st.columns(3)

    c1.metric("Score Global", round(global_score, 2))
    c2.metric("Mejor Concesión", best)
    c3.metric("Concesión Crítica", worst)

    # DECISIÓN AUTOMÁTICA
    if global_score >= 8:
        status = "🟢 Sistema estable"
    elif global_score >= 6.5:
        status = "🟡 Sistema en riesgo"
    else:
        status = "🔴 Sistema crítico"

    st.success(status)

    st.divider()

    # ─────────────────────────────────────────
    # CAPA 2: PROBLEMA REAL (AQUÍ ESTÁ EL NIVEL 3)
    # ─────────────────────────────────────────
    st.subheader("⚠ Diagnóstico Ejecutivo (NO descriptivo)")

    worst_score = conc.min()
    worst_gap = conc.max() - conc.min()

    # detectar dimensión problemática
    worst_col = df[q_cols].mean().idxmin()
    best_col = df[q_cols].mean().idxmax()

    st.error(f"""
    PROBLEMA CENTRAL DETECTADO:

    • Concesión que deteriora el sistema: {worst}
    • Dimensión crítica del sistema: {worst_col}
    • Brecha operativa entre concesiones: {round(worst_gap,2)}

    INTERPRETACIÓN:
    El problema no es general, es localizado y estructural.
    """)

    st.divider()

    # ─────────────────────────────────────────
    # CAPA 3: ACCIÓN (OBLIGATORIA, NO OPCIONAL)
    # ─────────────────────────────────────────
    st.subheader("🎯 Acciones obligatorias")

    actions = []

    if worst_score < 6.5:
        actions.append(f"🔴 Intervenir inmediatamente la concesión {worst}")

    if worst_gap > 2:
        actions.append("🟡 Estandarizar operación entre concesiones (alta variabilidad)")

    if df["score"].mean() < 7.5:
        actions.append("🟡 Revisar modelo de servicio integral TLV")

    actions.append(f"🟢 Replicar prácticas de {best} como benchmark interno")

    for a in actions:
        st.write(a)

    st.divider()

    # ─────────────────────────────────────────
    # CAPA 4: SOLO 1 GRÁFICO (NO MÁS RUIDO)
    # ─────────────────────────────────────────
    st.subheader("🏢 Ranking de Concesiones (único gráfico)")

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
    # DETALLE SOLO SI LO PIDEN
    # ─────────────────────────────────────────
    with st.expander("Ver datos crudos"):
        st.dataframe(df)

else:
    st.info("Carga tu archivo Excel para iniciar")
