---
name: xirang_ad_effect_enum_dsp_level2
description: dsp_level2（二级DSP）字段枚举值 → 中文含义映射。按一级DSP（dsp_level1）分为内部DSP（effect）与外部DSP（dsp）两表。用于按 DSP 过滤字段时查码值：外部如"优量汇"、"穿山甲"，内部如 `xiaomi.ocpa`。
---

# 二级DSP标识映射表（dsp_level2）

> `dsp_level2`（二级DSP）挂在一级DSP（`dsp_level1`）之下。`dsp_level1` 取值：
> - `effect` = 内部DSP（小米自有投放体系）
> - `dsp` = 外部DSP（第三方RTB/联盟）
> - `brand` = 品牌（息壤效果看板 query_xirang_ad_effect 暂无数据）
>
> 外部DSP中文含义来源：https://feishu.cn/wiki/BhoswY3NTitaNXkUvZGco0Y4nxb

## 内部DSP（dsp_level1=effect）

| dsp_level2 |
|---|
| xiaomi.ocpa |
| xiaomi.finocpa |
| xiaomi.gameocpa |
| xiaomi.ecomocpa |
| xiaomi.evokeocpa-cvr |
| xiaomi.delivery |
| xiaomi.push |
| xiaomi.excpa |

## 外部DSP（dsp_level1=dsp）

| dsp_level2 | 中文含义 |
|---|---|
| tengxunrtb | 优量汇（腾讯RTB） |
| bytedance | 穿山甲（字节RTB） |
| baidurtb | 百青藤（百度RTB） |
| bytedanceUG | 字节UG |
| yyb | 应用宝 |
| kuaishoudsp | 快手联盟 |
| chaojihuichuan | 超级汇川 |
| jingdongapi | 京东联盟 |
| tanxseat | 阿里妈妈（tanx） |
| YOYO | ？ |
| iqiyi | 爱奇艺 |
| pinduoduo | 拼多多 |
| xingchen | 星辰 |
| wangmairtb | 旺脉RTB |
| vlion | 汇量 |
| Feisuo | ？ |
| jiatou | ？ |
| AdMate | AdMate |
| Duomeng | 多盟 |
| adprof | AdProf |
| wisemedia | ？ |
| fancy | ？ |
