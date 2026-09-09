import requests
import streamlit as st
import pandas as pd

# Physical and financial constants used throughout the calculations
DAYS_PER_YEAR             = 365
KG_PER_TON                = 1_000
CARBON_FACTOR_KG_PER_KWH  = 0.82       # India grid average (CEA 2023)
PANEL_POWER_DENSITY_KW_M2 = 0.20       # 0.2 kW per m² — standard installer basis
MAINTENANCE_COST_PER_KW   = 500        # ₹500/kWp/year for O&M
DEFAULT_IRRADIANCE        = 4.8        # kWh/m²/day — conservative India-wide fallback
NOMINATIM_USER_AGENT      = "SolarPVAnalyzer/5.0"
RETRYABLE_STATUS_CODES    = {429, 500, 502, 503, 504}
API_MAX_RETRIES           = 2
API_BASE_DELAY_S          = 0.8        # short enough not to visibly block the UI


# ── Pure utilities — no Streamlit, safe to unit-test independently ────────────

def format_inr(amount: float) -> str:
    """Display rupee amounts in Crores, Lakhs, or plain — whichever fits."""
    if amount >= 1e7:
        return f"₹ {amount / 1e7:.2f} Cr"
    if amount >= 1e5:
        return f"₹ {amount / 1e5:.2f} L"
    return f"₹ {amount:,.0f}"


def calculate_solar_metrics(
    df: pd.DataFrame,
    irradiance: float,
    efficiency: float,
    loss_factor: float,
    usage_factor: float,
    elec_rate: float,
) -> pd.DataFrame:
    """
    Add solar output and financial columns to the buildings DataFrame.

    usage_factor scales the installed system size (how much roof is usable).
    """
    df = df.copy()

    conversion_factor = efficiency * (1 - loss_factor) * usage_factor * DAYS_PER_YEAR
    kwh_per_m2_year   = irradiance * conversion_factor

    area                                = df["Area"]
    df["System Size (kW)"]              = area * PANEL_POWER_DENSITY_KW_M2 * usage_factor
    df["Estimated Annual Energy (kWh)"] = area * kwh_per_m2_year
    df["CO2 Offset (tCO2e)"]            = df["Estimated Annual Energy (kWh)"] * CARBON_FACTOR_KG_PER_KWH / KG_PER_TON
    annual_om                           = df["System Size (kW)"] * MAINTENANCE_COST_PER_KW
    df["Financial Savings (₹)"]         = (df["Estimated Annual Energy (kWh)"] * elec_rate) - annual_om

    return df


