# Installation

Install Claude MPM and verify Claude Code CLI is available.

## Requirements

- **Claude Code CLI v1.0.92+**: https://docs.anthropic.com/en/docs/claude-code
- **Python 3.11+**

## Install (Recommended: pipx)

```bash
python -m pip install --user pipx
python -m pipx ensurepath

pipx install "claude-mpm[monitor]"
```

## Install (pip)

```bash
pip install "claude-mpm[monitor]"
```

## Install (Homebrew, macOS)

```bash
brew tap bobmatnyc/tools
brew install claude-mpm
```

## Install from Source (Developers)

```bash
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
pip install -e ".[dev,monitor]"
```

## Verify

```bash
claude --version
claude-mpm --version
claude-mpm doctor
```

## Next Steps

- **Quick Start**: [quick-start.md](quick-start.md)
- **Auto-Configuration**: [auto-configuration.md](auto-configuration.md)

## Troubleshooting

See [../user/troubleshooting.md](../user/troubleshooting.md) if installation fails.
