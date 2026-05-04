# ast-outline

[English](./README.md) · [Русский](./README.ru.md) · **简体中文**

> 基于 AST 的快速源码**结构化大纲**工具 —— 输出类、方法和签名及其行号范围，
> **不包含方法体**。专为大模型编码代理（LLM coding agents）设计：先看清文件
> 的"骨架"，再决定要不要读完整内容。
>
> 与 [ast-grep](https://github.com/ast-grep/ast-grep) 同属 `ast-*` 家族：
> **`ast-grep` 用于结构化*搜索*** 代码，**`ast-outline` 用于结构化*概览*** 代码。

[![Code: Apache 2.0](https://img.shields.io/badge/code-Apache%202.0-blue.svg)](./LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](./LICENSE-DOCS)
[![PyPI](https://img.shields.io/pypi/v/ast-outline.svg)](https://pypi.org/project/ast-outline/)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status: beta](https://img.shields.io/badge/status-beta-orange.svg)

📖 **文档:** <https://ast-outline.github.io/> · **站点源码:** [ast-outline/ast-outline.github.io](https://github.com/ast-outline/ast-outline.github.io)

> **ast-outline™** —— Dmitrii Zaitsev（dim-s）。原始项目：
> <https://github.com/ast-outline/ast-outline>（创建于 2026-04-22）。代码采用
> **Apache 2.0** 许可（v0.6.0 起；v0.5.x 及更早版本仍可在 MIT 下使用），
> 文档采用 **CC BY 4.0** —— 复用本 README 的文字内容须显式署名。
> 详见下方 [许可与署名](#许可与署名) 一节。

---

## 项目目的

**`ast-outline` 的存在是为了让大模型编码代理在浏览陌生代码库时更快、更省钱、更聪明。**

现代的 Agent 编码工具（Claude Code、Cursor 的 Agent 模式、Aider、Copilot Chat、
自建 CLI Agent）都是通过**直接读取文件**来探索代码库 —— 而不是靠 embeddings
或向量检索。这种方式可靠，但代价高：一个 1000 行的文件，Agent 为了回答
*"这里有哪些方法？"* 就得花费 1000 行的 token。

`ast-outline` 填平了这个缺口。它是给 Agent 的**预读层**：

1. **Token 节省 —— 通常 5–10 倍。** 当 Agent 只需要结构层面的理解时，
   用 outline 代替完整文件读取。
2. **更快的探索。** 整个模块的公共 API 一屏就能看完。
3. **精确定位。** 每个声明都带有行号范围（`L42-58`）。Agent 可以直接跳到
   它需要的方法体。
4. **AST 精准匹配，不是模糊查找。** `show` 和带继承关系的类型头基于真正的
   语法树工作 —— 不会把注释或字符串里的名字当成结果。
5. **零基础设施。** 没有索引、没有缓存、没有 embeddings、没有网络请求。
   实时、永远新鲜、对仓库零侵入。

### 典型 Agent 工作流

**没有 `ast-outline` 之前：**

```
Agent: Read Player.cs            # 1200 行 token
Agent: Read Enemy.cs             # 800 行 token
Agent: Read DamageSystem.cs      # 400 行 token
...
```

**用了 `ast-outline` 之后：**

```
Agent: ast-outline digest src/Combat         # ~100 行，整个模块一览
Agent: ast-outline Player.cs                 # 仅签名，5–10× 更小
Agent: ast-outline show Player.cs TakeDamage # 只取需要的方法体
```

结果：**同等的代码理解度，token 量和往返次数都是原来的零头。**

---

## 设计哲学

> **Stateless（无状态）。无索引、无缓存、无 embeddings、无网络。**
> 按需解析、打印、退出。

与 RAG 风格的代码库索引器（Cursor、Bloop、Continue、那一片基于
embeddings 的 MCP 服务器）相反。现代 LLM Agent 足够聪明，能将
`ast-outline` 与 `grep`、`find`、`ast-grep` 等 unix 工具串联起来，在
真实代码中快速导航 —— 无需完整读取文件，也无需让本地索引为自己的复杂性
付费。

`ast-outline` 自身也不做 MCP 服务器 —— 对一个 stateless CLI，Agent 在
`bash` 里串管道、并行调用，比通过 MCP 包装层调用同一组命令更有杠杆。

---

## 支持的语言

| 语言       | 扩展名 |
| ---        | --- |
| C#         | `.cs` |
| Python     | `.py`、`.pyi` |
| TypeScript | `.ts`、`.tsx` |
| JavaScript | `.js`、`.jsx`、`.mjs`、`.cjs` *（由 TypeScript 语法解析）* |
| Java       | `.java` |
| Kotlin     | `.kt`、`.kts` |
| Scala      | `.scala`、`.sc` |
| Go         | `.go` |
| Rust       | `.rs` |
| Markdown   | `.md`、`.markdown`、`.mdx`、`.mdown` |
| YAML       | `.yaml`、`.yml` |

<details>
<summary>各适配器识别的语法</summary>

- **Java** —— 类、接口、`@interface`、枚举、记录（record）、sealed 继承层级、泛型、throws、Javadoc。
- **Kotlin** —— 类、接口、`fun interface`、`object` / `companion object`、`data` / `sealed` / `enum` / `annotation` 类、扩展函数、`suspend` / `inline` / `const` / `lateinit`、带 `where` 约束的泛型、`typealias`、KDoc。
- **Scala** —— Scala 2 + Scala 3：类、trait、`object` / `case object`、`case class`、`sealed` 继承层级、Scala 3 `enum` / `given` / `using` / `extension`、缩进式语法体、higher-kinded 类型、context bound、`opaque type`、类型别名、Scaladoc。
- **Go** —— 包、结构体（方法按 receiver 分组）、接口、struct/interface 嵌入作为「继承」、泛型（Go 1.18+）、类型别名 + defined type、`iota` 枚举块、文档注释链。
- **Rust** —— 模块（递归）、结构体（普通 / 元组 / 单元）、unions、覆盖所有 variant 形式的 enum、trait（supertraits → bases）、**`impl` 块按目标类型重新分组**（inherent + `impl Trait for Foo` 将 Trait 加入 bases）、`extern "C"` 块、`macro_rules!`、类型别名、泛型 + 生命周期 + `where` 子句、可见性分类（`pub` / `pub(crate)` / `pub(super)` / `pub(in path)`）、外部文档注释 + `#[...]` 属性。
- **Markdown** —— 标题目录 + 代码块。
- **YAML** —— 键层级（含行范围）、`[i]` 序列索引路径、多文档分隔符、Kubernetes / OpenAPI / GitHub Actions 头部格式自动识别。

</details>

新增语言只需要加一个适配器文件。见
[`src/ast_outline/adapters/`](src/ast_outline/adapters/)。

---

## 安装

```bash
uv tool install ast-outline
```

将 `ast-outline` CLI 全局安装到 `~/.local/bin`（macOS / Linux）或
`%USERPROFILE%\.local\bin`（Windows）。还没装 [`uv`](https://docs.astral.sh/uv/)？

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                                          # macOS / Linux
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"       # Windows
```

升级 / 卸载：`uv tool upgrade ast-outline` / `uv tool uninstall ast-outline`。

<details>
<summary>其他安装方式（pipx、pip、源码安装、一键脚本）</summary>

```bash
pipx install ast-outline
pip  install ast-outline                                          # 在已激活的 venv 中

# 安装 main 分支最新代码，而不是 PyPI 发布版：
uv tool install git+https://github.com/ast-outline/ast-outline.git

# 一键安装脚本（如未安装 uv 会顺带安装）：
curl -LsSf https://raw.githubusercontent.com/ast-outline/ast-outline/main/scripts/install.sh | bash    # macOS / Linux
iwr -useb https://raw.githubusercontent.com/ast-outline/ast-outline/main/scripts/install.ps1 | iex     # Windows
```

</details>

---

## 快速上手

```bash
# 单个文件的结构化大纲
ast-outline path/to/Player.cs
ast-outline path/to/user_service.py

# 整个目录（递归查找所有受支持的扩展名）
ast-outline src/

# 打印某个具体方法的源码
ast-outline show Player.cs TakeDamage

# 一次提取多个方法
ast-outline show Player.cs TakeDamage Heal Die

# 整个模块的公共 API 精简视图
ast-outline digest src/Services

# 内置帮助
ast-outline help
ast-outline help show
```

---

## 配合 LLM 编码代理使用

**这是本工具的主要使用场景。** 把下面的片段加到你的 `CLAUDE.md`、
`AGENTS.md`、子 Agent 配置或任何引导编码 Agent 的系统提示里。之后
Agent 就会优先用 `ast-outline` 而不是直接读完整文件。

同样的片段也随工具一起发布 —— `ast-outline prompt` 会原样打印它，
不用手动复制就能直接追加到项目的 agent 配置里：

```bash
ast-outline prompt >> AGENTS.md
ast-outline prompt >> .claude/CLAUDE.md
ast-outline prompt | pbcopy   # macOS 剪贴板
```

### 提示词片段（直接复制）

```markdown
## 代码探索 —— 优先用 `ast-outline`，而不是完整读取

对于 `.cs`、`.py`、`.pyi`、`.ts`、`.tsx`、`.js`、`.jsx`、`.java`、`.kt`、`.kts`、
`.scala`、`.sc`、`.go`、`.rs`、`.md` 和 `.yaml`/`.yml` 文件，先用 `ast-outline`
读结构，再考虑打开完整内容。

从下面三个工具中选最小的那个，能回答你的问题就够了——这是一个
"从粗到细"的菜单，不是必须按顺序执行的步骤；如果已经知道符号名，
直接跳到 `show`：

1. **不熟悉的目录** —— `ast-outline digest <paths…>`：一页地图，列出每个
   文件的类型和公共方法。每个文件后会附带大小标签
   —— `[tiny]` / `[medium]` / `[large]` —— 当解析遇到错误、outline
   可能不完整时再加 `[broken]`。

2. **文件级结构** —— `ast-outline <paths…>`:签名 + 行号范围,不含
   方法体(对非平凡文件,比完整读取少用 5–10 倍 token)。如果头部出现
   `# WARNING: N parse errors`,说明 outline 是不完整的 —— 直接读取受影响
   区域的源码。

3. **某个方法 / 类型 / markdown 标题 / yaml 键** —— `ast-outline show <file>
   <Symbol>`。后缀匹配:`TakeDamage` 取单个方法;`User` 取整个类型的
   完整主体 —— class、struct、interface、trait、enum(当一个文件里
   有多个类型时尤其有用);有歧义时用 `Player.TakeDamage`。一次取多个:
   `ast-outline show Player.cs TakeDamage Heal Die`。
   markdown 的符号是标题文本,匹配为大小写不敏感的子串:`"installation"`
   能命中 `"2.1 Installation (macOS / Linux)"`。yaml 的符号是点分键路径
   (`spec.containers[0].image`) —— `show` 匹配**键**,不匹配值;要在值的
   文本里做自由搜索请用 `grep`。
   给以上任一形式加 `--signature` 只返回头部(docs + 属性 + 签名,
   不带方法体)—— 在 `digest` 之后,当你已经有符号名、只需契约而非实现时
   使用。

`outline` 和 `digest` 都支持一次传入多个路径(文件和目录,混合语言均可)
—— 一次性批量调用,不要循环。两个渲染器的类型头都会带上 `: Base, Trait`
形式的继承关系,所以无需单独查询就能看到类层次结构的形态。

当你需要知道**某个文件拉了什么进来**,或**被引用的类型 / 函数住在哪里**
时,给 `outline` 或 `digest` 加上 `--imports`。文件头会多出一行
`imports:`,按文件本身的语言语法逐条列出 `import` / `use` / `using`
语句 —— `from .core import X`、`use foo::Bar`、
`import { X } from './foo'`。读完这一行直接对源文件调用
`outline` / `show`,不用再 `grep` 找定义。常规读结构时不要带这个
flag —— 它每个文件多出一行。

只有当 `show` 给出的方法体不足以提供所需上下文时,才回退到完整读取。
`ast-outline help` 查看完整标志。
```

### 注意：子 Agent

`CLAUDE.md` / `AGENTS.md` 只能影响**主 Agent**。Claude Code 的隔离子 Agent
（内置 `Explore`、`.claude/agents/*.md` 里的任何文件）只能看到自己的
system prompt。要让 `Explore` 用上 `ast-outline`，请用
`.claude/agents/Explore.md`（或 `~/.claude/agents/Explore.md`）覆盖它，
并把 `ast-outline prompt` 的输出放进 body。

Cursor、Aider 和直接调用 API 的客户端没有嵌套子 Agent —— 在那里
`CLAUDE.md` / system prompt 就够了。

### 为什么有效

- **上下文较浅的新 Agent**（比如 Claude Code 的 `Explore`）可以用一次调用
  扫完整个模块，而不是 10–20 次 `Read`/`grep` 往返。
- **"X 定义在哪？"** 一旦 Agent 在 `digest` 或 `outline` 中看到符号，
  一次 `show` 调用就能拿到。
- **行号范围**（`L42-58`）把 outline 变成精确的导航器 —— Agent 只读
  必要的那几行。
- **基于 AST 的类型头** 携带真实的 `: Base, Trait` 继承关系，不会被字符串
  字面量、注释或无关的同名引用误导 —— 和 `grep` 完全不同。

### 适用对象

- Claude Code（以及自建子 Agent：`Explore`、`codebase-scout`）
- Cursor 的 Agent 模式
- Aider
- Copilot Chat / Workspace
- 任何基于 Claude / OpenAI / Gemini API 的自建 Agent
- 人类开发者（格式易读；`show` 是 `grep -A 20` 的更好替代）

---

## 命令

### `outline` —— 默认命令

打印文件中的类、方法、属性、字段及其行号范围。

```bash
ast-outline path/to/File.cs
ast-outline path/to/module.py --no-private --no-fields
```

选项：

- `--no-private` —— 隐藏私有成员（Python 中以 `_` 开头的名称）
- `--no-fields` —— 隐藏字段声明
- `--no-docs` —— 隐藏 `///` XML 文档注释和 docstring
- `--no-attrs` —— 隐藏 `[Attributes]` 和 `@decorator`
- `--no-lines` —— 隐藏行号后缀
- `--imports` —— 显示文件的 imports（详见下文）
- `--glob PATTERN` —— 自定义目录模式下的匹配规则

#### `--imports` —— 查看每个文件依赖什么

`outline` 与 `digest` 都接受 `--imports`。开启后，文件头之后会多出一行
`imports:`，按文件原本的语言语法逐条列出 `import` / `use` / `using`
语句 —— 没有需要 agent 单独学习的合成格式：

```
$ ast-outline service.py --imports
# src/services/user_service.py (140 行, ~1,200 tokens, 1 types, 5 methods)
# imports: from .core import UserBase; from .utils import parse_id; from typing import Optional
class UserService(UserBase):  L8-138
    ...
```

多行与分组形式会被展平：Go 的 `import (...)` 块拆成独立的
`import "fmt"` 行；多行 TS 的 `import { X, Y } from './long'`
合并到同一行。函数体或类体内部的 import 不会出现在列表里 —— 只展示
文件级依赖。

当 agent 想确认某个被引用的类型在哪里、或某个文件到底拉了什么进来再决定下一步读哪个文件时很有用。

### `show` —— 按符号名取出源码

```bash
ast-outline show File.cs TakeDamage
ast-outline show File.cs PlayerController.TakeDamage   # 区分重载
ast-outline show service.py UserService.get
ast-outline show File.cs TakeDamage Heal Die           # 一次多个
```

代码采用**后缀匹配**：`Foo.Bar` 可匹配任何 `*.Foo.Bar`。如有多个匹配，
会全部打印并附带摘要。

markdown 改用**大小写不敏感的子串**匹配，按点号路径的每一段子串进行包含检查。
LLM agent 通常无法准确记住标题装饰（数字前缀 `1.`、尾随的 `(Feb 2026)`、
`(Confidence: 70%)` 等），因此「凭意思」即可命中：

```bash
ast-outline show forecast.md "current analysis"
# → 命中 `## 1. CURRENT ANALYSIS (Feb 2026)`

ast-outline show forecast.md "scenario.transit"
# → 命中任意带 "scenario" 字样的父标题下的
#   `### SCENARIO A: "MANAGED TRANSIT"`
```

若子串命中多个标题，全部打印，stderr 输出消歧摘要，可再缩窄查询。

### `digest` —— 模块单页地图

```bash
ast-outline digest src/
```

示例输出：

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

  legacy_repo.py [large] (5234 lines, ~52,000 tokens, ...)
```

第一行是自描述的图例（legend），让 LLM 在没有加载 `ast-outline prompt`
的情况下也能直接读懂输出。图例是**动态的**——只列出输出正文中实际
出现的 token。如果 batch 只包含 YAML 或 markdown 文件（没有 callable、
没有 kind 标签、没有继承），则完全不输出图例；代码 batch 的图例也只
保留实际使用到的 token 子集。token 遵循通用编程文档约定：`name()` 表示
可调用，`name [kind]` 表示属性/字段/事件等非可调用项，方法修饰符
（`async`、`static`、`abstract`、`override`、`virtual`，以及语言原生
形式：Kotlin 的 `open` / `suspend`、Python 的 `@staticmethod` /
`@classmethod` / `@abstractmethod`、Java 的 `@Override`）以前缀方式
原样附加在方法名前——每种语言保留自己的惯用形态。`[N overloads]`
表示多个同名可调用项被合并，`[deprecated]` 表示类型/成员被标记为
`@Deprecated` / `[Obsolete]` / `#[deprecated]`。类型行首还会带上
内联装饰器/属性（`@dataclass`、`[ApiController]`、`#[derive(Debug)]`）
和语义修饰符（`abstract`、`sealed`、`static`、`final`、`open`、
`partial`）——运行时合约和实例化规则一眼可见。成员之间用 `, ` 分隔；
有方法体的类型末尾会加一个空行作为段落分隔，空类型紧凑堆叠以保持
digest 的紧凑性。源语言关键字（Rust 的 `trait`、Scala 的 `object`、
Kotlin 的 `data class`）会保留在类型行首，而不是替换成统一的
canonical kind。

每个文件名后会附带一个描述性的大小标签：`[tiny]`（≲500 tokens）、
`[medium]`（500–5000）、`[large]`（5000+）。标签**描述**文件大小，
不规定具体动作。LLM agent 读取标签，结合任务（需要整个文件？某个段落？
只看结构？）自行选择 Read / outline / show ——工具提供信息，agent 做判断。

大小估算基于 `len(chars)/4`（与真实 BPE 分词器误差 ±15-20%），对于大小
分类足够。同一个 `~N tokens` 计数也出现在每次 `outline` 输出的文件头中，
无论 agent 是否先跑过 `digest` 都能拿到尺寸信号。

### `prompt` —— 打印 LLM agent 提示片段

```bash
ast-outline prompt
ast-outline prompt >> AGENTS.md
```

打印规范的复制粘贴片段，用于引导 LLM 编码 agent 优先使用 `ast-outline`
而不是完整读取。英文，跨 Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5 通用。
每次运行都能拿到当前版本的推荐片段。

---

## 输出格式

格式专为**大模型友好**设计：Python 风格缩进、`L<start>-<end>` 形式的行号
后缀、保留文档注释。头部行汇总了文件规模并标记部分解析的情况。

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

### 带祖先上下文的 `show`

`ast-outline show <file> <Symbol>` 会在头部和方法体之间打印一行
`# in: ...` 面包屑 —— 列出所属的 namespace/类链路，这样你无需再次调用
`outline` 就能知道提取出来的代码嵌套在哪里：

```
# Player.cs:30-48  Game.Player.PlayerController.TakeDamage  (method)
# in: namespace Game.Player → public class PlayerController : MonoBehaviour, IDamageable
/// <summary>Apply damage.</summary>
public void TakeDamage(int amount) { ... }
```

顶层符号（没有外层 namespace/类型）不输出面包屑行。

### 部分解析

当 tree-sitter 从语法错误中恢复时，outline 仍然会产出，但头部会增加
第二行来标记这种情况：

```
# broken.java (16 lines, 1 types, 3 methods)
# WARNING: 3 parse errors — output may be incomplete
```

代理对这类文件应当把 outline 视为不完整的，针对受影响的区域直接读取
源码。

差异符合各语言的惯例：

- C# 的 `///` XML 文档注释在签名**上方**。
- Python 的 `"""docstring"""` 在签名**下方**并多一级缩进（和它在
  body 中的实际位置一致）。
- C# 的 `[Attr]` 和 Python 的 `@decorator` 和声明内联。
- C# 属性的访问器 `{ get; private set; }` 完整保留。

---

## 工作原理（简述）

- 使用 [tree-sitter](https://tree-sitter.github.io/) 解析源码 ——
  真正的 AST，不是正则。
- 语言专用的适配器把 AST 转换成统一的 `Declaration` 中间表示。
- 语言无关的渲染器负责产出 outline / digest / search 结果。
- 纯本地，无网络、无索引、无缓存 —— 只读你明确请求的文件。

没有向量数据库、没有 embeddings、没有 RAG。这是刻意的设计 —— 和 Claude
Code 这类 Agent 编码工具的真实工作方式保持一致。

---

## 本地开发

```bash
git clone https://github.com/ast-outline/ast-outline.git
cd ast-outline

# 创建 venv 并以 editable 模式安装
uv venv
uv pip install -e .

# 在仓库自带的样本上试运行
.venv/bin/ast-outline tests/sample.cs
.venv/bin/ast-outline tests/sample.py
.venv/bin/ast-outline digest tests/
```

### 运行测试

测试属于可选的开发依赖，最终用户不会被拉入。装一次之后通过 `pytest`
运行即可：

```bash
# 把 pytest 装进同一个 venv
uv pip install -e ".[dev]"

# 跑完整套件（约 0.1 秒）
.venv/bin/pytest

# 只跑一个文件，详细输出
.venv/bin/pytest tests/unit/test_csharp_adapter.py -v

# 按名字过滤
.venv/bin/pytest -k file_scoped_namespace -v
```

套件（600+ 个测试）覆盖全部适配器（C#、Python、TypeScript/JS、Java、
Kotlin、Scala、Go、Rust、Markdown、YAML）、与语言无关的渲染器、符号搜索
以及端到端的 CLI。Fixture 放在 `tests/fixtures/`，测试不会越出该目录。任何新行为都
应带上测试；新增语言时也应附带独立的 fixture 目录和一份
`tests/unit/test_<lang>_adapter.py`。

### 新增一门语言

在 `src/ast_outline/adapters/<lang>.py` 创建新文件，实现
`LanguageAdapter` 协议（见 `adapters/base.py`）。然后在
`adapters/__init__.py` 中注册即可。核心渲染器和 CLI 会自动识别，
无需其他接线。

---

## 路线图

- [x] TypeScript / JavaScript 适配器（`.ts`、`.tsx`、`.js`、`.jsx`、`.mjs`、`.cjs`）
- [x] Java 适配器（`.java`）—— 类、接口、`@interface`、枚举、记录（record）、sealed 继承层级、泛型、throws、Javadoc
- [x] Kotlin 适配器（`.kt`、`.kts`）—— 类、接口、`fun interface`、`object` / `companion object`、`data` / `sealed` / `enum` / `annotation` 类、扩展函数、`suspend` / `inline` / `const` / `lateinit`、带 `where` 约束的泛型、`typealias`、KDoc
- [x] Scala 适配器（`.scala`、`.sc`）—— Scala 2 + Scala 3：类、trait、`object` / `case object`、`case class`、`sealed` 继承层级、Scala 3 `enum` / `given` / `using` / `extension`、缩进式语法体、higher-kinded 类型、context bound、`opaque type`、类型别名、Scaladoc
- [x] Go 适配器（`.go`）—— 包、结构体（方法按 receiver 分组）、接口、struct/interface 嵌入作为「继承」、泛型（Go 1.18+）、类型别名 + defined type、`iota` 枚举块、文档注释链
- [x] Rust 适配器（`.rs`）—— 模块（递归）、结构体（普通 / 元组 / 单元）、unions、覆盖所有 variant 形式的 enum、trait（supertraits → bases）、**`impl` 块按目标类型重新分组**（inherent + `impl Trait for Foo` 将 Trait 加入 bases）、`extern "C"` 块、`macro_rules!`、类型别名、泛型 + 生命周期 + `where` 子句、可见性分类（`pub` / `pub(crate)` / `pub(super)` / `pub(in path)`）、外部文档注释 + `#[...]` 属性
- [x] Markdown 适配器（`.md`、`.markdown`、`.mdx`、`.mdown`）—— 标题目录 + 代码块
- [x] YAML 适配器（`.yaml`、`.yml`）—— 键层级、`[i]` 序列索引路径、多文档支持、Kubernetes / OpenAPI / GitHub Actions 头部格式识别
- [ ] `--format json` —— 方便程序化消费
- [ ] 针对超大代码库（>500 文件）的可选 multiprocessing

欢迎 PR。

---

## 项目历史

- **2026-04-22** —— 仓库以 `dim-s/code-outline` 名称在 GitHub 创建。首个公开提交，v0.2.0b0。
- **2026-04-22** —— 添加俄文与中文 README；同日新增 TypeScript / JavaScript 适配器。
- **2026-04-23** —— Kotlin 适配器；`prompt` 子命令。
- **2026-04-24** —— Scala 适配器。**项目从 `code-outline` 改名为 `ast-outline`（v0.3.0）。** GitHub 仓库改名为 `dim-s/ast-outline`。
- **2026-04-25** —— Go 适配器。
- **2026-04-28** —— 面向 LLM 的错误约定：`# note: …` 输出到 stdout 且 `rc=0`；Markdown 标题支持子串匹配。
- **2026-04-30** —— YAML 适配器；digest 表头加入按文件 size 标签与 token 估算；Rust 适配器。
- **2026-05-01** —— v0.4.0：digest 方法标记（`[async]` / `[unsafe]` / `[const]` / `[suspend]` / `[static]` / `[abstract]` / `[override]` / `[classmethod]` / `[property]`）；类型修饰符、属性和 `[deprecated]` 标签。v0.4.1。
- **2026-05-02** —— 发布到 PyPI：[`ast-outline`](https://pypi.org/project/ast-outline/)。v0.4.2 / v0.4.3 / v0.5.0（删除 `code-outline` CLI 别名）/ v0.5.1（删除 `implements` 命令 —— outline/digest 已能渲染 `: Base`）/ v0.5.2（`--imports` 选项）/ v0.5.3（`--version` 选项）。
- **2026-05-03** —— **v0.6.0：从 MIT 切换为 Apache License 2.0**，文档另行采用 CC BY 4.0。原 MIT 文本保留在 `LICENSE-MIT` 中，便于 0.5.x 分支的下游 fork 继续使用。
- **2026-05-03** —— 仓库由 `dim-s/ast-outline` 迁移至 GitHub 组织 [`ast-outline`](https://github.com/ast-outline)。旧的 `dim-s/ast-outline` URL 仍然会自动重定向。著作权仍归 Dmitrii Zaitsev（dim-s）所有；GitHub 组织只是托管基础设施，并非新的著作权持有者。

完整历史请见 `git log` 与 [GitHub Releases](https://github.com/ast-outline/ast-outline/releases)。

---

## 许可与署名

Copyright © 2026 **Dmitrii Zaitsev**（GitHub: [dim-s](https://github.com/dim-s)）与 ast-outline 贡献者。

本项目采用 **三种不同的许可证** 覆盖不同类型的内容：

| 内容 | 许可证 | 文件 |
| --- | --- | --- |
| **源代码**（`src/`、测试、构建配置）—— v0.6.0 及之后版本 | [Apache 2.0](./LICENSE) | `LICENSE` |
| **源代码** —— v0.5.3 及更早版本 | [MIT](./LICENSE-MIT) | `LICENSE-MIT` |
| **文档与文字内容**（本 README、各语言版本 README、CLI 帮助文本、prompt 文件、digest 图例、设计文档） | [CC BY 4.0](./LICENSE-DOCS) | `LICENSE-DOCS` |

三种许可证都是宽松许可 —— 你可以 fork、商用、移植到其他语言、集成到自己的产品中。之所以拆分，是为了 **让每类内容的署名要求都变得明确**。0.5.x 分支的 fork 可继续使用 MIT；新功能开发在 Apache 2.0 下进行。

### 如果你复用代码（v0.6.0+）

请在分发包中保留 `LICENSE`（Apache 2.0）和 `NOTICE` 文件。Apache 2.0 §4 要求你：

- 在分发包中包含 `LICENSE` 文件
- 将 `NOTICE` 内容包含到任何随附的 "NOTICE" 文本文件中
- 保留署名声明（不得删除版权头）
- 在被你修改过的文件中加入说明，表明你做了修改

### 如果你复用文字内容

如果你的项目复制了文档中较实质的部分 —— 段落、workflow 示例片段、digest 图例、标记词汇表、CLI 中 `# note:` 约定的措辞 —— CC BY 4.0 要求 **显式署名**。格式（请逐字使用或采用等效表述）：

> Based on [ast-outline](https://github.com/ast-outline/ast-outline) by Dmitrii Zaitsev (dim-s), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

请放在用户能看到的位置（通常是衍生项目的 README）。

### 商标

**ast-outline™** 是 Dmitrii Zaitsev（dim-s）的未注册商标，用于指代位于 <https://github.com/ast-outline/ast-outline> 的原始项目。Apache License 2.0 §6 明确不授予任何商标权利。**Fork、语言移植和重新命名的发行版必须使用不同的项目名称**，以避免对用户造成混淆。在 README 中使用「inspired by ast-outline」或「based on ast-outline」之类的措辞是允许且鼓励的；但将 `ast-outline` 本身用作你自己的项目名／包名／二进制名是不允许的。

如果你在任何包注册表（crates.io、npm、PyPI、Homebrew 等）维护着名为 `ast-outline` 但 **并非** 上述链接所指项目的发布包，请考虑改名。
