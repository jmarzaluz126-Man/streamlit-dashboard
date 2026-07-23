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
@st.cache
def load_data():
    try:
        # ---------- LECTURA DE HOJAS ----------
        # Q1: sin cabecera, saltamos 2 filas
        df_q1_raw = pd.read_excel(
            'Encuesta concesiones TLV Q1 y Q2.xlsx',
            sheet_name='Calificaciones Q1',
            header=None,
            skiprows=2
        )
        # Q2: sin cabecera, saltamos 1 fila
        df_q2_raw = pd.read_excel(
            'Encuesta concesiones TLV Q1 y Q2.xlsx',
            sheet_name='Calificaciones Q2',
            header=None,
            skiprows=1
        )

        # ---------- ELIMINAR FILAS DE SUBTOTAL Y VACÍAS ----------
        # Q1: columna 0 (ID)
        df_q1_raw = df_q1_raw.dropna(subset=[0])
        df_q1_raw = df_q1_raw[~df_q1_raw[0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
        df_q1_raw = df_q1_raw[df_q1_raw[0].astype(str).str.strip() != '']
        df_q1_raw = df_q1_raw[df_q1_raw[0].astype(str).str.isnumeric()]

        # Q2: columna 0 (Nombre)
        df_q2_raw = df_q2_raw.dropna(subset=[0])
        df_q2_raw = df_q2_raw[~df_q2_raw[0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
        df_q2_raw = df_q2_raw[df_q2_raw[0].astype(str).str.strip() != '']

        # ---------- DEFINIR PREGUNTAS ----------
        preguntas_cortas = [
            'P1_Eficiencia_Operativa', 'P2_Tiempos_Respuesta', 
            'P3_Precision_Conciliaciones', 'P4_Facilidad_Procesos',
            'P5_Gestion_Incobrables', 'P6_Monitoreo_24_7',
            'P7_Comunicacion_Eventos', 'P8_Dispersion_Pagos',
            'P9_Transparencia_Reportes', 'P10_Acompanamiento_Comercial',
            'P11_Informacion_Estrategica', 'P12_Reuniones_Mensuales',
            'P13_Reporte_BI', 'P14_Comunicacion_Proactiva',
            'P15_Satisfaccion_Integral'
        ]

        # ---------- CONSTRUIR Q1 ----------
        q1_fijas = df_q1_raw.iloc[:, 0:7].copy()
        q1_fijas.columns = ['ID', 'Hora de inicio', 'Hora de finalización', 
                           'Correo electrónico', 'Nombre', 'Nombre de la Concesión', 'Área / Cargo']
        q1_preg = df_q1_raw.iloc[:, 7:22].copy()
        q1_preg.columns = preguntas_cortas
        q1_text = df_q1_raw.iloc[:, 23:26].copy()
        q1_text.columns = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']
        q1_nps = pd.DataFrame({'NPS': [np.nan] * len(q1_fijas)})

        # ---------- CONSTRUIR Q2 ----------
        q2_fijas = df_q2_raw.iloc[:, 0:3].copy()
        q2_fijas.columns = ['Nombre', 'Nombre de la Concesión', 'Área / Cargo']
        q2_preg = df_q2_raw.iloc[:, 3:18].copy()
        q2_preg.columns = preguntas_cortas
        q2_nps = df_q2_raw.iloc[:, 18].copy().rename('NPS')
        q2_text = df_q2_raw.iloc[:, 20:23].copy()
        q2_text.columns = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']

        # ---------- UNIR Q1 ----------
        df_q1_full = pd.concat([q1_fijas.reset_index(drop=True),
                                q1_preg.reset_index(drop=True),
                                q1_nps.reset_index(drop=True),
                                q1_text.reset_index(drop=True)], axis=1)
        df_q1_full['CU'] = 'Q1'

        # ---------- UNIR Q2 ----------
        df_q2_full = pd.concat([q2_fijas.reset_index(drop=True),
                                q2_preg.reset_index(drop=True),
                                q2_nps.reset_index(drop=True),
                                q2_text.reset_index(drop=True)], axis=1)
        df_q2_full['CU'] = 'Q2'

        # ---------- HOMOLOGAR NOMBRES ----------
        df_q1_full['Nombre de la Concesión'] = df_q1_full['Nombre de la Concesión'].replace({
            'AUNORTE': 'Vias Urbanas'
        })
        df_q2_full['Nombre de la Concesión'] = df_q2_full['Nombre de la Concesión'].replace({
            'AUNORTE': 'Vias Urbanas'
        })

        # ---------- UNIFICAR ----------
        for col in ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico']:
            if col not in df_q2_full.columns:
                df_q2_full[col] = np.nan

        orden = ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico',
                 'Nombre', 'Nombre de la Concesión', 'Área / Cargo'] + preguntas_cortas + ['NPS', 'Aciertos', 'Áreas_mejora', 'Comentarios_contacto', 'CU']
        df_q1_full = df_q1_full[orden]
        df_q2_full = df_q2_full[orden]

        df = pd.concat([df_q1_full, df_q2_full], ignore_index=True)

        # ---------- CONVERTIR A NUMÉRICO ----------
        for p in preguntas_cortas:
            df[p] = pd.to_numeric(df[p], errors='coerce')
        df['NPS'] = pd.to_numeric(df['NPS'], errors='coerce')
        df['Total_Promedio'] = df[preguntas_cortas].mean(axis=1)

        return df, preguntas_cortas

    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        # Si hay error, devolver DataFrames vacíos con estructura mínima
        preguntas_cortas = ['P1_Eficiencia_Operativa', 'P2_Tiempos_Respuesta']
        df = pd.DataFrame(columns=['Nombre de la Concesión', 'CU', 'Total_Promedio'])
        return df, preguntas_cortas


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def calc_nps(group):
    if group['NPS'].count() == 0:
        return np.nan
    promotores = (group['NPS'] >= 9).sum()
    detractores = (group['NPS'] <= 6).sum()
    total = group['NPS'].count()
    return round(((promotores - detractores) / total) * 100, 1)

def get_status(variacion):
    if pd.isna(variacion):
        return '🆕 Nueva'
    elif variacion < 0:
        return '🔴 Retroceso'
    elif variacion == 0:
        return '⚖️ Estable'
    else:
        return '✅ Mejora'

def get_meta_status(valor, meta=8.0):
    if pd.isna(valor):
        return 'N/A', '#6c757d'
    elif valor >= meta:
        return '🟢 Cumple', '#28a745'
    elif valor >= 7.0:
        return '🟡 Cerca', '#ffc107'
    else:
        return '🔴 Prioridad', '#dc3545'


# ============================================================
# CARGA DE DATOS
# ============================================================
df, preguntas = load_data()

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.image("https://www.aleatica.com/wp-content/uploads/2024/01/logo-aleatica.png", width=200)
st.sidebar.markdown("---")

modo_oscuro = st.sidebar.toggle("🌙 Modo Oscuro", value=False)
template = 'plotly_dark' if modo_oscuro else 'plotly_white'

cu_selected = st.sidebar.multiselect(
    "Selecciona trimestre",
    options=sorted(df['CU'].unique()) if not df.empty else ['Q1', 'Q2'],
    default=sorted(df['CU'].unique()) if not df.empty else ['Q1', 'Q2']
)

concesiones = st.sidebar.multiselect(
    "Filtrar por concesión",
    options=sorted(df['Nombre de la Concesión'].dropna().unique()) if not df.empty else ['Sin datos'],
    default=sorted(df['Nombre de la Concesión'].dropna().unique()) if not df.empty else ['Sin datos']
)

df_filtrado = df[df['CU'].isin(cu_selected)] if not df.empty else df
df_filtrado = df_filtrado[df_filtrado['Nombre de la Concesión'].isin(concesiones)] if not df_filtrado.empty else df_filtrado

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
# ENCABEZADO
# ============================================================
st.title("📊 Encuesta de Satisfacción - Telepeaje")
st.markdown(f"**Registros analizados:** {len(df_filtrado):,} | **Trimestres:** {', '.join(cu_selected)}")
st.divider()

# ============================================================
# KPIs
# ============================================================
st.header("📈 Resumen Ejecutivo")

col1, col2, col3, col4 = st.columns(4)

with col1:
    prom_q1 = df_filtrado[df_filtrado['CU']=='Q1']['Total_Promedio'].mean() if not df_filtrado.empty else np.nan
    prom_q2 = df_filtrado[df_filtrado['CU']=='Q2']['Total_Promedio'].mean() if not df_filtrado.empty else np.nan
    delta = prom_q2 - prom_q1 if (not np.isnan(prom_q1) and not np.isnan(prom_q2)) else 0
    st.metric("⭐ Satisfacción Global",
              f"{prom_q2:.2f}" if 'Q2' in cu_selected else f"{prom_q1:.2f}",
              delta=f"{delta:+.2f}" if len(cu_selected)>1 else None)

with col2:
    if 'Q2' in cu_selected and not df_filtrado.empty:
        nps_val = calc_nps(df_filtrado[df_filtrado['CU']=='Q2'])
        st.metric("📊 NPS (Q2)", f"{nps_val:.1f}" if not np.isnan(nps_val) else "N/A")
    else:
        st.metric("📊 NPS", "Selecciona Q2")

with col3:
    total_encuestas = len(df_filtrado)
    st.metric("📋 Total Encuestas", f"{total_encuestas:,}")

with col4:
    if 'Q1' in cu_selected and 'Q2' in cu_selected and not df_filtrado.empty:
        brechas = []
        for p in preguntas:
            m1 = df_filtrado[df_filtrado['CU']=='Q1'][p].mean()
            m2 = df_filtrado[df_filtrado['CU']=='Q2'][p].mean()
            if not np.isnan(m1) and not np.isnan(m2):
                brechas.append(m2 - m1)
        brecha_prom = np.mean(brechas) if brechas else 0
        st.metric("📉 Brecha Promedio (Q2 - Q1)", f"{brecha_prom:+.2f}")
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
# TABLA DE RESULTADOS GENERALES (VS META 8)
# ============================================================
if not df_filtrado.empty:
    st.header("📊 Resultados Generales vs Meta (mínimo 8)")

    dimensiones = {
        'Eficiencia operativa': 'P1_Eficiencia_Operativa',
        'Tiempos de respuesta': 'P2_Tiempos_Respuesta',
        'Precisión de conciliaciones': 'P3_Precision_Conciliaciones',
        'Gestión de incobrables': 'P5_Gestion_Incobrables',
        'Monitoreo 24/7': 'P6_Monitoreo_24_7',
        'Comunicación ante crisis': 'P7_Comunicacion_Eventos',
        'Comunicación proactiva': 'P14_Comunicacion_Proactiva',
        'Gestión de pagos': 'P8_Dispersion_Pagos',
        'Acompañamiento comercial': 'P10_Acompanamiento_Comercial',
        'Satisfacción general': 'P15_Satisfaccion_Integral'
    }

    META = 8.0
    tabla_meta = []

    for nombre, clave in dimensiones.items():
        q1_val = df_filtrado[df_filtrado['CU']=='Q1'][clave].mean() if 'Q1' in cu_selected else np.nan
        q2_val = df_filtrado[df_filtrado['CU']=='Q2'][clave].mean() if 'Q2' in cu_selected else np.nan
        
        variacion = q2_val - q1_val if (not np.isnan(q1_val) and not np.isnan(q2_val)) else np.nan
        distancia = META - q2_val if not np.isnan(q2_val) else np.nan
        progreso = (q2_val / META) * 100 if not np.isnan(q2_val) else np.nan
        status_mejora = get_status(variacion)
        status_meta, _ = get_meta_status(q2_val, META)

        tabla_meta.append({
            'Dimensión': nombre,
            'Q1': f"{q1_val:.2f}" if not np.isnan(q1_val) else "N/A",
            'Q2': f"{q2_val:.2f}" if not np.isnan(q2_val) else "N/A",
            'Variación': f"{variacion:+.2f}" if not np.isnan(variacion) else "N/A",
            'Estatus': status_mejora,
            'Meta 8': status_meta,
            'Distancia': f"{distancia:+.2f}" if not np.isnan(distancia) else "N/A",
            'Progreso': f"{progreso:.0f}%" if not np.isnan(progreso) else "N/A"
        })

    df_tabla_meta = pd.DataFrame(tabla_meta)
    st.dataframe(df_tabla_meta, use_container_width=True, hide_index=True)
    st.divider()

    # ============================================================
    # GRÁFICO DE BARRAS COMPARATIVAS
    # ============================================================
    st.subheader("📊 Comparativa por Dimensión")

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

    df_means = df_filtrado.groupby('CU')[preguntas].mean().reset_index()
    df_means_melt = df_means.melt(id_vars='CU', var_name='Pregunta', value_name='Promedio')
    df_means_melt['Pregunta'] = df_means_melt['Pregunta'].map(etiquetas)

    orden = list(etiquetas.values())
    df_means_melt['Pregunta'] = pd.Categorical(df_means_melt['Pregunta'], categories=orden, ordered=True)

    fig = px.bar(df_means_melt,
                 x='Pregunta',
                 y='Promedio',
                 color='CU',
                 barmode='group',
                 color_discrete_map={'Q1': COLOR_Q1, 'Q2': COLOR_Q2},
                 text_auto='.2f',
                 title='Promedio por dimensión - Q1 vs Q2',
                 template=template)
    fig.update_layout(yaxis_range=[0, 5.5], height=500, legend_title='Trimestre')
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True, config=plot_config)
    st.divider()

    # ============================================================
    # GRÁFICO DE META
    # ============================================================
    if 'Q2' in cu_selected:
        st.subheader("🎯 Cumplimiento de Meta (mínimo 8)")

        meta_data = []
        for nombre, clave in dimensiones.items():
            q2_val = df_filtrado[df_filtrado['CU']=='Q2'][clave].mean()
            if not np.isnan(q2_val):
                meta_data.append({'Dimensión': nombre, 'Q2': q2_val})

        if meta_data:
            df_meta = pd.DataFrame(meta_data)
            fig_meta = go.Figure()
            fig_meta.add_trace(go.Bar(
                x=df_meta['Dimensión'],
                y=df_meta['Q2'],
                name='Q2 2026',
                marker_color=COLOR_Q1,
                text=df_meta['Q2'].round(2),
                textposition='outside'
            ))
            fig_meta.add_trace(go.Scatter(
                x=df_meta['Dimensión'],
                y=[META] * len(df_meta),
                mode='lines',
                name=f'Meta ({META})',
                line=dict(color=COLOR_META, width=3, dash='dash')
            ))
            fig_meta.update_layout(height=450, yaxis_range=[0, 9], template=template, showlegend=True)
            fig_meta.update_xaxes(tickangle=45)
            st.plotly_chart(fig_meta, use_container_width=True, config=plot_config)
            st.divider()

    # ============================================================
    # RADAR CHART
    # ============================================================
    if len(cu_selected) > 1:
        st.subheader("🔸 Radar Comparativo")
        radar_pregs = [
            'P1_Eficiencia_Operativa', 'P2_Tiempos_Respuesta',
            'P3_Precision_Conciliaciones', 'P5_Gestion_Incobrables',
            'P6_Monitoreo_24_7', 'P7_Comunicacion_Eventos',
            'P14_Comunicacion_Proactiva', 'P8_Dispersion_Pagos',
            'P10_Acompanamiento_Comercial', 'P15_Satisfaccion_Integral'
        ]
        radar_etiquetas = [etiquetas[p] for p in radar_pregs]

        fig_radar = go.Figure()
        for cu in ['Q1', 'Q2']:
            valores = df_filtrado[df_filtrado['CU']==cu][radar_pregs].mean().values.tolist()
            valores.append(valores[0])
            etiquetas_radar = radar_etiquetas + [radar_etiquetas[0]]
            fig_radar.add_trace(go.Scatterpolar(
                r=valores,
                theta=etiquetas_radar,
                name=cu,
                fill='toself',
                line_color=COLOR_Q1 if cu=='Q1' else COLOR_Q2,
                opacity=0.3
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
    # NPS (Q2)
    # ============================================================
    if 'Q2' in cu_selected:
        st.header("⭐ NPS - Q2")
        df_q2_filtrado = df_filtrado[df_filtrado['CU']=='Q2']

        col1, col2 = st.columns(2)
        with col1:
            df_nps_dist = df_q2_filtrado['NPS'].value_counts().reset_index()
            df_nps_dist.columns = ['Puntuación', 'Conteo']
            df_nps_dist = df_nps_dist.sort_values('Puntuación')
            fig_nps = px.bar(df_nps_dist, x='Puntuación', y='Conteo', text_auto=True,
                           title='Distribución de probabilidad de recomendación',
                           template=template, color_discrete_sequence=[COLOR_Q1])
            fig_nps.update_layout(xaxis=dict(tickmode='linear', dtick=1), height=400)
            st.plotly_chart(fig_nps, use_container_width=True, config=plot_config)

        with col2:
            nps_val = calc_nps(df_q2_filtrado)
            promotores = (df_q2_filtrado['NPS'] >= 9).sum() if 'NPS' in df_q2_filtrado.columns else 0
            pasivos = (df_q2_filtrado['NPS'].between(7, 8)).sum() if 'NPS' in df_q2_filtrado.columns else 0
            detractores = (df_q2_filtrado['NPS'] <= 6).sum() if 'NPS' in df_q2_filtrado.columns else 0
            total = df_q2_filtrado['NPS'].count() if 'NPS' in df_q2_filtrado.columns else 0

            if total > 0:
                st.metric("📊 NPS General", f"{nps_val:.1f}")
                st.write(f"**Promotores (9-10):** {promotores} ({promotores/total*100:.1f}%)")
                st.write(f"**Pasivos (7-8):** {pasivos} ({pasivos/total*100:.1f}%)")
                st.write(f"**Detractores (0-6):** {detractores} ({detractores/total*100:.1f}%)")
                st.write(f"**Total respuestas:** {total}")
            else:
                st.info("No hay datos de NPS disponibles")

        st.divider()

    # ============================================================
    # TABLA POR CONCESIÓN
    # ============================================================
    st.subheader("📋 Comparativa por Concesión (Q1 vs Q2)")

    df_conc = df_filtrado.groupby(['CU', 'Nombre de la Concesión'])['Total_Promedio'].mean().reset_index()
    df_conc_pivot = df_conc.pivot(index='Nombre de la Concesión', columns='CU', values='Total_Promedio').reset_index()
    df_conc_pivot.columns = ['Concesión', 'Q1', 'Q2']
    df_conc_pivot['Variación'] = df_conc_pivot['Q2'] - df_conc_pivot['Q1']
    df_conc_pivot['Estatus'] = df_conc_pivot['Variación'].apply(get_status)

    df_conc_display = df_conc_pivot.copy()
    df_conc_display['Q1'] = df_conc_display['Q1'].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
    df_conc_display['Q2'] = df_conc_display['Q2'].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
    df_conc_display['Variación'] = df_conc_display['Variación'].apply(lambda x: f"{x:+.2f}" if not pd.isna(x) else "N/A")

    st.dataframe(df_conc_display, use_container_width=True, hide_index=True)
    st.divider()

    # ============================================================
    # ANÁLISIS DE COMENTARIOS
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
                                 'quienes', 'cuyo', 'cuya', 'cuyos', 'cuyas'])
                all_words = " ".join(textos).lower()
                all_words = re.sub(r'[^\w\s]', ' ', all_words)
                all_words = re.sub(r'\d+', ' ', all_words)
                words = all_words.split()
                words = [w for w in words if len(w) > 2 and w not in stopwords]

                if len(words) > 0:
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
            st.info("No hay comentarios en esta categoría.")
        st.divider()

# ============================================================
# DATOS CRUDOS Y DESCARGA
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
