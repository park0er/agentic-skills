#!/usr/bin/env python3
"""Dashboard query runner for rollie-diagnose server.

POST a dashboard query to ``/api/v1/query/dashboard``.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

# Make ``scripts/`` importable as a package root (so ``from utils.http_client``
# resolves when this file is invoked directly).
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils.http_client import (  # noqa: E402
    SKILL_ROOT,
    SKILL_VERSION,
    build_url,
    execute_and_emit,
    resolve_base_url,
    safe_identifier,
)

__version__ = SKILL_VERSION

QUERY_PATH = "/api/v1/query/dashboard"
QUERY_METHOD = "POST"


def _dashboard_help_text() -> str:
    return """
用法:dashboard_query.py --dashboard <query_name> --params '<json>' [选项]

⚠️  传参前必须先读本地字典文件确认字段,不要猜(本help约100行,全部读完不要截断)。
    字典文件位于:skills/rollie-diagnose/references/

--dashboard  执行查询

  --dashboard <query_name> --params '<json>' [--session-id <id>]

  通用 params 结构(四子对象,均可省略):
    {
      "time": {
        "start_time": "2026-03-21T00:00:00+08:00",   // 必须 +08:00 格式
        "end_time":   "2026-03-21T08:00:00+08:00",   // 与 hours 二选一
        "hours": 24,                                  // 相对时间窗口,默认 24
        "compare": true,                              // 是否带同环比,涉及日期同环比时为true，当为true时一定需要填写"comparison_start_time"和"comparison_end_time"；没有同环比时为false，当为false时只需要填写"start_time"和"end_time"
        "comparison_start_time": "...",               // 自定义对比期起始时间(+08:00)
        "comparison_end_time":   "..."                // 自定义对比期结束时间(+08:00)
      },
      "filters": {                                    // 过滤维度,唯一路径
        "customerId": "1357652",                      // 单值等值，注意息壤看板参数为 customer_id
        "tagId": ["101", "102"]                       // 多值 IN 查询，注意息壤看板参数为 tag_id
      },
      "split": {
        "group_by": "adId",                           // 下钻维度,也可传数组 ["adId","mediaType"] 表达多维交叉，注意息壤看板参数为 ad_id及media_type
        "top": 50,                                    // 返回条数,默认 50
        "sort_by": "fee"                              // 排序指标,默认 measures[0]
      },
      "measures": ["fee", "view", "click"]            // 指标列表,空则用模板默认
    }


  可查询看板(详细字段含义见对应字典文件):

  query_request_info           ① 媒体请求
    作用:确认请求量/质量是否异常
    字典:references/request_info_field_dictionary.md
    group_by: tagId, mediaType
    measures: count, eRawQuery, eQuery, eFill

  query_pivot_search_term      辅助 搜索词
    作用:查看 SearchTermV2 搜索词维度的请求/曝光/点击/消耗和预估指标
    字典:references/pivot_search_term_field_dictionary.md
    group_by: query, dsp, tagId, adId, campaignId, customerId, appId, mediaType
    measures: count, request, view, pctr, fee, feeRtb, totalfee, click, ctr, ecpm
    拼写陷阱:真实搜索词字段是 query，keyword/search_query/searchTerm 只是 alias

  query_emi_diagnosis          ② 广告下发
    作用:排查下发链路是否掉量
    字典:references/emi_diagnosis_field_dictionary.md
    group_by: campaignId, adId
    measures: count, delivery, budgetDelivery, controlScore

  query_xirang_delivery_diagnosis  ③ 召回+业务过滤(息壤)
    作用:排查息壤看板 lifecycle 过滤变化
    字典:references/xirang_delivery_diagnosis_field_dictionary.md
    ⚠️  此看板参数必须用下划线风格(customer_id, ad_id, campaign_id, tag_id),非 camelCase
    group_by: index_ad_lifecycle, campaign_id, ad_id, tag_id, media_type
    measures: index_filter_count

  query_xirang_adx_diagnosis  ADX链路多维分析(息壤)
    作用:排查 ADX 请求、填充、竞胜、超时和过滤状态
    字典:references/xirang_adx_diagnosis_field_dictionary.md
    group_by: dt, media_type, tag_id, physical_dsp, deal_id, adx_status, adx_reason
    measures: adx_request, adx_fill, adx_win, adx_fill_rate, adx_win_rate, adx_media_request

  query_xirang_recall_diagnosis  召回链路多维分析(息壤)
    作用:排查召回过滤变化，按流量/应用/客户/广告/引擎链路维度下钻
    字典:references/xirang_recall_diagnosis_field_dictionary.md
    group_by: dt, media_type, tag_id, recall_pipeline, recall_ad_lifecycle, passMerge, ad_id, campaign_id
    measures: recall_filter_count

  query_xirang_pre_ranking      ④ 粗排(息壤)
    作用:排查粗排阶段请求数与 pscore 分布，按媒体/广告位/实验/过滤原因等维度下钻
    字典:references/xirang_pre_ranking_field_dictionary.md
    group_by: media_type, tag_id, recall_expid, recall_channel_name, recall_filter_reason, is_discard, ad_id, campaign_id
    measures: count, sum_pscore_recall, avg_pscore_recall

  query_xirang_fine_ranking      ⑥ 精排(息壤)
    作用:排查精排阶段请求数与模型打分(ctr/cvr/pltv等)，按媒体/广告位/实验/过滤原因等维度下钻
    字典:references/xirang_fine_ranking_field_dictionary.md
    group_by: media_type, tag_id, ad_id, campaign_id, filter_reason, rank_adsource, recall_channel_name
    measures: count, avg_pctr_rank, avg_pcvr_rank, avg_pdeepcvr_rank, avg_pltv_rank

  query_xirang_rta_diagnosis  RTA多维分析(息壤)
    作用:排查 RTA 请求、通过率、超时、缓存命中、出价系数填充
    字典:references/xirang_rta_diagnosis_field_dictionary.md
    group_by: dt, media_type, tag_id, rta_host, client_name, ret_code, req_type
    measures: de_rta_req_token, de_rta_ac_rate_token, rta_cus_req_client, rta_cus_timeout_rate_client

  query_xirang_budget_analysis  预算分析看板(息壤)
    作用:排查预算消耗、达限状态，按应用/账户/行业/区域/代理维度分析
    字典:references/xirang_budget_analysis_field_dictionary.md
    filters: app_id, campaign_id, customer_id, industry_level1, industry_level2,
             effect_region, agent_id, core_id
      第一/二层固定 IN，第三层支持 {"operator":"not_in","values":[...]}
    split.stat_type: "total"(合计) / "daily_avg"(日均)，默认 total
    split.group_by: application/customer/campaign，只返回该 bucket，精度不匹配报错
    reach_limit: 服务端默认 unlimited
    输出: application + customer 两张表

  query_guyu_recall            ④ 粗排
    作用:排查粗排拦截(filterReason)变化
    字典:references/guyu_recall_field_dictionary.md
    group_by: filterReason, campaignId, adId, tagId
    measures: count, pctr_avg, pcvr_avg, pscore_avg

  query_guyu_stat              ⑤ 精排
    作用:排查精排拦截与 OCPX_STRATEGY_FILTER 变化
    字典:references/guyu_stat_field_dictionary.md
    group_by: filterReason, campaignId, adId, tagId
    measures: count, pctr, pcvr, pdeepcvr

  query_ocpx_strategy          ⑥ OCPX 策略
    作用:排查策略拦截、调价与二次下钻原因
    字典:references/ocpx_strategy_field_dictionary.md
    group_by: campaignId, adId, tagId, sFilerReason, convType, deepconvType, incrementalStatus
    measures: count, price, priceRatio, ctr, cvr, cvrFixed, deepCvr, deepCvrFixed, riskBid, targetCpa, targetCpaRatio, deepTargetCpa, deepTargetCpaRatio

  query_xirang_ad_effect       ⑦ 曝光后链路(息壤)
    作用:查看广告效果数据(曝光/点击/收入/转化),支持行业/app/广告位等多维度下钻
    字典:references/xirang_ad_effect_field_dictionary.md
    ⚠️  此看板参数必须用下划线风格(customer_id, ad_id, campaign_id, tag_id, sale_industry 等),非 camelCase
    group_by: app_id, customer_id, campaign_id, ad_id, tag_id, media_type, sale_industry, dt 等; 支持数组多维交叉,如 ["media_type","tag_id"]
    measures: fee_total, fee_effect, fee_dsp_rtb, view, click, ctr, ecpm, target_conv_num_z, target_conv_cost_z 等
    extend_fields: app_name, tag_name, campaign_name, ad_name 等

  query_bi_realtime            ⑧ [已废弃] 曝光后链路总览
    ⛔ 已被 query_xirang_ad_effect 替代，禁止主动调用。
       仅当 query_xirang_ad_effect 完全不可用且用户明确确认后才可降级使用。
    作用:总览曝光后链路并按维度下钻
    字典:references/bi_realtime_field_dictionary.md
    group_by: adId, campaignId, tagId, sourceName, mediaType 等
    measures: fee, totalFee, view, click, targetConvNum 等
    default_measures: view, click, startDownload, fee, targetConvNum
    账户过滤参数: customerId(如 {"customerId":"1357652",...})

