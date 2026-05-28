# CLAUDE.md — AI短视频创作平台

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

# 标准开发工作流程（强制遵守）

## 阶段一：需求理解（先想清楚）

1. **理解用户真正要什么**，不是他说什么就改什么
2. 如果需求模糊，用 `AskUserQuestion` 问清楚（选项式，不要开放式提问）
3. 如果是复杂功能，**必须进入 Plan Mode**（`EnterPlanMode`）
4. 用 `Explore` agent 快速摸清代码现状（不改代码，只读）

## 阶段二：方案设计（Plan Mode）

1. 启动 `Plan` agent 设计实现方案
2. 写清楚：改哪些文件、改什么、为什么这样改
3. 方案写完后 `ExitPlanMode` 让用户确认
4. 用户确认后才能动手

**触发 Plan Mode 的条件：**
- 涉及 3 个以上文件
- 新功能或架构改动
- 有多种实现方案可选

## 阶段三：编码实施

1. 用 `TodoWrite` 建任务列表，拆成小步骤
2. **一次只做一个步骤**，做完标记 completed
3. 每个步骤：读懂现有代码 → 精确改动 → 本地语法检查 → 确认
4. 前端改动后 `npm run build`，后端改动后 Python 语法检查
5. **不在一次提交里混多个无关改动**

## 阶段四：验证测试

1. **先本地跑通**：本地启动前后端，curl 或 Python 测试关键 API
2. **再部署服务器**：upload_dist.py（前端）/ SFTP（后端）
3. **部署后必须看到 DEPLOY OK**（upload_dist.py 末尾）
4. **用 requests 模拟一次完整调用链路**（创建→上传→生成）
5. 检查服务器日志无异常（journalctl）

## 阶段五：交付

1. 确认所有验证通过
2. git commit + push
3. 告诉用户：改了什么、怎么测试

---

## 🔍 技能/插件持续优化原则

**每半个月自动搜索一次好用的 skill/plugin**（已设定定时任务，每月 1 号和 15 号执行），评估后安装或替换。

**遇到项目瓶颈时，优先从 skill/插件层面找解决方案**：
- 搜索是否有针对性的 skill 或 MCP 工具
- 对比评估：功能、评分、和现有方案优劣
- 更好的就替换，互补的就追加
- 不盲目造轮子——剪映、CapCut MCP、whisper 这些现成方案优先于手写 FFmpeg 滤镜

**对用户的报告义务**：发现好用的 skill/plugin，主动告知功能、优势、安装情况。

---

## ⚠️ 红线（违反一条就浪费用户时间）

1. **部署完不验证** → 禁止
2. **改完不测试就叫用户试** → 禁止
3. **出错不查日志直接改代码** → 禁止
4. **一次改多个文件不提交不验证** → 禁止
5. **React 组件里用 hooks 嵌套在普通函数里** → 禁止（会报错）
6. **遇到瓶颈闷头硬写不搜现成方案** → 禁止

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
