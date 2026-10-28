# Relationship Intelligence — Customer Visit Copilot v2

A complete Python-backed company relationship dashboard designed for the customer-visit workflow and an executive presentation. This version replaces the earlier Streamlit screen with a custom web interface served by Python. It runs locally and can also be deployed from a private GitHub repository to Vercel's native Flask runtime.

## Deploy from GitHub to Vercel

This package is ready to upload after extraction. Do **not** upload the ZIP as a
single repository file. Extract it, commit the project contents to a private
GitHub repository, and import that repository in Vercel. Vercel detects the
top-level Flask `app` in `app.py`; no build command or output directory is
required.

Follow [DEPLOY_TO_VERCEL.md](DEPLOY_TO_VERCEL.md) for the complete GitHub,
environment-variable, deployment and verification procedure. At minimum,
configure `REQUIRE_ACCESS_AUTH`, `APP_ACCESS_USERNAME`, and
`APP_ACCESS_PASSWORD` in Vercel. A Vercel deployment fails closed with HTTP 503
when the password is absent, so customer data is not accidentally displayed by
an unprotected deployment.

The deployed version serves JavaScript, CSS and the logo from `public/` through
Vercel's CDN. The bundled balance files are read-only in a deployment. Replace
them through Git and redeploy, or implement a private database/object-store
adapter for automatic updates. The included password prompt is a minimum
deployment safeguard, not a replacement for bank SSO, CIF entitlements and
audit logging.

### Mobile and performance

The dashboard is responsive down to a 390-pixel mobile viewport. Cards and
opportunities stack vertically, filters remain touch-friendly, and every chart
resizes to its panel without horizontal chart or page scrolling. Values and
labels remain rendered in the chart itself with a compact mobile label layout.

The interactive charts use native browser SVG rather than a third-party chart
library. The combined JavaScript, CSS and original logo are approximately
93 KB before transport compression, compared with the previous multi-megabyte
chart bundle. Static assets are CDN-cacheable, scripts load with `defer`, and
the page uses no external font, image or chart request.

## Start on Windows

1. Extract the ZIP into a **new folder** and open PowerShell in the application folder.
2. Run the Python launcher to prepare the environment and install the required packages:

```powershell
python launcher.py --setup
```

3. Open `.env` in Notepad and add your OpenRouter key:

```dotenv
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4.1-mini
```

4. Start the application directly with Python:

```powershell
python launcher.py
```

