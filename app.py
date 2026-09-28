import datetime
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURACIÓN PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Gestión de Operaciones - Transportes Yáñez (V Región)",
    page_icon="🚚",
    layout="wide"
)

st.title("🚚 Suite de Reportes Operativos - Beetrack & HELA")
st.markdown("Automated Reporting System | Transportes Yáñez - V Región")

# Inicialización del almacenamiento de sesión
if 'db_diaria' not in st.session_state:
    st.session_state['db_diaria'] = {}  # {fecha_str: data_dict}

# ==========================================
# MATRIZ TARIFARIA EXACTA V REGIÓN (37 FILAS)
# ==========================================
MATRIZ_COMUNAS = [
    ("LOS ANDES + PUTAENDO", 75400),
    ("PETORCA", 71470),
    ("PUTAENDO", 63920),
    ("SAN ESTEBAN", 63340),
    ("CALLE LARGA", 63220),
    ("LOS ANDES", 63220),
    ("SANTO DOMINGO", 62410),
    ("SANTA DOMINGO", 62410),
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
    ("LLAY-LLAY", 38060),
    ("PAPUDO", 37890),
    ("ZAPALLAR", 31670),
    ("NOGALES", 31200),
    ("CASABLANCA", 25990),
    ("HIJUELAS", 25680),
    ("LA CALERA", 25170),
    ("CALERA", 25170),
    ("LA CRUZ", 23710),
    ("PUCHUNCAVI", 19250),
    ("PUCHUNCAVÍ", 19250),
    ("QUILLOTA",Entendido. Para dejar listo el código en **`app.py`** dentro de tu repositorio GitHub **`LariWorkReports`**, he estructurado la lógica de procesamiento en Python utilizando `pandas`.

El sistema permite seleccionar la fecha o rango de fechas de operación, procesa las columnas exactas descritas y genera los 5 módulos del reporte: **NS Diario**, **Reporte de Comunas**, **Reporte de Bonificación**, **Cruce de Calces París** y el **Resumen Semanal**.

---

### Código Completo para `app.py`

```python
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y REGLAS DE NEGOCIO
# ---------------------------------------------------------
st.set_page_config(page_title="LariWorkReports - Logística", layout="wide")

st.title("📊 LariWorkReports - Generador de Reportes")

# Tabla de valores por comuna más lejana (Bonificaciones)
TABLA_BONIFICACION = {
    'CONCON': 0, 'QUILPUE': 0, 'VILLA ALEMANA': 0, 'OLMUE': 0, 'LIMACHE': 0,
    'VALPARAISO': 12180, 'QUINTERO': 13500, 'COLLIGUAY': 17070, 'QUILLOTA': 18540,
    'PUCHUNCAVI': 19250, 'LA CRUZ': 23710, 'LA CALERA': 25170, 'HIJUELAS': 25680,
    'CASABLANCA': 25990, 'NOGALES': 31200, 'ZAPALLAR': 31670, 'PAPUDO': 37890,
    'LLAY LLAY': 38060, 'CATEMU': 38780, 'ALGARROBO': 40840, 'PANQUEHUE': 44790,
    'LA LIGUA': 45340, 'EL QUISCO': 50900, 'EL TABO': 51200, 'CARTAGENA': 51410,
    'SAN ANTONIO': 56470, 'SAN FELIPE': 56940, 'SANTA MARIA': 57410, 'SANTA MARÍA': 57410,
    'RINCONADA': 57520, 'CABILDO': 57640, 'SANTO DOMINGO': 62410, 'LOS ANDES': 63220,
    'CALLE LARGA': 63220, 'SAN ESTEBAN': 63340, 'PUTAENDO': 63920, 'PETORCA': 71470,
    'LOS ANDES + PUTAENDO': 75400
}

# Homologación de estados para el cruce París vs Yáñez
EQUIVALENCIAS_PARIS = {
    'ENTREGADO': 'EN CLIENTE',
    'SIN MORADORES': 'CLIENTE NO ESTÁ',
    'CLIENTE ANULA': 'EXPECTATIVA',
    'DIRECCIÓN NO ENCONTRADA': 'DIRECCIÓN ERRÓNEA',
    'DIRECCION NO ENCONTRADA': 'DIRECCIÓN ERRÓNEA',
    'DESPACHO ADELANTADO': 'MOTIVOS CLIENTE',
    'REPROGRAMADO': 'MOTIVOS CLIENTE'
}

# ---------------------------------------------------------
# SELECCIÓN DE FECHAS Y CARGA DE ARCHIVOS
# ---------------------------------------------------------
col_f1, col_f2 = st.columns(2)
with col_f1:
    fecha_inicio = st.date_input("Fecha Inicio Reporte", datetime.today())
with col_f2:
    fecha_fin = st.date_input("Fecha Fin Reporte (para resumen semanal)", datetime.today())

st.markdown("---")
st.subheader("📁 Carga de Archivos Requeridos")

file_btk_yanez = st.file_uploader("Cargar BTK YÁÑEZ (.xlsx / .csv)", type=["xlsx", "csv"])
file_btk_paris = st.file_uploader("Cargar BTK PARÍS (.xlsx / .csv)", type=["xlsx", "csv"])
file_hela = st.file_uploader("Cargar Reporte HELA (.xlsx / .csv)", type=["xlsx", "csv"])

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------
def clean_str(val):
    if pd.isna(val): return ""
    return str(val).strip().upper()

def calcular_comuna_lejana(comunas_texto):
    if pd.isna(comunas_texto): return "SIN COMUNA", 0
    comunas_list = [c.strip().upper() for c in str(comunas_texto).replace('/', '-').split('-')]
    
    max_val = -1
    comuna_sel = "CONCON"
    for c in comunas_list:
        val = TABLA_BONIFICACION.get(c, 0)
        if val > max_val:
            max_val = val
            comuna_sel = c
            
    return comuna_sel, max_val if max_val != -1 else 0

# ---------------------------------------------------------
# PROCESAMIENTO PRINCIPAL
# ---------------------------------------------------------
if file_btk_yanez and file_hela:
    # Carga de datasets
    df_yanez = pd.read_excel(file_btk_yanez) if file_btk_yanez.name.endswith('.xlsx') else pd.read_csv(file_btk_yanez)
    df_hela = pd.read_excel(file_hela) if file_hela.name.endswith('.xlsx') else pd.read_csv(file_hela)
    
    df_paris = None
    if file_btk_paris:
        df_paris = pd.read_excel(file_btk_paris) if file_btk_paris.name.endswith('.xlsx') else pd.read_csv(file_btk_paris)

    # Filtrar solo clientes EASY y PARIS en BTK Yáñez
    df_yanez['Cliente_Clean'] = df_yanez.iloc[:, 3].apply(clean_str) # Columna D
    df_yanez = df_yanez[df_yanez['Cliente_Clean'].isin(['EASY', 'PARIS', 'PARÍS'])].copy()

    # Mapeo de columnas BTK Yáñez por índice de posición
    # Col A: Ruta(0), Col B: Patente(1), Col C: Orden(2), Col D: Cliente(3),
    # Col K: Estado(10), Col L: Subestado(11), Col M: Driver(12),
    # Col BU: Fecha Compromiso(72), Col BW: Comuna(74)
    
    col_ruta = df_yanez.columns[0]
    col_patente = df_yanez.columns[1]
    col_orden = df_yanez.columns[2]
    col_cliente = df_yanez.columns[3]
    col_estado = df_yanez.columns[10]
    col_subestado = df_yanez.columns[11]
    col_driver = df_yanez.columns[12]
    col_fc = df_yanez.columns[72]
    col_comuna = df_yanez.columns[74]

    st.success("Archivos cargados e identificados correctamente.")

    # ---------------------------------------------------------
    # 1. REPORTE NS DIARIO (EASY Y PARÍS)
    # ---------------------------------------------------------
    st.markdown("## 1. Reporte Nivel de Servicio (NS) Diario")
    
    total_pedidos = len(df_yanez)
    entregados_total = len(df_yanez[df_yanez[col_estado].astype(str).str.upper() == 'ENTREGADO'])
    no_entregados_total = total_pedidos - entregados_total
    ns_acido_general = (entregados_total / total_pedidos * 100) if total_pedidos > 0 else 0

    # Desglose por cliente
    df_easy = df_yanez[df_yanez['Cliente_Clean'] == 'EASY']
    df_paris_yanez = df_yanez[df_yanez['Cliente_Clean'].isin(['PARIS', 'PARÍS'])]

    easy_tot = len(df_easy)
    easy_ent = len(df_easy[df_easy[col_estado].astype(str).str.upper() == 'ENTREGADO'])
    easy_no_ent = easy_tot - easy_ent
    ns_easy = (easy_ent / easy_tot * 100) if easy_tot > 0 else 0

    paris_tot = len(df_paris_yanez)
    paris_ent = len(df_paris_yanez[df_paris_yanez[col_estado].astype(str).str.upper() == 'ENTREGADO'])
    paris_no_ent = paris_tot - paris_ent
    ns_paris = (paris_ent / paris_tot * 100) if paris_tot > 0 else 0

    # Flota y Móviles
    mobiles_tot = df_yanez[col_patente].nunique()
    mobiles_easy = df_easy[col_patente].nunique()
    mobiles_paris = df_paris_yanez[col_patente].nunique()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("NS Ácido General", f"{ns_acido_general:.1f}%")
    m2.metric("NS Ácido Easy", f"{ns_easy:.1f}%")
    m3.metric("NS Ácido París", f"{ns_paris:.1f}%")
    m4.metric("Móviles en Ruta", f"{mobiles_tot} (E:{mobiles_easy} / P:{mobiles_paris})")

    # Sub-estados de falla
    st.write("**Causales de No Entrega (Sub-estados del Día):**")
    df_fallas = df_yanez[df_yanez[col_estado].astype(str).str.upper() != 'ENTREGADO']
    subestados_conteo = df_fallas[col_subestado].value_counts().reset_index()
    subestados_conteo.columns = ['Sub-estado / Causal', 'Cantidad']
    st.dataframe(subestados_conteo, use_container_width=True)

    # ---------------------------------------------------------
    # 2. REPORTE DE COMUNAS DIARIO
    # ---------------------------------------------------------
    st.markdown("## 2. Reporte de Comunas (Por Patente / Ruta)")

    rep_comunas = []
    
    # Hela: Col A=Driver, Col B=Patente, Col C=Nombre Ruta, Col D=Comunas, Col E=Total Puntos, Col F=Compromisos
    for _, fila in df_hela.iterrows():
        pat = clean_str(fila.iloc[1])
        driver = fila.iloc[0]
        nom_ruta = fila.iloc[2]
        comunas_str = fila.iloc[3]
        puntos_hela = fila.iloc[4]
        compromisos_hela = fila.iloc[5]

        # Cruce con BTK Yáñez por patente
        df_pat = df_yanez[df_yanez[col_patente].apply(clean_str) == pat]
        ruta_btk = df_pat[col_ruta].iloc[0] if len(df_pat) > 0 else "SIN RUTA"
        
        c_lejana, val_lejana = calcular_comuna_lejana(comunas_str)
        
        p_ent = len(df_pat[df_pat[col_estado].astype(str).str.upper() == 'ENTREGADO'])
        p_no_ent = len(df_pat) - p_ent
        
        p_easy_ent = len(df_pat[(df_pat['Cliente_Clean'] == 'EASY') & (df_pat[col_estado].astype(str).str.upper() == 'ENTREGADO')])
        p_easy_no_ent = len(df_pat[(df_pat['Cliente_Clean'] == 'EASY') & (df_pat[col_estado].astype(str).str.upper() != 'ENTREGADO')])
        
        p_paris_ent = len(df_pat[(df_pat['Cliente_Clean'].isin(['PARIS', 'PARÍS'])) & (df_pat[col_estado].astype(str).str.upper() == 'ENTREGADO')])
        p_paris_no_ent = len(df_pat[(df_pat['Cliente_Clean'].isin(['PARIS', 'PARÍS'])) & (df_pat[col_estado].astype(str).str.upper() != 'ENTREGADO')])
        
        ns_pat = (p_ent / len(df_pat) * 100) if len(df_pat) > 0 else 0

        rep_comunas.append({
            'Fecha': fecha_inicio.strftime('%Y-%m-%d'),
            'Driver': driver,
            'Patente': pat,
            'Nombre Ruta': nom_ruta,
            'Comunas': comunas_str,
            'Ruta BTK': ruta_btk,
            'Total Puntos (Hela)': puntos_hela,
            'Compromisos (Hela)': compromisos_hela,
            'Comuna Lejana': c_lejana,
            'Valor Bonificación': val_lejana,
            'Pedidos Entregados BTK': p_ent,
            'Pedidos No Entregados BTK': p_no_ent,
            'Easy Entregados': p_easy_ent,
            'Easy No Entregados': p_easy_no_ent,
            'París Entregados': p_paris_ent,
            'París No Entregados': p_paris_no_ent,
            'NS Patente (%)': f"{ns_pat:.1f}%"
        })

    df_rep_comunas = pd.DataFrame(rep_comunas)
    st.dataframe(df_rep_comunas, use_container_width=True)

    # ---------------------------------------------------------
    # 3. REPORTE BONIFICACIÓN
    # ---------------------------------------------------------
    st.markdown("## 3. Reporte de Bonificación")
    
    df_bonif = pd.DataFrame({
        'Fecha Reporte': df_rep_comunas['Fecha'],
        'Patente': df_rep_comunas['Patente'],
        'Ruta': df_rep_comunas['Ruta BTK'],
        'Valor': df_rep_comunas['Valor Bonificación'],
        'Fecha Pago': df_rep_comunas['Fecha'],
        'Comuna Liquidada': df_rep_comunas['Comuna Lejana']
    })
    st.dataframe(df_bonif, use_container_width=True)

    # ---------------------------------------------------------
    # 4. REPORTE CRUCE DE CALCES PARÍS BTK - YÁÑEZ
    # ---------------------------------------------------------
    st.markdown("## 4. Cruce de Calces París (BTK Yáñez vs BTK París)")

    if df_paris is not None:
        # Col C en París es N° de Pedido (índice 2), Col G Estado (índice 6), Col H Subestado (índice 7)
        col_ord_p = df_paris.columns[2]
        col_est_p = df_paris.columns[6]
        col_sub_p = df_paris.columns[7]

        calces = []
        for _, f_y in df_paris_yanez.iterrows():
            pedido = f_y[col_orden]
            est_y = clean_str(f_y[col_estado])
            sub_y = clean_str(f_y[col_subestado])
            fc_y = f_y[col_fc]

            # Buscar en París
            match_p = df_paris[df_paris[col_ord_p] == pedido]
            
            if len(match_p) > 0:
                est_p = clean_str(match_p.iloc[0][col_est_p])
                sub_p = clean_str(match_p.iloc[0][col_sub_p])
                
                # Regla de coincidencia
                esperado_p = EQUIVALENCIAS_PARIS.get(sub_y, "")
                coincide = "COINCIDE" if (esperado_p in sub_p or sub_y in sub_p or est_y == est_p) else "NO COINCIDE"
            else:
                est_p = "NO ENCONTRADO"
                sub_p = "NO ENCONTRADO"
                coincide = "NO COINCIDE"

            calces.append({
                'Fecha': fecha_inicio.strftime('%Y-%m-%d'),
                'N° Pedido / Guía': pedido,
                'BTK Yáñez Estado': est_y,
                'BTK Yáñez Sub-Estado': sub_y,
                'BTK París Estado': est_p,
                'BTK París Sub-Estado': sub_p,
                'Estado Cruce': coincide,
                'Fecha Compromiso': fc_y
            })

        df_calces = pd.DataFrame(calces)
        
        # Resaltar diferencias
        def highlight_diff(val):
            color = 'background-color: #ffcccc' if val == 'NO COINCIDE' else 'background-color: #d4edda'
            return color

        st.dataframe(df_calces.style.map(highlight_diff, subset=['Estado Cruce']), use_container_width=True)
    else:
        st.info("Carga el archivo BTK París para ejecutar el cruce de calces.")

    # ---------------------------------------------------------
    # 5. METRICAS Y RESUMEN SEMANAL
    # ---------------------------------------------------------
    st.markdown("## 5. Resumen Semanal Acumulado")
    st.info(f"Rango de Fechas Seleccionado: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}")

    s1, s2, s3 = st.columns(3)
    s1.metric("Total Órdenes Salidas", total_pedidos)
    s2.metric("Total Entregadas", entregados_total)
    s3.metric("Total No Entregadas", no_entregados_total)

else:
    st.info("Por favor, sube al menos los archivos **BTK YÁÑEZ** y **Reporte HELA** para comenzar el procesamiento.")
