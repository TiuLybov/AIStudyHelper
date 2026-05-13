import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all model-variant experiments sequentially.")
    parser.add_argument("--config-dir", default="configs/all_subjects", help="Directory with experiment yaml configs")
    parser.add_argument("--max-samples", type=int, default=0, help="Optional sample cap per experiment")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    configs = [
        config_dir / "baseline_gpt.yaml",
        config_dir / "prompted_gpt.yaml",
        config_dir / "rag_gpt.yaml",
        config_dir / "finetuned_oss.yaml",
    ]

    for cfg in configs:
        if not cfg.exists():
            raise FileNotFoundError(f"Missing config: {cfg}")
        cmd = [sys.executable, "run_benchmark.py", "--config", str(cfg)]
        if args.max_samples > 0:
            cmd.extend(["--max-samples", str(args.max_samples)])
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    print("All experiments finished.")


if __name__ == "__main__":
    main()
