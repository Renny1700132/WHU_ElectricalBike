---
title: WHU ElectricalBike
emoji: 🌍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

## Warning
**更新README时，不要删除以上内容，以便Hugging Face远程部署正常！！**

# WHU Electrical Bike Backend

本仓库已经补充了一套可运行的 FastAPI 后端基础环境，用于武汉大学校园电单车 WebGIS 系统的后端联调与后续算法接入。

当前版本：`v0.3.0`

当前阶段目标：

- 搭建统一的 FastAPI 服务入口
- 挂出接口文档中已有的后端接口
- 直接复用本地校园 GeoJSON 数据
- 为尚未实现的算法接口提供结构正确的 mock/stub 返回
- 补充本地方案存储接口，便于联调与后续扩展
- 为未来算法过程可视化预留统一接口与算法目录结构
- 提供后端联调检查脚本与运行日志查看页面

## 当前能力

- FastAPI 应用基础启动
- 统一使用 `/api` 路由前缀
- 健康检查接口：`GET /health`
- 校园基础空间数据接口读取本地 GeoJSON
- 热力图、选址、评估、调度、分析、导出接口已注册
- 新增方案保存、列表、详情、删除接口
- 新增算法过程可视化预留接口
- 新增 `/backend` 后端调试页面，可实时查看运行日志
- `/backend` 页面读取的是当前运行日志文件，因此页面内容与控制台输出保持一致
- 对 `/backend` 与 `/backend/logs` 的 200 成功请求做一分钟聚合输出，并显示省略条数
- 若 `/backend` 或 `/backend/logs` 返回非 200，会立即输出异常日志
- 每次运行服务会在根目录 `log/` 下生成一个新的 `.log` 文件
- 算法相关接口目前返回占位结果，便于前端调试
- `/docs` 文档中的接口摘要与说明已补充中英文

## 运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
python run.py
```

运行 API 自检脚本：

```bash
python -m app.check_backend_api
```

启动后可访问：

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/backend`

## 已注册接口

基础业务接口：

- `GET /api/campus/base-data`
- `GET /api/demand/heatmap`
- `POST /api/siting/optimize`
- `POST /api/siting/evaluate`
- `GET /api/dispatch/status`
- `POST /api/dispatch/optimize`
- `GET /api/analysis/metrics`
- `GET /api/schemes`
- `POST /api/schemes`
- `GET /api/schemes/{scheme_id}`
- `DELETE /api/schemes/{scheme_id}`
- `POST /api/export/scheme`

算法过程可视化预留接口：

- `GET /api/algorithms/process-capabilities`
- `GET /api/algorithms/runs/{run_id}`
- `GET /api/algorithms/runs/{run_id}/states`
- `GET /api/algorithms/runs/{run_id}/states/{iteration}`

后端调试接口：

- `GET /backend`
- `GET /backend/logs`

说明：

- 基础空间数据接口读取 `whu_spatial_data` 下的本地 GeoJSON
- 算法相关接口仍为 mock/stub，占位但格式可用于联调
- 当 `include_process=true` 时，选址/调度接口会返回 `run_id` 和过程摘要
- 前端可再通过算法过程接口拉取迭代中间状态
- 方案存储接口使用本地文件保存到 `whu_spatial_data/schemes`
- 方案存储层已抽象出仓储接口，后续可迁移到数据库
- 运行日志保存到根目录 `log/`，并可通过 `/backend` 页面实时查看

## 本次后端文件结构

```text
WHU_ElectricalBike/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ check_backend_api.py
│  ├─ algorithm/
│  │  ├─ __init__.py
│  │  ├─ README.md
│  │  ├─ base.py
│  │  ├─ siting_optimization.py
│  │  ├─ manual_evaluation.py
│  │  ├─ demand_prediction.py
│  │  └─ dispatch_routing.py
│  ├─ api/
│  │  ├─ __init__.py
│  │  ├─ router.py
│  │  └─ endpoints/
│  │     ├─ __init__.py
│  │     ├─ analysis.py
│  │     ├─ campus.py
│  │     ├─ demand.py
│  │     ├─ dispatch.py
│  │     ├─ export.py
│  │     ├─ process.py
│  │     ├─ scheme.py
│  │     └─ siting.py
│  ├─ core/
│  │  ├─ __init__.py
│  │  └─ config.py
│  ├─ schemas/
│  │  ├─ __init__.py
│  │  ├─ analysis.py
│  │  ├─ campus.py
│  │  ├─ common.py
│  │  ├─ demand.py
│  │  ├─ dispatch.py
│  │  ├─ export.py
│  │  ├─ process.py
│  │  ├─ scheme.py
│  │  └─ siting.py
│  └─ services/
│     ├─ __init__.py
│     ├─ data_loader.py
│     ├─ mock_data.py
│     ├─ process_registry.py
│     ├─ runtime_logging.py
│     └─ scheme_storage.py
├─ log/
├─ requirements.txt
├─ run.py
└─ README.md
```

## 本次重点更新

### 1. `app/algorithm` 目录全部改为中文说明

已将以下文件中的 README、注释和文档字符串全部改成中文，并补充清楚：

- 该函数未来应实现什么算法功能
- 输入参数的含义、推荐格式和字段要求
- 返回值应符合哪个 API 响应模型
- 如果需要过程可视化，应如何输出中间状态

涉及文件：

- `app/algorithm/README.md`
- `app/algorithm/base.py`
- `app/algorithm/siting_optimization.py`
- `app/algorithm/manual_evaluation.py`
- `app/algorithm/demand_prediction.py`
- `app/algorithm/dispatch_routing.py`

### 2. 自检脚本已迁移到 `app/`

原根目录脚本已移到：

- `app/check_backend_api.py`

建议使用以下方式运行：

```bash
python -m app.check_backend_api
```

### 3. `/backend` 页面与控制台输出一致

当前实现方式：

- 控制台和日志文件共用同一套日志格式
- `/backend` 页面直接读取本次运行对应的 `.log` 文件
- 因此页面里看到的日志文本应与控制台里看到的日志文本一致

### 4. `/backend` 与 `/backend/logs` 的 200 成功日志已做聚合

当前规则：

- 第一条 200 请求会正常输出
- 之后 60 秒内的 200 成功请求不逐条打印
- 到下一次输出时，会标明该周期省略了多少条 200 请求日志
- 如果 `/backend` 或 `/backend/logs` 返回非 200，会立刻输出异常日志

## 当前建议的后续开发顺序

1. 让算法同学按 `app/algorithm` 中的中文函数约定补齐真实实现
2. 当某个算法需要过程展示时，在算法内部输出迭代状态并映射为过程接口格式
3. 如需长时任务，再把算法运行从同步调用改为后台任务队列
4. 当需要多人协作和历史检索时，再把方案存储从文件仓储迁移到数据库
5. 最后补充鉴权、日志分级、异常处理和部署配置

