"""「初回」が付かない初回面談の題名の取り込みと、自動処理の「空欄だけ埋める」書き込みのテスト。"""
from unittest.mock import MagicMock, patch

import pytest

from app.application.use_cases.auto_process_meetings import AutoProcessMeetingsUseCase
from app.domain.services.candidate_title_matcher import CandidateTitleMatcher
from app.infrastructure.zoho.client import ZohoWriteClient


@pytest.mark.parametrize("title,expected_first", [
    ("山田 太郎さん: 【ひとキャリ松浦】転職面談", "山田 太郎"),
    ("山田太郎さん: キャリア面談_株式会社b&q", "山田太郎"),
    ("レイノス株式会社 山田 太郎さん: 【株式会社b&q】転職面談", "山田 太郎"),
    ("転職面談 (山田 太郎)", "山田 太郎"),
    ("初回面談（山田 太郎）", "山田 太郎"),
    ("山田 太郎様【無料キャリア相談】", "山田 太郎"),
    ("JP15:30~ 山田 太郎様_初回面談", "山田 太郎"),
    ("JP9:00 山田太郎様_初回面談", "山田太郎"),
])
def test_extract_candidates_first_choice(title, expected_first):
    names = CandidateTitleMatcher(None).extract_candidates_from_title(title)
    assert names and names[0] == expected_first


def test_extract_candidates_never_returns_company_or_whole_title():
    m = CandidateTitleMatcher(None)
    assert m.extract_candidates_from_title("転職面談") == []
    assert m.extract_candidates_from_title("【定例】SEOツール") == []
    names = m.extract_candidates_from_title("レイノス株式会社 山田太郎さん: 転職面談")
    assert names == ["山田太郎"]
    assert all("株式会社" not in n for n in names)


def test_extract_candidates_respects_configured_regex():
    m = CandidateTitleMatcher(r"^【(?P<name>[^】]+)】")
    assert m.extract_candidates_from_title("【山田 太郎】初回") == ["山田 太郎"]
    assert m.extract_candidates_from_title("山田 太郎さん: 転職面談") == []


@pytest.mark.parametrize("title,ok", [
    ("JP15:30~ 山田様_初回面談", True),
    ("山田様【無料キャリア相談】", True),
    ("山田さん: 【ひとキャリ松浦】転職面談", True),
    ("山田さん: キャリア面談_株式会社b&q", True),
    ("JP20:00 山田様_面接対策", False),
    ("山田さん: 転職面談_面接対策", False),
    ("JP20:00 山田様_進捗面談", False),
    ("キャリア面談（提案）山田さん", False),
    ("【定例】SEOツール", False),
])
def test_auto_process_keywords(title, ok):
    assert AutoProcessMeetingsUseCase._has_auto_process_keyword(title) is ok


def test_filter_fill_only_keeps_existing_values_and_drops_blanks():
    data = {"field85": "人材紹介3年", "field131": "法人営業", "field28": 500, "desired_industry": ["人材"], "transfer_priorities": ""}
    current = {"field85": "CAが入れた職歴", "field131": None, "field28": None, "desired_industry": [], "transfer_priorities": "CAのメモ"}
    to_send, skipped = ZohoWriteClient._filter_fill_only(data, current)
    assert to_send == {"field131": "法人営業", "field28": 500, "desired_industry": ["人材"]}
    assert skipped == ["field85"]  # 空の抽出結果(transfer_priorities)は送らず、既存値も消さない


def _write_client():
    client = ZohoWriteClient.__new__(ZohoWriteClient)
    client.settings = MagicMock(zoho_app_hc_module="jobSeeker", zoho_api_base_url="https://example.invalid")
    client.field_mapping = {"career_history": "field85", "current_duties": "field131"}
    client._get_access_token = lambda: "token"
    return client


def test_fill_only_aborts_when_current_values_cannot_be_read():
    client = _write_client()
    client._get_current_values = MagicMock(side_effect=RuntimeError("boom"))
    with patch("app.infrastructure.zoho.client.request.urlopen") as urlopen:
        res = client.update_jobseeker_record("1", {"career_history": "x"}, skip_validation=True, fill_only=True)
    assert res["status"] == "error"
    urlopen.assert_not_called()  # 現在値が読めないときは書かない


