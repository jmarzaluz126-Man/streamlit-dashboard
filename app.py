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
    page_title="Encuesta integral de satisfacción concesiones Televía",
    layout="wide",
    page_icon="🛣️"
)

# ============================================================
# COLORES CORPORATIVOS
# ============================================================
COLORES_CU = {
    'Q1': '#E31B23',   # Rojo Aleática
    'Q2': '#1a2a6c',   # Azul profundo
    'Q3': '#28a745',   # Verde
    'Q4': '#ffc107',   # Amarillo
}
COLOR_META = '#C8102E'
META = 8.0

# ============================================================
# CARGA DE DATOS (DINÁMICA Q1..Q4)
# ============================================================
ARCHIVO = 'Encuesta concesiones TLV Q1, Q2 y Q3.xlsx'

PREGUNTAS_CORTAS = [
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
    'P15_Satisfaccion_Integral',
]

TEXT_COLS = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']


def _limpiar_df(df):
    """Elimina filas de subtotal, vacías y filas sin nombre."""
    df = df.copy()
    # Quitar filas completamente vacías
    df = df.dropna(how='all')
    # Quitar filas de SUBTOTAL en cualquier columna
    mask = df.apply(lambda r: r.astype(str).str.contains('SUBTOTAL', case=False, na=False).any(), axis=1)
    df = df[~mask]
    return df.reset_index(drop=True)


def _parsear_trimestre(df, cu, sheet_name):
    """
    Convierte una hoja cruda en un DataFrame normalizado con columnas:
    ID, Hora de inicio, Hora de finalización, Correo electrónico,
    Nombre, Nombre de la Concesión, Área / Cargo,
    P1..P15, NPS, Aciertos, Áreas_mejora, Comentarios_contacto, CU
    """
    df = _limpiar_df(df)

    if cu == 'Q1':
        # Q1: skiprows=2, columnas 0-6 fijas, 7-21 preguntas, 23-25 texto
        df_fijas = df.iloc[:, 0:7].copy()
        df_fijas.columns = ['ID', 'Hora de inicio', 'Hora de finalización',
                            'Correo electrónico', 'Nombre',
                            'Nombre de la Concesión', 'Área / Cargo']
        df_preg = df.iloc[:, 7:22].copy()
        df_preg.columns = PREGUNTAS_CORTAS
        df_text = df.iloc[:, 23:26].copy()
        df_text.columns = TEXT_COLS
        df_full = pd.concat([df_fijas.reset_index(drop=True),
                             df_preg.reset_index(drop=True),
                             df_text.reset_index(drop=True)], axis=1)
        df_full['NPS'] = np.nan

    elif cu in ('Q2', 'Q3', 'Q4'):
        # Q2/Q3/Q4: skiprows=1, columnas 0-2 fijas, 3-17 preguntas, 18 NPS, 20-22 texto
        df_fijas = df.iloc[:, 0:3].copy()
        df_fijas.columns = ['Nombre', 'Nombre de la Concesión', 'Área / Cargo']
        df_preg = df.iloc[:, 3:18].copy()
        df_preg.columns = PREGUNTAS_CORTAS
        # NPS está en columna 18 (índice 18)
        nps = pd.to_numeric(df.iloc[:, 18], errors='coerce').rename('NPS')
        df_text = df.iloc[:, 20:23].copy()
        df_text.columns = TEXT_COLS
        df_full = pd.concat([df_fijas.reset_index(drop=True),
                             df_preg.reset_index(drop=True),
                             nps.reset_index(drop=True),
                             df_text.reset_index(drop=True)], axis=1)
        # Columnas que no existen en Q2/Q3/Q4 -> NaN
        for col in ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico']:
            df_full[col] = np.nan

    else:
        raise ValueError(f"Trimestre desconocido: {cu}")

    df_full['CU'] = cu
    # Reordenar
    orden = ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico',
             'Nombre', 'Nombre de la Concesión', 'Área / Cargo'] + \
            PREGUNTAS_CORTAS + ['NPS'] + TEXT_COLS + ['CU']
    df_full = df_full[orden]
    return df_full


