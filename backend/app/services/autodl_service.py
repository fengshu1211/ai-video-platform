"""AutoDL GPU算力云 API — 弹性部署管理"""
import httpx
from app.config import AUTODL_TOKEN, AUTODL_API_BASE


def _headers():
    return {"Authorization": AUTODL_TOKEN}


def list_deployments() -> list[dict]:
    """查询已有部署"""
    r = httpx.post(f"{AUTODL_API_BASE}/api/v1/dev/deployment/container/list",
                   headers=_headers(), json={}, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data.get("data", {}).get("list", [])


def create_deployment(name: str, image_uuid: str, gpu_name: str = "RTX3060",
                      gpu_num: int = 1, cpu_num: int = 4, memory_gb: int = 16,
                      cmd: str = "", price_max: float = 0.5) -> dict | None:
    """创建GPU部署"""
    body = {
        "name": name,
        "deployment_type": "Container",
        "container_template": {
            "image_uuid": image_uuid,
            "gpu_name_set": [gpu_name],
            "gpu_num": gpu_num,
            "cpu_num_from": cpu_num,
            "cpu_num_to": cpu_num + 2,
            "memory_size_from": memory_gb,
            "memory_size_to": memory_gb + 8,
            "price_from": 0,
            "price_to": int(price_max * 1000),
            "cmd": cmd,
        }
    }
    r = httpx.post(f"{AUTODL_API_BASE}/api/v1/dev/deployment",
                   headers={**_headers(), "Content-Type": "application/json"},
                   json=body, timeout=30)
    if r.status_code == 200:
        return r.json().get("data", {})
    return None


def stop_deployment(deployment_uuid: str) -> bool:
    """停止/释放部署"""
    r = httpx.post(f"{AUTODL_API_BASE}/api/v1/dev/deployment/{deployment_uuid}/stop",
                   headers=_headers(), timeout=10)
    return r.status_code == 200


def get_container_info(deployment_uuid: str) -> dict | None:
    """获取容器信息（含SSH连接地址）"""
    r = httpx.post(f"{AUTODL_API_BASE}/api/v1/dev/deployment/container/list",
                   headers=_headers(),
                   json={"deployment_uuid": deployment_uuid}, timeout=10)
    data = r.json().get("data", {}).get("list", [])
    return data[0] if data else None
