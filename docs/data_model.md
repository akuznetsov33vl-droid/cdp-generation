# Модель данных · CDP Generation

> Pydantic-модели — единственный источник правды для всех данных в pipeline. Перед использованием в Supabase (фаза 2) — генерация TypeScript-типов через MCP.

## I. Pydantic-модели (Python, фаза 1 + 2)

### Конфигурация

```python
class AppSettings(BaseSettings):
    anthropic_api_key: SecretStr
    anthropic_model: str = "claude-opus-4-7"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    knowledge_base_path: Path
    output_dir: Path = Path("./output")
    chrome_path: Path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    # phase 2
    supabase_url: HttpUrl | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None
    telegram_bot_username: str | None = None
    allowed_telegram_ids: list[int] = []
    model_config = SettingsConfigDict(env_file=".env")
```

### Запрос на генерацию

```python
class GenerationRequest(BaseModel):
    client_url: HttpUrl
    additional_urls: list[HttpUrl] = []
    brief: str
    extra_notes: str | None = None
    industry_hint: str | None = None
    target_scenarios_count: int = Field(default=5, ge=1, le=10)
    user_telegram_id: int | None = None  # фаза 2
```

### Промежуточные данные (между агентами)

```python
class SiteFacts(BaseModel):
    """Что вытащил data-scout."""
    primary_domain: HttpUrl
    additional_domains: list[HttpUrl] = []
    company_name: str | None = None
    industry_detected: str
    detected_class: Literal["mass", "comfort", "business", "premium", "deluxe"] | None
    products: list[ProductRef] = []
    projects: list[ProjectRef] = []
    pricing_signals: list[PricingSignal] = []
    team_members: list[TeamMember] = []
    contact_blocks: list[ContactBlock] = []
    social_channels: list[SocialChannel] = []
    detected_crm_hints: list[str] = []  # "Bitrix24", "amoCRM" и т.д.

class ProjectRef(BaseModel):
    name: str
    url: HttpUrl | None = None
    location: str | None = None
    price_from: int | None = None  # в рублях
    status: str | None = None  # "сдан", "строится"

class TeamMember(BaseModel):
    name: str
    role: str

class BriefFacts(BaseModel):
    """Что вытащил doc-keeper из брифа/транскрипта."""
    main_kpi: str
    pain_points: list[str]
    constraints: list[str]
    explicit_no_go: list[str]  # «не предлагать SMS-промо», «не скидки» и т.п.
    industry_confirmation: str | None
    context_from_meeting: str | None

class IndustryMap(BaseModel):
    """Подобранная отраслевая карта из knowledge_base."""
    name: str
    source_path: Path
    key_scenarios: list[str]
    typical_kpis: list[str]
```

### Сценарий

```python
class Trigger(BaseModel):
    """Триггер из реального списка Calltouch (11 типов)."""
    type: Literal[
        "session_start", "session_end", "new_lead", "lead_change",
        "new_deal", "deal_status_change", "page_view", "goal_achieved",
        "interest_detected", "custom_event", "scheduled",
    ]
    config: dict[str, Any] = {}  # детали (URL-паттерн, период, цель)

class Action(BaseModel):
    """Действие из реального списка Calltouch (9 типов)."""
    type: Literal[
        "email_to_manager", "email_to_client",
        "sms_to_manager", "sms_to_known_client",
        "callback", "webhook", "show_form",
        "tag_client", "messenger_message",
    ]
    config: dict[str, Any] = {}  # текст, шаблон, канал

class Scenario(BaseModel):
    title: str
    pitch: str  # одно предложение «суть для менеджера»
    audience: str  # описание аудитории
    triggers: list[Trigger]
    actions: list[Action]
    logic_pseudocode: str  # текстовое описание потока (для PDF)
    popup_text: str | None = None
    email_text: str | None = None
    why_calltouch: str  # объяснение для блока «Почему именно Calltouch»
    expected_metrics: list[ScenarioMetric]

class ScenarioMetric(BaseModel):
    label: str  # "CR заявка→договор"
    value: str  # "×1,4–1,7"

class CaseReference(BaseModel):
    title: str
    source_path: Path
    industry: str
    key_numbers: list[str]
    applicability_to_this_client: str
```

