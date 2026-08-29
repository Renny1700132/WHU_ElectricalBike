# 成员 C（WebGIS Map Core）交付与对接说明：MapEngine

> 作用域：仅覆盖 `<div id="map">` 容器内部的地图渲染、图层管理与动画。  
> 目标读者：成员 D（前端交互/大屏）为主，成员 B（算法工程）为辅。  
> 代码位置：`webmap/map.js`（核心）、`webmap/style.css`（样式）、`webmap/index.html`（联调演示页）。

---

## 1. 职责边界（非常重要）

### 成员 C 负责（Map 内部）
- Leaflet 地图初始化、底图加载与离线降级（瓦片加载失败自动降级无底图）。
- 校园底数据渲染：建筑（buildings）/ 路网（road_network）/ POI（pois）。
- 需求热力图渲染：支持更高对比度参数 + 独立 `pane`，避免被建筑/路网遮挡。
- 算法结果上图：
  - 选址推荐点（optimal_sites）+ 覆盖圈（coverage_areas）
  - 调度路线（dispatch_routes）+ 车辆动画（play/stop）
  - 算法过程可视化（candidate_sites / dispatch_routes 的迭代态渲染与播放）
- 交互事件“抛出”：地图点击、手动点拖拽等（只发事件，不做业务逻辑）。

### 成员 C 不负责（Map 外部）
- 不做业务面板、按钮状态、页面路由、图表（ECharts）等。
- 不做“何时请求后端”的业务决策；不维护全局业务状态。
- 不做算法数学逻辑（只负责把算法输出渲染到地图上）。

> 备注：`webmap/index.html` 里存在“联调用”的 `fetch /campus/base-data` 示例，方便单页跑通；正式集成建议由成员 D 接管请求逻辑。

---

## 2. 快速联调（成员 D / 所有人）

### 启动后端（成员 A 交付）
在项目根目录：
```powershell
cd E:\whu_electricalbike
python run.py
```
验证后端：
- `http://127.0.0.1:7860/health`
- `http://127.0.0.1:7860/api/campus/base-data`

### 启动前端静态服务（推荐，不建议直接双击 html）
```powershell
cd E:\whu_electricalbike\webmap
python -m http.server 5173
```
打开：
```text
http://127.0.0.1:5173/?apiBase=http://127.0.0.1:7860/api
```

---

## 3. MapEngine 对外 API（供 D 调用）

### 3.1 初始化与配置
- `MapEngine.init(containerId, options?)`
  - `options.basemap`: `'cartoDark' | 'none'`（默认 `'cartoDark'`）
  - 内部创建 `heatPane`（zIndex=500）并将其 `pointerEvents='none'`，保证热力图不挡鼠标事件。

### 3.2 事件系统（只抛事件，不做业务）
- `MapEngine.on(eventName, handler)`
- `MapEngine.off(eventName, handler?)`：`handler` 为空则清空该事件所有回调
- `MapEngine.emit(eventName, payload)`：内部对回调 `try/catch`，避免单个回调报错影响其他回调

常用事件（建议 D 监听）：
- `ready`：地图已初始化
- `basemap:error`：底图瓦片加载失败，已降级
- `map:clicked`：地图被点击（可用于“拾取坐标”）
- `manualSite:clicked` / `manualSite:dragged`：手动点位交互
- `siting:rendered` / `dispatch:rendered` / `process:stateRendered`：地图层渲染完成回执

### 3.3 校园底数据
- `MapEngine.setCampusBaseData(baseData)`
  - 期望字段：`baseData.buildings`、`baseData.road_network`、`baseData.pois`（GeoJSON）
  - 渲染后自动 `flyToBounds`（若 bounds 可用）

### 3.4 需求热力图
- `MapEngine.renderHeatmap(points, options?)`
  - `points`：`[[lat, lng, weight], ...]`
  - 默认参数已针对深色底图增强可见性：`radius/blur/minOpacity/gradient`
  - 若点数在 `3~10` 会自动将 `weight * 2`（封顶 1.0），避免“太淡看不见”

### 3.5 选址结果上图（B → A → D → C）
- `MapEngine.setSitingOptimizeResponse(resp)`
  - 期望字段：`resp.optimal_sites`（GeoJSON Point FeatureCollection）、`resp.coverage_areas`（GeoJSON Polygon FeatureCollection）、`resp.global_metrics`
  - 会触发：`emit("siting:rendered", { count, metrics })`
- `MapEngine.setSitingEvaluateResponse(resp)`
  - 用于人工点位评估结果上图（覆盖面）
- `MapEngine.getSitingBounds()`

### 3.6 手动停车点（D 的核心交互入口）
- `MapEngine.addManualSite(site)`
  - 输入最少：`{ latitude, longitude }`
  - 输出：生成的 `site_id`
  - 交互：可拖拽，拖拽结束会 `emit("manualSite:dragged", {site_id, latitude, longitude})`
- `MapEngine.removeManualSite(site_id)`
- `MapEngine.getManualSites()`：返回可直接作为后端 `/api/siting/evaluate` 的 `current_sites`
- `MapEngine.clearManualSites()`

### 3.7 调度路线与动画（B → A → D → C）
- `MapEngine.setDispatchOptimizeResponse(resp)`
  - 期望字段：`resp.dispatch_routes`（GeoJSON LineString FeatureCollection）、`resp.efficiency_metrics`
  - 会触发：`emit("dispatch:rendered", { routeCount, efficiency })`
