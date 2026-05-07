# ARCHITECTURE.md — ins-cli 技术架构详解

## 这个项目是什么？

ins-cli 是一个 Instagram 命令行工具，它能让你在终端里操作 Instagram：
- **读取**（查看资料、搜索用户、下载图片）→ 用 HTTP API 请求
- **写入**（发帖、发 Story、评论）→ 用浏览器自动化

为什么读写要用两种不同的方式？下面逐步解释。

---

## 核心概念

### 1. CLI（Command Line Interface）

CLI 就是"命令行界面"。你在终端输入 `ins profile zuck`，程序帮你查用户资料。

```
你输入命令 → argparse 解析 → 调用对应函数 → 返回结果
```

本项目用 Python 的 `argparse` 库来解析命令。`argparse` 做两件事：
- **生成 --help 帮助信息**（展示有哪些命令和参数）
- **解析你输入的命令**（把 `ins profile zuck` 解析成"调用 profile 功能，参数是 zuck"）

相关文件：`src/ins_cli/cli.py`

### 2. HTTP API 请求 vs 浏览器自动化

这是本项目最核心的设计选择。

#### HTTP API 请求（读取用）

```
你的电脑 → 直接发 HTTP 请求 → Instagram 服务器 → 返回 JSON 数据
```

就像你在浏览器地址栏输入一个网址，服务器返回数据。Python 用 `requests` 库来做这件事。

**优点**：快、轻量、不需要打开浏览器
**缺点**：只能做 Instagram 允许的操作（读取资料、搜索等），发帖的 API Instagram 没有公开

相关文件：`src/ins_cli/reader.py`

#### 浏览器自动化（写入用）

```
你的电脑 → 控制 Chrome 浏览器 → 打开发帖页面 → 模拟点击按钮 → 完成
```

就像有一个机器人在帮你操作浏览器。Python 用 `Playwright` 库来控制浏览器。

**优点**：能做任何人类能做的事（发帖、发 Story 等）
**缺点**：需要打开浏览器，速度较慢

相关文件：`src/ins_cli/writer.py`、`src/ins_cli/browser.py`

### 3. Cookie（身份凭证）

当你登录 Instagram 后，浏览器会保存一个叫 Cookie 的小文件。Cookie 里包含你的登录信息。

```
Instagram 服务器 → "你是谁？" → 你的浏览器出示 Cookie → "哦，是你，进来吧"
```

本项目需要你的 Cookie 来证明身份：
- **读取**：从 Cookie 文件中读取，附在 HTTP 请求中发送
- **写入**：直接复用你 Chrome 浏览器中已登录的会话（不需要单独管理 Cookie）

相关文件：`src/ins_cli/auth.py`

### 4. 适配器（Adapter）

适配器是一个设计模式——把"不同的操作方式"统一成一个接口。

```
ins profile zuck   → reader.py 里的 get_profile()
ins post photo.jpg → writer.py 里的 post_image()
ins comment ...    → writer.py 里的 comment_on_post()
```

每个适配器函数就是一个"翻译器"：
- 把用户的 CLI 命令翻译成对应的操作（HTTP 请求或浏览器操作）
- 把返回的结果翻译成用户能看懂的格式（表格、JSON 等）

### 5. Playwright（浏览器自动化库）

Playwright 是微软开发的浏览器自动化工具。它能用代码控制浏览器：

```python
page.click("button")      # 点击按钮
page.fill("textarea", "你好")  # 输入文字
page.goto("https://...")  # 打开网页
```

本项目用 Playwright 来实现发帖、发 Story 等需要浏览器交互的功能。

### 6. CDP（Chrome DevTools Protocol）

CDP 是 Chrome 浏览器提供的一套远程控制接口。Playwright 底层就是通过 CDP 来控制浏览器的。

```
Playwright → CDP 协议 → Chrome 浏览器 → 执行操作
```

OpenCLI 也是用 CDP 来控制浏览器的（通过它的 Browser Bridge 扩展）。

### 7. Private API（私有 API）

Instagram 网页版在内部会调用一些 API 接口，这些接口没有公开文档，但可以通过浏览器开发者工具（F12 → Network）观察到。

本项目（以及 OpenCLI）使用的 `https://www.instagram.com/api/v1/...` 就是这些私有 API。

```
公开 API（有文档，有限制）     vs     私有 API（无文档，功能更多）
Instagram Graph API                   /api/v1/users/web_profile_info/
需要申请开发者账号                    只需要登录 Cookie
只能 Business 账号发帖               任何账号都能用
```

### 8. pyproject.toml 与 [project.scripts]

```toml
[project.scripts]
ins = "ins_cli.cli:main"
```

这行代码告诉 Python：当用户输入 `ins` 命令时，运行 `ins_cli.cli` 文件中的 `main()` 函数。

安装后，Python 会在 `~/.local/bin/` 创建一个叫 `ins` 的启动脚本。

---

## 项目结构

```
ins-cli/
├── pyproject.toml        # 包配置（依赖、入口点）
├── README.md             # 使用说明
├── ARCHITECTURE.md       # 本文件（技术详解）
└── src/
    └── ins_cli/
        ├── __init__.py   # 包标识
        ├── cli.py        # 命令行入口（argparse）
        ├── auth.py       # Cookie 管理（登录/保存/加载）
        ├── browser.py    # 浏览器启动（Playwright + Chrome 配置文件）
        ├── reader.py     # 读取操作（HTTP API 请求）
        └── writer.py     # 写入操作（浏览器自动化）
```

## 数据流

### 读取流程（如 `ins profile zuck`）

```
cli.py 解析命令
  → auth.py 加载 Cookie
    → reader.py 用 requests 发 HTTP 请求到 Instagram API
      → 返回 JSON 数据
        → cli.py 格式化输出（表格/JSON/纯文本）
```

### 写入流程（如 `ins post photo.jpg -c "Hello"`）

```
cli.py 解析命令
  → browser.py 启动 Playwright + 打开 Chrome
    → writer.py 控制浏览器：
      1. 打开 Instagram 发帖页
      2. 上传图片
      3. 输入文案
      4. 点击发布
    → 关闭浏览器
      → 返回结果
```

## 灵感来源

| 功能 | 灵感来自 | 实现方式 |
|------|---------|---------|
| 读取（HTTP API） | instaloader | 用 requests 直接调 Instagram 私有 API |
| 写入（浏览器自动化） | OpenCLI | 用 Playwright 控制浏览器模拟人工操作 |
| Cookie 管理 | xhs-cli | 从浏览器提取或手动输入 |
| CLI 框架 | argparse | Python 标准库，零额外依赖 |
