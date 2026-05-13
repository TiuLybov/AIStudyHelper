import argparse
import json
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import requests
import yaml
from tqdm import tqdm


def subject_of(item_id: str) -> str:
    return item_id.split("_", maxsplit=1)[0]


def normalize_answer(text: str) -> str:
    text = text.strip().lower().replace("ё", "е")
    text = re.sub(r"^\s*ответ\s*[:\-]?\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("\\n", " ").replace("\n", " ")
    text = re.sub(r"[^0-9a-zа-я\-\+\s]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_compact(text: str) -> str:
    return normalize_answer(text).replace(" ", "")


def split_gold_variants(gold: str) -> list[str]:
    raw = gold.strip()
    if not raw:
        return []
    variants = [v.strip() for v in raw.split(",") if v.strip()]
    return variants or [raw]


def answers_match(candidate: str, gold: str, subject: str) -> bool:
    cand_n = normalize_answer(candidate)
    cand_c = normalize_compact(candidate)
    if not cand_n:
        return False

    for gold_variant in split_gold_variants(gold):
        gold_n = normalize_answer(gold_variant)
        gold_c = normalize_compact(gold_variant)
        if not gold_n:
            continue
        if cand_n == gold_n or cand_c == gold_c:
            return True

        if re.search(rf"(^|\s){re.escape(gold_n)}($|\s)", cand_n):
            return True

        if subject == "13" and gold_c.isalpha() and cand_c == gold_c:
            return True

    return False


def extract_final_answer(text: str) -> str:
    text_wo_code = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    matches = re.findall(r"ответ\s*:\s*(.+)$", text_wo_code, flags=re.IGNORECASE | re.MULTILINE)
    if matches:
        return matches[-1].strip()
    return text.strip()


def make_eval_question(question: str) -> str:
    return (
        question.strip()
        + "\n\nВажно: верни только финальный ответ без пояснений. Формат: Ответ: <значение>. "
        + "Если для ответа нужно вычисление по файлу, можешь дать Python-код в ```python```, "
        + "который печатает только финальный ответ. "
        + "После кода обязательно продублируй финальный ответ отдельной строкой 'Ответ: ...'."
    )


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def ask_model_with_question(
    base_url: str,
    endpoint: str,
    model_variant: str,
    question: str,
    attachment_path: str | None,
    root_dir: Path,
) -> dict:
    eval_question = make_eval_question(question)
    if attachment_path:
        abs_attachment = root_dir / attachment_path
        with abs_attachment.open("rb") as fh:
            files = [("files", (abs_attachment.name, fh, "application/octet-stream"))]
            data = {"question": eval_question, "model_variant": model_variant}
            response = requests.post(f"{base_url}/ask-file", data=data, files=files, timeout=120)
    else:
        payload = {"question": eval_question, "model_variant": model_variant}
        response = requests.post(f"{base_url}{endpoint}", json=payload, timeout=120)

    response.raise_for_status()
    return response.json()


def ask_model(base_url: str, endpoint: str, model_variant: str, item: dict, root_dir: Path) -> dict:
    return ask_model_with_question(
        base_url=base_url,
        endpoint=endpoint,
        model_variant=model_variant,
        question=item["question"],
        attachment_path=item.get("attachment_path"),
        root_dir=root_dir,
    )


def is_malformed_final_answer(final_answer: str) -> bool:
    t = final_answer.strip()
    if not t:
        return True
    if len(t) > 120:
        return True
    if re.search(r"\b(решение|шаг|поясн|нужно|сначала|далее)\b", t, flags=re.IGNORECASE):
        return True
    return False


def make_code_first_question(question: str) -> str:
    return (
        question.strip()
        + "\n\nСначала дай Python-код в ```python```, который решает задачу и печатает финальный ответ. "
        + "После кода дай ровно одну строку: Ответ: <значение>"
    )


def should_use_code_first(item: dict, code_first_subjects: set[str]) -> bool:
    if item.get("attachment_path"):
        return True
    return subject_of(item["id"]) in code_first_subjects


def extract_python_code(text: str) -> str | None:
    matches = re.findall(r"```python\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    return matches[-1].strip()


def extract_file_mentions(question: str) -> list[str]:
    return re.findall(r"([A-Za-zА-Яа-я0-9_-]+\.(?:txt|csv|tsv|dat|json))", question)


def build_attachment_lookup(search_dirs: list[str], base_dir: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for d in search_dirs:
        p = Path(d)
        if not p.is_absolute():
            p = (base_dir / p).resolve()
        if not p.exists() or not p.is_dir():
            continue
        for child in p.glob("*"):
            if child.is_file():
                lookup.setdefault(child.name.lower(), str(child))
    return lookup


def resolve_attachment_path(item: dict, lookup: dict[str, str]) -> str | None:
    if item.get("attachment_path"):
        return str(item["attachment_path"])
    for filename in extract_file_mentions(item.get("question", "")):
        hit = lookup.get(filename.lower())
        if hit:
            return hit
    return None


def run_python_code_with_attachment(code: str, attachment_path: str, question: str) -> tuple[str | None, str]:
    src = Path(attachment_path)
    if not src.exists():
        return None, "attachment_not_found"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        main_name = src.name
        shutil.copy2(src, tmp_dir / main_name)

        for mentioned in extract_file_mentions(question):
            target = tmp_dir / mentioned
            if target.name != main_name and not target.exists():
                shutil.copy2(src, target)

        runner = tmp_dir / "runner.py"
        runner.write_text(code, encoding="utf-8")

        try:
            proc = subprocess.run(
                ["python", str(runner)],
                cwd=str(tmp_dir),
                capture_output=True,
                text=True,
                timeout=12,
            )
        except subprocess.TimeoutExpired:
            return None, "timeout"
        except Exception:
            return None, "subprocess_error"
        if proc.returncode != 0:
            return None, (proc.stderr or proc.stdout or "non_zero_exit").strip()[:1200]

        out_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if not out_lines:
            return None, "empty_stdout"
        return out_lines[-1], ""


def sample_dataset(rows: list[dict], limit: int, seed: int, stratified_by_subject: bool) -> list[dict]:
    if limit <= 0 or limit >= len(rows):
        return rows
    rng = random.Random(seed)
    if not stratified_by_subject:
        return rng.sample(rows, limit)

    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(subject_of(row["id"]), []).append(row)
    subjects = sorted(groups.keys())

    selected: list[dict] = []
    for s in subjects:
        selected.append(rng.choice(groups[s]))
    remaining = max(limit - len(selected), 0)
    if remaining == 0:
        return selected[:limit]

    pool: list[dict] = []
    selected_ids = {r["id"] for r in selected}
    for s in subjects:
        pool.extend([r for r in groups[s] if r["id"] not in selected_ids])
    if remaining >= len(pool):
        selected.extend(pool)
        return selected[:limit]
    selected.extend(rng.sample(pool, remaining))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to experiment config")
    parser.add_argument("--max-samples", type=int, default=0, help="Optional cap on dataset size for smoke tests")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    experiments_root = Path(__file__).resolve().parent
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    dataset_path = Path(cfg["dataset_path"])
    if not dataset_path.is_absolute():
        dataset_path = experiments_root / dataset_path
    dataset = load_jsonl(dataset_path)
    if bool(cfg.get("exclude_fallback_questions", True)):
        dataset = [row for row in dataset if row.get("meta", {}).get("question_source") != "fallback"]
    cfg_limit = int(cfg.get("max_samples", 0))
    cli_limit = int(args.max_samples or 0)
    limit = cli_limit if cli_limit > 0 else cfg_limit
    random_seed = int(cfg.get("random_seed", 42))
    sample_random = bool(cfg.get("sample_random", True))
    stratified_by_subject = bool(cfg.get("stratified_by_subject", True))
    if limit > 0:
        if sample_random:
            dataset = sample_dataset(dataset, limit=limit, seed=random_seed, stratified_by_subject=stratified_by_subject)
        else:
            dataset = dataset[:limit]
    predictions = []
    correct = 0
    enable_code_exec = bool(cfg.get("enable_code_exec", True))
    code_first_subjects = set(cfg.get("code_first_subjects", ["14", "16", "17", "23", "24", "25"]))
    code_fix_retries = int(cfg.get("code_fix_retries", 2))
    attachment_lookup = build_attachment_lookup(cfg.get("attachments_search_dirs", []), experiments_root)
    retry_if_malformed = bool(cfg.get("retry_if_malformed", True))
    max_retries = int(cfg.get("max_retries", 1))
    by_subject: dict[str, dict[str, int]] = {}

    for item in tqdm(dataset, desc=f"Running {cfg['name']}"):
        resolved_attachment_path = resolve_attachment_path(item, attachment_lookup)
        item_for_request: dict[str, Any] = dict(item)
        if resolved_attachment_path:
            item_for_request["attachment_path"] = resolved_attachment_path
        if should_use_code_first(item, code_first_subjects):
            item_for_request["question"] = make_code_first_question(item["question"])

        out = ask_model(
            base_url=cfg["backend_url"],
            endpoint=cfg["endpoint"],
            model_variant=cfg["model_variant"],
            item=item_for_request,
            root_dir=experiments_root,
        )
        raw_answer = out["answer"]
        final_answer = extract_final_answer(raw_answer)
        retries_done = 0
        while retry_if_malformed and retries_done < max_retries and is_malformed_final_answer(final_answer):
            retry_item = {
                **item,
                "question": (
                    item["question"].strip()
                    + "\n\nВерни только финальный ответ, строго одной строкой: Ответ: <значение>. "
                    + "Без объяснений и без лишнего текста."
                ),
            }
            out = ask_model(
                base_url=cfg["backend_url"],
                endpoint=cfg["endpoint"],
                model_variant=cfg["model_variant"],
                item=retry_item,
                root_dir=experiments_root,
            )
            raw_answer = out["answer"]
            final_answer = extract_final_answer(raw_answer)
            retries_done += 1
        candidates = [final_answer]
        code_result = None
        if enable_code_exec and resolved_attachment_path:
            code = extract_python_code(raw_answer)
            if code:
                code_result, exec_error = run_python_code_with_attachment(
                    code=code,
                    attachment_path=resolved_attachment_path,
                    question=item["question"],
                )
                fix_attempt = 0
                while not code_result and fix_attempt < code_fix_retries:
                    repair_prompt = (
                        item["question"].strip()
                        + "\n\nИсправь код, чтобы он корректно работал с файлом и печатал только финальный ответ."
                        + "\nОшибка выполнения:\n"
                        + exec_error
                        + "\n\nВерни исправленный код в ```python``` и строку `Ответ: ...`."
                    )
                    repair_out = ask_model_with_question(
                        base_url=cfg["backend_url"],
                        endpoint=cfg["endpoint"],
                        model_variant=cfg["model_variant"],
                        question=repair_prompt,
                        attachment_path=resolved_attachment_path,
                        root_dir=experiments_root,
                    )
                    repair_raw = repair_out["answer"]
                    repair_code = extract_python_code(repair_raw)
                    if not repair_code:
                        break
                    code_result, exec_error = run_python_code_with_attachment(
                        code=repair_code,
                        attachment_path=resolved_attachment_path,
                        question=item["question"],
                    )
                    if code_result:
                        candidates.append(extract_final_answer(repair_raw))
                        raw_answer = repair_raw
                        final_answer = extract_final_answer(raw_answer)
                        out = repair_out
                        break
                    fix_attempt += 1
                if code_result:
                    candidates.append(extract_final_answer(code_result))

        subj = subject_of(item["id"])
        is_correct = any(answers_match(c, item["answer"], subj) for c in candidates if c)
        correct += int(is_correct)
        subj_stat = by_subject.setdefault(subj, {"total": 0, "correct": 0})
        subj_stat["total"] += 1
        subj_stat["correct"] += int(is_correct)

        predictions.append(
            {
                "id": item["id"],
                "question": item["question"],
                "gold_answer": item["answer"],
                "model_answer_raw": raw_answer,
                "model_answer_final": final_answer,
                "model_answer_code_exec": code_result,
                "is_correct": is_correct,
                "subject": subj,
                "metadata": out.get("metadata", {}),
            }
        )

    accuracy = correct / max(len(dataset), 1)
    output_path = Path(cfg["output_path"])
    if not output_path.is_absolute():
        output_path = experiments_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in predictions:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    by_subject_accuracy = {
        k: {
            "total": v["total"],
            "correct": v["correct"],
            "accuracy": (v["correct"] / v["total"]) if v["total"] else 0.0,
        }
        for k, v in sorted(by_subject.items())
    }

    print(
        json.dumps(
            {
                "experiment": cfg["name"],
                "total": len(dataset),
                "correct": correct,
                "accuracy": accuracy,
                "by_subject": by_subject_accuracy,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
