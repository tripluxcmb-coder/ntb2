"""Optional browser checks. Screenshots are QA intermediates, not deliverables."""
from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

from app import create_app


def run(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    app = create_app({"TESTING": True})
    server = make_server("127.0.0.1", 0, app, threaded=True)
    address = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    failures = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
            page.on("pageerror", lambda error: failures.append(str(error)))
            page.goto(address, wait_until="networkidle")
            expect(page.locator("#company-cif")).to_have_text("50100120")
            expect(page.locator("#position-chart .plot-container")).to_have_count(1)
            expect(page.locator("#product-performance-chart .plot-container")).to_have_count(1)
            assert page.locator('#key-facts').count() == 0
            assert page.locator('#product-table').count() == 0
            assert page.locator('input[type="file"]').count() == 0
            assert page.locator('select').count() == 2
            assert '56.69' in page.locator('[data-value="liabilities"]').inner_text()
            assert page.locator('.recommendation').count() == 3
            expect(page.locator('#bank-logo')).to_be_visible()
            assert page.locator('#bank-logo').get_attribute('src') == '/bank-logo.png'
            assert page.locator('#bank-logo').evaluate('(img) => img.complete && img.naturalWidth === 480')
            expect(page.locator('#position-chart .textpoint text')).to_have_count(20)
            assert '56.69 Mn' in page.locator('#position-chart .textpoint text').all_text_contents()
            assert page.locator('#position-chart .xtick text').first.evaluate('(text) => getComputedStyle(text).stroke') == 'none'
            assert float(page.locator('#position-chart .xtick text').first.evaluate('(text) => parseFloat(getComputedStyle(text).fontSize)')) >= 12
            assert page.locator('#movement-chart .bartext').count() == 6
            assert all('Mn' in text for text in page.locator('#movement-chart .bartext').all_text_contents())
            assert page.locator('#product-performance-chart .product-point text').count() == 10
            page.locator('[data-product-category="liabilities"]').click()
            assert 'selected' in page.locator('[data-product-category="liabilities"]').get_attribute('class')
            assert page.locator('#product-performance-select option').count() >= 1
            assert page.locator('#product-performance-chart .product-point text').count() == 10
            page.locator('[data-product-category="assets"]').click()
            assert page.locator('#position-chart .textpoint text').evaluate_all('''(nodes) => {
                const n=nodes.length/2;
                return Array.from({length:n},(_,i)=>{
                    const a=nodes[i].getBoundingClientRect(),b=nodes[i+n].getBoundingClientRect();
                    return a.bottom<=b.top || b.bottom<=a.top;
                }).every(Boolean);
            }'''), 'Asset and liability labels overlap'
            page.screenshot(path=str(output/'desktop_central.png'), full_page=True)
            page.locator('#position-chart').screenshot(path=str(output/'position_central.png'))
            page.locator('#company-select').select_option('50688593')
            expect(page.locator("#company-cif")).to_have_text("50688593")
            assert '95.86' in page.locator('[data-value="assets"]').inner_text()
            assert '595.00' in page.locator('[data-value="contingent"]').inner_text()
            assert page.get_by_role('link',name='Financial statements',exact=True).count() == 1
            page.locator('[data-movement="ytd"]').click()
            assert page.locator('[data-movement="ytd"]').get_attribute('class') == 'selected'
            page.locator('#cif-input').fill('50223711')
            expect(page.locator("#company-cif")).to_have_text("50223711")
            assert 'Lion Brewery' in page.locator('#company-name').inner_text()
            page.locator('#cif-input').fill('')
            expect(page.locator("#company-select option")).to_have_count(14)
            companies = page.request.get(address+'/api/customers').json()['customers']
            for company in companies:
                page.locator('#company-select').select_option(company['cif'])
                expect(page.locator("#company-cif")).to_have_text(company["cif"])
                assert page.locator('.metric-card').count() == 4
                assert page.locator('.recommendation').count() == 3
                expect(page.locator('#position-chart .textpoint text')).to_have_count(20)
                expect(page.locator('#product-performance-chart .product-point text')).to_have_count(10)
                assert page.locator('#position-chart .textpoint text').evaluate_all('''(nodes) => {
                    const n=nodes.length/2;
                    return Array.from({length:n},(_,i)=>{
                        const a=nodes[i].getBoundingClientRect(),b=nodes[i+n].getBoundingClientRect();
                        return a.bottom<=b.top || b.bottom<=a.top;
                    }).every(Boolean);
                }'''), 'Labels overlap for '+company['cif']
            page.locator('#company-select').select_option('50688593')
            expect(page.locator("#company-cif")).to_have_text("50688593")
            response = page.request.get(address+'/brief/50688593?download=1')
            assert response.status == 200 and 'attachment' in response.headers['content-disposition']
            assert '<svg' in response.text()
            page.screenshot(path=str(output/'desktop_haycarb.png'), full_page=True)
            page.locator('#position-chart').screenshot(path=str(output/'position_haycarb.png'))
            page.locator('#presentation-button').click()
            assert page.locator('.selector-card').is_hidden()
            page.screenshot(path=str(output/'presentation_haycarb.png'),full_page=True)
            page.locator('#presentation-button').click()
            page.set_viewport_size({"width": 390,"height":844})
            page.wait_for_timeout(250)
            assert page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth'), 'Page overflows the mobile viewport'
            page.screenshot(path=str(output/'mobile_haycarb.png'),full_page=True)
            assert page.locator('.chart-viewport').evaluate_all('(views) => views.every(view => view.scrollWidth <= view.clientWidth + 1)')
            page.locator('#portfolio').screenshot(path=str(output/'portfolio_mobile.png'))
            assert not failures, failures
            browser.close()
        print('Browser checks passed: 14 companies, fitted charts, asset/liability product performance, visible Mn labels, CIF filter, YTD toggle, report, presentation mode and mobile layout.')
    finally:
        server.shutdown()
        thread.join(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT.parent/'browser_qa')
    run(parser.parse_args().output)
