import io
import math
import re
import html
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="Ahorro Inteligente — Comparador de Tasas",
    page_icon="🐷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# FUENTES OFICIALES
# ============================================================
SOCRATA_DATASET_ID = "axk9-g2nh"
SOCRATA_API = f"https://www.datos.gov.co/resource/{SOCRATA_DATASET_ID}.json"
DATASET_URL = f"https://www.datos.gov.co/d/{SOCRATA_DATASET_ID}"
SFC_RATE_URL = "https://www.superfinanciera.gov.co/Superfinanciera-Tasas/faces/generic/passiveInterestRates.xhtml"
SFC_ENTITIES_URL = "https://www.superfinanciera.gov.co/publicaciones/61694/industrias-supervisadasentidades-vigiladas-por-la-superintendencia-financiera-de-colombialista-general-de-entidades-vigiladas-por-la-superintendencia-financiera-de-colombia-61694/"
FOGAFIN_URL = "https://www.fogafin.gov.co/entidades-inscritas"
FOGAFIN_FAQ_URL = "https://www.fogafin.gov.co/preguntas-frecuentes"
FOGACOOP_URL = "https://www.fogacoop.gov.co/seguro-para-su-ahorro/preguntas-frecuentes"
DEPOSIT_INSURANCE_LIMIT = 50_000_000.0

# Fuentes oficiales adicionales para análisis financiero
SFC_SOLVENCY_DATASET_CANDIDATES = ["x586-r5d2", "snsm-7ynr"]
SFC_PORTFOLIO_DATASET_ID = "rvii-eis8"
SFC_SOLVENCY_PAGE = "https://www.superfinanciera.gov.co/publicaciones/60947/informes-y-cifrascifrasestablecimientos-de-creditoinformacion-periodicamensualevolucion-relacion-de-solvencia-60947/"
SFC_LIQUIDITY_PAGE = "https://www.superfinanciera.gov.co/publicaciones/10108240/informes-y-cifrascifrasestablecimientos-de-creditoinformacion-periodicamensualindicadores-de-riesgo-de-liquidez-10108240/"
SFC_QUALITY_PAGE = "https://www.superfinanciera.gov.co/publicaciones/10082252/informes-y-cifrascifrasestablecimientos-de-creditoinformacion-periodicamensualcalidad-de-cartera-establecimientos-de-credito-10082252/"

# ============================================================
# ESTILO
# ============================================================
AZUL = "#1479E8"
AZUL_OSCURO = "#123E6E"
VERDE = "#159A55"
AMARILLO = "#F6C21C"
NARANJA = "#F28C18"
ROJO = "#E52629"
TURQUESA = "#39AAB1"
GRIS = "#5E6B7A"
BORDE = "#E0E7EF"
FONDO = "#F6F8FC"

