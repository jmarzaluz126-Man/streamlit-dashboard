import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re
import os
import glob

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Encuesta integral de satisfacción concesiones Televía",
    layout="wide",
    page_icon="🛣️"
)

# ============================================================
# COLORES CORPORATIVOS Y META
# ============================================================
COLORES_CU = {
    'Q1': '#E31B23',   # Rojo Aleática
    'Q2': '#1a2a6c',   # Azul profundo
    'Q3': '#28a745',   # Verde
    'Q4': '#ffc107',   # Amarillo
}
COLOR_META = '#C8102E'
META = 8.5  # <--- AQUÍ SE CAMBIÓ LA META A 8.5

# ============================================================
# CARGA DE DATOS (DINÁMICA Q1..Q4)
# ============================================================
PREGUNTAS_CORTAS = [
    'P1_Eficiencia_Operativa', 'P2_Tiempos_Respuesta', 'P3_Precision_Conciliaciones',
    'P4_Facilidad_Procesos', 'P5_Gestion_Incobrables', 'P6_Monitoreo_24_7',
    'P7_Comunicacion_Eventos', 'P8_Dispersion_Pagos', 'P9_Transparencia_Reportes',
    'P10_Acompanamiento_Comercial', 'P11_Informacion_Estrategica', 'P12_Reuniones_Mensuales',
    'P13_Reporte_BI', 'P14_Comunicacion_Proactiva', 'P15_Satisfaccion_Integral',
]

TEXT_COLS = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']

def _limpiar_df(df):
    """Elimina filas de subtotal, vacías y filas sin nombre."""
    df = df.copy()
    df = df.dropna(how='all')
    mask = df.apply(lambda r: r.astype(str).str.contains('SUBTOTAL', case=False, na=False).any(), axis=1)
    df = df[~mask]
    return df.reset_index(drop=True)

def _parsear_trimestre(df, cu):
    df = _limpiar_df(df)
    
    if cu == 'Q1':
        df_fijas = df.iloc[:, 0:7].copy()
        df_fijas.columns = ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico', 'Nombre', 'Nombre de la Concesión', 'Área / Cargo']
        df_preg = df.iloc[:, 7:22].copy()
        df_preg.columns = PREGUNTAS_CORTAS
        df_text = df.iloc[:, 23:26].copy()
        df_text.columns = TEXT_COLS
        df_full = pd.concat([df_fijas.reset_index(drop=True), df_preg.reset_index(drop=True), df_text.reset_index(drop=True)], axis=1)
        df_full['NPS'] = np.nan

    elif cu in ('Q2', 'Q3', 'Q4'):
        df_fijas = df.iloc[:, 0:3].copy()
        df_fijas.columns = ['Nombre', 'Nombre de la Concesión', 'Área / Cargo']
        df_preg = df.iloc[:, 3:18].copy()
        df_preg.columns = PREGUNTAS_CORTAS
        nps = pd.to_numeric(df.iloc[:, 18], errors='coerce').rename('NPS')
        df_text = df.iloc[:, 20:23].copy()
        df_text.columns = TEXT_COLS
        df_full = pd.concat([df_fijas.reset_index(drop=True), df_preg.reset_index(drop=True), nps.reset_index(drop=True), df_text.reset_index(drop=True)], axis=1)
        for col in ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico']:
            df_full[col] = np.nan

    df_full['CU'] = cu
    orden = ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico', 'Nombre', 'Nombre de la Concesión', 'Área / Cargo'] + PREGUNTAS_CORTAS + ['NPS'] + TEXT_COLS + ['CU']
    return df_full[orden]

