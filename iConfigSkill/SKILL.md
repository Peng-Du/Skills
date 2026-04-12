---
name: iConfigSkill
description: This skill should be used when operating the H3C Configuration Tool (新华三配置器) web application, including login, creating quotations, adding devices, editing configurations, and modifying fan/power modules via chrome-devtools mcp automation.
---

# iConfigSkill

## Overview

iConfigSkill enables automated operations on the H3C Configuration Tool (H3C Configuration Tool) web application through chrome-devtools mcp automation. All operations are performed by interacting with the web UI directly.

## When to Use This Skill

Use this skill when:
- Operating the H3C iConfig system via browser automation
- Creating quotations and managing devices
- Fixing "Error" status on switch configurations by modifying fan/power modules

## References

- `references/h3c_products.md` - H3C product catalog for device type identification (switch, router, firewall, wireless AC, wireless AP, optical module classification)

### Login Steps
1. Navigate to `https://iconfig-cloud.h3c.com/iconfig/Index`
2. Open DevTools (F12) → Network panel
3. Use `list_network_requests` and `get_network_request` tools to analyze
4. Change language to English
5. Click the tab of H3C user
6. Wait 5s for the user to input Username and Password
7. Then click Login automatically

## Key UI Interactions

### Opening a Quotation
- Click **Quotation** link in top navigation
- Find the quotation in the list (e.g., "UK Test 8")
- Click the quotation name to open it

### Create Quotation
- Click **New** link to create a new quotation
- Enter Quotation name
- Select Country/Region, United Kindom by default
- Select Is U.S. ECCN needed as Yes
- Save

### Enter the Configuration
- Click **2. Configuration**

### Add a Device
- **Reference**: For device type identification, see `references/h3c_products.md`
  - If the device is a switch, router, firewall or wireless AC, click **Standard** to enter Standard config
  - If the device is an optical module or wireless AP, click **Parts** to enter Parts config
- Search for product, in the search box beside **Easy Choose**, Enter directly, don't click **Easy Choose**
- Select the correct product from results, keep the quantity as 1 here and edit later
- Click **Add** to add to quotation
- Remember the **Product model**
- Click **OK** and then Edit the Name, Quantity and Notes immediately

### Edit the Quantity, Name and Notes
- Click **Edit** link in the device row, Operation collumn
- Modify fields in the dialog:
   - **Config name**: Change it to the **Product model**
   - **Sets**: Quantity
   - **Configuration group notes**: Notes
- Click **OK** to save

### Product Search Strategy

**Critical**: When searching for products, use product codes from `references/h3c_products.md`:
- Search by exact product model number (e.g., "SFP-XG-SX-MM850-D" not "10Ge multimode")
- If product name search fails, try searching by product code/model directly
- Always verify the product code in h3c_products.md before searching

### Fixing Error Status (Configuring Fan/Power)

When a switch, router or firewall shows "Error" status, it needs fan and power modules configured:

#### Step 1: Enter Config name, enter this configuration

Click the "Config name" to enter this configuration

#### Step 2: Enter Details Page
1. In Components tab, find the product row
2. **Critical: Click the Product Name** (e.g., S6520X-HI Switch #1)
   - **Do NOT click "product detail" text** - that won't expand the product tree
   - Must click the number part of the Product Name to enter the Details page
3. This will expand the product tree and automatically enter the Details tab

#### Step 3: Configure Fan
1. In Details page, expand **Fan Options**
2. Select **Exhaust Airflow** model (Exhaust Airflow fan)
3. Click quantity cell to show dropdown
4. **Always select the MAXIMUM quantity from the dropdown** - do not select the minimum or default value

#### Step 4: Configure Power
1. In Details page, expand **Power Options**
2. Select **cheapest AC power** model
3. Click quantity cell to show dropdown
4. **Always select the MAXIMUM quantity from the dropdown** - even if the error message says it needs only 1 minimum (e.g., if it suggests 2 for redundancy, select 2)

**Important Rule 1: Always select the maximum available quantity for both fan and power modules, regardless of what the minimum requirement states. This ensures proper redundancy and configuration correctness.**

**Important Rule 2: Always keep the quantity as 1 when select the product and modify it after click Edit**

**Important Rule 3: Always search in the box beside "Easy Choose", then ENTER, Do NOT click "Easy Choose"**

**Important Rule 4: Do NOT use the search box below the product list**

**Important Rule 5: Edit the Quantity, Name and Notes before Fixing Error Status**

#### Success Indicator
- Status changes from Error to "Correct"

### Troubleshooting

**Problem: Clicking Product ID opens a new tab instead of expanding details**
- Solution: Right-click on the product row → select **Drill down** → **Details**

**Problem: Element ref IDs become stale during navigation**
- Solution: Take a fresh snapshot before each major interaction to get current ref IDs

**Problem: Product search returns no results**
- Solution: Use exact product model codes from `references/h3c_products.md`, not descriptive names