st.markdown(
    f"""
    <style>
      .stApp {{ background: {FONDO}; }}
      .block-container {{ max-width: 1500px; padding-top: 1.1rem; padding-bottom: 2rem; }}
      [data-testid="stSidebar"] {{ background: #F3F5FA; border-right: 1px solid {BORDE}; }}
      .hero {{ background: #fff; border: 1px solid {BORDE}; border-radius: 22px; padding: 24px 28px 18px 28px; margin-bottom: 16px; }}
      .hero-title {{ font-size: clamp(1.7rem, 2.8vw, 2.55rem); font-weight: 800; color: {AZUL_OSCURO}; line-height: 1.1; }}
      .hero-sub {{ color: {GRIS}; margin-top: 8px; font-size: .98rem; line-height: 1.5; }}
      .hero-line {{ height: 8px; border-radius: 8px; margin-top: 16px; background: linear-gradient(90deg,{AZUL},{TURQUESA},{VERDE},{AMARILLO},{NARANJA},{ROJO}); }}
      .edu-box {{ background: #EAF4FF; border-left: 6px solid {AZUL}; border-radius: 14px; padding: 14px 17px; color:#25476E; margin-bottom:16px; font-size:.94rem; line-height:1.5; }}
      .kpi-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:10px 0 18px; }}
      .kpi-card {{ background:#fff; border:1px solid {BORDE}; border-radius:17px; padding:15px 17px; min-width:0; }}
      .kpi-label {{ color:#596272; font-size:.88rem; font-weight:600; margin-bottom:7px; }}
      .kpi-value {{ color:#303541; font-size:clamp(1.25rem,1.8vw,1.9rem); font-weight:650; white-space:normal; overflow-wrap:anywhere; }}
      .good {{ background:#EAF8EF; border-left:5px solid {VERDE}; padding:13px 15px; border-radius:12px; }}
      .warn {{ background:#FFF8DF; border-left:5px solid {AMARILLO}; padding:13px 15px; border-radius:12px; }}
      .source {{ background:#fff; border:1px solid {BORDE}; border-radius:14px; padding:14px 16px; }}
      .metric-help {{ background:#fff; border:1px solid {BORDE}; border-radius:14px; padding:14px 16px; min-height:145px; }}
      .metric-help b {{ color:{AZUL_OSCURO}; }}
      .risk-summary {{ background:#fff; border:1px solid {BORDE}; border-radius:14px; padding:15px 17px; margin:10px 0 14px; }}
      .bank-profile {{ background:#fff; border:1px solid {BORDE}; border-radius:18px; padding:17px 18px; min-height:245px; box-shadow:0 4px 12px rgba(26,59,93,.05); margin-bottom:14px; }}
      .bank-profile h4 {{ color:{AZUL_OSCURO}; margin:0 0 9px 0; font-size:1.08rem; }}
      .bank-tag {{ display:inline-block; background:#EAF4FF; color:{AZUL_OSCURO}; border-radius:999px; padding:3px 9px; margin:2px 5px 6px 0; font-size:.78rem; font-weight:650; }}
      .bank-profile p {{ margin:.35rem 0; color:#4D5868; line-height:1.45; font-size:.89rem; }}
      .selection-note {{ background:#EEF7FF; border-left:5px solid {AZUL}; padding:12px 14px; border-radius:12px; margin:8px 0 14px; }}
      button[data-baseweb="tab"] p {{ font-size:.9rem!important; }}
      h2 {{ font-size:1.5rem!important; }}
      h3 {{ font-size:1.15rem!important; }}
      [data-testid="stDataFrame"] {{ font-size:.86rem; }}
      @media (max-width: 950px) {{ .kpi-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
      @media (max-width: 600px) {{ .kpi-grid {{ grid-template-columns:1fr; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# UTILIDADES
# ============================================================
def moneda(v):
    v = float(v)
    signo = "-" if v < 0 else ""
    return f"{signo}${abs(v):,.0f}".replace(",", ".")


def tasa_txt(v):
    return f"{float(v):.2f}%"


def render_kpis(items):
    cards = []
    for label, value in items:
        cards.append(
            f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>'
        )
    st.markdown('<div class="kpi-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


def normalize_text(s):
    return re.sub(r"\s+", " ", str(s or "").strip()).upper()


def clean_entity_name(name):
    """Normaliza visualmente nombres reportados sin cambiar la fuente original."""
    s = str(name or "").strip()
    s = re.sub(r'^[\"\']+|[\"\']+$', '', s).strip()
    s = re.sub(r'\s+', ' ', s)
    # Acorta algunos nombres que la fuente puede traer con alias extensos.
    aliases = {
        'BANCO UNION S.A. (EN ADELANTE "BANCO UNION")': 'Banco Unión S.A.',
        'BANCO UNIÓN S.A. (EN ADELANTE "BANCO UNIÓN")': 'Banco Unión S.A.',
    }
    return aliases.get(s.upper(), s)


def classify_sfc_segment(name):
    """Clasificación educativa por denominación de la entidad.
    La fuente de tasas sigue siendo la SFC; esta segmentación no es una calificación.
    """
    n = normalize_text(name)

    coop_tokens = [
        'COOPERATIVA', 'CONFIAR', 'COTRAFA', 'COOPKENNEDY',
        'COOPERATIVA FINANCIERA DE ANTIOQUIA', 'CFA'
    ]
    if any(t in n for t in coop_tokens):
        return 'Cooperativas financieras'

    cf_tokens = [
        ' C.F.', ' CF ', 'CF S.A', 'COMPAÑIA DE FINANCIAMIENTO',
        'COMPAÑÍA DE FINANCIAMIENTO', 'COLTEFINANCIERA', 'CREDIFAMILIA',
        'IRIS', 'KOA', 'BOLD', 'FINANCIERA DANN REGIONAL', 'TUYA'
    ]
    if any(t in f' {n} ' for t in cf_tokens):
        return 'Compañías de financiamiento'

    corp_tokens = ['CORPORACION FINANCIERA', 'CORPORACIÓN FINANCIERA', 'CORFICOLOMBIANA']
    if any(t in n for t in corp_tokens):
        return 'Corporaciones financieras'

    # Algunos bancos reportan marcas/nombres que no contienen literalmente la palabra BANCO.
    bank_aliases = [
        'AV VILLAS', 'BANCAMIA', 'BBVA COLOMBIA', 'DAVIBANK',
        'LULO BANK', 'ITAU', 'SCOTIABANK COLPATRIA', 'COLPATRIA'
    ]
    if 'BANCO' in n or any(a in n for a in bank_aliases):
        return 'Establecimientos bancarios'

    return 'Otros reportantes SFC'


def classify_product(desc):
    """Clasifica el producto usando texto normalizado de varios campos de la fuente."""
    d = normalize_text(desc)
    if "CDAT" in d or "CERTIFICADO DE DEPOSITO DE AHORRO A TERMINO" in d:
        return "CDAT"
    cdt_terms = [
        "CDT",
        "DEPOSITO A TERMINO",
        "DEPOSITOS A TERMINO",
        "CERTIFICADO DE DEPOSITO A TERMINO",
        "CERTIFICADOS DE DEPOSITO A TERMINO",
        "CERTIFICADO A TERMINO",
    ]
    if any(term in d for term in cdt_terms):
        return "CDT"
    ahorro_terms = [
        "CUENTA DE AHORRO",
        "CUENTAS DE AHORRO",
        "DEPOSITO DE AHORRO",
        "DEPOSITOS DE AHORRO",
        "AHORRO ORDINARIO",
        "AHORRO",
    ]
    if any(term in d for term in ahorro_terms):
        return "Cuenta de ahorro"
    return "Otro"


def extract_term_days(desc):
    """Heuristic only. Exact SFC description remains visible to user."""
    d = normalize_text(desc)
    patterns = [
        r"A\s+(\d+)\s+DIAS",
        r"A\s+(\d+)\s+DÍAS",
        r"(\d+)\s+DIAS",
        r"(\d+)\s+DÍAS",
    ]
    for p in patterns:
        m = re.search(p, d)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return None


def projected_return(capital, ea_pct, days):
    if capital <= 0 or days <= 0:
        return 0.0, capital
    ea = max(float(ea_pct), -99.999) / 100
    final = capital * ((1 + ea) ** (days / 365.0))
    return final - capital, final


def future_value_monthly(initial, contribution, ea_pct, months):
    if months <= 0:
        return initial
    ea = max(float(ea_pct), -99.999) / 100
    monthly = (1 + ea) ** (1/12) - 1
    value = initial
    for _ in range(months):
        value = value * (1 + monthly) + contribution
    return value



# ============================================================
# PERFILES EDUCATIVOS DE ENTIDADES
# Datos institucionales resumidos para contextualizar la comparación.
# No son una calificación de riesgo ni reemplazan la información oficial.
# ============================================================
BANK_PROFILES = [
    {
        "aliases": ["BANCOLOMBIA"],
        "name": "Bancolombia",
        "origin": "Colombia",
        "city": "Medellín",
        "colombia_since": 1875,
        "group": "Grupo Cibest / tradición Grupo Bancolombia",
        "focus": "Banca universal para personas, empresas e instituciones",
        "history": "Su historia se remonta a 1875 con el Banco de Colombia. En 1998 se fusionaron Banco de Colombia y Banco Industrial Colombiano para dar origen a Bancolombia; posteriormente integró Conavi y Corfinsura.",
        "source": "https://prensa.bancolombia.com/noticias/resultados-corporativos/historia-de-bancolombia",
    },
    {
        "aliases": ["PICHINCHA"],
        "name": "Banco Pichincha Colombia",
        "origin": "Ecuador / Grupo Pichincha",
        "city": "Bucaramanga (inicio de su historia en Colombia)",
        "colombia_since": 1964,
        "group": "Grupo Pichincha",
        "focus": "Banca de personas y empresas; también opera Pibank como propuesta digital",
        "history": "La historia de la entidad en Colombia comenzó en 1964. Grupo Pichincha llegó como accionista mayoritario en 1997 y desde 2011 opera como Banco Pichincha Colombia. Pibank nació en 2022.",
        "source": "https://www.bancopichincha.com.co/web/corporativo/quienes-somos",
    },
    {
        "aliases": ["BTG PACTUAL"],
        "name": "Banco BTG Pactual Colombia",
        "origin": "Brasil",
        "city": "Presencia en Colombia",
        "colombia_since": 2012,
        "group": "BTG Pactual",
        "focus": "Banca de inversión, gestión de activos, patrimonio y banca",
        "history": "BTG Pactual fue fundado en Río de Janeiro en 1983. Su expansión en Colombia se fortaleció en 2012 con la adquisición de Bolsa y Renta; la licencia bancaria colombiana fue aprobada en 2021.",
        "source": "https://ri.btgpactual.com/sobre-o-banco/negocio-e-historico",
    },
    {
        "aliases": ["BANCO W", "BANCO WWB"],
        "name": "Banco W",
        "origin": "Colombia",
        "city": "Cali",
        "colombia_since": 2011,
        "group": "Accionistas con participación de Fundación Grupo Social y Fundación WWB Colombia",
        "focus": "Microfinanzas, inclusión financiera, ahorro, inversión y servicios a micronegocios",
        "history": "Tiene raíces en la Fundación WWB Colombia, creada en 1980. En 2011 comenzó operaciones como banco (Banco WWB) y posteriormente evolucionó a la marca Banco W.",
        "source": "https://www.bancow.com.co/quienes-somos",
    },
    {
        "aliases": ["CAJA SOCIAL"],
        "name": "Banco Caja Social",
        "origin": "Colombia",
        "city": "Bogotá",
        "colombia_since": 1911,
        "group": "Fundación Grupo Social",
        "focus": "Banca social, personas, microempresarios, pymes y vivienda",
        "history": "Nació en 1911 como Caja Social de Ahorros del Círculo de Obreros. En 1992 se convirtió en banco; en 2005 se fusionó con Banco Colmena y en 2011 retomó el nombre Banco Caja Social.",
        "source": "https://www.bancocajasocial.com/informacion-corporativa/acerca-de-nosotros/nosotros/historia-del-banco-caja-social/",
    },
    {
        "aliases": ["CONTACTAR"],
        "name": "Banco Contactar",
        "origin": "Colombia",
        "city": "Nariño",
        "colombia_since": 2024,
        "group": "Corporación Contactar como principal antecedente/accionista",
        "focus": "Microfinanzas, zonas urbanas y rurales, pymes, ahorro e inversión",
        "history": "Banco Contactar inició operación bancaria en marzo de 2024 y recoge la trayectoria de más de tres décadas de la Corporación Contactar en inclusión financiera.",
        "source": "https://bancocontactar.com/conoce-a-banco-contactar/",
    },
    {
        "aliases": ["BANCO DE BOGOT"],
        "name": "Banco de Bogotá",
        "origin": "Colombia",
        "city": "Bogotá",
        "colombia_since": 1870,
        "group": "Grupo Aval",
        "focus": "Banca universal para personas, empresas e instituciones",
        "history": "Es uno de los bancos de mayor trayectoria del país. Fue fundado en Bogotá en 1870 y hoy forma parte de Grupo Aval.",
        "source": "https://www.bancodebogota.com/",
    },
    {
        "aliases": ["DAVIVIENDA"],
        "name": "Banco Davivienda",
        "origin": "Colombia",
        "city": "Bogotá",
        "colombia_since": 1972,
        "group": "Grupo Empresarial Bolívar",
        "focus": "Banca de personas, vivienda, empresas y servicios financieros",
        "history": "Nació en 1972 como Coldeahorro y en 1973 adoptó el nombre Davivienda. Hace parte del Grupo Empresarial Bolívar y tiene más de cinco décadas de trayectoria en Colombia.",
        "source": "https://ir.davivienda.com/historia/",
    },
    {
        "aliases": ["BBVA"],
        "name": "BBVA Colombia",
        "origin": "España / Grupo BBVA",
        "city": "Colombia",
        "colombia_since": 1996,
        "group": "Grupo BBVA",
        "focus": "Banca universal y servicios financieros digitales",
        "history": "La etapa de BBVA en Colombia comenzó en 1996 cuando BBV adquirió una participación en Banco Ganadero. Tras la fusión de BBV y Argentaria, la entidad evolucionó hacia la marca BBVA.",
        "source": "https://www.bbva.com.co/personas/historia.html",
    },
    {
        "aliases": ["OCCIDENTE"],
        "name": "Banco de Occidente",
        "origin": "Colombia",
        "city": "Cali",
        "colombia_since": 1965,
        "group": "Grupo Aval",
        "focus": "Banca de personas y empresas",
        "history": "Nació en Cali el 3 de mayo de 1965. Desde la década de 1970 inició su expansión nacional y actualmente hace parte de Grupo Aval.",
        "source": "https://webavc.bancodeoccidente.com.co/wps/portal/banco-de-occidente/bancodeoccidente/quienes-somos/quienessomos",
    },
    {
        "aliases": ["BANCO POPULAR"],
        "name": "Banco Popular",
        "origin": "Colombia",
        "city": "Bogotá",
        "colombia_since": 1950,
        "group": "Grupo Aval",
        "focus": "Banca de personas, libranza, empresas y sector institucional",
        "history": "Nació oficialmente el 30 de junio de 1950 y abrió al público en diciembre de ese año. En 1996 inició su proceso de privatización y posteriormente se integró a Grupo Aval.",
        "source": "https://www.bancopopular.com.co/wps/portal/bancopopular/inicio/sobre-nosotros/historia-banco-popular",
    },
    {
        "aliases": ["AV VILLAS", "AVVILLAS"],
        "name": "Banco AV Villas",
        "origin": "Colombia",
        "city": "Colombia",
        "colombia_since": 1972,
        "group": "Grupo Aval",
        "focus": "Banca de personas, vivienda, ahorro y crédito",
        "history": "Tuvo su origen en 1972 como Corporación de Ahorro y Vivienda Las Villas. Se integró a Grupo Aval y en 2002 se convirtió oficialmente en banco comercial.",
        "source": "https://avvillas.com.co/productos-en-oficina/acerca-de-avvillas/",
    },
    {
        "aliases": ["AGRARIO", "BANAGRARIO"],
        "name": "Banco Agrario de Colombia",
        "origin": "Colombia",
        "city": "Colombia",
        "colombia_since": 1999,
        "group": "Grupo Bicentenario / sector público",
        "focus": "Desarrollo rural, agro, inclusión financiera y banca de personas",
        "history": "Abrió sus puertas el 28 de junio de 1999, tras la liquidación de la Caja Agraria. Su propósito principal es ofrecer servicios bancarios orientados al desarrollo del sector rural.",
        "source": "https://www.bancoagrario.gov.co/relacion-con-accionistas/acerca-del-banco",
    },
    {
        "aliases": ["BANCAM"],
        "name": "Bancamía",
        "origin": "Colombia",
        "city": "Colombia",
        "colombia_since": 2008,
        "group": "Fundación Microfinanzas BBVA y organizaciones fundadoras colombianas",
        "focus": "Microfinanzas e inclusión financiera para microempresarios",
        "history": "Nació en 2008 de la unión de la Corporación Mundial de la Mujer Colombia, la Corporación Mundial de la Mujer Medellín y la Fundación Microfinanzas BBVA.",
        "source": "https://www.bancamia.com.co/somos_bancamia-nosotros/",
    },
    {
        "aliases": ["BANCOOMEVA", "COOMEVA"],
        "name": "Bancoomeva",
        "origin": "Colombia",
        "city": "Cali",
        "colombia_since": 2011,
        "group": "Grupo Empresarial Cooperativo Coomeva",
        "focus": "Banca de personas, asociados y empresas",
        "history": "Fue constituido en enero de 2011 e inició operaciones el 4 de abril de 2011, dando continuidad a la operación financiera que desarrollaba Coomeva Cooperativa Financiera.",
        "source": "https://www.bancoomeva.com.co/publicaciones/163397/historia/",
    },
]


def bank_profile(entity_name):
    n = str(entity_name or "").upper()
    for prof in BANK_PROFILES:
        if any(alias in n for alias in prof["aliases"]):
            return prof
    return {
        "name": str(entity_name),
        "origin": "Información institucional no integrada",
        "city": "N/D",
        "colombia_since": None,
        "group": "Consulta el sitio oficial de la entidad",
        "focus": "Entidad reportante/vigilada dentro de las fuentes utilizadas por la app",
        "history": "La aplicación aún no tiene una reseña institucional local para esta entidad. Esto no afecta la comparación de tasas ni el análisis financiero; puedes validar su historia directamente en su sitio oficial.",
        "source": SFC_ENTITIES_URL,
    }


def render_bank_profiles(entity_names, title="Conoce las entidades seleccionadas"):
    names = [str(x) for x in entity_names if str(x).strip()]
    if not names:
        return
    st.markdown(f"### {title}")
    st.caption("Reseña educativa para dar contexto. La historia o antigüedad de una entidad no equivale a una calificación de riesgo.")
    current_year = datetime.now().year
    cols = st.columns(2)
    for i, ent in enumerate(names):
        prof = bank_profile(ent)
        since = prof.get("colombia_since")
        if since:
            years = max(0, current_year - int(since))
            presence = f"Desde {since} · aprox. {years} años"
        else:
            presence = "Antigüedad no integrada"
        with cols[i % 2]:
            safe_name = html.escape(prof.get("name", ent))
            safe_origin = html.escape(prof.get("origin", "N/D"))
            safe_city = html.escape(prof.get("city", "N/D"))
            safe_group = html.escape(prof.get("group", "N/D"))
            safe_focus = html.escape(prof.get("focus", "N/D"))
            safe_history = html.escape(prof.get("history", ""))
            safe_source = html.escape(prof.get("source", SFC_ENTITIES_URL), quote=True)
            st.markdown(
                f"<div class='bank-profile'><h4>🏦 {safe_name}</h4>"
                f"<span class='bank-tag'>Origen: {safe_origin}</span>"
                f"<span class='bank-tag'>Colombia: {html.escape(presence)}</span>"
                f"<p><b>Base / referencia:</b> {safe_city}</p>"
                f"<p><b>Grupo o respaldo corporativo:</b> {safe_group}</p>"
                f"<p><b>Enfoque:</b> {safe_focus}</p>"
                f"<p><b>Resumen histórico:</b> {safe_history}</p>"
                f"<p><a href='{safe_source}' target='_blank'>Consultar fuente institucional ↗</a></p></div>",
                unsafe_allow_html=True,
            )


def savings_projection_series(initial, contribution, ea_pct, months):
    ea = max(float(ea_pct), -99.999) / 100
    monthly_rate = (1 + ea) ** (1/12) - 1
    values = [float(initial)]
    value = float(initial)
    for _ in range(int(months)):
        value = value * (1 + monthly_rate) + float(contribution)
        values.append(value)
    return values


def render_modern_savings_charts(sim_df, capital, monthly_contribution, months):
    if sim_df.empty:
        return
    st.markdown("### Comparación visual")
    tab_final, tab_evol = st.tabs(["📊 Resultado final", "📈 Evolución del ahorro"])
    with tab_final:
        plot_df = sim_df.sort_values("Valor estimado final", ascending=True).copy()
        plot_df["Aportado"] = float(capital) + float(monthly_contribution) * int(months)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=plot_df["Entidad"], x=plot_df["Aportado"], orientation="h",
            name="Capital + aportes", marker_color="#D9EAFB",
            hovertemplate="<b>%{y}</b><br>Capital + aportes: $%{x:,.0f}<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            y=plot_df["Entidad"], x=plot_df["Rendimiento estimado"], orientation="h",
            name="Rendimiento estimado", marker_color=AZUL,
            text=[moneda(x) for x in plot_df["Rendimiento estimado"]], textposition="inside",
            hovertemplate="<b>%{y}</b><br>Rendimiento: $%{x:,.0f}<extra></extra>"
        ))
        fig.update_layout(
            barmode="stack", height=max(360, 90 * len(plot_df)),
            margin=dict(l=20, r=35, t=20, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
            xaxis_title="Valor estimado", yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            font=dict(family="Arial, sans-serif", color="#374151"),
            xaxis=dict(gridcolor="#E9EEF5", tickprefix="$", separatethousands=True),
            yaxis=dict(automargin=True),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("La barra completa representa el valor estimado al final del horizonte: lo aportado + el rendimiento estimado.")
    with tab_evol:
        fig2 = go.Figure()
        for _, row in sim_df.iterrows():
            vals = savings_projection_series(capital, monthly_contribution, row["Tasa usada EA (%)"], months)
            fig2.add_trace(go.Scatter(
                x=list(range(0, int(months)+1)), y=vals, mode="lines",
                name=str(row["Entidad"]),
                hovertemplate="Mes %{x}<br>Saldo estimado: $%{y:,.0f}<extra>%{fullData.name}</extra>"
            ))
        fig2.update_layout(
            height=430, margin=dict(l=20, r=25, t=20, b=35),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
            xaxis_title="Mes", yaxis_title="Saldo estimado",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            font=dict(family="Arial, sans-serif", color="#374151"),
            xaxis=dict(gridcolor="#E9EEF5"), yaxis=dict(gridcolor="#E9EEF5", tickprefix="$", separatethousands=True),
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.caption("La evolución usa la tasa EA seleccionada como referencia constante para fines educativos; las tasas reales pueden cambiar.")

def deposit_protection_profile(segment, product_detected, amount):
    """Educational protection profile based on official deposit-insurance schemes.
    This is NOT a credit rating or probability of default.
    """
    seg = str(segment or "")
    prod = str(product_detected or "")
    amount = max(float(amount or 0), 0.0)

    fund = "Por verificar"
    covered = False
    coverage_note = "La aplicación no puede confirmar automáticamente el seguro para este tipo de entidad/producto."

    if seg in ["Establecimientos bancarios", "Compañías de financiamiento", "Corporaciones financieras"]:
        fund = "Fogafín"
        if prod in ["Cuenta de ahorro", "CDT"]:
            covered = True
            coverage_note = "Producto incluido en las categorías de depósitos protegidos por Fogafín."
        elif prod == "CDAT":
            coverage_note = "Fogafín no enumera expresamente CDAT en su listado público de productos protegidos; conviene verificar el sello y las condiciones contractuales."
    elif seg == "Cooperativas financieras":
        fund = "Fogacoop"
        if prod in ["Cuenta de ahorro", "CDT", "CDAT"]:
            covered = True
            coverage_note = "Los depósitos de ahorro y depósitos a término de cooperativas inscritas están cubiertos por Fogacoop, sujeto a sus reglas."

    insured_amount = min(amount, DEPOSIT_INSURANCE_LIMIT) if covered else 0.0
    uncovered_amount = max(amount - DEPOSIT_INSURANCE_LIMIT, 0.0) if covered else amount

    if covered and amount <= DEPOSIT_INSURANCE_LIMIT:
        grade = "A"
        label = "🟢 Protección alta"
        plain = "El monto simulado queda dentro del tope del seguro de depósitos, si la entidad y el producto cumplen las condiciones del fondo correspondiente."
    elif covered and amount > DEPOSIT_INSURANCE_LIMIT:
        grade = "B"
        label = "🟡 Protección parcial"
        plain = "Una parte del dinero supera el tope de seguro de depósitos en esta entidad. El excedente no queda cubierto por ese seguro."
    elif fund != "Por verificar":
        grade = "C"
        label = "🟠 Cobertura por verificar"
        plain = "La entidad pertenece a un tipo que participa en un esquema de seguro, pero la aplicación no confirma automáticamente que este producto específico esté cubierto."
    else:
        grade = "D"
        label = "⚪ Requiere revisión"
        plain = "La aplicación no tiene evidencia suficiente para asignar protección automática. Revisa supervisor, fondo de garantía y condiciones del producto."

    concentration = "Baja"
    if amount > DEPOSIT_INSURANCE_LIMIT and amount <= 2 * DEPOSIT_INSURANCE_LIMIT:
        concentration = "Media"
    elif amount > 2 * DEPOSIT_INSURANCE_LIMIT:
        concentration = "Alta"

    return {
        "Fondo": fund,
        "Producto cubierto": covered,
        "Monto cubierto estimado": insured_amount,
        "Monto no cubierto estimado": uncovered_amount,
        "Grado educativo": grade,
        "Nivel de protección": label,
        "Lectura sencilla": plain,
        "Riesgo de concentración": concentration,
        "Nota cobertura": coverage_note,
    }


def rating_plain_language(rating):
    """Translate a user-supplied external rating into plain language."""
    r = normalize_text(rating).replace(" ", "")
    r = re.sub(r"\(.*?\)", "", r)
    if not r:
        return "Ingresa una calificación publicada por una agencia para verla en lenguaje sencillo."
    if r.startswith("AAA"):
        return "Calidad crediticia muy alta dentro de la escala utilizada. Aun así, no significa riesgo cero."
    if r.startswith("AA"):
        return "Calidad crediticia alta. La entidad se considera con capacidad fuerte de pago, según esa escala."
    if r.startswith("A"):
        return "Calidad crediticia buena, aunque puede ser más sensible a cambios económicos que categorías superiores."
    if r.startswith("BBB"):
        return "Capacidad de pago considerada adecuada en muchas escalas, con mayor sensibilidad a condiciones adversas."
    if r.startswith("BB") or r.startswith("B"):
        return "La calificación suele indicar mayor vulnerabilidad al entorno y exige revisar con más detalle el riesgo."
    if r.startswith("CCC") or r.startswith("CC") or r.startswith("C") or r.startswith("D"):
        return "La escala suele asociar esta categoría con riesgo elevado o situación crediticia débil. Revisa la definición exacta de la agencia."
    return "No reconozco esta nomenclatura. Consulta la escala de la agencia que emitió la calificación."


def entity_key(name):
    n = normalize_text(name)
    for token in ["BANCO", "S.A.", "S.A", "SA", "S.A.S.", "SAS", "COLOMBIA", "COLOMBIANO", "CORPORACION", "CORPORACIÓN", "FINANCIERA", "COMPAÑIA", "COMPAÑÍA", "DE FINANCIAMIENTO", "COOPERATIVA", "LTDA", "LIMITADA"]:
        n = n.replace(token, " ")
    n = re.sub(r"[^A-Z0-9ÁÉÍÓÚÑ ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def best_entity_match(target, candidates):
    import difflib
    tk = entity_key(target)
    if not tk:
        return None
    exact = [c for c in candidates if entity_key(c) == tk]
    if exact:
        return exact[0]
    best, best_score = None, 0.0
    for c in candidates:
        ck = entity_key(c)
        if not ck:
            continue
        score = 0.95 if (tk in ck or ck in tk) else difflib.SequenceMatcher(None, tk, ck).ratio()
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= 0.72 else None


@st.cache_data(ttl=3600, show_spinner=False)
def socrata_get(dataset_id, params=None, timeout=35):
    url = f"https://www.datos.gov.co/resource/{dataset_id}.json"
    r = requests.get(url, params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=3600, show_spinner=False)
def socrata_metadata(dataset_id):
    r = requests.get(f"https://www.datos.gov.co/api/views/{dataset_id}", timeout=30)
    r.raise_for_status()
    return r.json()


def _find_field(meta, contains_any):
    for c in meta.get("columns", []) if isinstance(meta, dict) else []:
        text = normalize_text((c.get("name") or "") + " " + (c.get("description") or "") + " " + (c.get("fieldName") or ""))
        if any(normalize_text(k) in text for k in contains_any):
            return c.get("fieldName")
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_solvency_snapshot():
    for dataset_id in SFC_SOLVENCY_DATASET_CANDIDATES:
        try:
            meta = socrata_metadata(dataset_id)
            entity_f = _find_field(meta, ["NOMBRE ENTIDAD", "NOMBRE_ENTIDAD"])
            date_f = _find_field(meta, ["FECHA"])
            concept_f = _find_field(meta, ["CONCEPTO"])
            value_f = _find_field(meta, ["VALOR"])
            if not all([entity_f, date_f, concept_f, value_f]):
                continue
            latest = socrata_get(dataset_id, {"$select": date_f, "$order": f"{date_f} DESC", "$limit": 1})
            if not latest:
                continue
            latest_date = latest[0].get(date_f)
            rows = socrata_get(dataset_id, {"$where": f"{date_f}='{latest_date}'", "$limit": 50000})
            df = pd.DataFrame(rows)
            if df.empty:
                continue
            df[value_f] = pd.to_numeric(df[value_f], errors="coerce")
            c = df[concept_f].astype(str).map(normalize_text)
            mask = c.str.contains("SOLVENCIA TOTAL", na=False) | c.str.contains("RELACION DE SOLVENCIA", na=False) | c.str.contains("RELACIÓN DE SOLVENCIA", na=False)
            out = df.loc[mask, [entity_f, value_f]].dropna().copy()
            if out.empty:
                continue
            vals = out[value_f].astype(float)
            out["Solvencia (%)"] = vals.where(vals.abs() >= 1, vals * 100)
            out = out.rename(columns={entity_f: "Entidad SFC"})[["Entidad SFC", "Solvencia (%)"]]
            out["Fecha solvencia"] = str(latest_date)[:10]
            return out
        except Exception:
            continue
    return pd.DataFrame(columns=["Entidad SFC", "Solvencia (%)", "Fecha solvencia"])


@st.cache_data(ttl=3600, show_spinner=False)
def load_portfolio_quality_snapshot():
    try:
        meta = socrata_metadata(SFC_PORTFOLIO_DATASET_ID)
        entity_f = _find_field(meta, ["NOMBRE ENTIDAD", "ENTIDAD"])
        balance_f = _find_field(meta, ["SALDO"])
        rating_f = _find_field(meta, ["CALIFICACION", "CALIFICACIÓN"])
        year_f = _find_field(meta, ["AÑO", "ANO"])
        month_f = _find_field(meta, ["MES"])
        date_f = _find_field(meta, ["FECHA"])
        if not all([entity_f, balance_f, rating_f]):
            return pd.DataFrame(columns=["Entidad SFC", "Calidad cartera (%)", "Fecha calidad", "Tipo calidad"])
        where = None
        period_label = "Último disponible"
        if date_f:
            latest = socrata_get(SFC_PORTFOLIO_DATASET_ID, {"$select": date_f, "$order": f"{date_f} DESC", "$limit": 1})
            if latest:
                d = latest[0].get(date_f)
                where = f"{date_f}='{d}'"
                period_label = str(d)[:10]
        elif year_f and month_f:
            latest = socrata_get(SFC_PORTFOLIO_DATASET_ID, {"$select": f"{year_f},{month_f}", "$order": f"{year_f} DESC,{month_f} DESC", "$limit": 1})
            if latest:
                yy, mm = latest[0].get(year_f), latest[0].get(month_f)
                where = f"{year_f}={yy} AND {month_f}={mm}"
                period_label = f"{yy}-{str(mm).zfill(2)}"
        params = {"$limit": 50000}
        if where:
            params["$where"] = where
        df = pd.DataFrame(socrata_get(SFC_PORTFOLIO_DATASET_ID, params))
        if df.empty:
            return pd.DataFrame(columns=["Entidad SFC", "Calidad cartera (%)", "Fecha calidad", "Tipo calidad"])
        df[balance_f] = pd.to_numeric(df[balance_f], errors="coerce").fillna(0)
        df["_rating"] = df[rating_f].astype(str).str.upper().str.strip()
        df["_is_deteriorated"] = ~df["_rating"].str.startswith("A")
        total = df.groupby(entity_f)[balance_f].sum()
        bad = df[df["_is_deteriorated"]].groupby(entity_f)[balance_f].sum()
        ratio = ((bad / total) * 100).fillna(0)
        out = ratio.rename("Calidad cartera (%)").reset_index().rename(columns={entity_f: "Entidad SFC"})
        out["Fecha calidad"] = period_label
        out["Tipo calidad"] = "Proxy cartera B–E / total"
        return out
    except Exception:
        return pd.DataFrame(columns=["Entidad SFC", "Calidad cartera (%)", "Fecha calidad", "Tipo calidad"])


def relative_signal(series, value, higher_is_better=True):
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if pd.isna(value) or len(vals) < 3:
        return "⚪ Sin referencia"
    q1, q3 = vals.quantile([0.25, 0.75]).tolist()
    if higher_is_better:
        if value >= q3:
            return "🟢 Fuerte en la muestra"
        if value >= q1:
            return "🟡 Intermedio en la muestra"
        return "🔴 Requiere revisión"
    if value <= q1:
        return "🟢 Fuerte en la muestra"
    if value <= q3:
        return "🟡 Intermedio en la muestra"
    return "🔴 Requiere revisión"


@st.cache_data(ttl=1800, show_spinner=False)
def get_available_dates(limit=180):
    params = {
        "$select": "fechacorte",
        "$group": "fechacorte",
        "$order": "fechacorte DESC",
        "$limit": limit,
    }
    r = requests.get(SOCRATA_API, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    dates = [x.get("fechacorte") for x in data if x.get("fechacorte")]
    return dates


@st.cache_data(ttl=1800, show_spinner=False)
def get_rows_for_date(fecha_iso):
    # Socrata Floating Timestamp normally uses ISO strings like 2026-07-08T00:00:00.000
    params = {
        "$where": f"fechacorte='{fecha_iso}'",
        "$limit": 50000,
    }
    r = requests.get(SOCRATA_API, params=params, timeout=35)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ["tasa", "monto", "tipoentidad", "codigoentidad", "uca", "subcuenta"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "nombreentidad" not in df.columns:
        df["nombreentidad"] = ""
    # La estructura del conjunto puede variar en el texto descriptivo. Se combinan
    # los campos disponibles para no perder CDT/CDAT por depender de una sola columna.
    text_candidates = ["descripcion", "nombre", "nombre_sub", "nombresubcuenta", "tipo"]
    for c in text_candidates:
        if c not in df.columns:
            df[c] = ""
    def _join_product_text(row):
        vals = []
        for c in text_candidates:
            v = row.get(c, "")
            if pd.notna(v) and str(v).strip():
                vals.append(str(v).strip())
        return " | ".join(vals)
    df["Texto producto"] = df.apply(_join_product_text, axis=1)
    # Mantiene una etiqueta legible para el comparador.
    df["descripcion"] = df.apply(
        lambda r: str(r.get("descripcion") or r.get("nombre_sub") or r.get("nombre") or r.get("Texto producto") or "").strip(),
        axis=1,
    )
    df["Entidad (visual)"] = df["nombreentidad"].apply(clean_entity_name)
    df["Segmento SFC"] = df["Entidad (visual)"].apply(classify_sfc_segment)
    df["Producto detectado"] = df["Texto producto"].apply(classify_product)
    df["Plazo detectado (días)"] = df["Texto producto"].apply(extract_term_days)
    return df


@st.cache_data(ttl=1800, show_spinner=False)
def get_recent_entity_universe(latest_date_iso, lookback_days=90):
    try:
        latest = pd.to_datetime(latest_date_iso)
        start = latest - pd.Timedelta(days=lookback_days)
        start_iso = start.strftime('%Y-%m-%dT00:00:00.000')
        params = {
            '$select': 'nombreentidad,tipoentidad',
            '$where': f"fechacorte>='{start_iso}'",
            '$group': 'nombreentidad,tipoentidad',
            '$order': 'nombreentidad',
            '$limit': 5000,
        }
        r = requests.get(SOCRATA_API, params=params, timeout=35)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if df.empty or 'nombreentidad' not in df.columns:
            return pd.DataFrame(columns=['Entidad (visual)', 'Segmento SFC'])
        df['Entidad (visual)'] = df['nombreentidad'].apply(clean_entity_name)
        df['Segmento SFC'] = df['Entidad (visual)'].apply(classify_sfc_segment)
        return df[['Entidad (visual)', 'Segmento SFC']].drop_duplicates().reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=['Entidad (visual)', 'Segmento SFC'])


def build_entity_universe(raw_df, recent_df):
    frames = []
    if raw_df is not None and not raw_df.empty and 'Entidad (visual)' in raw_df.columns:
        frames.append(raw_df[['Entidad (visual)', 'Segmento SFC']].drop_duplicates())
    if recent_df is not None and not recent_df.empty:
        frames.append(recent_df[['Entidad (visual)', 'Segmento SFC']].drop_duplicates())
    if not frames:
        return pd.DataFrame(columns=['Entidad (visual)', 'Segmento SFC'])
    return (
        pd.concat(frames, ignore_index=True)
        .dropna(subset=['Entidad (visual)'])
        .drop_duplicates(subset=['Entidad (visual)'], keep='first')
        .sort_values('Entidad (visual)')
        .reset_index(drop=True)
    )


def product_access_summary(product_name, days):
    p = str(product_name or '')
    if p == 'Cuenta de ahorro':
        return 'Alta disponibilidad: normalmente puedes retirar, sujeto a condiciones y canales del producto.'
    if p in ['CDT', 'CDAT', 'CDT / CDAT']:
        plazo = f' ({int(days)} días en la simulación)' if days else ''
        return 'Disponibilidad restringida por plazo' + plazo + '. Verifica vencimiento y si existe redención anticipada.'
    return 'Revisar condiciones de disponibilidad y retiro del producto.'


def plain_financial_signal(sol_signal, quality_signal, liquidity_signal, sol_value, quality_value, liquidity_value):
    parts = []
    if pd.notna(sol_value):
        if '🟢' in str(sol_signal): parts.append('capital relativamente sólido en la muestra')
        elif '🔴' in str(sol_signal): parts.append('capital que conviene revisar con más detalle')
        else: parts.append('capital en rango intermedio de la muestra')
    else:
        parts.append('sin dato de solvencia integrado')
    if pd.notna(quality_value):
        if '🟢' in str(quality_signal): parts.append('cartera con menor deterioro relativo')
        elif '🔴' in str(quality_signal): parts.append('cartera con mayor deterioro relativo')
        else: parts.append('calidad de cartera en rango intermedio')
    else:
        parts.append('sin dato de calidad de cartera integrado')
    if pd.notna(liquidity_value):
        if '🟢' in str(liquidity_signal): parts.append('liquidez relativamente holgada')
        elif '🔴' in str(liquidity_signal): parts.append('liquidez que requiere revisión')
        else: parts.append('liquidez en rango intermedio')
    else:
        parts.append('liquidez financiera oficial no integrada')
    return '; '.join(parts) + '.'



CDT_BUCKETS = [
    ("A 30 días", 30),
    ("Entre 31 y 44 días", 37),
    ("A 45 días", 45),
    ("Entre 46 y 59 días", 52),
    ("A 60 días", 60),
    ("Entre 61 y 89 días", 75),
    ("A 90 días", 90),
    ("Entre 91 y 119 días", 105),
    ("A 120 días", 120),
    ("Entre 121 y 179 días", 150),
    ("A 180 días", 180),
    ("Entre 181 y 359 días", 270),
    ("A 360 días", 360),
    ("Superior a 360 días", 540),
]


def preferred_cdt_description(descriptions, days):
    """Escoge el rango oficial SFC más cercano al plazo de la simulación."""
    if not descriptions:
        return None
    normalized = {normalize_text(d): d for d in descriptions}
    candidates = []
    for label, mid in CDT_BUCKETS:
        n = normalize_text(label)
        # tolera codificación HTML defectuosa en el encabezado 91-119
        matches = [orig for nn, orig in normalized.items() if n == nn or ("91" in n and "119" in n and "91" in nn and "119" in nn)]
        if matches:
            candidates.append((abs(float(days)-mid), mid, matches[0]))
    if candidates:
        candidates.sort(key=lambda x:(x[0], x[1]))
        return candidates[0][2]
    return descriptions[0]


@st.cache_data(ttl=1800, show_spinner=False)
def load_sfc_public_rate_tables():
    """Carga directamente el comparador oficial de tasas pasivas de la SFC.

    Esta fuente es la visualización oficial dirigida a personas naturales y contiene
    las tablas de cuenta de ahorro y CDT. Se usa como fuente principal/fallback
    cuando el conjunto Socrata no permite identificar correctamente el producto.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
    }
    last_error = None
    page = None
    # Intento normal; si un proxy/certificado corporativo bloquea la validación SSL,
    # hacemos un segundo intento sin verificación de certificado.
    for verify_ssl in (True, False):
        try:
            r = requests.get(SFC_RATE_URL, headers=headers, timeout=40, verify=verify_ssl)
            r.raise_for_status()
            if r.text and len(r.text) > 1000:
                page = r.text
                break
        except Exception as e:
            last_error = e
    if page is None:
        raise RuntimeError(f"No fue posible consultar directamente el comparador SFC: {last_error}")

    m = re.search(r"Tasas efectivas anuales con corte al\s*(\d{4}-\d{2}-\d{2})", page, flags=re.I)
    cutoff = m.group(1) if m else datetime.now().strftime("%Y-%m-%d")

    tables = pd.read_html(StringIO(page))
    rows = []

    def flat_columns(df):
        out=[]
        for c in df.columns:
            if isinstance(c, tuple):
                vals=[str(x).strip() for x in c if str(x).strip() and not str(x).lower().startswith('unnamed')]
                out.append(vals[-1] if vals else str(c[-1]))
            else:
                out.append(str(c).strip())
        df=df.copy(); df.columns=out
        return df

    def parse_rate(v):
        if pd.isna(v): return None
        t=str(v).strip().replace('%','').replace('—','').replace('---','').strip()
        if not t: return None
        # SFC normally uses punto decimal; accept coma too.
        t=t.replace(' ','').replace(',','.')
        try: return float(t)
        except Exception: return None

    for raw in tables:
        if raw is None or raw.empty:
            continue
        df=flat_columns(raw)
        # detect entity column
        entity_col=None
        for c in df.columns:
            if normalize_text(c) in {'ENTIDAD','NOMBRE ENTIDAD'} or 'ENTIDAD' in normalize_text(c):
                entity_col=c; break
        if entity_col is None:
            continue
        normcols={c:normalize_text(c) for c in df.columns}
        is_savings=any('DEPOSITOS DE AHORRO ACTIVOS' in n or 'CUENTA DE AHORRO' in n for n in normcols.values())
        is_cdt=any('A 360 DIAS' in n or 'ENTRE 181 Y 359 DIAS' in n or 'A 90 DIAS' in n for n in normcols.values())
        if not (is_savings or is_cdt):
            continue
        prod='Cuenta de ahorro' if is_savings else 'CDT'
        for _, rr in df.iterrows():
            ent=clean_entity_name(rr.get(entity_col,''))
            if not ent or normalize_text(ent) in {'ENTIDAD','NAN'}:
                continue
            for c in df.columns:
                if c==entity_col:
                    continue
                rate=parse_rate(rr.get(c))
                if rate is None:
                    continue
                rows.append({
                    'fechacorte': cutoff+'T00:00:00.000',
                    'nombreentidad': ent,
                    'Entidad (visual)': ent,
                    'Segmento SFC': classify_sfc_segment(ent),
                    'descripcion': str(c).strip(),
                    'Texto producto': str(c).strip(),
                    'tasa': rate,
                    'monto': float('nan'),
                    'Producto detectado': prod,
                    'Plazo detectado (días)': extract_term_days(str(c)),
                    'Fuente tasa': 'Comparador oficial SFC',
                })
    out=pd.DataFrame(rows)
    if not out.empty:
        out=out.drop_duplicates(subset=['Entidad (visual)','descripcion','Producto detectado','tasa'])
    return out, cutoff


