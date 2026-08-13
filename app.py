import os
import re
import json
import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. HELPER FUNCTIONS & PAGE CONFIGURATION
# -----------------------------------------------------------------------------
def normalize_name(name):
    """Normaliza nombres y razones sociales para búsquedas e inflexiones de coincidencia."""
    if not name:
        return ""
    return re.sub(r'\s+', ' ', str(name).strip().upper())

def parse_date_safe(val):
    """Parsea fechas en diversos formatos string (ISO, DD/MM/YYYY) a datetime.date."""
    if not val:
        return None
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    val_str = str(val).strip()
    m1 = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val_str)
    if m1:
        try:
            return datetime.date(int(m1.group(1)), int(m1.group(2)), int(m1.group(3)))
        except ValueError:
            pass
    m2 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', val_str)
    if m2:
        try:
            return datetime.date(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)))
        except ValueError:
            pass
    return None

def format_as_bullet_list(text):
    """Formatea textos largos o múltiples elementos (apoderados, poderes, escrituras) como listas con viñetas."""
    if not text:
        return "N/D"
    text_str = str(text).strip()
    if not text_str or text_str.upper() in ["N/A", "N/D", "X", "NONE", "NULL"]:
        return "N/D"
    
    clean_str = re.sub(r'\s+Y/O\s+', '; ', text_str, flags=re.IGNORECASE)
    parts = re.split(r'[\n;]|\s*,\s*', clean_str)
    items = [p.strip() for p in parts if p.strip() and p.strip().upper() not in ["Y", "O", "Y/O"]]
    
    if len(items) > 1:
        return "\n".join([f"- {it}" for it in items])
    return text_str