@st.cache_data(show_spinner=False)
def load_data():
    # Detectar pestañas disponibles
    xls = pd.ExcelFile(ARCHIVO)
    hojas = xls.sheet_names
    trimestres_disponibles = []
    for cu in ['Q1', 'Q2', 'Q3', 'Q4']:
        if f'Calificaciones {cu}' in hojas:
            trimestres_disponibles.append(cu)

    frames = []
    for cu in trimestres_disponibles:
        sheet = f'Calificaciones {cu}'
        skip = 2 if cu == 'Q1' else 1
        df_raw = pd.read_excel(ARCHIVO, sheet_name=sheet, header=None, skiprows=skip)
        df_norm = _parsear_trimestre(df_raw, cu, sheet)
        frames.append(df_norm)

    df = pd.concat(frames, ignore_index=True)

    # Convertir a numérico
    for p in PREGUNTAS_CORTAS:
        df[p] = pd.to_numeric(df[p], errors='coerce')
    df['NPS'] = pd.to_numeric(df['NPS'], errors='coerce')

    # Promedio general por fila (solo preguntas)
    df['Total_Promedio'] = df[PREGUNTAS_CORTAS].mean(axis=1)

    # Limpieza de strings
    df['Nombre'] = df['Nombre'].astype(str).str.strip()
    df['Nombre de la Concesión'] = df['Nombre de la Concesión'].astype(str).str.strip()

    return df, PREGUNTAS_CORTAS, trimestres_disponibles


df, preguntas, trimestres_disponibles = load_data()

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.image("https://www.aleatica.com/wp-content/uploads/2024/01/logo-aleatica.png", width=200)
st.sidebar.title("🔍 Filtros")

modo_oscuro = st.sidebar.toggle("🌙 Modo Oscuro", value=False)
template = 'plotly_dark' if modo_oscuro else 'plotly_white'

cu_selected = st.sidebar.multiselect(
    "Selecciona trimestre(s)",
    options=trimestres_disponibles,
    default=trimestres_disponibles,
)

concesiones = st.sidebar.multiselect(
    "Filtrar por concesión",
    options=sorted(df['Nombre de la Concesión'].dropna().unique()),
    default=sorted(df['Nombre de la Concesión'].dropna().unique()),
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


def color_cu(cu):
    return COLORES_CU.get(cu, '#888888')


# ============================================================
# ENCABEZADO
# ============================================================
st.title("📊 Encuesta integral de satisfacción concesiones Televía")
st.markdown(f"**Registros analizados:** {len(df_filtrado):,} | "
            f"**Trimestres disponibles:** {', '.join(trimestres_disponibles)} | "
            f"**Seleccionados:** {', '.join(cu_selected) if cu_selected else 'Ninguno'}")
st.divider()

# ============================================================
# 1. RESUMEN EJECUTIVO
# ============================================================
st.header("📈 Resumen Ejecutivo")

col1, col2, col3, col4 = st.columns(4)

# Satisfacción global: último trimestre seleccionado vs anterior
ultimo_cu = cu_selected[-1] if cu_selected else None
prev_cu = cu_selected[-2] if len(cu_selected) > 1 else None

with col1:
    if ultimo_cu:
        prom_ult = df_filtrado[df_filtrado['CU'] == ultimo_cu]['Total_Promedio'].mean()
        delta = None
        if prev_cu:
            prom_prev = df_filtrado[df_filtrado['CU'] == prev_cu]['Total_Promedio'].mean()
            delta = prom_ult - prom_prev if not (np.isnan(prom_ult) or np.isnan(prom_prev)) else None
        st.metric(f"⭐ Satisfacción Global ({ultimo_cu})",
                  f"{prom_ult:.2f}" if not np.isnan(prom_ult) else "N/A",
                  delta=f"{delta:+.2f}" if delta is not None else None)
    else:
        st.metric("⭐ Satisfacción Global", "N/A")

with col2:
    nps_candidates = [cu for cu in cu_selected if cu in ('Q2', 'Q3', 'Q4')]
    if nps_candidates:
        cu_nps = nps_candidates[-1]
        nps_val = calc_nps(df_filtrado[df_filtrado['CU'] == cu_nps])
        st.metric(f"📊 NPS ({cu_nps})", f"{nps_val:.1f}" if not np.isnan(nps_val) else "N/A")
    else:
        st.metric("📊 NPS", "No disponible")

with col3:
    st.metric("📋 Total Encuestas", f"{len(df_filtrado):,}")

with col4:
    if len(cu_selected) >= 2:
        brechas = []
        for p in preguntas:
            m_ult = df_filtrado[df_filtrado['CU'] == cu_selected[-1]][p].mean()
            m_prev = df_filtrado[df_filtrado['CU'] == cu_selected[-2]][p].mean()
            if not (np.isnan(m_ult) or np.isnan(m_prev)):
                brechas.append(m_ult - m_prev)
        if brechas:
            st.metric(f"📉 Brecha {cu_selected[-1]} vs {cu_selected[-2]}", f"{np.mean(brechas):+.2f}")
        else:
            st.metric("📉 Brecha Promedio", "N/A")
    else:
        st.metric("📉 Brecha Promedio", "Selecciona 2+ trimestres")

st.divider()

# ============================================================
# CONFIGURACIÓN DE GRÁFICOS
# ============================================================
plot_config = {
    'displayModeBar': True,
    'displaylogo': False,
    'toImageButtonOptions': {'format': 'png', 'filename': 'dashboard_plot', 'scale': 2},
}

# ============================================================
# 2. TABLA DE RESULTADOS GENERALES (CON META 8)
# ============================================================
st.header(f"📊 Resultados Generales vs Meta (mínimo {META:.0f})")

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
    'Satisfacción general': 'P15_Satisfaccion_Integral',
}

