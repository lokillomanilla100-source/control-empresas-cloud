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
    # Formato YYYY-MM-DD
    m1 = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val_str)
    if m1:
        try:
            return datetime.date(int(m1.group(1)), int(m1.group(2)), int(m1.group(3)))
        except ValueError:
            pass
    # Formato DD/MM/YYYY
    m2 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', val_str)
    if m2:
        try:
            return datetime.date(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)))
        except ValueError:
            pass
    return None

st.set_page_config(
    page_title="Control Empresas Cloud",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a modern corporate dashboard aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Background */
    .stApp {
        background-color: #0e1117;
        color: #e0e6ed;
    }
    
    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, #1e2640 0%, #151b2d 100%);
        border: 1px solid #2e3a59;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 12px;
    }
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8b9bb4;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-subtitle {
        font-size: 0.8rem;
        color: #00d2ff;
        margin-top: 4px;
    }

    /* Badge / Pill Styles */
    .badge-primary {
        background-color: #1e3a8a;
        color: #93c5fd;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 6px;
    }
    .badge-success {
        background-color: #064e3b;
        color: #6ee7b7;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-tag {
        background-color: #312e81;
        color: #c7d2fe;
        padding: 3px 8px;
        border-radius: 14px;
        font-size: 0.75rem;
        margin-right: 4px;
    }

    /* Tab Header Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1a2133;
        border-radius: 8px;
        color: #a0aec0;
        font-weight: 600;
        padding: 10px 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }

    /* Dataframe Styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #2d3748;
    }

    /* Form Container */
    .stForm {
        background-color: #161e2e;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 24px;
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
    """Verifica credenciales contra st.secrets['passwords'], .env o valores por defecto."""
    load_dotenv()
    secrets_passwords = {}
    try:
        if hasattr(st, "secrets") and "passwords" in st.secrets:
            secrets_passwords = dict(st.secrets["passwords"])
    except Exception:
        pass
    
    # 1. Perfil Admin (Hermana)
    admin_pass = secrets_passwords.get("admin") or os.getenv("ADMIN_PASSWORD", "admin")
    if user_input.lower() == "admin" and pass_input == admin_pass:
        return True, "admin", "Administrador (Hermana)"

    # 2. Perfil Lector (Jefe)
    lector_pass = secrets_passwords.get("jefe") or secrets_passwords.get("lector") or os.getenv("LECTOR_PASSWORD", "jefe")
    if user_input.lower() in ["jefe", "lector"] and pass_input == lector_pass:
        return True, "lector", "Consultor / Lector (Jefe)"

    # 3. Consulta dinámica en st.secrets["passwords"]
    if user_input in secrets_passwords and pass_input == secrets_passwords[user_input]:
        role = "admin" if "admin" in user_input.lower() else "lector"
        rname = "Administrador (Hermana)" if role == "admin" else "Consultor / Lector (Jefe)"
        return True, role, rname

    return False, None, None

# Pantalla de Login si no está autenticado
if not st.session_state.authenticated:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.markdown("<h2 style='text-align: center;'>🏢 Control Empresas Cloud</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #8b9bb4;'>Inicio de Sesión al Sistema Corporativo</p>", unsafe_allow_html=True)
            st.markdown("---")
            user_in = st.text_input("Usuario", placeholder="admin / jefe")
            pass_in = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("🔑 Iniciar Sesión", use_container_width=True)

        if submit_login:
            ok, role, rname = verify_credentials(user_in.strip(), pass_in.strip())
            if ok:
                st.session_state.authenticated = True
                st.session_state.username = user_in.strip()
                st.session_state.user_role = role
                st.session_state.role_name = rname
                st.success(f"Bienvenido {rname}")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos. Verifique sus credenciales.")
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
    """Consulta la base de datos Supabase con fallback transparente a JSONs locales."""
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
# 4. NAVEGACIÓN EN SIDEBAR Y CONTROL DE ROLES
# -----------------------------------------------------------------------------
st.sidebar.markdown("# 🏢 Control Corporativo")
st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state.username}`")
st.sidebar.markdown(f"🔑 **Perfil:** `{st.session_state.role_name}`")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.role_name = None
    st.rerun()

st.sidebar.markdown("---")

all_data, is_db_connected = fetch_all_data()
empresas = all_data["empresas"]

if is_db_connected:
    st.sidebar.success("🟢 Conectado a Supabase")
else:
    st.sidebar.info("📂 Modo Archivos Local (/data_processed/)")

# Filtro de Modalidades según Rol de Usuario
if st.session_state.user_role == "lector":
    available_modes = ["🔍 Consultar Empresa"]
else:
    available_modes = ["🔍 Consultar Empresa", "➕ Registrar Nueva Empresa", "✏️ Modificar / Editar Empresa"]

mode = st.sidebar.radio("Selecciona Modalidad:", available_modes)
st.sidebar.markdown("---")

# Buscador Inteligente
emp_options = {}
for i, emp in enumerate(empresas):
    rs = emp.get("razon_social") or "SIN RAZÓN SOCIAL"
    rfc = emp.get("rfc") or "SIN RFC"
    label = f"{rs} | RFC: {rfc}"
    emp_options[label] = i

selected_empresa_idx = None
selected_empresa = None

if mode in ["🔍 Consultar Empresa", "✏️ Modificar / Editar Empresa"]:
    if emp_options:
        search_selection = st.sidebar.selectbox(
            "🔍 Buscar Empresa (Razón Social o RFC):",
            options=list(emp_options.keys())
        )
        selected_empresa_idx = emp_options.get(search_selection)
        if selected_empresa_idx is not None:
            selected_empresa = empresas[selected_empresa_idx]
    else:
        st.sidebar.warning("No hay empresas registradas.")

# -----------------------------------------------------------------------------
# 5. VISTA 1: CONSULTAR EMPRESA ("MODO WOW") CON HISTÓRICO DE SOCIOS
# -----------------------------------------------------------------------------
if mode == "🔍 Consultar Empresa":
    if not selected_empresa:
        st.warning("⚠️ No se ha seleccionado ninguna empresa para consultar.")
    else:
        # Header Principal
        rs = selected_empresa.get("razon_social") or "Sin Razón Social"
        rfc = selected_empresa.get("rfc") or "SIN RFC"
        tipo = selected_empresa.get("tipo_empresa") or "N/A"
        tags = selected_empresa.get("origen_tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        st.markdown(f"## 🏢 {rs}")
        
        tags_html = "".join([f'<span class="badge-tag">{t}</span>' for t in tags])
        st.markdown(
            f'<span class="badge-primary">RFC: {rfc}</span>'
            f'<span class="badge-success">TIPO: {tipo}</span> '
            f'{tags_html}',
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # KPI Cards
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
                <div class="metric-value" style="font-size: 1.1rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{selected_empresa.get('administrador_unico_gerente') or 'N/D'}</div>
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

        # Pestañas de detalle
        t1, t2, t3, t4, t5 = st.tabs([
            "📋 Constitutivos y Socios",
            "📍 Domicilios Fiscales",
            "⚖️ Poderes y Revocaciones",
            "📈 Ventas / Cap. Variable",
            "📜 Reformas a Estatutos"
        ])

        with t1:
            st.subheader("Ficha de Gobierno Corporativo")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Domicilio Social:** {selected_empresa.get('domicilio_social') or 'N/D'}")
                st.write(f"**Apoderados:** {selected_empresa.get('apoderados') or 'N/D'}")
                st.write(f"**Delegado:** {selected_empresa.get('delegado') or 'N/D'}")
                st.write(f"**ASA Venta:** {selected_empresa.get('asa_venta') or 'N/D'}")
            with col_b:
                st.write(f"**Nº Poder / Revocación:** {selected_empresa.get('numero_poder_revocacion') or 'N/D'}")
                st.write(f"**Modificación Estatutos:** {selected_empresa.get('modificacion_estatutos') or 'N/D'}")
                st.write(f"**AFAC / CAPI:** {selected_empresa.get('afac_capi') or 'N/D'}")
                st.write(f"**Observaciones:** {selected_empresa.get('observacion') or 'Sin observaciones'}")

            st.markdown("---")
            st.subheader("👥 Estructura Histórica de Socios por Fecha Vigente")
            
            cd1, cd2 = st.columns([2, 2])
            with cd1:
                fecha_consulta = st.date_input(
                    "📅 Consultar vigencia de socios a la fecha:",
                    value=datetime.date.today(),
                    help="Filtra los socios y asambleas de transmisión vigentes a la fecha seleccionada."
                )

            rel_socios = [s for s in all_data["socios"] if is_related(s)]
            rel_ventas = [v for v in all_data["ventas"] if is_related(v)]

            # Filtrar asambleas y transmisiones de ventas a la fecha consultada
            ventas_vigentes = []
            for v in rel_ventas:
                v_fec = parse_date_safe(v.get("fecha"))
                if v_fec is None or v_fec <= fecha_consulta:
                    ventas_vigentes.append(v)

            # Filtrar socios vigentes a la fecha consultada
            socios_vigentes = []
            for s in rel_socios:
                s_fec = parse_date_safe(s.get("fecha") or s.get("created_at"))
                if s_fec and s_fec > fecha_consulta:
                    continue
                socios_vigentes.append({
                    "Nombre Socio / Accionista": s.get("nombre_socio"),
                    "Participación / Acciones": s.get("porcentaje") or s.get("porcentaje_participacion") or "N/D",
                    "Tipo Socio": s.get("tipo_socio") or "CAPITAL_FIJO",
                    "Origen / Registro": s.get("origen_tabla") or "CONSTITUCIÓN"
                })

            if socios_vigentes:
                st.dataframe(pd.DataFrame(socios_vigentes), use_container_width=True)
                if ventas_vigentes:
                    st.markdown(f"**📜 Movimientos de Transmisión de Acciones / Asambleas Vigentes ({len(ventas_vigentes)}):**")
                    df_v_summary = pd.DataFrame([{
                        "Nº Escritura": v.get("numero_escritura") or "N/D",
                        "Fecha": v.get("fecha") or "N/D",
                        "Documento": v.get("documento") or "ASAMBLEA VENTA ACCIONES",
                        "Notaría": v.get("notaria") or "N/D",
                        "Detalle / Socios Cap. Variable": v.get("socios_capital_variable") or v.get("observaciones") or "N/D"
                    } for v in ventas_vigentes])
                    st.dataframe(df_v_summary, use_container_width=True)
            else:
                st.info(f"ℹ️ No hay registros adicionales de socios en la fecha seleccionada ({fecha_consulta.strftime('%d/%m/%Y')}).")

        with t2:
            st.subheader("📍 Domicilios Registrados")
            rel_dom = [d for d in all_data["domicilios"] if is_related(d)]
            if rel_dom:
                df_d = pd.DataFrame(rel_dom)
                cols_to_show = [c for c in ["estado", "municipio_delegacion", "conocido", "domicilio_fiscal", "estatus"] if c in df_d.columns]
                st.dataframe(df_d[cols_to_show], use_container_width=True)
            else:
                st.info("ℹ️ No hay registros adicionales en esta categoría.")

        with t3:
            st.subheader("⚖️ Poderes y Revocaciones Otorgados")
            rel_pod = [p for p in all_data["poderes"] if is_related(p)]
            if rel_pod:
                df_p = pd.DataFrame(rel_pod)
                cols_to_show = [c for c in ["tipo_empresa", "numero_escritura", "rpp", "fecha", "notaria", "documento", "administrador_unico_gerente", "apoderados", "delegado", "observaciones"] if c in df_p.columns]
                st.dataframe(df_p[cols_to_show], use_container_width=True)
            else:
                st.info("ℹ️ No hay registros adicionales en esta categoría.")

        with t4:
            st.subheader("📈 Ventas y Movimientos de Capital Variable")
            rel_vta = [v for v in all_data["ventas"] if is_related(v)]
            if rel_vta:
                df_v = pd.DataFrame(rel_vta)
                cols_to_show = [c for c in ["tipo_empresa", "numero_escritura", "rpp", "fecha", "notaria", "documento", "domicilio_social", "capital_total_fijo", "socios_capital_variable", "administrador_unico_gerente", "apoderados", "observaciones"] if c in df_v.columns]
                st.dataframe(df_v[cols_to_show], use_container_width=True)
            else:
                st.info("ℹ️ No hay registros adicionales en esta categoría.")

        with t5:
            st.subheader("📜 Reformas a Estatutos")
            rel_est = [e for e in all_data["estatutos"] if is_related(e)]
            if rel_est:
                df_e = pd.DataFrame(rel_est)
                cols_to_show = [c for c in ["numero_escritura", "rpp", "fecha", "notaria", "documento", "domicilio_social", "capital_total_fijo", "administrador_unico_gerente", "apoderados", "observaciones"] if c in df_e.columns]
                st.dataframe(df_e[cols_to_show], use_container_width=True)
            else:
                st.info("ℹ️ No hay registros adicionales en esta categoría.")

# -----------------------------------------------------------------------------
# 6. VISTA 2: REGISTRAR NUEVA EMPRESA (SOLO ADMIN / HERMANA)
# -----------------------------------------------------------------------------
elif mode == "➕ Registrar Nueva Empresa":
    if st.session_state.user_role != "admin":
        st.error("🚫 Acceso Denegado: Su perfil no tiene permisos para crear nuevas empresas.")
    else:
        st.markdown("## ➕ Registrar Nueva Empresa en el Sistema")
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

            submit_new = st.form_submit_button("💾 Guardar Empresa en Base de Datos", use_container_width=True)

        if submit_new:
            if not new_rs:
                st.error("⚠️ El campo Razón Social es obligatorio.")
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
                st.success(f"🎉 ¡Empresa '{new_rs}' registrada exitosamente en el sistema!")

# -----------------------------------------------------------------------------
# 7. VISTA 3: MODIFICAR / EDITAR EMPRESA (SOLO ADMIN / HERMANA)
# -----------------------------------------------------------------------------
elif mode == "✏️ Modificar / Editar Empresa":
    if st.session_state.user_role != "admin":
        st.error("🚫 Acceso Denegado: Su perfil no tiene permisos para editar información.")
    elif not selected_empresa:
        st.warning("⚠️ Selecciona una empresa en la barra lateral para editar sus datos.")
    else:
        st.markdown(f"## ✏️ Editar Empresa: {selected_empresa.get('razon_social')}")
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

            submit_edit = st.form_submit_button("💾 Actualizar Registro de Empresa", use_container_width=True)

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
                    st.success("✅ Empresa actualizada en Supabase con éxito.")
                except Exception as e:
                    st.warning(f"No se pudo actualizar en Supabase: {e}")

            local_empresas = load_local_json("empresas.json")
            if selected_empresa_idx is not None and selected_empresa_idx < len(local_empresas):
                local_empresas[selected_empresa_idx].update(updated_fields)
                save_local_json("empresas.json", local_empresas)

            st.cache_data.clear()
            st.success("🎉 Datos actualizados correctamente en el sistema.")
