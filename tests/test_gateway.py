from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import requests

from banker.gateway import GatewayError, OpenRouterClient, build_payload, validate_result
from banker.recommendations import candidates
from banker.service import BankService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def context():
    service=BankService(ROOT)
    data=service.dashboard('50100120')
    choices=candidates(data['profile'],data['company'],service.catalog)
    return data['profile'],data['company'],choices


def valid_response(profile,company,choices):
    selected=[];themes=set()
    # Reversing the candidate list proves AI selection can change the rule ranking.
    for choice in reversed(choices):
        if choice['theme'] in themes: continue
        themes.add(choice['theme'])
        selected.append({'product_id':choice['id'],'why_now':'Match the service to the company operating cycle.',
                         'question':'What requirements would make this useful for your treasury team?',
                         'evidence_ids':[choice['evidence_ids'][0],'C_PROFILE']})
        if len(selected)==3: break
    return {'visit_objective':'Discuss the operating requirements and treasury priorities.','recommendations':selected}


class Response:
    def __init__(self,output,status=200,finish='stop'):
        self.output,self.status_code,self.finish=output,status,finish
    def json(self):
        return {'choices':[{'finish_reason':self.finish,'message':{'content':json.dumps(self.output)}}]}


class Session:
    def __init__(self,responses): self.responses=list(responses);self.calls=[]
    def post(self,url,**kwargs):
        self.calls.append((url,kwargs))
        response=self.responses.pop(0)
        if isinstance(response,Exception): raise response
        return response


def test_ai_ranks_bank_catalog_using_company_and_balances(context):
    output=valid_response(*context)
    session=Session([Response(output)])
    result=OpenRouterClient('test-key',session=session).recommend(*context)
    payload=json.loads(session.calls[0][1]['json']['messages'][1]['content'])
    assert payload['company']['name']=='CENTRAL FINANCE COMPANY PLC'
    assert payload['company']['industry']=='financial_services'
    assert 'business_description' in payload['company']
    assert payload['position']['opening_period']=='2025-12'
    assert payload['position']['zero_and_null_balances_are_final_zero'] is True
    assert '50100120' not in json.dumps(payload)
    assert any(f.get('amount_mn')==56.691975 for f in payload['position']['facts'])
    assert [r['id'] for r in result['recommendations']] == [r['product_id'] for r in output['recommendations']]
    assert result['recommendations'][0]['id'] != context[2][0]['id']
    assert result['origin']=='ai'
    body=session.calls[0][1]['json']
    assert body['provider']['require_parameters'] is True
    assert body['provider']['data_collection']=='deny'
    assert 'plugins' not in body


@pytest.mark.parametrize('mutation',['invented_product','numeric_claim','unsupported_evidence','no_balance_evidence','duplicate','wrong_count','data_error_claim'])
def test_ai_output_is_constrained_to_bank_products_and_facts(context,mutation):
    output=valid_response(*context)
    if mutation=='invented_product': output['recommendations'][0]['product_id']='unlisted_financial_product'
    if mutation=='numeric_claim': output['recommendations'][0]['why_now']='Offer a rate of 15%.'
    if mutation=='unsupported_evidence': output['recommendations'][0]['evidence_ids']=['P999']
    if mutation=='no_balance_evidence': output['recommendations'][0]['evidence_ids']=['C_PROFILE']
    if mutation=='duplicate': output['recommendations'][1]=copy.deepcopy(output['recommendations'][0])
    if mutation=='wrong_count': output['recommendations']=[]
    if mutation=='data_error_claim': output['recommendations'][0]['why_now']='The missing data should be verified.'
    with pytest.raises(GatewayError): validate_result(output,context[0],context[2])


def test_truncated_output_is_rejected(context):
    with pytest.raises(GatewayError,match='incomplete'):
        OpenRouterClient('key',session=Session([Response({},finish='length')])).recommend(*context)


def test_request_retries_are_bounded_and_do_not_print_provider_errors(context):
    session=Session([Response({},429),Response({},503)])
    sleeps=[]
    with pytest.raises(GatewayError,match='503'):
        OpenRouterClient('key',session=session,sleep=sleeps.append).recommend(*context)
    assert len(session.calls)==2 and sleeps==[1]


def test_transport_error_sanitized(context):
    session=Session([requests.ConnectionError('private balance secret')]*2)
    with pytest.raises(GatewayError) as error:
        OpenRouterClient('key',session=session,sleep=lambda _:None).recommend(*context)
    assert 'secret' not in str(error.value)


def test_missing_key():
    with pytest.raises(GatewayError,match='OPENROUTER_API_KEY'): OpenRouterClient('')


def test_gateway_failure_preserves_local_brief():
    class FailingAI:
        def recommend(self,*args): raise GatewayError('No provider')
    service=BankService(ROOT,ai_factory=FailingAI)
    result=service.recommend('50100120')
    assert result['origin']=='rules' and len(result['recommendations'])==3