@st.cache_data(show_spinner=False)
def load_data():
    # Buscar cualquier archivo que empiece con 'Encuesta concesiones' y termine en '.xlsx'
    archivos = glob.glob("Encuesta concesiones*.xlsx")
    if not archivos:
        st.error("❌ No se encontró ningún archivo de Excel en la carpeta. Asegúrate de haberlo subido a GitHub.")
        st.stop()
    
    archivo_real = archivos[0]
    
    try:
        xls = pd.ExcelFile(archivo_real)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo Excel: {e}")
        st.stop()
        
    hojas = xls.sheet_names
    trimestres_disponibles = [cu for cu in ['Q1', 'Q2', 'Q3', 'Q4'] if f'Calificaciones {cu}' in hojas]

    if not trimestres_disponibles:
        st.error("❌ No se encontraron las pestañas 'Calificaciones Q1', 'Q2', etc. Revisa el Excel.")
        st.stop()

    frames = []
    for cu in trimestres_disponibles:
        sheet = f'Calificaciones {cu}'
        skip = 2 if cu == 'Q1' else 1
        df_raw = pd.read_excel(archivo_real, sheet_name=sheet, header=None, skiprows=skip)
        df_norm = _parsear_trimestre(df_raw, cu)
        frames.append(df_norm)

    df = pd.concat(frames, ignore_index=True)

    for p in PREGUNTAS_CORTAS:
        df[p] = pd.to_numeric(df[p], errors='coerce')
    df['NPS'] = pd.to_numeric(df['NPS'], errors='coerce')
    df['Total_Promedio'] = df[PREGUNTAS_CORTAS].mean(axis=1)

    df['Nombre'] = df['Nombre'].astype(str).str.strip()
    df['Nombre de la Concesión'] = df['Nombre de la Concesión'].astype(str).str.strip().str.upper()
    
    homologacion = {
        'AUTOPISTAS DE GUERRERO S.A. DE C.V.': 'AUTOPISTAS DE GUERRERO',
        'METLAPIL': 'AUTOPISTAS DE GUERRERO',
        'CONCESIONARIA AUTOPISTA LIBRAMIENTO HERMOSILLO': 'LIBRAMIENTO HERMOSILLO',
        'CEM': 'CIRCUITO EXTERIOR MEXIQUENSE',
        'VIAS URBANAS': 'VIAS URBANAS',
        'URBANAS': 'VIAS URBANAS'
    }
    df['Nombre de la Concesión'] = df['Nombre de la Concesión'].replace(homologacion)

    return df, PREGUNTAS_CORTAS, trimestres_disponibles

df, preguntas, trimestres_disponibles = load_data()

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.image("https://www.aleatica.com/wp-content/uploads/2024/01/logo-aleatica.png", width=200)
st.sidebar.title("🔍 Filtros")

modo_oscuro = st.sidebar.toggle("🌙 Modo Oscuro", value=False)
template = 'plotly_dark' if modo_oscuro else 'plotly_white'

cu_selected = st.sidebar.multiselect("Selecciona trimestre(s)", options=trimestres_disponibles, default=trimestres_disponibles)
concesiones = st.sidebar.multiselect("Filtrar por concesión", options=sorted(df['Nombre de la Concesión'].dropna().unique()), default=sorted(df['Nombre de la Concesión'].dropna().unique()))

df_filtrado = df[df['CU'].isin(cu_selected)]
df_filtrado = df_filtrado[df_filtrado['Nombre de la Concesión'].isin(concesiones)]

# ============================================================
# CSS
# ============================================================
if modo_oscuro:
    st.markdown("""<style>.stApp { background-color: #1e1e1e; color: white; } .stMetric { background-color: #2d2d2d; padding: 10px; border-radius: 10px; }</style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>.stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }</style>""", unsafe_allow_html=True)

# ============================================================
# FUNCIONES Y ENCABEZADO
# ============================================================
def calc_nps(group):
    if group['NPS'].count() == 0: return np.nan
    promotores = (group['NPS'] >= 9).sum()
    detractores = (group['NPS'] <= 6).sum()
    return round(((promotores - detractores) / group['NPS'].count()) * 100, 1)

def color_cu(cu): return COLORES_CU.get(cu, '#888888')

st.title("📊 Encuesta integral de satisfacción concesiones Televía")
st.markdown(f"**Registros analizados:** {len(df_filtrado):,} | **Trimestres disponibles:** {', '.join(trimestres_disponibles)}")
st.divider()

# ============================================================
# 1. RESUMEN EJECUTIVO
# ============================================================
st.header("📈 Resumen Ejecutivo")
col1, col2, col3, col4 = st.columns(4)

ultimo_cu = cu_selected[-1] if cu_selected else None
prev_cu = cu_selected[-2] if len(cu_selected) > 1 else None

with col1:
    if ultimo_cu:
        prom_ult = df_filtrado[df_filtrado['CU'] == ultimo_cu]['Total_Promedio'].mean()
        delta = (prom_ult - df_filtrado[df_filtrado['CU'] == prev_cu]['Total_Promedio'].mean()) if prev_cu else None
        st.metric(f"⭐ Satisfacción Global ({ultimo_cu})", f"{prom_ult:.2f}" if not np.isnan(prom_ult) else "N/A", delta=f"{delta:+.2f}" if delta is not None else None)

