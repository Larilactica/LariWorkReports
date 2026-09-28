import datetime
import pandas as pd
import streamlit as st
import io

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Gestión de Operaciones - Transportes Yáñez",
    page_icon="🚚",
    layout="wide"
)

# ==========================================
# SISTEMA DE ACCESO Y CONTRASEÑA
# ==========================================
PASSWORD_SECRETA = "Larilaxia"

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 Acceso Restringido - Transportes Yáñez")
        st.markdown("Ingresa la contraseña corporativa para acceder a la Suite de Reportes.")
        
        password_input = st.text_input("Contraseña", type="password")
        
        if st.button("Iniciar Sesión"):
            if password_input == PASSWORD_SECRETA:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# MATRIZ DE COMUNAS Y BONIFICACIONES V REGIÓN
# ==========================================
MATRIZ_COMUNAS = [
    ("LOS ANDES + PUTAENDO", 75400),
    ("PETORCA", 71470),
    ("PUTAENDO", 63920),
    ("SAN ESTEBAN", 63340),
    ("CALLE LARGA", 63220),
    ("LOS ANDES", 63220),
    ("SANTO DOMINGO", 62410),
    ("CABILDO", 57640),
    ("RINCONADA", 57520),
    ("SANTA MARIA", 57410),
    ("SANTA MARÍA", 57410),
    ("SAN FELIPE", 56940),
    ("SAN ANTONIO", 56470),
    ("CARTAGENA", 51410),
    ("EL TABO", 51200),
    ("EL QUISCO", 50900),
    ("LA LIGUA", 45340),
    ("PANQUEHUE", 44790),
    ("ALGARROBO", 40840),
    ("CATEMU", 38780),
    ("LLAY LLAY", 38060),
    ("LLAYLLAY", 38060),
    ("PAPUDO", 37890),
    ("ZAPALLAR", 31670),
    ("NOGALES", 31200),
    ("CASABLANCA", 25990),
    ("HIJUELAS", 25680),
    ("LA CALERA", 25170),
    ("LA CRUZ", 23710),
    ("PUCHUNCAVI", 19250),
    ("QUILLOTA", 18540),
    ("COLLIGUAY", 17070),
    ("QUINTERO", 13500),
    ("VALPARAISO", 12180),
    ("VALPARAÍSO", 12180),
    ("CONCON", 0),
    ("CON CON", 0),
    ("QUILPUE", 0),
    ("VILLA ALEMANA", 0),
    ("OLMUE", 0),
    ("LIMACHE", 0)
]

def limpiar_texto(texto):
    if pd.isna(texto):
        return ""
    txt = str(texto).upper().strip()
    replacements = (
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        (".", ""), (",", "")
    )
    for a, b in replacements:
        txt = txt.replace(a, b)
    return txt

def obtener_tarifa_comuna(comuna_str):
    comuna_clean = limpiar_texto(comuna_str)
    for nombre_m, tarifa in MATRIZ_COMUNAS:
        if nombre_m in comuna_clean or comuna_clean in nombre_m:
            return nombre_m, tarifa
    return "OTRA / DESCONOCIDA", 0

if 'db_diaria' not in st.session_state:
    st.session_state['db_diaria'] = {}

if 'db_comunas' not in st.session_state:
    st.session_state['db_comunas'] = {}  # {fecha_str: df_comunas}

if 'db_calces' not in st.session_state:
    st.session_state['db_calces'] = {}   # {fecha_str: df_calces}

st.title("🚚 Suite de Reportes Operativos - Transportes Yáñez")

tabs = st.tabs([
    "1. NS Diario (Easy & París)", 
    "2. Reporte Comunas", 
    "3. Reporte Bonificación", 
    "4. Cruce de Calces París", 
    "5. Consolidado Semanal/Rango"
])

