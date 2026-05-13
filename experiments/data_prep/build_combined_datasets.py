import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build combined benchmark/finetune/rag datasets from generated EGE files.")
    parser.add_argument("--generated-dir", default="datasets/generated", help="Directory with ege*_*.jsonl files")
    parser.add_argument("--output-prefix", default="ege_all", help="Combined output prefix")
    args = parser.parse_args()

    generated_dir = Path(args.generated_dir)
    prefix = args.output_prefix

    bench_files = sorted(generated_dir.glob("ege*_benchmark.jsonl"))
    finetune_files = sorted(generated_dir.glob("ege*_finetune.jsonl"))
    rag_files = sorted(generated_dir.glob("ege*_rag_kb.jsonl"))

    benchmark_rows: list[dict] = []
    finetune_rows: list[dict] = []
    rag_rows: list[dict] = []

    seen_bench_ids = set()
    seen_ft_ids = set()
    seen_rag_ids = set()

    for p in bench_files:
        for row in load_jsonl(p):
            rid = row.get("id")
            if rid in seen_bench_ids:
                continue
            seen_bench_ids.add(rid)
            benchmark_rows.append(row)

    for p in finetune_files:
        for row in load_jsonl(p):
            rid = row.get("task_id")
            if rid in seen_ft_ids:
                continue
            seen_ft_ids.add(rid)
            finetune_rows.append(row)

    for p in rag_files:
        for row in load_jsonl(p):
            rid = row.get("id")
            if rid in seen_rag_ids:
                continue
            seen_rag_ids.add(rid)
            rag_rows.append(row)

    benchmark_rows.sort(key=lambda x: str(x.get("id", "")))
    finetune_rows.sort(key=lambda x: str(x.get("task_id", "")))
    rag_rows.sort(key=lambda x: str(x.get("id", "")))

    out_bench = generated_dir / f"{prefix}_benchmark.jsonl"
    out_ft = generated_dir / f"{prefix}_finetune.jsonl"
    out_rag = generated_dir / f"{prefix}_rag_kb.jsonl"
    out_report = generated_dir / f"{prefix}_build_report.json"

    write_jsonl(out_bench, benchmark_rows)
    write_jsonl(out_ft, finetune_rows)
    write_jsonl(out_rag, rag_rows)

    report = {
        "sources": {
            "benchmark_files": [str(p) for p in bench_files],
            "finetune_files": [str(p) for p in finetune_files],
            "rag_files": [str(p) for p in rag_files],
        },
        "rows": {
            "benchmark": len(benchmark_rows),
            "finetune": len(finetune_rows),
            "rag": len(rag_rows),
        },
        "outputs": {"benchmark": str(out_bench), "finetune": str(out_ft), "rag": str(out_rag)},
    }
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
