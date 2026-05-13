# Подготовка датасетов из `ege13.doc`, `answers.xls`, `13solve`

Скрипт `build_ege13_datasets.py` собирает три набора:

- `ege13_benchmark.jsonl` — задачи + эталонные ответы для оценки accuracy.
- `ege13_finetune.jsonl` — диалоги `messages` для дообучения.
- `ege13_rag_kb.jsonl` — чанки теории для RAG.

## Запуск

```bash
python data_prep/build_ege13_datasets.py \
  --doc-path "C:\Users\n.tiunov\Downloads\ege13.doc" \
  --answers-xls "C:\Users\n.tiunov\Downloads\answers.xls" \
  --solutions-dir "C:\Users\n.tiunov\Downloads\13solve" \
  --output-dir "datasets/generated"
```

Если в задачах используются внешние файлы (например, `17data`, `24data`), добавь:

```bash
--attachments-dir "C:\Users\n.tiunov\Downloads\17data"
```

## Что важно по формату

- Для `.doc` нужен установленный Microsoft Word (используется COM через `pywin32`).
- Если Word недоступен, сохрани `ege13.doc` как `.docx` или `.txt` и передай этот путь.
- Ответы в `answers.xls` ожидаются в строках как `номер | ответ` (первые 2 непустые ячейки).
- Номера решений читаются из имен файлов: `13-127.py`, `13-194.cpp`, `13-P-13.py`.

## Проверка результата

После запуска создается отчет `ege13_build_report.json` с покрытием:

- сколько задач найдено в документе;
- сколько ответов прочитано из xls;
- сколько решений найдено в папке;
- сколько строк удалось собрать для benchmark/finetune/rag.
- сколько строк получили `attachment_path`.
