import json
import os
import tempfile
import threading
from pathlib import Path

from django.conf import settings


class StorageService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._initialized_dir = None

    def _base_dir(self) -> Path:
        return Path(settings.DATA_DIR)

    def ensure_initialized(self) -> None:
        base_dir = self._base_dir()
        if self._initialized_dir == base_dir:
            return
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "journals").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "lists").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "snapshots").mkdir(parents=True, exist_ok=True)

        self._initialized_dir = base_dir

        if not (self.base_dir / "accounts.json").exists():
            self._write_atomic(
                self.base_dir / "accounts.json",
                [
                    {
                        "id": "general",
                        "name": "通用账户",
                        "type": "asset",
                        "status": "active",
                        "currency": "CNY",
                    },
                    {
                        "id": "cash",
                        "name": "现金",
                        "type": "asset",
                        "status": "active",
                        "currency": "CNY",
                    },
                    {
                        "id": "wechat",
                        "name": "微信",
                        "type": "asset",
                        "status": "active",
                        "currency": "CNY",
                    },
                    {
                        "id": "alipay",
                        "name": "支付宝",
                        "type": "asset",
                        "status": "active",
                        "currency": "CNY",
                    },
                    {
                        "id": "boc",
                        "name": "中国银行",
                        "type": "asset",
                        "status": "active",
                        "currency": "CNY",
                    },
                    {
                        "id": "cmb",
                        "name": "招商银行",
                        "type": "asset",
                        "status": "active",
                        "currency": "CNY",
                    },
                    {
                        "id": "expense",
                        "name": "费用汇总",
                        "type": "expense",
                        "status": "active",
                        "currency": "CNY",
                    },
                    {
                        "id": "income",
                        "name": "收入汇总",
                        "type": "income",
                        "status": "active",
                        "currency": "CNY",
                    },
                ],
            )

        if not (self.base_dir / "categories.json").exists():
            self._write_atomic(
                self.base_dir / "categories.json",
                [
                    {
                        "id": "food",
                        "name": "餐饮",
                        "group": "必要",
                        "budget_monthly": 2000,
                    },
                    {
                        "id": "transport",
                        "name": "交通",
                        "group": "必要",
                        "budget_monthly": 800,
                    },
                    {
                        "id": "shopping",
                        "name": "购物",
                        "group": "可选",
                        "budget_monthly": 1500,
                    },
                    {
                        "id": "housing",
                        "name": "住房",
                        "group": "必要",
                        "budget_monthly": 4000,
                    },
                    {
                        "id": "entertainment",
                        "name": "娱乐",
                        "group": "可选",
                        "budget_monthly": 1000,
                    },
                ],
            )

        if not (self.base_dir / "lists" / "shopping.json").exists():
            self._write_atomic(self.base_dir / "lists" / "shopping.json", [])

    def _full_path(self, relative_path: str) -> Path:
        self.ensure_initialized()
        path = self.base_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def load_json(self, relative_path: str, default=None):
        path = self._full_path(relative_path)
        if not path.exists():
            return [] if default is None else default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, relative_path: str, data) -> None:
        path = self._full_path(relative_path)
        with self._lock:
            self._write_atomic(path, data)

    def _write_atomic(self, path: Path, data) -> None:
        with tempfile.NamedTemporaryFile(
            "w", delete=False, encoding="utf-8", dir=path.parent, suffix=".tmp"
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, path)


storage_service = StorageService()