示例

  # 执行查询
  bash scripts/query/dashboard_query.sh \\
    --dashboard query_xirang_delivery_diagnosis \\
    --params '{"time":{"hours":8,"compare":true},"filters":{"ad_id":"415796252"},"split":{"group_by":"processorName"}}' \\
    --session-id <id>

See also
  创建会话请用            scripts/session/create_session.sh --help
  会话门控请用            scripts/session/session_gate.sh --help
  过滤码查询请用          scripts/query/filter_rule_query.sh --help
  报告保存请用            scripts/report/save_report.sh --help
""".strip()


def _load_params(params_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(params_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid params json: {exc}")
    if not isinstance(parsed, dict):
        raise SystemExit("params must be a JSON object")
    return parsed


def _load_cookies_b64() -> str:
    """Read cookies from the default state file and return a base64 string.

    Kept inside the query runner because only dashboard queries need cookies
    (see spec ``cookies_b64 唯一注入通道``). Session and report runners MUST NOT
    carry cookies.
    """
    default_cookie_file = SKILL_ROOT / "state" / ".cookies.json"
    if not default_cookie_file.exists():
        raise SystemExit(
            "missing cookies: ensure state/.cookies.json exists before querying dashboards"
        )

    raw_json = default_cookie_file.read_text(encoding="utf-8")

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid cookies json: {exc}")
    if not isinstance(parsed, dict):
        raise SystemExit("cookies json must be a JSON object")

    return base64.b64encode(
        json.dumps(parsed, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")


def main() -> int:
    # --help-dashboards and -h/--help short-circuit before argparse so the
    # custom text is the only thing printed.
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(_dashboard_help_text())
        return 0
    if "--help-dashboards" in sys.argv[1:]:
        print(_dashboard_help_text())
        return 0

    parser = argparse.ArgumentParser(
        description="Dashboard query runner for rollie-diagnose server.",
        add_help=False,
    )
    parser.add_argument("--dashboard")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--session-id")
    parser.add_argument("--help-dashboards", action="store_true")
    args = parser.parse_args()

    if not args.dashboard:
        raise SystemExit("--dashboard is required (use --help-dashboards for available dashboards)")

    payload = {
        "dashboard": args.dashboard,
        "params": _load_params(args.params),
        "session_id": args.session_id,
        "cookies_b64": _load_cookies_b64(),
    }

    base_url = resolve_base_url()
    url = build_url(base_url, QUERY_PATH)
    identifier = safe_identifier(args.session_id, args.dashboard, QUERY_PATH)

    return execute_and_emit(
        url=url,
        method=QUERY_METHOD,
        payload=payload,
        identifier=identifier,
    )


if __name__ == "__main__":
    raise SystemExit(main())
