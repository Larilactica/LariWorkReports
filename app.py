import datetime
import io
import re
import unicodedata
import json
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# =====================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y SUPABASE
# =====================================================================
st.set_page_config(
    page_title="Gestión de Operaciones Lari",
    page_icon="🐈‍⬛",
    layout="wide"
)

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("Error al conectar con Supabase. Verifica tus secretos en Streamlit Cloud.")
    st.stop()


# =====================================================================
# 2. SEGURIDAD Y ACCESO (TEMA ESPACIAL 🚀)
# =====================================================================
if "APP_PASSWORD" not in st.secrets:
    st.error("Falta configurar la variable 'APP_PASSWORD' en los Secrets de Streamlit Cloud.")
    st.stop()

PASSWORD_SECRETA = st.secrets["APP_PASSWORD"]

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        # Inyección de CSS para la Estética Espacial
        st.markdown(
            """
            <style>
            /* Fondo de galaxia/espacio profundo */
            .stApp {
                background: radial-gradient(ellipse at bottom, #1B2735 0%, #090A0F 100%) !important;
                color: #E0E6ED;
            }

            /* Título principal con brillo neón estelar */
            .stApp h1 {
                color: #A0C4FF !important;
                text-shadow: 0 0 10px rgba(160, 196, 255, 0.6), 0 0 20px rgba(108, 92, 231, 0.4);
                font-weight: 700;
            }

            /* Subtítulos */
            .stApp h3, .stApp p, .stApp label {
                color: #D6E4FF !important;
            }

            /* Estilo del campo de texto de contraseña */
            .stTextInput input {
                background-color: rgba(15, 23, 42, 0.8) !important;
                color: #00F5FF !important;
                border: 1px solid #4834D4 !important;
                border-radius: 10px !important;
                box-shadow: 0 0 10px rgba(72, 52, 212, 0.3);
            }

            .stTextInput input:focus {
                border-color: #00F5FF !important;
                box-shadow: 0 0 15px rgba(0, 245, 255, 0.6) !important;
            }

            /* Botón con degradado espacial e iluminación */
            .stButton > button {
                width: 100%;
                background: linear-gradient(135deg, #6C5CE7 0%, #4834D4 50%, #00D2D3 100%) !important;
                color: #FFFFFF !important;
                font-weight: bold !important;
                border-radius: 12px !important;
                border: none !important;
                padding: 12px 24px !important;
                box-shadow: 0 0 15px rgba(108, 92, 231, 0.5);
                transition: all 0.3s ease-in-out !important;
            }

            .stButton > button:hover {
                transform: translateY(-2px) scale(1.02);
                box-shadow: 0 0 25px rgba(0, 245, 255, 0.8) !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Contenido de la pantalla de acceso espacial
        st.title("🚀 Control de Misión - Reportes Naves 🪐")
        st.markdown("### 🌌 Estación de Autenticación Intergaláctica")
        st.caption("Ingresa la clave de seguridad para iniciar despegue hacia la Suite de Reportes.")

        password_input = st.text_input("🔑 Clave de Acceso Espacial", type="password")
        
        if st.button("🛸 Iniciar Despegue"):
            if password_input == PASSWORD_SECRETA:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Clave incorrecta. Acceso denegado por el centro de comando espacial.")
        return False
    return True

if not check_password():
    st.stop()
# =====================================================================
# 3. REGLAS DE NEGOCIO Y MATRIZ DE COMUNAS
# =====================================================================
TARIFAS_BASE = {
    "LOS ANDES + PUTAENDO": 75400, "PETORCA": 71470, "PUTAENDO": 63920,
    "SAN ESTEBAN": 63340, "CALLE LARGA": 63220, "LOS ANDES": 63220,
    "SANTO DOMINGO": 62410, "CABILDO": 57640, "RINCONADA": 57520,
    "SANTA MARIA": 57410, "SAN FELIPE": 56940, "SAN ANTONIO": 56470,
    "CARTAGENA": 51410, "EL TABO": 51200, "EL QUISCO": 50900,
    "LA LIGUA": 45340, "PANQUEHUE": 44790, "ALGARROBO": 40840,
    "CATEMU": 38780, "LLAY LLAY": 38060, "LLAYLLAY": 38060, "LLAY-LLAY": 38060,
    "PAPUDO": 37890, "ZAPALLAR": 31670, "NOGALES": 31200,
    "CASABLANCA": 25990, "HIJUELAS": 25680, "LA CALERA": 25170,
    "LA CRUZ": 23710, "PUCHUNCAVI": 19250, "QUILLOTA": 18540,
    "COLLIGUAY": 17070, "QUINTERO": 13500, "VALPARAISO": 12180,
    "CONCON": 0, "CON CON": 0, "QUILPUE": 0, "VILLA ALEMANA": 0,
    "OLMUE": 0, "LIMACHE": 0,
}
COMBO = "LOS ANDES + PUTAENDO"
ESTADOS_GESTIONADOS = {"ENTREGADO", "RECOGIDO"}

REGLAS_CALCE = [
    ("SIN MORADORES", "CLIENTE NO ESTA"),
    ("CLIENTE ANULA", "EXPECTATIVA"),
    ("DIRECCION NO ENCONTRADA", "DIRECCION ERRONEA"),
    ("DESPACHO ADELANTADO", "MOTIVOS CLIENTE"),
    ("REPROGRAMADO", "MOTIVOS CLIENTE"),
]

# =====================================================================
# 4. UTILIDADES Y NORMALIZACIÓN DE TEXTO
# =====================================================================
def limpiar_texto(texto):
    if texto is None or pd.isna(texto):
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.upper().replace(".", "").replace(",", "")
    return re.sub(r"\s+", " ", t).strip()

def txt(serie):
    s = serie.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    return s.replace({"nan": "", "None": "", "NaT": "", "<NA>": ""})

def clave_patente(p):
    return re.sub(r"[\s\-\.]", "", str(p).upper())

def pct(a, b):
    return (a / b * 100) if b else 0.0

def fmt_pct(x):
    return f"{x:.2f}".replace(".", ",") + " %"

TARIFAS = {limpiar_texto(k): v for k, v in TARIFAS_BASE.items()}
NOMBRES_PARCIAL = sorted([n for n in TARIFAS if n != COMBO], key=len, reverse=True)

def obtener_tarifa_comuna(comuna_str):
    c = limpiar_texto(comuna_str)
    if not c:
        return None
    if c in TARIFAS:
        return c, TARIFAS[c]
    for n in NOMBRES_PARCIAL:
        if re.search(rf"\b{re.escape(n)}\b", c):
            return n, TARIFAS[n]
    return None

def comuna_mas_lejana(comunas_texto):
    texto = "" if comunas_texto is None or pd.isna(comunas_texto) else str(comunas_texto)
    encontrados, desconocidas = [], []
    for item in re.split(r"[,;/]", texto):
        if not limpiar_texto(item):
            continue
        r = obtener_tarifa_comuna(item)
        if r:
            encontrados.append(r)
        else:
            desconocidas.append(item.strip())
    nombres = {n for n, _ in encontrados}
    if "LOS ANDES" in nombres and "PUTAENDO" in nombres:
        encontrados.append((COMBO, TARIFAS[COMBO]))
    if not encontrados:
        return "CONCON", 0, desconocidas
    nombre, valor = max(encontrados, key=lambda x: x[1])
    return nombre, valor, desconocidas

# =====================================================================
# 5. MAPEO DINÁMICO DE COLUMNAS (SOPORTE ROBUSTO A CAMBIOS DE EXCEL)
# =====================================================================
def buscar_columna(df, palabras_clave, indice_defecto):
    cols_clean = [limpiar_texto(col) for col in df.columns]
    for kw in palabras_clave:
        kw_clean = limpiar_texto(kw)
        for idx, col_name in enumerate(cols_clean):
            if kw_clean in col_name:
                return df.iloc[:, idx]
    if df.shape[1] > indice_defecto:
        return df.iloc[:, indice_defecto]
    return pd.Series([None] * len(df), index=df.index)

def preparar_btk(df):
    b = pd.DataFrame(index=df.index)
    b["RUTA"] = txt(buscar_columna(df, ["Ruta", "Nombre Ruta"], 0))
    b["PATENTE"] = txt(buscar_columna(df, ["Patente", "Móvil", "Vehículo"], 1)).str.upper()
    b["PAT_KEY"] = b["PATENTE"].map(clave_patente)
    b["ORDEN"] = txt(buscar_columna(df, ["Orden", "Pedido", "Guia", "Tracking"], 2))
    b["CLIENTE_TXT"] = txt(buscar_columna(df, ["Cliente", "Nombre Cliente"], 3))
    b["CLIENTE"] = b["CLIENTE_TXT"].map(limpiar_texto)
    b["ESTADO_TXT"] = txt(buscar_columna(df, ["Estado Guia", "Estado"], 10))
    b["ESTADO"] = b["ESTADO_TXT"].map(limpiar_texto)
    b["SUBESTADO"] = txt(buscar_columna(df, ["Subestado", "Sub Estado", "Sub-estado"], 11))
    b["SUB_CLEAN"] = b["SUBESTADO"].map(limpiar_texto)
    b["USUARIO"] = txt(buscar_columna(df, ["Usuario", "Driver", "Conductor"], 12))
    
    col_fcomp = buscar_columna(df, ["Compromiso", "Fecha Compromiso", "F_Comp"], 72)
    b["F_COMP"] = pd.to_datetime(col_fcomp, errors="coerce", dayfirst=True, format="mixed").dt.date
    
    b["COMUNA"] = txt(buscar_columna(df, ["Comuna", "Ciudad"], 74))
    b["ES_EASY"] = b["CLIENTE"].str.contains("EASY", na=False)
    b["ES_PARIS"] = b["CLIENTE"].str.contains("PARIS", na=False)
    b["ENTREGADO"] = b["ESTADO"].isin(ESTADOS_GESTIONADOS)
    b = b[b["PAT_KEY"].ne("") | b["ORDEN"].ne("")]
    return b.reset_index(drop=True)

# =====================================================================
# 6. EXPORTADORES (PDF Y EXCEL)
# =====================================================================
def a_excel(hojas):
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    usados = set()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            if df is None or df.empty:
                continue
            n = re.sub(r"[\[\]\:\*\?\/\\]", "-", str(nombre))[:31]
            base, i = n, 2
            while n in usados:
                n = f"{base[:28]}_{i}"
                i += 1
            usados.add(n)
            df.to_excel(writer, sheet_name=n, index=False)
            ws = writer.sheets[n]
            ws.freeze_panes = "A2"
            if ws.max_row > 1 and ws.max_column >= 1:
                ws.auto_filter.ref = ws.dimensions
            for celda in ws[1]:
                celda.font = Font(bold=True)
                celda.fill = PatternFill("solid", fgColor="E9EDF2")
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
    return buf.getvalue()

def pdf_ns(m, sub_df):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    fecha_str = datetime.date.fromisoformat(str(m["fecha"])).strftime("%d/%m/%Y")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=estilos["Title"], alignment=0, fontSize=16, spaceAfter=4)
    seccion = ParagraphStyle("seccion", parent=estilos["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4)

    def tabla(datos, negrita_ultima=False):
        t = Table(datos, repeatRows=1, hAlign="LEFT")
        est = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EDF2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C0CC")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        if negrita_ultima:
            est.append(("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"))
        t.setStyle(TableStyle(est))
        return t

    historia = [Paragraph(f"Informe de Nivel de Servicio | {fecha_str}", titulo)]
    
    # Acid NS
    historia.append(Paragraph("1. Nivel de Servicio Ácido", seccion))
    datos_acid = [
        ["Ámbito", "Total Órdenes", "Entregados", "NS Ácido (%)"],
        ["General", str(m["tot_acid_gen"]), str(m["ent_acid_gen"]), fmt_pct(m["ns_acid_gen"])],
        ["Easy", str(m["tot_acid_easy"]), str(m["ent_acid_easy"]), fmt_pct(m["ns_acid_easy"])],
        ["París", str(m["tot_acid_paris"]), str(m["ent_acid_paris"]), fmt_pct(m["ns_acid_paris"])]
    ]
    historia.append(tabla(datos_acid))

    # Flota
    historia.append(Paragraph("2. Flota y Móviles en Ruta", seccion))
    datos_flota = [
        ["Indicador", "Cantidad"],
        ["Total Móviles en Ruta", str(m["q_moviles_gen"])]
    ]
    historia.append(tabla(datos_flota))

    # Sub-estados
    historia.append(Paragraph("3. Sub-estados de No Entrega", seccion))
    datos_sub = [["Sub-estado", "Cantidad"]]
    tot_f = 0
    if sub_df is not None and not sub_df.empty:
        for _, fila in sub_df.iterrows():
            datos_sub.append([str(fila.iloc[0]), str(int(fila.iloc[1]))])
            tot_f += int(fila.iloc[1])
    datos_sub.append(["Total No Entregados", str(tot_f)])
    historia.append(tabla(datos_sub, negrita_ultima=True))

    doc.build(historia)
    return buf.getvalue()

# =====================================================================
# 7. INTERFAZ EN STREAMLIT
# =====================================================================
st.title(" 🐾 Suite de Reportes Operativos - Lari ")

tabs = st.tabs([
    "1. NS Diario (Easy & París)", 
    "2. Reporte Comunas", 
    "3. Reporte Bonificación", 
    "4. Cruce de Calces París", 
    "5. Consolidado Semanal/Rango"
])

# ---------------------------------------------------------------------
# TAB 1: NS DIARIO
# ---------------------------------------------------------------------
with tabs[0]:
    st.header("1. Reporte Nivel de Servicio (NS) Diario")
    fecha_ns = st.date_input("Fecha a la que corresponde este archivo BTK", datetime.date.today(), key="f_ns")
    file_btk_yanez = st.file_uploader("Cargar Archivo BTK YÁÑEZ (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_btk_main")

    if file_btk_yanez and st.button("Procesar y Guardar NS Diario en Supabase", key="b_proc_ns"):
        df_raw = pd.read_excel(file_btk_yanez) if file_btk_yanez.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file_btk_yanez)
        b = preparar_btk(df_raw)

        f = b[b["ES_EASY"] | b["ES_PARIS"]]
        easy = f[f["ES_EASY"]]
        paris = f[f["ES_PARIS"]]

        tot_acid_easy = len(easy)
        ent_acid_easy = int(easy["ENTREGADO"].sum())
        ns_acid_easy = pct(ent_acid_easy, tot_acid_easy)

        tot_acid_paris = len(paris)
        ent_acid_paris = int(paris["ENTREGADO"].sum())
        ns_acid_paris = pct(ent_acid_paris, tot_acid_paris)

        tot_acid_gen = tot_acid_easy + tot_acid_paris
        ent_acid_gen = ent_acid_easy + ent_acid_paris
        noent_acid_gen = tot_acid_gen - ent_acid_gen
        ns_acid_gen = pct(ent_acid_gen, tot_acid_gen)

        q_moviles_gen = int(f.loc[f["PAT_KEY"].ne(""), "PAT_KEY"].nunique())

        noent = f[~f["ENTREGADO"]]
        sub_dict = noent["SUBESTADO"].replace("", "(sin sub-estado)").value_counts().to_dict()

        row_ns = {
            "fecha": str(fecha_ns),
            "tot_acid_gen": tot_acid_gen,
            "ent_acid_gen": ent_acid_gen,
            "noent_acid_gen": noent_acid_gen,
            "ns_acid_gen": float(ns_acid_gen),
            "tot_acid_easy": tot_acid_easy,
            "ent_acid_easy": ent_acid_easy,
            "ns_acid_easy": float(ns_acid_easy),
            "tot_acid_paris": tot_acid_paris,
            "ent_acid_paris": ent_acid_paris,
            "ns_acid_paris": float(ns_acid_paris),
            "q_moviles_gen": q_moviles_gen,
            "subestados": sub_dict
        }

        supabase.table("reporte_ns_diario").upsert(row_ns).execute()
        st.success(f"¡Datos guardados exitosamente en Supabase para el día {fecha_ns.strftime('%d/%m/%Y')}!")

        # Visualización
        m1, m2, m3 = st.columns(3)
        m1.metric("NS Ácido General", f"{ns_acid_gen:.2f}%", f"Total: {tot_acid_gen}")
        m2.metric("NS Ácido Easy", f"{ns_acid_easy:.2f}%", f"Ent: {ent_acid_easy}")
        m3.metric("NS Ácido París", f"{ns_acid_paris:.2f}%", f"Ent: {ent_acid_paris}")

        sub_df = pd.DataFrame(list(sub_dict.items()), columns=["Sub-estado No Entrega", "Cantidad"])
        st.dataframe(sub_df, use_container_width=True)

        pdf_bytes = pdf_ns(row_ns, sub_df)
        st.download_button("📥 Descargar Reporte PDF", data=pdf_bytes, file_name=f"NS_Diario_{fecha_ns}.pdf", mime="application/pdf")

# ---------------------------------------------------------------------
# TAB 2: REPORTE COMUNAS
# ---------------------------------------------------------------------
with tabs[1]:
    st.header("2. Reporte de Comunas (HELA vs BTK)")
    fecha_archivo_com = st.date_input("Fecha a la que corresponde este archivo", datetime.date.today(), key="f_com_arch")

    c1, c2 = st.columns(2)
    with c1:
        file_hela = st.file_uploader("Cargar Reporte HELA (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_hela")
    with c2:
        file_btk_com = st.file_uploader("Cargar BTK YÁÑEZ para Comunas (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_btk_com")

    if file_hela and file_btk_com and st.button("Procesar y Guardar Comunas en Supabase", key="b_proc_com"):
        df_h = pd.read_excel(file_hela) if file_hela.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file_hela)
        df_b_raw = pd.read_excel(file_btk_com) if file_btk_com.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file_btk_com)
        b = preparar_btk(df_b_raw)

        filas_db = []
        for idx, row in df_h.iterrows():
            pat_raw = row.iloc[1]
            if pd.isna(pat_raw) or not str(pat_raw).strip():
                continue
            patente = str(pat_raw).upper().strip()
            clave = clave_patente(patente)
            bp = b[b["PAT_KEY"] == clave]

            comuna_h, valor, des = comuna_mas_lejana(row.iloc[3])
            easy = bp[bp["ES_EASY"]]
            paris = bp[bp["ES_PARIS"]]
            tot = len(bp)
            ent = int(bp["ENTREGADO"].sum())
            ent_easy = int(easy["ENTREGADO"].sum())
            ent_paris = int(paris["ENTREGADO"].sum())

            filas_db.append({
                "fecha": str(fecha_archivo_com),
                "driver": str(row.iloc[0]),
                "patente": patente,
                "nombre_ruta": str(row.iloc[2]),
                "comunas": str(row.iloc[3]),
                "ruta_btk": str(bp["RUTA"].iloc[0]) if tot > 0 else "SIN RUTA BTK",
                "total_puntos": int(row.iloc[4]) if pd.notna(row.iloc[4]) else 0,
                "compromisos": int(row.iloc[5]) if pd.notna(row.iloc[5]) else 0,
                "comuna_lejana": comuna_h,
                "valor": valor,
                "entregados_btk": ent,
                "no_entregados_btk": tot - ent,
                "entregados_easy": ent_easy,
                "no_entregados_easy": len(easy) - ent_easy,
                "entregados_paris": ent_paris,
                "no_entregados_paris": len(paris) - ent_paris,
                "ns_patente": float(round(pct(ent, tot), 2))
            })

        supabase.table("detalle_comunas").delete().eq("fecha", str(fecha_archivo_com)).execute()
        supabase.table("detalle_comunas").insert(filas_db).execute()
        st.success(f"¡Reporte de Comunas del {fecha_archivo_com.strftime('%d/%m/%Y')} guardado en Supabase!")

    st.markdown("---")
    st.subheader("🔍 Consultar Comunas por Rango de Fechas")
    rc1, rc2 = st.columns(2)
    with rc1:
        f_ini_c = st.date_input("Desde Fecha", datetime.date.today(), key="fi_c")
    with rc2:
        f_fin_c = st.date_input("Hasta Fecha", datetime.date.today(), key="ff_c")

    if st.button("Consultar Comunas", key="b_show_com"):
        res = supabase.table("detalle_comunas").select("*").gte("fecha", str(f_ini_c)).lte("fecha", str(f_fin_c)).execute()
        if res.data:
            df_res = pd.DataFrame(res.data)
            df_res['fecha'] = pd.to_datetime(df_res['fecha']).dt.strftime('%d/%m/%Y')
            st.session_state['ultimo_rep_comunas'] = df_res
            st.dataframe(df_res, use_container_width=True)
            
            excel_bytes = a_excel({"Reporte Comunas": df_res})
            st.download_button("📥 Descargar Excel Comunas", data=excel_bytes, file_name=f"Comunas_{f_ini_c}_al_{f_fin_c}.xlsx")
        else:
            st.warning("No hay datos cargados para el rango de fechas seleccionado.")

# ---------------------------------------------------------------------
# TAB 3: REPORTE BONIFICACIÓN
# ---------------------------------------------------------------------
with tabs[2]:
    st.header("3. Reporte de Bonificación")
    st.markdown("Extracto listo para liquidación basado en la consulta realizada en la Pestaña 2.")

    if 'ultimo_rep_comunas' in st.session_state and not st.session_state['ultimo_rep_comunas'].empty:
        df_src = st.session_state['ultimo_rep_comunas']
        df_bonif = pd.DataFrame({
            "A: Fecha": df_src["fecha"],
            "B: Patente": df_src["patente"],
            "C: Ruta": df_src["ruta_btk"],
            "D: Valor": df_src["valor"],
            "E: Fecha Repetida": df_src["fecha"],
            "F: Comuna Pagada": df_src["comuna_lejana"]
        })
        st.dataframe(df_bonif, use_container_width=True)
        excel_bonif = a_excel({"Bonificación": df_bonif})
        st.download_button("📥 Descargar Excel Bonificaciones", data=excel_bonif, file_name="Bonificaciones_Extra.xlsx")
    else:
        st.info("Primero debes consultar un rango de fechas en la Pestaña 2 para generar este informe.")

# ---------------------------------------------------------------------
# TAB 4: CRUCE DE CALCES PARÍS
# ---------------------------------------------------------------------
with tabs[3]:
    st.header("4. Reporte Cruce de Calces París")
    fecha_calce = st.date_input("Fecha del archivo de calce", datetime.date.today(), key="f_calce")

    cy, cp = st.columns(2)
    with cy:
        f_y = st.file_uploader("Cargar BTK YÁÑEZ (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_y_cal")
    with cp:
        f_p = st.file_uploader("Cargar BTK PARÍS (Excel/CSV)", type=["xlsx", "xls", "csv"], key="u_p_cal")

    if f_y and f_p and st.button("Ejecutar y Guardar Cruce de Calces", key="b_proc_cal"):
        df_y_raw = pd.read_excel(f_y) if f_y.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_y)
        df_p_raw = pd.read_excel(f_p) if f_p.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f_p)

        by = preparar_btk(df_y_raw)
        yp = by[by["ES_PARIS"]].copy()

        p = pd.DataFrame({
            "ORDEN": txt(buscar_columna(df_p_raw, ["Orden", "Pedido", "Guía"], 2)),
            "EST_P": txt(buscar_columna(df_p_raw, ["Estado"], 6)),
            "SUB_P": txt(buscar_columna(df_p_raw, ["Subestado", "Sub Estado"], 7))
        }).drop_duplicates("ORDEN")

        m = yp.merge(p, on="ORDEN", how="left")
        res_calces = []
        for idx, row in m.iterrows():
            est_y, sub_y = row["ESTADO"], row["SUB_CLEAN"]
            est_p = limpiar_texto(row["EST_P"]) if pd.notna(row["EST_P"]) else ""
            sub_p = limpiar_texto(row["SUB_P"]) if pd.notna(row["SUB_P"]) else ""

            coincide = False
            if est_y == 'ENTREGADO' and 'EN CLIENTE' in sub_p:
                coincide = True
            elif any(a in sub_y and b in sub_p for a, b in REGLAS_CALCE):
                coincide = True
            elif sub_y != "" and sub_y == sub_p:
                coincide = True

            res_calces.append({
                "fecha": str(fecha_calce),
                "guia": row["ORDEN"],
                "btk_ty_estado": row["ESTADO_TXT"],
                "btk_ty_subestado": row["SUBESTADO"],
                "btk_paris_estado": row["EST_P"] if pd.notna(row["EST_P"]) else "NO ENCONTRADO",
                "btk_paris_subestado": row["SUB_P"] if pd.notna(row["SUB_P"]) else "NO ENCONTRADO",
                "estado_cruce": "COINCIDE" if coincide else "NO COINCIDE",
                "fecha_compromiso": str(row["F_COMP"]) if row["F_COMP"] else ""
            })

        supabase.table("cruce_calces").delete().eq("fecha", str(fecha_calce)).execute()
        supabase.table("cruce_calces").insert(res_calces).execute()
        st.success(f"¡Cruce de Calces del {fecha_calce.strftime('%d/%m/%Y')} guardado con éxito!")

    st.markdown("---")
    st.subheader("🔍 Consultar Cruce de Calces por Rango")
    k1, k2 = st.columns(2)
    with k1:
        fk_i = st.date_input("Desde Fecha", datetime.date.today(), key="fki")
    with k2:
        fk_f = st.date_input("Hasta Fecha", datetime.date.today(), key="fkf")

    if st.button("Consultar Calces", key="b_sh_cal"):
        res = supabase.table("cruce_calces").select("*").gte("fecha", str(fk_i)).lte("fecha", str(fk_f)).execute()
        if res.data:
            df_cal_res = pd.DataFrame(res.data)
            def highlight_no_match(val):
                return 'background-color: #ffcccc' if val == 'NO COINCIDE' else 'background-color: #d4edda'
            st.dataframe(df_cal_res.style.map(highlight_no_match, subset=['estado_cruce']), use_container_width=True)
            excel_calce = a_excel({"Calces Paris": df_cal_res})
            st.download_button("📥 Descargar Excel Calces", data=excel_calce, file_name="Cruce_Calces_Paris.xlsx")

# ---------------------------------------------------------------------
# TAB 5: CONSOLIDADO SEMANAL / RANGO
# ---------------------------------------------------------------------
with tabs[4]:
    st.header("5. Consolidado Semanal y Reporte por Rango")
    s1, s2 = st.columns(2)
    with s1:
        f_sem_i = st.date_input("Fecha Inicio", datetime.date.today() - datetime.timedelta(days=6), key="fsi")
    with s2:
        f_sem_f = st.date_input("Fecha Fin", datetime.date.today(), key="fsf")

    if st.button("Generar Reporte Consolidado", key="b_sem_gen"):
        res = supabase.table("reporte_ns_diario").select("*").gte("fecha", str(f_sem_i)).lte("fecha", str(f_sem_f)).execute()
        if res.data:
            dias = res.data
            tot_gen = sum(d['tot_acid_gen'] for d in dias)
            ent_gen = sum(d['ent_acid_gen'] for d in dias)
            noent_gen = sum(d['noent_acid_gen'] for d in dias)
            ns_gen = pct(ent_gen, tot_gen)

            tot_easy = sum(d['tot_acid_easy'] for d in dias)
            ent_easy = sum(d['ent_acid_easy'] for d in dias)
            ns_easy = pct(ent_easy, tot_easy)

            tot_paris = sum(d['tot_acid_paris'] for d in dias)
            ent_paris = sum(d['ent_acid_paris'] for d in dias)
            ns_paris = pct(ent_paris, tot_paris)

            st.subheader("🌐 Métricas Globales del Rango")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Órdenes a Ruta", tot_gen)
            m2.metric("Órdenes Entregadas", ent_gen)
            m3.metric("Órdenes No Entregadas", noent_gen)
            m4.metric("NS Ácido Semanal General", f"{ns_gen:.2f}%")

            c1, c2 = st.columns(2)
            c1.metric("NS Ácido Easy", f"{ns_easy:.2f}%", f"Total: {tot_easy}")
            c2.metric("NS Ácido París", f"{ns_paris:.2f}%", f"Total: {tot_paris}")

            st.markdown("---")
            st.subheader("⚠️ Ranking Consolidado de Submotivos de No Entrega")
            sub_acum = {}
            for d in dias:
                sub_dict = d.get('subestados', {})
                if isinstance(sub_dict, dict):
                    for k_sub, v_sub in sub_dict.items():
                        sub_acum[k_sub] = sub_acum.get(k_sub, 0) + v_sub

            df_rank = pd.DataFrame(list(sub_acum.items()), columns=['Causal No Entrega', 'Impacto Acumulado']).sort_values(by='Impacto Acumulado', ascending=False)
            st.dataframe(df_rank, use_container_width=True)

            excel_sem = a_excel({"Métricas Rango": pd.DataFrame(dias), "Ranking Fallas": df_rank})
            st.download_button("📥 Descargar Reporte Consolidado Completo (Excel)", data=excel_sem, file_name=f"Consolidado_{f_sem_i}_al_{f_sem_f}.xlsx")
        else:
            st.warning("No hay registros guardados en Supabase dentro de este rango de fechas.")
