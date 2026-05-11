# Knowledge Base · связь с локальной базой знаний CDP Calltouch

Эта папка — **точка входа в RAG-поиск** для всех агентов проекта CDP Generation. Сама база знаний физически живёт по соседству:

```
c:\Users\Mechrevo\Desktop\AI\Обучение\
├── cdp_calltouch_kb/        ← Сама база знаний (источник истины)
└── CDP Generation/          ← Этот проект
    └── knowledge_base/      ← Эта папка (только указатели + RAG-индекс)
```

## Что лежит в `cdp_calltouch_kb/` (источник)

| Раздел | Содержимое | Кто использует |
|---|---|---|
| `01_product/` | Описание CDP, архитектура, тарификация, этапы внедрения, технические нюансы, глоссарий | `scenario-author`, `reviewer`, `prompt-engineer` |
| `02_sales/` | УТП, отработка возражений, сравнение с конкурентами (для устной отработки), методология ВСПВ, новый процесс продажи | `scenario-author`, `prompt-engineer` |
| `03_clients/` | Подходящие отрасли, специфика по отраслям, ограничения и запреты | `scenario-author`, `data-scout`, `reviewer` |
| `04_templates/` | Базовые сценарии, расширенные, креативные паттерны, структура предложения, отраслевые карты коммуникаций | `scenario-author`, `visual-designer` |
| `05_cases/` | Кейсы по медицине, авто, e-commerce, недвижимости, прочие | `scenario-author`, `doc-keeper` |
| `output_lw_group/` | Эталонный кейс LW Group / Lake Wood (HTML + PDF) | `visual-designer` (template), `reviewer` (smoke-test) |
| `output_level_group/` | Эталонный кейс Level Group (HTML + PDF) | `visual-designer` (template), `reviewer` (smoke-test) |

## Как агенты с этим работают

### Поиск по теме (RAG)

```python
from src.kb import retrieve_relevant_chunks

chunks = retrieve_relevant_chunks(
    query="триггеры для премиум-недвижимости с длинным циклом",
    top_k=5,
    sections=["01_product/02_architecture", "04_templates/05_industry_communication_maps"],
)
```

Реализация (на старте фазы 1) — простой поиск по подстрокам + опциональные эмбеддинги через `text-embedding-3-small` от OpenAI или free Gemini embedding endpoint.

### Эталонные шаблоны для PDF

`visual-designer` использует существующие HTML-кейсы как scaffolding:
- `../cdp_calltouch_kb/output_lw_group/LW_Group_CDP_Proposal.html`
- `../cdp_calltouch_kb/output_level_group/Level_Group_CDP_Proposal.html`

Брать структуру + классы CSS, заменять контент.

### Smoke-тесты для `reviewer`

Эталонные PDF используются как «золотой стандарт». При изменении промптов / pipeline — новый сгенерированный PDF сравнивается со старым:
- Все секции присутствуют
- Цены актуальные («от 10 500 ₽», «от 5 000 ₽»)
- Нет упоминаний конкурентов
- Реализуемые триггеры/действия

## Зачем не копировать сюда базу

База знаний — живой документ. Менеджер дописывает её по мере обучения, появления новых кейсов и регламентов. Дублировать — значит синхронизировать вручную, что быстро рассинхронизируется.

Поэтому: **файлы остаются в `cdp_calltouch_kb/`, RAG читает их по абсолютным путям**, а в этой папке хранится только индекс/кэш эмбеддингов (через `.gitignore`).

## Файлы в этой папке (планируется)

- `index.json` — метаданные о всех md-файлах базы (путь, секция, размер, чек-сум)
- `chunks.jsonl` — нарезанные чанки (~500–1000 токенов) для RAG
- `embeddings.npy` — векторные представления (по чанкам)

Все три файла — продукты предобработки, в git не попадают (см. `.gitignore`).

## Команда регенерации индекса

```bash
python -m src.kb.build_index
```

Запускать:
- При первой настройке проекта
- После обновления `cdp_calltouch_kb/`
- При изменении модели эмбеддингов
