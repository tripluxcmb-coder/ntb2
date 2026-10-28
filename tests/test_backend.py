from __future__ import annotations

import csv
import io
import shutil
from pathlib import Path

import pytest

from app import app as vercel_app, create_app
from banker.service import BankService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    return create_app({"TESTING":True}).test_client()


def test_company_dropdown_source_and_all_customers(client):
    companies = client.get('/api/customers').json
    assert len(companies["customers"]) == 14
    for customer in companies["customers"]:
        response = client.get('/api/customer/' + customer["cif"])
        assert response.status_code == 200
        p = response.json
        assert p["profile"]["reporting_month"] == "2026-09"
        assert len(p["priorities"]["recommendations"]) == 3
        assert p["company"]["description"]
        assert all(link["label"] != 'Company source 1' for link in p["company"]["links"])


def test_executive_ui_has_no_upload_or_month_controls(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.text
    assert 'id="company-select"' in html and 'id="cif-input"' in html
    assert 'type="file"' not in html and 'Reporting month</label>' not in html
    assert 'missing data' not in html.lower()
    assert 'verify entity' not in html.lower()
    assert 'id="key-facts"' not in html and 'id="product-table"' not in html
    assert 'id="product-performance-chart"' in html
    assert 'data-product-category="assets"' in html and 'data-product-category="liabilities"' in html


def test_printable_brief_is_downloadable_and_self_contained(client):
    response = client.get('/brief/50100120?download=1')
    assert response.status_code == 200
    assert 'attachment;' in response.headers['Content-Disposition']
    assert '<svg ' in response.text
    assert '2025' in response.text and 'YTD' in response.text
    assert 'Official website' in response.text and 'Financial statements' in response.text
    assert '<script src=' not in response.text and '<link rel="stylesheet"' not in response.text


def test_raw_backend_files_are_not_served(client):
    for path in ['/data/customer_balances.csv','/data/products.csv','/.env','/upload']:
        assert client.get(path).status_code == 404


def test_supplied_logo_is_served_and_embedded_in_offline_report(client):
    import base64
    import re
    image = client.get('/bank-logo.png')
    assert image.status_code == 200 and image.mimetype == 'image/png'
    assert 'id="bank-logo"' in client.get('/').text
    report = client.get('/brief/50100120').text
    embedded = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', report)
    assert embedded and base64.b64decode(embedded[1]) == image.data


def test_vercel_entrypoint_and_public_assets(client):
    assert vercel_app.name == "app"
    assert client.get('/app.css').status_code == 200
    javascript = client.get('/app.js')
    assert javascript.status_code == 200 and len(javascript.data) < 40_000
    assert client.get('/plotly.min.js').status_code == 404


def test_mobile_frontend_payload_stays_lightweight(client):
    assets = [client.get(path).data for path in ('/app.js', '/app.css', '/bank-logo.png')]
    assert sum(map(len, assets)) < 120_000
    assert b'Plotly' not in assets[0]


def test_vercel_access_protection_fails_closed(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("APP_ACCESS_PASSWORD", raising=False)
    protected = create_app({"TESTING": True}).test_client()
    assert protected.get('/').status_code == 503
    assert protected.get('/health').status_code == 200

    monkeypatch.setenv("APP_ACCESS_USERNAME", "officer")
    monkeypatch.setenv("APP_ACCESS_PASSWORD", "correct-horse")
    protected = create_app({"TESTING": True}).test_client()
    assert protected.get('/').status_code == 401
    assert protected.get('/', headers={"Authorization": "Basic b2ZmaWNlcjpjb3JyZWN0LWhvcnNl"}).status_code == 200


def test_exported_chart_displays_current_values_in_millions(client):
    from banker.reporting import position_svg
    from xml.etree import ElementTree
    profile = client.get('/api/customer/50100120').json['profile']
    chart = ElementTree.fromstring(position_svg(profile))
    text = [node.text for node in chart.findall('{http://www.w3.org/2000/svg}text')]
    assert '56.69 Mn' in text and '1.09 Mn' in text
    assert profile['unit'] in text
    assert sum(value.endswith(' Mn') for value in text if value) == 21


def test_unknown_cif(client):
    response = client.get('/api/customer/unknown')
    assert response.status_code == 404
    assert 'No customer' in response.json['error']


def test_cross_origin_ai_request_rejected(client):
    response = client.post('/api/customer/50100120/recommendations',json={},headers={
        'Origin':'https://unrelated.example','X-Requested-With':'RelationshipDashboard'})
    assert response.status_code == 403


def test_backend_replacement_refreshes_current_position(tmp_path):
    shutil.copytree(ROOT/'data', tmp_path/'data')
    shutil.copytree(ROOT/'config', tmp_path/'config')
    service = BankService(tmp_path)
    before = service.dashboard('50100120')
    target = tmp_path/'data/customer_balances.csv'
    text = target.read_text(encoding='utf-8-sig')
    rows = list(csv.DictReader(io.StringIO(text)))
    for row in rows:
        if row['CIF']=='50100120' and row['Product']=='CASA' and row['Payment Type']=='CR':
            row['Sep-26'] = '0'
    with target.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    after = service.dashboard('50100120')
    assert before['version'] != after['version']
    assert after['profile']['metrics']['liabilities']['amount_mn'] == 37.000512
    assert next(p for p in after['profile']['products'] if p['product']=='CASA')['amount_mn'] == 0


def test_backend_append_october_automatically_selects_latest(tmp_path):
    shutil.copytree(ROOT/'data', tmp_path/'data')
    shutil.copytree(ROOT/'config', tmp_path/'config')
    target=tmp_path/'data/customer_balances.csv'
    rows=list(csv.DictReader(target.open(encoding='utf-8-sig')))
    fields=[*rows[0],'Oct-26']
    for row in rows: row['Oct-26']=''
    with target.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    profile=BankService(tmp_path).dashboard('50100120')['profile']
    assert profile['reporting_month']=='2026-10'
    assert profile['metrics']['assets']['amount_mn']==0
    assert profile['metrics']['liabilities']['amount_mn']==0
    assert profile['metrics']['liabilities']['mom']['pct']==-100


def test_ai_cache_is_customer_and_snapshot_specific(tmp_path):
    shutil.copytree(ROOT/'data', tmp_path/'data');shutil.copytree(ROOT/'config', tmp_path/'config')
    calls=[]
    class FakeAI:
        def recommend(self,profile,company,choices):
            from banker.recommendations import fallback_recommendations
            calls.append(profile['cif'])
            result=fallback_recommendations(profile,company,choices)
            result['origin']='ai'
            return result
    service=BankService(tmp_path,ai_factory=FakeAI)
    first=service.dashboard('50100120')
    assert service.recommend('50100120',first['version'])['origin']=='ai'
    service.recommend('50100120',first['version'])
    assert calls==['50100120']
    service.recommend('50688593')
    assert calls==['50100120','50688593']
    assert service.dashboard('50100120')['priorities']['origin']=='ai'
    target=tmp_path/'data/customer_balances.csv';target.write_bytes(target.read_bytes()+b'\n')
    assert service.dashboard('50100120')['priorities']['origin']=='rules'