def test_fill_only_with_nothing_to_fill_does_not_call_zoho():
    client = _write_client()
    client._get_current_values = MagicMock(return_value={"field85": "既存", "field131": "既存"})
    with patch("app.infrastructure.zoho.client.request.urlopen") as urlopen:
        res = client.update_jobseeker_record("1", {"career_history": "x", "current_duties": "y"}, skip_validation=True, fill_only=True)
    assert res["status"] == "success" and res["updated_fields"] == [] and sorted(res["skipped_fields"]) == ["field131", "field85"]
    urlopen.assert_not_called()


@pytest.mark.asyncio
async def test_collect_filters_by_title_and_date_on_server_side():
    use_case = AutoProcessMeetingsUseCase()
    repo = MagicMock()
    repo.list_meetings_paginated.return_value = {"items": [], "has_next": False}
    with patch("app.application.use_cases.auto_process_meetings.ZohoClient"):
        await use_case._collect_processing_candidates(repo, MagicMock(), None, 5, None, lookback_days=7)
    kwargs = repo.list_meetings_paginated.call_args.kwargs
    assert "転職面談" in kwargs["title_keywords"] and "初回" in kwargs["title_keywords"]
    assert kwargs["created_at_gte"] and kwargs["created_at_gte"].endswith("Z")
    assert kwargs["structured"] is False


@pytest.mark.asyncio
async def test_same_name_search_runs_once_per_run_and_duplicates_are_skipped():
    use_case = AutoProcessMeetingsUseCase()
    repo = MagicMock()
    repo.list_meetings_paginated.return_value = {"items": [
        {"id": "m1", "title": "山田 太郎さん: 転職面談"},
        {"id": "m2", "title": "JP9:00 山田 太郎様_初回面談"},
    ], "has_next": False}
    zoho = MagicMock()
    zoho.search_app_hc_by_exact_name.return_value = [
        {"record_id": "1", "candidate_name": "山田 太郎"}, {"record_id": "2", "candidate_name": "山田太郎"}]
    with patch("app.application.use_cases.auto_process_meetings.ZohoClient", return_value=zoho):
        out = await use_case._collect_processing_candidates(repo, CandidateTitleMatcher(None), None, 5, None, lookback_days=7)
    assert zoho.search_app_hc_by_exact_name.call_count == 1  # 同じ名前は1回だけ検索
    assert all(getattr(c, "skip_reason", None) == "zoho_not_exact" for c in out)  # 同名2人は処理しない


def test_exact_name_search_falls_back_to_loose_like_when_spacing_differs():
    from app.infrastructure.zoho.client import ZohoClient
    client = ZohoClient.__new__(ZohoClient)
    client.settings = MagicMock(zoho_app_hc_module="jobSeeker", zoho_app_hc_name_field_api="Name", zoho_app_hc_id_field_api="field1")
    client._get = MagicMock(return_value={})  # equals / starts_with では当たらない
    client._coql_query = MagicMock(return_value={"data": [{"id": "9", "Name": "山田 太郎", "field1": "C9"}]})
    out = client.search_app_hc_by_exact_name("山田太郎", name_variations=["山田太郎"])
    q = client._coql_query.call_args.args[0]
    assert "from jobSeeker" in q and " in (" in q and "'山田 太郎'" in q and "'山田　太郎'" in q and "'山田太郎'" in q
    assert out[0]["record_id"] == "9" and out[0]["candidate_name"] == "山田 太郎"
    assert CandidateTitleMatcher(None).is_exact_match("山田太郎", out[0]["candidate_name"], pre_extracted=True)


def test_loose_search_rejects_unsafe_names():
    from app.infrastructure.zoho.client import ZohoClient
    client = ZohoClient.__new__(ZohoClient)
    client._coql_query = MagicMock()
    assert client._search_app_hc_by_loose_name("jobSeeker", "Name", None, "O'Brien") == []
    assert client._search_app_hc_by_loose_name("jobSeeker", "Name", None, "山") == []
    assert client._search_app_hc_by_loose_name("jobSeeker", "Name", None, "あ" * 13) == []
    client._coql_query.assert_not_called()