st.set_page_config(
    page_title="Control Empresas Cloud",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS & Google Fonts Injected for SaaS Corporate UI/UX Aesthetics (Cero Emojis)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    
    :root {
        --bg-main: #0b0f19;
        --bg-sidebar: #0d1322;
        --bg-card: #131b2e;
        --border-color: #1e293b;
        --accent-blue: #2563eb;
        --accent-hover: #1d4ed8;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main App Background */
    .stApp {
        background-color: var(--bg-main);
        color: var(--text-primary);
    }
    
    /* Dark Corporate Sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border-color);
    }

    /* Minimalist Profile Card in Sidebar */
    .profile-card {
        background-color: #162035;
        border: 1px solid #233252;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 16px;
    }
    .user-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: #ffffff;
    }
    .user-role {
        font-size: 0.8rem;
        color: #38bdf8;
        font-weight: 500;
        margin-top: 2px;
    }
    .led-status {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 8px;
    }
    .led-dot {
        height: 8px;
        width: 8px;
        background-color: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10b981;
    }

    /* Corporate Primary Buttons */
    .stButton button, div[data-testid="stFormSubmitButton"] button {
        background-color: var(--accent-blue) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 8px 18px !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {
        background-color: var(--accent-hover) !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4) !important;
        transform: translateY(-1px);
    }
    
    /* Container Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--bg-card) !important;
        border: 1px solid #23314d !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
        padding: 16px !important;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #182238 0%, #111827 100%);
        border: 1px solid #283756;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 8px;
    }
    .metric-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-secondary);
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.35rem;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-subtitle {
        font-size: 0.8rem;
        color: #38bdf8;
        margin-top: 4px;
    }

    /* Badge & Chip Styles */
    .badge-primary {
        background-color: #1e3a8a;
        color: #bfdbfe;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 6px;
    }
    .badge-success {
        background-color: #064e3b;
        color: #a7f3d0;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-tag {
        background-color: #312e81;
        color: #e0e7ff;
        padding: 3px 10px;
        border-radius: 14px;
        font-size: 0.78rem;
        margin-right: 4px;
    }

    /* Tab Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: var(--bg-card);
        border-radius: 8px;
        color: var(--text-secondary);
        font-weight: 600;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--accent-blue) !important;
        color: #ffffff !important;
    }

    /* Dataframe Styling */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid var(--border-color);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOGIN & AUTENTICACIÓN POR ROLES
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role_name" not in st.session_state:
    st.session_state.role_name = None

def verify_credentials(user_input, pass_input):
    """Verifica credenciales según especificaciones exactas de roles y usuarios."""
    load_dotenv()
    secrets_passwords = {}
    try:
        if hasattr(st, "secrets") and "passwords" in st.secrets:
            secrets_passwords = dict(st.secrets["passwords"])
    except Exception:
        pass
    
    u_lower = user_input.lower().strip()

    # 1. Administrador Central ('admin' o 'diego')
    admin_pass = secrets_passwords.get("admin") or secrets_passwords.get("diego") or os.getenv("ADMIN_PASSWORD", "admin")
    if u_lower in ["admin", "diego"] and pass_input == admin_pass:
        return True, "admin_central", "Administrador Central"

    # 2. Administrador ('hermana')
    hermana_pass = secrets_passwords.get("hermana") or os.getenv("HERMANA_PASSWORD", "hermana")
    if u_lower == "hermana" and pass_input == hermana_pass:
        return True, "admin", "Administrador"

    # 3. Consultor / Lector ('jefe')
    jefe_pass = secrets_passwords.get("jefe") or secrets_passwords.get("lector") or os.getenv("JEFE_PASSWORD", "jefe")
    if u_lower in ["jefe", "lector"] and pass_input == jefe_pass:
        return True, "lector", "Consultor / Lector"

    if user_input in secrets_passwords and pass_input == secrets_passwords[user_input]:
        if u_lower in ["admin", "diego"]:
            return True, "admin_central", "Administrador Central"
        elif u_lower == "hermana":
            return True, "admin", "Administrador"
        else:
            return True, "lector", "Consultor / Lector"

    return False, None, None

# Pantalla de Login si no está autenticado
if not st.session_state.authenticated:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>Control Empresas Cloud</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94a3b8;'>Acceso al Expediente Corporativo</p>", unsafe_allow_html=True)
            st.markdown("---")
            user_in = st.text_input("Usuario", placeholder="admin / diego / hermana / jefe")
            pass_in = st.text_input("Contraseña", type="password")
            submit_login = st.button("Iniciar Sesión", icon=":material/login:", use_container_width=True)

            if submit_login:
                ok, role, rname = verify_credentials(user_in.strip(), pass_in.strip())
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.username = user_in.strip()
                    st.session_state.user_role = role
                    st.session_state.role_name = rname
                    st.success(f"Sesión iniciada como {rname}")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

# -----------------------------------------------------------------------------
# 3. CONEXIÓN A SUPABASE & PROVEEDOR DE DATOS
# -----------------------------------------------------------------------------
def get_secret_or_env(key_name):
    """Obtiene una variable probando st.secrets (Streamlit Cloud) y luego os.getenv (Local)."""
    try:
        if hasattr(st, "secrets") and key_name in st.secrets:
            val = st.secrets[key_name]
            if val:
                return val
    except Exception:
        pass
    return os.getenv(key_name)

@st.cache_resource
def get_supabase_client():
    supabase_url = get_secret_or_env("SUPABASE_URL")
    supabase_key = get_secret_or_env("SUPABASE_SERVICE_KEY") or get_secret_or_env("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        return None, "No se encontraron credenciales en st.secrets ni en .env"
    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        return client, None
    except Exception as e:
        return None, str(e)

supabase, conn_error = get_supabase_client()

DATA_DIR = "data_processed"

def load_local_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

@st.cache_data(ttl=15)
def fetch_all_data():
    """Consulta Supabase con fallback transparente a JSONs locales."""
    data = {
        "empresas": [],
        "socios": [],
        "domicilios": [],
        "ventas": [],
        "poderes": [],
        "estatutos": []
    }
    
    use_supabase = False
    if supabase:
        try:
            res_emp = supabase.table("empresas").select("*").execute()
            if res_emp.data and len(res_emp.data) > 0:
                data["empresas"] = res_emp.data
                data["socios"] = supabase.table("socios").select("*").execute().data or []
                data["domicilios"] = supabase.table("domicilios").select("*").execute().data or []
                data["ventas"] = supabase.table("ventas").select("*").execute().data or []
                data["poderes"] = supabase.table("poderes").select("*").execute().data or []
                data["estatutos"] = supabase.table("estatutos").select("*").execute().data or []
                use_supabase = True
        except Exception:
            use_supabase = False

    if not use_supabase:
        data["empresas"] = load_local_json("empresas.json")
        data["socios"] = load_local_json("socios.json")
        data["domicilios"] = load_local_json("domicilios.json")
        data["ventas"] = load_local_json("ventas.json")
        data["poderes"] = load_local_json("poderes_revocacion.json") or load_local_json("poderes.json")
        data["estatutos"] = load_local_json("modificacion_estatutos.json") or load_local_json("estatutos.json")

    return data, use_supabase

def save_local_json(filename, content):
    filepath = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

# -----------------------------------------------------------------------------
# 4. NAVEGACIÓN EN SIDEBAR Y TARJETA DE USUARIO MINIMALISTA
# -----------------------------------------------------------------------------
st.sidebar.markdown("## Control Corporativo")

# Tarjeta de Usuario Minimalista en Sidebar con LED Indicator
db_status_text = "Supabase PostgreSQL" if supabase else "Archivos Locales"
st.sidebar.markdown(f"""
<div class="profile-card">
    <div class="user-name">{st.session_state.username}</div>
    <div class="user-role">{st.session_state.role_name}</div>
    <div class="led-status">
        <span class="led-dot"></span> Conectado ({db_status_text})
    </div>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("Cerrar Sesión", icon=":material/logout:", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.role_name = None
    st.rerun()

st.sidebar.markdown("---")

all_data, is_db_connected = fetch_all_data()
empresas = all_data["empresas"]

# Filtro de Modalidades por Rol usando Material Icons
if st.session_state.user_role in ["admin_central", "admin"]:
    mode_map = {
        ":material/search: Consultar Empresa": "Consultar Empresa",
        ":material/person_search: Buscador de Personas 360°": "Buscador de Personas",
        ":material/add_business: Registrar Empresa": "Registrar Empresa",
        ":material/edit: Modificar Empresa": "Modificar Empresa"
    }
else:
    mode_map = {
        ":material/search: Consultar Empresa": "Consultar Empresa",
        ":material/person_search: Buscador de Personas 360°": "Buscador de Personas"
    }

selected_mode_label = st.sidebar.radio("Navegación del Sistema:", list(mode_map.keys()))
mode = mode_map[selected_mode_label]
st.sidebar.markdown("---")

# Buscador Inteligente de Empresa para Modos de Consulta y Edición
emp_options = {}
for i, emp in enumerate(empresas):
    rs = emp.get("razon_social") or "SIN RAZÓN SOCIAL"
    rfc = emp.get("rfc") or "SIN RFC"
    label = f"{rs} | RFC: {rfc}"
    emp_options[label] = i

selected_empresa_idx = None
selected_empresa = None

if mode in ["Consultar Empresa", "Modificar Empresa"]:
    if emp_options:
        search_selection = st.sidebar.selectbox(
            "Buscar Empresa (Razón Social o RFC):",
            options=list(emp_options.keys())
        )
        selected_empresa_idx = emp_options.get(search_selection)
        if selected_empresa_idx is not None:
            selected_empresa = empresas[selected_empresa_idx]
    else:
        st.sidebar.warning("No hay empresas registradas.")

# -----------------------------------------------------------------------------
# 5. VISTA 1: CONSULTAR EMPRESA (MODO CORPORATIVO WOW)
# -----------------------------------------------------------------------------
if mode == "Consultar Empresa":
    if not selected_empresa:
        st.warning("No se ha seleccionado ninguna empresa para consultar.")
    else:
        # Header Principal
        rs = selected_empresa.get("razon_social") or "Sin Razón Social"
        rfc = selected_empresa.get("rfc") or "SIN RFC"
        tipo = selected_empresa.get("tipo_empresa") or "N/A"
        tags = selected_empresa.get("origen_tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        st.markdown(f"## {rs}")
        
        tags_html = "".join([f'<span class="badge-tag">{t}</span>' for t in tags])
        st.markdown(
            f'<span class="badge-primary">RFC: {rfc}</span>'
            f'<span class="badge-success">TIPO: {tipo}</span> '
            f'{tags_html}',
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # KPI Cards en Tarjetas Estructuradas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Escritura Pública</div>
                <div class="metric-value">{selected_empresa.get('numero_escritura') or 'N/D'}</div>
                <div class="metric-subtitle">Notaría: {selected_empresa.get('notaria') or 'N/D'}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Capital Total Fijo</div>
                <div class="metric-value">{selected_empresa.get('capital_total_fijo') or 'N/D'}</div>
                <div class="metric-subtitle">Duración: {selected_empresa.get('duracion') or 'Indefinida'}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Registro RPP</div>
                <div class="metric-value">{selected_empresa.get('rpp') or 'N/D'}</div>
                <div class="metric-subtitle">Fecha: {selected_empresa.get('fecha') or selected_empresa.get('fecha_texto') or 'N/D'}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Administrador / Gerente</div>
                <div class="metric-value">{selected_empresa.get('administrador_unico_gerente') or 'N/D'}</div>
                <div class="metric-subtitle">Comisario: {selected_empresa.get('comisario') or 'N/D'}</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Matching de registros vinculados
        emp_id = selected_empresa.get("id")
        emp_rfc = selected_empresa.get("rfc")
        emp_name_norm = normalize_name(selected_empresa.get("razon_social"))

        def is_related(rec):
            if emp_id and rec.get("empresa_id") == emp_id:
                return True
            if emp_rfc and rec.get("rfc") and rec.get("rfc") == emp_rfc:
                return True
            if emp_rfc and rec.get("rfc_empresa") and rec.get("rfc_empresa") == emp_rfc:
                return True
            if emp_name_norm:
                r_name = normalize_name(rec.get("razon_social") or rec.get("razon_social_empresa") or rec.get("denominacion_social"))
                if r_name == emp_name_norm:
                    return True
            return False

        # Pestañas con Material Icons
        t1, t2, t3, t4, t5 = st.tabs([
            ":material/badge: Constitutivos y Socios",
            ":material/pin_drop: Domicilios Fiscales",
            ":material/gavel: Poderes y Revocaciones",
            ":material/show_chart: Ventas / Cap. Variable",
            ":material/description: Reformas a Estatutos"
        ])

        with t1:
            st.subheader("Ficha de Gobierno Corporativo")
            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Domicilio Social:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('domicilio_social')))
                    st.markdown("**Apoderados:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('apoderados')))
                    st.markdown("**Delegado:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('delegado')))
                    st.markdown("**ASA Venta:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('asa_venta')))
                with col_b:
                    st.markdown("**Nº Poder / Revocación:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('numero_poder_revocacion')))
                    st.markdown("**Modificación Estatutos:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('modificacion_estatutos')))
                    st.markdown("**AFAC / CAPI:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('afac_capi')))
                    st.markdown("**Observaciones:**")
                    st.markdown(format_as_bullet_list(selected_empresa.get('observacion')))

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Estructura de Socios / Accionistas")
            
            cd1, cd2 = st.columns([2, 2])
            with cd1:
                fecha_consulta = st.date_input(
                    "Filtrar transmisiones de acciones a la fecha (Opcional):",
                    value=datetime.date.today(),
                    help="Permite consultar si hubo transmisiones de acciones registradas antes de la fecha seleccionada."
                )

            rel_socios = [s for s in all_data["socios"] if is_related(s)]
            rel_ventas = [v for v in all_data["ventas"] if is_related(v)]

            # 1. MOSTRAR SIEMPRE LA LISTA DE SOCIOS VINCULADOS
            if rel_socios:
                df_s = pd.DataFrame(rel_socios)
                cols_to_show = [c for c in ["nombre_socio", "porcentaje", "porcentaje_participacion", "tipo_socio", "origen_tabla"] if c in df_s.columns]
                rename_dict = {
                    "nombre_socio": "Socio / Accionista",
                    "porcentaje": "Participación / Acciones",
                    "porcentaje_participacion": "Participación / Acciones",
                    "tipo_socio": "Tipo de Socio",
                    "origen_tabla": "Origen / Registro"
                }
                st.dataframe(df_s[cols_to_show].rename(columns=rename_dict), use_container_width=True)
            else:
                st.info("No hay registros de socios registrados para esta empresa.")

            # 2. MOSTRAR TRANSMISIONES HASTA LA FECHA CONSULTADA
            ventas_hasta_fecha = []
            for v in rel_ventas:
                v_fec = parse_date_safe(v.get("fecha"))
                if v_fec is None or v_fec <= fecha_consulta:
                    ventas_hasta_fecha.append(v)

            if ventas_hasta_fecha:
                st.markdown(f"**Transmisiones / Asambleas de Acciones Registradas hasta el {fecha_consulta.strftime('%d/%m/%Y')} ({len(ventas_hasta_fecha)}):**")
                df_v_summary = pd.DataFrame([{
                    "Nº Escritura": v.get("numero_escritura") or "N/D",
                    "Fecha": v.get("fecha") or "N/D",
                    "Documento": v.get("documento") or "ASAMBLEA VENTA ACCIONES",
                    "Notaría": v.get("notaria") or "N/D",
                    "Detalle / Socios Cap. Variable": format_as_bullet_list(v.get("socios_capital_variable") or v.get("observaciones"))
                } for v in ventas_hasta_fecha])
                st.dataframe(df_v_summary, use_container_width=True)
            else:
                st.caption(f"No hay transmisiones de acciones adicionales registradas en o antes del {fecha_consulta.strftime('%d/%m/%Y')}.")

        with t2:
            st.subheader("Domicilios Registrados")
            rel_dom = [d for d in all_data["domicilios"] if is_related(d)]
            if rel_dom:
                df_d = pd.DataFrame(rel_dom)
                cols_to_show = [c for c in ["estado", "municipio_delegacion", "conocido", "domicilio_fiscal", "estatus"] if c in df_d.columns]
                st.dataframe(df_d[cols_to_show], use_container_width=True)
            else:
                st.info("No hay registros adicionales en esta categoría.")

        with t3:
            st.subheader("Poderes y Revocaciones Otorgados")
            col_p1, col_p2 = st.columns([2, 2])
            with col_p1:
                fecha_poderes = st.date_input(
                    "Consultar apoderados vigentes a la fecha:",
                    value=datetime.date.today(),
                    help="Filtra los poderes y revocaciones otorgados en o antes de la fecha seleccionada."
                )

            rel_pod = [p for p in all_data["poderes"] if is_related(p)]

            poderes_hasta_fecha = []
            for p in rel_pod:
                p_fec = parse_date_safe(p.get("fecha"))
                if p_fec is None or p_fec <= fecha_poderes:
                    poderes_hasta_fecha.append(p)

            st.markdown("### Apoderados Vigentes")

            apoderados_encontrados = []
            for p in poderes_hasta_fecha:
                apod_val = p.get("apoderados") or p.get("administrador_unico_gerente")
                if apod_val and apod_val.strip() not in ["N/D", "N/A", "X", "NONE", "NULL"]:
                    doc_type = p.get("documento") or "PODER OTORGADO"
                    fec_str = p.get("fecha") or "N/D"
                    esc_str = p.get("numero_escritura") or "N/D"
                    apoderados_encontrados.append({
                        "apoderado": apod_val,
                        "documento": doc_type,
                        "fecha": fec_str,
                        "escritura": esc_str
                    })

            if apoderados_encontrados:
                st.markdown(f"**Apoderados registrados en eventos de poderes al {fecha_poderes.strftime('%d/%m/%Y')}:**")
                for item in apoderados_encontrados:
                    st.info(f"Escritura {item['escritura']} ({item['fecha']}) - {item['documento']}:\n\n" + format_as_bullet_list(item['apoderado']))
            else:
                emp_apod = selected_empresa.get("apoderados") or selected_empresa.get("administrador_unico_gerente")
                st.markdown("**Apoderados registrados en la sociedad (Constitutivo / Ficha Principal):**")
                st.markdown(format_as_bullet_list(emp_apod))

            st.markdown("---")
            st.markdown("### Historial Completo de Escrituras de Poder y Revocaciones")
            if poderes_hasta_fecha:
                df_p = pd.DataFrame(poderes_hasta_fecha)
                cols_to_show = [c for c in ["tipo_empresa", "numero_escritura", "rpp", "fecha", "notaria", "documento", "administrador_unico_gerente", "apoderados", "delegado", "observaciones"] if c in df_p.columns]
                st.dataframe(df_p[cols_to_show], use_container_width=True)
            else:
                st.caption(f"No hay escrituras de poderes adicionales registradas en o antes del {fecha_poderes.strftime('%d/%m/%Y')}.")

        with t4:
            st.subheader("Ventas y Movimientos de Capital Variable")
            rel_vta = [v for v in all_data["ventas"] if is_related(v)]
            if rel_vta:
                df_v = pd.DataFrame(rel_vta)
                cols_to_show = [c for c in ["tipo_empresa", "numero_escritura", "rpp", "fecha", "notaria", "documento", "domicilio_social", "capital_total_fijo", "socios_capital_variable", "administrador_unico_gerente", "apoderados", "observaciones"] if c in df_v.columns]
                st.dataframe(df_v[cols_to_show], use_container_width=True)
            else:
                st.info("No hay registros adicionales en esta categoría.")

        with t5:
            st.subheader("Reformas a Estatutos")
            rel_est = [e for e in all_data["estatutos"] if is_related(e)]
            if rel_est:
                df_e = pd.DataFrame(rel_est)
                cols_to_show = [c for c in ["numero_escritura", "rpp", "fecha", "notaria", "documento", "domicilio_social", "capital_total_fijo", "administrador_unico_gerente", "apoderados", "observaciones"] if c in df_e.columns]
                st.dataframe(df_e[cols_to_show], use_container_width=True)
            else:
                st.info("No hay registros adicionales en esta categoría.")

# -----------------------------------------------------------------------------
# 6. VISTA NUEVA: BUSCADOR DE PERSONAS / HISTORIAL 360°
# -----------------------------------------------------------------------------
elif mode == "Buscador de Personas":
    st.markdown("## Expediente y Búsqueda por Persona (Historial 360°)")
    st.markdown("Consulte el expediente corporativo integral de cualquier socio, apoderado o directivo a través de todas las sociedades registradas.")
    st.markdown("---")

    query_person = st.text_input(
        "Ingrese el nombre o apellidos de la persona:",
        placeholder="ej. Gerardo Rejón / Ricardo Ruiz",
        help="Realiza una búsqueda cruzada en Socios, Apoderados, Administradores, Comisarios y Delegados."
    )

    if query_person and len(query_person.strip()) >= 2:
        q_norm = normalize_name(query_person)

        person_results = {
            "socios": [],
            "poderes": [],
            "cargos": []
        }

        # 1. Búsqueda en Socios
        for s in all_data["socios"]:
            nom_s = normalize_name(s.get("nombre_socio"))
            if q_norm in nom_s:
                person_results["socios"].append({
                    "Empresa / Sociedad": s.get("razon_social_empresa") or "N/D",
                    "RFC Empresa": s.get("rfc_empresa") or "N/D",
                    "Socio / Accionista": s.get("nombre_socio"),
                    "Participación / Acciones": s.get("porcentaje") or s.get("porcentaje_participacion") or "N/D",
                    "Tipo Socio": s.get("tipo_socio") or "CAPITAL_FIJO",
                    "Origen Registro": s.get("origen_tabla") or "CONSTITUCIÓN"
                })

        # 2. Búsqueda en Empresas (Ficha Principal)
        for emp in all_data["empresas"]:
            emp_name = emp.get("razon_social") or "SIN RAZÓN SOCIAL"
            rfc = emp.get("rfc") or "SIN RFC"
            
            # Admin / Gerente
            admin = emp.get("administrador_unico_gerente")
            if admin and q_norm in normalize_name(admin):
                person_results["cargos"].append({
                    "Empresa / Sociedad": emp_name,
                    "RFC Empresa": rfc,
                    "Cargo / Función": "Administrador Único / Gerente",
                    "Detalle Representante": admin,
                    "Origen Protocolización": f"Escritura {emp.get('numero_escritura') or 'Constitutiva'}"
                })
            
            # Comisario
            com = emp.get("comisario")
            if com and q_norm in normalize_name(com):
                person_results["cargos"].append({
                    "Empresa / Sociedad": emp_name,
                    "RFC Empresa": rfc,
                    "Cargo / Función": "Comisario",
                    "Detalle Representante": com,
                    "Origen Protocolización": f"Escritura {emp.get('numero_escritura') or 'Constitutiva'}"
                })

            # Delegado
            del_g = emp.get("delegado")
            if del_g and q_norm in normalize_name(del_g):
                person_results["cargos"].append({
                    "Empresa / Sociedad": emp_name,
                    "RFC Empresa": rfc,
                    "Cargo / Función": "Delegado Especial",
                    "Detalle Representante": del_g,
                    "Origen Protocolización": f"Escritura {emp.get('numero_escritura') or 'Constitutiva'}"
                })

            # Apoderados principales
            apod = emp.get("apoderados")
            if apod and q_norm in normalize_name(apod):
                person_results["poderes"].append({
                    "Empresa / Sociedad": emp_name,
                    "RFC Empresa": rfc,
                    "Tipo Poder / Facultades": "Apoderado General (Ficha Principal)",
                    "Nº Escritura": emp.get("numero_escritura") or "N/D",
                    "Notaría": emp.get("notaria") or "N/D",
                    "Fecha": emp.get("fecha") or "N/D",
                    "Detalle Facultades": apod
                })

        # 3. Búsqueda en Poderes (Eventos)
        for p in all_data["poderes"]:
            emp_name = p.get("razon_social") or "N/D"
            rfc = p.get("rfc") or "N/D"
            
            apod = p.get("apoderados")
            if apod and q_norm in normalize_name(apod):
                person_results["poderes"].append({
                    "Empresa / Sociedad": emp_name,
                    "RFC Empresa": rfc,
                    "Tipo Poder / Facultades": p.get("documento") or "PODER OTORGADO",
                    "Nº Escritura": p.get("numero_escritura") or "N/D",
                    "Notaría": p.get("notaria") or "N/D",
                    "Fecha": p.get("fecha") or "N/D",
                    "Detalle Facultades": apod
                })

            admin = p.get("administrador_unico_gerente")
            if admin and q_norm in normalize_name(admin):
                person_results["cargos"].append({
                    "Empresa / Sociedad": emp_name,
                    "RFC Empresa": rfc,
                    "Cargo / Función": "Administrador / Gerente (Escritura)",
                    "Detalle Representante": admin,
                    "Origen Protocolización": f"Escritura {p.get('numero_escritura') or 'N/D'}"
                })

        # 4. Búsqueda en Ventas / Asambleas
        for v in all_data["ventas"]:
            emp_name = v.get("razon_social") or "N/D"
            rfc = v.get("rfc") or "N/D"
            
            soc_var = v.get("socios_capital_variable") or v.get("observaciones")
            if soc_var and q_norm in normalize_name(soc_var):
                person_results["socios"].append({
                    "Empresa / Sociedad": emp_name,
                    "RFC Empresa": rfc,
                    "Socio / Accionista": q_norm,
                    "Participación / Acciones": "Movimiento Cap. Variable",
                    "Tipo Socio": "CAPITAL_VARIABLE",
                    "Origen Registro": f"Asamblea {v.get('fecha') or 'N/D'}"
                })

        # Calcular métricas consolidadas de la persona
        empresas_vinculadas = set()
        for item in person_results["socios"] + person_results["poderes"] + person_results["cargos"]:
            if item.get("Empresa / Sociedad"):
                empresas_vinculadas.add(item["Empresa / Sociedad"])

        st.markdown(f"### Expediente Corporativo de: `{query_person.upper()}`")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Empresas Vinculadas</div>
                <div class="metric-value">{len(empresas_vinculadas)}</div>
                <div class="metric-subtitle">Sociedades registradas</div>
            </div>
            """, unsafe_allow_html=True)
        with col_m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Participaciones Accionarias</div>
                <div class="metric-value">{len(person_results['socios'])}</div>
                <div class="metric-subtitle">Registros de socio</div>
            </div>
            """, unsafe_allow_html=True)
        with col_m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Poderes Otorgados</div>
                <div class="metric-value">{len(person_results['poderes'])}</div>
                <div class="metric-subtitle">Escrituras de apoderamiento</div>
            </div>
            """, unsafe_allow_html=True)
        with col_m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Cargos Corporativos</div>
                <div class="metric-value">{len(person_results['cargos'])}</div>
                <div class="metric-subtitle">Admin / Comisario / Gerente</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Pestañas de Historial 360°
        pt1, pt2, pt3 = st.tabs([
            ":material/pie_chart: Participación Accionaria",
            ":material/gavel: Poderes y Apoderamientos",
            ":material/badge: Cargos Corporativos"
        ])

        with pt1:
            st.subheader("Participación Accionaria y Registro de Socios")
            if person_results["socios"]:
                st.dataframe(pd.DataFrame(person_results["socios"]), use_container_width=True)
            else:
                st.info("No se encontraron participaciones accionarias registradas a este nombre.")

        with pt2:
            st.subheader("Poderes, Facultades y Apoderamientos")
            if person_results["poderes"]:
                st.dataframe(pd.DataFrame(person_results["poderes"]), use_container_width=True)
            else:
                st.info("No se encontraron escrituras de poder o apoderamientos a este nombre.")

        with pt3:
            st.subheader("Cargos de Administración, Gobierno y Representación")
            if person_results["cargos"]:
                st.dataframe(pd.DataFrame(person_results["cargos"]), use_container_width=True)
            else:
                st.info("No se encontraron cargos de Administración, Comisario o Gerencia a este nombre.")

    elif query_person:
        st.info("Ingrese al menos 2 caracteres para realizar la búsqueda de personas.")

# -----------------------------------------------------------------------------
# 7. VISTA 3: REGISTRAR NUEVA EMPRESA
# -----------------------------------------------------------------------------
elif mode == "Registrar Empresa":
    if st.session_state.user_role not in ["admin_central", "admin"]:
        st.error("Acceso Denegado: Su perfil no tiene permisos para crear nuevas empresas.")
    else:
        st.markdown("## Registrar Nueva Empresa en el Sistema")
        st.markdown("Complete el formulario para incorporar una nueva sociedad al expediente corporativo.")
        st.markdown("---")

        with st.form("form_nueva_empresa"):
            st.subheader("1. Datos Generales de la Sociedad")
            col1, col2, col3 = st.columns(3)
            with col1:
                new_rs = st.text_input("Razón Social / Denominación *", placeholder="EJ. ACME S.A. DE C.V.")
                new_rfc = st.text_input("RFC (12 o 13 caracteres)", placeholder="ACM990101XXX")
            with col2:
                new_tipo = st.text_input("Tipo de Empresa", placeholder="EJ. SA DE CV, S DE RL")
                new_dom_social = st.text_input("Domicilio Social", placeholder="Ciudad / Estado")
            with col3:
                new_duracion = st.text_input("Duración", value="INDEFINIDA")
                new_capital = st.text_input("Capital Total Fijo ($)", placeholder="100000")

            st.subheader("2. Datos de Protocolización")
            col4, col5, col6, col7 = st.columns(4)
            with col4:
                new_escritura = st.text_input("Nº Escritura", placeholder="12345")
            with col5:
                new_rpp = st.text_input("Registro RPP", placeholder="12345*1")
            with col6:
                new_fecha = st.date_input("Fecha de Protocolización", value=datetime.date.today())
            with col7:
                new_notaria = st.text_input("Notaría / Notario", placeholder="Notaría Nº 4")

            st.subheader("3. Gobierno Corporativo Inicial")
            col8, col9, col10, col11 = st.columns(4)
            with col8:
                new_admin = st.text_input("Administrador Único / Gerente")
            with col9:
                new_apod = st.text_input("Apoderados")
            with col10:
                new_comisario = st.text_input("Comisario")
            with col11:
                new_delegado = st.text_input("Delegado")

            new_obs = st.text_area("Observaciones Generales", placeholder="Anotaciones importantes...")

            st.subheader("4. Socios Iniciales (Hasta 5)")
            socios_inputs = []
            for i in range(1, 6):
                c_nom, c_pct = st.columns([3, 1])
                with c_nom:
                    s_nom = st.text_input(f"Nombre Socio {i}", key=f"s_nom_{i}")
                with c_pct:
                    s_pct = st.text_input(f"% Participación {i}", key=f"s_pct_{i}")
                if s_nom:
                    socios_inputs.append({"nombre_socio": s_nom.strip(), "porcentaje": s_pct.strip() if s_pct else None})

            submit_new = st.form_submit_button("Guardar Empresa en Base de Datos", icon=":material/save:", use_container_width=True)

        if submit_new:
            if not new_rs:
                st.error("El campo Razón Social es obligatorio.")
            else:
                new_empresa_dict = {
                    "razon_social": new_rs.strip().upper(),
                    "rfc": new_rfc.strip().upper() if new_rfc else None,
                    "tipo_empresa": new_tipo.strip().upper() if new_tipo else None,
                    "numero_escritura": new_escritura.strip() if new_escritura else None,
                    "rpp": new_rpp.strip() if new_rpp else None,
                    "fecha": str(new_fecha),
                    "notaria": new_notaria.strip() if new_notaria else None,
                    "domicilio_social": new_dom_social.strip() if new_dom_social else None,
                    "duracion": new_duracion.strip() if new_duracion else None,
                    "capital_total_fijo": new_capital.strip() if new_capital else None,
                    "administrador_unico_gerente": new_admin.strip() if new_admin else None,
                    "apoderados": new_apod.strip() if new_apod else None,
                    "comisario": new_comisario.strip() if new_comisario else None,
                    "delegado": new_delegado.strip() if new_delegado else None,
                    "observacion": new_obs.strip() if new_obs else None,
                    "origen_tags": ["CAPTURA_DIRECTA"]
                }

                if supabase:
                    try:
                        clean_dict = {k: v for k, v in new_empresa_dict.items() if k != "origen_tags"}
                        res = supabase.table("empresas").insert([clean_dict]).execute()
                        if res.data:
                            new_emp_id = res.data[0].get("id")
                            if new_emp_id and socios_inputs:
                                for soc in socios_inputs:
                                    soc["empresa_id"] = new_emp_id
                                supabase.table("socios").insert(socios_inputs).execute()
                    except Exception as e:
                        st.warning(f"No se pudo guardar en Supabase: {e}")

                local_empresas = load_local_json("empresas.json")
                local_empresas.append(new_empresa_dict)
                save_local_json("empresas.json", local_empresas)

                if socios_inputs:
                    local_socios = load_local_json("socios.json")
                    for soc in socios_inputs:
                        local_socios.append({
                            "rfc_empresa": new_empresa_dict["rfc"],
                            "razon_social_empresa": new_empresa_dict["razon_social"],
                            "nombre_socio": soc["nombre_socio"],
                            "porcentaje_participacion": soc["porcentaje"],
                            "tipo_socio": "INICIAL",
                            "origen_tabla": "CAPTURA_DIRECTA"
                        })
                    save_local_json("socios.json", local_socios)

                st.cache_data.clear()
                st.success(f"Empresa '{new_rs}' registrada exitosamente en el sistema.")

# -----------------------------------------------------------------------------
# 8. VISTA 4: MODIFICAR / EDITAR EMPRESA
# -----------------------------------------------------------------------------
elif mode == "Modificar Empresa":
    if st.session_state.user_role not in ["admin_central", "admin"]:
        st.error("Acceso Denegado: Su perfil no tiene permisos para editar información.")
    elif not selected_empresa:
        st.warning("Selecciona una empresa en la barra lateral para editar sus datos.")
    else:
        st.markdown(f"## Editar Empresa: {selected_empresa.get('razon_social')}")
        st.markdown("---")

        with st.form("form_editar_empresa"):
            st.subheader("Datos Generales")
            c1, c2, c3 = st.columns(3)
            with c1:
                edit_rs = st.text_input("Razón Social", value=selected_empresa.get("razon_social") or "")
                edit_rfc = st.text_input("RFC", value=selected_empresa.get("rfc") or "")
            with c2:
                edit_tipo = st.text_input("Tipo de Empresa", value=selected_empresa.get("tipo_empresa") or "")
                edit_dom = st.text_input("Domicilio Social", value=selected_empresa.get("domicilio_social") or "")
            with c3:
                edit_dur = st.text_input("Duración", value=selected_empresa.get("duracion") or "INDEFINIDA")
                edit_cap = st.text_input("Capital Total Fijo", value=selected_empresa.get("capital_total_fijo") or "")

            st.subheader("Protocolización")
            c4, c5, c6, c7 = st.columns(4)
            with c4:
                edit_esc = st.text_input("Nº Escritura", value=selected_empresa.get("numero_escritura") or "")
            with c5:
                edit_rpp = st.text_input("RPP", value=selected_empresa.get("rpp") or "")
            with c6:
                edit_fec = st.text_input("Fecha", value=selected_empresa.get("fecha") or selected_empresa.get("fecha_texto") or "")
            with c7:
                edit_not = st.text_input("Notaría", value=selected_empresa.get("notaria") or "")

            st.subheader("Gobierno Corporativo")
            c8, c9, c10, c11 = st.columns(4)
            with c8:
                edit_admin = st.text_input("Administrador Único / Gerente", value=selected_empresa.get("administrador_unico_gerente") or "")
            with c9:
                edit_apod = st.text_input("Apoderados", value=selected_empresa.get("apoderados") or "")
            with c10:
                edit_com = st.text_input("Comisario", value=selected_empresa.get("comisario") or "")
            with c11:
                edit_del = st.text_input("Delegado", value=selected_empresa.get("delegado") or "")

            edit_obs = st.text_area("Observaciones", value=selected_empresa.get("observacion") or "")

            submit_edit = st.form_submit_button("Actualizar Registro de Empresa", icon=":material/save:", use_container_width=True)

        if submit_edit:
            updated_fields = {
                "razon_social": edit_rs.strip().upper(),
                "rfc": edit_rfc.strip().upper() if edit_rfc else None,
                "tipo_empresa": edit_tipo.strip().upper() if edit_tipo else None,
                "numero_escritura": edit_esc.strip() if edit_esc else None,
                "rpp": edit_rpp.strip() if edit_rpp else None,
                "fecha": edit_fec.strip() if edit_fec else None,
                "notaria": edit_not.strip() if edit_not else None,
                "domicilio_social": edit_dom.strip() if edit_dom else None,
                "duracion": edit_dur.strip() if edit_dur else None,
                "capital_total_fijo": edit_cap.strip() if edit_cap else None,
                "administrador_unico_gerente": edit_admin.strip() if edit_admin else None,
                "apoderados": edit_apod.strip() if edit_apod else None,
                "comisario": edit_com.strip() if edit_com else None,
                "delegado": edit_del.strip() if edit_del else None,
                "observacion": edit_obs.strip() if edit_obs else None
            }

            if supabase and selected_empresa.get("id"):
                try:
                    supabase.table("empresas").update(updated_fields).eq("id", selected_empresa["id"]).execute()
                    st.success("Empresa actualizada en Supabase con éxito.")
                except Exception as e:
                    st.warning(f"No se pudo actualizar en Supabase: {e}")

            local_empresas = load_local_json("empresas.json")
            if selected_empresa_idx is not None and selected_empresa_idx < len(local_empresas):
                local_empresas[selected_empresa_idx].update(updated_fields)
                save_local_json("empresas.json", local_empresas)

            st.cache_data.clear()
            st.success("Datos actualizados correctamente en el sistema.")
