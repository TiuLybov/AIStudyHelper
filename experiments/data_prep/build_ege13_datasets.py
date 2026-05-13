import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Iterable

import xlrd


""" 
Позволяет строить обучающие датасеты для задач ЕГЭ по информатике
Строит из word методических материалов
"""


def read_doc_text(doc_path: Path) -> str:
    suffix = doc_path.suffix.lower()
    if suffix == ".txt":
        return doc_path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        from docx import Document  # type: ignore

        document = Document(str(doc_path))
        return "\n".join([p.text for p in document.paragraphs])
    if suffix == ".doc":
        try:
            import win32com.client  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Для .doc требуется pywin32 + установленный MS Word, "
                "или заранее сохраните файл как .docx/.txt."
            ) from exc

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_txt = Path(tmp_dir) / "source.txt"
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            try:
                doc = word.Documents.Open(str(doc_path))
                doc.SaveAs(str(tmp_txt), FileFormat=2)
                doc.Close()
            finally:
                word.Quit()
            raw = tmp_txt.read_bytes()
            for enc in ("utf-8", "cp1251", "windows-1251", "cp866", "latin-1"):
                try:
                    return raw.decode(enc)
                except Exception:
                    continue
            return raw.decode("utf-8", errors="ignore")

    raise RuntimeError(f"Unsupported file format: {doc_path.suffix}")


