from __future__ import annotations

from typing import Any, Protocol


class AlgorithmResult(Protocol):
    """算法模块统一返回约定。

    作用：
    - 约束未来所有算法入口函数的基本返回形式。
    - 提醒实现者：算法层返回的是“可直接交给接口层序列化”的字典结构。

    预期返回：
    - `dict[str, Any]`
    - 字段内容应与对应 API 的响应模型一致。

    例如：
    - 选址算法应返回与 `SitingOptimizeResponse` 兼容的数据。
    - 调度算法应返回与 `DispatchOptimizeResponse` 兼容的数据。
    - 如果启用了过程可视化，还应补充 `run_id`、`process_summary` 等字段，
      或者将中间状态写入统一的过程接口仓库中。
    """

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...
