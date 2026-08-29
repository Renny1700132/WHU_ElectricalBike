# MapEngine Console 自测脚本（成员 C）

> 用途：在浏览器 DevTools Console 中“复制粘贴”完成 C 侧全功能回归测试。  
> 前置：后端已启动在 `http://127.0.0.1:7860`，前端建议用静态服务器打开：`http://127.0.0.1:5173/?apiBase=http://127.0.0.1:7860/api`。

---

## A) 安装测试 Helper（先粘贴这段）

```js
const API = new URLSearchParams(location.search).get("apiBase") || "http://127.0.0.1:7860/api";
console.log("[TEST] API =", API);

async function jget(path) {
  const url = `${API}${path}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`);
  return res.json();
}

async function jpost(path, body) {
  const url = `${API}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url} :: ${await res.text().catch(()=> "")}`);
  return res.json();
}

function layerCount(layer) {
  return layer?.getLayers ? layer.getLayers().length : 0;
}

function assert(cond, msg) {
  if (!cond) throw new Error("[ASSERT FAIL] " + msg);
  console.log("[OK]", msg);
}

// 事件监听（可随时 off）
window.__ME_LOG_READY__ = (d) => console.log("[evt] ready", d);
window.__ME_LOG_CLICK__ = (d) => console.log("[evt] map:clicked", d);
window.__ME_LOG_BASEMAP__ = (d) => console.warn("[evt] basemap:error", d);
window.__ME_LOG_SITING__ = (d) => console.log("[evt] siting:rendered", d);
window.__ME_LOG_DISPATCH__ = (d) => console.log("[evt] dispatch:rendered", d);
window.__ME_LOG_MANUAL_DRAG__ = (d) => console.log("[evt] manualSite:dragged", d);
window.__ME_LOG_MANUAL_CLICK__ = (d) => console.log("[evt] manualSite:clicked", d);
window.__ME_LOG_PROCESS__ = (d) => console.log("[evt] process:stateRendered", d);

MapEngine.on("ready", window.__ME_LOG_READY__);
MapEngine.on("map:clicked", window.__ME_LOG_CLICK__);
MapEngine.on("basemap:error", window.__ME_LOG_BASEMAP__);
MapEngine.on("siting:rendered", window.__ME_LOG_SITING__);
MapEngine.on("dispatch:rendered", window.__ME_LOG_DISPATCH__);
MapEngine.on("manualSite:dragged", window.__ME_LOG_MANUAL_DRAG__);
MapEngine.on("manualSite:clicked", window.__ME_LOG_MANUAL_CLICK__);
MapEngine.on("process:stateRendered", window.__ME_LOG_PROCESS__);

console.log("[TEST] helpers installed");
```

---

## B) 冒烟：MapEngine 就绪

```js
assert(!!window.MapEngine, "window.MapEngine exists");
assert(!!MapEngine.map, "MapEngine.map initialized");
assert(!!MapEngine.layers, "MapEngine.layers exists");

console.log("[TEST] layer counts:", {
  campusBase: layerCount(MapEngine.layers.campusBase),
  heatmap: layerCount(MapEngine.layers.heatmap),
  sitingSites: layerCount(MapEngine.layers.sitingSites),
  sitingCoverage: layerCount(MapEngine.layers.sitingCoverage),
  manualSites: layerCount(MapEngine.layers.manualSites),
  dispatchRoutes: layerCount(MapEngine.layers.dispatchRoutes),
  dispatchVehicles: layerCount(MapEngine.layers.dispatchVehicles),
  processArtifacts: layerCount(MapEngine.layers.processArtifacts),
});
```

---

## C) 底数据：buildings / roads / pois

```js
const base = await jget("/campus/base-data");
console.log("[TEST] base-data metadata:", base.metadata);
MapEngine.setCampusBaseData(base);
assert(layerCount(MapEngine.layers.campusBase) > 0, "campusBase rendered");
```

---

## D) 热力图：morning/noon/evening

```js
const heat = await jget("/demand/heatmap?period=morning");
console.log("[TEST] heat points length =", heat.points?.length, "p0 =", heat.points?.[0]);
MapEngine.renderHeatmap(heat.points);
assert(layerCount(MapEngine.layers.heatmap) > 0, "heatmap rendered");
```

---

