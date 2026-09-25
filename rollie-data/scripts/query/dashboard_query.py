#!/usr/bin/env python3
"""Dashboard query runner for rollie-data skill.

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
from auth.paths import COOKIE_FILE as COOKIES_FILE  # noqa: E402

__version__ = SKILL_VERSION

QUERY_PATH = "/api/v1/query/dashboard"
QUERY_METHOD = "POST"


def _dashboard_help_text() -> str:
    return """
用法:dashboard_query.py --dashboard <query_name> --params '<json>' [选项]

⚠️  传参前必须先读本地字典文件确认字段,不要猜(本help约100行,全部读完不要截断)。
    字典文件位于:references/ (相对 skill 根目录)

--dashboard  执行查询

  --dashboard <query_name> --params '<json>' [--session-id <id>]

  通用 params 结构(四子对象,均可省略):
    {
      "time": {
        "start_time": "2026-03-21T00:00:00+08:00",   // 必须 +08:00 格式
        "end_time":   "2026-03-21T08:00:00+08:00",   // 与 hours 二选一
        "hours": 24,                                  // 相对时间窗口,默认 24
        "compare": true,                              // 是否带同环比,涉及日期同环比时为true,当为true时一定需要填写"comparison_start_time"和"comparison_end_time";没有同环比时为false,当为false时只需要填写"start_time"和"end_time"
        "comparison_start_time": "...",               // 自定义对比期起始时间(+08:00)
        "comparison_end_time":   "..."                // 自定义对比期结束时间(+08:00)
      },
      "filters": {                                    // 过滤维度,唯一路径
        "customer_id": "1357652",                     // 单值等值
        "tag_id": ["101", "102"]                      // 多值 IN 查询
      },
      "split": {
        "group_by": "ad_id",                          // 下钻维度,也可传数组 ["media_type","tag_id"] 表达多维交叉(笛卡尔组合,top 指总行数上限)
        "top": 50,                                    // 返回条数,默认 50
        "sort_by": "fee_effect"                       // 排序指标,默认 measures[0]
      },
      "measures": ["fee_effect", "view", "click"]     // 指标列表,省略或空数组时由服务端按各看板 default_measures 兜底(不传则用看板默认指标,无需本地补值)
                                                     // ⚠️ 例外:query_pivot_birealtime_v3_ext 不适用该兜底,必须显式传 measures
    }


  可查询看板(详细字段含义见对应字典文件):

  query_xirang_ad_effect       ① 曝光后链路(息壤)
    作用:广告效果数据总览。查看曝光/点击/消耗/转化,按广告/计划/广告位/媒体/应用/行业等多维度下钻,支持时间趋势。最常用的查数入口。
    字典:references/xirang_ad_effect_field_dictionary.md
        references/xirang_ad_effect_field_dictionary_low_freq.md (高频字典找不到时翻低频)
    group_by: app_id, customer_id, campaign_id, ad_id, tag_id, media_type, sale_industry, dt 等(可单传字符串,也可传数组多维交叉,如 ["media_type","tag_id"])
    measures: fee_total, fee_effect, fee_dsp_rtb, view, click, ctr, ecpm, target_conv_num_z, target_conv_cost_z 等
    extend_fields: app_name, tag_name, campaign_name, ad_name 等

  query_request_info           ② 媒体请求
    作用:上游流量入口是否正常,判断掉量是否源于媒体侧请求减少。
    字典:references/request_info_field_dictionary.md
    group_by: tagId, mediaType
    measures: count, eRawQuery, eQuery, eFill

  query_emi_diagnosis          ③ 广告下发
    作用:广告是否被拉黑、下发链路是否受预算或控制评分压制。不支持 tagId 过滤和搜索词维度。
    字典:references/emi_diagnosis_field_dictionary.md
    group_by: campaignId, adId
    measures: count, delivery, budgetDelivery, controlScore

  query_xirang_delivery_diagnosis  ④ 召回+业务过滤(息壤)
    作用:定位哪个 index_ad_lifecycle 环节过滤了广告。通过量看 resultAd,过滤量看其他 lifecycle。
    字典:references/xirang_delivery_diagnosis_field_dictionary.md
    group_by: index_ad_lifecycle, campaign_id, ad_id, tag_id, media_type
    measures: index_filter_count

  query_xirang_adx_diagnosis  ADX竞价链路(息壤)
    作用:外部 DSP 填充→参竞→竞胜→下发漏斗,了解填充率、竞胜率及过滤原因。
    字典:references/xirang_adx_diagnosis_field_dictionary.md
    group_by: dt, media_type, tag_id, physical_dsp, deal_id, adx_status, adx_reason
    measures: adx_request, adx_fill, adx_win, adx_fill_rate, adx_win_rate, adx_media_request

  query_xirang_recall_diagnosis  召回链路多维分析(息壤)
    作用:按流量/应用/客户/引擎链路维度下钻,排查召回过滤原因。
    字典:references/xirang_recall_diagnosis_field_dictionary.md
    group_by: dt, media_type, tag_id, recall_pipeline, recall_ad_lifecycle, passMerge, ad_id, campaign_id
    measures: recall_filter_count

  query_xirang_pre_ranking      ⑤ 粗排(息壤)
    作用:排查粗排阶段请求量变化与 pscore 分布,按过滤原因/召回通道/是否丢弃下钻。
    字典:references/xirang_pre_ranking_field_dictionary.md
    group_by: media_type, tag_id, recall_expid, recall_channel_name, recall_filter_reason, is_discard, ad_id, campaign_id
    measures: count, sum_pscore_recall, avg_pscore_recall

  query_xirang_fine_ranking      ⑥ 精排(息壤)
    作用:排查精排阶段请求量变化与模型打分分布(pctr/pcvr/pltv),按过滤原因/广告来源/召回通道下钻。
    字典:references/xirang_fine_ranking_field_dictionary.md
    group_by: media_type, tag_id, ad_id, campaign_id, filter_reason, rank_adsource, recall_channel_name
    measures: count, avg_pctr_rank, avg_pcvr_rank, avg_pdeepcvr_rank, avg_pltv_rank

  query_xirang_strategy_service  策略服务看板(息壤正式环境)
    作用:排查策略服务阶段收入、补贴、出价、pPrice/pPriceRatio 等指标
    字典:references/xirang_strategy_service_field_dictionary.md
    group_by: dt, tag_id, media_type, campaign_id, ad_id, customer_id, sfilter_reason, fixed_price_source
    measures: count, avg_p_price_strategy, avg_p_priceratio_strategy, avg_targetcpa_strategy, avg_risk_bid_strategy

  query_xirang_media_analysis  媒体多维分析(息壤)
    作用:按媒体/广告位/DSP/联盟应用与开发者/设备维度查看请求、填充、曝光、点击、收入和转化。
    字典:references/xirang_media_analysis_field_dictionary.md
    group_by: dt, media_type, tag_id, ad_form_id, dsp_level1, dsp_level2, ua_id, up_id, union_developer_id, device_type
    measures: query, valid_query, delivery, view, click, fee_effect, ecpm, target_conv_num_z

  query_xirang_rta_diagnosis  RTA多维分析(息壤)
    作用:排查 RTA 请求量、通过率、超时、缓存命中、出价系数。一般搭配 client_name 或 token_name 使用。
    字典:references/xirang_rta_diagnosis_field_dictionary.md
    group_by: dt, media_type, tag_id, rta_host, client_name, ret_code, req_type
    measures: de_rta_req_token, de_rta_ac_rate_token, rta_cus_req_client, rta_cus_timeout_rate_client

  query_xirang_budget_analysis  预算分析(息壤)
    作用:排查预算消耗、达限状态,按应用/账户/行业/区域/代理维度分析。split.group_by 为 application/customer/campaign 三选一 bucket(非普通 group_by)。
    字典:references/xirang_budget_analysis_field_dictionary.md
    filters: app_id, campaign_id, customer_id, industry_level1, industry_level2,
             effect_region, agent_id, core_id
    split.stat_type: "total"(合计) / "daily_avg"(日均),默认 total
    split.group_by: application/customer/campaign,只返回该 bucket,精度不匹配报错
    reach_limit: 服务端默认 unlimited
    输出: application + customer 两张表

  query_pivot_search_term      搜索词粒度
    作用:xirang_ad_effect 最细只到广告位,本看板填补缺口——按搜索词查看请求/曝光/点击/消耗和预估指标。⚠️ 搜索词字段是 query,不是 keyword/search_query。
    字典:references/pivot_search_term_field_dictionary.md
    group_by: query, dsp, tagId, adId, campaignId, customerId, appId, mediaType
    measures: count, request, view, pctr, fee, feeRtb, totalfee, click, ctr, ecpm

  query_pivot_birealtime_v3_ext  BIrealtimev3ext 实验分析看板(算法侧)
    作用:算法侧排查实验数据——算实验组相对对照组在核心指标上的 diff、定位 pcoc 预估偏离、
         看内外部 DSP 与计费结构差异。
    ⚠️ 必须显式传 measures(不适用上面的 default_measures 兜底)
    ⚠️ 必须带且仅带一个 expLayerN,并且要同时放进 split.group_by;
       只放 filters 时各实验组会被合并成一行返回且不报错,diff 无从计算
    字典:references/pivot_birealtimev3ext_field_dictionary.md
    group_by: expLayer20~expLayer66(42 个实验层,注意是 expLayer20 不是 exp20)、mediaType, tagId,
              appId, adId, dspLevel1, dsp, billingType, targetConvType, GuyuFilterReason, __time/time
    measures: CTR 层(expLayer20/expLayer66) view, ecpm, totalFee, advv, ctr1, ctr_pcoc
              CVR 层(其余各层)              view, ecpm, totalFee, advv, cvr, cvr_pcoc, billingRatio

  ⛔ 已废弃看板(禁止主动调用;仅当对应息壤看板同参数重试1次仍无数据/超时/报错,且用户明确同意后,兜底重查一次。兜底请读该看板自己的词典,不要沿用息壤字段名):

  query_guyu_recall            → 用 query_xirang_pre_ranking 替代
  query_guyu_stat              → 用 query_xirang_fine_ranking 替代
  query_bi_realtime            → 用 query_xirang_ad_effect 替代
  query_ocpx_strategy          → 用 query_xirang_strategy_service 替代

