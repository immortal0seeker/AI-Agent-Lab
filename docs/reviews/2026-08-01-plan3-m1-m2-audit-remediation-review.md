# Plan 3 M1/M2 Audit Remediation Review

## Scope And Baseline

本次只审核并修复已提交的 Plan 3 M1/M2。开始时 `main`、`HEAD` 与
`origin/main` 均为 `c9cefc498a746ad39ee47f5726afc959e8db4f9c`，工作区和
暂存区为空；`v0.2.0`、`v0.2.1` peeled targets 保持不变。未开始 M3、
Embedding、Qdrant client/collection、Retriever、RAG API、前端 RAG 或 Plan 4+
能力，也未读取或修改 `backend/ai_agent_lab.db`。

## Acceptance Matrix

| 审核项 | 原缺口 | 修复契约 | 状态 |
|---|---|---|---|
| Qdrant 暴露 | Compose 绑定所有接口 | 只绑定 `127.0.0.1:6333` | implemented |
| 存储路径 | root 提前解引用，Windows 分隔符/大小写可非规范化 | 保留 root 链接证据并要求严格 canonical path | implemented |
| 文档资源 | parser/chunker 可被页数、字符、结构、chunk 数放大 | 一个不可变 limits 契约贯穿 Settings、parser、chunker、service | implemented |
| Markdown metadata | 代码正文重复保存，cleaner 破坏 fence 内空行和行号 | 只存结构定位，fence-aware 清洗并重映射 | implemented |
| KB 删除 | ORM/DB 级联但本地文件不协调 | 非空返回安全 409，DB RESTRICT，数据/文件不变 | implemented |
| Document 去重 | 只有查询式预检 | 同 KB hash 唯一约束和安全 race 规范化 | implemented |
| RagQuery answer | ORM 删除可清空，raw SQL 被复合 FK 阻止 | 单列 SET NULL + 复合 NO ACTION | implemented |
| 活动文档 | Batch 6 与验收清单陈旧 | 同步真实 M1/M2 完成事实 | implemented |

## Confirmed Findings And Fixes

- 新增安全固定文案 `Document exceeds the processing limit.`，资源超限不会包含
  文件名、路径、正文、hash 或底层诊断，也不会持久化部分 chunks。
- 默认限制为 PDF 500 页、10,000,000 提取字符、20,000 Markdown 结构和
  10,000 chunks；配置上界分别为 10,000、100,000,000、100,000、100,000。
- Alembic head 演进到 `20260801_0006`；迁移先统计重复组，发现历史重复时只报告
  组数并要求人工复核，不自动删除、合并或暴露行内容。
- `knowledge_base_not_empty` 返回 HTTP 409 和固定安全消息；Document hash 唯一
  竞争继续使用既有 `document_duplicate` 409 契约。

## TDD Evidence

Task 1～6 均先运行行为级 RED，再做最小 GREEN。最终逐任务 GREEN 证据包括：

- 配置/Qdrant：`34 passed`；
- Settings/Storage：`68 passed`；
- Parser/Cleaner：`27 passed`；
- 配置/Chunker/Ingestion/Document API：`91 passed, 1 warning`；
- ORM/Migration：`33 passed`；
- KB/Document Service/API/Error：`58 passed, 1 warning`。

warning 均为既知 Starlette `TestClient` / httpx 弃用提示。

## Full Verification Evidence

- 聚焦 backend：`208 passed, 1 warning`。
- 完整 backend：`735 passed, 1 warning`。
- `pip check`：`No broken requirements found.`。
- 临时 SQLite Alembic：`upgrade head`、`current --check-heads`、
  `alembic check`、downgrade `20260726_0005`、再次 upgrade head 全部通过；
  head 为 `20260801_0006`，临时目录校验后删除。
- frontend：typecheck 通过，`18 files / 90 tests`，production build
  `1813 modules`。
- Compose：`docker compose config --quiet` 返回 0；`docker compose ps` 因本机
  daemon pipe 不存在且 Docker config 无访问权限而返回 1，因此本次 runtime
  health 为 `not_checked`，未访问 `/healthz`。历史 2026-07-26 health 证据不变。
- 文档：`95` 个 Markdown、`69` 个本地链接/图片、`0 missing`。
- 安全/边界：高置信 token `0`，12 个私钥头部均为 denylist/合成夹具/历史
  实施文档，unexpected `0`；`web_fetch` runtime `0`；tracked artifacts `0`。
- later-Plan 名称 6 个：1 个是明确不支持 OCR 的负面限制，5 个是前端测试辅助
  函数 `createMemoryStorage`，均非 later-Plan runtime。
- final Git gate：`git diff --check` 通过，staged paths `0`，状态共 `46`
  个预期路径（41 modified、5 untracked），无 untracked trailing whitespace；
  `HEAD == origin/main == c9cefc498a746ad39ee47f5726afc959e8db4f9c`，既有
  `v0.2.0` / `v0.2.1` peeled targets 未改变。

## Security And Plan-Boundary Checks

最终本地扫描已运行。实现范围未新增 Provider、网络 Tool、Embedding、Vector
Store、Retriever、RAG answer、前端 RAG、OCR、Advanced RAG、Rerank、Evaluation、
Memory、multimodal、MCP 或 Human Approval runtime。未读取、迁移、删除或重建
`backend/ai_agent_lab.db`。

## Codex Self-Review

### Must fix

已修复并复验：

- 原路径参数测试会因文件不存在产生伪通过；改为先创建真实受控文件，并补含
  字母 UUID 和 Windows `KB/nested\doc` 场景。
- Markdown 畸形布尔行号可能因 `bool` 是 `int` 子类而被改写；增加类型敏感 RED
  后改为严格 `type(...) is int`。
- 同步旧的 Batch 6、级联删除、migration head、Qdrant 绑定和 processing metadata
  文档事实。

无剩余 must-fix。

### Later Step

- M3：Embedding Provider、Qdrant Vector Store 与向量入库。
- 后续 Plan 3：Document 查询/删除、文件生命周期协调、Retriever、Naive RAG API
  与前端。

### Accepted limitation

- 文档处理仍同步占用上传请求；未引入 worker/background architecture。
- 特权进程在校验与文件访问之间的完整 TOCTOU 防御不在当前本地单用户边界内。
- hard-crash 可能留下历史孤儿文件；本批不扫描或删除它们。
- 扫描 PDF 不做 OCR；token 数仍是确定性估算。
- 本次 Docker daemon 不可访问，所以只有 Compose 静态配置证据，没有新的 runtime
  health；保留 2026-07-26 的历史本机 health 记录。
- 既知 Starlette `TestClient` / httpx 弃用 warning 保留。

### Not applicable

- PostgreSQL 迁移、前端截图、真实/付费 Provider、真实网络 Tool 和外部 review。

## Readiness Conclusion

M1/M2 审核修复已实现并通过全量验证；Codex self-review 无剩余 must-fix。
在用户手动提交本批后，可进入 `P3-M3-S1～S3`。该结论不表示 M3 已开始。
