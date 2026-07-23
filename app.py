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
# COLORES CORPORATIVOS
# ============================================================
COLOR_Q1 = '#E31B23'      # Rojo Aleática
COLOR_Q2 = '#1a2a6c'      # Azul profundo
COLOR_META = '#C8102E'    # Rojo Televía
COLOR_VERDE = '#28a745'   # Mejora
COLOR_AMARILLO = '#ffc107' # Alerta
COLOR_ROJO = '#dc3545'    # Crítico

# ============================================================
# CARGA DE DATOS
# ============================================================
@st.cache_data
def load_data():
    # ---------- LECTURA DE Q1 ----------
    df_q1 = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q1',
        header=None,
        skiprows=2
    )
    # Q2
    df_q2 = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q2',
        header=None,
        skiprows=1
    )

    # ---------- ELIMINAR FILAS DE SUBTOTAL Y VACÍAS ----------
    df_q1 = df_q1.dropna(subset=[0])
    df_q1 = df_q1[~df_q1[0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q1 = df_q1[df_q1[0].astype(str).str.strip() != '']

    df_q2 = df_q2.dropna(subset=[0])
    df_q2 = df_q2[~df_q2[0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q2 = df_q2[df_q2[0].astype(str).str.strip() != '']

    # ---------- DEFINIR NOMBRES DE COLUMNAS ----------
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
    
    q1_text_cols = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']

    # ---------- CONSTRUIR Q1 ----------
    q1_fijas = df_q1.iloc[:, 0:7].copy()
    q1_fijas.columns = ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico',
                        'Nombre', 'Nombre de la Concesión', 'Área / Cargo']
    q1_preg = df_q1.iloc[:, 7:22].copy()
    q1_preg.columns = preguntas_cortas
    q1_text = df_q1.iloc[:, 23:26].copy()
    q1_text.columns = q1_text_cols

    # ---------- CONSTRUIR Q2 ----------
    q2_fijas = df_q2.iloc[:, 0:3].copy()
    q2_fijas.columns = ['Nombre', 'Nombre de la Concesión', 'Área / Cargo']
    q2_preg = df_q2.iloc[:, 3:18].copy()
    q2_preg.columns = preguntas_cortas
    q2_nps = df_q2.iloc[:, 18].copy().rename('NPS')
    q2_text = df_q2.iloc[:, 20:23].copy()
    q2_text.columns = q1_text_cols

    # ---------- UNIR Q1 ----------
    df_q1_full = pd.concat([q1_fijas.reset_index(drop=True),
                            q1_preg.reset_index(drop=True),
                            q1_text.reset_index(drop=True)], axis=1)
    df_q1_full['CU'] = 'Q1'
    df_q1_full['NPS'] = np.nan

    # ---------- UNIR Q2 ----------
    df_q2_full = pd.concat([q2_fijas.reset_index(drop=True),
                            q2_preg.reset_index(drop=True),
                            q2_nps.reset_index(drop=True),
                            q2_text.reset_index(drop=True)], axis=1)
    df_q2_full['CU'] = 'Q2'

    # Asegurar que Q2 tenga las mismas columnas que Q1
    for col in ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico']:
        if col not in df_q2_full.columns:
            df_q2_full[col] = np.nan

    # Reordenar columnas
    orden_columnas = ['ID', 'Hora de inicio', 'Hora de finalización',
                      'Correo electrónico', 'Nombre', 'Nombre de la Concesión',
                      'Área / Cargo'] + preguntas_cortas + ['NPS'] + ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto'] + ['CU']
    df_q1_full = df_q1_full[orden_columnas]
    df_q2_full = df_q2_full[orden_columnas]

    # Concatenar
    df = pd.concat([df_q1_full, df_q2_full], ignore_index=True)

    # ---------- CONVERTIR NUMÉRICOS ----------
    for p in preguntas_cortas:
        df[p] = pd.to_numeric(df[p], errors='coerce')
    df['NPS'] = pd.to_numeric(df['NPS'], errors='coerce')

    # Calcular promedio general
    df['Total_Promedio'] = df[preguntas_cortas].mean(axis=1)

    # Limpiar nombres
    df['Nombre'] = df['Nombre'].astype(str).str.strip()
    df['Nombre de la Concesión'] = df['Nombre de la Concesión'].astype(str).str.strip()

    return df, preguntas_cortas

# Cargar datos
df, preguntas = load_data()

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.image("https://www.aleatica.com/wp-content/uploads/2024/01/logo-aleatica.png", width=200)
st.sidebar.title("🔍 Filtros")

modo_oscuro = st.sidebar.toggle("🌙 Modo Oscuro", value=False)
template = 'plotly_dark' if modo_oscuro else 'plotly_white'

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
# CSS
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
# FUNCIONES
# ============================================================
def calc_nps(group):
    if group['NPS'].count() == 0:
        return np.nan
    promotores = (group['NPS'] >= 9).sum()
    detractores = (group['NPS'] <= 6).sum()
    total = group['NPS'].count()
    return round(((promotores - detractores) / total) * 100, 1)

# ============================================================
# ENCABEZADO
# ============================================================
st.title("📊 Encuesta de Satisfacción - Telepeaje")
st.markdown(f"**Registros analizados:** {len(df_filtrado):,} | **Trimestres:** {', '.join(cu_selected)}")
st.divider()

# ============================================================
# 1. RESUMEN EJECUTIVO
# ============================================================
st.header("📈 Resumen Ejecutivo")

col1, col2, col3, col4 = st.columns(4)

with col1:
    prom_q1 = df_filtrado[df_filtrado['CU']=='Q1']['Total_Promedio'].mean()
    prom_q2 = df_filtrado[df_filtrado['CU']=='Q2']['Total_Promedio'].mean()
    delta = prom_q2 - prom_q1 if (not np.isnan(prom_q1) and not np.isnan(prom_q2)) else 0
    st.metric("⭐ Satisfacción Global",
              f"{prom_q2:.2f}" if 'Q2' in cu_selected else f"{prom_q1:.2f}",
              delta=f"{delta:+.2f}" if len(cu_selected)>1 else None)

with col2:
    if 'Q2' in cu_selected:
        nps_val = calc_nps(df_filtrado[df_filtrado['CU']=='Q2'])
        st.metric("📊 NPS (Q2)", f"{nps_val:.1f}" if not np.isnan(nps_val) else "N/A")
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
            if not np.isnan(m1) and not np.isnan(m2):
                brechas.append(m2 - m1)
        if brechas:
            brecha_prom = np.mean(brechas)
            st.metric("📉 Brecha Promedio (Q2 - Q1)", f"{brecha_prom:+.2f}")
        else:
            st.metric("📉 Brecha Promedio", "N/A")
    else:
        st.metric("📉 Brecha Promedio", "Ambos trimestres")

st.divider()

# ============================================================
# CONFIGURACIÓN DE GRÁFICOS
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
# 2. TABLA DE RESULTADOS GENERALES (CON META 8)
# ============================================================
st.header("📊 Resultados Generales vs Meta (mínimo 8)")

META = 8.0

# Definir las dimensiones clave del informe (10 dimensiones)
dimensiones = {
    'Eficiencia operativa (gestión de cruces)': 'P1_Eficiencia_Operativa',
    'Tiempos de respuesta a incidencias': 'P2_Tiempos_Respuesta',
    'Precisión de conciliaciones': 'P3_Precision_Conciliaciones',
    'Gestión de incobrables y discrepancias': 'P5_Gestion_Incobrables',
    'Capacidad de monitoreo 24/7': 'P6_Monitoreo_24_7',
    'Comunicación y notificación ante crisis': 'P7_Comunicacion_Eventos',
    'Comunicación proactiva sobre cambios': 'P14_Comunicacion_Proactiva',
    'Gestión de pagos y liquidez': 'P8_Dispersion_Pagos',
    'Acompañamiento del equipo comercial': 'P10_Acompanamiento_Comercial',
    'Satisfacción general': 'P15_Satisfaccion_Integral'
}

def get_meta_status(valor):
    if pd.isna(valor):
        return 'N/A'
    elif valor >= META:
        return '🟢 Cumple'
    elif valor >= 7.0:
        return '🟡 Cerca'
    else:
        return '🔴 Prioridad'

tabla = []
for nombre, clave in dimensiones.items():
    q1_prom = df_filtrado[df_filtrado['CU']=='Q1'][clave].mean()
    q2_prom = df_filtrado[df_filtrado['CU']=='Q2'][clave].mean()
    if np.isnan(q1_prom):
        q1_prom = np.nan
    if np.isnan(q2_prom):
        q2_prom = np.nan
    variacion = q2_prom - q1_prom if (not np.isnan(q1_prom) and not np.isnan(q2_prom)) else np.nan
    distancia = META - q2_prom if not np.isnan(q2_prom) else np.nan
    progreso = (q2_prom / META) * 100 if not np.isnan(q2_prom) else np.nan
    
    # Estatus de mejora
    if not np.isnan(variacion):
        if variacion < 0:
            status = "🔴 Requiere mejora"
        elif variacion > 0:
            status = "✅ Mejora"
        else:
            status = "⚖️ Estable"
    else:
        status = "N/A"
    
    # Estatus vs meta
    meta_status = get_meta_status(q2_prom)
    
    tabla.append({
        'Dimensión': nombre,
        'Q1': f"{q1_prom:.2f}" if not np.isnan(q1_prom) else "N/A",
        'Q2': f"{q2_prom:.2f}" if not np.isnan(q2_prom) else "N/A",
        'Variación': f"{variacion:+.2f}" if not np.isnan(variacion) else "N/A",
        'Mejora': status,
        'Meta 8': meta_status,
        'Distancia': f"{distancia:+.2f}" if not np.isnan(distancia) else "N/A",
        'Progreso': f"{progreso:.0f}%" if not np.isnan(progreso) else "N/A"
    })

# Añadir fila de promedio general
prom_q1 = df_filtrado[df_filtrado['CU']=='Q1']['Total_Promedio'].mean()
prom_q2 = df_filtrado[df_filtrado['CU']=='Q2']['Total_Promedio'].mean()
variacion_gral = prom_q2 - prom_q1 if (not np.isnan(prom_q1) and not np.isnan(prom_q2)) else np.nan
distancia_gral = META - prom_q2 if not np.isnan(prom_q2) else np.nan
progreso_gral = (prom_q2 / META) * 100 if not np.isnan(prom_q2) else np.nan

if not np.isnan(variacion_gral):
    if variacion_gral < 0:
        status_gral = "🔴 Requiere mejora"
    elif variacion_gral > 0:
        status_gral = "✅ Mejora"
    else:
        status_gral = "⚖️ Estable"
else:
    status_gral = "N/A"

tabla.append({
    'Dimensión': '**Promedio General**',
    'Q1': f"{prom_q1:.2f}" if not np.isnan(prom_q1) else "N/A",
    'Q2': f"{prom_q2:.2f}" if not np.isnan(prom_q2) else "N/A",
    'Variación': f"{variacion_gral:+.2f}" if not np.isnan(variacion_gral) else "N/A",
    'Mejora': status_gral,
    'Meta 8': get_meta_status(prom_q2),
    'Distancia': f"{distancia_gral:+.2f}" if not np.isnan(distancia_gral) else "N/A",
    'Progreso': f"{progreso_gral:.0f}%" if not np.isnan(progreso_gral) else "N/A"
})

df_tabla = pd.DataFrame(tabla)
st.dataframe(df_tabla, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# 3. GRÁFICO DE BARRAS COMPARATIVO (HORIZONTAL)
# ============================================================
st.subheader("🔹 Comparativa por dimensión")

# Preparar datos para gráfico
df_means = df_filtrado.groupby('CU')[preguntas].mean().reset_index()
df_means_melt = df_means.melt(id_vars='CU', var_name='Pregunta', value_name='Promedio')

# Mapear nombres
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
    'P11_Informacion_Estrategica': 'Info. estratégica',
    'P12_Reuniones_Mensuales': 'Reuniones mensuales',
    'P13_Reporte_BI': 'Reporte BI',
    'P14_Comunicacion_Proactiva': 'Comunicación proactiva',
    'P15_Satisfaccion_Integral': 'Satisfacción integral'
}

df_means_melt['Pregunta'] = df_means_melt['Pregunta'].map(etiquetas)
orden_preguntas = list(etiquetas.values())
df_means_melt['Pregunta'] = pd.Categorical(df_means_melt['Pregunta'], categories=orden_preguntas, ordered=True)

# Gráfico de barras horizontales
if len(cu_selected) > 1:
    fig = px.bar(df_means_melt,
                 y='Pregunta',
                 x='Promedio',
                 color='CU',
                 barmode='group',
                 color_discrete_map={'Q1': COLOR_Q1, 'Q2': COLOR_Q2},
                 text_auto='.2f',
                 title='Promedio por dimensión - Q1 vs Q2',
                 template=template,
                 orientation='h')
    fig.update_layout(xaxis_range=[0, 5.5], height=600, legend_title='Trimestre')
    st.plotly_chart(fig, use_container_width=True, config=plot_config)
else:
    df_means_single = df_filtrado[preguntas].mean().reset_index()
    df_means_single.columns = ['Pregunta', 'Promedio']
    df_means_single['Pregunta'] = df_means_single['Pregunta'].map(etiquetas)
    df_means_single['Pregunta'] = pd.Categorical(df_means_single['Pregunta'], categories=orden_preguntas, ordered=True)
    fig = px.bar(df_means_single,
                 y='Pregunta',
                 x='Promedio',
                 color='Pregunta',
                 text_auto='.2f',
                 title=f'Promedio por dimensión - {cu_selected[0]}',
                 template=template,
                 orientation='h')
    fig.update_layout(xaxis_range=[0, 5.5], height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config=plot_config)

# ============================================================
# 4. GRÁFICO DE CUMPLIMIENTO DE META (Q2 vs META 8)
# ============================================================
st.subheader("🎯 Cumplimiento de Meta (mínimo 8)")

# Preparar datos para el gráfico de meta
meta_data = []
for nombre, clave in dimensiones.items():
    q2_val = df_filtrado[df_filtrado['CU']=='Q2'][clave].mean()
    if not np.isnan(q2_val):
        meta_data.append({
            'Dimensión': nombre,
            'Q2': q2_val,
            'Meta': META
        })

if meta_data:
    df_meta = pd.DataFrame(meta_data)
    
    fig_meta = go.Figure()
    # Barras de Q2
    fig_meta.add_trace(go.Bar(
        x=df_meta['Dimensión'],
        y=df_meta['Q2'],
        name='Q2 2026',
        marker_color=COLOR_Q1,
        text=df_meta['Q2'].round(2),
        textposition='outside'
    ))
    # Línea de meta
    fig_meta.add_trace(go.Scatter(
        x=df_meta['Dimensión'],
        y=[META] * len(df_meta),
        mode='lines',
        name=f'Meta ({META})',
        line=dict(color=COLOR_META, width=3, dash='dash'),
        showlegend=True
    ))
    
    fig_meta.update_layout(
        height=450,
        yaxis_range=[0, 9],
        template=template,
        showlegend=True,
        xaxis_tickangle=45
    )
    st.plotly_chart(fig_meta, use_container_width=True, config=plot_config)
else:
    st.info("No hay datos de Q2 disponibles para mostrar la meta.")

# ============================================================
# 5. RADAR CHART (SOLO DIMENSIONES CLAVE)
# ============================================================
if len(cu_selected) > 1:
    st.subheader("🔸 Radar Comparativo")
    
    # Dimensiones clave para el radar (las mismas que en la tabla)
    radar_pregs = [
        'P1_Eficiencia_Operativa',
        'P2_Tiempos_Respuesta',
        'P3_Precision_Conciliaciones',
        'P5_Gestion_Incobrables',
        'P6_Monitoreo_24_7',
        'P7_Comunicacion_Eventos',
        'P14_Comunicacion_Proactiva',
        'P8_Dispersion_Pagos',
        'P10_Acompanamiento_Comercial',
        'P15_Satisfaccion_Integral'
    ]
    radar_etiquetas = ['Eficiencia operativa', 'Tiempos respuesta', 'Precisión conciliaciones',
                       'Gestión incobrables', 'Monitoreo 24/7', 'Comunicación eventos',
                       'Comunicación proactiva', 'Dispersión pagos', 'Acompañamiento comercial',
                       'Satisfacción general']
    
    fig_radar = go.Figure()
    for cu in ['Q1', 'Q2']:
        valores = df_filtrado[df_filtrado['CU']==cu][radar_pregs].mean().values.tolist()
        valores.append(valores[0])  # cerrar el radar
        etiquetas_radar = radar_etiquetas + [radar_etiquetas[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=valores,
            theta=etiquetas_radar,
            name=cu,
            fill='toself',
            line_color=COLOR_Q1 if cu=='Q1' else COLOR_Q2,
            opacity=0.6
        ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5.5],
                tickvals=[0, 1, 2, 3, 4, 5],
                ticktext=['0', '1', '2', '3', '4', '5']
            )
        ),
        height=600,
        showlegend=True,
        template=template
    )
    st.plotly_chart(fig_radar, use_container_width=True, config=plot_config)

st.divider()

# ============================================================
# 6. NPS
# ============================================================
if 'Q2' in cu_selected:
    st.header("⭐ NPS - Q2")
    df_q2_filtrado = df_filtrado[df_filtrado['CU']=='Q2']
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribución de NPS
        df_nps_dist = df_q2_filtrado['NPS'].value_counts().reset_index()
        df_nps_dist.columns = ['Puntuación', 'Conteo']
        df_nps_dist = df_nps_dist.sort_values('Puntuación')
        fig_nps = px.bar(df_nps_dist,
                         x='Puntuación',
                         y='Conteo',
                         text_auto=True,
                         title='Distribución de probabilidad de recomendación',
                         template=template,
                         color_discrete_sequence=[COLOR_Q1])
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
# 7. COMPARATIVA POR CONCESIÓN
# ============================================================
st.header("📋 Comparativa por Concesión (Q1 vs Q2)")

# Calcular promedios por concesión y trimestre
df_conc = df_filtrado.groupby(['CU', 'Nombre de la Concesión'])['Total_Promedio'].mean().reset_index()
# Pivotar
df_conc_pivot = df_conc.pivot(index='Nombre de la Concesión', columns='CU', values='Total_Promedio').reset_index()
# Calcular variación
if 'Q1' in df_conc_pivot.columns and 'Q2' in df_conc_pivot.columns:
    df_conc_pivot['Variación'] = df_conc_pivot['Q2'] - df_conc_pivot['Q1']
else:
    df_conc_pivot['Variación'] = np.nan

# Renombrar
df_conc_pivot.columns = ['Concesión', 'Q1', 'Q2', 'Variación']

# Aplicar estilo y mostrar
st.dataframe(df_conc_pivot.style.format({'Q1': '{:.2f}', 'Q2': '{:.2f}', 'Variación': '{:+.2f}'}),
             use_container_width=True, hide_index=True)

# Gráfico de barras
if len(cu_selected) > 1:
    fig_conc = px.bar(df_conc, x='Nombre de la Concesión', y='Total_Promedio',
                      color='CU', barmode='group',
                      color_discrete_map={'Q1': COLOR_Q1, 'Q2': COLOR_Q2},
                      title='Satisfacción promedio por concesión',
                      template=template)
    fig_conc.update_layout(yaxis_range=[0, 5.5], height=450)
    st.plotly_chart(fig_conc, use_container_width=True, config=plot_config)

st.divider()

# ============================================================
# 8. ANÁLISIS DE COMENTARIOS
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
                                   color_continuous_scale='Reds')
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
# 9. DATOS CRUDOS
# ============================================================
st.header("📋 Datos crudos")
st.dataframe(df_filtrado, use_container_width=True)

csv = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar datos filtrados (CSV)",
    data=csv,
    file_name='datos_filtrados.csv',
    mime='text/csv',
)

st.caption("Dashboard desarrollado con Streamlit | Datos de encuesta de satisfacción - Telepeaje")
