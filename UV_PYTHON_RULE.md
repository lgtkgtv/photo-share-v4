# 🚨 CRITICAL: UV Python Environment Rule
# ========================================

## **MANDATORY RULE FOR ALL DEVELOPERS**

**ALL Python environment management MUST use `uv`. This is non-negotiable.**

---

## ✅ **REQUIRED: Use UV Commands Only**

### Environment Setup
```bash
uv venv                    # Create virtual environment
source .venv/bin/activate  # Activate environment
uv sync                    # Install dependencies from pyproject.toml
uv sync --extra all        # Install with all optional dependencies
```

### Package Management
```bash
uv add package-name        # Add runtime dependency
uv add --group dev pytest  # Add development dependency
uv remove package-name     # Remove dependency
uv sync --upgrade          # Update all dependencies
```

### Running Commands
```bash
uv run pytest             # Run pytest in environment
uv run python script.py   # Run Python script in environment
uv run black .             # Run code formatter
uv run mypy .              # Run type checker
```

---

## ❌ **FORBIDDEN: Never Use These Commands**

```bash
# ❌ NEVER use pip commands
pip install package-name
pip install -r requirements.txt
pip freeze
python -m pip install

# ❌ NEVER use other environment tools
virtualenv venv
python -m venv venv
pipenv install
poetry install
conda install
```

---

## 🎯 **Quick Development Workflow**

### First Time Setup
```bash
./scripts/dev-setup.sh     # Sets up everything automatically
```

### Daily Development
```bash
source .venv/bin/activate              # Activate environment
./scripts/dev-commands.sh test         # Run tests
./scripts/dev-commands.sh format       # Format code
./scripts/dev-commands.sh services     # Start Docker services
```

---

## 🔧 **Development Helper Scripts**

We provide scripts that enforce UV usage:

- `./scripts/dev-setup.sh` - First time environment setup
- `./scripts/dev-commands.sh` - Common development tasks
- `.uv-python-rule.md` - This rule reference

---

## 🚨 **Why This Rule Exists**

1. **Speed**: UV is 10-100x faster than pip
2. **Reliability**: Consistent dependency resolution across all environments
3. **Security**: Better vulnerability detection and validation
4. **Modern Standards**: UV represents the future of Python packaging
5. **Team Consistency**: Everyone uses the same tools and processes

---

## 📚 **UV Reference**

### Project Structure
```
photo-share-consul/
├── pyproject.toml         # Project configuration and dependencies
├── .venv/                 # Virtual environment (created by uv venv)
├── scripts/
│   ├── dev-setup.sh      # Initial setup script
│   └── dev-commands.sh   # Development workflow script
```

### Key Commands
- `uv --help` - Get help
- `uv venv --help` - Virtual environment help
- `uv add --help` - Package management help
- `uv run --help` - Command execution help

---

## ⚠️ **Enforcement**

This rule will be enforced through:
- Pre-commit hooks that check for pip usage
- Documentation that only shows UV commands
- Code reviews that reject pip usage
- CI/CD that validates UV dependency management

---

**Remember**: If you see `pip` anywhere in documentation or need to install a package, always use the UV equivalent instead!

**Questions?** Check the comprehensive documentation in [USER_GUIDE.md](./USER_GUIDE.md) or [CLAUDE.md](./CLAUDE.md)