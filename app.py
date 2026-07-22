import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard Telepeaje - Satisfacción",
    layout="wide",
    page_icon="🛣️"
)

# ============================================================
# CARGA DE DATOS (CACHE) - VERSIÓN POR ÍNDICES
# ============================================================
@st.cache_data
def load_data():
    # ---------- LECTURA DE HOJAS ----------
    # Q1: cabecera en fila 1 (índice 1), datos desde fila 2 (índice 2)
    df_q1 = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q1',
        header=1  # Toma la fila 1 como cabecera
    )
    # Q2: cabecera en fila 0, datos desde fila 1
    df_q2 = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q2',
        header=0
    )

    # ---------- LIMPIEZA DE NOMBRES (solo para referencia, no los usaremos para seleccionar) ----------
    df_q1.columns = df_q1.columns.str.strip()
    df_q2.columns = df_q2.columns.str.strip()

    # ---------- ELIMINAR FILAS DE SUBTOTAL Y VACÍAS ----------
    # Q1: usar primera columna (índice 0) como identificador
    df_q1 = df_q1.dropna(subset=[df_q1.columns[0]])
    df_q1 = df_q1[~df_q1.iloc[:, 0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q1 = df_q1[df_q1.iloc[:, 0].astype(str).str.strip() != '']

    # Q2: usar primera columna (índice 0)
    df_q2 = df_q2.dropna(subset=[df_q2.columns[0]])
    df_q2 = df_q2[~df_q2.iloc[:, 0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q2 = df_q2[df_q2.iloc[:, 0].astype(str).str.strip() != '']

    # ---------- EXTRAER COLUMNAS POR POSICIÓN ----------
    # Definir nombres cortos para las 15 preguntas
    preguntas_cortas = [
        'P1_Eficiencia_Operativa',
        'P2_Tiempos_Respuesta',
        'P3_Precision_Conciliaciones',
        'P4_Facilidad_Procesos',
        'P5_Gestion_Incobrables',
        'P6_Monitoreo_24_7',
        'P7_Comunicacion_Eventos',
        'P8_Dispersion_Pagos',
        'P9_Transparencia_Reportes',
        'P10_Acompanamiento_Comercial',
        'P11_Informacion_Estrategica',
        'P12_Reuniones_Mensuales',
        'P13_Reporte_BI',
        'P14_Comunicacion_Proactiva',
        'P15_Satisfaccion_Integral'
    ]

    # ---------- Q1: columnas fijas (0-6) y preguntas (7-21) ----------
    # Seleccionar las columnas por índices
    q1_fijas = df_q1.iloc[:, 0:7]  # Columnas 0 a 6 (ID, Hora de inicio, ...)
    q1_preguntas = df_q1.iloc[:, 7:22]  # Columnas 7 a 21 (15 preguntas)
    # Renombrar las preguntas
    q1_preguntas.columns = preguntas_cortas

    # ---------- Q2: columnas fijas (0-2) y preguntas (3-17) ----------
    q2_fijas = df_q2.iloc[:, 0:3]  # Columnas 0 a 2 (Nombre, Concesión, Área)
    q2_preguntas = df_q2.iloc[:, 3:18]  # Columnas 3 a 17 (15 preguntas)
    q2_preguntas.columns = preguntas_cortas

    # ---------- EXTRAER NPS DE Q2 (columna 18) ----------
    # La columna 18 es "¿Qué probabilidades hay de que recomiende usar TeleVía?"
    if df_q2.shape[1] > 18:
        nps_series = df_q2.iloc[:, 18]
        # Intentar convertir a numérico
        nps_series = pd.to_numeric(nps_series, errors='coerce')
    else:
        nps_series = pd.Series([np.nan] * len(df_q2))

    # ---------- CONSTRUIR DATAFRAMES LIMPIOS ----------
    # Q1: unir fijas + preguntas
    df_q1_clean = pd.concat([q1_fijas.reset_index(drop=True), q1_preguntas.reset_index(drop=True)], axis=1)
    # Q2: unir fijas + preguntas + NPS
    df_q2_clean = pd.concat([
        q2_fijas.reset_index(drop=True),
        q2_preguntas.reset_index(drop=True),
        pd.DataFrame({'NPS': nps_series.values})
    ], axis=1)

    # ---------- AÑADIR COLUMNA DE TRIMESTRE ----------
    df_q1_clean['CU'] = 'Q1'
    df_q2_clean['CU'] = 'Q2'

    # ---------- ESTANDARIZAR NOMBRES DE COLUMNAS FIJAS ----------
    # Para Q1, renombrar las primeras 7 columnas
    q1_fijas_nombres = ['ID', 'Hora de inicio', 'Hora de finalización', 
                        'Correo electrónico', 'Nombre', 'Nombre de la Concesión', 
                        'Área / Cargo']
    df_q1_clean.columns = q1_fijas_nombres + preguntas_cortas + ['CU']

    # Para Q2, las primeras 3 columnas
    q2_fijas_nombres = ['Nombre', 'Nombre de la Concesión', 'Área / Cargo']
    # Pero Q2 también tiene NPS, así que el orden de columnas será: fijas + preguntas + NPS + CU
    df_q2_clean.columns = q2_fijas_nombres + preguntas_cortas + ['NPS', 'CU']

    # ---------- UNIFICAR AMBOS DATAFRAMES ----------
    # Asegurar que Q2 tenga las mismas columnas que Q1 (agregar ID, Hora, etc. con NaN)
    for col in ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico']:
        df_q2_clean[col] = np.nan

    # Reordenar columnas para que coincidan
    orden_columnas = ['ID', 'Hora de inicio', 'Hora de finalización', 
                      'Correo electrónico', 'Nombre', 'Nombre de la Concesión', 
                      'Área / Cargo'] + preguntas_cortas + ['NPS', 'CU']
    df_q1_clean = df_q1_clean[orden_columnas]
    df_q2_clean = df_q2_clean[orden_columnas]

    # Concatenar
    df = pd.concat([df_q1_clean, df_q2_clean], ignore_index=True)

    # ---------- CONVERTIR PREGUNTAS A NUMÉRICO ----------
    for p in preguntas_cortas:
        df[p] = pd.to_numeric(df[p], errors='coerce')
    df['NPS'] = pd.to_numeric(df['NPS'], errors='coerce')

    # ---------- CALCULAR TOTAL PROMEDIO GENERAL ----------
    df['Total_Promedio'] = df[preguntas_cortas].mean(axis=1)

    # ---------- DETECTAR COLUMNAS DE TEXTO (comentarios) ----------
    # Volver a leer las hojas para obtener las columnas de texto, ya que las descartamos
    # Vamos a leer Q1 y Q2 completas sin cabecera para extraer las columnas de texto por posición
    df_q1_text = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q1',
        header=None,  # Sin cabecera
        skiprows=2    # Saltar las dos primeras filas (vacía y cabecera)
    )
    df_q2_text = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q2',
        header=None,
        skiprows=1    # Saltar la cabecera
    )

    # Eliminar filas de subtotal en las versiones de texto
    # Usamos la primera columna para identificar
    df_q1_text = df_q1_text[~df_q1_text.iloc[:, 0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q1_text = df_q1_text[df_q1_text.iloc[:, 0].astype(str).str.strip() != '']
    df_q2_text = df_q2_text[~df_q2_text.iloc[:, 0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q2_text = df_q2_text[df_q2_text.iloc[:, 0].astype(str).str.strip() != '']

    # Q1: las columnas de texto son las índices 23, 24, 25 (W, X, Y) en el Excel original (0-indexado)
    # Pero con skiprows=2, las columnas siguen siendo las mismas posiciones
    if df_q1_text.shape[1] > 23:
        df_q1_text_cols = df_q1_text.iloc[:, 23:26]  # columnas 23,24,25
        # Renombrarlas
        df_q1_text_cols.columns = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']
    else:
        df_q1_text_cols = pd.DataFrame()

    # Q2: las columnas de texto son las índices 20, 21, 22 (U, V, W)
    if df_q2_text.shape[1] > 20:
        df_q2_text_cols = df_q2_text.iloc[:, 20:23]
        df_q2_text_cols.columns = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']
    else:
        df_q2_text_cols = pd.DataFrame()

    # Combinar los textos con el DataFrame principal usando el nombre (columna 4 en Q1, columna 0 en Q2)
    # Para Q1, el nombre está en la columna 4 (índice 4)
    if not df_q1_text_cols.empty:
        df_q1_text_cols['Nombre'] = df_q1_text.iloc[:, 4].values
    # Para Q2, el nombre está en la columna 0
    if not df_q2_text_cols.empty:
        df_q2_text_cols['Nombre'] = df_q2_text.iloc[:, 0].values

    # Unir todos los textos en un solo DataFrame
    textos_combined = pd.concat([df_q1_text_cols, df_q2_text_cols], ignore_index=True)

    # Hacer merge con el df principal usando 'Nombre'
    if not textos_combined.empty:
        # Conservar solo las columnas de texto y Nombre
        textos_combined = textos_combined[['Nombre', 'Aciertos', 'Áreas_mejora', 'Comentarios_contacto']]
        df = df.merge(textos_combined, on='Nombre', how='left')
    else:
        for col in ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']:
            df[col] = np.nan

    return df, preguntas_cortas


df, preguntas = load_data()

# ============================================================
# SIDEBAR - FILTROS Y CONFIGURACIONES
# ============================================================
st.sidebar.image("https://www.aleatica.com/wp-content/uploads/2024/01/logo-aleatica.png", width=200)
st.sidebar.title("🔍 Filtros")

modo_oscuro = st.sidebar.toggle("🌙 Activar Modo Oscuro", value=False)
template = 'plotly_dark' if modo_oscuro else 'plotly_white'

umbral_alerta = st.sidebar.slider("🚨 Umbral de alerta (%)", 1, 20, 5,
                                 help="Si la satisfacción baja más de este % entre Q1 y Q2, se mostrará una alerta.")

cu_selected = st.sidebar.multiselect(
    "Selecciona trimestre",
    options=sorted(df['CU'].unique()),
    default=sorted(df['CU'].unique())
)

concesiones = st.sidebar.multiselect(
    "Filtrar por concesión",
    options=sorted(df['Nombre de la Concesión'].dropna().unique()),
    default=sorted(df['Nombre de la Concesión'].dropna().unique())
)

df_filtrado = df[df['CU'].isin(cu_selected)]
df_filtrado = df_filtrado[df_filtrado['Nombre de la Concesión'].isin(concesiones)]

# ============================================================
# CSS PARA MODO OSCURO
# ============================================================
if modo_oscuro:
    st.markdown("""
        <style>
        .stApp { background-color: #1e1e1e; color: white; }
        .stMetric { background-color: #2d2d2d; padding: 10px; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

# ============================================================
# FUNCIONES DE CÁLCULO
# ============================================================
def calc_nps(group):
    if group['NPS'].count() == 0:
        return np.nan
    promotores = (group['NPS'] >= 9).sum()
    detractores = (group['NPS'] <= 6).sum()
    total = group['NPS'].count()
    return round(((promotores - detractores) / total) * 100, 1)

# ============================================================
# 🚨 ALERTAS POR BAJADA DE MÉTRICAS
# ============================================================
if 'Q1' in cu_selected and 'Q2' in cu_selected:
    prom_q1 = df_filtrado[df_filtrado['CU']=='Q1']['Total_Promedio'].mean()
    prom_q2 = df_filtrado[df_filtrado['CU']=='Q2']['Total_Promedio'].mean()
    if prom_q1 > 0:
        drop = ((prom_q2 - prom_q1) / prom_q1) * 100
        if drop < -umbral_alerta:
            st.error(f"🚨 ALERTA: La satisfacción global cayó un {abs(drop):.1f}% entre Q1 y Q2.")
        elif drop < 0:
            st.warning(f"⚠️ Atención: La satisfacción global bajó un {abs(drop):.1f}% entre Q1 y Q2.")
        else:
            st.success(f"✅ La satisfacción global mejoró un {drop:.1f}% entre Q1 y Q2.")

# ============================================================
# ENCABEZADO
# ============================================================
st.title("📊 Encuesta de Satisfacción - Telepeaje")
st.markdown(f"**Registros analizados:** {len(df_filtrado):,} | **Trimestres:** {', '.join(cu_selected)}")
st.divider()

# ============================================================
# 1. RESUMEN EJECUTIVO (KPIs)
# ============================================================
st.header("📈 Resumen Ejecutivo")

col1, col2, col3, col4 = st.columns(4)

with col1:
    prom_q1 = df_filtrado[df_filtrado['CU']=='Q1']['Total_Promedio'].mean()
    prom_q2 = df_filtrado[df_filtrado['CU']=='Q2']['Total_Promedio'].mean()
    delta = prom_q2 - prom_q1
    st.metric("⭐ Satisfacción Global (promedio)",
              f"{prom_q2:.2f}" if 'Q2' in cu_selected else f"{prom_q1:.2f}",
              delta=f"{delta:+.2f}" if len(cu_selected)>1 else None)

with col2:
    if 'Q2' in cu_selected:
        nps_val = calc_nps(df_filtrado[df_filtrado['CU']=='Q2'])
        st.metric("📊 NPS (Q2)", f"{nps_val:.1f}")
    else:
        st.metric("📊 NPS", "Selecciona Q2")

with col3:
    total_encuestas = len(df_filtrado)
    st.metric("📋 Total Encuestas", f"{total_encuestas:,}")

with col4:
    if 'Q1' in cu_selected and 'Q2' in cu_selected:
        brechas = []
        for p in preguntas:
            m1 = df_filtrado[df_filtrado['CU']=='Q1'][p].mean()
            m2 = df_filtrado[df_filtrado['CU']=='Q2'][p].mean()
            brechas.append(m2 - m1)
        brecha_prom = np.mean(brechas)
        st.metric("📉 Brecha Promedio (Q2 - Q1)", f"{brecha_prom:+.2f}")
    else:
        st.metric("📉 Brecha Promedio", "Selecciona ambos trimestres")

st.divider()

# ============================================================
# CONFIGURACIÓN DE GRÁFICOS (para exportar PNG)
# ============================================================
plot_config = {
    'displayModeBar': True,
    'displaylogo': False,
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'dashboard_plot',
        'scale': 2
    }
}

# ============================================================
# GRÁFICO 1: Comparativa de Preguntas (Barras agrupadas)
# ============================================================
st.subheader("🔹 Comparativa por dimensión")

etiquetas = {
    'P1_Eficiencia_Operativa': 'Eficiencia operativa',
    'P2_Tiempos_Respuesta': 'Tiempos de respuesta',
    'P3_Precision_Conciliaciones': 'Precisión conciliaciones',
    'P4_Facilidad_Procesos': 'Facilidad procesos',
    'P5_Gestion_Incobrables': 'Gestión incobrables',
    'P6_Monitoreo_24_7': 'Monitoreo 24/7',
    'P7_Comunicacion_Eventos': 'Comunicación eventos',
    'P8_Dispersion_Pagos': 'Dispersión de pagos',
    'P9_Transparencia_Reportes': 'Transparencia reportes',
    'P10_Acompanamiento_Comercial': 'Acompañamiento comercial',
    'P11_Informacion_Estrategica': 'Información estratégica',
    'P12_Reuniones_Mensuales': 'Reuniones mensuales',
    'P13_Reporte_BI': 'Reporte BI',
    'P14_Comunicacion_Proactiva': 'Comunicación proactiva',
    'P15_Satisfaccion_Integral': 'Satisfacción integral'
}

if len(cu_selected) > 1:
    df_means = df_filtrado.groupby('CU')[preguntas].mean().reset_index()
    df_means_melt = df_means.melt(id_vars='CU', var_name='Pregunta', value_name='Promedio')
    df_means_melt['Pregunta'] = df_means_melt['Pregunta'].map(etiquetas)
    
    fig = px.bar(df_means_melt,
                 x='Pregunta',
                 y='Promedio',
                 color='CU',
                 barmode='group',
                 color_discrete_map={'Q1': '#1f77b4', 'Q2': '#ff7f0e'},
                 text_auto='.2f',
                 title='Promedio por dimensión - Q1 vs Q2',
                 template=template)
    fig.update_layout(yaxis_range=[0, 5.5], height=500, legend_title='Trimestre')
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True, config=plot_config)
else:
    df_means = df_filtrado[preguntas].mean().reset_index()
    df_means.columns = ['Pregunta', 'Promedio']
    df_means['Pregunta'] = df_means['Pregunta'].map(etiquetas)
    fig = px.bar(df_means,
                 x='Pregunta',
                 y='Promedio',
                 color='Pregunta',
                 text_auto='.2f',
                 title=f'Promedio por dimensión - {cu_selected[0]}',
                 template=template)
    fig.update_layout(yaxis_range=[0, 5.5], height=500, showlegend=False)
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True, config=plot_config)

# ============================================================
# GRÁFICO 2: Radar Chart (solo si hay ambas CUs)
# ============================================================
if len(cu_selected) > 1:
    st.subheader("🔸 Radar Comparativo")
    fig_radar = go.Figure()
    for cu in ['Q1', 'Q2']:
        valores = df_filtrado[df_filtrado['CU']==cu][preguntas].mean().values.tolist()
        valores.append(valores[0])
        etiquetas_radar = list(etiquetas.values()) + [list(etiquetas.values())[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=valores,
            theta=etiquetas_radar,
            name=cu,
            fill='toself',
            line_color='#1f77b4' if cu=='Q1' else '#ff7f0e'
        ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5.5])),
        height=600,
        showlegend=True,
        template=template
    )
    st.plotly_chart(fig_radar, use_container_width=True, config=plot_config)

st.divider()

# ============================================================
# 2. ANÁLISIS DE NPS (solo Q2)
# ============================================================
if 'Q2' in cu_selected:
    st.header("⭐ NPS - Q2")
    df_q2_filtrado = df_filtrado[df_filtrado['CU']=='Q2']
    
    col1, col2 = st.columns(2)
    
    with col1:
        df_nps_dist = df_q2_filtrado['NPS'].value_counts().reset_index()
        df_nps_dist.columns = ['Puntuación', 'Conteo']
        df_nps_dist = df_nps_dist.sort_values('Puntuación')
        fig_nps = px.bar(df_nps_dist,
                         x='Puntuación',
                         y='Conteo',
                         text_auto=True,
                         title='Distribución de la probabilidad de recomendación',
                         template=template)
        fig_nps.update_layout(xaxis=dict(tickmode='linear', dtick=1), height=400)
        st.plotly_chart(fig_nps, use_container_width=True, config=plot_config)
    
    with col2:
        nps_val = calc_nps(df_q2_filtrado)
        promotores = (df_q2_filtrado['NPS'] >= 9).sum()
        pasivos = (df_q2_filtrado['NPS'].between(7, 8)).sum()
        detractores = (df_q2_filtrado['NPS'] <= 6).sum()
        total = df_q2_filtrado['NPS'].count()
        
        st.metric("📊 NPS General", f"{nps_val:.1f}")
        st.write(f"**Promotores (9-10):** {promotores} ({promotores/total*100:.1f}%)")
        st.write(f"**Pasivos (7-8):** {pasivos} ({pasivos/total*100:.1f}%)")
        st.write(f"**Detractores (0-6):** {detractores} ({detractores/total*100:.1f}%)")
        st.write(f"**Total respuestas:** {total}")

st.divider()

# ============================================================
# 3. PERFIL DEL ENCUESTADO
# ============================================================
st.header("👤 Perfil del Encuestado")

col1, col2, col3 = st.columns(3)

with col1:
    df_concesion = df_filtrado['Nombre de la Concesión'].value_counts().reset_index()
    df_concesion.columns = ['Concesión', 'Conteo']
    fig_conc = px.bar(df_concesion,
                      x='Concesión',
                      y='Conteo',
                      text_auto=True,
                      title='Respuestas por Concesión',
                      template=template)
    fig_conc.update_layout(height=400)
    st.plotly_chart(fig_conc, use_container_width=True, config=plot_config)

with col2:
    df_area = df_filtrado['Área / Cargo'].value_counts().reset_index()
    df_area.columns = ['Área/Cargo', 'Conteo']
    fig_area = px.bar(df_area,
                      x='Área/Cargo',
                      y='Conteo',
                      text_auto=True,
                      title='Respuestas por Área/Cargo',
                      template=template)
    fig_area.update_layout(height=400)
    st.plotly_chart(fig_area, use_container_width=True, config=plot_config)

with col3:
    if 'Q1' in cu_selected and 'Q2' in cu_selected:
        df_conc_prom = df_filtrado.groupby(['CU', 'Nombre de la Concesión'])['Total_Promedio'].mean().reset_index()
        fig_conc_prom = px.bar(df_conc_prom,
                               x='Nombre de la Concesión',
                               y='Total_Promedio',
                               color='CU',
                               barmode='group',
                               color_discrete_map={'Q1': '#1f77b4', 'Q2': '#ff7f0e'},
                               title='Satisfacción promedio por concesión',
                               template=template)
        fig_conc_prom.update_layout(height=400, yaxis_range=[0, 5.5])
        st.plotly_chart(fig_conc_prom, use_container_width=True, config=plot_config)
    else:
        st.info("Selecciona ambos trimestres para ver la comparativa por concesión.")

st.divider()

# ============================================================
# 4. 💬 ANÁLISIS DE TEXTO LIBRE
# ============================================================
text_cols = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']
text_cols_existentes = [col for col in text_cols if col in df_filtrado.columns]

if text_cols_existentes:
    st.header("💬 Análisis de Comentarios")
    
    col_texto = st.selectbox("Selecciona el tipo de comentario", text_cols_existentes)
    
    textos = df_filtrado[col_texto].dropna().astype(str)
    textos = textos[textos.str.strip() != '']
    
    if len(textos) > 0:
        col_t1, col_t2 = st.columns([1, 1])
        
        with col_t1:
            st.subheader("🔎 Buscador de comentarios")
            busqueda = st.text_input("Escribe una palabra clave")
            if busqueda:
                resultados = textos[textos.str.contains(busqueda, case=False, na=False)]
                st.dataframe(pd.DataFrame(resultados, columns=[col_texto]), use_container_width=True)
            else:
                st.dataframe(pd.DataFrame(textos.head(100), columns=[col_texto]), use_container_width=True)
                st.caption(f"Mostrando 100 de {len(textos)} comentarios. Usa el buscador para filtrar.")
        
        with col_t2:
            st.subheader("📊 Palabras más frecuentes")
            stopwords = set(['que', 'de', 'la', 'el', 'en', 'y', 'a', 'los', 'del', 'las', 'un', 'por', 'con', 'no',
                             'su', 'para', 'es', 'lo', 'como', 'mas', 'pero', 'sus', 'le', 'ya', 'este', 'entre', 'si',
                             'porque', 'esta', 'son', 'uno', 'todo', 'tambien', 'otro', 'asi', 'mis', 'te', 'se', 'me',
                             'mi', 'tu', 'yo', 'nos', 'ellos', 'ellas', 'nosotros', 'vosotros', 'les', 'os', 'algo',
                             'nada', 'muy', 'poco', 'mucho', 'tan', 'cada', 'solo', 'hasta', 'desde', 'durante',
                             'mediante', 'contra', 'sobre', 'entre', 'sin', 'ni', 'o', 'u', 'cual', 'cuales', 'quien',
                             'quienes', 'cuyo', 'cuya', 'cuyos', 'cuyas', 'que', 'ya', 'ha', 'he', 'lo', 'le', 'les',
                             'me', 'nos', 'os', 'te', 'se', 'sí', 'mí', 'ti'])
            
            all_words = " ".join(textos).lower()
            all_words = re.sub(r'[^\w\s]', ' ', all_words)
            all_words = re.sub(r'\d+', ' ', all_words)
            words = all_words.split()
            words = [w for w in words if len(w) > 2 and w not in stopwords]
            
            if len(words) > 0:
                counter = Counter(words).most_common(20)
                df_words = pd.DataFrame(counter, columns=['Palabra', 'Frecuencia'])
                fig_words = px.bar(df_words,
                                   x='Frecuencia',
                                   y='Palabra',
                                   orientation='h',
                                   title='Top 20 palabras',
                                   template=template,
                                   color='Frecuencia',
                                   color_continuous_scale='Blues')
                fig_words.update_layout(height=500, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_words, use_container_width=True, config=plot_config)
            else:
                st.info("No se encontraron palabras significativas.")
    else:
        st.info("No hay comentarios en esta categoría para los datos seleccionados.")
else:
    st.info("💬 No se detectaron columnas de comentarios.")

st.divider()

# ============================================================
# 5. TABLA DE DATOS CRUDOS
# ============================================================
st.header("📋 Datos crudos")
st.dataframe(df_filtrado, use_container_width=True)

# ============================================================
# 6. DESCARGA DE DATOS FILTRADOS
# ============================================================
csv = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar datos filtrados (CSV)",
    data=csv,
    file_name='datos_filtrados.csv',
    mime='text/csv',
)

st.caption("Dashboard desarrollado con Streamlit | Datos de encuesta de satisfacción - Telepeaje")