with col2:
    nps_candidates = [cu for cu in cu_selected if cu in ('Q2', 'Q3', 'Q4')]
    if nps_candidates:
        cu_nps = nps_candidates[-1]
        nps_val = calc_nps(df_filtrado[df_filtrado['CU'] == cu_nps])
        st.metric(f"📊 NPS ({cu_nps})", f"{nps_val:.1f}" if not np.isnan(nps_val) else "N/A")
    else:
        st.metric("📊 NPS", "No disponible")

with col3: st.metric("📋 Total Encuestas", f"{len(df_filtrado):,}")

with col4:
    if len(cu_selected) >= 2:
        brechas = [df_filtrado[df_filtrado['CU'] == cu_selected[-1]][p].mean() - df_filtrado[df_filtrado['CU'] == cu_selected[-2]][p].mean() for p in preguntas]
        st.metric(f"📉 Brecha {cu_selected[-1]} vs {cu_selected[-2]}", f"{np.nanmean(brechas):+.2f}")

st.divider()

# ============================================================
# 2. TABLA DE RESULTADOS GENERALES (CON META 8.5)
# ============================================================
st.header(f"📊 Resultados Generales vs Meta (mínimo {META:.1f})")

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

def get_meta_status(v):
    if pd.isna(v): return 'N/A'
    return '🟢 Cumple' if v >= META else ('🟡 Cerca' if v >= 7.0 else '🔴 Prioridad')

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
            var = v_ult - v_prev
            fila['Variación'] = f"{var:+.2f}"
            fila['Mejora'] = "✅ Mejora" if var > 0 else ("🔴 Requiere mejora" if var < 0 else "⚖️ Estable")
        else:
            fila['Variación'], fila['Mejora'] = "N/A", "N/A"
        fila[f'Meta {META:.1f}'] = get_meta_status(v_ult)
        fila['Distancia'] = f"{META - v_ult:+.2f}" if not np.isnan(v_ult) else "N/A"
        fila['Progreso'] = f"{(v_ult / META) * 100:.0f}%" if not np.isnan(v_ult) else "N/A"
    tabla.append(fila)

fila_gral = {'Dimensión': '**Promedio General**'}
for cu in cu_selected:
    val = df_filtrado[df_filtrado['CU'] == cu]['Total_Promedio'].mean()
    fila_gral[cu] = f"{val:.2f}" if not np.isnan(val) else "N/A"
if len(cu_selected) >= 2:
    v_ult = df_filtrado[df_filtrado['CU'] == cu_selected[-1]]['Total_Promedio'].mean()
    v_prev = df_filtrado[df_filtrado['CU'] == cu_selected[-2]]['Total_Promedio'].mean()
    if not (np.isnan(v_ult) or np.isnan(v_prev)):
        var = v_ult - v_prev
        fila_gral['Variación'] = f"{var:+.2f}"
        fila_gral['Mejora'] = "✅ Mejora" if var > 0 else ("🔴 Requiere mejora" if var < 0 else "⚖️ Estable")
    else:
        fila_gral['Variación'], fila_gral['Mejora'] = "N/A", "N/A"
    fila_gral[f'Meta {META:.1f}'] = get_meta_status(v_ult)
    fila_gral['Distancia'] = f"{META - v_ult:+.2f}" if not np.isnan(v_ult) else "N/A"
    fila_gral['Progreso'] = f"{(v_ult / META) * 100:.0f}%" if not np.isnan(v_ult) else "N/A"
tabla.append(fila_gral)
st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)
st.divider()

# ============================================================
# GRÁFICOS Y CONFIG
# ============================================================
plot_config = {'displayModeBar': True, 'displaylogo': False, 'toImageButtonOptions': {'format': 'png', 'filename': 'dashboard_plot', 'scale': 2}}
etiquetas = {p: p.replace('P', '').replace('_', ' ').replace('1 ', '1. ').replace('2 ', '2. ') for p in PREGUNTAS_CORTAS}

# 3. GRÁFICO DE BARRAS COMPARATIVO
st.subheader("🔹 Comparativa por dimensión")
df_means = df_filtrado.groupby('CU')[preguntas].mean().reset_index()
df_means_melt = df_means.melt(id_vars='CU', var_name='Pregunta', value_name='Promedio')
df_means_melt['Pregunta'] = df_means_melt['Pregunta'].map(etiquetas)
orden_preguntas = list(etiquetas.values())
df_means_melt['Pregunta'] = pd.Categorical(df_means_melt['Pregunta'], categories=orden_preguntas, ordered=True)

if len(cu_selected) > 1:
    fig = px.bar(df_means_melt, y='Pregunta', x='Promedio', color='CU', barmode='group', color_discrete_map=COLORES_CU, text_auto='.2f', template=template, orientation='h')
    fig.update_layout(xaxis_range=[0, 10.5], height=650, legend_title='Trimestre')