def get_meta_status(valor):
    if pd.isna(valor):
        return 'N/A'
    if valor >= META:
        return '🟢 Cumple'
    if valor >= 7.0:
        return '🟡 Cerca'
    return '🔴 Prioridad'

tabla = []
for nombre, clave in dimensiones.items():
    fila = {'Dimensión': nombre}
    for cu in cu_selected:
        val = df_filtrado[df_filtrado['CU'] == cu][clave].mean()
        fila[cu] = f"{val:.2f}" if not np.isnan(val) else "N/A"
    if len(cu_selected) >= 2:
        v_ult = df_filtrado[df_filtrado['CU'] == cu_selected[-1]][clave].mean()
        v_prev = df_filtrado[df_filtrado['CU'] == cu_selected[-2]][clave].mean()
        if not (np.isnan(v_ult) or np.isnan(v_prev)):
            variacion = v_ult - v_prev
            fila['Variación'] = f"{variacion:+.2f}"
            fila['Mejora'] = "✅ Mejora" if variacion > 0 else ("🔴 Requiere mejora" if variacion < 0 else "⚖️ Estable")
        else:
            fila['Variación'] = "N/A"
            fila['Mejora'] = "N/A"
        fila['Meta 8'] = get_meta_status(v_ult)
        fila['Distancia'] = f"{META - v_ult:+.2f}" if not np.isnan(v_ult) else "N/A"
        fila['Progreso'] = f"{(v_ult / META) * 100:.0f}%" if not np.isnan(v_ult) else "N/A"
    tabla.append(fila)

# Fila de promedio general
fila_gral = {'Dimensión': '**Promedio General**'}
for cu in cu_selected:
    val = df_filtrado[df_filtrado['CU'] == cu]['Total_Promedio'].mean()
    fila_gral[cu] = f"{val:.2f}" if not np.isnan(val) else "N/A"
if len(cu_selected) >= 2:
    v_ult = df_filtrado[df_filtrado['CU'] == cu_selected[-1]]['Total_Promedio'].mean()
    v_prev = df_filtrado[df_filtrado['CU'] == cu_selected[-2]]['Total_Promedio'].mean()
    if not (np.isnan(v_ult) or np.isnan(v_prev)):
        variacion = v_ult - v_prev
        fila_gral['Variación'] = f"{variacion:+.2f}"
        fila_gral['Mejora'] = "✅ Mejora" if variacion > 0 else ("🔴 Requiere mejora" if variacion < 0 else "⚖️ Estable")
    else:
        fila_gral['Variación'] = "N/A"
        fila_gral['Mejora'] = "N/A"
    fila_gral['Meta 8'] = get_meta_status(v_ult)
    fila_gral['Distancia'] = f"{META - v_ult:+.2f}" if not np.isnan(v_ult) else "N/A"
    fila_gral['Progreso'] = f"{(v_ult / META) * 100:.0f}%" if not np.isnan(v_ult) else "N/A"
tabla.append(fila_gral)

st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)
st.divider()

# ============================================================
# 3. GRÁFICO DE BARRAS COMPARATIVO (HORIZONTAL)
# ============================================================
st.subheader("🔹 Comparativa por dimensión")

df_means = df_filtrado.groupby('CU')[preguntas].mean().reset_index()
df_means_melt = df_means.melt(id_vars='CU', var_name='Pregunta', value_name='Promedio')

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
    'P15_Satisfaccion_Integral': 'Satisfacción integral',
}

df_means_melt['Pregunta'] = df_means_melt['Pregunta'].map(etiquetas)
orden_preguntas = list(etiquetas.values())
df_means_melt['Pregunta'] = pd.Categorical(df_means_melt['Pregunta'], categories=orden_preguntas, ordered=True)

if len(cu_selected) > 1:
    fig = px.bar(df_means_melt, y='Pregunta', x='Promedio', color='CU',
                 barmode='group', color_discrete_map=COLORES_CU,
                 text_auto='.2f',
                 title='Promedio por dimensión - comparativa de trimestres',
                 template=template, orientation='h')
    fig.update_layout(xaxis_range=[0, 10.5], height=650, legend_title='Trimestre')
    st.plotly_chart(fig, use_container_width=True, config=plot_config)
