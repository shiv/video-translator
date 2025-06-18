# Module Rename Changes: open_dubbing → app

This document summarizes all the changes made when renaming the module from `open_dubbing` to `app`.

## Files Modified

### 1. `setup.py`
- **Changed**: `fname="open_dubbing/__init__.py"` → `fname="app/__init__.py"`
- **Changed**: `"open-dubbing=open_dubbing.main:main"` → `"open-dubbing=app.main:main"`
- **Reason**: Update module path references for version reading and console script entry point

### 2. `app/__init__.py`
- **Changed**: `logging.getLogger("open_dubbing")` → `logging.getLogger("app")`
- **Reason**: Update logger name to match new module name

### 3. `app/main.py`
- **Changed**: `logging.getLogger("open_dubbing")` → `logging.getLogger("app")`
- **Changed**: `"open_dubbing.log"` → `"app.log"`
- **Reason**: Update logger configuration to use new module name and log file

### 4. `Makefile`
- **Changed**: `PATHS = open_dubbing/ tests/ e2e-tests/` → `PATHS = app/ tests/ e2e-tests/`
- **Reason**: Update development tools to target correct directory

## Files Cleaned Up

### 1. `open_dubbing.egg-info/` (directory)
- **Action**: Removed entire directory
- **Reason**: Old build artifacts from previous module name

### 2. `open_dubbing.log`
- **Action**: Removed file
- **Reason**: Old log file, app will now create `app.log`

## Files NOT Changed

### Package Names Remain the Same
- **PyPI package name**: Still `open-dubbing` in setup.py
- **Console command**: Still `open-dubbing` for users
- **Error messages**: Still reference `pip install open-dubbing[openai]`
- **Reason**: These are user-facing names that should remain consistent

### Documentation and Config Files
- **README.md**: Contains PyPI package references, not module references
- **ENVIRONMENT_VARIABLES.md**: No module-specific content
- **env.example**: No module-specific content
- **.gitignore**: Uses generic patterns
- **setup.cfg**: No module-specific content
- **requirements.txt**: No module references

## Key Points

1. **User Experience Unchanged**: Users still install `pip install open-dubbing` and run `open-dubbing` command
2. **Internal Module Structure**: All internal imports now use `app.` prefix
3. **Logging**: Logger name changed from "open_dubbing" to "app", log file from "open_dubbing.log" to "app.log"
4. **Build System**: setup.py correctly reads version from `app/__init__.py`
5. **Development Tools**: Makefile and other dev tools target the `app/` directory

## Testing the Changes

```bash
# Test that setup.py works
python setup.py --version

# Test that the package can be installed in development mode
pip install -e .

# Test that the console script works
open-dubbing --help
```

## Benefits of the Rename

1. **Shorter import paths**: `from app.services.tts import ...` vs `from open_dubbing.services.tts import ...`
2. **Cleaner module structure**: Generic `app` name is more suitable for internal organization
3. **Maintained backwards compatibility**: Users don't see any changes in how they interact with the package

## What Wasn't Changed

- All file imports within the `app/` directory were already using relative imports
- The directory structure under `app/` remained the same
- No changes to actual functionality or API
- Package metadata (name, description, etc.) in setup.py remained the same 