def load_embedded_sfc_snapshot():
    """Respaldo local con tasas oficiales SFC observadas al 2026-10-01.

    Se usa únicamente si el equipo no logra conectarse a Datos Abiertos ni al
    comparador web oficial. Esto evita dejar la app sin tasas durante una clase.
    La pantalla identifica claramente que se trata de un snapshot de respaldo.
    """
    cutoff = "2026-10-01"
    savings = {
        'RappiPay':5.93,'Av Villas':0.36,'BAN100 S.A.':9.93,
        'BANCO AGRARIO DE COLOMBIA o BANAGRARIO.':0.73,'BANCO CAJA SOCIAL':0.87,
        'BANCO CONTACTAR':10.00,'BANCO DE BOGOTÁ S.A.':0.49,'BANCO SERFINANZA S.A.':3.93,
        'BANCO UNIÓN S.A.':0.47,'BANCO W S.A.':2.31,'BBVA Colombia':0.40,
        'Bancamía S.A.':6.23,'Banco Davivienda':0.42,'Banco Falabella S.A.':3.16,
        'Banco GNB Sudameris':0.82,'Banco Mundo Mujer S.A.':2.75,'Banco Pichincha S.A.':11.00,
        'Banco Popular':2.51,'Banco Santander Colombia S.A.':0.00,'Banco de Occidente':1.94,
        'Bancolombia':0.07,'Bancoomeva':4.21,'CREZCAMOS S.A.':0.35,'Coltefinanciera':1.91,
        'DAVIBANK S.A. o DAVIBANK.':2.19,'FINANDINA BIC o BANCO FINANDINA BIC':6.48,
        'Financiera Juriscoop C.F.':1.83,'Itaú; Banco Itaú.':0.01,'LULO BANK':8.77,
        'Mibanco S.A.':1.86,'NU o NU Financiera':8.76
    }
    cdt360 = {
        'Av Villas':11.85,'BAN100 S.A.':12.88,'BANCO AGRARIO DE COLOMBIA o BANAGRARIO.':9.73,
        'BANCO CAJA SOCIAL':9.73,'BANCO CONTACTAR':12.53,'BANCO DE BOGOTÁ S.A.':12.12,
        'BANCO SERFINANZA S.A.':12.36,'BANCO UNIÓN S.A.':12.34,'BANCO W S.A.':12.84,
        'BBVA Colombia':11.64,'Bancamía S.A.':12.51,
        'Banco BTG Pactual Colombia, Banco BTG Pactual (Colombia)':13.19,
        'Banco Davivienda':10.73,'Banco Falabella S.A.':11.90,'Banco GNB Sudameris':12.26,
        'Banco Mundo Mujer S.A.':12.04,'Banco Pichincha S.A.':13.49,'Banco Popular':11.79,
        'Banco Santander Colombia S.A.':11.80,'Banco de Occidente':11.78,'Bancolombia':11.80,
        'Bancoomeva':11.32,'CREZCAMOS S.A.':11.90,'Coltefinanciera':11.83,
        'Credifamilia':12.68,'FINANDINA BIC o BANCO FINANDINA BIC':11.66,
        'Financiera Juriscoop C.F.':12.50,'IRIS CF':13.00,'LULO BANK':11.27,
        'Mibanco S.A.':12.42,'NU o NU Financiera':11.00,'Tuya':12.94
    }
    rows=[]
    for ent, rate in savings.items():
        ent2=clean_entity_name(ent)
        rows.append({
            'fechacorte':cutoff+'T00:00:00.000','nombreentidad':ent2,'Entidad (visual)':ent2,
            'Segmento SFC':classify_sfc_segment(ent2),'descripcion':'Depósitos de ahorro activos',
            'Texto producto':'Depósitos de ahorro activos','tasa':float(rate),'monto':float('nan'),
            'Producto detectado':'Cuenta de ahorro','Plazo detectado (días)':None,
            'Fuente tasa':'Snapshot oficial SFC integrado'
        })
    for ent, rate in cdt360.items():
        ent2=clean_entity_name(ent)
        rows.append({
            'fechacorte':cutoff+'T00:00:00.000','nombreentidad':ent2,'Entidad (visual)':ent2,
            'Segmento SFC':classify_sfc_segment(ent2),'descripcion':'A 360 días',
            'Texto producto':'A 360 días','tasa':float(rate),'monto':float('nan'),
            'Producto detectado':'CDT','Plazo detectado (días)':360,
            'Fuente tasa':'Snapshot oficial SFC integrado'
        })
    return pd.DataFrame(rows), cutoff

