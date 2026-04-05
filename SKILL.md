---
name: iConfigSkill
description: This skill should be used when operating the H3C Configuration Tool (新华三配置器) web application, including login, creating quotations, adding devices, editing configurations, and modifying fan/power modules via Chrome DevTools browser automation.
---

# iConfigSkill

## Overview

iConfigSkill enables automated operations on the H3C Configuration Tool (H3C Configuration Tool) web application through Chrome DevTools browser automation. All operations are performed by interacting with the web UI directly.

## When to Use This Skill

Use this skill when:
- Operating the H3C iConfig system via browser automation
- Creating quotations and managing devices
- Fixing "Error" status on switch configurations by modifying fan/power modules
- Analyzing XHR network requests for the iConfig web application

## Browser Navigation

1. Navigate to `https://iconfig-cloud.h3c.com/iconfig/Index`
2. Open DevTools (F12) → Network panel
3. Filter by `XHR` and look for `MauiServlet` requests
4. Use `list_network_requests` and `get_network_request` tools to analyze
5. Change language to English
6. Click the tab of H3C user
7. Wait 5s for the user to input Username and Password
8. Then click Login automatically

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
- If the device is a switch, router, firewall or wireless AC, click **Standard** to enter Standard config
- If the device is an optical module or wireless AP, click **Parts** to enter Parts config
- Search for product, in the search box beside **Easy Choose** (e.g., "S6520X", or "S5590-24X4YC-EI")
- Select the correct product from results
- Click **Add** to add to quotation
- Remember the **Product model**
- Click **OK** and then Edit the Name, Quantity and Notes immediately

### Edit the Name, Quantity and Notes
- Click **Edit** link in the device row
- Modify fields in the dialog:
   - **Config name**: Change it to the **Product model**
   - **Sets**: Quantity
   - **Site**: Location
   - **Configuration group notes**: Notes
- Click **OK** to save

### Fixing Error Status (Configuring Fan/Power)

When a switch, router or firewall shows "Error" status, it needs fan and power modules configured:

#### Step 1: Enter Config name, enter this configuration

#### Step 2: Enter Details Page
1. In Components tab, find the product row
2. **Critical: Click the Product ID** (e.g., 0235A4L7)
   - **Do NOT click "product detail" text** - that won't expand the product tree
   - Must click the number part of the Product ID to enter the Details page
3. This will expand the product tree and automatically enter the Details tab

#### Step 3: Configure Fan
1. In Details page, expand **Fan Options**
2. Select **Exhaust Airflow** model (Exhaust Airflow fan)
3. Click quantity cell to show dropdown
4. Select maximum from the dropdown (e.g., 3 for S6520X-30HF-HI)

#### Step 4: Configure Power
1. In Details page, expand **Power Options**
2. Select **cheapest AC power** model
3. Click quantity cell to show dropdown
4. Select maximum from the dropdown, although the model is the cheapest (e.g., 2 for S5590-24X4YC-EI)

#### Success Indicator
- Status changes from Error to "Correct"