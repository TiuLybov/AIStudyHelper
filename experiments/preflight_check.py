import argparse
import json
from pathlib import Path

import requests
import yaml


def check_file(path: Path) -> dict:
    return {"path": str(path), "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0}


def check_health(url: str) -> dict:
    try:
        r = requests.get(url, timeout=5)
        return {"url": url, "ok": r.status_code == 200, "status_code": r.status_code, "body": r.text[:200]}
    except Exception as exc:
        return {"url": url, "ok": False, "error": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick preflight checks before running experiments.")
    parser.add_argument("--config-dir", default="configs/smoke", help="Directory with experiment configs")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    cfg_paths = sorted(config_dir.glob("*.yaml"))
    report = {"config_dir": str(config_dir), "configs": [], "dataset_files": [], "health": []}

    backend_url = None
    for cfg_path in cfg_paths:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        report["configs"].append(check_file(cfg_path))
        dataset_path = (Path(".") / cfg["dataset_path"]).resolve()
        report["dataset_files"].append(check_file(dataset_path))
        if backend_url is None:
            backend_url = cfg["backend_url"]

    report["dataset_files"].append(check_file((Path("rag") / "knowledge_base.jsonl").resolve()))

    if backend_url:
        report["health"].append(check_health(f"{backend_url}/health"))
        report["health"].append(check_health("http://localhost:8010/health"))

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
