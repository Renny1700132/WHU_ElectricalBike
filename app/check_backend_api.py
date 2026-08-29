from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def check(name: str, method: str, path: str, json_body: dict | None = None) -> None:
    """执行一次接口检查并在终端打印结果。

    参数：
    - name: 当前检查项名称。
    - method: HTTP 方法，仅支持 GET、POST、DELETE。
    - path: 请求路径。
    - json_body: POST 请求体，默认不传。
    """
    if method == 'GET':
        response = client.get(path)
    elif method == 'POST':
        response = client.post(path, json=json_body)
    elif method == 'DELETE':
        response = client.delete(path)
    else:
        raise ValueError(f'Unsupported method: {method}')

    print(f'[{response.status_code}] {name}: {method} {path}')
    if response.headers.get('content-type', '').startswith('application/json'):
        data = response.json()
        if isinstance(data, dict):
            print('  keys =', list(data.keys())[:10])
    if response.status_code >= 400:
        raise SystemExit(1)


def main() -> None:
    """执行后端基础接口冒烟测试。"""
    check('health', 'GET', '/health')
    check('base-data', 'GET', '/api/campus/base-data')
    check('heatmap', 'GET', '/api/demand/heatmap?period=morning')

    response = client.post(
        '/api/siting/optimize',
        json={
            'algorithm_type': 'GA',
            'target_sites_count': 3,
            'service_radius': 120,
            'include_process': True,
        },
    )
    print(f"[{response.status_code}] siting-optimize: POST /api/siting/optimize")
    run_id = response.json().get('run_id')
    if run_id:
        check('process-detail', 'GET', f'/api/algorithms/runs/{run_id}')
        check('process-states', 'GET', f'/api/algorithms/runs/{run_id}/states')
        check('process-state-detail', 'GET', f'/api/algorithms/runs/{run_id}/states/1')

    check('dispatch-status', 'GET', '/api/dispatch/status?period=noon')
    check('dispatch-optimize', 'POST', '/api/dispatch/optimize', {'period': 'evening', 'algorithm_type': 'ACO', 'include_process': True})
    check('analysis', 'GET', '/api/analysis/metrics')

    scheme_response = client.post(
        '/api/schemes',
        json={
            'name': 'smoke-test-scheme',
            'scheme_type': 'siting',
            'description': 'temporary smoke test',
            'scheme_data': {'ok': True},
        },
    )
    scheme_id = scheme_response.json()['item']['scheme_id']
    print(f"[{scheme_response.status_code}] save-scheme: POST /api/schemes")
    check('scheme-list', 'GET', '/api/schemes')
    check('scheme-detail', 'GET', f'/api/schemes/{scheme_id}')
    check('scheme-delete', 'DELETE', f'/api/schemes/{scheme_id}')
    check('export', 'POST', '/api/export/scheme', {'scheme_data': {'name': 'demo'}, 'file_format': 'csv', 'file_name': 'demo'})
    check('backend-page', 'GET', '/backend')
    check('backend-logs', 'GET', '/backend/logs')
    print('All backend smoke tests passed.')


if __name__ == '__main__':
    main()

