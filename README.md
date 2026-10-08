# DASH Demand Forecast Dashboard

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Open the local URL shown by Streamlit. Upload a CSV or use the included DASH sample.

## CSV columns

The dashboard accepts the DASH columns `order_created_at`, `quantity`, and `sku`, and Shopify columns `Created at`, `Lineitem quantity`, and `Lineitem sku`.

`Expected growth (%)` is an editable assumption in the sidebar and recomputes the daily forecast, weekly demand, forecast table, and CSV download immediately.

## Production and purchasing workflow

The sidebar includes two additional pages:

1. **BOM & Suppliers** — upload or edit the bill of materials and approved supplier master data. The included `dash_bom_template.csv` and `dash_supplier_template.csv` are starter assumptions and should be replaced with validated operational data.
2. **Production & Purchasing** — transforms the current forecast into a finished-box production plan, ingredient and packaging requirements, and supplier-level draft purchase-order lines.

Open the **Demand Forecast** page first to load data and set the forecast. Then save master data on **BOM & Suppliers** and open **Production & Purchasing**.