else:
    cu = cu_selected[0]
    df_single = df_filtrado[preguntas].mean().reset_index()
    df_single.columns = ['Pregunta', 'Promedio']
    df_single['Pregunta'] = df_single['Pregunta'].map(etiquetas)
    df_single['Pregunta'] = pd.Categorical(df_single['Pregunta'], categories=orden_preguntas, ordered=True)
    fig = px.bar(df_single, y='Pregunta', x='Promedio', color='Pregunta', text_auto='.2f', template=template, orientation='h')
    fig.update_layout(xaxis_range=[0, 10.5], height=650, showlegend=False)
st.plotly_chart(fig, use_container_width=True, config=plot_config)

# 4. GRÁFICO DE CUMPLIMIENTO DE META
st.subheader(f"🎯 Cumplimiento de Meta (mínimo {META:.1f})")
meta_data = [{'Dimensión': nom, 'Valor': df_filtrado[df_filtrado['CU'] == cu_selected[-1]][clave].mean()} for nom, clave in dimensiones.items() if not np.isnan(df_filtrado[df_filtrado['CU'] == cu_selected[-1]][clave].mean())]
if meta_data:
    df_meta = pd.DataFrame(meta_data)
    fig_meta = go.Figure()
    fig_meta.add_trace(go.Bar(x=df_meta['Dimensión'], y=df_meta['Valor'], name=cu_selected[-1], marker_color=color_cu(cu_selected[-1]), text=df_meta['Valor'].round(2), textposition='outside'))
    fig_meta.add_trace(go.Scatter(x=df_meta['Dimensión'], y=[META] * len(df_meta), mode='lines', name=f'Meta ({META})', line=dict(color=COLOR_META, width=3, dash='dash')))
    fig_meta.update_layout(height=450, yaxis_range=[0, 9.5], template=template, xaxis_tickangle=45)
    st.plotly_chart(fig_meta, use_container_width=True, config=plot_config)

# 5. RADAR CHART
if len(cu_selected) > 1:
    st.subheader("🔸 Radar Comparativo")
    radar_pregs = ['P1_Eficiencia_Operativa', 'P2_Tiempos_Respuesta', 'P3_Precision_Conciliaciones', 'P5_Gestion_Incobrables', 'P6_Monitoreo_24_7', 'P7_Comunicacion_Eventos', 'P14_Comunicacion_Proactiva', 'P8_Dispersion_Pagos', 'P10_Acompanamiento_Comercial', 'P15_Satisfaccion_Integral']
    fig_radar = go.Figure()
    for cu in cu_selected:
        valores = df_filtrado[df_filtrado['CU'] == cu][radar_pregs].mean().values.tolist()
        fig_radar.add_trace(go.Scatterpolar(r=valores + [valores[0]], theta=[etiquetas[p] for p in radar_pregs] + [etiquetas[radar_pregs[0]]], name=cu, fill='toself', line_color=color_cu(cu), opacity=0.5))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10.5], tickvals=[0, 2, 4, 6, 8, 10])), height=600, template=template)
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
        total = df_cu['NPS'].count()
        if total > 0:
            col1, col2 = st.columns(2)
            with col1:
                df_nps_dist = df_cu['NPS'].value_counts().reset_index()
                df_nps_dist.columns = ['Puntuación', 'Conteo']
                fig_nps = px.bar(df_nps_dist.sort_values('Puntuación'), x='Puntuación', y='Conteo', text_auto=True, template=template, color_discrete_sequence=[color_cu(cu)])
                fig_nps.update_layout(xaxis=dict(tickmode='linear', dtick=1), height=400)
                st.plotly_chart(fig_nps, use_container_width=True, config=plot_config)
            with col2:
                st.metric("📊 NPS General", f"{calc_nps(df_cu):.1f}")
                st.write(f"**Promotores (9-10):** {(df_cu['NPS'] >= 9).sum()} ({(df_cu['NPS'] >= 9).sum()/total*100:.1f}%)")
                st.write(f"**Pasivos (7-8):** {df_cu['NPS'].between(7, 8).sum()} ({df_cu['NPS'].between(7, 8).sum()/total*100:.1f}%)")
                st.write(f"**Detractores (0-6):** {(df_cu['NPS'] <= 6).sum()} ({(df_cu['NPS'] <= 6).sum()/total*100:.1f}%)")
st.divider()

