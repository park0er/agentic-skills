---
name: xiaomi-postgres-workorder
description: "按已实测规则离线润色小米云 DevX PostgreSQL 工单和迁移 SQL：避开 BEGIN/ROLLBACK、SET LOCAL、DO 和已知不支持的表达式索引；使用普通列并发索引及 CHECK NOT VALID 等已过审写法。用于公司 PostgreSQL 脚本适配、工单语法报错和迁移预处理。直接输出改写 SQL 与必要的语义差异，不要求浏览器、数据库连接或重新做已知语法实验。"
---

# 小米 PostgreSQL SQL 改写规则

拿到 SQL 后，直接按以下规则离线改写。**已知坑不要再去页面重测；不需要浏览器或数据库连接才能完成润色。** 规则来自 2026-09-09 小米云 DevX SQL 工单实测（后端 PostgreSQL 14.8），描述的是平台审核兼容性，不是 PostgreSQL 引擎语法能力。

## 1. 普通列索引：显式写 CONCURRENTLY

输入：

```sql
CREATE UNIQUE INDEX user_email_uq ON public."user" (email);
```

输出：

```sql
CREATE UNIQUE INDEX CONCURRENTLY user_email_uq ON public."user" (email);
```

两种形式均已过审；平台会把前者改成后者。直接输出后者，让源脚本与平台执行方式一致。不要包在 BEGIN/COMMIT 中，也不要为凑事务去掉 CONCURRENTLY。

## 2. 邮箱表达式索引：不要再调括号，按条件换 CHECK + 普通列索引

以下写法均已被审核器拒绝：

```sql
CREATE UNIQUE INDEX CONCURRENTLY user_email_uq ON public."user" ((lower(btrim(email))));
CREATE UNIQUE INDEX CONCURRENTLY user_email_uq ON public."user" (lower(btrim(email)));
CREATE UNIQUE INDEX user_email_uq ON public."user" (lower(btrim(email)));
CREATE UNIQUE INDEX user_email_uq ON public."user" (lower(email));
CREATE UNIQUE INDEX user_email_uq ON public."user" (lower(trim(email)));
```

不要再尝试增减括号、删除 CONCURRENTLY 或把 btrim 换 trim。对于“邮箱按小写、去首尾普通空格后唯一”的需求，若存量邮箱已规范化，且写入方先规范化，可改成以下**已过审**组合：

```sql
ALTER TABLE public."user"
  ADD CONSTRAINT user_email_canonical_check
  CHECK (email = lower(btrim(email))) NOT VALID;

CREATE UNIQUE INDEX CONCURRENTLY user_email_uq
  ON public."user" (email);
```

直接给出这份条件式改写，不要求先连接数据库才能生成。随脚本列出执行前置条件：现有重复邮箱已处理、现有邮箱已规范化、写入方遵守同一规范。

必须说明一个差异：表达式索引允许保存非规范原值；这个组合会**拒绝**新的非规范值，不会自动修正。若必须保留原值，不能用此替代。不要把所有表达式索引都套用邮箱方案，也不要只换 UNIQUE(email) 而漏掉 CHECK。

NOT VALID 不校验历史行，但会约束后续 INSERT/UPDATE。历史全量验证的标准后续语句是：

```sql
ALTER TABLE public."user" VALIDATE CONSTRAINT user_email_canonical_check;
```

该后续语句尚未做平台审核实测，单独标为“平台兼容性未覆盖”，不把它混称为已过审。NULL 是否允许沿用原表约束；本组合不新增 NOT NULL。

## 3. CHECK：采用 NOT VALID 形式

已确认可过审的具体写法就是上一节的 `CHECK (email = lower(btrim(email))) NOT VALID`。平台识别它为安全两步法第一步，并提示注入 lock_timeout。

处理同类 CHECK 时优先输出 `ADD CONSTRAINT ... CHECK (...) NOT VALID`，将历史验证列为后续步骤。其他 CHECK 表达式没有逐一实测，不承诺所有函数都被解析器支持。不要悄悄省略历史验证的责任。

## 4. SET LOCAL 超时：不放入工单 SQL

这两句已确认被审核器拒绝：

```sql
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
```

如果它们只是独立 DDL 的执行环境设置，将其从工单 SQL 正文移到执行说明：上述已过审索引和 CHECK 路径由平台注入 lock_timeout。**平台具体值未知，也没有证据证明会注入 statement_timeout**，不要写成保留了原来的 5s/30s。

若业务要求这两个精确超时值，标为“需要执行器配置，不能仅靠已知 SQL 改写满足”；不要换一组未经验证的 SET 拼写继续猜。

## 5. BEGIN / ROLLBACK / DO：直接识别为不兼容，不盲删保证

BEGIN、ROLLBACK 已被拒绝为非可执行 DDL；DO $$ ... $$ 被拒绝为语法错误。不要生成这种工单包装：

```sql
BEGIN;
DO $$ BEGIN IF EXISTS (...) THEN RAISE EXCEPTION '...'; END IF; END $$;
-- DML or DDL
COMMIT;
```

- 独立并发建索引：去掉事务包装，按规则 1 输出独立语句，并标明它不属于原子事务。
- 多步 DML 依赖全成全败，或 DO 内含断言/循环：不能给出已证实等价的通用替换。保留这部分原文为“待改造片段”，先完成其他规则能处理的部分；不要要求重测已知拒绝的语法。
- COMMIT 未单独实测，不虚构报错，但不能把原本事务拆得只剩 COMMIT。
- 不把未测的数据修改 CTE 宣称为平台支持的事务替代方案。

## 6. 普通 UPDATE / DELETE：原样保留，不套过程块

以下结构已过审，平台反馈“DML/查询语句无需 DDL 改写，按原样执行”：

```sql
UPDATE public."user" SET email = email
WHERE id = '00000000-0000-0000-0000-000000000000'::uuid AND FALSE;

DELETE FROM public."user"
WHERE id = '00000000-0000-0000-0000-000000000000'::uuid AND FALSE;
```

这是当时用于零影响审核的例子，不是让未来使用者再做探针。规则是：保留普通 DML、schema 限定、双引号标识符、UUID `::uuid` 强制类型与原 WHERE 条件；不要无故套 DO。不要给业务脚本自动加 AND FALSE，也不要自动删去原文的 AND FALSE。

## 输出方式

1. 输出按上述规则改写的 SQL；无需先开页面、查询生产或做实验。
2. 只列实际发生的改写、执行前置条件和无法等价改写的片段。已知规则直接应用，未覆盖语法标“未覆盖”，不要因为规则不全而拒绝整份润色。
3. 区分“按已知兼容规则改写”与“这份工单已审核/已执行”。仅润色不自动提交或执行；用户另外要求提交时才进入平台流程，正常提交审核不是重复研究语法的前置任务。

原始报错与证据见 [实测记录](references/compatibility.md)，只在追溯报错或补充新经验时读取。