## E) 选址：optimize（推荐点+覆盖圈）

```js
const siting = await jpost("/siting/optimize", {
  algorithm_type: "GA",
  target_sites_count: 5,
  service_radius: 120,
  include_process: true,
});
console.log("[TEST] siting.run_id =", siting.run_id);
MapEngine.setSitingOptimizeResponse(siting);
assert(layerCount(MapEngine.layers.sitingSites) > 0, "sitingSites rendered");
assert(layerCount(MapEngine.layers.sitingCoverage) > 0, "sitingCoverage rendered");
```

---

## F) 手动点：添加/拖拽/点击/getManualSites

```js
MapEngine.clearManualSites();
const id1 = MapEngine.addManualSite({ name: "Manual-1", latitude: 30.5392, longitude: 114.3651, capacity: 40 });
const id2 = MapEngine.addManualSite({ name: "Manual-2", latitude: 30.5411, longitude: 114.3618, capacity: 35 });
console.log("[TEST] manual ids:", id1, id2);
assert(layerCount(MapEngine.layers.manualSites) >= 2, "manualSites >= 2 markers");
console.log("[TEST] manual sites =", MapEngine.getManualSites());

// 模拟一次 dragend
const m0 = MapEngine.layers.manualSites.getLayers()[0];
m0.setLatLng([30.5405, 114.3640]);
m0.fire("dragend", { target: m0 });
m0.fire("click");
```

---

## G) 人工评估：evaluate（覆盖圈）

```js
const evalResp = await jpost("/siting/evaluate", { current_sites: MapEngine.getManualSites() });
console.log("[TEST] siting.evaluate:", evalResp);
MapEngine.setSitingEvaluateResponse(evalResp);
assert(layerCount(MapEngine.layers.sitingCoverage) > 0, "manual-eval coverage rendered");
```

---

## H) 调度：optimize + 动画

```js
const dispatch = await jpost("/dispatch/optimize", {
  period: "morning",
  algorithm_type: "ACO",
  include_process: true,
});
console.log("[TEST] dispatch.run_id =", dispatch.run_id);
MapEngine.setDispatchOptimizeResponse(dispatch);
assert(layerCount(MapEngine.layers.dispatchRoutes) > 0, "dispatchRoutes rendered");
MapEngine.playDispatchAnimation({ duration: 8000 });
setTimeout(() => MapEngine.stopDispatchAnimation(), 8000);
```

---

## I) 过程回放：states 播放

```js
const runId = siting.run_id; // 或 dispatch.run_id
const statesResp = await jget(`/algorithms/runs/${runId}/states?limit=8`);
console.log("[TEST] states returned =", statesResp.states?.length);
MapEngine.setProcessStates(statesResp.states);
MapEngine.playProcess(400);
setTimeout(() => MapEngine.stopProcess(), 4000);
```

---

## J) 清理回归

```js
MapEngine.clearSiting();
MapEngine.clearManualSites();
MapEngine.clearDispatch();
MapEngine.clearProcessArtifacts();

console.log("[TEST] after clear:", {
  sitingSites: layerCount(MapEngine.layers.sitingSites),
  sitingCoverage: layerCount(MapEngine.layers.sitingCoverage),
  manualSites: layerCount(MapEngine.layers.manualSites),
  dispatchRoutes: layerCount(MapEngine.layers.dispatchRoutes),
  dispatchVehicles: layerCount(MapEngine.layers.dispatchVehicles),
  processArtifacts: layerCount(MapEngine.layers.processArtifacts),
});
```

---

## K) 卸载事件监听（验证 off）

```js
MapEngine.off("ready", window.__ME_LOG_READY__);
MapEngine.off("map:clicked", window.__ME_LOG_CLICK__);
MapEngine.off("basemap:error", window.__ME_LOG_BASEMAP__);
MapEngine.off("siting:rendered", window.__ME_LOG_SITING__);
MapEngine.off("dispatch:rendered", window.__ME_LOG_DISPATCH__);
MapEngine.off("manualSite:dragged", window.__ME_LOG_MANUAL_DRAG__);
MapEngine.off("manualSite:clicked", window.__ME_LOG_MANUAL_CLICK__);
MapEngine.off("process:stateRendered", window.__ME_LOG_PROCESS__);
console.log("[TEST] handlers removed");
```

