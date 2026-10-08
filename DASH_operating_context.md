# DASH Dog Food — Operating and Data Context

## Purpose

This document is the approved context source for building operations, procurement, inventory, forecasting, and automation micro-projects for DASH Dog Food. It defines the target analytical schema and the assumptions that still require validation. It is not a Shopify specification and does not copy the example export files.

The `orders_export_1.csv` and `inventory_export_1.csv` files belong to another store. They were reviewed only to identify fields that Shopify can commonly export. Their customers, products, prices, locations, results, and business rules must not be carried into DASH work.

## Observed Business Model

DASH sells fresh, frozen, portioned dog food through a direct-to-consumer subscription. The customer completes a quiz, receives a portion, recipe, and delivery recommendation, and can manage changes through a membership portal.

Observed commercial flow:

1. Dog profile.
2. Recommendation and feeding plan.
3. Treat add-on.
4. Trial checkout.
5. Expected conversion to a recurring full-size box.
6. Frozen delivery and subscription management.

The visible dog profile includes number of dogs, name, sex, neutering status, age, optional birthday, weight, body condition, current food, optional brand, nutrition priority, activity, allergies, health status, and email. Customer personal information should follow a minimum-access approach and should not enter operational analysis files unless essential.

## Observed Offer and Subscription

The following was observed in one checkout example for a dog named Jul. Prices and promotions are a point-in-time observation, not permanent model parameters.

| Item | Observation |
|---|---|
| Food trial | 8 lb, Beef & Chicken, US$69.00 original price and US$34.50 after `DASH50` |
| Add-on | Single Ingredient Freeze-Dried Beef Liver Bites, US$9.34 per box |
| Displayed cadence | Every 35 days for food and treats |
| Next full-size box | US$159.00, with a displayed US$127.20 after a 20% discount |
| Flexibility | Change, reschedule, or cancel the subscription |
| Logistics | Frozen food; shipping is calculated after address capture |

The initial checkout total must not be treated as LTV. It must be split into paid trial revenue, paid add-ons, shipping and taxes, and expected future subscription charges.

## Modeling Principles

- Separate source data, assumptions, calculations, and reports.
- Make the grain of every table explicit.
- Never sum inventory snapshots across dates.
- Never sum prices or percentages across lines to create order metrics; use compatible amounts and denominators.
- Preserve native Shopify IDs and create analytical IDs only when needed.
- Treat cancellations, refunds, skips, and pauses as distinct events.
- Separate confirmed demand, forecast demand, and scheduled subscription demand.
- Do not use PII in operational dashboards when an anonymous identifier is sufficient.

## Target Data Model

### 1. `dog_profile`

**Grain:** one dog per profile version.

Essential fields: `dog_id`, `customer_id`, `profile_updated_at`, `age`, `weight_lb`, `body_condition`, `activity_level`, `neutered_flag`, `current_food_type`, `priority`, `allergy_flag`, `allergy_ingredients`, `health_issue_flag`.

Use: portion recommendation, recipe mix, segmentation, and forecast drivers.

### 2. `product_variant`

**Grain:** one sellable SKU or variant.

Essential fields: `sku`, `product_id`, `product_name`, `product_type`, `recipe_or_protein`, `pack_size_lb`, `is_trial`, `is_add_on`, `is_subscription_eligible`, `active_flag`, `standard_price`, `standard_cost`, `shelf_life_days`, `storage_requirement`.

Use: master catalog, margin, inventory, and BOM.

### 3. `order_line`

**Grain:** one product line in one order.

Essential fields: `order_id`, `order_created_at`, `customer_id`, `dog_id` if available, `sku`, `quantity`, `gross_sales`, `line_discount`, `net_sales`, `tax`, `shipping_allocated`, `currency`, `financial_status`, `fulfillment_status`, `cancelled_at`, `refunded_amount`, `source`, `location_id`.

Use: actual demand, revenue, AOV, product mix, discounts, and fulfillment.

### 4. `subscription`

**Grain:** one current or historical dog subscription or plan.

Essential fields: `subscription_id`, `customer_id`, `dog_id`, `status`, `started_at`, `cancelled_at`, `pause_start_at`, `next_charge_at`, `delivery_frequency_days`, `recipe_or_plan`, `daily_portion`, `box_size`, `base_price`, `discount`, `shipping_charge`.

Use: future demand forecast, cohorts, churn, skips, pauses, and LTV.

### 5. `subscription_event`

**Grain:** one subscription change event.

Essential fields: `event_id`, `subscription_id`, `event_at`, `event_type`, `old_value`, `new_value`, `reason`, `effective_at`.

