import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend import main as m


def test_growth_does_not_turn_missing_or_loss_into_growth():
    assert m.percent_change(None, 10) is None
    assert m.percent_change(10, 0) is None
    assert m.percent_change(10, -10) is None
    assert m.percent_change(120, 100) == 20


def test_missing_values_not_zero():
    e, metrics, history, missing = m.build_evidence('000858.SZ',2025,{'income-statements':{'data':{'item':[{'fiscal_year':2025,'operating_income':None}]},'url':'https://fuyao.aicubes.cn','fetched_at':'now','cached':False,'request_id':'t'}})
    assert not any(x['id']=='E1' for x in e)
    assert metrics[0]['value'] is None
    assert missing


def analysis_fixture():
    return dict(verdict='partial',headline='有限支持',summary='根据[E1]分析',supporting=[{'evidence_id':'E1','reason':'相关证据'}],opposing=[],unknown=['缺少分部细节'],conflicts=[],change_conditions=['新增分部证据'],findings=[{'question_id':f'Q{i}','verdict':'unknown','answer':'无法完整判断','evidence_ids':['E1']} for i in range(1,5)])


def test_fabricated_citation_is_blocked():
    a=analysis_fixture()
    a['summary']='[E99]说明公司很好'
    with pytest.raises(m.ServiceError):
        m.validate_analysis(a,[{'id':'E1'}])


def test_missing_subquestion_is_blocked():
    a=analysis_fixture()
    a['findings'][3]['question_id']='Q3'
    with pytest.raises(m.ServiceError):
        m.validate_analysis(a,[{'id':'E1'}])


def test_complete_causal_certainty_is_downgraded():
    a=analysis_fixture(); a['verdict']='supported'
    assert m.validate_analysis(a,[{'id':'E1'}])['verdict']=='partial'


def test_scope_and_subject():
    with pytest.raises(HTTPException):
        m.check_scope('保证本金安全的收益，怎么买入？')
    with pytest.raises(HTTPException):
        m.check_scope('请预测下周美元汇率')
    with pytest.raises(HTTPException):
        m.check_subject(m.StudyInput(company='600519.SH',year=2024,thesis='五粮液2024年的主营业务利润改善。'))


def test_failed_data_never_produces_normal_conclusion(monkeypatch):
    async def fail(*a,**kw):
        raise m.ServiceError('模拟数据源不可用')
    async def should_not_run(*a,**kw):
        pytest.fail('缺少关键数据时不应请求模型生成正常结论')
    monkeypatch.setattr(m,'fuyao',fail)
    monkeypatch.setattr(m,'llm',should_not_run)
    with TestClient(m.app) as c:
        r=c.post('/api/research',json={'company':'000858.SZ','year':2024,'thesis':'五粮液2024年利润增长主要来自主营业务改善。'})
    events=[json.loads(x) for x in r.text.splitlines()]
    assert any(x['type']=='error' and x['code']=='missing_data' for x in events)
    assert not any(x['type']=='result' for x in events)


def test_missing_or_expired_session():
    with TestClient(m.app) as c:
        r=c.post('/api/followup',json={'research_id':'absent','question':'现金流为何下降？'})
    assert r.status_code==410


def test_followup_rejects_buy_sell_request():
    with TestClient(m.app) as c:
        r=c.post('/api/followup',json={'research_id':'absent','question':'现在应该买入吗？'})
    assert r.status_code==422


def test_public_document_sources_and_year_filters():
    docs=json.loads((m.ROOT/'backend/data/documents.json').read_text(encoding='utf-8'))
    assert all(d['page']>0 and d['url'].startswith('https://') for d in docs)
    e,*_=m.build_evidence('000858.SZ',2025,{})
    assert not any(x['kind']=='document' for x in e)


def test_limited_corpus_cannot_claim_no_company_disclosure():
    a=analysis_fixture()
    a['unknown']=['公司未提供解释', '公司没有披露具体原因']
    result=m.validate_analysis(a,[{'id':'E1'}])
    assert result['unknown']==['当前材料未覆盖', '当前材料未覆盖具体原因']


def test_model_failure_keeps_evidence_without_normal_result(monkeypatch):
    async def data(*a,**kw):
        return {'data':{'item':[
            {'fiscal_year':2024,'operating_income':120,'parent_holder_net_profit':20,'act_cash_flow_net':18},
            {'fiscal_year':2023,'operating_income':100,'parent_holder_net_profit':18,'act_cash_flow_net':21}
        ]},'url':'https://fuyao.aicubes.cn','fetched_at':'now','cached':False,'request_id':'test'}
    async def fail(*a,**kw):
        raise m.ServiceError('模拟模型超时','model_error')
    monkeypatch.setattr(m,'fuyao',data)
    monkeypatch.setattr(m,'llm',fail)
    with TestClient(m.app) as c:
        r=c.post('/api/research',json={'company':'000858.SZ','year':2024,'thesis':'五粮液2024年利润增长主要来自主营业务改善。'})
    events=[json.loads(x) for x in r.text.splitlines()]
    assert any(x['type']=='evidence' and x['evidence'] for x in events)
    assert any(x['type']=='error' and x['code']=='model_error' for x in events)
    assert not any(x['type']=='result' for x in events)
