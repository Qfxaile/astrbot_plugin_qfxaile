# astrbot_plugin_qfxaile

Qfxaile 综合插件，整合以下功能：

- OneBot 好友/加群申请转发与“同意”“拒绝”审批。
- 定时发图，以及群聊关键词随机发图。
- 使用 `?缩写` 或 `？缩写` 查询“能不能好好说话”。
- 管理员回复消息并发送“撤回”来撤回消息。
- `/wordcloud`、`/词云`、`/词云生成` 生成群词云。
- `/添加词云群组`、`/删除词云群组` 管理自动词云群组。

配置项已按功能前缀区分，避免原插件之间的同名配置冲突。原五个插件的配置值应迁移到对应的 `agree_*`、`daily_image_*`、`nbnhhsh_*`、`recall_*` 和 `wordcloud_*` 配置项。

依赖：`httpx`、`wordcloud`。

## uv 开发环境

项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 开发环境。AstrBot 安装插件时仍读取 `requirements.txt`；本地开发、测试和代码检查由 `pyproject.toml` 与 `uv.lock` 管理。

首次初始化环境：

```bash
uv sync
```

依赖声明变化后更新锁文件：

```bash
uv lock
uv sync --locked
```

提交前执行：

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
## 模块结构

`main.py` 仅负责 AstrBot 事件适配、权限判断和消息链输出。业务逻辑位于 `qfxaile/`：

- `config.py`：配置规范化、权限和资源路径。
- `onebot.py`：OneBot `call_action`/`call_api` 适配。
- `storage.py`：申请记录 JSON 原子存储。
- `scheduler.py`：后台任务启动、取消和等待。
- `request_approval.py`：好友/加群申请转发与审批。
- `daily_image.py`：定时发图和关键词发图策略。
- `abbreviation.py`：异步缩写查询。
- `recall.py`：回复消息解析和撤回。
- `wordcloud_service.py`：历史消息、统计和词云生成。

申请记录和词云图片默认保存到 AstrBot 的 `data/plugin_data/astrbot_plugin_qfxaile`，不会写入插件源码目录。

重构后仍需在真实 AstrBot 实例中验证插件加载、消息链发送和 OneBot 协议行为。