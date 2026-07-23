@st.cache_data
def load_data():
    # ---------- LECTURA DE HOJAS (SIN CABECERA) ----------
    # Q1: saltamos las primeras 2 filas (fila 0 vacía, fila 1 cabecera)
    df_q1_raw = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q1',
        header=None,
        skiprows=2
    )
    # Q2: saltamos la primera fila (cabecera)
    df_q2_raw = pd.read_excel(
        'Encuesta concesiones TLV Q1 y Q2.xlsx',
        sheet_name='Calificaciones Q2',
        header=None,
        skiprows=1
    )

    # ---------- ELIMINAR FILAS DE SUBTOTAL Y VACÍAS ----------
    # Q1: usar columna 0 (ID) como identificador
    df_q1_raw = df_q1_raw.dropna(subset=[0])
    df_q1_raw = df_q1_raw[~df_q1_raw[0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q1_raw = df_q1_raw[df_q1_raw[0].astype(str).str.strip() != '']
    df_q1_raw = df_q1_raw[df_q1_raw[0].astype(str).str.isnumeric()]  # Solo IDs numéricos

    # Q2: usar columna 0 (Nombre) como identificador
    df_q2_raw = df_q2_raw.dropna(subset=[0])
    df_q2_raw = df_q2_raw[~df_q2_raw[0].astype(str).str.contains('SUBTOTAL', case=False, na=False)]
    df_q2_raw = df_q2_raw[df_q2_raw[0].astype(str).str.strip() != '']

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

    # ---------- CONSTRUIR Q1 ----------
    # Columnas fijas: 0:ID, 1:Hora inicio, 2:Hora fin, 3:Correo, 4:Nombre, 5:Concesión, 6:Área
    q1_fijas = df_q1_raw.iloc[:, 0:7].copy()
    q1_fijas.columns = ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico',
                        'Nombre', 'Nombre de la Concesión', 'Área / Cargo']
    # Preguntas: columnas 7 a 21
    q1_preg = df_q1_raw.iloc[:, 7:22].copy()
    q1_preg.columns = preguntas_cortas
    # Texto: columnas 23, 24, 25
    q1_text = df_q1_raw.iloc[:, 23:26].copy()
    q1_text.columns = ['Aciertos', 'Áreas_mejora', 'Comentarios_contacto']
    # NPS: Q1 no tiene
    q1_nps = pd.DataFrame({'NPS': [np.nan] * len(q1_fijas)})

    # ---------- CONSTRUIR Q2 ----------
    # Columnas fijas: 0:Nombre, 1:Concesión, 2:Área
    q2_fijas = df_q2_raw.iloc[:, 0:3].copy()
    q2_fijas.columns = ['Nombre', 'Nombre de la Concesión', 'Área / Cargo']
    # Preguntas: columnas 3 a 17
    q2_preg = df_q2_raw.iloc[:, 3:18].copy()
    q2_preg.columns = preguntas_cortas
    # NPS: columna 18
    q2_nps = df_q2_raw.iloc[:, 18].copy().rename('NPS')
    # Texto: columnas 20, 21, 22
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

    # ---------- HOMOLOGAR NOMBRES DE CONCESIONES ----------
    df_q1_full['Nombre de la Concesión'] = df_q1_full['Nombre de la Concesión'].replace({
        'AUNORTE': 'Vias Urbanas'
    })
    df_q2_full['Nombre de la Concesión'] = df_q2_full['Nombre de la Concesión'].replace({
        'AUNORTE': 'Vias Urbanas'
    })

    # ---------- UNIFICAR AMBOS DATAFRAMES ----------
    # Añadir columnas faltantes a Q2
    for col in ['ID', 'Hora de inicio', 'Hora de finalización', 'Correo electrónico']:
        if col not in df_q2_full.columns:
            df_q2_full[col] = np.nan

    # Reordenar columnas para que coincidan
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
