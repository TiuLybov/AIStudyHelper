# Воспроизводимые эксперименты

Цель: сравнить 4 режима по метрике `accuracy` (доля задач, где финальный ответ совпал с эталоном).

## Структура

- `configs/` — YAML-конфиги для каждого режима.
- `datasets/tasks.jsonl` — набор задач вида:
  - `id`
  - `question`
  - `answer` (эталон)
  - `attachment_path` (опционально, относительный путь до файла)
- `prompts/tutor_system.txt` — обучающий системный промпт.
- `run_benchmark.py` — запуск эксперимента и подсчет метрик.
- `data_prep/` — скрипты подготовки датасетов из исходников (`doc/xls/solutions`).
- `results/` — результаты прогонов.
- `rag/` — файлы для базы знаний RAG.
- `finetune/` — рекомендации и шаблоны для дообучения.

## Пример запуска

```bash
python run_benchmark.py --config configs/baseline_gpt.yaml
python run_benchmark.py --config configs/prompted_gpt.yaml
python run_benchmark.py --config configs/rag_gpt.yaml
python run_benchmark.py --config configs/finetuned_oss.yaml
python aggregate_results.py --results-dir results --output results/summary.json
```

## Запуск на всех собранных EGE датасетах

1. Собрать объединенные датасеты:

```bash
python data_prep/build_combined_datasets.py --generated-dir datasets/generated --output-prefix ege_all
```

2. Обновить базу знаний для RAG:

```bash
copy datasets\generated\ege_all_rag_kb.jsonl rag\knowledge_base.jsonl
```

3. Быстрая проверка пайплайна (20 задач на режим):

```bash
python run_all_experiments.py --config-dir configs/smoke
python aggregate_results.py --results-dir results/smoke --output results/smoke/summary.json
```

4. Полный прогон (все задачи):

```bash
python run_all_experiments.py --config-dir configs/all_subjects
python aggregate_results.py --results-dir results/all_subjects --output results/all_subjects/summary.json
```

`run_benchmark.py` поддерживает `--max-samples`, если нужен кастомный лимит.

5. Рандомная выборка 200 задач из всех предметов (стратифицированно):

```bash
python run_all_experiments.py --config-dir configs/random200
python aggregate_results.py --results-dir results/random200 --output results/random200/summary.json
```

В `run_benchmark.py` есть поддержка:
- `sample_random` + `random_seed` — случайная выборка;
- `stratified_by_subject` — чтобы в выборке были задачи всех типов/предметов;
- `enable_code_exec` — если модель вернула Python-код для задач с файлами, скрипт попытается выполнить код и использовать его вывод как кандидат-ответ.

Подготовка датасета из твоих файлов:

```bash
python data_prep/build_ege13_datasets.py --doc-path "C:\Users\n.tiunov\Downloads\ege13.doc" --answers-xls "C:\Users\n.tiunov\Downloads\answers.xls" --solutions-dir "C:\Users\n.tiunov\Downloads\13solve" --output-dir "datasets/generated"
```