def normalize_ws(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_theory_and_task_block(full_text: str) -> tuple[str, str]:
    marker = re.search(r"(?im)^\s*(?:задани[ея]|тренировочн\w*\s+задани\w*)", full_text)
    if marker:
        return full_text[: marker.start()].strip(), full_text[marker.start() :].strip()

    first_task = re.search(r"(?m)^\s*(?:№\s*)?\d{1,3}[\)\.\:]\s+", full_text)
    if first_task:
        return full_text[: first_task.start()].strip(), full_text[first_task.start() :].strip()

    return full_text.strip(), ""


def parse_tasks(task_text: str, subject_prefix: str = "13") -> list[dict]:
    lines = task_text.splitlines()
    task_starts: list[tuple[int, str]] = []
    pattern = re.compile(r"^\s*(?:№\s*)?(\d{1,3}|P-\d{1,3})\)\s*(.*)$", flags=re.IGNORECASE)
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            task_starts.append((i, m.group(1)))

    tasks_by_id: dict[str, dict] = {}
    for idx, (start_i, task_num) in enumerate(task_starts):
        end_i = task_starts[idx + 1][0] if idx + 1 < len(task_starts) else len(lines)
        chunk = "\n".join(lines[start_i:end_i]).strip()
        chunk = normalize_ws(chunk)
        chunk_l = chunk.lower()
        task_cues = [
            "ip",
            "tcp",
            "в ответе",
            "определите",
            "найдите",
            "восстановите",
            "адрес",
            "маск",
            "сколько",
            "чему равно",
        ]
        if not any(cue in chunk_l for cue in task_cues):
            continue
        task_id = f"{subject_prefix}_{task_num}"
        row = {"id": task_id, "task_num": str(task_num), "question": chunk}
        prev = tasks_by_id.get(task_id)
        if prev is None or len(row["question"]) > len(prev["question"]):
            tasks_by_id[task_id] = row
    def task_sort_key(task_id: str) -> tuple[int, str]:
        suffix = task_id.split("_", maxsplit=1)[1]
        if suffix.isdigit():
            return (0, f"{int(suffix):06d}")
        return (1, suffix)

    return [tasks_by_id[k] for k in sorted(tasks_by_id.keys(), key=task_sort_key)]


def parse_answers_xls(xls_path: Path, subject_prefix: str = "13") -> dict[str, str]:
    wb = xlrd.open_workbook(str(xls_path))
    answers: dict[str, str] = {}
    sheet = wb.sheet_by_index(0)

    target_col = None
    for col in range(sheet.ncols):
        header = str(sheet.cell_value(0, col)).strip()
        header = re.sub(r"\.0$", "", header)
        if header == subject_prefix:
            target_col = col
            break
    if target_col is None:
        return answers

    for row in range(1, sheet.nrows):
        variant_raw = str(sheet.cell_value(row, 0)).strip()
        variant_raw = re.sub(r"\.0$", "", variant_raw)
        if not re.fullmatch(r"\d{1,4}", variant_raw):
            continue

        answer = str(sheet.cell_value(row, target_col)).strip()
        answer = re.sub(r"\.0$", "", answer)
        answer = answer.replace("\r", "\n")
        answer = re.sub(r"https?://\S+", "", answer)
        answer = [part.strip() for part in answer.split("\n") if part.strip()]
        answer = answer[0] if answer else ""
        if not answer:
            continue
        answers[f"{subject_prefix}_{variant_raw}"] = answer

    return answers


def read_solution_files(solutions_dir: Path, subject_prefix: str = "13") -> dict[str, dict]:
    result: dict[str, dict] = {}
    pattern = re.compile(rf"^{re.escape(subject_prefix)}-(\d{{1,3}}|P-\d{{1,3}})\.(py|cpp|pas)$", flags=re.IGNORECASE)

    for path in sorted(solutions_dir.glob("*")):
        if not path.is_file():
            continue
        m = pattern.match(path.name)
        if not m:
            continue
        task_num = m.group(1)
        task_id = f"{subject_prefix}_{task_num}"
        result[task_id] = {
            "path": str(path),
            "language": path.suffix.lstrip(".").lower(),
            "code": path.read_text(encoding="utf-8", errors="ignore"),
        }
    return result


def chunk_theory(theory_text: str, max_chars: int = 900) -> list[str]:
    paragraphs = [p.strip() for p in theory_text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if not current:
            current = p
            continue
        if len(current) + 2 + len(p) <= max_chars:
            current += "\n\n" + p
        else:
            chunks.append(current)
            current = p
    if current:
        chunks.append(current)
    return chunks


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def fallback_question(task_id: str, solution: dict | None) -> str:
    if solution:
        code = solution.get("code", "")
        lines = [ln.strip() for ln in code.splitlines() if ln.strip()]
        comment_lines = [ln for ln in lines[:40] if ln.startswith("#")]
        if comment_lines:
            return " ".join([ln.lstrip("#").strip() for ln in comment_lines[:3]]).strip()
    return f"Задача {task_id}. Текст задачи не удалось извлечь автоматически из документа."


def build_attachment_index(attachments_dir: Path | None) -> dict[str, Path]:
    if attachments_dir is None or not attachments_dir.exists():
        return {}
    index: dict[str, Path] = {}
    for path in attachments_dir.glob("*"):
        if path.is_file():
            index[path.name.lower()] = path
    return index


def detect_attachment_path(
    question: str,
    task_num: str,
    subject_prefix: str,
    attachment_index: dict[str, Path],
) -> str | None:
    if not attachment_index:
        return None

    mentioned = re.findall(r"([A-Za-zА-Яа-я0-9_-]+\.(?:txt|csv|tsv|dat|xls|xlsx|json|xml))", question)
    for filename in mentioned:
        p = attachment_index.get(filename.lower())
        if p:
            return str(p)

    if not re.search(r"в\s+файл|из\s+файл|файле", question.lower()):
        return None

    fallback_names = [f"{subject_prefix}-{task_num}.txt", f"{subject_prefix}_{task_num}.txt"]
    for name in fallback_names:
        p = attachment_index.get(name.lower())
        if p:
            return str(p)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build EGE-13 datasets from doc/xls/solutions")
    parser.add_argument("--doc-path", required=True, help="Path to ege13.doc or .docx/.txt")
    parser.add_argument("--answers-xls", required=True, help="Path to answers.xls")
    parser.add_argument("--solutions-dir", required=True, help="Path to folder with your code solutions")
    parser.add_argument("--output-dir", default="datasets/generated", help="Output dataset directory")
    parser.add_argument("--subject-prefix", default="13", help="Subject/task prefix (default: 13)")
    parser.add_argument("--attachments-dir", default="", help="Optional directory with task data files")
    args = parser.parse_args()

    doc_path = Path(args.doc_path)
    answers_xls = Path(args.answers_xls)
    solutions_dir = Path(args.solutions_dir)
    output_dir = Path(args.output_dir)
    subject_prefix = args.subject_prefix
    attachments_dir = Path(args.attachments_dir) if args.attachments_dir else None
    attachment_index = build_attachment_index(attachments_dir)

    full_text = normalize_ws(read_doc_text(doc_path))
    theory_text, task_block = split_theory_and_task_block(full_text)
    tasks = parse_tasks(task_block, subject_prefix=subject_prefix)
    answers = parse_answers_xls(answers_xls, subject_prefix=subject_prefix)
    solutions = read_solution_files(solutions_dir, subject_prefix=subject_prefix)
    task_by_id = {t["id"]: t for t in tasks}

    benchmark_rows = []
    finetune_rows = []
    missing_task_text_ids: list[str] = []

    def sort_key(task_id: str) -> tuple[int, str]:
        suffix = task_id.split("_", maxsplit=1)[1]
        if suffix.isdigit():
            return (0, f"{int(suffix):06d}")
        return (1, suffix)

    for task_id in sorted(answers.keys(), key=sort_key):
        answer = answers[task_id]
        task = task_by_id.get(task_id)
        solution = solutions.get(task_id)
        if task:
            question = task["question"]
            task_num = task["task_num"]
            question_source = "doc"
        else:
            question = fallback_question(task_id, solution)
            task_num = task_id.split("_", maxsplit=1)[1]
            question_source = "fallback"
            missing_task_text_ids.append(task_id)

        attachment_path = detect_attachment_path(
            question=question,
            task_num=task_num,
            subject_prefix=subject_prefix,
            attachment_index=attachment_index,
        )

        benchmark_rows.append(
            {
                "id": task_id,
                "question": question,
                "answer": answer,
                "meta": {"task_num": task_num, "source": str(doc_path), "question_source": question_source},
                **({"attachment_path": attachment_path} if attachment_path else {}),
            }
        )

        if solution:
            user_text = question
            if attachment_path:
                user_text += f"\n\nДля решения используй данные из файла: {Path(attachment_path).name}"
            finetune_rows.append(
                {
                    "task_id": task_id,
                    **({"attachment_path": attachment_path} if attachment_path else {}),
                    "subject": f"ege_{subject_prefix}",
                    "messages": [
                        {"role": "system", "content": "Ты обучающий ассистент: объясняй ход решения и заверши строкой 'Ответ: ...'."},
                        {"role": "user", "content": user_text},
                        {
                            "role": "assistant",
                            "content": (
                                "Решение через программу:\n"
                                f"```{solution['language']}\n{solution['code']}\n```\n"
                                "Краткая интерпретация: программа перебирает/проверяет условия задачи.\n"
                                f"Ответ: {answer}"
                            ),
                        },
                    ],
                }
            )

    rag_rows = []
    for i, chunk in enumerate(chunk_theory(theory_text), start=1):
        rag_rows.append(
            {
                "id": f"{subject_prefix}_theory_{i:03d}",
                "source": f"ege{subject_prefix}_theory",
                "text": chunk,
            }
        )

    benchmark_path = output_dir / f"ege{subject_prefix}_benchmark.jsonl"
    finetune_path = output_dir / f"ege{subject_prefix}_finetune.jsonl"
    rag_path = output_dir / f"ege{subject_prefix}_rag_kb.jsonl"
    report_path = output_dir / f"ege{subject_prefix}_build_report.json"

    write_jsonl(benchmark_path, benchmark_rows)
    write_jsonl(finetune_path, finetune_rows)
    write_jsonl(rag_path, rag_rows)

    report = {
        "doc_path": str(doc_path),
        "answers_xls": str(answers_xls),
        "solutions_dir": str(solutions_dir),
        "parsed_tasks_total": len(tasks),
        "answers_total": len(answers),
        "solutions_total": len(solutions),
        "benchmark_rows": len(benchmark_rows),
        "finetune_rows": len(finetune_rows),
        "rag_rows": len(rag_rows),
        "missing_task_text_count": len(missing_task_text_ids),
        "missing_task_text_ids_preview": missing_task_text_ids[:30],
        "attachments_dir": str(attachments_dir) if attachments_dir else "",
        "benchmark_with_attachments": sum(1 for r in benchmark_rows if "attachment_path" in r),
        "finetune_with_attachments": sum(1 for r in finetune_rows if "attachment_path" in r),
        "outputs": {
            "benchmark": str(benchmark_path),
            "finetune": str(finetune_path),
            "rag": str(rag_path),
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
