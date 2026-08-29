from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


"""算法层数据加载模块。

作用：
- 为未来 `app/algorithm` 下的真实算法实现提供统一的数据读取入口。
- 默认读取项目根目录 `whu_spatial_data/` 中已经清洗好的三个 GeoJSON 文件。
- 当前约定读取以下数据：
  - `whu_roads.geojson`
  - `whu_buildings.geojson`
  - `whu_pois.geojson`

设计说明：
- 该模块仅负责“把本地文件读取成 Python 字典对象”。
- 不负责具体算法逻辑，也不负责坐标分析、图构建、字段清洗等后续处理。
- 未来如果迁移到数据库，可保留函数签名不变，仅替换内部实现。
"""


def _read_geojson(path: Path) -> dict[str, Any]:
    """读取单个 GeoJSON 文件。

    输入参数：
    - `path: Path`
      GeoJSON 文件路径。

    返回值格式：
    - `dict[str, Any]`
      GeoJSON 反序列化后的 Python 字典对象。

    异常说明：
    - 若文件不存在，抛出 `FileNotFoundError`。
    - 若文件内容不是合法 JSON，抛出 `json.JSONDecodeError`。
    """
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def load_spatial_geojson() -> dict[str, dict[str, Any]]:
    """一次性加载算法所需的三份基础空间数据。

    预期功能：
    - 读取路网、建筑、POI 三份 GeoJSON。
    - 供选址算法、调度算法、需求预测算法等直接使用。
    - 使用缓存避免在同一进程中重复读取大文件。

    返回值格式：
    - 返回 `dict[str, dict[str, Any]]`
    - 结构如下：
      - `roads`: `whu_roads.geojson` 的内容
      - `buildings`: `whu_buildings.geojson` 的内容
      - `pois`: `whu_pois.geojson` 的内容

    返回示例：
    ```python
    {
        'roads': {...},
        'buildings': {...},
        'pois': {...},
    }
    ```
    """
    return {
        'roads': _read_geojson(settings.data_dir / 'whu_roads.geojson'),
        'buildings': _read_geojson(settings.data_dir / 'whu_buildings.geojson'),
        'pois': _read_geojson(settings.data_dir / 'whu_pois.geojson'),
    }


@lru_cache(maxsize=1)
def load_roads_geojson() -> dict[str, Any]:
    """加载校园路网 GeoJSON。

    返回值：
    - `dict[str, Any]`
      路网 GeoJSON 数据，通常用于构建路网图、路径规划图或慢行网络分析。
    """
    return _read_geojson(settings.data_dir / 'whu_roads.geojson')


@lru_cache(maxsize=1)
def load_buildings_geojson() -> dict[str, Any]:
    """加载校园建筑 GeoJSON。

    返回值：
    - `dict[str, Any]`
      建筑面要素 GeoJSON 数据，通常用于分析建筑分布、服务覆盖和空间约束。
    """
    return _read_geojson(settings.data_dir / 'whu_buildings.geojson')


@lru_cache(maxsize=1)
def load_pois_geojson() -> dict[str, Any]:
    """加载校园 POI GeoJSON。

    返回值：
    - `dict[str, Any]`
      POI 点要素 GeoJSON 数据，通常用于需求建模、功能区识别和站点候选分析。
    """
    return _read_geojson(settings.data_dir / 'whu_pois.geojson')


def get_data_file_paths() -> dict[str, str]:
    """返回算法层当前使用的数据文件绝对路径。

    预期用途：
    - 调试时确认算法实际读取的是哪几个文件。
    - 后续迁移数据库前，可作为临时排查辅助函数。

    返回值格式：
    - `dict[str, str]`
    - 键包括：`roads`、`buildings`、`pois`
    """
    return {
        'roads': str(settings.data_dir / 'whu_roads.geojson'),
        'buildings': str(settings.data_dir / 'whu_buildings.geojson'),
        'pois': str(settings.data_dir / 'whu_pois.geojson'),
    }