示例

  # 执行查询(息壤效果看板)
  bash scripts/query/dashboard_query.sh \\
    --dashboard query_xirang_ad_effect \\
    --params '{"time":{"start_time":"2026-04-01T00:00:00+08:00","end_time":"2026-04-01T23:59:59+08:00","compare":false},"filters":{"customer_id":"1357652"},"split":{"group_by":"campaign_id","top":50,"sort_by":"fee_effect"},"measures":["fee_effect","view","click","ctr","target_conv_num_z"]}' \\
    --session-id <id>

  # 执行查询(谷雨粗排看板)
  bash scripts/query/dashboard_query.sh \\
    --dashboard query_xirang_pre_ranking \\
    --params '{"time":{"start_time":"2026-06-01T00:00:00+08:00","end_time":"2026-06-01T23:59:59+08:00","compare":false},"filters":{"ad_id":"415796252"},"split":{"group_by":"recall_filter_reason","top":30}}' \\
    --session-id <id>

See also
  创建会话请用            scripts/session/create_session.sh --help
  Cookie 校验请用         scripts/auth/check_cookies.sh --help
  过滤码查询请用          scripts/query/filter_rule_query.sh --help
  策略/操作查询请用       scripts/query/strategy_operation_query.sh --help
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
    """Read cookies from the shared Rollie auth file and return a base64 string.

    Kept inside the query runner because only dashboard queries need cookies
    (see spec ``cookies_b64 唯一注入通道``). Session and report runners MUST NOT
    carry cookies.
    """
    if not COOKIES_FILE.exists():
        raise SystemExit(
            "missing cookies: ensure ~/.rollie/auth/.cookies.json exists before querying dashboards"
        )

    raw_json = COOKIES_FILE.read_text(encoding="utf-8")

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
        description="Dashboard query runner for rollie-data skill.",
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