else:
    cu = cu_selected[0]
    df_single = df_filtrado[preguntas].mean().reset_index()
    df_single.columns = ['Pregunta', 'Promedio']
    df_single['Pregunta'] = df_single['Pregunta'].map(etiquetas)
    df_single['Pregunta'] = pd.Categorical(df_single['Pregunta'], categories=orden_preguntas, ordered=True)
    fig = px.bar(df_single, y='Pregunta', x='Promedio', color='Pregunta',
                 text_auto='.2f', title=f'Promedio por dimensión - {cu}',
                 template=template, orientation='h')
    fig.update_layout(xaxis_range=[0, 10.5], height=650, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config=plot_config)

# ============================================================
# 4. GRÁFICO DE CUMPLIMIENTO DE META
# ============================================================
st.subheader(f"🎯 Cumplimiento de Meta (mínimo {META:.0f})")

meta_data = []
for nombre, clave in dimensiones.items():
    ult = df_filtrado[df_filtrado['CU'] == cu_selected[-1]][clave].mean() if cu_selected else np.nan
    if not np.isnan(ult):
        meta_data.append({'Dimensión': nombre, 'Valor': ult, 'Meta': META, 'CU': cu_selected[-1]})

if meta_data:
    df_meta = pd.DataFrame(meta_data)
    fig_meta = go.Figure()
    fig_meta.add_trace(go.Bar(
        x=df_meta['Dimensión'], y=df_meta['Valor'],
        name=cu_selected[-1], marker_color=color_cu(cu_selected[-1]),
        text=df_meta['Valor'].round(2), textposition='outside'
    ))
    fig_meta.add_trace(go.Scatter(
        x=df_meta['Dimensión'], y=[META] * len(df_meta),
        mode='lines', name=f'Meta ({META})',
        line=dict(color=COLOR_META, width=3, dash='dash')
    ))
    fig_meta.update_layout(height=450, yaxis_range=[0, 9.5],
                           template=template, xaxis_tickangle=45)
    st.plotly_chart(fig_meta, use_container_width=True, config=plot_config)
else:
    st.info("No hay datos para el trimestre seleccionado.")

# ============================================================
# 5. RADAR CHART
# ============================================================
if len(cu_selected) > 1:
    st.subheader("🔸 Radar Comparativo")
    radar_pregs = [
        'P1_Eficiencia_Operativa', 'P2_Tiempos_Respuesta',
        'P3_Precision_Conciliaciones', 'P5_Gestion_Incobrables',
        'P6_Monitoreo_24_7', 'P7_Comunicacion_Eventos',
        'P14_Comunicacion_Proactiva', 'P8_Dispersion_Pagos',
        'P10_Acompanamiento_Comercial', 'P15_Satisfaccion_Integral',
    ]
    radar_etiquetas = ['Eficiencia operativa', 'Tiempos respuesta',
                       'Precisión conciliaciones', 'Gestión incobrables',
                       'Monitoreo 24/7', 'Comunicación eventos',
                       'Comunicación proactiva', 'Dispersión pagos',
                       'Acompañamiento comercial', 'Satisfacción general']

    fig_radar = go.Figure()
    for cu in cu_selected:
        valores = df_filtrado[df_filtrado['CU'] == cu][radar_pregs].mean().values.tolist()
        valores.append(valores[0])
        fig_radar.add_trace(go.Scatterpolar(
            r=valores, theta=radar_etiquetas + [radar_etiquetas[0]],
            name=cu, fill='toself', line_color=color_cu(cu), opacity=0.5
        ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10.5],
                                   tickvals=[0, 2, 4, 6, 8, 10])),
        height=600, showlegend=True, template=template
    )
    st.plotly_chart(fig_radar, use_container_width=True, config=plot_config)

st.divider()

