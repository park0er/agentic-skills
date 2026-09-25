# DevX PostgreSQL 实测矩阵

日期：2026-09-09。入口：小米云 DevX / 数据库 / PostgreSQL / SQL 工单。引擎只读查询显示 PostgreSQL 14.8。下列为审核器反馈，**不是实际执行成功记录**。同平台润色直接复用，不要求逐次重测；不把结论外推到其他数据库产品。

| 语法 | 审核观测 | 应对 |
| --- | --- | --- |
| BEGIN、ROLLBACK | 拒绝：PG DDL 审核仅支持 DDL 语句，当前语句不是可执行 DDL | 不能直接去掉事务保证 |
| SET LOCAL lock_timeout / statement_timeout | 无法解析：at or near 参数名，syntax error: unimplemented: this syntax | 引擎支持不代表审核器支持 |
| DO $$ ... $$ | 无法解析：at or near "do": syntax error | 不能直接移除断言 |
| UPDATE / DELETE，带 UUID 强制类型和 AND FALSE 探针 | 通过：DML/查询语句无需 DDL 改写，按原样执行 | 仅证明探针审核通过，实际范围另验 |
| UNIQUE INDEX (lower(btrim(email))) | 拒绝：at or near ")": syntax error: unimplemented: this syntax | 有/无 CONCURRENTLY、有/无额外括号均失败 |
| UNIQUE INDEX (lower(email)) / (lower(trim(email))) | 同上 | 不再只调整括号；检查替代设计的语义 |
| CREATE UNIQUE INDEX ... ON ... (email) | 通过：已改写为 CREATE INDEX CONCURRENTLY，避免阻塞 DML | 不能假定整张工单原子执行 |
| CREATE UNIQUE INDEX CONCURRENTLY ... (email) | 通过：不阻塞 DML，注入 lock_timeout 后执行 | 重复数据会使建立失败；错误后查无效索引 |
| ADD CONSTRAINT ... CHECK (email = lower(btrim(email))) NOT VALID | 通过：已是安全两步法第一步，注入 lock_timeout 后执行 | 还需验 VALIDATE 支持和最终 convalidated |

## 当时的探针记录（无需重做）

以下是历史审核使用的脱敏示例，不是使用技能的操作步骤。AND FALSE 语句不是生产迁移。

```sql
UPDATE public.example_user SET email = email
WHERE id = '00000000-0000-0000-0000-000000000000'::uuid AND FALSE;
CREATE UNIQUE INDEX CONCURRENTLY example_email_uq ON public.example_user (email);
```

## 扩充记录

每个案例记录时间、平台入口、引擎版本、脱敏原句、原始错误、改写句、语义差异、审核状态、演练状态和执行状态。未执行写“未执行”，不从审核建议推断运行成功。

未知项包括数据修改 CTE、VALIDATE CONSTRAINT、备份/恢复语句及多语句失败边界。当前润色将它们标为未覆盖即可，不要求为完成润色而上页面实验；以后实际遇到新结果再补充。