### Финальный результат

```python
class PricingBlock(BaseModel):
    cdp_price_from: int = 10500  # ₽/мес
    big_data_price_from: int = 5000
    additional_products: list[str] = []  # без WABA по умолчанию
    notes: str | None = None

class GenerationResult(BaseModel):
    request_id: UUID
    client_name: str
    industry: str
    target_segments: list[str]
    site_facts: SiteFacts
    brief_facts: BriefFacts
    scenarios: list[Scenario]
    cases: list[CaseReference]
    pricing: PricingBlock
    html_path: Path
    pdf_path: Path
    review_passed: bool
    review_issues: list[str]
    generated_at: datetime
    user_telegram_id: int | None = None
```

## II. Схема Supabase (фаза 2)

### Таблицы

```sql
-- Пользователи (allow-list по telegram_id)
create table public.users (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint not null unique,
  telegram_username text,
  first_name text,
  role text not null default 'manager' check (role in ('manager', 'admin')),
  is_active boolean not null default true,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

-- Клиенты (карточки)
create table public.clients (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid references public.users(id) on delete cascade,
  display_name text not null,
  primary_domain text not null,
  additional_domains text[] default '{}',
  industry text,
  detected_class text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Брифы (транскрипты, заметки менеджера)
create table public.briefs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  brief_text text not null,
  meeting_date timestamptz,
  source text default 'manual',
  created_at timestamptz not null default now()
);

-- История сгенерированных КП
create table public.kp_history (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  brief_id uuid references public.briefs(id),
  request_payload jsonb not null,         -- полный GenerationRequest
  result_payload jsonb not null,          -- полный GenerationResult
  pdf_storage_path text,                  -- путь в Supabase Storage
  html_storage_path text,
  review_passed boolean,
  review_issues text[] default '{}',
  generation_cost_rub numeric(10,2),     -- факт затрат API
  generation_duration_seconds int,
  created_at timestamptz not null default now()
);

-- Логи входов
create table public.auth_log (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint not null,
  ip_address inet,
  user_agent text,
  outcome text not null check (outcome in ('success', 'denied_not_in_allowlist', 'denied_invalid_hash', 'denied_expired')),
  created_at timestamptz not null default now()
);

-- Индексы
create index idx_clients_owner on public.clients(owner_user_id);
create index idx_kp_history_client on public.kp_history(client_id);
create index idx_kp_history_created on public.kp_history(created_at desc);
create index idx_auth_log_telegram on public.auth_log(telegram_id, created_at desc);
```

### Row Level Security (обязательно)

```sql
alter table public.users enable row level security;
alter table public.clients enable row level security;
alter table public.briefs enable row level security;
alter table public.kp_history enable row level security;
alter table public.auth_log enable row level security;

-- Политика "владелец видит только своё"
create policy "users see own profile" on public.users
  for select using (auth.uid()::text = id::text);

create policy "users manage own clients" on public.clients
  for all using (owner_user_id::text = auth.uid()::text);

-- Аналогично для briefs и kp_history через JOIN с clients
create policy "users access own briefs" on public.briefs
  for all using (
    exists (
      select 1 from public.clients c
      where c.id = briefs.client_id
        and c.owner_user_id::text = auth.uid()::text
    )
  );

create policy "users access own kp_history" on public.kp_history
  for all using (
    exists (
      select 1 from public.clients c
      where c.id = kp_history.client_id
        and c.owner_user_id::text = auth.uid()::text
    )
  );
```

> ⚠️ Перед применением миграции — проверить актуальный синтаксис RLS-политик в Supabase через `mcp__claude_ai_Context7__query-docs` и через `mcp__claude_ai_Supabase__get_advisors` после.

### Storage

- Бакет `kp-pdfs/` — хранение сгенерированных PDF
- Бакет `kp-htmls/` — хранение HTML
- Доступ: signed URL на 24 часа для скачивания, генерируется через Supabase API

## III. Миграция фаза 1 → фаза 2

При переходе:
1. Экспорт SQLite → JSON
2. `apply_migration` через Supabase MCP — создать схему
3. Импорт JSON → Supabase
4. Контроль через `get_advisors`
5. Генерация TypeScript-типов через `generate_typescript_types`