def clean_input(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """
    Normalise column names, drop bad rows, and deduplicate building names.
    Returns the cleaned DataFrame plus counts of rows dropped for NaN and negative area.
    """
    df = df.copy()
    df.columns = df.columns.str.strip().str.title()   # accepts 'area', 'AREA', 'Area', etc.

    df["Area"]  = pd.to_numeric(df["Area"], errors="coerce")
    nan_dropped = int(df["Area"].isna().sum())
    df          = df.dropna(subset=["Area"])

    neg_mask    = df["Area"] <= 0
    neg_dropped = int(neg_mask.sum())
    df          = df[~neg_mask].reset_index(drop=True)

    # Rename duplicates to "Block A (2)", "Block A (3)" so users spot them easily
    if df["Building"].duplicated().any():
        counts = df.groupby("Building").cumcount()
        df["Building"] = df.apply(
            lambda r: f"{r['Building']} ({int(counts[r.name]) + 1})" if counts[r.name] > 0 else r["Building"],
            axis=1,
        )

    return df, nan_dropped, neg_dropped


# ── External API calls — no Streamlit, safe to unit-test independently ────────

_session = requests.Session()
_session.headers.update({"User-Agent": NOMINATIM_USER_AGENT})


def _request_with_retry(url: str, params: dict, timeout: int = 10) -> requests.Response:
    import time
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(API_MAX_RETRIES):
        try:
            resp = _session.get(url, params=params, timeout=timeout)
            if resp.status_code in RETRYABLE_STATUS_CODES:
                raise requests.HTTPError(f"Retryable status {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_exc = exc
            if attempt < API_MAX_RETRIES - 1:
                time.sleep(API_BASE_DELAY_S * (attempt + 1))
    raise last_exc


def geocode_city(location_query: str) -> tuple[float | None, float | None, str | None]:
    try:
        resp = _request_with_retry(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location_query.strip(), "format": "json", "limit": 1},
            timeout=8,
        )
        data = resp.json()
        if data:
            short_label = data[0]["display_name"].split(",")[0].strip()
            return float(data[0]["lat"]), float(data[0]["lon"]), short_label
    except Exception:
        pass
    return None, None, None


def fetch_annual_irradiance(lat: float, lon: float) -> float:
    try:
        resp = _request_with_retry(
            "https://power.larc.nasa.gov/api/temporal/climatology/point",
            params={
                "parameters": "ALLSKY_SFC_SW_DWN",
                "community":  "RE",
                "longitude":  lon,
                "latitude":   lat,
                "format":     "JSON",
            },
            timeout=8,
        )
        annual_val = resp.json()["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].get("ANN")
        if annual_val and float(annual_val) > 0:
            return float(annual_val)
    except Exception:
        pass
    return DEFAULT_IRRADIANCE


# ── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Solar Insights Dashboard",
    page_icon="☀️",
    layout="wide",
)

st.markdown("<style>footer { visibility: hidden; }</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False, ttl=86_400)
def _geocode(location_query: str) -> tuple:
    return geocode_city(location_query)


@st.cache_data(show_spinner=False, ttl=86_400)
def _irradiance(lat: float, lon: float) -> float:
    return fetch_annual_irradiance(lat, lon)


with st.sidebar:
    st.title("⚙️ Configuration")

    with st.form("settings_form"):
        st.header("📍 Project Location")
        location_query = st.text_input(
            "City / Location",
            "Ranchi, India",
            help='Type any location, e.g. "Tokyo, Japan" or "Berlin" or "Mumbai"',
        ).strip()

        st.header("💰 Cost Settings")
        elec_rate = st.number_input(
            "Electricity Tariff (₹/kWh)", value=7.50, step=0.10, format="%.2f"
        )

        st.header("🔧 System Parameters")
        efficiency   = st.slider("PV Panel Efficiency (%)",           10, 25,  18) / 100
        loss_factor  = st.slider("System Derate / Loss Factor (%)",     5, 40,  15) / 100
        usage_factor = st.slider("Rooftop Utilisation (%)",           10, 100, 70) / 100

        st.form_submit_button("▶ Update Analysis", use_container_width=True)

    st.header("📂 Upload Rooftop Data")
    uploaded_file = st.file_uploader("Upload Rooftop Dataset (CSV)", type=["csv"])


st.title("Solar Energy Potential Dashboard")

lat, lon, city_label = _geocode(location_query)

if lat is None:
    st.warning(f"⚠️ Could not geocode **{location_query}**. Using default irradiance.")
    irradiance = DEFAULT_IRRADIANCE
else:
    irradiance = _irradiance(lat, lon)
    st.success(f"📍 **{city_label}** — Annual Average GHI: **{irradiance:.2f} kWh/m²/day**")

df_raw: pd.DataFrame | None = None

if "manual_df" in st.session_state:
    df_raw = st.session_state["manual_df"].copy()

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file)
    st.session_state.pop("manual_df", None)

if df_raw is None:
    st.info("**Getting started:** Upload a CSV via the sidebar.")
    st.stop()

df_clean, nan_dropped, neg_dropped = clean_input(df_raw)

if "Building" not in df_clean.columns or "Area" not in df_clean.columns:
    st.error("❌ CSV must contain **Building** and **Area** columns.")
    st.stop()

df_result = calculate_solar_metrics(
    df_clean, irradiance, efficiency, loss_factor, usage_factor, elec_rate
)

total_area     = df_result["Area"].sum()
total_capacity = df_result["System Size (kW)"].sum()
total_gen      = df_result["Estimated Annual Energy (kWh)"].sum()
total_co2      = df_result["CO2 Offset (tCO2e)"].sum()
total_savings  = df_result["Financial Savings (₹)"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Area",             f"{total_area:,.0f} m²")
c2.metric("System Capacity",        f"{total_capacity:,.0f} kWp")
c3.metric("Estimated Annual Energy", f"{total_gen:,.0f} kWh")
c4.metric("Carbon Emission Reduction", f"{total_co2:,.1f} tCO₂e")
c5.metric("Estimated Annual Savings", format_inr(total_savings))

st.subheader("📊 Energy & Financial Projections")
tab1, tab2 = st.tabs(["Energy Generation", "Financial Impact"])

chart_base = df_result.set_index("Building")

with tab1:
    st.bar_chart(chart_base["Estimated Annual Energy (kWh)"], color="#1c3d5a")
with tab2:
    st.bar_chart(chart_base["Financial Savings (₹)"], color="#f0a500")

st.subheader("📋 System Breakdown")
st.dataframe(
    df_result[[
        "Building", "Area", "System Size (kW)",
        "Estimated Annual Energy (kWh)", "CO2 Offset (tCO2e)",
        "Financial Savings (₹)",
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Area":                          st.column_config.NumberColumn("Area (m²)",        format="%.0f"),
        "System Size (kW)":              st.column_config.NumberColumn("Capacity (kWp)",   format="%.1f"),
        "Estimated Annual Energy (kWh)": st.column_config.NumberColumn("Generation (kWh)", format="%,.0f"),
        "CO2 Offset (tCO2e)":            st.column_config.NumberColumn("CO₂ (tCO₂e)",      format="%.2f"),
        "Financial Savings (₹)":         st.column_config.NumberColumn("Net Savings (₹)",  format="₹%,.0f"),
    },
)

st.download_button(
    label="📥 Download Full Analysis (CSV)",
    data=df_result.to_csv(index=False).encode("utf-8"),
    file_name="solar_analysis.csv",
    mime="text/csv",
    use_container_width=True,
)