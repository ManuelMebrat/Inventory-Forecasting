"""Maintain the recipe/BOM and supplier master data used by the planning page."""

from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="DASH | BOM & suppliers", page_icon="🧾", layout="wide")


def load_template(name: str) -> pd.DataFrame:
    return pd.read_csv(Path(__file__).parents[1] / name)


def read_upload(upload, required: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(upload)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    return frame


st.title("Recipe, packaging & supplier master data")
st.caption("Set the materials needed to make each finished SKU, then link each material to a supplier. These assumptions drive the production plan and draft purchase orders.")

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Bill of materials")
        bom_upload = st.file_uploader("Upload BOM CSV", type="csv", key="bom_upload")
        st.download_button("Download BOM template", (Path(__file__).parents[1] / "dash_bom_template.csv").read_bytes(), "dash_bom_template.csv", "text/csv")
with right:
    with st.container(border=True):
        st.subheader("Approved suppliers")
        supplier_upload = st.file_uploader("Upload supplier CSV", type="csv", key="supplier_upload")
        st.download_button("Download supplier template", (Path(__file__).parents[1] / "dash_supplier_template.csv").read_bytes(), "dash_supplier_template.csv", "text/csv")

try:
    bom = read_upload(bom_upload, {"sku", "component_id", "component_name", "component_type", "qty_per_box", "uom"}) if bom_upload else st.session_state.get("bom", load_template("dash_bom_template.csv"))
    suppliers = read_upload(supplier_upload, {"component_id", "supplier_id", "supplier_name", "purchase_uom", "units_per_purchase_uom", "minimum_order_qty", "lead_time_days"}) if supplier_upload else st.session_state.get("suppliers", load_template("dash_supplier_template.csv"))
except Exception as error:
    st.error(f"Could not use the uploaded master data: {error}")
    st.stop()

with st.container(border=True):
    st.subheader("Bill of materials (BOM)")
    st.caption("One row = one ingredient or packaging component required for one finished box. `qty_per_box` must be in the listed UOM.")
    bom_edited = st.data_editor(bom, num_rows="dynamic", hide_index=True, width="stretch", key="bom_editor", column_config={
        "component_type": st.column_config.SelectboxColumn("Component type", options=["ingredient", "packaging"]),
        "qty_per_box": st.column_config.NumberColumn("Quantity per box", min_value=0.0),
        "safety_stock_pct": st.column_config.NumberColumn("Safety stock (%)", min_value=0.0, max_value=500.0),
    })

with st.container(border=True):
    st.subheader("Approved suppliers")
    st.caption("One row = one possible supplier for a component. Lowest `priority` is selected for the draft purchase order.")
    supplier_edited = st.data_editor(suppliers, num_rows="dynamic", hide_index=True, width="stretch", key="supplier_editor", column_config={
        "units_per_purchase_uom": st.column_config.NumberColumn("Units per purchase unit", min_value=0.0001),
        "minimum_order_qty": st.column_config.NumberColumn("Minimum order quantity", min_value=0.0),
        "lead_time_days": st.column_config.NumberColumn("Lead time (days)", min_value=0.0),
        "priority": st.column_config.NumberColumn("Priority", min_value=1, step=1),
    })

if st.button("Save master data for planning", type="primary"):
    st.session_state["bom"] = bom_edited.copy()
    st.session_state["suppliers"] = supplier_edited.copy()
    st.success("Master data saved. Open Production & purchasing plan from the sidebar.")

download_a, download_b = st.columns(2)
with download_a:
    st.download_button("Download current BOM", bom_edited.to_csv(index=False).encode("utf-8"), "dash_bom.csv", "text/csv")
with download_b:
    st.download_button("Download current suppliers", supplier_edited.to_csv(index=False).encode("utf-8"), "dash_suppliers.csv", "text/csv")
