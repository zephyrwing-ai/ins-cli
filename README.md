# ins-cli

Instagram command-line tool for reading public/account data and automating write actions through Google Chrome.

`ins-cli` uses two execution paths:

- Read operations use Instagram Web private APIs, with an automatic fallback to a logged-in Google Chrome browser context when direct HTTP requests are rate-limited or rejected.
- Write operations use browser automation with stable Google Chrome and the user's saved Instagram cookies.

The project does not use Google Chrome Canary.

## Features

Currently implemented and tested:

- `ins login` - extract Instagram cookies from stable Google Chrome or enter cookies manually.
- `ins logout` - clear saved cookies.
- `ins search` - search Instagram users.
- `ins profile` - read user profile info.
- `ins posts` - list recent posts from a user.
- `ins comments` - read comments from a media id / pk.
- `ins post` - publish an image/video post through Google Chrome automation.

Partially implemented / still being hardened:

- `ins comment` - comment on a user's post. The command exists, but UI behavior can vary by Instagram page state.
- `ins story` - Story publishing still needs a private publish implementation; current Instagram Web UI redirects Story creation to the regular post composer.

## Requirements

- Python 3.10+
- Stable Google Chrome installed
- You must be logged in to Instagram in stable Google Chrome

Optional environment overrides:

```bash
export INS_CHROME_EXECUTABLE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
export INS_CHROME_USER_DATA_DIR="$HOME/Library/Application Support/Google/Chrome"
```

## Installation

After this package is published to PyPI:

```bash
pip install ins-cli
```

Or install it as a uv tool:

```bash
uv tool install ins-cli
```

Then use the generated CLI:

```bash
ins --help
```

For local development from this repository:

```bash
uv sync
uv run ins --help
```

## Usage

### Login

```bash
ins login
```

If automatic cookie extraction fails:

```bash
ins login --manual
```

Cookies are stored in:

```text
~/.ins-cli/cookies.json
```

### Read

```bash
ins search instagram --count 3 -f json
ins profile instagram -f json
ins posts instagram --count 5 -f table
ins comments <media_id_or_pk> --count 10 -f json
```

Output formats:

```bash
ins profile instagram -f table
ins profile instagram -f json
ins profile instagram -f plain
```

### Publish A Post

```bash
ins post photo.jpg -c "Hello from ins-cli"
```

Supported media formats:

- Images: `.jpg`, `.jpeg`, `.png`, `.webp`
- Videos: `.mp4`

### Comment

```bash
ins comment username "Nice post!" --index 1
```

`--index 1` means the user's latest visible post.

## Development

Run commands against the current source tree:

```bash
uv run ins search instagram --count 3 -f json
uv run python -m ins_cli.cli profile instagram -f json
```

Build the package:

```bash
uv build
```

Or with Python build tooling:

```bash
python -m pip install build
python -m build
```

## Publishing To PyPI

1. Create a PyPI account:

   - PyPI: https://pypi.org/
   - TestPyPI: https://test.pypi.org/

2. Install publishing tools:

```bash
uv tool install twine
```

3. Build distributions:

```bash
uv build
```

This creates files under `dist/`.

4. Test upload to TestPyPI first:

```bash
uv tool run twine upload --repository testpypi dist/*
```

5. Install from TestPyPI in a clean environment and verify:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ins-cli
ins --help
```

6. Upload to real PyPI:

```bash
uv tool run twine upload dist/*
```

After publishing, users can install with:

```bash
pip install ins-cli
```

or:

```bash
uv tool install ins-cli
```

## Notes

Instagram private APIs and Web UI behavior change frequently. This tool uses the user's own logged-in Chrome session and may need updates when Instagram changes endpoints, request requirements, or page structure.

Use this project responsibly and follow Instagram's terms and rate limits.

## License

MIT
