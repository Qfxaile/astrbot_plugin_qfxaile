# astrbot_plugin_qfxaile 项目开发指南

> AstrBot 的 Qfxaile 综合插件，提供申请审批、定时发图、缩写查询、消息撤回和词云功能。

## 技术栈

- Python 3.12+
- AstrBot 插件 API
- uv、pytest、pytest-asyncio、Ruff

## 目录结构

- `main.py`：AstrBot 事件入口、功能开关、权限判断和后台调度。
- `qfxaile/`：业务服务模块。
- `_conf_schema.json`：嵌套功能配置 schema。
- `tests/`：pytest 测试。
- `requirements.txt`、`pyproject.toml`、`uv.lock`：依赖和开发工具配置。

## 模块索引

- `config.py`：点路径配置读取、写入、数值限制、时间解析和资源路径。
- `request_approval.py`：好友/加群申请转发与审批。
- `daily_image.py`：定时发图、关键词随机发图和群组会话生成。
- `abbreviation.py`：异步缩写查询。
- `recall.py`：消息撤回。
- `wordcloud_service.py`：历史消息读取、统计和词云生成。
- `onebot.py`：OneBot API 适配。
- `scheduler.py`：后台任务生命周期管理。
- `storage.py`：申请记录 JSON 存储。

## 配置约定

配置使用嵌套 JSON 分组，例如 `daily_image.schedule_time`、`wordcloud.schedule.time`。每个功能的 `enabled` 开关由 `main.py` 入口统一检查；词云总开关同时控制词云命令和自动统计。定时目标只配置群号，平台由代码自动发现。

## 开发流程

1. 修改前先搜索现有模块和配置路径，优先复用已有服务。
2. 先设计并确认影响范围，再修改代码。
3. 新增或修改行为时同步更新 `_conf_schema.json` 和相关测试。
4. 修改完成后必须执行并记录以下检查：
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
5. 仅检查通过后再报告完成。

## 文档同步

涉及功能、配置、模块职责、目录结构或验证流程时，必须同步更新本文件和 README。

## 安全与操作约束

- 不提交密钥、管理员 ID 或其他敏感信息。
- 删除文件、修改配置、安装依赖、运行测试、构建和 Git 操作前，先向用户说明影响并获得确认。
- 不在 Conda base 环境安装依赖。
