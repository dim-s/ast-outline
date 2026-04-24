# ast-outline

[English](./README.md) · [Русский](./README.ru.md) · **简体中文**

> **v0.3.0 已由 `code-outline` 重命名** 为 `ast-outline`，以加入 [ast-grep](https://github.com/ast-grep/ast-grep) 推广的 `ast-*` 家族命名约定。旧 CLI 命令 `code-outline` 在 0.4.x 期间继续作为向后兼容别名保留。

> 基于 AST 的快速源码**结构化大纲**工具 —— 输出类、方法和签名及其行号范围，
> **不包含方法体**。专为大模型编码代理（LLM coding agents）设计：先看清文件
> 的"骨架"，再决定要不要读完整内容。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status: beta](https://img.shields.io/badge/status-beta-orange.svg)

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
4. **AST 精准匹配，不是模糊查找。** `implements` 和 `show` 基于真正的
   语法树工作 —— 不会把注释或字符串里的名字当成结果。
5. **零基础设施。** 没有索引、没有缓存、没有 embeddings、没有网络请求。
   实时、永远新鲜、对仓库零侵入。

### 典型 Agent 工作流

**没有 `ast-outline` 之前：**

```
Agent: Read Player.cs            # 1200 行 token
Agent: Read Enemy.cs             # 800 行 token
Agent: Read DamageSystem.cs      # 400 行 token
Agent: grep "IDamageable" src/   # 噪声多，很多误匹配
...
```

**用了 `ast-outline` 之后：**

```
Agent: ast-outline digest src/Combat         # ~100 行，整个模块一览
Agent: ast-outline implements IDamageable    # 精准列表，无 grep 噪声
Agent: ast-outline show Player.cs TakeDamage # 只取需要的方法体
```

结果：**同等的代码理解度，token 量和往返次数都是原来的零头。**

---

## 支持的语言

| 语言 | 扩展名 |
| --- | --- |
| C#         | `.cs` |
| Python     | `.py`、`.pyi` |
| TypeScript | `.ts`、`.tsx` |
| JavaScript | `.js`、`.jsx`、`.mjs`、`.cjs`（由 TypeScript 语法解析） |
| Java       | `.java` —— 类、接口、`@interface`、枚举、记录（record）、sealed 继承层级、泛型、throws、Javadoc |
| Kotlin     | `.kt`、`.kts` —— 类、接口、`fun interface`、`object` / `companion object`、`data` / `sealed` / `enum` / `annotation` 类、扩展函数、`suspend` / `inline` / `const` / `lateinit`、带 `where` 约束的泛型、`typealias`、KDoc |
| Scala      | `.scala`、`.sc` —— Scala 2 + Scala 3：类、trait、`object` / `case object`、`case class`、`sealed` 继承层级、Scala 3 `enum` / `given` / `using` / `extension`、缩进式语法体、higher-kinded 类型、context bound、`opaque type`、类型别名、Scaladoc |
| Markdown   | `.md`、`.markdown`、`.mdx`、`.mdown` —— 标题目录 + 代码块 |

新增语言只需要加一个适配器文件。见
[`src/ast_outline/adapters/`](src/ast_outline/adapters/)。

---

## 安装

### 一行命令（推荐 —— macOS / Linux / Windows）

需要 [`uv`](https://docs.astral.sh/uv/)（一个快速的 Python 包管理器）：

```bash
uv tool install git+https://github.com/dim-s/ast-outline.git
```

这会把 `ast-outline` CLI 全局安装到 `~/.local/bin`（Mac / Linux）或
`%USERPROFILE%\.local\bin`（Windows）—— 确保该目录在你的 `PATH` 中。

还没装 `uv`？

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 使用仓库里的安装脚本

```bash
# macOS / Linux
curl -LsSf https://raw.githubusercontent.com/dim-s/ast-outline/main/scripts/install.sh | bash

# Windows (PowerShell)
iwr -useb https://raw.githubusercontent.com/dim-s/ast-outline/main/scripts/install.ps1 | iex
```

### 备选：`pipx`

```bash
pipx install git+https://github.com/dim-s/ast-outline.git
```

### 备选：`pip`（在已激活的 venv 中）

```bash
pip install git+https://github.com/dim-s/ast-outline.git
```

### 升级 / 卸载

```bash
uv tool upgrade ast-outline
uv tool uninstall ast-outline
```

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

# 找出所有继承/实现指定类型的类
ast-outline implements IDamageable src/

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
`.scala`、`.sc` 和 `.md` 文件，先用 `ast-outline` 读结构，再考虑打开完整内容。
方法体只在你已经确定需要某一个时才去取。

哪一步能回答问题就停在哪一步：

1. **不熟悉的目录** —— `ast-outline digest <dir>`：一页地图，列出每个
   文件的类型和公共方法。

2. **单个文件的结构** —— `ast-outline <file>`：签名 + 行号范围，不含
   方法体（比完整读取少用 5–10 倍 token）。

3. **某个方法 / 类 / markdown 段落** —— `ast-outline show <file> <Symbol>`。
   后缀匹配：`TakeDamage`，有歧义时用 `Player.TakeDamage`。一次取多个：
   `ast-outline show Player.cs TakeDamage Heal Die`。markdown 的符号名
   就是标题文本。

4. **谁继承/实现了某个类型** —— `ast-outline implements <Type> <dir>`：
   基于 AST（不用 `grep`），默认是传递性的 —— 间接匹配会带 `[via Parent]`
   标记。加 `--direct` 只显示直接子类。

只有当 `show` 给出的方法体不足以提供所需上下文时，才回退到完整读取。

如果 outline 头部包含 `# WARNING: N parse errors`，说明该文件的 outline
是不完整的 —— 直接读取受影响区域的源码。

`ast-outline help` 查看完整标志和冷门选项。
```

### 为什么有效

- **上下文较浅的新 Agent**（比如 Claude Code 的 `Explore`）可以用一次调用
  扫完整个模块，而不是 10–20 次 `Read`/`grep` 往返。
- **"X 定义在哪？"** 变成一次 `implements` 或 `show` 调用。
- **行号范围**（`L42-58`）把 outline 变成精确的导航器 —— Agent 只读
  必要的那几行。
- **基于 AST 的 `implements`** 不会被字符串字面量、注释或无关的同名
  引用误导 —— 和 `grep` 完全不同。

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
- `--glob PATTERN` —— 自定义目录模式下的匹配规则

### `show` —— 按符号名取出源码

```bash
ast-outline show File.cs TakeDamage
ast-outline show File.cs PlayerController.TakeDamage   # 区分重载
ast-outline show service.py UserService.get
ast-outline show File.cs TakeDamage Heal Die           # 一次多个
```

匹配采用**后缀方式**：`Foo.Bar` 可匹配任何 `*.Foo.Bar`。如有多个匹配，
会全部打印并附带摘要。

### `digest` —— 模块单页地图

```bash
ast-outline digest src/
```

示例输出：

```
src/services/
  user_service.py (140 lines)
    class UserService : IUserService  L8-138
      +get  +search  +create  +delete  +update
  auth_service.py (95 lines)
    class AuthService  L10-95
      +login  +logout  +refresh  +verify_token
```

### `implements` —— 找出子类 / 实现

```bash
ast-outline implements IDamageable src/
```

基于 AST —— 不会被注释或无关引用干扰。**默认是传递性的**：如果
`Puppy extends Dog extends Animal`，那么 `implements Animal` 会返回这三者，
间接匹配会被附上链路注释：

```
# 3 match(es) for 'Animal' (incl. transitive):
src/Animals.cs:5   class Dog : Animal
src/Cats.cs:3      class Cat : Animal
src/Puppies.cs:12  class Puppy : Dog          [via Dog]
```

加上 `--direct` / `-d` 可以只限定为直接子类（第一层）：

```bash
ast-outline implements --direct IDamageable src/
```

搜索可以跨任意数量的文件和嵌套目录 —— 不依赖「文件名 = 类名」的约定。
按类型名的最后一段匹配（泛型和 namespace 前缀会被剥离）。

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
git clone https://github.com/dim-s/ast-outline.git
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

套件（400+ 个测试）覆盖全部适配器（C#、Python、TypeScript/JS、Java、
Kotlin、Scala、Markdown）、与语言无关的渲染器、符号搜索以及端到端的
CLI。Fixture 放在 `tests/fixtures/`，测试不会越出该目录。任何新行为都
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
- [x] Markdown 适配器（`.md`、`.markdown`、`.mdx`、`.mdown`）—— 标题目录 + 代码块
- [ ] Go 适配器
- [ ] Rust 适配器
- [ ] `--format json` —— 方便程序化消费
- [ ] 针对超大代码库（>500 文件）的可选 multiprocessing

欢迎 PR。

---

## 许可证

[MIT](./LICENSE)