# ============================================================
# 6. NPS
# ============================================================
cu_con_nps = [cu for cu in cu_selected if cu in ('Q2', 'Q3', 'Q4')]
if cu_con_nps:
    st.header("⭐ NPS")
    for cu in cu_con_nps:
        st.subheader(f"NPS - {cu}")
        df_cu = df_filtrado[df_filtrado['CU'] == cu]
        nps_val = calc_nps(df_cu)
        total = df_cu['NPS'].count()

        if total == 0:
            st.info(f"No hay respuestas de NPS en {cu}.")
            continue

        col1, col2 = st.columns(2)
        with col1:
            df_nps_dist = df_cu['NPS'].value_counts().reset_index()
            df_nps_dist.columns = ['Puntuación', 'Conteo']
            df_nps_dist = df_nps_dist.sort_values('Puntuación')
            fig_nps = px.bar(df_nps_dist, x='Puntuación', y='Conteo', text_auto=True,
                             title=f'Distribución NPS - {cu}',
                             template=template, color_discrete_sequence=[color_cu(cu)])
            fig_nps.update_layout(xaxis=dict(tickmode='linear', dtick=1), height=400)
            st.plotly_chart(fig_nps, use_container_width=True, config=plot_config)
        with col2:
            promotores = (df_cu['NPS'] >= 9).sum()
            pasivos = (df_cu['NPS'].between(7, 8)).sum()
            detractores = (df_cu['NPS'] <= 6).sum()
            st.metric("📊 NPS General", f"{nps_val:.1f}")
            st.write(f"**Promotores (9-10):** {promotores} ({promotores/total*100:.1f}%)")
            st.write(f"**Pasivos (7-8):** {pasivos} ({pasivos/total*100:.1f}%)")
            st.write(f"**Detractores (0-6):** {detractores} ({detractores/total*100:.1f}%)")
            st.write(f"**Total respuestas:** {total}")
        st.divider()

# ============================================================
# 7. COMPARATIVA POR CONCESIÓN
# ============================================================
st.header("📋 Comparativa por Concesión")

df_conc = df_filtrado.groupby(['CU', 'Nombre de la Concesión'])['Total_Promedio'].mean().reset_index()
df_conc_pivot = df_conc.pivot(index='Nombre de la Concesión', columns='CU', values='Total_Promedio').reset_index()

# Asegurar columnas en orden
for cu in cu_selected:
    if cu not in df_conc_pivot.columns:
        df_conc_pivot[cu] = np.nan

cols_show = ['Nombre de la Concesión'] + cu_selected
if len(cu_selected) >= 2:
    df_conc_pivot['Variación'] = df_conc_pivot[cu_selected[-1]] - df_conc_pivot[cu_selected[-2]]

def get_status(v):
    if pd.isna(v):
        return '🆕'
    if v < 0:
        return '🔴 Retroceso'
    if v == 0:
        return '⚖️ Estable'
    return '✅ Mejora'

if 'Variación' in df_conc_pivot.columns:
    df_conc_pivot['Estatus'] = df_conc_pivot['Variación'].apply(get_status)

df_display = df_conc_pivot.copy()
for cu in cu_selected:
    if cu in df_display.columns:
        df_display[cu] = df_display[cu].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
if 'Variación' in df_display.columns:
    df_display['Variación'] = df_display['Variación'].apply(lambda x: f"{x:+.2f}" if not pd.isna(x) else "N/A")

st.dataframe(df_display, use_container_width=True, hide_index=True)

if len(cu_selected) > 1:
    fig_conc = px.bar(df_conc, x='Nombre de la Concesión', y='Total_Promedio',
                      color='CU', barmode='group', color_discrete_map=COLORES_CU,
                      title='Satisfacción promedio por concesión',
                      template=template)
    fig_conc.update_layout(yaxis_range=[0, 10.5], height=500, xaxis_tickangle=45)
    st.plotly_chart(fig_conc, use_container_width=True, config=plot_config)

st.divider()

# ============================================================
# 8. ANÁLISIS DE COMENTARIOS
# ============================================================
text_cols_existentes = [c for c in TEXT_COLS if c in df_filtrado.columns]
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
                res = textos[textos.str.contains(busqueda, case=False, na=False)]
                st.dataframe(pd.DataFrame(res, columns=[col_texto]), use_container_width=True)
            else:
                st.dataframe(pd.DataFrame(textos.head(100), columns=[col_texto]), use_container_width=True)
                st.caption(f"Mostrando 100 de {len(textos)} comentarios.")
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
            words = [w for w in all_words.split() if len(w) > 2 and w not in stopwords]
            if words:
                counter = Counter(words).most_common(20)
                df_words = pd.DataFrame(counter, columns=['Palabra', 'Frecuencia'])
                fig_words = px.bar(df_words, x='Frecuencia', y='Palabra', orientation='h',
                                   title='Top 20 palabras', template=template,
                                   color='Frecuencia', color_continuous_scale='Reds')
                fig_words.update_layout(height=500, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_words, use_container_width=True, config=plot_config)
            else:
                st.info("No se encontraron palabras significativas.")
    else:
        st.info("No hay comentarios en esta categoría para los datos seleccionados.")
else:
    st.info("💬 No se detectaron columnas de comentarios.")

st
