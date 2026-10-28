# Validation record

Validated on 28 October 2026 using Python 3.12.

Python-only launch update: a clean setup was exercised in a new folder containing spaces. The launcher created its virtual environment, installed runtime dependencies, preserved an existing `.env`, reused dependencies on the next launch, and started the live server successfully. The health endpoint and 14-company API passed. This launcher smoke check ran on Linux; the Windows executable path is configured separately in the launcher. The package no longer contains batch files.

- **50 automated tests passed.** The tests reconcile every current, historical and opening source cell independently, including final null/zero cells and complementary company-name segments.
- Independently checked Central Finance's funded assets, liabilities, monthly movements and December-based YTD movements against the updated CSV and the documented accounting mapping.
- Verified that Dialog's loan balance at zero produces the actual reduction from the December opening, without any missing-data warning.
- Verified that guarantees, documentary credits and payment activity are kept separate from funded assets and liabilities.
- Verified that a newly appended reporting month becomes the current month automatically, even when all new values are null and therefore zero.
- Browser checks passed for all 14 companies, company-name selection, CIF filtering, all three portfolio charts, Assets/Liabilities product selection, Monthly/YTD comparison, report download, presentation mode and a 390-pixel mobile viewport.
- Visually reviewed the desktop, presentation and mobile layouts. All three chart panels rendered within their available screen width, no chart or page-wide horizontal overflow was found on mobile, and no browser JavaScript error occurred.
- Bank branding update: the supplied transparent logo is preserved unchanged. Blue `#2874C2`, light blue `#3E8ECD` and magenta `#D23B82` are used across the view. The logo is displayed in the page corner and embedded in offline visit briefs.
- Chart readability update: position values appear at every monthly point on desktop, signed movement values appear on bars, and the selected asset/liability product displays its monthly values, all in millions. Axis and product labels are larger and darker. Mobile charts use compact labels and fit their panels without horizontal scrolling.
- Verified that the customer view contains no upload widget, month selector, source-numbering labels or research-status banner. The raw CSV files and `.env` are not served by the app.
- Verified that AI product choices can change the local candidate order, remain within the uploaded catalog and retain local eligibility checks and evidence. Rejected invented products, unsupported facts, duplicate themes, model-authored figures and output describing final zero balances as missing data.
- Verified per-customer/per-snapshot recommendation caching and invalidation when backend data changes.
- Verified the top-level Vercel WSGI entry point, Flask import under a Vercel-style environment, 14-company API, public CDN asset paths and valid `vercel.json` configuration.
- Verified that Vercel access protection fails closed with HTTP 503 when its password is absent, rejects unauthenticated requests and accepts correct HTTP Basic credentials. The public health endpoint exposes only `{"status":"ok"}`.
- Replaced the 4.85 MB Plotly dependency with native browser SVG charts. The charts retain visible million-value labels, bank colors, monthly/YTD switching, Assets/Liabilities product analysis and responsive screen fitting without a chart-library download.
- Removed the **Key facts for the visit** and **Product profile** sections from the web page as requested. Their underlying exact facts remain available to the recommendation engine and downloadable visit brief.
- The combined application JavaScript, CSS and original logo are approximately 93 KB before transport compression, and an automated budget prevents these core frontend assets from exceeding 120 KB.
- Extracted the final GitHub ZIP, initialized a repository, confirmed the required data and deployment files are tracked, and reran all 50 tests from the extracted artifact. No `.env`, virtual environment, Vercel project link, Git metadata, cache, log or compiled Python file is included.

No live paid OpenRouter request was made because an API key was not supplied. The gateway and its success/error paths were tested using mocked responses. A valid key, sufficient credits and a compatible structured-output provider are required to validate the live service in the bank's environment.

The source dictionary assumptions in `config/accounting_map.json`, especially CARD CR, Foreign Bills and Remittance, are documented in README.md. These mappings are configurable and were not independently confirmed by the source owner. The supplied null/zero rule was applied exactly as instructed.