# ==========================================
# TAB 1: REPORT NS DIARIO
# ==========================================
with tabs[0]:
    st.header("1. Reporte Nivel de Servicio (NS) Diario")
    fecha_ns = st.date_input("Fecha a la que corresponde este archivo BTK", datetime.date.today(), key="f_ns")
    
    file_btk_yanez = st.file_uploader("Cargar Archivo BTK YÁÑEZ (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_btk_main")
    
    st.subheader("📊 Datos Fecha Compromiso (Ingreso Manual)")
    col_e, col_p = st.columns(2)
    with col_e:
        st.markdown("**EASY - Fecha Compromiso**")
        fc_easy_tot = st.number_input("Totales FC Easy", min_value=0, value=0, key="fc_et")
        fc_easy_ent = st.number_input("Entregados FC Easy", min_value=0, value=0, key="fc_ee")
        fc_easy_noent = st.number_input("No Entregados FC Easy", min_value=0, value=0, key="fc_en")
        
        st.markdown("**EASY - Retiros**")
        ret_easy_tot = st.number_input("Totales Retiros Easy", min_value=0, value=0, key="rt_et")
        ret_easy_ent = st.number_input("Entregados Retiros Easy", min_value=0, value=0, key="rt_ee")
        
    with col_p:
        st.markdown("**PARÍS - Fecha Compromiso**")
        fc_paris_tot = st.number_input("Totales FC París", min_value=0, value=0, key="fc_pt")
        fc_paris_ent = st.number_input("Entregados FC París", min_value=0, value=0, key="fc_pe")
        fc_paris_noent = st.number_input("No Entregados FC París", min_value=0, value=0, key="fc_pn")

        st.markdown("**PARÍS - Retiros / Recogidos**")
        ret_paris_tot = st.number_input("Totales Retiros París", min_value=0, value=0, key="rt_pt")
        ret_paris_ent = st.number_input("Entregados Retiros París", min_value=0, value=0, key="rt_pe")

    if file_btk_yanez and st.button("Procesar y Guardar NS Diario", key="b_proc_ns"):
        df_btk = pd.read_excel(file_btk_yanez) if file_btk_yanez.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file_btk_yanez)
        
        col_cliente = df_btk.iloc[:, 3]
        col_estado = df_btk.iloc[:, 10]
        col_subestado = df_btk.iloc[:, 11]
        col_patente = df_btk.iloc[:, 1]
        
        df_btk['CLIENTE_CLEAN'] = col_cliente.astype(str).str.upper().str.strip()
        df_btk['ESTADO_CLEAN'] = col_estado.astype(str).str.upper().str.strip()
        
        df_filt = df_btk[df_btk['CLIENTE_CLEAN'].str.contains('EASY|PARIS|PARÍS', regex=True)].copy()
        
        ns_fc_easy = (fc_easy_ent / fc_easy_tot * 100) if fc_easy_tot > 0 else 0
        ns_fc_paris = (fc_paris_ent / fc_paris_tot * 100) if fc_paris_tot > 0 else 0
        tot_fc_gen = fc_easy_tot + fc_paris_tot
        ent_fc_gen = fc_easy_ent + fc_paris_ent
        ns_fc_gen = (ent_fc_gen / tot_fc_gen * 100) if tot_fc_gen > 0 else 0

        df_easy = df_filt[df_filt['CLIENTE_CLEAN'].str.contains('EASY')]
        df_paris = df_filt[df_filt['CLIENTE_CLEAN'].str.contains('PARIS|PARÍS')]

        tot_acid_easy = len(df_easy)
        ent_acid_easy = len(df_easy[df_easy['ESTADO_CLEAN'] == 'ENTREGADO'])
        noent_acid_easy = tot_acid_easy - ent_acid_easy
        ns_acid_easy = (ent_acid_easy / tot_acid_easy * 100) if tot_acid_easy > 0 else 0

        tot_acid_paris = len(df_paris)
        ent_acid_paris = len(df_paris[df_paris['ESTADO_CLEAN'] == 'ENTREGADO'])
        noent_acid_paris = tot_acid_paris - ent_acid_paris
        ns_acid_paris = (ent_acid_paris / tot_acid_paris * 100) if tot_acid_paris > 0 else 0

        tot_acid_gen = tot_acid_easy + tot_acid_paris
        ent_acid_gen = ent_acid_easy + ent_acid_paris
        noent_acid_gen = tot_acid_gen - ent_acid_gen
        ns_acid_gen = (ent_acid_gen / tot_acid_gen * 100) if tot_acid_gen > 0 else 0

        ns_ret_easy = (ret_easy_ent / ret_easy_tot * 100) if ret_easy_tot > 0 else 0
        ns_ret_paris = (ret_paris_ent / ret_paris_tot * 100) if ret_paris_tot > 0 else 0
        tot_ret_gen = ret_easy_tot + ret_paris_tot
        ent_ret_gen = ret_easy_ent + ret_paris_ent
        ns_ret_gen = (ent_ret_gen / tot_ret_gen * 100) if tot_ret_gen > 0 else 0

        q_moviles_gen = df_filt.iloc[:, 1].nunique()
        q_moviles_easy = df_easy.iloc[:, 1].nunique()
        q_moviles_paris = df_paris.iloc[:, 1].nunique()

        st.markdown("---")
        st.subheader(f"📈 Resultados NS del {fecha_ns.strftime('%d/%m/%Y')}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("NS Compromiso General", f"{ns_fc_gen:.2f}%")
        c2.metric("NS Compromiso Easy", f"{ns_fc_easy:.2f}%")
        c3.metric("NS Compromiso París", f"{ns_fc_paris:.2f}%")

        c4, c5, c6 = st.columns(3)
        c4.metric("NS Ácido General", f"{ns_acid_gen:.2f}%", f"Tot: {tot_acid_gen} | Ent: {ent_acid_gen}")
        c5.metric("NS Ácido Easy", f"{ns_acid_easy:.2f}%", f"Tot: {tot_acid_easy} | Ent: {ent_acid_easy}")
        c6.metric("NS Ácido París", f"{ns_acid_paris:.2f}%", f"Tot: {tot_acid_paris} | Ent: {ent_acid_paris}")

        c7, c8, c9 = st.columns(3)
        c7.metric("NS Retiros General", f"{ns_ret_gen:.2f}%")
        c8.metric("Rutas Total Móviles", q_moviles_gen)
        c9.metric("Móviles Easy / París", f"{q_moviles_easy} / {q_moviles_paris}")

        st.subheader("⚠️ Sub-estados de No Entrega del Día")
        df_noent = df_filt[df_filt['ESTADO_CLEAN'] != 'ENTREGADO']
        subest_counts = df_noent.iloc[:, 11].value_counts().reset_index()
        subest_counts.columns = ['Sub-estado No Entrega', 'Cantidad']
        st.dataframe(subest_counts, use_container_width=True)

        f_key = fecha_ns.strftime("%Y-%m-%d")
        st.session_state['db_diaria'][f_key] = {
            'fecha': fecha_ns,
            'tot_acid_gen': tot_acid_gen,
            'ent_acid_gen': ent_acid_gen,
            'noent_acid_gen': noent_acid_gen,
            'ns_acid_gen': ns_acid_gen,
            'tot_acid_easy': tot_acid_easy,
            'ent_acid_easy': ent_acid_easy,
            'ns_acid_easy': ns_acid_easy,
            'tot_acid_paris': tot_acid_paris,
            'ent_acid_paris': ent_acid_paris,
            'ns_acid_paris': ns_acid_paris,
            'q_moviles_gen': q_moviles_gen,
            'df_noent': df_noent
        }
        st.success(f"¡Día {fecha_ns.strftime('%d/%m/%Y')} guardado exitosamente en la memoria de sesión!")

# ==========================================
# TAB 2: REPORTE COMUNAS
# ==========================================
with tabs[1]:
    st.header("2. Reporte de Comunas (Cargar archivo con su fecha)")
    
    fecha_archivo_com = st.date_input("Fecha a la que corresponde este archivo de Comunas", datetime.date.today(), key="f_com_arch")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        file_hela = st.file_uploader("Cargar Reporte HELA (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_hela")
    with col_f2:
        file_btk_com = st.file_uploader("Cargar BTK YÁÑEZ para Comunas (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_btk_com")

    if file_hela and file_btk_com and st.button("Procesar y Guardar Comunas del Día", key="b_proc_com"):
        df_h = pd.read_excel(file_hela) if file_hela.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file_hela)
        df_b = pd.read_excel(file_btk_com) if file_btk_com.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file_btk_com)

        df_b['PATENTE_CLEAN'] = df_b.iloc[:, 1].astype(str).str.upper().str.strip()
        df_b['ESTADO_CLEAN'] = df_b.iloc[:, 10].astype(str).str.upper().str.strip()
        df_b['CLIENTE_CLEAN'] = df_b.iloc[:, 3].astype(str).str.upper().str.strip()

        filas_rep = []
        for idx, row in df_h.iterrows():
            driver = row.iloc[0]
            patente = str(row.iloc[1]).upper().strip()
            nom_ruta = row.iloc[2]
            comunas_hela = str(row.iloc[3])
            tot_puntos = row.iloc[4]
            compromisos = row.iloc[5]

            df_b_pat = df_b[df_b['PATENTE_CLEAN'] == patente]
            ruta_btk = df_b_pat.iloc[0, 0] if len(df_b_pat) > 0 else "SIN RUTA BTK"
            
            lista_comunas = [c.strip() for c in comunas_hela.split(',')]
            max_val = -1
            comuna_lej = "CONCON"
            for c_item in lista_comunas:
                nom_c, val_c = obtener_tarifa_comuna(c_item)
                if val_c > max_val:
                    max_val = val_c
                    comuna_lej = nom_c

            p_ent = len(df_b_pat[df_b_pat['ESTADO_CLEAN'] == 'ENTREGADO'])
            p_noent = len(df_b_pat[df_b_pat['ESTADO_CLEAN'] != 'ENTREGADO'])
            
            df_b_easy = df_b_pat[df_b_pat['CLIENTE_CLEAN'].str.contains('EASY')]
            p_ent_easy = len(df_b_easy[df_b_easy['ESTADO_CLEAN'] == 'ENTREGADO'])
            
            df_b_paris = df_b_pat[df_b_pat['CLIENTE_CLEAN'].str.contains('PARIS|PARÍS')]
            p_ent_paris = len(df_b_paris[df_b_paris['ESTADO_CLEAN'] == 'ENTREGADO'])
            p_noent_paris = len(df_b_paris[df_b_paris['ESTADO_CLEAN'] != 'ENTREGADO'])

            tot_btk_pat = len(df_b_pat)
            ns_pat = (p_ent / tot_btk_pat * 100) if tot_btk_pat > 0 else 0

            filas_rep.append({
                'A: Fecha': fecha_archivo_com.strftime("%d/%m/%Y"),
                'B: Driver': driver,
                'C: Patente': patente,
                'D: Nombre ruta': nom_ruta,
                'E: Comunas': comunas_hela,
                'F: Ruta BTK': ruta_btk,
                'G: Total puntos HELA': tot_puntos,
                'H: Compromisos HELA': compromisos,
                'I: Comuna Lejana': comuna_lej,
                'J: Valor': max_val,
                'K: Entregados BTK': p_ent,
                'L: No Entregados BTK': p_noent,
                'M: Entregados Easy BTK': p_ent_easy,
                'N: No Entregados Easy BTK': len(df_b_easy) - p_ent_easy,
                'O: Entregados París BTK': p_ent_paris,
                'P: No Entregados París BTK': p_noent_paris,
                'Q: NS Patente (%)': round(ns_pat, 2),
                '_fecha_obj': fecha_archivo_com
            })

        df_res_comunas = pd.DataFrame(filas_rep)
        f_key_com = fecha_archivo_com.strftime("%Y-%m-%d")
        st.session_state['db_comunas'][f_key_com] = df_res_comunas
        st.success(f"¡Reporte de Comunas del {fecha_archivo_com.strftime('%d/%m/%Y')} procesado y guardado con éxito!")

    # Visualizar acumulado por rango de fechas
    st.markdown("---")
    st.subheader("🔍 Consultar Comunas por Rango de Fechas")
    col_rc1, col_rc2 = st.columns(2)
    with col_rc1:
        f_ini_c = st.date_input("Desde Fecha", datetime.date.today(), key="fi_c")
    with col_rc2:
        f_fin_c = st.date_input("Hasta Fecha", datetime.date.today(), key="ff_c")

    if st.button("Mostrar Reporte Comunas del Rango", key="b_show_com"):
        if st.session_state['db_comunas']:
            dfs_match = [df for k, df in st.session_state['db_comunas'].items() if f_ini_c <= datetime.datetime.strptime(k, "%Y-%m-%d").date() <= f_fin_c]
            if dfs_match:
                df_final_com = pd.concat(dfs_match, ignore_index=True)
                st.session_state['ultimo_rep_comunas'] = df_final_com.drop(columns=['_fecha_obj'])
                st.dataframe(st.session_state['ultimo_rep_comunas'], use_container_width=True)
            else:
                st.warning("No hay registros de comunas en el rango de fechas seleccionado.")
        else:
            st.info("Aún no has procesado ningún archivo de comunas en esta sesión.")

