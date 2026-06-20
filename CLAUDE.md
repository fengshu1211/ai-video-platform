# CLAUDE.md — AI短视频创作平台

> ⚡ **全局规则**：`d:\应用开发项目集\CLAUDE.md` 中的 Agent 自动触发规则、开发工作流程、红线对此项目同样有效。

## 用户：丰哥

- 自媒体历史类博主（历史方向），非专业程序员
- 说人话、分步来、少确认、结果导向
- 不要一次给太多信息，重点加粗，回复简短

## 技术栈

- 前端：React 19 + Vite 6 + TypeScript + Ant Design 5
- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + SQLite
- TTS：DashScope CosyVoice V2（主力）/ SiliconFlow CosyVoice（声音克隆）
- AI文本：通义千问 API（DashScope，OpenAI 兼容格式）
- 视频：FFmpeg（subprocess）
- 服务器：阿里云 ECS 47.109.78.122 (2核1.6G Ubuntu 22.04)
- 部署：nginx → 前端静态文件 + API 代理到 :8000
- 部署脚本：upload_dist.py（前端+验证）/ SFTP 直传（后端）

## 🔧 MCP 工具自动使用规则

项目已安装以下 MCP 工具，**根据工作内容自动调用，无需用户提醒**：

| MCP | 自动触发条件 |
| --- | --- |
| **Context7** | 需要查 React 19 / Ant Design 5 / FastAPI / Vite 等框架 API 时，自动 query-docs 获取最新文档，不凭记忆写代码 |
| **Playwright** | 排查前端 UI 问题、手机端兼容性、上传/渲染流程 Bug 时，自动启动浏览器模拟操作定位问题 |

## ⚡ 模型切换提醒

日常开发用 **Sonnet (Flash)** 或 **Haiku (Flash)**。遇到以下情况时，**主动提醒丰哥切换到 Opus (Pro)**：

| 触发条件 | 说明 |
| --- | --- |
| 跨 3+ 文件重构 | 多文件协同改动 |
| 复杂算法/业务逻辑 | 空间计算、多层递归、报价引擎 |
| 深度 Bug 排查 | 尝试 2 次仍未定位根因 |
| 方案设计阶段 | 需要对比多种实现路径 |

切换方式：Claude Code 里 `/model opus`，任务完成切回 `/model sonnet`。

## 启动命令

```bash
# 后端 (Windows本地)
cd backend && python -m uvicorn app.main:app --reload --port 8000
# 前端 (Windows本地)
cd frontend && npm run dev
# 部署前端到服务器
python upload_dist.py
# 部署后端到服务器（SFTP直传 + systemctl restart ai-video）
```

---

## 标准开发工作流程

**全局规则见 `d:\应用开发项目集\CLAUDE.md`**，这里只写本项目特有的。

## 启动命令

```bash
# 后端 (Windows本地)
cd backend && python -m uvicorn app.main:app --reload --port 8000
# 前端 (Windows本地)
cd frontend && npm run dev
# 部署前端到服务器
python upload_dist.py
# 部署后端到服务器（SFTP直传 + systemctl restart ai-video）
```

## Skill / Agent 调用规范（什么时候用什么）

### 编码阶段

| 场景 | 用什么 | 触发方式 |
|------|--------|----------|
| **开始写代码前**：摸清现有逻辑 | `Explore` agent | Agent tool, subagent_type="Explore" |
| **复杂功能**：需要设计方案 | `Plan` agent + `EnterPlanMode` | 先 EnterPlanMode，再 Agent |
| **拆任务**：跟踪进度 | `TodoWrite` | 直接调用 |
| **写完了**：确认代码正确 | `verify` skill | Skill tool, skill="verify" |
| **提交前**：自查代码质量 | `code-review` skill | Skill tool, skill="code-review" |
| **审查后**：应用修复建议 | `simplify` skill | Skill tool, skill="simplify" |

### 调试阶段

| 场景 | 用什么 | 触发方式 |
|------|--------|----------|
| **出 Bug**：系统性排查 | `systematic-debugging` skill | Skill tool, skill="systematic-debugging" |
| **查根因**：搜日志+读代码 | Grep + Bash (journalctl) | 直接调用 |
| **卡死任务**：清理重置 | `python clean_db.py` | SFTP 上传 + 执行 |
| **部署失败**：检查前后端 | curl API + nginx 日志 | 直接调用 |

### 部署阶段

| 场景 | 用什么 |
|------|--------|
| 部署前端到服务器 | `python upload_dist.py`（自带验证，必须看到 DEPLOY OK） |
| 部署后端到服务器 | SFTP 上传文件 + `systemctl restart ai-video` |
| 部署后验证 | `verify` skill + curl API 检查 |
| 快速部署后端（不改前端） | SFTP 直传改动的 .py 文件 |

### 注意事项

- **Explore agent**：只读不改，适合摸清代码。用 1-3 个 agent 并行探索
- **Plan agent**：输出方案不是代码，适合复杂任务。用户确认后才能实施
- **verify skill**：每次部署后必须跑，确认改动生效
- **code-review skill**：大改之前跑一遍，避免低级错误
- **systematic-debugging skill**：不要跳过直接改代码——先查日志、定位根因、再动手