Your browser opens at [http://127.0.0.1:8501](http://127.0.0.1:8501). No batch file or PowerShell script is required. If your Windows installation uses the Python launcher, substitute `py` for `python`. You can also open `launcher.py` in VS Code and use **Run Python File in Terminal**.

Python 3.11 or later is required. The package was tested on Python 3.12. The runtime dependencies are Python packages; the dashboard does not require a Chromium or Playwright installation.

Manual PowerShell setup, if you prefer managing the virtual environment yourself:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe run.py
```

On subsequent runs, use `python launcher.py`, or the last manual command above. The launcher preserves your existing `.env` and reuses installed packages when requirements have not changed. Keep the console open while using the application. Stop it with Ctrl+C. Port 8501 must be free; stop the earlier version if it is still using that port, or change `PORT` in `.env`.

On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Add your OpenRouter key to .env.
.venv/bin/python run.py
```

## What changed

- **Company name dropdown is the primary selection.** A separate CIF filter remains available. A CIF prefix narrows the dropdown; an exact CIF opens the company directly.
- The latest reporting month is selected automatically from the backend. There is no reporting-month selector.
- There are no CSV upload widgets, source-data sidebar, raw-file preview, data-quality page or blank-handling controls in the web view.
- **Every null, empty numeric cell and zero is a confirmed final zero.** A balance moving to zero produces its actual MoM and YTD movement. It is not described as missing, assumed or erroneous.
- Assets, liabilities, non-funded facilities and payment activity are shown separately from the bank's perspective.
- The previous December's year-end closing balance is the opening balance for calendar-YTD calculations.
- All amounts are displayed in **millions**, including position cards, product performance charts, movement charts, evidence and visit briefs.
- The company overview is concise. Links have business labels such as **Official website** and **Financial statements**. Research status, verification banners, industry/checked-date metadata strings and source numbering are absent from the interface.
- Product priorities use the **22 groups supplied in your product list**. OpenRouter evaluates company business context and existing bank positions to **select and rank products**, rather than only rewriting static recommendations.
- The interface uses the supplied bank logo's blue and magenta colors, bank-position cards, interactive charts, company and movement summaries, three opportunity cards and a presentation mode.

## Bank logo and chart readability

The supplied transparent logo appears in the upper-left page corner and in downloaded visit briefs. The original PNG is preserved unchanged as `public/bank-logo.png`; report exports embed the same bytes so the logo remains available offline.

The sampled brand palette is **blue `#2874C2`**, **light blue `#3E8ECD`** and **magenta `#D23B82`**. These colors are used across the header, navigation, cards, buttons, charts and visit briefs. Blue identifies bank assets and magenta identifies bank liabilities in the position chart. Blue movement bars show increases and magenta bars show decreases; the signed labels identify the actual movement.

Both position lines display values directly at every monthly point on desktop, in millions. Movement bars display the signed value in millions at the end of each bar. The Monthly / Year to date control updates both the bar values and the comparison title. The product performance panel lets the officer switch between **Assets** and **Liabilities**, select a product, and review its month-wise balance history. Values are not available only on hover. Source values are not divided into millions again: the charts use the existing Python-calculated million-unit values.

Charts have larger, darker axis and product labels, responsive panels, additional value-label padding and separate icon styling so icon outlines do not affect chart text. On smaller screens, month names and value labels use a compact layout while the complete chart remains fitted to the screen.

## The CEO demonstration

1. Select **Central Finance Company PLC** to show the drop in funding balances and a retention-oriented conversation.
2. Select **Haycarb PLC** to show a manufacturing relationship, funded trade balances and non-funded guarantees.
3. Select **LOLC Finance PLC** or **Citizens Development Business Finance PLC** to show a large institutional lending and deposit relationship.
4. Type a CIF to demonstrate direct customer filtering.
5. Use **Monthly / Year to date** on the movement chart to switch the comparison, without selecting a reporting month.
6. In **Product month-wise performance**, switch between **Assets** and **Liabilities**, then choose the product to review.
7. Click **Present** to focus the page on the selected company.
8. Click **Download visit brief**. The HTML includes the company overview, bank position, movements, product priorities, embedded chart and note space. Open it and print to PDF if required.

With an API key configured, AI priorities are generated automatically after the company is loaded. **AI-informed priorities** appears after a valid AI result is accepted. Without a key, a complete local dashboard remains available with clearly labelled **Relationship priorities**. No synthetic AI result is preloaded or represented as live AI output.

## Your included data

| File | Contents |
| --- | --- |
| `data/customer_balances.csv` | Your updated 74-row customer balance file, including December 2025 closing and January–September 2026. |
| `data/products.csv` | Your 22 bank product groups, including Treasury Bonds. |
| `data/company_master.json` | Short sourced profiles, legal names, business industries and labelled website/financial-report links for the 14 companies. |
| `config/accounting_map.json` | Explicit product/CR-DR mapping for bank-side position classification. |

The Lion Brewery history is stored under two name variants in the source. Complementary monthly segments are joined by CIF/product/side before nulls are finalized as zero. The original customer history and opening balance remain intact.

## Backend updates — no web upload

Configure paths in `.env`:

```dotenv
BALANCES_PATH=data/customer_balances.csv
PRODUCTS_PATH=data/products.csv
COMPANY_MASTER_PATH=data/company_master.json
ACCOUNTING_MAP_PATH=config/accounting_map.json
SOURCE_CURRENCY=LKR
```

An existing bank ETL or scheduled process can replace the balance CSV at that path. Relative paths are resolved against the application folder; absolute Windows paths are also supported. The server reads updated bytes on every API request and invalidates cached recommendations when any input changes. The browser checks for updates every sixty seconds, and the refresh icon reloads immediately.

For an atomic update from a new export:

```powershell
.\.venv\Scripts\python.exe backend_update.py --balances "C:\BankData\bank_products_latest.csv"
.\.venv\Scripts\python.exe backend_update.py --products "C:\BankData\Products_list.csv"
```

The helper validates structure and uses an atomic replacement so users cannot read a half-written CSV. This file adapter can be replaced by your database or data-service adapter without changing the frontend. There is **no live connection to the bank's systems included**; the delivered backend reads the supplied files until your ETL updates them.

Add `Oct-26`, `Nov-26`, etc. to the backend file as new periods arrive. The rightmost chronological month becomes the current position even when all its values are zero/null. For a new calendar year, provide that year's monthly columns together with its previous December balance. Keep one calendar year per snapshot.

## Assets and liabilities: the configured bank-side interpretation

The application uses an explicit mapping, not an unconditional sum of all CR or DR rows. The default mapping for this month-end balance extract is:

| Source product / side | Position category | Display |
| --- | --- | --- |
| CASA CR | Bank liabilities | Current & savings balances |
| TD CR | Bank liabilities | Fixed & term deposits |
| FC MARGIN CR | Bank liabilities | Cash margin deposits |
| CARD CR | Bank liabilities | Card credit balances |
| CASA DR | Bank assets | Overdrafts |
| LN DR | Bank assets | Loans & advances |
| CARD DR | Bank assets | Card debit balances |
| Foreign Bills DR | Bank assets | Foreign bills financing |
| Bank Guarantee DR | Non-funded facilities | Bank guarantees |
| Document Credit DR | Non-funded facilities | Documentary credits |
| Remittance DR | Payment activity | Remittances & payments |

**Important source-dictionary assumption:** CARD CR is treated as a customer credit balance because the supplied input is described as a month-end balance file. If CARD CR in your actual source represents merchant-acquiring turnover or settlement volume instead, change its category to `payments`; it must then be excluded from bank liabilities. Similarly, the default assumes Foreign Bills DR is funded bills outstanding and Remittance is a payment measure. The CSV alone cannot independently establish these accounting meanings. Confirm these source definitions with Finance before presenting the funded totals as the bank's accounting position. This is a classification question, not an error or uncertainty about the supplied zero/null amounts.

The mapping is a management view of the supplied balances, not an audited IFRS balance sheet or regulatory exposure calculation. Guarantees and letters of credit remain separate from funded assets. Payment activity is never added to funded assets or liabilities. Bank liabilities include customer credit balances, so this total is not labelled purely as deposits. `Liabilities − Assets` is the signed net funding position; it is not profit, risk-adjusted exposure or customer net worth. No loan-to-deposit, profitability or market-wallet ratio is inferred.

If a new product/side appears, add a mapping before using that export. The backend stops on unsupported structures instead of silently excluding amounts. There are no warnings for legitimate zero/null balances.

## Exact movements and millions

- Source values are parsed using `Decimal`, retained as integer hundredths, and consolidated exactly. Floating-point values are used only for JSON chart coordinates; arithmetic and formatted fact amounts originate in Python.
- Current position is the latest reporting column.
- **MoM** = latest balance − previous **calendar month's** balance. For January, December opening is the previous month.
- **Calendar YTD** = latest balance − the previous December closing balance in `year End Balance`.
- Percentage change = change / positive comparison balance. When the comparison is zero or negative, the amount movement remains available and the percentage is not calculated.
- Opening, monthly and current null values are final zero after complementary source segments are joined. A transition from positive to zero is a real decline and can be −100%.
- A zero balance is not by itself proof that a legal account or sanctioned facility is closed. Recommendations can discuss re-engagement without asserting closure.
- Two decimals are used for readability in millions. Nonzero amounts below 0.01 Mn use enough additional precision to distinguish them from a confirmed zero.
- Inputs accept comma-formatted amounts, parentheses for negatives, UTF-8/UTF-16/Windows-1252 CSV, and up to two decimal places in the original currency unit. Structural errors such as overlapping populated records or invalid text remain backend validation issues.

**Independent source example:** Central Finance's latest bank liabilities are **56.691975 Mn** under the configured mapping. They changed by **−28.044819 Mn** from August and **−1,003.192440 Mn** from the December 2025 opening. Its guarantee balance is a legitimate **0.00 Mn**, with **−7.00 Mn** YTD movement. Remittance activity of **65.256803 Mn** is shown separately and is not counted as funded lending.

LKR is the configured sample currency because this is a Sri Lankan bank demonstration. If your extract is a different currency or reporting equivalent, set `SOURCE_CURRENCY` accordingly. The app performs no currency conversion; supply consistent units before aggregation.

## Product and AI decision process

The bank product CSV is the source of available **group names**. It does not provide exact product SKUs, eligibility rules, pricing or full terms. The app preserves these group names in every recommendation. It does not invent a bank product name or rate.

The flow is:

1. Build the company business profile and exact bank position, MoM and YTD facts.
2. Build relevant candidate discussions from the supplied groups: retention, operating accounts, liquidity, institutional funding, trade, payments, treasury and expense services.
3. Apply scope checks. **Internal & Control Accounts** is not a customer offer. **Interbank Accounts** requires an actual bank entity; none of the sample finance companies is assumed to be a licensed bank. Savings & Investment Plans is not proposed to these PLCs without confirmed corporate eligibility. These groups remain in the backend catalog; their exclusion from a visit is a suitability choice, not deletion from the bank list.
4. OpenRouter evaluates the company business description and selected customer's actual existing balances and movements, then chooses and ranks three distinct product themes from the allowed candidates.
5. Validate that the chosen names exist in the bank catalog, IDs and supporting facts are valid, themes are distinct, and every suggestion cites at least one bank-position fact. Required local suitability/credit checks cannot be removed by the AI.
6. Render exact amounts from Python fact records alongside the AI discussion rationale and question. The model cannot alter numeric facts. Numeric digits and URLs in generated prose are rejected so model-authored figures cannot be displayed as financial facts.

The product logic distinguishes retaining or deepening an existing group from exploring another group. A large decline in term deposits can make retention more useful than a new credit sale. A manufacturing trade relationship can lead to trade or FX discussions, while a finance company can lead to institutional liquidity and funding. FX proposals require an actual underlying exposure and suitability review. Investments require mandate, liquidity and risk checks. Lending still requires the normal credit process. No automatic approval, guaranteed return, propensity percentage or revenue promise is generated.

The AI prompt applies the decision perspective of a senior corporate banker and head of banking products. It does not represent a human's experience or substitute a bank credit or treasury decision. The rule policies are in `banker/recommendations.py`; replace or extend them with the product team's actual eligibility and offer policies.

If an API key is unavailable, the API fails, or the output is invalid, the view retains the local relationship priorities. A valid AI response can change the rule order and selected product set. The origin label accurately shows whether the current priorities came from AI.

## OpenRouter and information flow

The API key is read from backend `.env`, never returned to the browser. The visit recommendation request includes the selected company's legal name, business description, industry, aggregate bank-position facts and allowed product discussions. CIF, raw CSV, other customers, account numbers and source file paths are excluded. This selected-customer information is sent to OpenRouter because it is needed for the requested company-and-balance analysis. Use a bank-approved account and data-sharing configuration.

The request uses the Chat Completions endpoint with JSON-schema output, `provider.require_parameters=true` and `provider.data_collection=deny`. Optionally set `OPENROUTER_REQUIRE_ZDR=true` to restrict model routing to endpoints advertising zero data retention. No web search is enabled on the confidential product-recommendation request. There is no automatic downgrade of provider policy or silent model fallback.

The company master uses sourced public background descriptions. Public statements are linked for the officer; the app does not download or financially analyze those statements during every visit. Refresh descriptions and URLs in the backend as required. The data file retains source dates for maintenance, but this metadata is intentionally absent from the executive view.

Recommendations are cached in memory by complete backend snapshot, customer and model. They are invalidated when balances, catalog, company profiles or accounting mapping change. Different customer requests cannot reuse one another's AI response. The browser also ignores late responses from previously selected customers.

## Print and export

**Download visit brief** creates a self-contained `.html` report with embedded SVG chart and print styling. Open it in a browser and choose Print → Save as PDF. It requires no chart CDN and works offline. Example reports for Central Finance and Haycarb are in `sample_reports`.

## Checks and tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Tests independently reconcile every populated and null source cell, exact assets/liability totals, December-based YTD, January's MoM baseline, movements to zero, alias segments, leading-zero CIFs, catalog names and scope exclusions, AI product ranking, unsupported model claims, company/snapshot cache isolation, backend replacement and automatic latest-month selection. Flask routes, downloadable reports and absence of raw-file routes are tested as well.

Optional browser QA is provided in `tools/browser_check.py` and requires Playwright and its Chromium headless shell. This is a development check only, not a requirement to run the app. Main dependency versions used for testing are recorded in `TESTED_VERSIONS.txt`. `VALIDATION.md` records the completed checks and any execution limits. No live OpenRouter request was made during preparation because no API key was supplied; the AI integration was exercised with mocked responses.

## Deployment security scope

The local server is Waitress, compatible with Windows and bound to `127.0.0.1` by default. The Vercel deployment uses Vercel's Flask runtime instead of Waitress. A fail-closed HTTP password guard is included for a private demonstration, but there is no built-in bank SSO, server-side CIF entitlement model, persistent audit store or core-banking connector. Before shared bank deployment, connect those existing controls and validate the source dictionary and approved product policies. Changing `HOST` or deploying a public URL does not add those controls.

No source upload or file-edit endpoint is exposed in the web view. The API key and raw backend files are not served. Browser APIs use `Cache-Control: no-store`; recommendation POSTs require the dashboard request header and reject cross-origin requests. The design has no external font, image or chart CDN dependency. Company names, source links and generated wording are escaped in the view and reports.

## File map

| File | Purpose |
| --- | --- |
| `launcher.py` | Python-only setup and launch, including virtual-environment preparation |
| `app.py`, `vercel.json`, `.python-version` | Flask API and Vercel runtime configuration |
| `run.py`, `launcher.py` | Optional local Waitress setup and startup |
| `templates/index.html` | Company-first executive dashboard |
| `public/app.css`, `public/app.js` | Lightweight native-SVG charts, responsive design, filtering and presentation mode |
| `public/bank-logo.png`, `banker/branding.py` | Supplied logo, sampled colors and self-contained report branding |
| `templates/brief.html` | Standalone printable report |
| `banker/data.py` | Exact CSV ingestion and final-zero policy |
| `banker/analytics.py` | Bank positions, MoM and YTD |
| `banker/recommendations.py` | Catalog candidate and fallback policies |
| `banker/gateway.py` | OpenRouter selection/ranking and validation |
| `banker/service.py` | Backend refresh and recommendation cache |
| `backend_update.py` | Atomic CSV update helper |
| `config/accounting_map.json` | Product/side accounting interpretation |
| `data/` | Your balances, product list and sourced profiles |
| `tests/` | Automated financial, API and AI tests |
| `DEPLOY_TO_VERCEL.md` | Private GitHub and Vercel deployment walkthrough |

## Sources

- [Nations Trust Bank annual report](https://www.nationstrust.com/about-us/investor-relations/annual-reports) — banking presentation of loans/advances, deposit funding and separate commitments/contingencies.
- [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).
- [OpenRouter provider selection](https://openrouter.ai/docs/guides/routing/provider-selection).
- [Flask testing](https://flask.palletsprojects.com/en/stable/testing/).
- Public company-background and financial-report links are stored with each company in `data/company_master.json`.
