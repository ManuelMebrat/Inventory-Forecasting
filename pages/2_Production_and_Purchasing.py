from datetime import date
from pathlib import Path
import math

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

st.set_page_config(page_title="DASH | Production & purchasing", page_icon="🏭", layout="wide")


def template(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def numeric(frame: pd.DataFrame, column: str, default: float = 0) -> pd.Series:
    source = frame[column] if column in frame.columns else pd.Series(default, index=frame.index)
    return pd.to_numeric(source, errors="coerce").fillna(default)


def build_material_plan(forecast: pd.DataFrame, bom: pd.DataFrame, suppliers: pd.DataFrame) -> pd.DataFrame:
    requirements = forecast.merge(bom, on="sku", how="left")
    missing = requirements[requirements["component_id"].isna()]["sku"].drop_duplicates()
    if not missing.empty:
        st.warning("No BOM found for: " + ", ".join(missing["sku"].astype(str)) + ". Those SKUs are excluded from material planning.")
    requirements = requirements.dropna(subset=["component_id"]).copy()
    requirements["qty_per_box"] = numeric(requirements, "qty_per_box")
    requirements["safety_stock_pct"] = numeric(requirements, "safety_stock_pct")
    requirements["net_requirement"] = requirements["forecast_boxes"] * requirements["qty_per_box"]
    requirements["planned_requirement"] = requirements["net_requirement"] * (1 + requirements["safety_stock_pct"] / 100)
    material = requirements.groupby(["component_id", "component_name", "component_type", "uom"], as_index=False).agg(
        forecast_boxes=("forecast_boxes", "sum"), net_requirement=("net_requirement", "sum"), planned_requirement=("planned_requirement", "sum")
    )
    material["safety_stock_pct"] = (material["planned_requirement"] / material["net_requirement"] - 1).mul(100).where(material["net_requirement"].ne(0), 0)
    supplier_choice = suppliers.copy()
    supplier_choice["priority"] = numeric(supplier_choice, "priority", 999)
    supplier_choice = supplier_choice.sort_values(["component_id", "priority"]).drop_duplicates("component_id")
    plan = material.merge(supplier_choice, on="component_id", how="left")
    plan["units_per_purchase_uom"] = numeric(plan, "units_per_purchase_uom", 1)
    plan["minimum_order_qty"] = numeric(plan, "minimum_order_qty", 0)
    plan["purchase_units_exact"] = plan["planned_requirement"] / plan["units_per_purchase_uom"]
    plan["purchase_units_to_order"] = plan.apply(
        lambda row: max(math.ceil(row["purchase_units_exact"]), math.ceil(row["minimum_order_qty"])) if pd.notna(row["supplier_id"]) else None,
        axis=1,
    )
    for optional_column, default in {"supplier_sku": "", "unit_price": 0, "currency": ""}.items():
        if optional_column not in plan.columns:
            plan[optional_column] = default
    plan["expected_receipt"] = pd.to_datetime(date.today()) + pd.to_timedelta(numeric(plan, "lead_time_days"), unit="D")
    return plan


st.title("Production & purchasing plan")
st.caption("This page converts the current demand forecast into finished-box production targets, ingredient and packaging requirements, and supplier-specific draft purchase orders.")

bom = st.session_state.get("bom", template("dash_bom_template.csv"))
suppliers = st.session_state.get("suppliers", template("dash_supplier_template.csv"))
forecast = st.session_state.get("planning_forecast_by_sku")

if forecast is None or forecast.empty:
    st.info("First open **Demand Forecast**, load your order CSV, and set the growth and horizon. Then return here; the latest forecast will appear automatically.")
    st.stop()

forecast = forecast.copy()
forecast["forecast_boxes"] = numeric(forecast, "forecast_boxes")
plan = build_material_plan(forecast, bom, suppliers)
horizon = st.session_state.get("planning_forecast_horizon", 30)
forecast_end = st.session_state.get("planning_forecast_end_date")

top1, top2, top3, top4 = st.columns(4)
with top1:
    with st.container(border=True):
        st.metric(f"Production target ({horizon} days)", f"{forecast['forecast_boxes'].sum():,.0f} boxes")
with top2:
    with st.container(border=True):
        st.metric("Ingredient lines", f"{(plan['component_type'] == 'ingredient').sum()}")
with top3:
    with st.container(border=True):
        st.metric("Packaging lines", f"{(plan['component_type'] == 'packaging').sum()}")
with top4:
    with st.container(border=True):
        st.metric("Unassigned materials", f"{plan['supplier_id'].isna().sum()}")
if forecast_end is not None:
    st.caption(f"Forecast demand ends {pd.Timestamp(forecast_end):%b %d, %Y}. Purchase-order receipts below are estimated from today plus supplier lead time.")

st.subheader("Production plan by finished SKU")
production = forecast.rename(columns={"forecast_boxes": "boxes_to_produce"}).copy()
production["boxes_to_produce"] = production["boxes_to_produce"].round(0).astype(int)
st.dataframe(production, hide_index=True, width="stretch", column_config={"boxes_to_produce": st.column_config.NumberColumn("Boxes to produce", format="%d")})
st.download_button("Download production plan", production.to_csv(index=False).encode("utf-8"), "production_plan.csv", "text/csv")

st.subheader("Material requirements")
materials = plan[["component_id", "component_name", "component_type", "uom", "net_requirement", "planned_requirement", "safety_stock_pct", "supplier_name"]].copy()
materials[["net_requirement", "planned_requirement"]] = materials[["net_requirement", "planned_requirement"]].round(2)
st.dataframe(materials, hide_index=True, width="stretch")
st.download_button("Download material requirements", materials.to_csv(index=False).encode("utf-8"), "material_requirements.csv", "text/csv")

st.subheader("Draft purchase orders")
st.caption("Each line is assigned to the approved supplier with the lowest priority number. Order quantities honor the supplier's purchase-unit size and MOQ.")
po_columns = ["supplier_id", "supplier_name", "component_id", "component_name", "supplier_sku", "purchase_uom", "purchase_units_to_order", "unit_price", "currency", "expected_receipt"]
purchase_orders = plan[plan["supplier_id"].notna()][po_columns].copy()
purchase_orders["expected_receipt"] = pd.to_datetime(purchase_orders["expected_receipt"]).dt.date
purchase_orders = purchase_orders.sort_values(["supplier_name", "component_name"])
purchase_orders["po_number"] = "DRAFT-" + purchase_orders["supplier_id"].astype(str) + "-" + date.today().strftime("%Y%m%d")
purchase_orders["po_status"] = "Draft"
purchase_orders["ordered_at"] = pd.NaT
purchase_orders["received_qty"] = 0.0
purchase_orders = purchase_orders[["po_number", "po_status", "supplier_id", "supplier_name", "component_id", "component_name", "supplier_sku", "purchase_uom", "purchase_units_to_order", "received_qty", "unit_price", "currency", "ordered_at", "expected_receipt"]]
st.dataframe(purchase_orders, hide_index=True, width="stretch")
st.download_button("Download draft purchase orders", purchase_orders.to_csv(index=False).encode("utf-8"), "draft_purchase_orders.csv", "text/csv", type="primary")

st.subheader("Purchase-order tracker")
st.caption("Update the status as each supplier order is placed and received. This tracker is kept for the current browser session; download it to retain or share it.")
tracker = st.session_state.get("po_tracker", purchase_orders)
tracker = st.data_editor(tracker, hide_index=True, width="stretch", key="po_tracker_editor", column_config={
    "po_status": st.column_config.SelectboxColumn("PO status", options=["Draft", "Sent", "Confirmed", "Partially received", "Received", "Cancelled"]),
    "ordered_at": st.column_config.DateColumn("Ordered on"),
    "expected_receipt": st.column_config.DateColumn("Expected receipt"),
    "received_qty": st.column_config.NumberColumn("Received quantity", min_value=0.0),
})
if st.button("Save PO tracker"):
    st.session_state["po_tracker"] = tracker.copy()
    st.success("PO tracker saved for this session.")
st.download_button("Download PO tracker", tracker.to_csv(index=False).encode("utf-8"), "purchase_order_tracker.csv", "text/csv")

with st.expander("How the calculations work"):
    st.write("Finished-box forecast × BOM quantity per box = net material requirement. The BOM safety-stock percentage is added to form the planned requirement. Planned requirement ÷ supplier units per purchase unit is then rounded up, and raised to the supplier MOQ when needed.")