Expected events: creation, renewal, skip, pause, resume, recipe change, quantity change, frequency change, reschedule, and cancellation.

### 6. `inventory_snapshot`

**Grain:** one SKU, location, and snapshot timestamp.

Essential fields: `snapshot_at`, `sku`, `location_id`, `on_hand`, `available`, `committed`, `unavailable`, `incoming`, `allocated`, `lot_id` if available, `expiry_date` if available.

Use: availability, weeks of supply, stockout risk, and reconciliation.

### 7. `purchase_order_line`

**Grain:** one purchase order line.

Essential fields: `po_id`, `supplier_id`, `po_status`, `ordered_at`, `expected_receipt_at`, `received_at`, `sku_or_material_id`, `ordered_qty`, `received_qty`, `unit_cost`, `currency`, `minimum_order_qty`, `lead_time_days`.

Use: procurement, inbound supply, costs, and supply risk.

### 8. `bom_recipe`

**Grain:** one component per finished SKU or recipe.

Essential fields: `finished_sku`, `material_id`, `qty_per_finished_unit`, `uom`, `yield_rate`, `effective_from`, `effective_to`.

Use: translating box forecasts into ingredient and packaging requirements.

### 9. `fulfillment_shipment`

**Grain:** one shipment or package.

Essential fields: `shipment_id`, `order_id`, `location_id`, `carrier`, `service_level`, `temperature_controlled_flag`, `shipped_at`, `delivered_at`, `shipment_status`, `freight_cost`, `tracking_number`, `exception_type`.

Use: OTIF, freight cost, exceptions, cold-chain compliance, and customer service.

## Shopify Mapping Guidance

The reviewed Shopify exports show that an initial source often includes order and line data (`Name`, `Created at`, `Lineitem quantity`, `Lineitem sku`, `Lineitem price`, `Lineitem discount`, `Financial Status`, `Fulfillment Status`, `Cancelled at`, `Refunded Amount`, `Location`) and SKU-location snapshots (`SKU`, `Location`, `Incoming`, `Unavailable`, `Committed`, `Available`, `On hand`).

For DASH, these fields should map to `order_line` and `inventory_snapshot` without assuming that every field exists, has the same name, or carries the same business definition. Critical data not evidenced by those examples — subscriptions, dog profiles, BOM, lots, expiry, purchase orders, and shipments — needs additional sources.

## Required Metric Support

### Commercial and Subscription

- Quiz-to-trial conversion.
- Trial AOV, add-on attach rate, and net revenue per order.
- Trial-to-full-box conversion.
- Active subscribers, renewal rate, churn, pauses, and skips.
- Subscription revenue forecast and cohort LTV.

### Inventory, Procurement, and Production

- Available, on-hand, and committed inventory by SKU and location.
- Weeks of Supply: available inventory divided by weekly forecast demand.
- Stockout risk, excess stock, and aging or expiry risk when lot data exists.
- Purchase-order on-time delivery, supplier lead time, and purchase-price variance.
- Ingredient and packaging requirements derived from forecast multiplied by BOM.

### Fulfillment and Freight

- Fill rate, order accuracy, OTIF, and time-to-ship.
- Freight cost per order, per pound, and by zone.
- Delivery exceptions and carrier performance.

## Initial Operating Definitions

| Term | Proposed definition |
|---|---|
| Trial | First promotional order, separate from the recurring full-size box. |
| Add-on | Optional product added to an order or subscription, such as treats. |
| Confirmed demand | Units from paid orders or firm fulfillment commitments. |
| Future subscription demand | Next active subscription charges, adjusted for skip or cancellation probability once history exists. |
| Forecast | Statistical demand that is not yet confirmed. It is not mixed with scheduled future orders. |
| Stockout | Available inventory is insufficient for confirmed demand or the defined coverage horizon. |
| Bias | Forecast minus actual demand. A positive value means over-forecast. |

## Assumptions and Gaps to Validate

- Whether 35 days is the standard cadence or only a recommendation in the observed case.
- The real recipe, size, SKU, cost, weight, and allergy-compatibility catalog.
- Pricing, promotion, and effective-date rules.
- The source of truth for subscriptions and subscription events.
- Whether fulfillment is internal, outsourced, or hybrid, and which locations participate.
- Lead times, MOQs, suppliers, BOM, yields, and shelf life.
- Shipping SLAs, carriers, cold-chain requirements, and successful-delivery definition.
- Revenue-recognition, refund, and cancellation policies.

## How to Use This Context

Each micro-project must state: the process to solve, end user, decision enabled, available data, assumptions, time horizon, grain, primary KPI, and requested output. If an input is missing, create an editable field labeled as an assumption; never invent operational data and present it as historical actuals.
