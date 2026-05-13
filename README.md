# ИИ помощник в обучении
## План работы

### Сбор и подготовка данных
 1. Открытые образовательные датасеты
 2. Собственные учебные материалы
 3. Синтетически созданные данные для покрытия редких или сложных случаев
 4. Очистка данных
 5. Разметка данных, если потребуется
 6. Проведение EDA анализа

⸻

### Создание и оценка базовой версии модели

 1. Выбор архитектуры бейслайна
 2. Обучение модели на стандартных задачах: классификация, вопрос–ответ, суммаризация
 3. Проведение серии экспериментов для сравнения архитектурных вариантов
 4. Тестирование на выделенных наборах данных построенных бейслайнов
 5. Формирование списка направлений для улучшения

⸻

### Разработка основной модели

 1. Тонкая настройка модели на большом количестве диалоговых и образовательных инструкций
 2. Разделение данных на предметные области и обучение специализированных компонентов
 3. Формирование предпочтений от фидбэка человека, определяющих качество объяснений
 4. Использование методов RLHF или аналогичных подходов

⸻

### Проверка безопасности
 1. Фильтрация нежелательного контента
 2. Защита от утечек данных
 3. Проверка корректности и нейтральности формулировок

⸻

### Тестирование и валидация
 1. Тестирование логики и стабильности модели
 2. Проверка на стандартных наборах задач
 3. Отработка стресс-тестов
 4. Подключение тестовой группы пользователей
 5. Сбор и анализ обратной связи
 6. Корректировка модели на основе выявленных проблем.
⸻

### Интеграция и развёртывание
 1. Создание чат бота в Telegram
 2. Настройка инфраструктуры: серверы, облачные решения, контейнеризация
 3. Подготовка систем логирования, мониторинга и сбора аналитики
 4. Масштабирование системы при росте нагрузки

## Литература
### Книги
 1. Goodfellow I., Bengio Y., Courville A. Deep Learning. MIT Press, 2016.
 2. Bishop C. Pattern Recognition and Machine Learning. Springer, 2006.
 3. Zhang A., Lipton Z., Li M., Smola A. Dive into Deep Learning. 2023.
 4. O’Reilly Media. Designing Machine Learning Systems / Chip Huyen. O’Reilly, 2022.
 5. Jurafsky D., Martin J. Speech and Language Processing. 3rd Edition (draft), 2023.
 
⸻

### Статьи
1. Radford A. et al. Improving Language Understanding by Generative Pre-Training. OpenAI, 2018.
2. Brown T. et al. Language Models are Few-Shot Learners (GPT-3). NeurIPS, 2020.
3. Ouyang L. et al. Training Language Models to Follow Instructions with Human Feedback (RLHF). OpenAI, 2022.
4. Ziegler D. et al. Fine-Tuning Language Models from Human Preferences. OpenAI, 2019.
5. Bubeck S. et al. Sparks of Artificial General Intelligence in GPT-4. Microsoft Research, 2023.

⸻

### Документации
 1. PyTorch Documentation. https://pytorch.org/docs
 2. HuggingFace Transformers Docs. https://huggingface.co/docs/transformers
 3. MLflow Documentation. https://mlflow.org
 4. Docker Documentation. https://docs.docker.com
 5. Kubernetes Documentation. https://kubernetes.io/docs


Репозиторий подготовлен как каркас экспериментов, на основе которых строилась модель помощника в обучении. Данный помощник должен уметь не только давать решения задачи, но и пошагово указывать ученику на подсказки, наталкивать на идею. Также желательно, чтобы ученикам заходило объяснение, поэтому нужно было давать и свои решения, чтобы модель понимала стиль преподавателей. 

Здесь продемонстрирована основная часть экспериментов на сэмплах и подсэмплах данных. Показано, как строилась продовая модель. Модель с прода реализана как ИИ помощник на сайте https://znanie-platform.ru

В этом репозитории реализован Backend сервис, в котором можно подергать модель на выбор. Реализованы воспроизводимые эксперимент с примерным промптом и RAGом

- `backend/` — сервис с API, который принимает вопрос, позволяет выбрать вариант модели и возвращает ответ
- `experiments/` — воспроизводимые эксперименты для сравнения 4 подходов:
  1. Базовый GPT
  2. GPT с обучающим системным промптом
  3. GPT + RAG
  4. Дообученная open-source модель 

## Быстрый старт

1. Создать виртуальное окружение и установить зависимости:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Настроить переменные окружения:

```bash
copy .env.example .env
```

3. Запустить API:

```bash
uvicorn app.main:app --reload --port 8000
```

4. Запустить экспериментальный прогон:

```bash
cd ..\experiments
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_benchmark.py --config configs\baseline_gpt.yaml
```

5. Собрать сводку по всем прогонам:

```bash
python aggregate_results.py --results-dir results --output results\summary.json
```

## Запуск через Docker Compose

Поднимает сразу:

- `backend` на `http://localhost:8000`
- `finetuned_oss_mock` на `http://localhost:8010`

```bash
docker compose up --build
```

Перед запуском нужно создать `backend/.env` на основе `backend/.env.example`.

## Как обращаться к Yandex Cloud

В текущем каркасе используется OpenAI-совместимый SDK к Yandex API.

- `YANDEX_API_KEY` — API-ключ сервисного аккаунта.
- `YANDEX_BASE_URL` — `https://ai.api.cloud.yandex.net/v1`
- `YANDEX_PROJECT_ID` — ID проекта
- `YANDEX_PROMPT_ID` — ID промпта (опционально, если используешь prompt template)
- `YANDEX_MODEL` — модель для `responses.create` (используется, если `YANDEX_PROMPT_ID` не задан), формат: `gpt://<project_id>/yandexgpt/latest`

Подключение реализовано в стиле:

```python
from openai import OpenAI

client = OpenAI(
    api_key="<API_key_value>",
    base_url="https://ai.api.cloud.yandex.net/v1",
    project="b1g5jloil44qmt951piv",
)

response = client.responses.create(
    prompt={"id": "fvt3rl6bjqg8ndjpqes8"},
    input="some message",
)
```

## Отчеты

- A/B/C тест с учениками: `reports/ab_test_weekly_report.md`