# ==========================================
# TAB 3: REPORTE BONIFICACIÓN
# ==========================================
with tabs[2]:
    st.header("3. Reporte de Bonificación (Basado en el Rango Consultado)")
    st.markdown("Generación automática de las 6 columnas derivadas del Reporte de Comunas.")

    if 'ultimo_rep_comunas' in st.session_state and not st.session_state['ultimo_rep_comunas'].empty:
        df_c_src = st.session_state['ultimo_rep_comunas']
        
        df_bonif = pd.DataFrame({
            'Columna A (Fecha)': df_c_src['A: Fecha'],
            'Columna B (Patente)': df_c_src['C: Patente'],
            'Columna C (Ruta)': df_c_src['F: Ruta BTK'],
            'Columna D (Valor)': df_c_src['J: Valor'],
            'Columna E (Fecha Repetida)': df_c_src['A: Fecha'],
            'Columna F (Comuna Pagada)': df_c_src['I: Comuna Lejana']
        })
        
        st.dataframe(df_bonif, use_container_width=True)
    else:
        st.warning("Primero debes generar y consultar el Reporte de Comunas por Rango en la Pestaña 2.")

# ==========================================
# TAB 4: CRUCE DE CALCES PARÍS
# ==========================================
with tabs[3]:
    st.header("4. Reporte Cruce de Calces París (Cargar archivo con su fecha)")
    
    fecha_archivo_calce = st.date_input("Fecha a la que corresponde este archivo de Calce", datetime.date.today(), key="f_calce_arch")

    col_cy, col_cp = st.columns(2)
    with col_cy:
        f_yanez_calce = st.file_uploader("Cargar BTK YÁÑEZ (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_y_c")
    with col_cp:
        f_paris_calce = st.file_uploader("Cargar BTK PARÍS (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_p_c")

    if f_yanez_calce and f_paris_calce and st.button("Procesar y Guardar Calces del Día", key="b_proc_calce"):
        df_y = pd.read_excel(f_yanez_calce) if f_yanez_calce.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_yanez_calce)
        df_p = pd.read_excel(f_paris_calce) if f_paris_calce.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_paris_calce)

        df_y['CLIENTE_CLEAN'] = df_y.iloc[:, 3].astype(str).str.upper().str.strip()
        df_y_paris = df_y[df_y['CLIENTE_CLEAN'].str.contains('PARIS|PARÍS')].copy()

        df_y_paris['ORDEN_CLEAN'] = df_y_paris.iloc[:, 2].astype(str).str.strip()
        df_p['ORDEN_CLEAN'] = df_p.iloc[:, 2].astype(str).str.strip()

        res_calce = []
        for idx, row_y in df_y_paris.iterrows():
            guia = row_y['ORDEN_CLEAN']
            est_y = str(row_y.iloc[10]).strip()
            sub_y = str(row_y.iloc[11]).strip()
            f_comp = row_y.iloc[72] if len(row_y) > 72 else ""

            match_p = df_p[df_p['ORDEN_CLEAN'] == guia]

            if len(match_p) > 0:
                est_p = str(match_p.iloc[0, 6]).strip()
                sub_p = str(match_p.iloc[0, 7]).strip()
            else:
                est_p = "NO ENCONTRADO"
                sub_p = "NO ENCONTRADO"

            coincide = False
            sub_y_u = sub_y.upper()
            sub_p_u = sub_p.upper()

            if est_y.upper() == 'ENTREGADO' and 'EN CLIENTE' in sub_p_u:
                coincide = True
            elif 'SIN MORADORES' in sub_y_u and 'CLIENTE NO ESTA' in sub_p_u:
                coincide = True
            elif 'CLIENTE ANULA' in sub_y_u and 'EXPECTATIVA' in sub_p_u:
                coincide = True
            elif 'DIRECCION NO ENCONTRADA' in sub_y_u and 'DIRECCION ERRONEA' in sub_p_u:
                coincide = True
            elif ('DESPACHO ADELANTADO' in sub_y_u or 'REPROGRAMADO' in sub_y_u) and 'MOTIVOS CLIENTE' in sub_p_u:
                coincide = True
            elif sub_y_u == sub_p_u:
                coincide = True

            res_calce.append({
                'A: Fecha': fecha_archivo_calce.strftime("%d/%m/%Y"),
                'B: N° Pedido / Guía': guia,
                'C: BTK TY Estado': est_y,
                'D: BTK TY Sub Estado': sub_y,
                'E: BTK París Estado': est_p,
                'F: BTK París Sub Estado': sub_p,
                'G: Estado Cruce': 'COINCIDE' if coincide else 'NO COINCIDE',
                'H: Fecha Compromiso': f_comp,
                '_fecha_obj': fecha_archivo_calce
            })

        df_res_calce = pd.DataFrame(res_calce)
        f_key_calce = fecha_archivo_calce.strftime("%Y-%m-%d")
        st.session_state['db_calces'][f_key_calce] = df_res_calce
        st.success(f"¡Cruce de Calces del {fecha_archivo_calce.strftime('%d/%m/%Y')} guardado con éxito!")

    # Consultar Calces por Rango
    st.markdown("---")
    st.subheader("🔍 Consultar Cruce de Calces por Rango de Fechas")
    col_rcal1, col_rcal2 = st.columns(2)
    with col_rcal1:
        f_ini_cal = st.date_input("Desde Fecha", datetime.date.today(), key="fi_cal")
    with col_rcal2:
        f_fin_cal = st.date_input("Hasta Fecha", datetime.date.today(), key="ff_cal")

    if st.button("Mostrar Calces del Rango", key="b_show_cal"):
        if st.session_state['db_calces']:
            dfs_match_cal = [df for k, df in st.session_state['db_calces'].items() if f_ini_cal <= datetime.datetime.strptime(k, "%Y-%m-%d").date() <= f_fin_cal]
            if dfs_match_cal:
                df_final_cal = pd.concat(dfs_match_cal, ignore_index=True).drop(columns=['_fecha_obj'])
                
                def highlight_no_match(val):
                    color = 'background-color: #ffcccc' if val == 'NO COINCIDE' else 'background-color: #d4edda'
                    return color

                st.dataframe(df_final_cal.style.map(highlight_no_match, subset=['G: Estado Cruce']), use_container_width=True)
            else:
                st.warning("No hay registros de calces en el rango de fechas seleccionado.")
        else:
            st.info("Aún no has procesado ningún archivo de calces en esta sesión.")