# ============================================================
# 7. COMPARATIVA POR CONCESIÓN
# ============================================================
st.header("📋 Comparativa por Concesión")
df_conc = df_filtrado.groupby(['CU', 'Nombre de la Concesión'])['Total_Promedio'].mean().reset_index()
df_conc_pivot = df_conc.pivot(index='Nombre de la Concesión', columns='CU', values='Total_Promedio').reset_index()

for cu in cu_selected:
    if cu not in df_conc_pivot.columns: df_conc_pivot[cu] = np.nan

if len(cu_selected) >= 2:
    df_conc_pivot['Variación'] = df_conc_pivot[cu_selected[-1]] - df_conc_pivot[cu_selected[-2]]

def get_status(v):
    if pd.isna(v): return '🆕'
    return '🔴 Retroceso' if v < 0 else ('⚖️ Estable' if v == 0 else '✅ Mejora')

if 'Variación' in df_conc_pivot.columns:
    df_conc_pivot['Estatus'] = df_conc_pivot['Variación'].apply(get_status)

df_display = df_conc_pivot.copy()
for cu in cu_selected:
    if cu in df_display.columns: df_display[cu] = df_display[cu].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
if 'Variación' in df_display.columns: df_display['Variación'] = df_display['Variación'].apply(lambda x: f"{x:+.2f}" if not pd.isna(x) else "N/A")

st.dataframe(df_display, use_container_width=True, hide_index=True)

if len(cu_selected) > 1:
    fig_conc = px.bar(df_conc, x='Nombre de la Concesión', y='Total_Promedio', color='CU', barmode='group', color_discrete_map=COLORES_CU, template=template)
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
    
    palabras_basura = ['import streamlit', 'st.write', '>>>', 'streamlit run', 'How to use']
    for basura in palabras_basura:
        textos = textos[~textos.str.contains(basura, case=False, na=False)]

    if len(textos) > 0:
        col_t1, col_t2 = st.columns([1, 1])
        with col_t1:
            st.subheader("🔎 Buscador")
            busqueda = st.text_input("Escribe una palabra clave")
            res = textos[textos.str.contains(busqueda, case=False, na=False)] if busqueda else textos
            st.dataframe(pd.DataFrame(res.head(100), columns=[col_texto]), use_container_width=True)
            st.caption(f"Mostrando {min(100, len(res))} de {len(res)} comentarios.")
        with col_t2:
            st.subheader("📊 Frecuencia")
            stopwords = set(['que', 'de', 'la', 'el', 'en', 'y', 'a', 'los', 'del', 'las', 'un', 'por', 'con', 'no', 'su', 'para', 'es', 'lo', 'como', 'mas', 'pero', 'sus', 'le', 'ya', 'este', 'entre', 'si', 'porque', 'esta', 'son', 'uno', 'todo', 'tambien', 'otro', 'asi', 'mis', 'te', 'se', 'me', 'mi', 'tu', 'yo', 'nos', 'ellos', 'ellas', 'nosotros', 'vosotros', 'les', 'os', 'algo', 'nada', 'muy', 'poco', 'mucho', 'tan', 'cada', 'solo', 'hasta', 'desde', 'durante', 'mediante', 'contra', 'sobre', 'entre', 'sin', 'ni', 'o', 'u', 'cual', 'cuales', 'quien', 'quienes', 'cuyo', 'cuya', 'cuyos', 'cuyas', 'que', 'ya', 'ha', 'he', 'lo', 'le', 'les', 'me', 'nos', 'os', 'te', 'se', 'sí', 'mí', 'ti', 'streamlit', 'import', 'write', 'run'])
            all_words = re.sub(r'[^\w\s]', ' ', re.sub(r'\d+', ' ', " ".join(textos).lower()))
            words = [w for w in all_words.split() if len(w) > 2 and w not in stopwords]
            if words:
                df_words = pd.DataFrame(Counter(words).most_common(20), columns=['Palabra', 'Frecuencia'])
                fig_words = px.bar(df_words, x='Frecuencia', y='Palabra', orientation='h', template=template, color='Frecuencia', color_continuous_scale='Reds')
                fig_words.update_layout(height=500, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_words, use_container_width=True, config=plot_config)
    else:
        st.info("No hay comentarios válidos.")

st.divider()

# ============================================================
# 9. DATOS CRUDOS
# ============================================================
st.header("📋 Datos crudos")
st.dataframe(df_filtrado, use_container_width=True)
csv = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button(label="📥 Descargar datos filtrados (CSV)", data=csv, file_name='datos_filtrados.csv', mime='text/csv')
st.caption("Dashboard desarrollado con Streamlit | Datos de encuesta de satisfacción - Telepeaje")