def prepare_product_rows(df, product):
    if df.empty:
        return df
    if product == "Cuenta de ahorro":
        out = df[df["Producto detectado"] == "Cuenta de ahorro"].copy()
    elif product == "CDT / CDAT":
        out = df[df["Producto detectado"].isin(["CDT", "CDAT"])].copy()
    else:
        out = df.copy()
    out = out[out["tasa"].notna()].copy()
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def find_recent_date_with_product(product, candidate_dates, max_checks=35):
    """Busca hacia atrás la fecha más reciente que sí contenga el producto elegido."""
    checked = 0
    for d in list(candidate_dates)[:max_checks]:
        try:
            temp = get_rows_for_date(d)
            checked += 1
            if temp is None or temp.empty:
                continue
            prod = prepare_product_rows(temp, product)
            if not prod.empty:
                return d, checked
        except Exception:
            checked += 1
            continue
    return None, checked


def force_data_refresh():
    """Vacía la caché de consultas y vuelve a pedir los datos abiertos."""
    st.cache_data.clear()
    st.session_state["refresh_counter"] = st.session_state.get("refresh_counter", 0) + 1



# ============================================================
# ENCABEZADO
# ============================================================
st.markdown(
    """
    <div class="hero">
      <div class="hero-title">🐷 Ahorro Inteligente — Simulador y Comparador SFC</div>
      <div class="hero-sub">Consulta datos abiertos oficiales de captación, mantiene visible el universo de entidades del segmento, compara tasas equivalentes y resume respaldo y señales financieras en lenguaje sencillo.</div>
      <div class="hero-line"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="edu-box"><b>Herramienta educativa.</b> Las tasas mostradas provienen del conjunto público de la Superintendencia Financiera disponible en Datos Abiertos Colombia. Son tasas reportadas/promedio del período y <b>no necesariamente equivalen a una oferta comercial vigente para una persona específica</b>. Antes de contratar, verifica directamente con la entidad condiciones, monto mínimo, plazo, costos, impuestos, disponibilidad y cobertura aplicable.</div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CARGA DE DATOS
# ============================================================
connection_error = None
available_dates = []
try:
    with st.spinner("Consultando fechas disponibles en Datos Abiertos Colombia..."):
        available_dates = get_available_dates()
except Exception as e:
    connection_error = str(e)

with st.sidebar:
    st.markdown("## 🔎 Consulta")
    product = st.selectbox("Producto", ["Cuenta de ahorro", "CDT / CDAT"])

    st.markdown("### Estado de la consulta")
    if available_dates:
        try:
            ultima = pd.to_datetime(available_dates[0]).strftime("%d/%m/%Y")
        except Exception:
            ultima = str(available_dates[0])
        st.success(f"Última fecha disponible detectada en la fuente: {ultima}")
        st.caption("La fecha más reciente del conjunto general puede no tener registros de todos los productos. La app valida el producto y, si es necesario, usa la fecha anterior más reciente con información comparable.")
    else:
        st.warning("No se pudo determinar una fecha disponible en la fuente.")
        if st.button("🔄 Actualizar datos", key="retry_data_tab", use_container_width=False):
            force_data_refresh()
            st.rerun()

    st.markdown("### Segmentación de entidades")
    segment_options = [
        "Todas las entidades reportantes SFC",
        "Establecimientos bancarios",
        "Compañías de financiamiento",
        "Cooperativas financieras",
        "Corporaciones financieras",
        "Otros reportantes SFC",
    ]
    segment_sel = st.selectbox(
        "Segmento",
        segment_options,
        index=1,
        help="Segmentación educativa por tipo de entidad. No implica recomendación ni evaluación de solvencia."
    )

    if available_dates:
        fecha_sel = st.selectbox(
            "Fecha de corte",
            available_dates,
            index=0,
            format_func=lambda x: pd.to_datetime(x).strftime("%d/%m/%Y") if x else "",
        )
    else:
        fecha_sel = None
        st.warning("No fue posible consultar el portal en este momento.")

    st.divider()
    st.markdown("## 💰 Simulación")
    capital = st.number_input("Capital inicial", min_value=0.0, value=10000000.0, step=500000.0)
    days = st.number_input("Plazo para comparar (días)", min_value=1, max_value=1825, value=360, step=30)
    aporte_mensual = st.number_input("Aporte mensual para simulación", min_value=0.0, value=500000.0, step=50000.0)
    meses_ahorro = st.slider("Horizonte de ahorro (meses)", 1, 120, 24)

    st.divider()
    st.markdown("## 🔄 Actualización de datos")
    st.caption("Si la consulta no trae registros o los datos parecen desactualizados, fuerza una nueva consulta al portal oficial.")
    if st.button("🔄 Actualizar datos ahora", use_container_width=True, type="primary"):
        force_data_refresh()
        st.rerun()
    st.caption("Fuentes: comparador oficial de tasas pasivas SFC + Datos Abiertos Colombia. La app usa automáticamente la fuente que tenga datos comparables.")

# Fuente de tasas para comparación educativa.
# IMPORTANTE: para Cuenta de ahorro y CDT se prioriza SIEMPRE el comparador
# oficial de tasas pasivas de la SFC, porque allí los productos y los rangos de
# plazo ya vienen homologados para personas naturales. Datos Abiertos queda como
# fuente complementaria y nunca vuelve a desplazar la tabla oficial con renglones
# contables o de red de oficinas que no son equivalentes al CDT del comparador.
raw_df = pd.DataFrame()
fecha_efectiva = fecha_sel
product_date_notice = None
rate_source = 'Comparador oficial SFC'
sfc_live_error = None

# 1) Comparador oficial SFC: fuente principal para tasas comparables.
try:
    with st.spinner('Consultando el comparador oficial de tasas pasivas de la SFC...'):
        sfc_page_df, sfc_cutoff = load_sfc_public_rate_tables()
    page_product = prepare_product_rows(sfc_page_df, product) if not sfc_page_df.empty else pd.DataFrame()
    if not page_product.empty:
        raw_df = sfc_page_df
        fecha_efectiva = sfc_cutoff + 'T00:00:00.000'
        rate_source = 'Comparador oficial SFC'
        connection_error = None
        if product == 'CDT / CDAT':
            product_date_notice = (
                f'Para la comparación de CDT/CDAT la app usa como referencia el CDT para personas naturales '
                f'publicado por la SFC, con corte al {pd.to_datetime(sfc_cutoff).strftime("%d/%m/%Y")}. '
                'Los rangos de plazo son los oficiales del comparador SFC.'
            )
except Exception as e:
    sfc_live_error = str(e)

# 2) Si la consulta web falla, usa el snapshot oficial integrado. Así CDT no queda vacío.
if raw_df.empty or prepare_product_rows(raw_df, product).empty:
    try:
        snap_df, snap_cutoff = load_embedded_sfc_snapshot()
        snap_product = prepare_product_rows(snap_df, product)
        if not snap_product.empty:
            raw_df = snap_df
            fecha_efectiva = snap_cutoff + 'T00:00:00.000'
            rate_source = 'Respaldo local SFC (01/10/2026)'
            product_date_notice = (
                'No fue posible recuperar en vivo el comparador SFC. La app está usando el respaldo local '
                f'de tasas oficiales con corte al {pd.to_datetime(snap_cutoff).strftime("%d/%m/%Y")}. '
                'Pulsa Actualizar datos para volver a intentar la consulta en línea.'
            )
            connection_error = None
    except Exception as snap_e:
        connection_error = f'Comparador SFC: {sfc_live_error or "sin datos"} | Respaldo local: {snap_e}'

# 3) Datos Abiertos queda como complemento únicamente si las dos fuentes anteriores fallan.
if raw_df.empty or prepare_product_rows(raw_df, product).empty:
    try:
        if fecha_sel:
            with st.spinner('Consultando Datos Abiertos como fuente complementaria...'):
                da_df = get_rows_for_date(fecha_sel)
            da_product = prepare_product_rows(da_df, product) if not da_df.empty else pd.DataFrame()
            if da_product.empty and available_dates:
                found_date, _ = find_recent_date_with_product(product, available_dates, max_checks=35)
                if found_date:
                    da_df = get_rows_for_date(found_date)
                    da_product = prepare_product_rows(da_df, product)
                    fecha_efectiva = found_date
            if not da_product.empty:
                raw_df = da_df
                rate_source = 'Datos Abiertos Colombia (fuente complementaria)'
                product_date_notice = (
                    'No fue posible usar el comparador SFC ni el respaldo local. Se muestran datos de la fuente '
                    'complementaria de Datos Abiertos; verifica que el renglón corresponda exactamente al producto.'
                )
                connection_error = None
    except Exception as e:
        connection_error = f'Comparador SFC: {sfc_live_error or "sin datos"} | Datos Abiertos: {e}'

# Universo reciente de entidades: evita que desaparezcan bancos por falta de dato
# en un renglón exacto o en una sola fecha.
recent_entity_df = pd.DataFrame(columns=['Entidad (visual)', 'Segmento SFC'])
if fecha_efectiva:
    try:
        recent_entity_df = get_recent_entity_universe(fecha_efectiva)
    except Exception:
        recent_entity_df = pd.DataFrame(columns=['Entidad (visual)', 'Segmento SFC'])
entity_universe = build_entity_universe(raw_df, recent_entity_df)

# ============================================================
# TABS
# ============================================================
tab_comp, tab_sim, tab_risk, tab_data, tab_guide = st.tabs([
    "1️⃣ Comparar tasas",
    "2️⃣ Simular ahorro",
    "3️⃣ Riesgo y respaldo",
    "4️⃣ Datos y fuente",
    "5️⃣ Guía para decidir",
])

# ============================================================
# TAB 1: COMPARADOR
# ============================================================
with tab_comp:
    st.markdown('## Comparador de tasas')
    if product_date_notice:
        st.info(product_date_notice)
    st.markdown(
        '<div class="edu-box"><b>La comparación usa primero el comparador oficial de tasas pasivas de la SFC.</b> Además separa el universo de entidades del segmento y las entidades que sí tienen una tasa comparable en el rango elegido. Por eso un banco puede aparecer con <b>Sin dato comparable</b> en vez de desaparecer.</div>',
        unsafe_allow_html=True,
    )

    if connection_error or raw_df.empty:
        st.error('No se encontraron datos en la consulta actual o no fue posible conectarse al portal de Datos Abiertos.')
        c_retry, c_info = st.columns([1, 2])
        with c_retry:
            if st.button('🔄 Actualizar datos', key='retry_compare', use_container_width=True, type='primary'):
                force_data_refresh()
                st.rerun()
        with c_info:
            st.info('El botón borra la caché local y vuelve a consultar la fuente oficial.')
        if connection_error:
            with st.expander('Detalle técnico'):
                st.code(connection_error)
    else:
        dfp = prepare_product_rows(raw_df, product)
        universe = entity_universe.copy()
        if segment_sel != 'Todas las entidades reportantes SFC':
            dfp = dfp[dfp['Segmento SFC'].eq(segment_sel)].copy()
            universe = universe[universe['Segmento SFC'].eq(segment_sel)].copy()

        entity_options = sorted(universe['Entidad (visual)'].dropna().astype(str).unique().tolist())
        if not entity_options:
            entity_options = sorted(dfp['Entidad (visual)'].dropna().astype(str).unique().tolist())
        # Selección compartida entre Comparar tasas, Simular ahorro y Riesgo y respaldo.
        valid_shared = [e for e in st.session_state.get('shared_entities', []) if e in entity_options]
        if st.session_state.get('shared_entities', []) != valid_shared:
            st.session_state['shared_entities'] = valid_shared
        entity_filter = st.multiselect(
            'Entidades a incluir (opcional)', entity_options,
            key='shared_entities', max_selections=8,
            help='La selección se conserva en Simular ahorro y Riesgo y respaldo. Déjalo vacío para ver todo el segmento.'
        )
        if entity_filter:
            st.markdown('<div class="selection-note"><b>Selección compartida activa:</b> estas mismas entidades se usarán automáticamente en Simular ahorro y Riesgo y respaldo.</div>', unsafe_allow_html=True)
        show_missing = st.checkbox(
            'Mostrar entidades del segmento aunque no tengan tasa en el renglón seleccionado', value=True,
            help='Una entidad sin tasa comparable no se excluye; se marca como Sin dato.'
        )
        if entity_filter:
            dfp = dfp[dfp['Entidad (visual)'].isin(entity_filter)].copy()
            universe = universe[universe['Entidad (visual)'].isin(entity_filter)].copy()

        if dfp.empty:
            st.warning('No se encontraron registros comparables para este producto, incluso después de revisar fechas recientes.')
            if not universe.empty:
                st.caption(f"El segmento contiene {universe['Entidad (visual)'].nunique()} entidades en el universo reciente. Esto no significa que no ofrezcan el producto; significa que la app no logró identificar un renglón comparable en las fechas revisadas.")
            c1,c2=st.columns(2)
            with c1:
                if st.button('🔄 Actualizar y buscar otra vez', key='retry_empty_product', type='primary', use_container_width=True):
                    force_data_refresh(); st.rerun()
            with c2:
                st.info('La actualización borra la caché y vuelve a consultar la fuente. Si la última fecha general no contiene CDT/CDAT, la app busca automáticamente una fecha anterior que sí los tenga.')
        else:
            cutoff = pd.to_datetime(fecha_efectiva).strftime('%d/%m/%Y')
            render_kpis([
                ('Fecha de corte', cutoff),
                ('Fuente de tasa', rate_source),
                ('Entidades con dato del producto', str(dfp['Entidad (visual)'].nunique())),
                ('Entidades en universo del segmento', str(universe['Entidad (visual)'].nunique() if not universe.empty else dfp['Entidad (visual)'].nunique())),
                ('Tasa máxima observada', tasa_txt(dfp['tasa'].max())),
            ])
            st.markdown('### 1. Escoge una categoría comparable')
            st.caption('Selecciona el mismo renglón para comparar productos equivalentes. Las entidades sin dato en ese renglón permanecen visibles.')
            desc_counts = (dfp.groupby('descripcion', dropna=False)
                .agg(Entidades=('Entidad (visual)', 'nunique'), Registros=('Entidad (visual)', 'size'))
                .reset_index())
            descriptions = desc_counts['descripcion'].dropna().astype(str).tolist()

            if product == 'CDT / CDAT' and rate_source.startswith('Comparador oficial SFC'):
                order_map = {normalize_text(lbl): i for i,(lbl,_) in enumerate(CDT_BUCKETS)}
                descriptions = sorted(
                    descriptions,
                    key=lambda d: next((i for n,i in order_map.items() if n == normalize_text(d) or ('91' in n and '119' in n and '91' in normalize_text(d) and '119' in normalize_text(d))), 999)
                )
                preferred = preferred_cdt_description(descriptions, days)
                default_idx = descriptions.index(preferred) if preferred in descriptions else 0
                st.caption(f'La app selecciona por defecto el rango SFC más cercano al plazo de simulación ({int(days)} días). Puedes cambiarlo.')
            else:
                desc_counts = desc_counts.sort_values(['Entidades','descripcion'], ascending=[False,True])
                descriptions = desc_counts['descripcion'].dropna().astype(str).tolist()
                default_idx = 0

            desc_sel = st.selectbox(
                'Categoría / renglón de captación', descriptions, index=default_idx,
                format_func=lambda x: f"{x} · {int(desc_counts.loc[desc_counts['descripcion'].eq(x), 'Entidades'].iloc[0])} entidades con dato"
            )
            comp = dfp[dfp['descripcion'].astype(str).eq(desc_sel)].copy()
            agg = comp.groupby(['Entidad (visual)','Segmento SFC'], as_index=False).agg(**{
                'Tasa EA (%)': ('tasa','max'), 'Monto reportado ($ miles)': ('monto','sum')})
            if show_missing and not universe.empty:
                agg = universe.merge(agg, on=['Entidad (visual)','Segmento SFC'], how='left')
            agg['Estado del dato'] = agg['Tasa EA (%)'].apply(lambda x: 'Disponible' if pd.notna(x) else 'Sin dato comparable en esta categoría/fecha')
            agg['Rendimiento estimado'] = agg['Tasa EA (%)'].apply(lambda t: projected_return(capital,t,days)[0] if pd.notna(t) else float('nan'))
            agg['Valor estimado al plazo'] = agg['Tasa EA (%)'].apply(lambda t: projected_return(capital,t,days)[1] if pd.notna(t) else float('nan'))
            detected_product = classify_product(desc_sel)
            risk_df = pd.DataFrame([deposit_protection_profile(r['Segmento SFC'], detected_product, capital) for _,r in agg.iterrows()])
            agg['Seguro de depósitos'] = risk_df['Fondo']
            agg['Cobertura estimada'] = risk_df['Nivel de protección']
            agg = agg.sort_values('Tasa EA (%)', ascending=False, na_position='last').reset_index(drop=True)
            # Columna nullable entera: evita error de pandas al asignar enteros
            # sobre una columna creada inicialmente como texto.
            agg['Posición por tasa'] = pd.Series(pd.NA, index=agg.index, dtype='Int64')
            mask_rate = agg['Tasa EA (%)'].notna()
            agg.loc[mask_rate, 'Posición por tasa'] = pd.array(
                range(1, int(mask_rate.sum()) + 1), dtype='Int64'
            )
            available_agg = agg[mask_rate].copy()
            if not available_agg.empty:
                best=available_agg.iloc[0]
                render_kpis([
                    ('Mayor tasa del renglón', tasa_txt(best['Tasa EA (%)'])),
                    ('Entidad asociada', str(best['Entidad (visual)'])),
                    (f'Rendimiento estimado en {days} días', moneda(best['Rendimiento estimado'])),
                    ('Entidades sin dato comparable', str(int(agg['Tasa EA (%)'].isna().sum()))),
                ])
            cols=['Posición por tasa','Entidad (visual)','Segmento SFC','Estado del dato','Tasa EA (%)','Monto reportado ($ miles)','Rendimiento estimado','Valor estimado al plazo','Seguro de depósitos','Cobertura estimada']
            st.dataframe(agg[cols].style.format({
                'Tasa EA (%)': lambda x: 'N/D' if pd.isna(x) else f'{x:.2f}%',
                'Monto reportado ($ miles)': lambda x: 'N/D' if pd.isna(x) else f'{x:,.0f}',
                'Rendimiento estimado': lambda x: 'N/D' if pd.isna(x) else moneda(x),
                'Valor estimado al plazo': lambda x: 'N/D' if pd.isna(x) else moneda(x),
            }), use_container_width=True, hide_index=True, height=560)
            st.caption('La ausencia de tasa en un renglón no significa que la entidad no ofrezca el producto; solo que no hay dato comparable en esa categoría y fecha.')

# ============================================================
# TAB 2: SIMULADOR
# ============================================================
with tab_sim:
    st.markdown("## Simular el crecimiento del ahorro")

    if raw_df.empty:
        st.info("Cuando la consulta en línea esté disponible, podrás seleccionar tasas reportadas y simular escenarios.")
    else:
        dfp = prepare_product_rows(raw_df, product)
        if segment_sel != "Todas las entidades reportantes SFC":
            dfp = dfp[dfp["Segmento SFC"].eq(segment_sel)].copy()
        if not dfp.empty:
            by_entity = (
                dfp.groupby(["Entidad (visual)", "Segmento SFC"], as_index=False)
                .agg(**{"Tasa EA (%)": ("tasa", "max")})
                .dropna()
                .sort_values("Tasa EA (%)", ascending=False)
            )
            options = by_entity["Entidad (visual)"].tolist()
            shared = [e for e in st.session_state.get('shared_entities', []) if e in options]
            if shared:
                selected_entities = shared
                st.markdown('<div class="selection-note"><b>Filtro sincronizado:</b> se están simulando las mismas entidades elegidas en <b>Comparar tasas</b>.</div>', unsafe_allow_html=True)
                st.write("**Entidades seleccionadas:** " + " · ".join(selected_entities))
            else:
                selected_entities = options[: min(3, len(options))]
                st.info("No seleccionaste entidades en Comparar tasas. Para mostrar un ejemplo, se usan hasta 3 entidades con datos disponibles. Si eliges bancos en la primera pestaña, este módulo se filtrará automáticamente.")

            if selected_entities:
                rows = []
                for ent in selected_entities:
                    rate = float(by_entity.loc[by_entity["Entidad (visual)"].eq(ent), "Tasa EA (%)"].iloc[0])
                    final = future_value_monthly(capital, aporte_mensual, rate, meses_ahorro)
                    aportado = capital + aporte_mensual * meses_ahorro
                    rows.append({
                        "Entidad": ent,
                        "Tasa usada EA (%)": rate,
                        "Capital inicial": capital,
                        "Aportes acumulados": aporte_mensual * meses_ahorro,
                        "Valor estimado final": final,
                        "Rendimiento estimado": final - aportado,
                    })
                sim = pd.DataFrame(rows).sort_values("Valor estimado final", ascending=False)
                st.dataframe(
                    sim.style.format({
                        "Tasa usada EA (%)": "{:.2f}%",
                        "Capital inicial": lambda x: moneda(x),
                        "Aportes acumulados": lambda x: moneda(x),
                        "Valor estimado final": lambda x: moneda(x),
                        "Rendimiento estimado": lambda x: moneda(x),
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
                render_modern_savings_charts(sim, capital, aporte_mensual, meses_ahorro)
                render_bank_profiles(selected_entities, "Resumen de los bancos seleccionados")
                st.markdown('<div class="warn"><b>Importante:</b> para esta simulación se usa la mayor tasa reportada encontrada para cada entidad dentro del producto seleccionado. Esto sirve para explorar sensibilidad, pero no garantiza que esa tasa aplique al monto, plazo o perfil del usuario. Para una comparación contractual, usa la categoría exacta en la pestaña <b>Comparar tasas</b>.</div>', unsafe_allow_html=True)

# ============================================================
# TAB 3: RIESGO Y RESPALDO
# ============================================================
with tab_risk:
    st.markdown('## Riesgo y respaldo — lectura sencilla por entidad')
    st.markdown(
        '<div class="edu-box"><b>Basado en la presentación de la Sesión 2:</b> revisamos 1) quién supervisa, 2) qué respaldo tiene el depósito, 3) cuándo puedes disponer del dinero y 4) qué señales financieras públicas conviene observar: solvencia, liquidez y calidad de cartera.</div>',
        unsafe_allow_html=True,
    )
    risk_universe = entity_universe.copy()
    if segment_sel != 'Todas las entidades reportantes SFC':
        risk_universe = risk_universe[risk_universe['Segmento SFC'].eq(segment_sel)].copy()
    if risk_universe.empty and not raw_df.empty:
        risk_universe = raw_df[['Entidad (visual)','Segmento SFC']].drop_duplicates().copy()
        if segment_sel != 'Todas las entidades reportantes SFC':
            risk_universe = risk_universe[risk_universe['Segmento SFC'].eq(segment_sel)].copy()
    ent_options = sorted(risk_universe['Entidad (visual)'].dropna().astype(str).unique().tolist())
    shared_risk = [e for e in st.session_state.get('shared_entities', []) if e in ent_options]
    if shared_risk:
        selected_risk = shared_risk
        st.markdown('<div class="selection-note"><b>Filtro sincronizado:</b> el análisis de riesgo usa las mismas entidades elegidas en <b>Comparar tasas</b>.</div>', unsafe_allow_html=True)
        st.write("**Entidades analizadas:** " + " · ".join(selected_risk))
    else:
        selected_risk = ent_options[:min(8,len(ent_options))]
        st.info('No hay una selección activa en Comparar tasas. Se muestra una muestra del segmento. Elige bancos en la primera pestaña para sincronizar el análisis.')

    if selected_risk:
        render_bank_profiles(selected_risk, 'Perfil institucional de las entidades analizadas')
        with st.spinner('Consultando señales financieras públicas...'):
            solv_df = load_solvency_snapshot(); quality_df = load_portfolio_quality_snapshot()
        dfp_r = prepare_product_rows(raw_df, product) if not raw_df.empty else pd.DataFrame()
        if not dfp_r.empty:
            rate_rep=(dfp_r[dfp_r['Entidad (visual)'].isin(selected_risk)]
                .groupby(['Entidad (visual)','Segmento SFC'],as_index=False).agg(**{'Tasa EA (%)':('tasa','max')}))
        else:
            rate_rep=pd.DataFrame(columns=['Entidad (visual)','Segmento SFC','Tasa EA (%)'])
        base_entities=risk_universe[risk_universe['Entidad (visual)'].isin(selected_risk)].copy()
        base_entities=base_entities.merge(rate_rep,on=['Entidad (visual)','Segmento SFC'],how='left')
        rows=[]
        for _,rr in base_entities.iterrows():
            ent=rr['Entidad (visual)']; seg=rr['Segmento SFC']
            sol_val,sol_date=float('nan'),'N/D'
            if not solv_df.empty:
                m=best_entity_match(ent,solv_df['Entidad SFC'].astype(str).tolist())
                if m:
                    srow=solv_df[solv_df['Entidad SFC'].astype(str).eq(m)].iloc[0]
                    sol_val=pd.to_numeric(srow.get('Solvencia (%)'),errors='coerce'); sol_date=str(srow.get('Fecha solvencia','N/D'))
            quality_val,quality_date,quality_type=float('nan'),'N/D','N/D'
            if not quality_df.empty:
                mq=best_entity_match(ent,quality_df['Entidad SFC'].astype(str).tolist())
                if mq:
                    qrow=quality_df[quality_df['Entidad SFC'].astype(str).eq(mq)].iloc[0]
                    quality_val=pd.to_numeric(qrow.get('Calidad cartera (%)'),errors='coerce'); quality_date=str(qrow.get('Fecha calidad','N/D')); quality_type=str(qrow.get('Tipo calidad','N/D'))
            liquidity_val=float('nan'); liquidity_date='N/D'; liquidity_type='IRL / CFEN oficial no integrado automáticamente'
            prod_for_cover='Cuenta de ahorro' if product=='Cuenta de ahorro' else 'CDT'
            prof=deposit_protection_profile(seg,prod_for_cover,capital)
            rows.append({
                'Entidad':ent,'Tipo de entidad':seg,'Tasa EA (%)':rr.get('Tasa EA (%)'),
                'Supervisión':'SFC · entidad reportante en fuente oficial reciente',
                'Seguro depósitos':prof['Fondo'],'Cobertura estimada':prof['Nivel de protección'],'Monto cubierto estimado':prof['Monto cubierto estimado'],
                'Disponibilidad del dinero':product_access_summary(product,days),
                'Solvencia (%)':sol_val,'Liquidez (IRL/CFEN)':liquidity_val,'Calidad cartera (%)':quality_val,
                'Fecha solvencia':sol_date,'Fecha liquidez':liquidity_date,'Fecha calidad':quality_date,'Tipo liquidez':liquidity_type,'Tipo calidad':quality_type})
        risk_table=pd.DataFrame(rows)
        if not risk_table.empty:
            risk_table['Señal solvencia']=[relative_signal(risk_table['Solvencia (%)'],v,True) for v in risk_table['Solvencia (%)']]
            risk_table['Señal liquidez']=[relative_signal(risk_table['Liquidez (IRL/CFEN)'],v,True) for v in risk_table['Liquidez (IRL/CFEN)']]
            risk_table['Señal calidad']=[relative_signal(risk_table['Calidad cartera (%)'],v,False) for v in risk_table['Calidad cartera (%)']]
            def sw(sig,missing=False):
                if missing:return 'Dato por completar'
                if '🟢' in str(sig):return 'Señal favorable en la muestra'
                if '🔴' in str(sig):return 'Conviene revisar'
                return 'Señal intermedia en la muestra'
            risk_table['Solvencia sencilla']=[sw(s,pd.isna(v)) for s,v in zip(risk_table['Señal solvencia'],risk_table['Solvencia (%)'])]
            risk_table['Liquidez sencilla']=[sw(s,pd.isna(v)) for s,v in zip(risk_table['Señal liquidez'],risk_table['Liquidez (IRL/CFEN)'])]
            risk_table['Cartera sencilla']=[sw(s,pd.isna(v)) for s,v in zip(risk_table['Señal calidad'],risk_table['Calidad cartera (%)'])]
            risk_table['Señales financieras']=risk_table.apply(lambda r: plain_financial_signal(r['Señal solvencia'],r['Señal calidad'],r['Señal liquidez'],r['Solvencia (%)'],r['Calidad cartera (%)'],r['Liquidez (IRL/CFEN)']),axis=1)
            def overall(r):
                rate='sin tasa comparable en la selección actual' if pd.isna(r['Tasa EA (%)']) else f"tasa observada {r['Tasa EA (%)']:.2f}% EA"
                return f"Supervisada/reportante ante la SFC; respaldo de depósito: {r['Seguro depósitos']}; {rate}. {r['Señales financieras']}"
            def review(r):
                items=['condiciones reales del producto','cobertura aplicable al depósito']
                if pd.isna(r['Liquidez (IRL/CFEN)']):items.append('IRL/CFEN oficial')
                if pd.isna(r['Solvencia (%)']):items.append('solvencia actualizada')
                if pd.isna(r['Calidad cartera (%)']):items.append('calidad de cartera actualizada')
                return '; '.join(items)
            risk_table['Resumen para una persona']=risk_table.apply(overall,axis=1)
            risk_table['Qué revisar antes de elegir']=risk_table.apply(review,axis=1)
            st.markdown('### Resumen por entidad')
            st.caption('Los cuatro criterios de la diapositiva se muestran en lenguaje sencillo.')
            simple_cols=['Entidad','Tasa EA (%)','Supervisión','Seguro depósitos','Cobertura estimada','Disponibilidad del dinero','Solvencia sencilla','Liquidez sencilla','Cartera sencilla','Resumen para una persona','Qué revisar antes de elegir']
            st.dataframe(risk_table[simple_cols].style.format({'Tasa EA (%)':lambda x:'N/D' if pd.isna(x) else f'{x:.2f}%'}),use_container_width=True,hide_index=True,height=600)
            st.markdown('### Explicación individual')
            ent_detail=st.selectbox('Entidad para explicar',risk_table['Entidad'].tolist(),key='risk_entity_detail_v8')
            erow=risk_table[risk_table['Entidad'].eq(ent_detail)].iloc[0]
            detail_html = (
                f"<div class='risk-summary'><b>{ent_detail}</b><br><br>"
                f"<b>1. Supervisión:</b> {erow['Supervisión']}<br>"
                f"<b>2. Respaldo del depósito:</b> {erow['Seguro depósitos']} - {erow['Cobertura estimada']} - monto cubierto estimado {moneda(erow['Monto cubierto estimado'])}.<br>"
                f"<b>3. Disponibilidad:</b> {erow['Disponibilidad del dinero']}<br>"
                f"<b>4. Señales financieras:</b> {erow['Señales financieras']}<br><br>"
                f"<b>Lectura final:</b> {erow['Resumen para una persona']}<br>"
                f"<b>Antes de elegir:</b> {erow['Qué revisar antes de elegir']}</div>"
            )
            st.markdown(detail_html,unsafe_allow_html=True)
            with st.expander('📊 Ver datos técnicos que soportan el resumen',expanded=False):
                tech=['Entidad','Solvencia (%)','Señal solvencia','Fecha solvencia','Liquidez (IRL/CFEN)','Señal liquidez','Fecha liquidez','Calidad cartera (%)','Señal calidad','Fecha calidad','Tipo calidad','Seguro depósitos','Cobertura estimada']
                st.dataframe(risk_table[tech].style.format({
                    'Solvencia (%)':lambda x:'N/D' if pd.isna(x) else f'{x:.2f}%',
                    'Liquidez (IRL/CFEN)':lambda x:'N/D' if pd.isna(x) else f'{x:.2f}',
                    'Calidad cartera (%)':lambda x:'N/D' if pd.isna(x) else f'{x:.2f}%'}),use_container_width=True,hide_index=True,height=520)
                st.caption('N/D significa que la app no logró integrar automáticamente un dato oficial comparable. No se interpreta como una señal negativa.')
            st.info('Objetivo educativo: comprender el nivel de información disponible. La aplicación no etiqueta entidades como buenas o malas ni sustituye una calificación oficial.')

# ============================================================
# TAB 4: DATOS Y FUENTE
# ============================================================
with tab_data:
    st.markdown("## Datos abiertos y trazabilidad")
    st.markdown(
        f'''<div class="source"><b>Conjunto:</b> Tasas de interés de captación y operaciones del mercado monetario.<br><b>Proveedor:</b> Superintendencia Financiera de Colombia.<br><b>ID del recurso:</b> {SOCRATA_DATASET_ID}<br><b>API:</b> {SOCRATA_API}<br><b>Página del conjunto:</b> {DATASET_URL}<br><b>Consulta pública SFC:</b> {SFC_RATE_URL}</div>''',
        unsafe_allow_html=True,
    )
    st.markdown("### Segmentación de entidades")
    st.info(
        "La aplicación permite filtrar por establecimientos bancarios, compañías de financiamiento, "
        "cooperativas financieras, corporaciones financieras y otros reportantes. La segmentación es "
        "solo una ayuda de navegación; todas las tasas mostradas siguen viniendo del conjunto oficial de la SFC."
    )

    st.markdown("### Qué campos utiliza la aplicación")
    st.markdown("- `NOMBREENTIDAD`: entidad reportante.\n- `FECHACORTE`: fecha del reporte.\n- `DESCRIPCION`: renglón/producto/plazo reportado.\n- `TASA`: tasa informada en el conjunto.\n- `MONTO`: monto reportado por la fuente, cuando está disponible.")

    if not raw_df.empty:
        st.markdown("### Explorador de descripciones")
        keyword = st.text_input("Buscar en descripción", value="")
        explore = raw_df.copy()
        if keyword.strip():
            explore = explore[explore["descripcion"].astype(str).str.contains(keyword, case=False, na=False)]
        cols = [c for c in ["Entidad (visual)", "Segmento SFC", "nombreentidad", "fechacorte", "descripcion", "tasa", "monto", "Producto detectado", "Plazo detectado (días)"] if c in explore.columns]
        st.dataframe(explore[cols].head(300), use_container_width=True, hide_index=True, height=480)

        csv = explore[cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Descargar vista en CSV", csv, "tasas_captacion_vista.csv", "text/csv")

# ============================================================
# TAB 5: GUÍA
# ============================================================
with tab_guide:
    st.markdown("## Guía para comparar un ahorro")
    st.markdown("""
    Antes de escoger una alternativa, revisa al menos:
    1. **Producto y plazo comparables:** una cuenta de ahorro no tiene la misma liquidez que un CDT/CDAT.
    2. **Tasa efectiva anual y forma de pago de rendimientos.**
    3. **Monto mínimo y condiciones de apertura.**
    4. **Disponibilidad del dinero:** retiros, penalidades o vencimiento.
    5. **Costos, impuestos y retenciones aplicables.**
    6. **Cobertura y naturaleza de la entidad/producto.**
    7. **Fecha de la tasa:** las tasas cambian en el tiempo.
    8. **Seguro de depósitos:** identifica si aplica Fogafín o Fogacoop y cuánto del monto queda cubierto.
    9. **Calificación externa:** si existe, revisa agencia, escala, fecha y tipo de obligación; no te quedes solo con las letras.
    """)

    prompt = f"""Actúa como facilitador de educación financiera. No tomes la decisión por mí.
Ayúdame a comparar alternativas de ahorro usando información oficial y a identificar qué debo verificar antes de contratar.

Datos de mi simulación:
- Capital inicial: {moneda(capital)}
- Aporte mensual: {moneda(aporte_mensual)}
- Horizonte: {meses_ahorro} meses
- Producto que estoy explorando: {product}
- Segmento de entidades: {segment_sel}
- Fecha de corte de los datos: {pd.to_datetime(fecha_efectiva).strftime('%d/%m/%Y') if fecha_efectiva else 'No disponible'}

Quiero que me ayudes a:
1. Explicar las diferencias entre las alternativas de forma sencilla.
2. Comparar tasa, liquidez, plazo y disponibilidad del dinero.
3. Señalar qué información contractual todavía debo verificar con cada entidad.
4. Mostrar los riesgos de comparar solo por la tasa.
5. Proponer escenarios que sea útil simular.

No me digas en qué entidad ahorrar ni cuál producto escoger. Ayúdame a analizar la información."""
    st.markdown("### Prompt sugerido para IA")
    st.code(prompt, language=None)

st.divider()
st.caption("Ahorro Inteligente v14 · Herramienta educativa. Fuente de tasas: Datos Abiertos Colombia / Superintendencia Financiera de Colombia. El universo de entidades se construye con reportantes recientes para no ocultar bancos sin dato en una categoría puntual. Las simulaciones son aproximaciones y no constituyen asesoría financiera ni una oferta comercial.")