# ==========================================
# TAB 5: CONSOLIDADO SEMANAL / RANGO
# ==========================================
with tabs[4]:
    st.header("5. Reporte Semanal y Rango de Fechas (Lunes a Sábado)")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        f_inicio = st.date_input("Fecha Inicio (Rango/Semana)", datetime.date.today() - datetime.timedelta(days=6), key="fi_sem")
    with col_r2:
        f_fin = st.date_input("Fecha Fin (Rango/Semana)", datetime.date.today(), key="ff_sem")

    if st.button("Generar Reporte Semanal", key="b_proc_sem"):
        if 'db_diaria' in st.session_state and st.session_state['db_diaria']:
            dias_filtrados = [
                v for k, v in st.session_state['db_diaria'].items() 
                if f_inicio <= v['fecha'] <= f_fin
            ]

            if dias_filtrados:
                tot_sem_gen = sum(d['tot_acid_gen'] for d in dias_filtrados)
                ent_sem_gen = sum(d['ent_acid_gen'] for d in dias_filtrados)
                noent_sem_gen = sum(d['noent_acid_gen'] for d in dias_filtrados)
                ns_sem_gen = (ent_sem_gen / tot_sem_gen * 100) if tot_sem_gen > 0 else 0

                tot_sem_easy = sum(d['tot_acid_easy'] for d in dias_filtrados)
                ent_sem_easy = sum(d['ent_acid_easy'] for d in dias_filtrados)
                ns_sem_easy = (ent_sem_easy / tot_sem_easy * 100) if tot_sem_easy > 0 else 0

                tot_sem_paris = sum(d['tot_acid_paris'] for d in dias_filtrados)
                ent_sem_paris = sum(d['ent_acid_paris'] for d in dias_filtrados)
                ns_sem_paris = (ent_sem_paris / tot_sem_paris * 100) if tot_sem_paris > 0 else 0

                st.subheader("🌐 Métricas Globales del Rango Seleccionado")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Órdenes Salidas a Ruta", tot_sem_gen)
                m2.metric("Órdenes Entregadas", ent_sem_gen)
                m3.metric("Órdenes No Entregadas", noent_sem_gen)
                m4.metric("NS Ácido Semanal General", f"{ns_sem_gen:.2f}%")

                c1, c2 = st.columns(2)
                c1.metric("NS Ácido Semanal Easy", f"{ns_sem_easy:.2f}%", f"Total: {tot_sem_easy}")
                c2.metric("NS Ácido Semanal París", f"{ns_sem_paris:.2f}%", f"Total: {tot_sem_paris}")

                st.markdown("---")
                st.subheader("🚛 Promedio y Totales de Flota")
                prom_moviles = sum(d['q_moviles_gen'] for d in dias_filtrados) / len(dias_filtrados)
                st.metric("Promedio Móviles Diarios en Ruta", f"{prom_moviles:.1f}")

                st.markdown("---")
                st.subheader("⚠️ Consolidado Semanal de Submotivos de No Entrega")
                dfs_noent_sem = [d['df_noent'] for d in dias_filtrados if 'df_noent' in d and not d['df_noent'].empty]
                if dfs_noent_sem:
                    df_all_noent = pd.concat(dfs_noent_sem, ignore_index=True)
                    ranking_fallas = df_all_noent.iloc[:, 11].value_counts().reset_index()
                    ranking_fallas.columns = ['Causal / Submotivo No Entrega', 'Total Impacto Acumulado']
                    st.dataframe(ranking_fallas, use_container_width=True)
                else:
                    st.info("No se registraron fallas o no entregas en los días seleccionados.")
            else:
                st.warning("No hay registros en la base de datos para el rango de fechas seleccionado.")
        else:
            st.warning("No hay datos cargados en la sesión actual.")
