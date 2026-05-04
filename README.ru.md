# ast-outline

[English](./README.md) · **Русский** · [简体中文](./README.zh-CN.md)

> Быстрый **структурный outline** исходников на основе AST — классы, методы,
> сигнатуры с номерами строк, но **без тел методов**. Сделан для LLM-агентов,
> которым нужно понять *форму* файла раньше, чем читать его целиком.
>
> Сосед [ast-grep](https://github.com/ast-grep/ast-grep) в семействе `ast-*`:
> **`ast-grep` ищет** по структуре кода, **`ast-outline` показывает обзор**.

[![Code: Apache 2.0](https://img.shields.io/badge/code-Apache%202.0-blue.svg)](./LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](./LICENSE-DOCS)
[![PyPI](https://img.shields.io/pypi/v/ast-outline.svg)](https://pypi.org/project/ast-outline/)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status: beta](https://img.shields.io/badge/status-beta-orange.svg)

📖 **Документация:** <https://ast-outline.github.io/> · **Исходник сайта:** [ast-outline/ast-outline.github.io](https://github.com/ast-outline/ast-outline.github.io)

> **ast-outline™** — Dmitrii Zaitsev (dim-s). Оригинальный проект:
> <https://github.com/ast-outline/ast-outline> (создан 2026-04-22). Код под
> **Apache 2.0** (с v0.6.0; v0.5.x и более ранние остаются под MIT),
> документация под **CC BY 4.0** — переиспользование текста этого README
> требует видимой атрибуции. Подробнее — раздел
> [«Лицензии и атрибуция»](#лицензии-и-атрибуция) ниже.

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
4. **AST, не регулярки.** `show` и заголовки типов с наследованием
   работают на реальном синтаксисе — ложных срабатываний из
   комментариев или строковых литералов не бывает.
5. **Никакой инфраструктуры.** Нет индекса, нет кеша, нет embeddings, нет
   сетевых вызовов. Всегда свежо, ничего не засоряет репозиторий.

### Типичный workflow агента

**Без `ast-outline`:**

```
Агент: Read Player.cs            # 1200 строк токенов
Агент: Read Enemy.cs             # 800 строк токенов
Агент: Read DamageSystem.cs      # 400 строк токенов
...
```

**С `ast-outline`:**

```
Агент: ast-outline digest src/Combat         # ~100 строк, весь модуль
Агент: ast-outline Player.cs                 # только сигнатуры, в 5–10× меньше
Агент: ast-outline show Player.cs TakeDamage # только нужный метод
```

Итог: **то же понимание кода, в разы меньше токенов, в разы меньше раундов.**

---

## Философия проекта

> **Stateless. Никакого индекса, кеша, embeddings, сети.**
> Парсит по запросу, печатает, выходит.

Противоположность RAG-style индексаторам (Cursor, Bloop, Continue,
толпа MCP-серверов на embeddings). Современные LLM-агенты достаточно
умны, чтобы цеплять `ast-outline` с `grep`, `find`, `ast-grep` и
другими unix-утилитами и быстро ходить по реальному коду — без полного
чтения файлов и без локального индекса, который отрабатывал бы свою
сложность.

И самой `ast-outline` тоже не делается MCP-сервер: для stateless CLI
у агента больше рычагов, когда он пайпит и параллелит её в `bash`,
чем через MCP-обёртку с теми же вызовами.

---

## Поддерживаемые языки

| Язык       | Расширения |
| ---        | --- |
| C#         | `.cs` |
| Python     | `.py`, `.pyi` |
| TypeScript | `.ts`, `.tsx` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` *(парсятся через TS-грамматику)* |
| Java       | `.java` |
| Kotlin     | `.kt`, `.kts` |
| Scala      | `.scala`, `.sc` |
| Go         | `.go` |
| Rust       | `.rs` |
| Markdown   | `.md`, `.markdown`, `.mdx`, `.mdown` |
| YAML       | `.yaml`, `.yml` |

<details>
<summary>Что распознаёт каждый адаптер</summary>

- **Java** — классы, интерфейсы, `@interface`, enum'ы, records, sealed-иерархии, generics, throws, Javadoc.
- **Kotlin** — классы, интерфейсы, `fun interface`, `object` / `companion object`, `data` / `sealed` / `enum` / `annotation`-классы, extension-функции, `suspend` / `inline` / `const` / `lateinit`, generics с `where`-ограничениями, `typealias`, KDoc.
- **Scala** — Scala 2 + Scala 3: классы, trait'ы, `object` / `case object`, `case class`, `sealed`-иерархии, Scala 3 `enum` / `given` / `using` / `extension`, indentation-синтаксис, higher-kinded types, context bounds, `opaque type`, type-алиасы, Scaladoc.
- **Go** — пакеты, struct'ы (методы группируются под receiver), интерфейсы, embedding (struct и interface) как механизм «наследования», generics (Go 1.18+), type-алиасы + defined types, `iota`-enum'ы, цепочки doc-комментариев.
- **Rust** — модули (рекурсивно), struct'ы (regular / tuple / unit), unions, enum'ы со всеми формами variant'ов, trait'ы (supertraits → bases), **группировка `impl`-блоков под целевой тип** (inherent + `impl Trait for Foo` добавляет Trait в bases), `extern "C"`, `macro_rules!`, type-алиасы, generics + lifetimes + `where`-clauses, классификация видимости (`pub` / `pub(crate)` / `pub(super)` / `pub(in path)`), внешние doc-комментарии (`///`, `/** */`) и `#[...]`-атрибуты.
- **Markdown** — оглавление по заголовкам + код-блоки.
- **YAML** — иерархия ключей с диапазонами строк, `[i]` пути для sequence-элементов, multi-document сепараторы, format-detect для Kubernetes / OpenAPI / GitHub Actions в шапке.

</details>

Добавление нового языка — это один новый файл-адаптер. См.
[`src/ast_outline/adapters/`](src/ast_outline/adapters/).

---

## Установка

```bash
uv tool install ast-outline
```

Поставит CLI `ast-outline` глобально в `~/.local/bin` (macOS / Linux)
или `%USERPROFILE%\.local\bin` (Windows). Нет [`uv`](https://docs.astral.sh/uv/)?

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                                          # macOS / Linux
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"       # Windows
```

Обновить / удалить: `uv tool upgrade ast-outline` / `uv tool uninstall ast-outline`.

<details>
<summary>Другие способы установки (pipx, pip, из исходников, скрипт-обёртка)</summary>

```bash
pipx install ast-outline
pip  install ast-outline                                          # в активный venv

# Свежий main вместо последнего PyPI-релиза:
uv tool install git+https://github.com/ast-outline/ast-outline.git

# Скрипт-обёртка (поставит и uv, если его нет):
curl -LsSf https://raw.githubusercontent.com/ast-outline/ast-outline/main/scripts/install.sh | bash    # macOS / Linux
iwr -useb https://raw.githubusercontent.com/ast-outline/ast-outline/main/scripts/install.ps1 | iex     # Windows
```

</details>

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
`.kts`, `.scala`, `.sc`, `.go`, `.rs`, `.md` и `.yaml`/`.yml` сначала читай
структуру через `ast-outline`, а не полное содержимое.

Выбирай минимальный из инструментов, который отвечает на твой вопрос —
это меню «от широкого к узкому», а не последовательность; сразу прыгай
к `show`, если символ уже известен:

1. **Незнакомая директория** — `ast-outline digest <paths…>`: карта на одну
   страницу — типы и публичные методы каждого файла. К каждому файлу —
   size-метка `[tiny]` / `[medium]` / `[large]`, плюс `[broken]` если
   parse-ошибки могли оставить outline неполным.

2. **Структура файлов** — `ast-outline <paths…>`: сигнатуры с
   диапазонами строк, без тел (в 5–10 раз меньше токенов на нетривиальных
   файлах). Строка `# WARNING: N parse errors` в шапке означает что
   outline частичный — читай исходник для затронутой области.

3. **Одно тело метода / типа / markdown-заголовка / yaml-ключа** —
   `ast-outline show <file> <Symbol>`. Поиск по суффиксу: `TakeDamage`
   для одного метода; `User` для целого типа — класс, struct,
   interface, trait, enum (всё тело, полезно когда в файле несколько
   типов); `Player.TakeDamage` если имя неоднозначно. За раз несколько
   символов: `ast-outline show Player.cs TakeDamage Heal Die`. Для
   markdown символ — это текст заголовка, матчинг подстрочный и
   регистронезависимый: `"текущий анализ"` найдёт
   `"1. ТЕКУЩИЙ АНАЛИЗ (февраль 2026)"`. Для yaml символ — точечный
   путь по ключам (`spec.containers[0].image`). `show` матчит **ключи**,
   не значения — для freeform-поиска текста внутри значений → `grep`.
   Добавь `--signature` к любому из вышеперечисленных, чтобы вернуть
   только заголовок (docs + атрибуты + сигнатура, без тела) — полезно
   после `digest`, когда имя уже известно и нужен контракт, а не
   реализация.

`outline` и `digest` принимают несколько путей за один вызов (файлы и
директории, разные языки вперемешку — OK) — батчь, а не цикль.
Заголовки типов в обоих рендерерах несут наследование как
`: Base, Trait`, поэтому форма иерархий видна без отдельного запроса.

Когда нужно понять, **что файл тянет**, или **где живёт упомянутый
тип / функция**, — добавь `--imports` к `outline` или `digest`. В шапке
файла появится строка `imports:` со всеми `import` / `use` / `using`
в native-синтаксисе языка (`from .core import X`, `use foo::Bar`,
`import { X } from './foo'`). Прочитай импорты, затем сразу вызывай
`outline` / `show` по нужному файлу вместо `grep`-а по определению.
Не используй флаг при рутинных структурных чтениях — он добавляет одну
строку на файл.

Возвращайся к полному чтению только если `show` отдал тело, но нужен
контекст за его пределами. `ast-outline help` — флаги.
```

### Внимание: субагенты

`CLAUDE.md` / `AGENTS.md` доходят **только до главного агента**.
Изолированные субагенты Claude Code (встроенный `Explore`, любые файлы
из `.claude/agents/*.md`) видят только собственный system prompt. Чтобы
`Explore` пошёл через `ast-outline`, перекрой его файлом
`.claude/agents/Explore.md` (или `~/.claude/agents/Explore.md`) и положи
в body вывод `ast-outline prompt`.

Cursor, Aider и прямые API-клиенты вложенных субагентов не имеют —
там `CLAUDE.md` / system prompt достаточно.

### Почему это помогает

- **Свежие субагенты с чистым контекстом** (типа `Explore` в Claude Code)
  сканируют целый модуль одним вызовом вместо 10–20 раундов `Read`/`grep`.
- **«Где определён X?»** становится одним вызовом `show`, как только агент
  заметил символ в `digest` или `outline`.
- **Диапазоны строк** (`L42-58`) превращают outline в точный навигатор —
  агент читает только нужные строки.
- **Заголовки типов** несут реальное `: Base, Trait` наследование на основе
  AST, без ложных срабатываний на строковых литералах, комментариях или
  случайных упоминаниях имени — в отличие от `grep`.

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
- `--imports` — показать импорты файла (см. ниже)
- `--glob PATTERN` — своя маска для режима директории

#### `--imports` — что подтягивает каждый файл

Флаг `--imports` поддерживают `outline` и `digest`. Когда он включён,
после шапки файла печатается строка `imports:` со всеми
`import`/`use`/`using`-стейтментами **в native-синтаксисе самого
языка** — никакого синтетического формата, который агенту пришлось бы
учить:

```
$ ast-outline service.py --imports
# src/services/user_service.py (140 строк, ~1,200 токенов, 1 типов, 5 методов)
# imports: from .core import UserBase; from .utils import parse_id; from typing import Optional
class UserService(UserBase):  L8-138
    ...
```

Многострочные и сгруппированные формы разворачиваются: Go-блок
`import (...)` распадётся на отдельные строки `import "fmt"`,
многострочный TS `import { X, Y } from './long'` свернётся в одну.
Импорты внутри функций и классов не попадают в список — только
файл-уровень.

Полезно, когда агенту нужно понять, где живёт упомянутый тип, или что
файл вообще тянет, прежде чем решать, что читать дальше.

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
# legend: name()=callable, name [kind]=non-callable, marker name()=method modifier (async/static/override/…), [N overloads]=N callables share name, [deprecated]=obsolete, L<a>-<b>=line range, : Base, …=inheritance
src/services/
  __init__.py [tiny] (8 lines, ~74 tokens, 1 fields)
  user_service.py [medium] (140 lines, ~1,200 tokens, 1 types, 5 methods)
    @Service abstract class UserService [deprecated] : IUserService  L8-138
      async get(), async search(), abstract create(), delete(), update_v1() [deprecated]

  auth_service.py [medium] (95 lines, ~840 tokens, 1 types, 4 methods)
    [ApiController] sealed class AuthService  L10-95
      async login(), logout(), refresh(), override verify_token()

  legacy_repo.py [large] [broken] (5234 lines, ~52,000 tokens, ...)
```

Первая строка — самообъясняющая легенда, чтобы LLM мог прочитать
вывод cold, без подгруженного `ast-outline prompt`. Токены следуют
универсальной конвенции программистской документации: `name()` —
callable, `name [kind]` — property/field/event и т.п., method-маркеры
(`async`, `static`, `abstract`, `override`, `virtual`, плюс
language-native формы: Kotlin `open` / `suspend`, Python
`@staticmethod` / `@classmethod` / `@abstractmethod`, Java
`@Override`) — префикс к имени source-true, каждый язык в своей
идиоме. `[N overloads]` — когда несколько callable делят одно имя,
`[deprecated]` — когда у типа/метода стоит `@Deprecated` /
`[Obsolete]` / `#[deprecated]`. В шапке типа также видны inline-
декораторы и атрибуты (`@dataclass`, `[ApiController]`,
`#[derive(Debug)]`) плюс семантические модификаторы (`abstract`,
`sealed`, `static`, `final`, `open`, `partial`) — runtime-контракт
и правила инстанцирования читаются с одного взгляда. Члены
разделены `, `; типы с телом получают завершающую пустую строку
как «paragraph break», пустые типы стекаются плотно — digest
остаётся компактным. Source-language ключевые слова (Rust `trait`,
Scala `object`, Kotlin `data class`) сохраняются в шапке типа
вместо канонического kind.

К каждому файлу прилагается описательная size-метка: `[tiny]` (до ~500
токенов), `[medium]` (500–5000), `[large]` (5000+). Дополнительная метка
`[broken]` появляется когда у файла были parse-ошибки и outline может
быть неполным. Метки **описывают** файл, а не предписывают действие —
LLM-агент читает их, оценивает свою задачу (нужен весь файл? одна
секция? только структура?) и сам выбирает между Read / outline / show.

Описание соглашений живёт в каноничном промпте (`ast-outline prompt`)
— один раз за сессию, а не на каждый digest-вызов. Подсчёт токенов —
`len(chars)/4`, ±15-20% от реальных BPE-токенизаторов, для классификации
размера хватает. Тот же `~N tokens` появляется в шапке каждого
`outline`-вывода.

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
git clone https://github.com/ast-outline/ast-outline.git
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

Сьют (600+ тестов) покрывает все адаптеры (C#, Python, TypeScript/JS,
Java, Kotlin, Scala, Go, Rust, Markdown, YAML), языко-агностичные рендереры, поиск по
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
- [x] Адаптер Rust (`.rs`) — модули (рекурсивно), struct'ы (regular / tuple / unit), unions, enum'ы со всеми формами variant'ов, trait'ы (supertraits → bases), **группировка `impl`-блоков под целевой тип** (inherent + `impl Trait for Foo` добавляет Trait в bases), `extern "C"`, `macro_rules!`, type-алиасы, generics + lifetimes + `where`-clauses, классификация видимости (`pub` / `pub(crate)` / `pub(super)` / `pub(in path)`), внешние doc-комментарии + `#[...]`-атрибуты
- [x] Адаптер Markdown (`.md`, `.markdown`, `.mdx`, `.mdown`) — TOC из заголовков + код-блоки
- [x] Адаптер YAML (`.yaml`, `.yml`) — иерархия ключей, `[i]` пути для sequence-элементов, multi-document, format-detect для Kubernetes / OpenAPI / GitHub Actions
- [ ] `--format json` для программной обработки вывода
- [ ] Опциональный multiprocessing для очень больших кодовых баз (>500 файлов)

PR приветствуются.

---

## История проекта

- **2026-04-22** — Репозиторий создан на GitHub как `dim-s/code-outline`. Первый публичный коммит, v0.2.0b0.
- **2026-04-22** — Добавлены русский и китайский README; в тот же день — адаптер TypeScript / JavaScript.
- **2026-04-23** — Адаптер Kotlin; подкоманда `prompt`.
- **2026-04-24** — Адаптер Scala. **Переименование `code-outline` → `ast-outline` (v0.3.0).** GitHub-репозиторий переименован в `dim-s/ast-outline`.
- **2026-04-25** — Адаптер Go.
- **2026-04-28** — LLM-friendly контракт ошибок: `# note: …` на stdout с `rc=0`; substring-матчинг для заголовков Markdown.
- **2026-04-30** — Адаптер YAML; per-file size-метки и оценка токенов в заголовках digest; адаптер Rust.
- **2026-05-01** — v0.4.0: маркеры методов в digest (`[async]` / `[unsafe]` / `[const]` / `[suspend]` / `[static]` / `[abstract]` / `[override]` / `[classmethod]` / `[property]`); модификаторы типов, атрибуты и тег `[deprecated]`. v0.4.1.
- **2026-05-02** — Публикация на PyPI как [`ast-outline`](https://pypi.org/project/ast-outline/). v0.4.2 / v0.4.3 / v0.5.0 (CLI-алиас `code-outline` удалён) / v0.5.1 (команда `implements` удалена — outline/digest и так показывают `: Base`) / v0.5.2 (флаг `--imports`) / v0.5.3 (флаг `--version`).
- **2026-05-03** — **v0.6.0: смена лицензии MIT → Apache License 2.0**, документация — отдельно под CC BY 4.0. Прежний текст MIT сохранён в `LICENSE-MIT` для совместимости с форками 0.5.x-ветки.
- **2026-05-03** — Репозиторий перенесён из `dim-s/ast-outline` в GitHub-организацию [`ast-outline`](https://github.com/ast-outline). Старые ссылки `dim-s/ast-outline` продолжают редиректить. Копирайт остаётся за Dmitrii Zaitsev (dim-s); GitHub-организация — это хостинговая инфраструктура, а не новый правообладатель.

Полная история — `git log` и [GitHub Releases](https://github.com/ast-outline/ast-outline/releases).

---

## Лицензии и атрибуция

Copyright © 2026 **Dmitrii Zaitsev** (GitHub: [dim-s](https://github.com/dim-s)) и контрибьюторы ast-outline.

В проекте **три разных лицензии** для разных типов работы:

| Что | Лицензия | Файл |
| --- | --- | --- |
| **Исходный код** (`src/`, тесты, build-конфиг) — v0.6.0 и новее | [Apache 2.0](./LICENSE) | `LICENSE` |
| **Исходный код** — v0.5.3 и более ранние | [MIT](./LICENSE-MIT) | `LICENSE-MIT` |
| **Документация и проза** (этот README, переведённые README, тексты CLI-помощи, prompt-файлы, легенда digest, дизайн-доки) | [CC BY 4.0](./LICENSE-DOCS) | `LICENSE-DOCS` |

Все три лицензии — пермиссивные. Можно форкать, использовать коммерчески, портировать на другие языки, поставлять в продукте. Разделение нужно лишь для того, чтобы **требования атрибуции были явными** для каждого типа контента. Форки 0.5.x-ветки могут продолжать жить под MIT; новая разработка идёт под Apache 2.0.

### Если переиспользуете код (v0.6.0+)

Сохраняйте файлы `LICENSE` (Apache 2.0) и `NOTICE` в дистрибутиве. Apache 2.0 §4 требует:

- включить `LICENSE` в дистрибутив
- включить `NOTICE` в любой "NOTICE" текстовый файл, поставляемый с вашей работой
- сохранять attribution-уведомления (нельзя удалять copyright-заголовок)
- в изменённых файлах добавлять уведомление, что вы внесли изменения

### Если переиспользуете прозу

Если ваш проект копирует нетривиальные фрагменты документации — абзацы, workflow-сниппеты, легенду digest, словарь маркеров, формулировки конвенции `# note:` для CLI — CC BY 4.0 требует **видимой атрибуции**. Формат (используйте дословно или эквивалентно):

> Based on [ast-outline](https://github.com/ast-outline/ast-outline) by Dmitrii Zaitsev (dim-s), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Размещайте там, где это увидят пользователи (обычно — README производного проекта).

### Торговая марка

**ast-outline™** — незарегистрированная торговая марка Dmitrii Zaitsev (dim-s), используется для идентификации оригинального проекта по адресу <https://github.com/ast-outline/ast-outline>. Apache License 2.0 §6 явно исключает любой грант на торговые марки. **Форки, языковые порты и ребрендинговые дистрибутивы должны использовать другое имя** во избежание путаницы у пользователей. Формулировки «inspired by ast-outline» или «based on ast-outline» в README — допустимы и приветствуются; использование самого имени `ast-outline` для своего проекта / пакета / бинарника — нет.

Если вы поддерживаете публичный пакет с именем `ast-outline` на любом реестре (crates.io, npm, PyPI, Homebrew и т.д.), который **не является** проектом по ссылке выше — пожалуйста, переименуйте его.
