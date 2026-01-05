[العربية](README.ar.md)

# MHMA Inventory (`mhma_inventory`)

Custom Odoo module (Odoo 17) that extends **Inventory/Stock** operations and adds an **end-to-end approvals workflow** from requisition to guidance and execution, with enhanced reporting and governance controls.

> Note: This is a custom module (not an official OCA module). The documentation structure follows an OCA-like style.

## Table of contents
- [Overview](#overview)
- [Key features](#key-features)
  - [Inventory enhancements](#inventory-enhancements)
  - [Approvals & workflow](#approvals--workflow)
  - [PDF reports](#pdf-reports)
  - [Security & governance](#security--governance)
  - [Localization](#localization)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Inventory usage](#inventory-usage)
  - [Approvals usage](#approvals-usage)
- [Known issues / Limitations](#known-issues--limitations)
- [Roadmap](#roadmap)
- [Bug Tracker](#bug-tracker)
- [Credits](#credits)
- [Maintainers](#maintainers)
- [License](#license)

## Overview
`mhma_inventory` provides:
- Practical enhancements for product and stock operations (search, valuation helpers, lot automation, stock ledger fields, etc.).
- A structured approvals workflow covering requisitions, purchasing guidance, issue guidance, service and maintenance guidance.
- Better PDF outputs for internal audit and signature-based processes.

## Key features

### Inventory enhancements
- **Product Variant Description**
  - Adds a text field on the product variant to store extra details beyond the product template description.

- **Product Variant Valuation Helper**
  - Computes: **Variant valuation = Purchase cost × Quantity on hand**.

- **Advanced Product Search**
  - Enables searching by a single value across:
    - Internal reference
    - Name
    - Display name
    - Barcode
    - Product template tags
    - Additional product tags

- **Product Issue Type**
  - Classifies products as:
    - Commodity item
    - Fixed asset
    - Personal custody item

- **Stock Move Line extra fields**
  - Adds fields to identify:
    - Stock UoM on the move line
    - Beneficiary department (who received the quantity)

- **Automatic LOT/Serial name generation**
  - If a lot name is not provided (or not required), the system can generate it from the **expiration date** (day/month/year).

- **Stock Ledger (Inventory master)**
  - Consolidated view of stock movement including:
    - Opening balance (qty & cost)
    - Incoming (qty & cost)
    - Outgoing (qty & cost)
    - Closing balance (qty & cost)
    - Discount value
    - Actual/real movement cost

- **Picking / Issue enhancements (Receipt & Issue Orders)**
  - Total picking cost (sum of underlying stock move costs)
  - Total cost displayed as **number + Arabic text**
  - Notify receiver to confirm receipt
  - Receiver can confirm receipt directly
  - Link issue order with requisition / issue guidance (with automated defaulting)
  - Add department structure fields (Sector / Directorate / Office / Department)

- **Import picking lines from Excel**
  - Bulk import lines using **internal reference + quantity** for multiple items at once.

- **Prevent negative stock**
  - Blocks issuing quantities that would make on-hand quantity negative.

- **Lock Unit of Measure**
  - Option to freeze UoM field so stock users cannot change it (finance requirement).

- **Statement subject**
  - Adds a mandatory/controlled field used by inventory accountant on receipt/issue operations.

### Approvals & workflow
- **Approval category types** (added/extended)
  1. Requisition (items request) / Stock issue request
  2. Purchase request
  3. Item specification definition
  4. Purchase guidance
  5. Issue guidance
  6. Service guidance
  7. Maintenance guidance

- **Access control per approval category**
  - Restrict who can create/see specific categories (e.g., requisitions).

- **Requisition → guidance → execution workflow**
  - Employee fills:
    - Statement subject (mandatory)
    - Contact information
    - Description (optional)
    - Requested items with qty & details
  - Workflow approvals (typical):
    - Direct managers review and adjust
    - Finance manager reviews and estimates/approves budget
    - Procurement/Warehouse manager checks availability and approves/adjusts by stock
    - Guidance issued to inventory/procurement accountant for execution
    - Stock issue order created and delivered by storekeeper
    - Receiver is notified and confirms receipt

- **Purchase request / specifications / purchase guidance**
  - Committee defines items, specs, quantities, and estimated costs.
  - Follows the organization’s approval chain.

- **Guidance for services and maintenance**
  - Supports requests like internet/electricity payments (service) and repairs (maintenance),
    routed to the responsible team for execution.

- **Request Products catalog**
  - Dedicated model to simplify requesting common items (e.g., pens, A4 paper), including:
    - Request product name
    - Product category
    - Unit of measure
    - Estimated cost
    - Product type
    - Description
    - Access group restriction (who can request it)
    - Details template

- **Request line traceability**
  - Any change to qty/description/estimated cost/details is tracked in the **Chatter**.

- **Links to operational documents**
  - Link **Issue guidance → stock pickings/issue orders**
  - Link **Purchase guidance → purchase orders**

- **Vendor creation request**
  - Workflow to request adding a vendor, routed for finance approval then created in contacts.
  - Includes payable/receivable accounts and required validation (e.g., vendor name).

- **Coding / naming**
  - Approval categories can be auto-coded (prefix + sequence).
  - Renaming logic includes approval reference + statement subject for clarity.

- **Direct purchase (Expenses) UI**
  - Designed for purchases below a defined threshold (e.g., **< 30,000 YER**),
    linked to purchase guidance and the requester/receiver confirmation flow.

### PDF reports
Inventory & approvals reporting improvements:
- Print forms with **signatories/approvers** ready for signature
- Show **statement subject** in printouts
- Hide Barcode image and keep **QR code**
- Hide serial/lot numbers in printout where required (show name only)
- Print requisitions/guidance/purchase requests with:
  - Requester name
  - Statement subject
  - Submission date
  - Lines including updated qty/description/cost/details

### Security & governance
- Adds a **read-only full access** role for inventory models for auditors/reviewers.
- Access restrictions for approvals categories to prevent unauthorized requests.

### Localization
- Bilingual UI support: **Arabic (AR)** and **English (EN)** (translations included where applicable).

## Installation
1. Copy `mhma_inventory` into your Odoo addons path.
2. Restart the Odoo server.
3. Enable **Developer Mode**.
4. Go to **Apps** → **Update Apps List**.
5. Search for `mhma_inventory` and click **Install**.

## Configuration
- Assign user groups/roles:
  - Inventory users / storekeepers
  - Inventory accountant
  - Approvals creators/approvers per category
  - Inventory auditor/reviewer (read-only)
- Configure approval categories, routes, and approvers according to your organization structure.
- Configure request product catalog (optional but recommended).

## Usage

### Inventory usage
- Open **Inventory** app and use enhanced search on products.
- Use product variant “Variant Description” for additional details.
- Use pickings/issue orders with:
  - Statement subject
  - Department fields
  - Cost totals and receipt confirmation
- Import issue lines from Excel (internal reference + qty) when needed.

### Approvals usage
- Create a requisition / request and fill statement subject + items.
- Send for approval.
- Approvers review and adjust lines (tracked in Chatter).
- After final approval, guidance is issued and execution documents are linked and traceable.
- Receiver confirms receipt via notification.

## Known issues / Limitations
- None documented yet. Please report issues via GitHub.

## Roadmap
- Improve templates for Excel import and validation messages.
- Add more printable report templates if needed.

## Bug Tracker
Bugs and feature requests can be reported in GitHub Issues of this repository.

## Credits

### Authors
- Mustapha Alahdel

### Contributors
- Community contributions are welcome (PRs).

## Maintainers
This module is maintained by **Mustapha Alahdel**.

## License
This module is released under the license specified in `__manifest__.py`.
