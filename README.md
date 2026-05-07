# ins-cli

Instagram CLI — 读取用 HTTP API，写入用浏览器自动化。

## 安装

```bash
pip install ins-cli
# 或
uv tool install ins-cli

# 安装浏览器驱动（首次）
playwright install chromium
```

## 使用

### 登录

```bash
# 自动从浏览器提取 Cookie
ins login

# 手动输入 Cookie
ins login --manual
```

### 读取（HTTP API，不需要浏览器）

```bash
ins profile zuck                    # 查看用户资料
ins search "mark zuckerberg"        # 搜索用户
ins posts zuck --count 5            # 查看最近帖子
ins comments <media_id>             # 查看帖子评论
```

### 写入（浏览器自动化，需要已登录的 Chrome）

```bash
ins post photo.jpg -c "Hello World" # 发帖
ins story photo.jpg                 # 发 Story
ins comment zuck "Nice post!"       # 评论
```

### 输出格式

```bash
ins profile zuck -f json    # JSON
ins search cat -f plain     # 纯文本
ins posts zuck -f table     # 表格（默认）
```

## 技术架构

详见 [ARCHITECTURE.md](./ARCHITECTURE.md)

## License

MIT
