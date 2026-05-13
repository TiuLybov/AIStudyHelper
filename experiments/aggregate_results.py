import argparse
import json
from pathlib import Path


def read_predictions(path: Path) -> tuple[int, int]:
    total = 0
    correct = 0
    if not path.exists():
        return total, correct
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            total += 1
            correct += int(bool(row.get("is_correct", False)))
    return total, correct


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results", help="Directory with *_predictions.jsonl files")
    parser.add_argument("--output", default="results/summary.json", help="Summary output json")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    files = sorted(results_dir.glob("*_predictions.jsonl"))
    summary = []
    for f in files:
        total, correct = read_predictions(f)
        acc = correct / total if total else 0.0
        summary.append({"experiment": f.stem.replace("_predictions", ""), "total": total, "correct": correct, "accuracy": acc})

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Experiment summary:")
    for row in summary:
        print(f"- {row['experiment']}: accuracy={row['accuracy']:.4f} ({row['correct']}/{row['total']})")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
