# DASH Demand Forecast Dashboard

## 📦  Inventory Forecasting ## 
Smarter Inventory Decisions, Powered by Data
Inventory-Forecasting transforms sales and inventory data into practical insights that help businesses plan ahead with confidence. The project is designed to anticipate product demand, maintain healthier stock levels, and minimize the operational cost of both stockouts and overstocking.

## 🚀 Business Impact 
Accurate inventory planning supports better decisions across purchasing, logistics, sales, and supply chain operations. By forecasting future demand, businesses can:
- Reduce lost sales caused by unavailable products.
- Avoid unnecessary capital tied up in excess inventory.
- Improve replenishment planning and purchasing priorities.
- Deliver a more reliable customer experience.
- Operate with greater efficiency and less waste.

## 🔎 From Historical Data to Actionable Insights
The solution analyzes historical sales and inventory patterns to identify demand trends and generate forecasts that can support daily business decisions. Instead of relying solely on intuition, teams can use data to understand what products may be needed, when they will be needed, and where attention should be focused.

## 🛠️ Technical Approach
This project combines:
- Data analysis to explore sales and inventory behavior.
- Data visualization to communicate key trends clearly.
- Forecasting models to estimate future product demand.
- An interactive application interface for accessible decision-making.

## 💼 Why It Matters
Inventory-Forecasting demonstrates the ability to connect technical skills with real business challenges. It shows how data-driven tools can turn operational information into measurable value—helping organizations make faster, smarter, and more strategic inventory decisions.




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