- `MapEngine.playDispatchAnimation(options?)`
  - `options.duration`：一圈动画时长（ms）
- `MapEngine.stopDispatchAnimation()`
- `MapEngine.clearDispatch()`

### 3.8 算法过程可视化（可选）
- `MapEngine.renderProcessState(state)`
  - 支持渲染 `state.artifacts.candidate_sites` / `state.artifacts.dispatch_routes`
  - 会触发：`emit("process:stateRendered", { iteration, metrics })`
- `MapEngine.setProcessStates(statesArray)`
- `MapEngine.playProcess(intervalMs)`
- `MapEngine.stopProcess()`
- `MapEngine.clearProcessArtifacts()`

---

## 4. 成员 D 对接指南（推荐流程）

### 4.1 数据流推荐（职责清晰）
1) D 启动页面、决定 `apiBase`（环境配置）
2) D 请求后端接口拿 JSON
3) D 将**原始 JSON**直接传入 MapEngine（C 只负责“画图”）
4) C 抛出事件给 D（例如拖拽后坐标变化），D 决定是否触发后端评估/优化并更新 UI

### 4.2 典型调用模板（伪代码）
```js
MapEngine.init("map", { basemap: "cartoDark" });

// 1) 底数据
const base = await fetch(`${apiBase}/campus/base-data`).then(r => r.json());
MapEngine.setCampusBaseData(base);

// 2) 热力图（按早/中/晚切换）
const heat = await fetch(`${apiBase}/demand/heatmap?period=morning`).then(r => r.json());
MapEngine.renderHeatmap(heat.points);

// 3) 智能选址
const siting = await fetch(`${apiBase}/siting/optimize`, {method:"POST", body:...}).then(r => r.json());
MapEngine.setSitingOptimizeResponse(siting);

// 4) 手动点：点击按钮时由 D 调用 addManualSite（C 不做按钮）
const newId = MapEngine.addManualSite({ latitude, longitude, capacity: 30, name: "手动点" });

MapEngine.on("manualSite:dragged", async ({ site_id, latitude, longitude }) => {
  // D 决定是否触发评估
  const evalResp = await fetch(`${apiBase}/siting/evaluate`, {method:"POST", body: JSON.stringify({ current_sites: MapEngine.getManualSites() })}).then(r => r.json());
  MapEngine.setSitingEvaluateResponse(evalResp);
});

// 5) 调度
const dispatch = await fetch(`${apiBase}/dispatch/optimize`, {method:"POST", body:...}).then(r => r.json());
MapEngine.setDispatchOptimizeResponse(dispatch);
MapEngine.playDispatchAnimation({ duration: 8000 });
```

---

## 5. 成员 B 对接说明（输出结构建议）

> B 不需要关心 Leaflet/OpenLayers 细节；只需要保证输出数据结构稳定，最终由 A 封装为后端响应，D 再喂给 MapEngine。

### 5.1 坐标与格式（高频踩坑）
- GeoJSON 坐标顺序必须是：`[lng, lat]`
- 热力图点位数组顺序是：`[lat, lng, weight]`（不是 GeoJSON）
- 建议使用 WGS84（EPSG:4326）经纬度；不要输出投影坐标（米制坐标）

### 5.2 选址输出（建议字段）
- `optimal_sites`: `FeatureCollection(Point)`  
  `properties` 建议包含：`site_id`, `name`, `capacity`, `served_people`
- `coverage_areas`: `FeatureCollection(Polygon)`  
  `properties` 建议包含：`site_id`, `name`, `service_radius`
- `global_metrics`: `coverage_ratio`, `average_walking_distance` 等（供 D 做图表）

### 5.3 调度输出（建议字段）
- `dispatch_routes`: `FeatureCollection(LineString)`  
  `properties` 建议包含：`vehicle_id`, `from_site`, `to_site`, `transfer_count`
- `efficiency_metrics`: `total_distance_km`, `total_duration_min`, `estimated_cost` 等（供 D 做图表）

### 5.4 过程可视化（可选但强烈推荐）
若要支持过程回放，建议每次迭代输出：
- `candidate_sites`: `FeatureCollection(Point)`（选址）
- `dispatch_routes`: `FeatureCollection(LineString)`（调度）
并在 `state.metrics` 中包含可画曲线的指标（fitness/coverage/distance/cost 等）。

---

## 6. 自测（成员 C 完整功能回归）

浏览器 DevTools Console 可以执行一套端到端自测脚本（包含：底数据、热力图、选址、手动点、评估、调度、过程回放、clear、off）。

建议参考：成员 C 提供的 Console 自测脚本（可复制粘贴执行）。
如果需要将自测脚本固化成文件（例如 `webmap/devtest.js` 并提供 `runAllTests()`），可再沟通追加。

---

## 7. 已知注意事项 / FAQ

1) **Chrome 控制台提示 `willReadFrequently`**  
这是 Canvas 性能建议，不是错误；leaflet-heat 在重绘时会出现该提示。

2) **底图黑屏/瓦片被墙**  
MapEngine 已在瓦片连续报错时自动降级无底图，并通过事件 `basemap:error` 提醒；D 可提示用户改用 `basemap:'none'`。

3) **热力图看不见**  
常见原因：点数太少/权重太低/视野不在点附近/层级被遮挡。当前已通过 `heatPane(zIndex=500)` + 默认参数增强可见性。

