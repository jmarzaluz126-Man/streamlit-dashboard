import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Dashboard TeleVía", layout="wide")

# =========================
# LOAD DATA
# =========================
df = pd.read_excel("Encuestas concesiones TLV.xlsx")

# =========================
# CLEAN TEXT FUNCTION
# =========================
def clean_text(x):
    if pd.isna(x):
        return None
    x = str(x).strip().lower()
    if x in ["", ".", "ok", "sin comentarios", "ninguno", "no puedo opinar"]:
        return None
    if len(x) < 10:
        return None
    return x

# =========================
# COMMENT COLUMNS (AJUSTA SI CAMBIAN NOMBRES)
# =========================
col_pos = "¿Qué aspectos considera que TeleVía realiza correctamente y debe mantener?"
col_neg = "¿Qué aspectos considera que TeleVía realiza incorrectamente y debe corregir, (Que no este mencionado arriba)?"
col_extra = "Comentarios adicionales / contacto para seguimiento (nombre y correo si desea respuesta personalizada):"

df["pos_clean"] = df[col_pos].apply(clean_text)
df["neg_clean"] = df[col_neg].apply(clean_text)

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs([
    "📊 Ejecutivo",
    "📈 KPIs",
    "💬 Voz del Cliente"
])

# =========================
# TAB 3 - VOZ DEL CLIENTE (VERSIÓN B BIEN HECHA)
# =========================
with tab3:

    st.title("💬 Voz del Cliente")

    # -------------------------
    # FRECUENCIAS
    # -------------------------
    def get_top(series, n=5):
        texts = series.dropna().tolist()
        words = []
        for t in texts:
            words += t.split()
        return Counter(words).most_common(n)

    st.subheader("🟢 Fortalezas más mencionadas")
    pos_texts = df["pos_clean"].dropna()
    pos_top = Counter(" ".join(pos_texts).split()).most_common(8)
    for word, freq in pos_top:
        st.write(f"- {word} ({freq})")

    st.divider()

    st.subheader("🔴 Problemas más mencionados")
    neg_texts = df["neg_clean"].dropna()
    neg_top = Counter(" ".join(neg_texts).split()).most_common(8)
    for word, freq in neg_top:
        st.write(f"- {word} ({freq})")

    st.divider()

    # -------------------------
    # EXAMPLES FILTERED (LO QUE PEDISTE)
    # -------------------------
    st.subheader("🟡 Evidencia real (comentarios filtrados)")

    st.markdown("### 🔴 Problemas relevantes")
    for c in df["neg_clean"].dropna().head(6):
        st.write(f"• {c}")

    st.markdown("### 🟢 Fortalezas relevantes")
    for c in df["pos_clean"].dropna().head(6):
        st.write(f"• {c}")
