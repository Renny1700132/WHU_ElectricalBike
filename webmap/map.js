/**
 * 武大电单车系统 - MapEngine (成员 C 负责)
 * 核心逻辑：离线降级、图层渲染、POI加载、动画调度、健壮事件系统
 */

// 🚨 核心补丁：强行让老版本的 leaflet.heat 支持 Leaflet 1.x 的 pane 选项
// 确保热力图可以独立设置层级，不被建筑和路网遮挡
if (typeof L.HeatLayer !== 'undefined') {
    L.HeatLayer.include({
        onAdd: function (map) {
            this._map = map;
            if (!this._canvas) {
                this._initCanvas();
            }
            // 如果传入了 pane，就放在专属 pane 里，否则才放默认 pane
            if (this.options.pane) {
                this.getPane().appendChild(this._canvas);
            } else {
                map._panes.overlayPane.appendChild(this._canvas);
            }
            map.on('moveend', this._reset, this);
            if (map.options.zoomAnimation && L.Browser.any3d) {
                map.on('zoomanim', this._animateZoom, this);
            }
            this._reset();
        }
    });
}

const MapEngine = {
    map: null,
    layers: {
        campusBase: L.featureGroup(),
        heatmap: L.layerGroup(),
        sitingSites: L.featureGroup(),
        sitingCoverage: L.featureGroup(),
        manualSites: L.featureGroup(),
        manualCoverage: L.featureGroup(),
        dispatchRoutes: L.featureGroup(),
        dispatchVehicles: L.layerGroup(),
        processArtifacts: L.featureGroup()
    },
    
    _events: {},
    _animationState: { reqId: null, startTime: 0, vehicles: [], duration: 5000 }, 
    _processPlayState: { timer: null, states: [], currentIndex: 0 }, 

    // ==========================================
    // 1. 核心初始化与事件系统
    // ==========================================
    init(containerId, options = {}) {
        if (this.map) return;
        const basemapType = options.basemap || 'cartoDark';

        const whuBounds = L.latLngBounds([30.515, 114.340], [30.550, 114.380]);

        this.map = L.map(containerId, {
            center: [30.528, 114.360],
            zoom: 16,
            minZoom: 14, 
            maxBounds: whuBounds,
            maxBoundsViscosity: 1.0, 
            zoomControl: false 
        });

        this.map.createPane('heatPane');
        this.map.getPane('heatPane').style.zIndex = 500;
        this.map.getPane('heatPane').style.pointerEvents = 'none';

        if (basemapType === 'cartoDark') {
            const tileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; CARTO',
                subdomains: 'abcd',
                maxZoom: 20
            }).addTo(this.map);

            let tileErrorCount = 0;
            tileLayer.on('tileerror', () => {
                tileErrorCount++;
                if (tileErrorCount === 2) { 
                    this.emit('basemap:error', { message: '瓦片加载失败，切为无底图模式' });
                    this.map.removeLayer(tileLayer);
                    
                    const errorControl = L.control({ position: 'bottomright' });
                    errorControl.onAdd = function () {
                        const div = L.DomUtil.create('div', 'basemap-error-toast');
                        div.innerHTML = '⚠️ 底图瓦片加载失败，已自动降级为无底图模式';
                        return div;
                    };
                    errorControl.addTo(this.map);
                }
            });
        }

        Object.values(this.layers).forEach(layer => layer.addTo(this.map));

        const legendControl = L.control({ position: 'bottomright' });
        legendControl.onAdd = function () {
            const div = document.createElement('div');
            div.style.cssText = 'background:rgba(15,25,35,0.95);border:1px solid #2a3a4a;border-radius:8px;padding:8px 12px;font-size:11px;color:#e0e0e0;box-shadow:0 2px 10px rgba(0,0,0,0.3);';

            const title = document.createElement('div');
            title.style.cssText = 'font-weight:bold;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid #2a3a4a;color:#00FA9A;font-size:12px;';
            title.textContent = '图例';
            div.appendChild(title);

            const items = [
                { color: '#2ecc71', label: '推荐停车点' },
                { color: '#3498db', label: '手动选址点' },
                { color: '#90EE90', label: '服务覆盖区' },
                { color: '#e74c3c', label: '需求热力' }
            ];

            items.forEach(item => {
                const row = document.createElement('div');
                row.style.cssText = 'display:flex;align-items:center;margin:3px 0;';

                const colorBox = document.createElement('span');
                colorBox.style.cssText = `width:12px;height:12px;border-radius:2px;margin-right:6px;background-color:${item.color};`;

                const label = document.createElement('span');
                label.textContent = item.label;

                row.appendChild(colorBox);
                row.appendChild(label);
                div.appendChild(row);
            });

            return div;
        };
        legendControl.addTo(this.map);

        this.map.on('click', (e) => this.emit('map:clicked', { latlng: e.latlng }));
        this.emit('ready', { status: 'ok' });
    },

    on(eventName, handler) {
        if (!this._events[eventName]) this._events[eventName] = [];
        this._events[eventName].push(handler);
    },

    off(eventName, handler) {
        if (!this._events[eventName]) return;
        if (!handler) {
            this._events[eventName] = []; 
        } else {
            this._events[eventName] = this._events[eventName].filter(h => h !== handler);
        }
    },

    emit(eventName, payload) {
        if (this._events[eventName]) {
            this._events[eventName].forEach(handler => {
                try {
                    handler(payload);
                } catch (err) {
                    console.error(`[MapEngine] 事件 ${eventName} 的回调执行报错:`, err);
                }
            });
        }
    },

    // ==========================================
    // 2. 基础底图模块 & 热力图
    // ==========================================
    setCampusBaseData(geoJsonData) {
        this.layers.campusBase.clearLayers();
        if (!geoJsonData) return;
        
        if (geoJsonData.buildings) {
            L.geoJSON(geoJsonData.buildings, { 
                style: { color: '#00E5FF', weight: 1.5, fillColor: '#0A243F', fillOpacity: 0.6 } 
            }).addTo(this.layers.campusBase);
        }
        
        if (geoJsonData.road_network) {
            L.geoJSON(geoJsonData.road_network, { 
                style: { color: '#00FA9A', weight: 2, dashArray: '3, 6', opacity: 0.4 } 
            }).addTo(this.layers.campusBase);
        }

        if (geoJsonData.pois) {
            L.geoJSON(geoJsonData.pois, {
                pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
                    radius: 4,
                    fillColor: '#F1C40F', 
                    color: '#FFF',
                    weight: 1,
                    fillOpacity: 0.8,
                    className: 'campus-poi-marker'
                }),
                onEachFeature: (feature, layer) => {
                    const name = feature.properties?.name || '未知建筑 (POI)';
                    layer.bindPopup(`<div class="siting-popup"><b>${name}</b></div>`);
                }
            }).addTo(this.layers.campusBase);
        }
        
        if (this.map && this.layers.campusBase.getLayers().length > 0 && typeof this.layers.campusBase.getBounds === "function") {
            const bounds = this.layers.campusBase.getBounds();
            if (bounds && bounds.isValid && bounds.isValid()) {
                this.map.flyToBounds(bounds, { padding: [20, 20], duration: 1.5 });
            }
        }
    },

    // ✨ 彻底改造的专属热力图渲染方法 (修复：颜色渐变整体向“红”移动)
    renderHeatmap(points, options = {}) {
        this.layers.heatmap.clearLayers();
        if (!points || points.length === 0) return;

        let processedPoints = points;
        
        // 如果点位较少（3~10个），自动将其权重翻倍（封顶为1.0），防止光晕太黯淡
        if (points.length >= 3 && points.length <= 10) {
            processedPoints = points.map(p => {
                if (p.length > 2) {
                    return [p[0], p[1], Math.min(1.0, p[2] * 2)];
                }
                return p;
            });
        }

        // 合并默认参数与传入参数
        const heatOptions = {
            radius: options.radius || 55,         // 光晕更大
            blur: options.blur || 35,             // 边缘更柔和
            minOpacity: options.minOpacity || 0.45, // 保证最低权重也依然清晰可见
            // 🚨 颜色渐变升级：更红、更暖的霓虹赛博朋克色系
            // 从青色(0.1)到黄色(0.5)再到鲜艳红色(0.9)
            gradient: options.gradient || { 
                '0.1': '#22d3ee', // 亮青色，表示 cool 区域
                '0.5': '#fcd34d', // 黄色，表示 warning 区域
                '0.9': '#ef4444'  // 亮红色，表示极热、最高需求区域
            },
            pane: 'heatPane' // 指向在 init 中创建的 500 层级专属 pane
        };

        L.heatLayer(processedPoints, heatOptions).addTo(this.layers.heatmap);
    },

    // ==========================================
    // 3. 智能选址模块 & 人工选址
    // ==========================================
    setSitingOptimizeResponse(resp) {
        this.clearSiting();
        if (!resp) return;

        if (resp.coverage_areas) {
            L.geoJSON(resp.coverage_areas, { style: { color: '#2ecc71', weight: 2, opacity: 0.8, fillColor: '#90EE90', fillOpacity: 0.2, className: 'siting-coverage-path' } }).addTo(this.layers.sitingCoverage);
        }
        if (resp.optimal_sites) {
            L.geoJSON(resp.optimal_sites, {
                pointToLayer: (feature, latlng) => L.circleMarker(latlng, { radius: 8, fillColor: '#2ecc71', color: '#fff', weight: 2, fillOpacity: 0.9, className: 'siting-point-marker' }),
                onEachFeature: (feature, layer) => {
                    const props = feature.properties;
                    layer.bindPopup(`<div class="siting-popup"><h4>推荐停车点</h4><p><b>编号:</b> ${props.site_id}</p><p><b>容量:</b> ${props.capacity}</p><p><b>服务人数:</b> ${props.served_people}</p></div>`);
                    layer.on('click', () => this.emit('marker:clicked', { type: 'optimal', id: props.site_id, data: props }));
                }
            }).addTo(this.layers.sitingSites);
        }

        this.layers.sitingSites.addTo(this.map);
        this.layers.sitingCoverage.addTo(this.map);

        const bounds = this.getSitingBounds();
        if (bounds) this.map.flyToBounds(bounds, { padding: [50, 50], duration: 1.2 });

        this.emit("siting:rendered", { count: resp.optimal_sites?.features.length || 0, metrics: resp.global_metrics });
    },

    setSitingEvaluateResponse(resp) {
        this.layers.manualCoverage.clearLayers();
        if (resp?.coverage_areas) {
            L.geoJSON(resp.coverage_areas, { style: { color: '#3498db', weight: 2, dashArray: '5, 10', fillColor: '#ADD8E6', fillOpacity: 0.3 } }).addTo(this.layers.manualCoverage);
        }
        this.layers.manualCoverage.addTo(this.map);
    },

    addSitingData(resp) {
        if (!resp) return;
        if (resp.coverage_areas) {
            L.geoJSON(resp.coverage_areas, { style: { color: '#2ecc71', weight: 2, opacity: 0.8, fillColor: '#90EE90', fillOpacity: 0.2, className: 'siting-coverage-path' } }).addTo(this.layers.sitingCoverage);
        }
        if (resp.optimal_sites) {
            L.geoJSON(resp.optimal_sites, {
                pointToLayer: (feature, latlng) => L.circleMarker(latlng, { radius: 8, fillColor: '#2ecc71', color: '#fff', weight: 2, fillOpacity: 0.9, className: 'siting-point-marker' }),
                onEachFeature: (feature, layer) => {
                    const props = feature.properties;
                    layer.bindPopup(`<div class="siting-popup"><h4>推荐停车点</h4><p><b>编号:</b> ${props.site_id}</p><p><b>容量:</b> ${props.capacity}</p><p><b>服务人数:</b> ${props.served_people}</p></div>`);
                    layer.on('click', () => this.emit('marker:clicked', { type: 'optimal', id: props.site_id, data: props }));
                }
            }).addTo(this.layers.sitingSites);
        }
    },

    addManualCoverageData(resp) {
        if (resp?.coverage_areas) {
            L.geoJSON(resp.coverage_areas, { style: { color: '#3498db', weight: 2, dashArray: '5, 10', fillColor: '#ADD8E6', fillOpacity: 0.3 } }).addTo(this.layers.manualCoverage);
        }
    },

    getSitingBounds() {
        const hasSites = this.layers.sitingSites.getLayers().length > 0;
        const hasCoverage = this.layers.sitingCoverage.getLayers().length > 0;
        let bounds = null;
        if (hasSites) bounds = this.layers.sitingSites.getBounds();
        if (hasCoverage) {
            const coverageBounds = this.layers.sitingCoverage.getBounds();
            bounds = bounds ? bounds.extend(coverageBounds) : coverageBounds;
        }
        return bounds && bounds.isValid() ? bounds : null;
    },

    addManualSite(site) {
        if (!site || site.latitude === undefined || site.longitude === undefined) return null;
        const site_id = site.site_id || `manual-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        const customIcon = L.divIcon({ className: 'manual-site-marker', iconSize: [18, 18], iconAnchor: [9, 9] });
        const marker = L.marker([site.latitude, site.longitude], { icon: customIcon, draggable: true });
        marker.siteData = { site_id, name: site.name || '自定义点位', capacity: site.capacity || 30, latitude: site.latitude, longitude: site.longitude };

        marker.on('dragend', (e) => {
            const newPos = e.target.getLatLng();
            marker.siteData.latitude = newPos.lat;
            marker.siteData.longitude = newPos.lng;
            this.emit("manualSite:dragged", { site_id: marker.siteData.site_id, latitude: newPos.lat, longitude: newPos.lng });
        });
        marker.on('click', () => this.emit("manualSite:clicked", marker.siteData));
        marker.addTo(this.layers.manualSites);
        if (!this.map.hasLayer(this.layers.manualSites)) {
            this.layers.manualSites.addTo(this.map);
        }
        return site_id;
    },

    removeManualSite(site_id) {
        this.layers.manualSites.eachLayer((layer) => { if (layer.siteData && layer.siteData.site_id === site_id) this.layers.manualSites.removeLayer(layer); });
    },

    getManualSites() {
        const sites = [];
        this.layers.manualSites.eachLayer((layer) => { if (layer.siteData) sites.push({ ...layer.siteData }); });
        return sites;
    },

    // ==========================================
    // 4. 车辆调度与动画模块 
    // ==========================================
    setDispatchOptimizeResponse(resp) {
        this.clearDispatch();
        if (!resp || !resp.dispatch_routes) return;

        const colorPalette = ['#e74c3c', '#9b59b6', '#34495e', '#16a085', '#27ae60', '#2980b9', '#f39c12', '#d35400'];
        const getRouteColor = (vid) => {
            let num = String(vid).replace(/\D/g, '') || 0;
            return colorPalette[num % colorPalette.length];
        };

        let routeCount = 0;

        L.geoJSON(resp.dispatch_routes, {
            style: (feature) => {
                return {
                    color: getRouteColor(feature.properties.vehicle_id),
                    weight: 8, opacity: 0.8, dashArray: '15, 10', className: 'dispatch-route-line'
                };
            },
            onEachFeature: (feature, layer) => {
                routeCount++;
                const props = feature.properties;
                layer.bindPopup(`
                    <div class="dispatch-popup">
                        <h4>调度任务</h4>
                        <p><b>车辆 ID:</b> ${props.vehicle_id}</p>
                        <p><b>起点:</b> ${props.from_site || '未知'}</p>
                        <p><b>终点:</b> ${props.to_site || '未知'}</p>
                        <p><b>搬运数量:</b> ${props.transfer_count} 辆</p>
                    </div>
                `);
                layer.on('click', (e) => L.DomEvent.stopPropagation(e));
            }
        }).addTo(this.layers.dispatchRoutes);

        if (this.layers.dispatchRoutes.getLayers().length > 0) {
            this.map.flyToBounds(this.layers.dispatchRoutes.getBounds(), { padding: [50, 50], duration: 1.2 });
        }
        this.emit("dispatch:rendered", { routeCount, efficiency: resp.efficiency_metrics });
    },

    playDispatchAnimation(options = {}) {
        this.stopDispatchAnimation(); 
        
        const routes = [];
        this.layers.dispatchRoutes.eachLayer((geoJsonLayer) => {
            if (geoJsonLayer.eachLayer) {
                geoJsonLayer.eachLayer((subLayer) => { if (subLayer.getLatLngs) routes.push(subLayer); });
            } else if (geoJsonLayer.getLatLngs) {
                routes.push(geoJsonLayer);
            }
        });

        if (routes.length === 0) return;

        this._animationState.duration = options.duration || 8000; 
        this._animationState.vehicles = [];

        routes.forEach(routeLayer => {
            const latlngs = routeLayer.getLatLngs();
            const pathCoords = Array.isArray(latlngs[0]) ? latlngs[0] : latlngs; 
            if (!pathCoords || pathCoords.length < 2) return;

            const routeColor = routeLayer.options?.color || '#333';
            const vehicleIcon = L.divIcon({
                className: 'dispatch-vehicle-marker',
                html: `<div style="background-color: ${routeColor};"></div>`,
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });

            const vehicleMarker = L.marker(pathCoords[0], { icon: vehicleIcon, zIndexOffset: 1000 }).addTo(this.layers.dispatchVehicles);

            let totalDist = 0;
            const dists = [0];
            for (let i = 0; i < pathCoords.length - 1; i++) {
                const d = pathCoords[i].distanceTo(pathCoords[i+1]);
                totalDist += d;
                dists.push(totalDist);
            }

            this._animationState.vehicles.push({ marker: vehicleMarker, path: pathCoords, dists: dists, totalDist: totalDist });
        });

        this._animationState.startTime = performance.now();
        const animate = (currentTime) => {
            let elapsed = currentTime - this._animationState.startTime;
            let progress = (elapsed % this._animationState.duration) / this._animationState.duration;

            this._animationState.vehicles.forEach(v => {
                const targetDist = v.totalDist * progress;
                for (let i = 0; i < v.dists.length - 1; i++) {
                    if (targetDist >= v.dists[i] && targetDist <= v.dists[i+1]) {
                        const segmentLen = v.dists[i+1] - v.dists[i];
                        const segmentFraction = segmentLen === 0 ? 0 : (targetDist - v.dists[i]) / segmentLen;
                        
                        const p1 = v.path[i];
                        const p2 = v.path[i+1];
                        const lat = p1.lat + (p2.lat - p1.lat) * segmentFraction;
                        const lng = p1.lng + (p2.lng - p1.lng) * segmentFraction;
                        
                        v.marker.setLatLng([lat, lng]);
                        break;
                    }
                }
            });
            this._animationState.reqId = requestAnimationFrame(animate);
        };
        this._animationState.reqId = requestAnimationFrame(animate);
    },

    stopDispatchAnimation() {
        if (this._animationState.reqId) {
            cancelAnimationFrame(this._animationState.reqId);
            this._animationState.reqId = null;
        }
        this.layers.dispatchVehicles.clearLayers();
        this._animationState.vehicles = [];
    },

    // ==========================================
    // 5. 算法迭代过程可视化模块
    // ==========================================
    renderProcessState(state) {
        this.layers.processArtifacts.clearLayers();
        if (!state || !state.artifacts) return;

        if (state.artifacts.candidate_sites) {
            L.geoJSON(state.artifacts.candidate_sites, {
                pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
                    radius: 5, fillColor: '#95a5a6', color: '#7f8c8d', weight: 1, fillOpacity: 0.6, className: 'process-candidate-site'
                }),
                interactive: false 
            }).addTo(this.layers.processArtifacts);
        }

        if (state.artifacts.dispatch_routes) {
            L.geoJSON(state.artifacts.dispatch_routes, {
                style: {
                    color: '#bdc3c7', weight: 2, dashArray: '4, 6', opacity: 0.6, className: 'process-dispatch-route'
                },
                interactive: false
            }).addTo(this.layers.processArtifacts);
        }

        if (this.layers.processArtifacts.getLayers().length > 0) {
            this.map.flyToBounds(this.layers.processArtifacts.getBounds(), { padding: [30, 30], duration: 0.5 }); 
        }

        this.emit("process:stateRendered", { iteration: state.iteration, metrics: state.metrics });
    },

    setProcessStates(statesArray) {
        this._processPlayState.states = statesArray || [];
        this._processPlayState.currentIndex = 0;
    },

    playProcess(intervalMs = 300) {
        this.stopProcess();
        if (!this._processPlayState.states.length) return;

        this._processPlayState.timer = setInterval(() => {
            if (this._processPlayState.currentIndex >= this._processPlayState.states.length) {
                this.stopProcess();
                this.emit("process:finished", {}); 
                return;
            }
            const state = this._processPlayState.states[this._processPlayState.currentIndex];
            this.renderProcessState(state);
            this._processPlayState.currentIndex++;
        }, intervalMs);
    },

    stopProcess() {
        if (this._processPlayState.timer) {
            clearInterval(this._processPlayState.timer);
            this._processPlayState.timer = null;
        }
    },

    // ==========================================
    // 6. 统一清理方法集
    // ==========================================
    clearSiting() {
        if (this.map.hasLayer(this.layers.sitingSites)) this.map.removeLayer(this.layers.sitingSites);
        if (this.map.hasLayer(this.layers.sitingCoverage)) this.map.removeLayer(this.layers.sitingCoverage);
        this.layers.sitingSites.clearLayers();
        this.layers.sitingCoverage.clearLayers();
    },
    clearManualSites() {
        if (this.map.hasLayer(this.layers.manualSites)) this.map.removeLayer(this.layers.manualSites);
        if (this.map.hasLayer(this.layers.manualCoverage)) this.map.removeLayer(this.layers.manualCoverage);
        this.layers.manualSites.clearLayers();
        this.layers.manualCoverage.clearLayers();
    },
    clearManualCoverage() {
        if (this.map.hasLayer(this.layers.manualCoverage)) this.map.removeLayer(this.layers.manualCoverage);
        this.layers.manualCoverage.clearLayers();
    },
    clearDispatch() {
        this.stopDispatchAnimation(); 
        this.layers.dispatchRoutes.clearLayers();
    },
    clearProcessArtifacts() { 
        this.stopProcess(); 
        this.layers.processArtifacts.clearLayers(); 
    }
};

window.MapEngine = MapEngine;