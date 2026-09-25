#!/usr/bin/env python3
"""
format_cross_table.py — 将 xirang_ad_effect 查询结果转为交叉表

用法:
  python3 format_cross_table.py <json_file> --row <row_dim> --col <col_dim> --measures <m1,m2,...> [--sort-by <measure>] [--unit <yuan|wan>]

参数:
  json_file    原始查询结果 JSON 文件路径（包含 result.current 数组）
  --row        行维度字段名（如 app_id, tag_id, media_type）
  --col        列维度字段名（如 dt）
  --measures   指标字段名，逗号分隔（如 fee_effect,fee_dsp_rtb,total_fee_effect）
  --sort-by    排序指标（默认第一个 measure）
  --desc       降序排列（默认）
  --asc        升序排列
  --unit       yuan=元（默认）, wan=万元
  --row-name   行维度中文名映射文件（可选，格式: dimValue<tab>中文名）
  --add-total  添加行合计
  --add-avg    添加行日均（仅当 col=dt 且天数>1 时有意义）
  --pct        指标显示为百分比（值已为百分比格式，如 CTR=75.12 表示 75.12%）
"""

import json
import sys
import argparse
from collections import defaultdict


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 兼容多种包装结构
    if isinstance(data, dict):
        if 'body' in data and isinstance(data['body'], dict):
            data = data['body']
        if 'result' in data and isinstance(data['result'], dict):
            data = data['result']
        if 'current' in data and isinstance(data['current'], list):
            return data['current']
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected JSON structure: {type(data)}, keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")


def load_name_mapping(path):
    """加载 dimValue -> 中文名 映射"""
    mapping = {}
    if not path:
        return mapping
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                mapping[parts[0].strip()] = parts[1].strip()
    return mapping


def format_number(val, unit='yuan', is_pct=False):
    """格式化数值"""
    if val is None or val == '' or val == '-':
        return '-'
    try:
        v = float(val)
    except (ValueError, TypeError):
        return str(val)
    if is_pct:
        return f"{v:.2f}%"
    if unit == 'wan':
        v = v / 10000
        return f"{v:,.2f}"
    return f"{v:,.2f}"


def main():
    parser = argparse.ArgumentParser(description='将查询结果转为交叉表')
    parser.add_argument('json_file', help='原始查询结果 JSON 文件')
    parser.add_argument('--row', required=True, help='行维度字段名')
    parser.add_argument('--col', required=True, help='列维度字段名')
    parser.add_argument('--measures', required=True, help='指标字段名，逗号分隔')
    parser.add_argument('--sort-by', default=None, help='排序指标')
    parser.add_argument('--asc', action='store_true', help='升序排列')
    parser.add_argument('--unit', default='yuan', choices=['yuan', 'wan'], help='数值单位')
    parser.add_argument('--row-name', default=None, help='行维度中文名映射文件')
    parser.add_argument('--add-total', action='store_true', help='添加行合计')
    parser.add_argument('--add-avg', action='store_true', help='添加行日均')
    parser.add_argument('--pct', action='store_true', help='指标为百分比格式')

    args = parser.parse_args()

    records = load_json(args.json_file)
    measures = [m.strip() for m in args.measures.split(',')]
    row_dim = args.row
    col_dim = args.col
    sort_by = args.sort_by or measures[0]
    name_map = load_name_mapping(args.row_name)

    # 聚合: {row_val: {col_val: {measure: value}}}
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    col_values = set()

    for rec in records:
        rv = str(rec.get(row_dim, ''))
        cv = str(rec.get(col_dim, ''))
        col_values.add(cv)
        for m in measures:
            try:
                data[rv][cv][m] += float(rec.get(m, 0))
            except (ValueError, TypeError):
                pass

    col_values = sorted(col_values)

    # 按 sort_by 的合计排序行
    def row_sort_key(rv):
        total = sum(data[rv].get(cv, {}).get(sort_by, 0) for cv in col_values)
        return total

    row_values = sorted(data.keys(), key=row_sort_key, reverse=not args.asc)

    # 表头
    row_label = name_map.get(row_dim, row_dim)
    col_labels = col_values

    # 构建输出
    lines = []

    # 表头行
    header_parts = [f"| {row_label} "]
    for cv in col_labels:
        for m in measures:
            header_parts.append(f"| {cv}_{m} ")
    if args.add_total:
        for m in measures:
            header_parts.append(f"| 合计_{m} ")
    if args.add_avg:
        for m in measures:
            header_parts.append(f"| 日均_{m} ")
    header_parts.append("|")
    lines.append(''.join(header_parts))

    # 分隔线
    sep_parts = ["|---"]
    for _ in col_labels:
        for _ in measures:
            sep_parts.append("|---")
    if args.add_total:
        sep_parts.extend(["---"] * len(measures))
    if args.add_avg:
        sep_parts.extend(["---"] * len(measures))
    sep_parts.append("|")
    lines.append(''.join(sep_parts))

    # 数据行
    for rv in row_values:
        display_name = name_map.get(rv, rv)
        row_parts = [f"| {display_name} "]

        # 各列值
        for cv in col_labels:
            for m in measures:
                val = data[rv].get(cv, {}).get(m, None)
                row_parts.append(f"| {format_number(val, args.unit, args.pct)} ")

        # 合计
        if args.add_total:
            for m in measures:
                total = sum(data[rv].get(cv, {}).get(m, 0) for cv in col_values)
                row_parts.append(f"| {format_number(total, args.unit, args.pct)} ")

        # 日均
        if args.add_avg:
            n_days = len(col_values)
            for m in measures:
                total = sum(data[rv].get(cv, {}).get(m, 0) for cv in col_values)
                avg = total / n_days if n_days > 0 else 0
                row_parts.append(f"| {format_number(avg, args.unit, args.pct)} ")

        row_parts.append("|")
        lines.append(''.join(row_parts))

    # 输出
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
