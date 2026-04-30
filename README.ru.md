# ast-outline

[English](./README.md) · **Русский** · [简体中文](./README.zh-CN.md)

> **Переименован из `code-outline` в v0.3.0** — встраиваемся в семейство `ast-*` по соглашению [ast-grep](https://github.com/ast-grep/ast-grep). Старая CLI-команда `code-outline` продолжает работать как backward-compat alias через 0.4.x.

> Быстрый **структурный outline** исходников на основе AST — классы, методы,
> сигнатуры с номерами строк, но **без тел методов**. Сделан для LLM-агентов,
> которым нужно понять *форму* файла раньше, чем читать его целиком.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status: beta](https://img.shields.io/badge/status-beta-orange.svg)

---

## Зачем это нужно

**`ast-outline` существует, чтобы LLM-кодовые агенты работали быстрее,
дешевле и точнее, когда исследуют незнакомый код.**

Современные агенты (Claude Code, agent-режим Cursor, Aider, Copilot Chat,
собственные CLI-агенты) изучают кодовую базу *читая файлы напрямую* — без
embeddings и vector search. Подход надёжный, но дорогой: на 1000-строчном
файле агент тратит 1000 строк токенов только чтобы ответить на вопрос
*«какие здесь есть методы?»*.

`ast-outline` закрывает эту дыру. Это **слой-предчтение** для агентов:

1. **Экономия токенов — типично в 5–10 раз.** Outline заменяет полное
   чтение файла, когда агенту нужна только структура.
2. **Быстрая разведка.** Публичное API целого модуля помещается на одной
   странице — агент понимает архитектуру за один вызов, а не за 10–20.
3. **Точная навигация.** У каждой декларации есть диапазон строк
   (`L42-58`). Агент идёт сразу к нужному методу — без перелопачивания.
4. **AST, не регулярки.** `implements` и `show` работают на реальном
   синтаксисе — ложных срабатываний из комментариев или строковых
   литералов не бывает.
5. **Никакой инфраструктуры.** Нет индекса, нет кеша, нет embeddings, нет
   сетевых вызовов. Всегда свежо, ничего не засоряет репозиторий.

### Типичный workflow агента

**Без `ast-outline`:**

```
Агент: Read Player.cs            # 1200 строк токенов
Агент: Read Enemy.cs             # 800 строк токенов
Агент: Read DamageSystem.cs      # 400 строк токенов
Агент: grep "IDamageable" src/   # шумно, куча ложных совпадений
...
```

**С `ast-outline`:**

```
Агент: ast-outline digest src/Combat         # ~100 строк, весь модуль
Агент: ast-outline implements IDamageable    # точный список, без шума grep
Агент: ast-outline show Player.cs TakeDamage # только нужный метод
```

Итог: **то же понимание кода, в разы меньше токенов, в разы меньше раундов.**

---

## Поддерживаемые языки

| Язык | Расширения |
| --- | --- |
| C#         | `.cs` |
| Python     | `.py`, `.pyi` |
| TypeScript | `.ts`, `.tsx` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` (парсятся через TS-грамматику) |
| Java       | `.java` — классы, интерфейсы, `@interface`, enum'ы, records, sealed-иерархии, generics, throws, Javadoc |
| Kotlin     | `.kt`, `.kts` — классы, интерфейсы, `fun interface`, `object` / `companion object`, `data` / `sealed` / `enum` / `annotation`-классы, extension-функции, `suspend` / `inline` / `const` / `lateinit`, generics с `where`-ограничениями, `typealias`, KDoc |
| Scala      | `.scala`, `.sc` — Scala 2 + Scala 3: классы, trait'ы, `object` / `case object`, `case class`, `sealed`-иерархии, Scala 3 `enum` / `given` / `using` / `extension`, indentation-синтаксис, higher-kinded types, context bounds, `opaque type`, type-алиасы, Scaladoc |
| Go         | `.go` — пакеты, struct'ы (методы группируются под receiver), интерфейсы, embedding (struct и interface) как механизм «наследования», generics (Go 1.18+), type-алиасы + defined types, `iota`-enum'ы, цепочки doc-комментариев |
| Markdown   | `.md`, `.markdown`, `.mdx`, `.mdown` — оглавление по заголовкам + код-блоки |
| YAML       | `.yaml`, `.yml` — иерархия ключей с диапазонами строк, `[i]` пути для sequence-элементов, multi-document сепараторы, format-detect для Kubernetes / OpenAPI / GitHub Actions в шапке |

Добавление нового языка — это один новый файл-адаптер. См.
[`src/ast_outline/adapters/`](src/ast_outline/adapters/).

---

## Установка

### Одной командой (рекомендуется — macOS / Linux / Windows)

Нужен [`uv`](https://docs.astral.sh/uv/) (быстрый Python package manager):

```bash
uv tool install git+https://github.com/dim-s/ast-outline.git
```

Это поставит CLI `ast-outline` глобально в `~/.local/bin` (Mac / Linux)
или `%USERPROFILE%\.local\bin` (Windows) — убедись что эта папка в `PATH`.

Нет `uv`?

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Через install-скрипты из репозитория

```bash
# macOS / Linux
curl -LsSf https://raw.githubusercontent.com/dim-s/ast-outline/main/scripts/install.sh | bash

# Windows (PowerShell)
iwr -useb https://raw.githubusercontent.com/dim-s/ast-outline/main/scripts/install.ps1 | iex
```

### Альтернатива: `pipx`

```bash
pipx install git+https://github.com/dim-s/ast-outline.git
```

### Альтернатива: `pip` (в активный venv)

```bash
pip install git+https://github.com/dim-s/ast-outline.git
```

### Обновить / удалить

```bash
uv tool upgrade ast-outline
uv tool uninstall ast-outline
```

---

## Быстрый старт

```bash
# Структурный обзор одного файла
ast-outline path/to/Player.cs
ast-outline path/to/user_service.py

# Обзор целой папки (рекурсивно по поддерживаемым расширениям)
ast-outline src/

# Показать исходник конкретного метода
ast-outline show Player.cs TakeDamage

# Несколько методов за раз
ast-outline show Player.cs TakeDamage Heal Die

# Компактная карта публичного API модуля
ast-outline digest src/Services

# Все классы, которые наследуют/реализуют тип
ast-outline implements IDamageable src/

# Встроенный help
ast-outline help
ast-outline help show
```

---

## Использование с LLM-агентами

**Это основной кейс применения.** Добавь блок ниже в свой `CLAUDE.md`,
`AGENTS.md`, файл субагента или любой system-prompt, который управляет
кодовым агентом. После этого агент будет использовать `ast-outline`
вместо полного чтения файлов.

Тот же snippet идёт с утилитой — `ast-outline prompt` печатает его
as-is, так что можно сразу дописать в agent-конфиг проекта без ручного
копипаста:

```bash
ast-outline prompt >> AGENTS.md
ast-outline prompt >> .claude/CLAUDE.md
ast-outline prompt | pbcopy   # буфер обмена в macOS
```

### Snippet для промпта (скопируй как есть)

```markdown
## Изучение кода — выбирай `ast-outline` вместо полного чтения

Для файлов `.cs`, `.py`, `.pyi`, `.ts`, `.tsx`, `.js`, `.jsx`, `.java`, `.kt`,
`.kts`, `.scala`, `.sc`, `.go` и `.md` сначала читай структуру через `ast-outline`,
а не полное содержимое.
Тела методов — только когда уже знаешь, какое именно тело тебе нужно.

Останавливайся на шаге, который ответил на вопрос:

1. **Незнакомая директория** — `ast-outline digest <dir>`: карта на одну
   страницу — типы и публичные методы каждого файла.

2. **Структура одного файла** — `ast-outline <file>`: сигнатуры с
   диапазонами строк, без тел (в 5–10 раз меньше токенов, чем полное чтение).

3. **Одно тело метода / класса / markdown-секции** — `ast-outline show
   <file> <Symbol>`. Поиск по суффиксу: `TakeDamage`, или
   `Player.TakeDamage` если имя неоднозначно. За раз несколько символов:
   `ast-outline show Player.cs TakeDamage Heal Die`. Для markdown
   символ — это текст заголовка, а матчинг — **подстрочный** и
   регистронезависимый: `"текущий анализ"` найдёт
   `"1. ТЕКУЩИЙ АНАЛИЗ (февраль 2026)"`. Если совпало несколько секций —
   печатаются все, запрос можно сузить.

4. **Кто наследует/реализует тип** — `ast-outline implements <Type>
   <dir>`: AST-поиск (не нужен `grep`), транзитивный по умолчанию — внуки
   получают метку `[via Parent]`. Добавь `--direct` для только прямых
   наследников.

Возвращайся к полному чтению только если `show` отдал тело, но нужен
контекст за его пределами.

Если в header'е outline есть строка `# WARNING: N parse errors`, outline
для этого файла частичный — читай исходник напрямую для затронутой области.

`ast-outline help` — флаги и редкие опции.
```

### Почему это помогает

- **Свежие субагенты с чистым контекстом** (типа `Explore` в Claude Code)
  сканируют целый модуль одним вызовом вместо 10–20 раундов `Read`/`grep`.
- **«Где определён X?»** становится одним вызовом `implements` или `show`.
- **Диапазоны строк** (`L42-58`) превращают outline в точный навигатор —
  агент читает только нужные строки.
- **AST-поиск в `implements`** не даёт ложных срабатываний на строковых
  литералах, комментариях и случайных упоминаниях имени — в отличие от `grep`.

### Работает с

- Claude Code (+ кастомные субагенты типа `Explore`, `codebase-scout`)
- Cursor в режиме agent
- Aider
- Copilot Chat / Workspace
- Любой кастомный агент на API Claude / OpenAI / Gemini
- Людьми (формат читаемый; `show` — приятная альтернатива `grep -A 20`)

---

## Команды

### `outline` — по умолчанию

Печатает классы, методы, свойства, поля файла с диапазонами строк.

```bash
ast-outline path/to/File.cs
ast-outline path/to/module.py --no-private --no-fields
```

Флаги:

- `--no-private` — скрыть приватные (для Python: имена с `_`)
- `--no-fields` — скрыть декларации полей
- `--no-docs` — скрыть `///` XML-doc и docstrings
- `--no-attrs` — скрыть `[Attributes]` и `@decorators`
- `--no-lines` — скрыть суффиксы с номерами строк
- `--glob PATTERN` — своя маска для режима директории

### `show` — исходник по имени символа

```bash
ast-outline show File.cs TakeDamage
ast-outline show File.cs PlayerController.TakeDamage   # разрешить overloads
ast-outline show service.py UserService.get
ast-outline show File.cs TakeDamage Heal Die           # несколько за раз
```

Для кода поиск по **суффиксу**: `Foo.Bar` найдёт любой `*.Foo.Bar`. Если
совпадений несколько — печатаются все со сводкой.

Для markdown поиск **подстрочный** и регистронезависимый — по каждой части
точечного пути. LLM-агент редко помнит точную декорацию заголовка
(префиксы вроде `1.`, скобочные хвосты `(февраль 2026)`,
`(Уверенность: 70%)`), поэтому работает «по смыслу»:

```bash
ast-outline show forecast.md "текущий анализ"
# → найдёт `## 1. ТЕКУЩИЙ АНАЛИЗ (февраль 2026)`

ast-outline show forecast.md "сценарий.транзит"
# → найдёт `### СЦЕНАРИЙ A: "УПРАВЛЯЕМЫЙ ТРАНЗИТ"` под любым
#   родительским заголовком, содержащим "сценарий"
```

Если подстрока совпала с несколькими заголовками — печатаются все, на
stderr идёт сводка дисамбигуации, запрос можно сузить.

### `digest` — карта модуля на одной странице

```bash
ast-outline digest src/
```

Пример вывода:

```
# size labels next to each file: [tiny] / [medium] / [large]

src/services/
  __init__.py [tiny] (8 lines, ~74 tokens, 1 fields)
  user_service.py [medium] (140 lines, ~1,200 tokens, 1 types, 5 methods)
    class UserService : IUserService  L8-138
      +get  +search  +create  +delete  +update
  auth_service.py [medium] (95 lines, ~840 tokens, 1 types, 4 methods)
    class AuthService  L10-95
      +login  +logout  +refresh  +verify_token
  legacy_repo.py [large] (5234 lines, ~52,000 tokens, ...)
```

К каждому файлу прилагается описательная size-метка: `[tiny]` (до ~500
токенов), `[medium]` (500–5000), `[large]` (5000+). Метки **описывают**
файл, а не предписывают действие. LLM-агент читает метку, оценивает свою
задачу (нужен весь файл? одна секция? только структура?) и сам выбирает
между Read / outline / show — инструмент информирует, агент решает.

Подсчёт — `len(chars)/4`, ±15-20% от реальных BPE-токенизаторов, точности
для классификации размера хватает. Тот же `~N tokens` появляется в шапке
каждого `outline`-вывода — сигнал о размере доступен независимо от того,
делал ли агент сначала `digest`.

### `implements` — найти наследников / реализации

```bash
ast-outline implements IDamageable src/
```

AST-поиск — без ложных срабатываний из комментариев и случайных упоминаний.
**Транзитивный по умолчанию**: если `Puppy extends Dog extends Animal`, то
`implements Animal` вернёт всех троих, а непрямые совпадения получают
аннотацию цепочки:

```
# 3 match(es) for 'Animal' (incl. transitive):
src/Animals.cs:5   class Dog : Animal
src/Cats.cs:3      class Cat : Animal
src/Puppies.cs:12  class Puppy : Dog          [via Dog]
```

Флаг `--direct` / `-d` ограничивает только прямыми наследниками (level 1):

```bash
ast-outline implements --direct IDamageable src/
```

Поиск работает по любому количеству файлов и вложенных папок — не
полагается на соглашение «имя_файла = имя_класса». Матчинг по последнему
сегменту имени (generics и namespace-префикс стрипаются).

### `prompt` — напечатать snippet для LLM-агента

```bash
ast-outline prompt
ast-outline prompt >> AGENTS.md
```

Печатает canonical copy-paste snippet, который настраивает LLM-агента
использовать `ast-outline` вместо полного чтения. Английский,
универсальный под Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5. Запуск
команды гарантирует что ты получишь текущую рекомендованную версию.

---

## Формат вывода

Формат сделан **удобным для LLM**: Python-стиль индентации, суффиксы
с номерами строк `L<start>-<end>`, doc-комментарии сохраняются. Header
показывает масштаб файла и сигнализирует о частичном парсинге.

### C#

```
# Player.cs (142 lines, 3 types, 12 methods, 5 fields)
namespace Game.Player
    [RequireComponent(typeof(Rigidbody2D))] public class PlayerController : MonoBehaviour, IDamageable  L10-120
        [SerializeField] private float speed = 5f  L12
        public int CurrentHealth { get; private set; }  L15
        /// <summary>Apply damage.</summary>
        public void TakeDamage(int amount)  L30-48
        private void Die()  L50-55
```

### Python

```
# user_service.py (70 lines, 2 types, 5 methods, 3 fields)
@dataclass class User  L16-29
    def display_name(self) -> str  L26-29
        """Human-friendly label."""

class UserService  L31-58
    def __init__(self, storage: Storage) -> None  L34-35
    def get(self, user_id: int) -> User | None  L37-42
        """Look up a user by id."""
    def save(self, user: User) -> None  L44-46
```

### `show` с контекстом предка

`ast-outline show <file> <Symbol>` между header'ом и телом печатает
строку `# in: ...` — цепочку enclosing namespace/класса, чтобы ты видел
куда вложен извлечённый код без дополнительного вызова `outline`:

```
# Player.cs:30-48  Game.Player.PlayerController.TakeDamage  (method)
# in: namespace Game.Player → public class PlayerController : MonoBehaviour, IDamageable
/// <summary>Apply damage.</summary>
public void TakeDamage(int amount) { ... }
```

Для top-level символов (нет enclosing namespace/типа) breadcrumb не выводится.

### Частичный парсинг

Если tree-sitter восстановился после синтаксических ошибок, outline
сохраняется, но вторая строка header'а сигнализирует о дыре:

```
# broken.java (16 lines, 1 types, 3 methods)
# WARNING: 3 parse errors — output may be incomplete
```

Агенту для таких файлов стоит считать outline частичным и читать
исходник напрямую для затронутой области.

Разница естественна для языков:

- C# `///` XML-doc идёт **над** сигнатурой.
- Python `"""docstrings"""` — **под** сигнатурой с отступом (соответствует
  тому, как оно реально лежит в body).
- C# `[Attr]` и Python `@decorator` инлайнятся с декларацией.
- C# свойства с аксессорами `{ get; private set; }` сохраняются.

---

## Как это работает (кратко)

- Парсит исходники через [tree-sitter](https://tree-sitter.github.io/) —
  настоящий AST, не regex.
- Языко-специфичные адаптеры приводят AST к единому промежуточному
  представлению `Declaration`.
- Язык-агностичные рендереры строят outline / digest / search вывод.
- Локально, без сети, без индексации, без кеша — только читает и парсит
  те файлы, которые ты запросил.

Никаких векторных баз, embeddings или RAG. Это осознанно — философия
совпадает с тем, как реально работают agentic-инструменты типа Claude Code.

---

## Разработка

```bash
git clone https://github.com/dim-s/ast-outline.git
cd ast-outline

# Создать venv и поставить в editable-режим
uv venv
uv pip install -e .

# Прогнать на тестовых сэмплах из репо
.venv/bin/ast-outline tests/sample.cs
.venv/bin/ast-outline tests/sample.py
.venv/bin/ast-outline digest tests/
```

### Запуск тестов

Тесты — опциональная dev-зависимость, конечным пользователям они не нужны.
Поставить один раз, дальше гонять через `pytest`:

```bash
# Поставить pytest в тот же venv
uv pip install -e ".[dev]"

# Прогнать весь сьют (~0.1 сек)
.venv/bin/pytest

# Один файл, подробный вывод
.venv/bin/pytest tests/unit/test_csharp_adapter.py -v

# Фильтр по имени теста
.venv/bin/pytest -k file_scoped_namespace -v
```

Сьют (400+ тестов) покрывает все адаптеры (C#, Python, TypeScript/JS,
Java, Kotlin, Scala, Go, Markdown), языко-агностичные рендереры, поиск по
символам и CLI end-to-end. Фикстуры лежат в `tests/fixtures/`; тесты не
выходят за эту директорию. Любая новая фича должна приходить с тестом;
новый язык — с отдельной папкой фикстур и файлом
`tests/unit/test_<lang>_adapter.py`.

### Добавить новый язык

Создай `src/ast_outline/adapters/<lang>.py` с реализацией протокола
`LanguageAdapter` (см. `adapters/base.py`). Затем зарегистрируй его в
`adapters/__init__.py`. Рендереры и CLI подхватят автоматически, никакой
дополнительной связки не нужно.

---

## Roadmap

- [x] Адаптер TypeScript / JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`)
- [x] Адаптер Java (`.java`) — классы, интерфейсы, `@interface`, enum'ы, records, sealed-иерархии, generics, throws, Javadoc
- [x] Адаптер Kotlin (`.kt`, `.kts`) — классы, интерфейсы, `fun interface`, `object` / `companion object`, `data` / `sealed` / `enum` / `annotation`-классы, extension-функции, `suspend` / `inline` / `const` / `lateinit`, generics с `where`, `typealias`, KDoc
- [x] Адаптер Scala (`.scala`, `.sc`) — Scala 2 + Scala 3: классы, trait'ы, `object` / `case object`, `case class`, `sealed`-иерархии, Scala 3 `enum` / `given` / `using` / `extension`, indentation-синтаксис, higher-kinded types, context bounds, `opaque type`, type-алиасы, Scaladoc
- [x] Адаптер Go (`.go`) — пакеты, struct'ы (методы группируются под receiver), интерфейсы, struct/interface embedding как «наследование», generics (Go 1.18+), type-алиасы + defined types, `iota`-enum'ы, цепочки doc-комментариев
- [x] Адаптер Markdown (`.md`, `.markdown`, `.mdx`, `.mdown`) — TOC из заголовков + код-блоки
- [x] Адаптер YAML (`.yaml`, `.yml`) — иерархия ключей, `[i]` пути для sequence-элементов, multi-document, format-detect для Kubernetes / OpenAPI / GitHub Actions
- [ ] Адаптер Rust
- [ ] `--format json` для программной обработки вывода
- [ ] Опциональный multiprocessing для очень больших кодовых баз (>500 файлов)

PR приветствуются.

---

## Лицензия

[MIT](./LICENSE)
