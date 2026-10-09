from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

st.set_page_config(page_title="DASH | Demand forecast", page_icon="🐕", layout="wide")

DATE_COLUMNS = ("order_created_at", "Created at", "created_at", "date", "Date")
QUANTITY_COLUMNS = ("quantity", "Lineitem quantity", "Quantity", "units", "Units")
SKU_COLUMNS = ("sku", "Lineitem sku", "SKU", "product", "Lineitem name")
ORDER_COLUMNS = ("order_id", "Name", "Order ID", "order_number")


def first_present(columns, candidates):
    normalized = {str(column).strip().casefold(): column for column in columns}
    for candidate in candidates:
        if candidate.strip().casefold() in normalized:
            return normalized[candidate.strip().casefold()]
    return None


@st.cache_data(show_spinner=False)
def read_csv(file_data: bytes) -> pd.DataFrame:
    return pd.read_csv(__import__("io").BytesIO(file_data))


def prepare_orders(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    date_col = first_present(raw.columns, DATE_COLUMNS)
    qty_col = first_present(raw.columns, QUANTITY_COLUMNS)
    sku_col = first_present(raw.columns, SKU_COLUMNS)
    order_col = first_present(raw.columns, ORDER_COLUMNS)
    if not date_col or not qty_col:
        raise ValueError(
            "The CSV needs a date column (for example order_created_at or Created at) "
            "and a quantity column (quantity or Lineitem quantity)."
        )

    data = pd.DataFrame(
        {
            "date": pd.to_datetime(raw[date_col], errors="coerce", utc=True).dt.tz_localize(None),
            "quantity": pd.to_numeric(raw[qty_col], errors="coerce"),
            "sku": raw[sku_col].fillna("Unspecified") if sku_col else "All products",
            "order_id": raw[order_col].astype(str) if order_col else raw.index.astype(str),
        }
    )
    data = data.dropna(subset=["date", "quantity"])
    data = data[data["quantity"] > 0].copy()
    data["date"] = data["date"].dt.normalize()
    return data, {"date": date_col, "quantity": qty_col, "sku": sku_col, "order": order_col}


def make_forecast(daily: pd.DataFrame, growth_pct: float, horizon: int) -> pd.DataFrame:
    full_dates = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    history = daily.set_index("date").reindex(full_dates, fill_value=0).rename_axis("date").reset_index()
    baseline = history["actual_units"].mean()
    if baseline <= 0:
        raise ValueError("The selected data has no positive demand to forecast.")

    calendar_mean = history.groupby(history["date"].dt.day)["actual_units"].mean()
    factors = (calendar_mean / baseline).clip(lower=0.50, upper=2.00)
    future_dates = pd.date_range(history["date"].max() + pd.Timedelta(days=1), periods=horizon, freq="D")
    forecast = pd.DataFrame({"date": future_dates})
    forecast["seasonality_factor"] = forecast["date"].dt.day.map(factors).fillna(1.0)
    forecast["forecast_units"] = baseline * (1 + growth_pct / 100) * forecast["seasonality_factor"]
    forecast["forecast_units"] = forecast["forecast_units"].round(1)
    forecast["forecast_day"] = range(1, horizon + 1)
    return forecast


def weekly_summary(history: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    actual = history.rename(columns={"actual_units": "units"})[["date", "units"]].assign(period="Actual")
    planned = forecast.rename(columns={"forecast_units": "units"})[["date", "units"]].assign(period="Forecast")
    combined = pd.concat([actual, planned], ignore_index=True)
    combined["week_start"] = combined["date"] - pd.to_timedelta(combined["date"].dt.weekday, unit="D")
    return (
        combined.groupby(["week_start", "period"], as_index=False)["units"]
        .sum()
        .rename(columns={"units": "weekly_units"})
        .sort_values("week_start")
    )


def chicken_purchase_plan(
    forecast_boxes: float, box_weight_kg: float, chicken_unit_lb: float, chicken_pct: float
) -> dict:
    total_food_kg = forecast_boxes * box_weight_kg
    chicken_kg = total_food_kg * (chicken_pct / 100)
    chicken_lb = chicken_kg * 2.2046226218
    chicken_units = chicken_lb / chicken_unit_lb
    return {
        "total_food_kg": total_food_kg,
        "chicken_kg": chicken_kg,
        "chicken_lb": chicken_lb,
        "chicken_units": chicken_units,
        "chicken_units_rounded": int(__import__("math").ceil(chicken_units)),
    }


st.title("DASH demand forecast")
st.caption("Upload order-line data to view actual demand, an editable 30-day forecast, and weekly units.")

with st.sidebar:
    st.header("Forecast settings")
    uploaded = st.file_uploader("Order CSV", type="csv", help="DASH or Shopify order-line export")
    growth = st.number_input("Expected growth (%)", min_value=-95.0, max_value=500.0, value=25.0, step=1.0)
    horizon = st.slider("Forecast horizon (days)", min_value=7, max_value=90, value=30, step=1)
    st.divider()
    st.subheader("Chicken purchasing")
    box_weight_kg = st.number_input("Box weight (kg)", min_value=0.1, max_value=100.0, value=10.0, step=0.5)
    chicken_unit_lb = st.number_input("Chicken purchase unit (lb)", min_value=1.0, max_value=10_000.0, value=125.0, step=5.0)
    chicken_pct = st.number_input("Chicken content of each box (%)", min_value=0.0, max_value=100.0, value=100.0, step=1.0)
    st.caption("Growth is applied to the historical average daily demand. Calendar seasonality is derived from the uploaded history.")

try:
    if uploaded:
        raw = read_csv(uploaded.getvalue())
        source_label = uploaded.name
    else:
        sample_path = DATA_DIR / "dash_orders_30_days_sample.csv"
        raw = pd.read_csv(sample_path)
        source_label = sample_path.name
    orders, mapping = prepare_orders(raw)
except Exception as error:
    st.error(f"Could not read this CSV: {error}")
    st.stop()

with st.sidebar:
    sku_values = sorted(orders["sku"].astype(str).unique())
    selected_skus = st.multiselect("Products", sku_values, default=sku_values)

filtered = orders[orders["sku"].astype(str).isin(selected_skus)].copy()
if filtered.empty:
    st.warning("Select at least one product with valid demand.")
    st.stop()

daily = filtered.groupby("date", as_index=False)["quantity"].sum().rename(columns={"quantity": "actual_units"})
forecast = make_forecast(daily, growth, horizon)
weekly = weekly_summary(daily, forecast)
purchase_plan = chicken_purchase_plan(
    forecast["forecast_units"].sum(), box_weight_kg, chicken_unit_lb, chicken_pct
)
sku_mix = filtered.groupby("sku", as_index=False)["quantity"].sum()
sku_mix["forecast_boxes"] = forecast["forecast_units"].sum() * sku_mix["quantity"] / sku_mix["quantity"].sum()
st.session_state["planning_forecast_by_sku"] = sku_mix[["sku", "forecast_boxes"]].copy()
st.session_state["planning_forecast_end_date"] = forecast["date"].max()
st.session_state["planning_forecast_horizon"] = horizon

latest_7 = daily.sort_values("date").tail(7)["actual_units"].mean()
next_7 = forecast.head(7)["forecast_units"].mean()
growth_vs_latest = ((next_7 / latest_7) - 1) * 100 if latest_7 else 0

st.caption(f"Source: **{source_label}** · {len(filtered):,} valid order lines · Historical period: {daily.date.min():%b %d, %Y} – {daily.date.max():%b %d, %Y}")
metric1, metric2, metric3, metric4 = st.columns(4)
with metric1:
    with st.container(border=True):
        st.metric("Historical units", f"{daily.actual_units.sum():,.0f}")
with metric2:
    with st.container(border=True):
        st.metric("Historical units", f"{daily.actual_units.sum():,.0f}")
with metric3:
    with st.container(border=True):
        st.metric(f"Next {horizon}-day forecast", f"{forecast.forecast_units.sum():,.0f}")
with metric4:
    with st.container(border=True):
        st.metric("Next 7 days vs. latest 7", f"{growth_vs_latest:+.1f}%")

st.subheader("Daily demand and forecast")
actual_chart = daily.rename(columns={"actual_units": "units"}).assign(series="Actual")
forecast_chart = forecast.rename(columns={"forecast_units": "units"}).assign(series="Forecast")
chart_data = pd.concat([actual_chart[["date", "units", "series"]], forecast_chart[["date", "units", "series"]]])
fig = px.line(chart_data, x="date", y="units", color="series", markers=True, color_discrete_map={"Actual": "#356B52", "Forecast": "#862633"})
fig.update_layout(
    height=410,
    xaxis_title=None,
    yaxis_title="Units",
    legend_title=None,
    margin=dict(l=0, r=0, t=20, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#28231F",
    xaxis_gridcolor="#E2D3AE",
    yaxis_gridcolor="#E2D3AE",
)
st.plotly_chart(fig, width="stretch")

st.subheader("Chicken purchasing requirement")
st.caption(
    f"Based on {forecast.forecast_units.sum():,.1f} forecast boxes × {box_weight_kg:g} kg per box "
    f"× {chicken_pct:g}% chicken. Purchase units are rounded up to avoid a shortfall."
)
procurement_metrics = st.columns(4)
with procurement_metrics[0]:
    with st.container(border=True):
        st.metric("Forecast food weight", f"{purchase_plan['total_food_kg']:,.0f} kg")
with procurement_metrics[1]:
    with st.container(border=True):
        st.metric("Chicken required", f"{purchase_plan['chicken_kg']:,.0f} kg")
with procurement_metrics[2]:
    with st.container(border=True):
        st.metric("Chicken required", f"{purchase_plan['chicken_lb']:,.0f} lb")
with procurement_metrics[3]:
    with st.container(border=True):
        st.metric(
            f"{chicken_unit_lb:g}-lb chicken units to buy",
            f"{purchase_plan['chicken_units_rounded']:,}",
            help=f"Exact requirement: {purchase_plan['chicken_units']:,.2f} purchase units.",
        )

left, right = st.columns((1.05, 1))
with left:
    st.subheader("Weekly demand")
    weekly_fig = px.bar(weekly, x="week_start", y="weekly_units", color="period", barmode="group", color_discrete_map={"Actual": "#356B52", "Forecast": "#862633"})
    weekly_fig.update_layout(
        height=350,
        xaxis_title="Week starting",
        yaxis_title="Units",
        legend_title=None,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#28231F",
        xaxis_gridcolor="#E2D3AE",
        yaxis_gridcolor="#E2D3AE",
    )
    st.plotly_chart(weekly_fig, width="stretch")
with right:
    st.subheader(f"{horizon}-day forecast")
    display_forecast = forecast[["forecast_day", "date", "seasonality_factor", "forecast_units"]].copy()
    display_forecast["date"] = display_forecast["date"].dt.date
    st.dataframe(display_forecast, hide_index=True, width="stretch", height=350, column_config={
        "forecast_day": "Day", "date": "Date", "seasonality_factor": st.column_config.NumberColumn("Seasonality", format="%.2fx"), "forecast_units": st.column_config.NumberColumn("Forecast units", format="%.1f")
    })

st.download_button(
    "Download forecast CSV",
    forecast.to_csv(index=False).encode("utf-8"),
    file_name="demand_forecast.csv",
    mime="text/csv",
)

with st.expander("Data mapping and forecast logic"):
    st.write("Detected columns:", {key: value for key, value in mapping.items() if value})
    st.write("The dashboard uses positive line-item quantities. It fills missing historical days with zero demand, uses the average daily units as the baseline, applies the editable growth percentage, and retains bounded day-of-month seasonality when enough history is available.")
