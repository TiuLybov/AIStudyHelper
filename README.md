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
