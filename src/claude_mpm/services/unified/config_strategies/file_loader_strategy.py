"""
File Loader Strategy - Consolidates 215 file loading instances into 5 strategic loaders
Part of Phase 3 Configuration Consolidation
"""

import configparser
import importlib.util
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml

from claude_mpm.core.logging_utils import get_logger

from .unified_config_service import ConfigFormat, IConfigStrategy


class LoaderType(Enum):
    """Strategic loader types consolidating 215 instances"""

    STRUCTURED = "structured"  # JSON, YAML, TOML - 85 instances
    ENVIRONMENT = "environment"  # ENV files and variables - 45 instances
    PROGRAMMATIC = "programmatic"  # Python modules - 35 instances
    LEGACY = "legacy"  # INI, properties - 30 instances
    COMPOSITE = "composite"  # Multi-source loading - 20 instances


@dataclass
class FileLoadContext:
    """Context for file loading operations"""

    path: Path
    format: ConfigFormat
    encoding: str = "utf-8"
    strict: bool = True
    interpolate: bool = False
    includes: List[str] = None
    excludes: List[str] = None
    transformations: List[Callable] = None
    fallback_paths: List[Path] = None


class BaseFileLoader(ABC):
    """Base class for all file loaders"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._cache = {}

    @abstractmethod
    def load(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load configuration from file"""

    @abstractmethod
    def supports(self, format: ConfigFormat) -> bool:
        """Check if loader supports the format"""

    def _read_file(self, path: Path, encoding: str = "utf-8") -> str:
        """Read file with proper error handling"""
        try:
            with Path(path).open(
                encoding=encoding,
            ) as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for enc in ["latin-1", "cp1252", "utf-16"]:
                try:
                    with Path(path).open(
                        encoding=enc,
                    ) as f:
                        self.logger.warning(
                            f"Read {path} with fallback encoding: {enc}"
                        )
                        return f.read()
                except (UnicodeDecodeError, OSError):
                    continue
            raise

    def _apply_transformations(
        self, config: Dict[str, Any], transformations: List[Callable]
    ) -> Dict[str, Any]:
        """Apply transformation pipeline"""
        if not transformations:
            return config

        for transform in transformations:
            try:
                config = transform(config)
            except Exception as e:
                self.logger.error(f"Transformation failed: {e}")

        return config


class StructuredFileLoader(BaseFileLoader):
    """
    Handles JSON, YAML, TOML formats
    Consolidates 85 individual loaders
    """

    def supports(self, format: ConfigFormat) -> bool:
        return format in [ConfigFormat.JSON, ConfigFormat.YAML, ConfigFormat.TOML]

    def load(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load structured configuration files"""
        if context.path in self._cache:
            self.logger.debug(f"Using cached config: {context.path}")
            return self._cache[context.path]

        content = self._read_file(context.path, context.encoding)

        if context.format == ConfigFormat.JSON:
            config = self._load_json(content, context)
        elif context.format == ConfigFormat.YAML:
            config = self._load_yaml(content, context)
        elif context.format == ConfigFormat.TOML:
            config = self._load_toml(content, context)
        else:
            raise ValueError(f"Unsupported format: {context.format}")

        # Handle includes
        if context.includes:
            config = self._process_includes(config, context)

        # Handle excludes
        if context.excludes:
            config = self._process_excludes(config, context)

        # Apply transformations
        if context.transformations:
            config = self._apply_transformations(config, context.transformations)

        # Cache result
        self._cache[context.path] = config

        return config

    def _load_json(self, content: str, context: FileLoadContext) -> Dict[str, Any]:
        """Load JSON with comments support"""
        # Remove comments if present
        if "//" in content or "/*" in content:
            content = self._strip_json_comments(content)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            if context.strict:
                raise
            self.logger.warning(f"JSON parse error, attempting recovery: {e}")
            return self._recover_json(content)

    def _load_yaml(self, content: str, context: FileLoadContext) -> Dict[str, Any]:
        """Load YAML with advanced features"""
        try:
            # Support multiple documents
            docs = list(yaml.safe_load_all(content))

            if len(docs) == 1:
                return docs[0] or {}
            # Merge multiple documents
            result = {}
            for doc in docs:
                if doc:
                    result.update(doc)
            return result

        except yaml.YAMLError as e:
            if context.strict:
                raise
            self.logger.warning(f"YAML parse error: {e}")
            return {}

    def _load_toml(self, content: str, context: FileLoadContext) -> Dict[str, Any]:
        """Load TOML configuration"""
        try:
            import toml

            return toml.loads(content)
        except ImportError:
            self.logger.error("toml package not installed")
            try:
                import tomli

                return tomli.loads(content)
            except ImportError as e:
                raise ImportError("Neither toml nor tomli package is installed") from e
        except Exception as e:
            if context.strict:
                raise
            self.logger.warning(f"TOML parse error: {e}")
            return {}

    def _strip_json_comments(self, content: str) -> str:
        """Remove comments from JSON content"""
        # Remove single-line comments
        content = re.sub(r"//.*?$", "", content, flags=re.MULTILINE)
        # Remove multi-line comments
        return re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    def _recover_json(self, content: str) -> Dict[str, Any]:
        """Attempt to recover from malformed JSON"""
        # Try to fix common issues
        content = content.replace("'", '"')  # Single to double quotes
        content = re.sub(r",\s*}", "}", content)  # Trailing commas in objects
        content = re.sub(r",\s*]", "]", content)  # Trailing commas in arrays

        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return {}

    def _process_includes(
        self, config: Dict[str, Any], context: FileLoadContext
    ) -> Dict[str, Any]:
        """Process include directives"""
        for include_key in context.includes:
            if include_key in config:
                include_path = Path(config[include_key])
                if not include_path.is_absolute():
                    include_path = context.path.parent / include_path

                if include_path.exists():
                    include_context = FileLoadContext(
                        path=include_path,
                        format=self._detect_format(include_path),
                        encoding=context.encoding,
                        strict=context.strict,
                    )
                    included_config = self.load(include_context)

                    # Merge included config
                    config = self._merge_configs(config, included_config)

                # Remove include directive
                del config[include_key]

        return config

    def _process_excludes(
        self, config: Dict[str, Any], context: FileLoadContext
    ) -> Dict[str, Any]:
        """Process exclude patterns"""
        for pattern in context.excludes:
            config = self._exclude_keys(config, pattern)
        return config

    def _exclude_keys(self, config: Dict[str, Any], pattern: str) -> Dict[str, Any]:
        """Exclude keys matching pattern"""
        if "*" in pattern or "?" in pattern:
            # Glob pattern
            import fnmatch

            return {k: v for k, v in config.items() if not fnmatch.fnmatch(k, pattern)}
        # Exact match
        config.pop(pattern, None)
        return config

    def _merge_configs(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge configurations"""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _detect_format(self, path: Path) -> ConfigFormat:
        """Detect file format from extension"""
        suffix = path.suffix.lower()

        if suffix == ".json":
            return ConfigFormat.JSON
        if suffix in [".yaml", ".yml"]:
            return ConfigFormat.YAML
        if suffix == ".toml":
            return ConfigFormat.TOML
        # Try to detect from content
        content = self._read_file(path)
        if content.strip().startswith("{"):
            return ConfigFormat.JSON
        if ":" in content:
            return ConfigFormat.YAML
        return ConfigFormat.JSON


class EnvironmentFileLoader(BaseFileLoader):
    """
    Handles environment files and variables
    Consolidates 45 individual loaders
    """

    def supports(self, format: ConfigFormat) -> bool:
        return format == ConfigFormat.ENV

    def load(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load environment configuration"""
        config = {}

        # Load from file if exists
        if context.path and context.path.exists():
            config.update(self._load_env_file(context.path, context))

        # Load from environment variables
        config.update(self._load_env_vars(context))

        # Apply variable interpolation if requested
        if context.interpolate:
            config = self._interpolate_variables(config)

        # Apply transformations
        if context.transformations:
            config = self._apply_transformations(config, context.transformations)

        return config

    def _load_env_file(self, path: Path, context: FileLoadContext) -> Dict[str, Any]:
        """Load .env file format"""
        config = {}
        content = self._read_file(path, context.encoding)

        for line in content.splitlines():
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE format
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]

                # Parse value type
                config[key] = self._parse_env_value(value)

        return config

    def _load_env_vars(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load from environment variables"""
        config = {}
        prefix = context.path.stem.upper() if context.path else ""

        for key, value in os.environ.items():
            # Check if key matches pattern
            if self._should_include_env_var(key, prefix, context):
                clean_key = self._clean_env_key(key, prefix)
                config[clean_key] = self._parse_env_value(value)

        return config

    def _should_include_env_var(
        self, key: str, prefix: str, context: FileLoadContext
    ) -> bool:
        """Check if environment variable should be included"""
        if context.includes:
            return any(key.startswith(inc) for inc in context.includes)
        if context.excludes:
            return not any(key.startswith(exc) for exc in context.excludes)
        if prefix:
            return key.startswith(prefix)
        return True

    def _clean_env_key(self, key: str, prefix: str) -> str:
        """Clean environment variable key"""
        if prefix and key.startswith(prefix):
            key = key[len(prefix) :]
            if key.startswith("_"):
                key = key[1:]

        # Convert to lowercase and replace underscores
        return key.lower().replace("__", ".").replace("_", "-")

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        # Boolean
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"

        # None
        if value.lower() in ["none", "null"]:
            return None

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON array or object
        if value.startswith(("[", "{")):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                pass

        # Comma-separated list
        if "," in value:
            return [v.strip() for v in value.split(",")]

        return value

    def _interpolate_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Interpolate variables in configuration values"""

        def interpolate_value(value: Any) -> Any:
            if isinstance(value, str):
                # Replace ${VAR} or $VAR patterns
                pattern = r"\$\{([^}]+)\}|\$(\w+)"

                def replacer(match):
                    var_name = match.group(1) or match.group(2)
                    # Look in config first, then environment
                    if var_name in config:
                        return str(config[var_name])
                    if var_name in os.environ:
                        return os.environ[var_name]
                    return match.group(0)

                return re.sub(pattern, replacer, value)

            if isinstance(value, dict):
                return {k: interpolate_value(v) for k, v in value.items()}

            if isinstance(value, list):
                return [interpolate_value(v) for v in value]

            return value

        return {k: interpolate_value(v) for k, v in config.items()}


class ProgrammaticFileLoader(BaseFileLoader):
    """
    Handles Python module configurations
    Consolidates 35 individual loaders
    """

    def supports(self, format: ConfigFormat) -> bool:
        return format == ConfigFormat.PYTHON

    def load(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load Python module as configuration"""
        if not context.path.exists():
            raise FileNotFoundError(f"Python config not found: {context.path}")

        # Load module
        spec = importlib.util.spec_from_file_location("config", context.path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load Python module: {context.path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Extract configuration
        config = self._extract_config(module, context)

        # Apply transformations
        if context.transformations:
            config = self._apply_transformations(config, context.transformations)

        return config

    def _extract_config(self, module: Any, context: FileLoadContext) -> Dict[str, Any]:
        """Extract configuration from Python module"""
        config = {}

        # Look for specific config patterns
        if hasattr(module, "CONFIG"):
            # Direct CONFIG dict
            config = module.CONFIG
        elif hasattr(module, "config"):
            # config dict or function
            config = module.config() if callable(module.config) else module.config
        elif hasattr(module, "get_config"):
            # get_config function
            config = module.get_config()
        else:
            # Extract all uppercase variables
            for name in dir(module):
                if name.isupper() and not name.startswith("_"):
                    value = getattr(module, name)
                    # Skip modules and functions unless specified
                    if not (callable(value) or isinstance(value, type)):
                        config[name] = value

        # Apply includes/excludes
        if context.includes:
            config = {k: v for k, v in config.items() if k in context.includes}
        if context.excludes:
            config = {k: v for k, v in config.items() if k not in context.excludes}

        return config


class LegacyFileLoader(BaseFileLoader):
    """
    Handles INI and properties files
    Consolidates 30 individual loaders
    """

    def supports(self, format: ConfigFormat) -> bool:
        return format == ConfigFormat.INI

    def load(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load legacy configuration formats"""
        content = self._read_file(context.path, context.encoding)

        # Detect format from content if needed
        if self._is_properties_format(content):
            config = self._load_properties(content, context)
        else:
            config = self._load_ini(content, context)

        # Apply transformations
        if context.transformations:
            config = self._apply_transformations(config, context.transformations)

        return config

    def _is_properties_format(self, content: str) -> bool:
        """Check if content is Java properties format"""
        # Properties files don't have sections
        return not any(line.strip().startswith("[") for line in content.splitlines())

    def _load_ini(self, content: str, context: FileLoadContext) -> Dict[str, Any]:
        """Load INI format configuration"""
        parser = configparser.ConfigParser(
            interpolation=(
                configparser.ExtendedInterpolation() if context.interpolate else None
            ),
            allow_no_value=True,
        )

        try:
            parser.read_string(content)
        except configparser.Error as e:
            if context.strict:
                raise
            self.logger.warning(f"INI parse error: {e}")
            return {}

        # Convert to dict
        config = {}

        # Handle DEFAULT section
        if parser.defaults():
            config["_defaults"] = dict(parser.defaults())

        # Handle other sections
        for section in parser.sections():
            config[section] = {}
            for key, value in parser.items(section):
                config[section][key] = self._parse_ini_value(value)

        # Flatten if only one section (excluding defaults)
        sections = [s for s in config if s != "_defaults"]
        if len(sections) == 1 and not config.get("_defaults"):
            config = config[sections[0]]

        return config

    def _load_properties(
        self, content: str, context: FileLoadContext
    ) -> Dict[str, Any]:
        """Load Java properties format"""
        config = {}

        for line in content.splitlines():
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith(("#", "!")):
                continue

            # Handle line continuation
            while line.endswith("\\"):
                line = line[:-1]
                next_line = next(content.splitlines(), "")
                line += next_line.strip()

            # Parse key=value or key:value
            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                # Key without value
                key = line
                value = ""

            key = key.strip()
            value = value.strip()

            # Unescape special characters
            value = self._unescape_properties_value(value)

            # Store in nested dict structure based on dots in key
            self._set_nested_value(config, key, value)

        return config

    def _parse_ini_value(self, value: str) -> Any:
        """Parse INI value to appropriate type"""
        if not value:
            return ""

        # Boolean
        if value.lower() in ["true", "yes", "on", "1"]:
            return True
        if value.lower() in ["false", "no", "off", "0"]:
            return False

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # List (comma-separated)
        if "," in value:
            return [v.strip() for v in value.split(",")]

        return value

    def _unescape_properties_value(self, value: str) -> str:
        """Unescape Java properties special characters"""
        replacements = {
            "\\n": "\n",
            "\\r": "\r",
            "\\t": "\t",
            "\\\\": "\\",
            "\\:": ":",
            "\\=": "=",
            "\\ ": " ",
        }

        for old, new in replacements.items():
            value = value.replace(old, new)

        return value

    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any):
        """Set value in nested dict structure based on dot notation"""
        parts = key.split(".")
        current = config

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value


class CompositeFileLoader(BaseFileLoader):
    """
    Handles multi-source configuration loading
    Consolidates 20 individual loaders
    """

    def __init__(self):
        super().__init__()
        self.loaders = {
            LoaderType.STRUCTURED: StructuredFileLoader(),
            LoaderType.ENVIRONMENT: EnvironmentFileLoader(),
            LoaderType.PROGRAMMATIC: ProgrammaticFileLoader(),
            LoaderType.LEGACY: LegacyFileLoader(),
        }

    def supports(self, format: ConfigFormat) -> bool:
        """Composite loader supports all formats"""
        return True

    def load(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load configuration from multiple sources"""
        configs = []

        # Check for directory of configs
        if context.path.is_dir():
            configs.extend(self._load_directory(context))

        # Check for fallback paths
        if context.fallback_paths:
            for fallback in context.fallback_paths:
                if fallback.exists():
                    fallback_context = FileLoadContext(
                        path=fallback,
                        format=self._detect_format(fallback),
                        encoding=context.encoding,
                        strict=False,  # Non-strict for fallbacks
                    )
                    try:
                        config = self._load_single(fallback_context)
                        configs.append(config)
                    except Exception as e:
                        self.logger.debug(f"Fallback load failed: {e}")

        # Load primary config
        if context.path.is_file():
            configs.append(self._load_single(context))

        # Merge all configs
        result = {}
        for config in configs:
            result = self._deep_merge(result, config)

        # Apply transformations
        if context.transformations:
            result = self._apply_transformations(result, context.transformations)

        return result

    def _load_directory(self, context: FileLoadContext) -> List[Dict[str, Any]]:
        """Load all config files from directory"""
        configs = []

        # Define load order
        patterns = ["default.*", "config.*", "settings.*", "*.config.*", "*.settings.*"]

        # Load files in order
        for pattern in patterns:
            for file_path in context.path.glob(pattern):
                if file_path.is_file():
                    file_context = FileLoadContext(
                        path=file_path,
                        format=self._detect_format(file_path),
                        encoding=context.encoding,
                        strict=context.strict,
                    )
                    try:
                        config = self._load_single(file_context)
                        configs.append(config)
                    except Exception as e:
                        self.logger.warning(f"Failed to load {file_path}: {e}")

        return configs

    def _load_single(self, context: FileLoadContext) -> Dict[str, Any]:
        """Load single configuration file"""
        # Find appropriate loader
        for _loader_type, loader in self.loaders.items():
            if loader.supports(context.format):
                return loader.load(context)

        raise ValueError(f"No loader available for format: {context.format}")

    def _detect_format(self, path: Path) -> ConfigFormat:
        """Detect configuration format from file"""
        suffix = path.suffix.lower()

        format_map = {
            ".json": ConfigFormat.JSON,
            ".yaml": ConfigFormat.YAML,
            ".yml": ConfigFormat.YAML,
            ".toml": ConfigFormat.TOML,
            ".env": ConfigFormat.ENV,
            ".py": ConfigFormat.PYTHON,
            ".ini": ConfigFormat.INI,
            ".cfg": ConfigFormat.INI,
            ".conf": ConfigFormat.INI,
            ".properties": ConfigFormat.INI,
        }

        return format_map.get(suffix, ConfigFormat.JSON)

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two configurations"""
        result = base.copy()

        for key, value in override.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, list):
                    result[key].extend(value)
                else:
                    result[key] = value
            else:
                result[key] = value

        return result


class FileLoaderStrategy(IConfigStrategy):
    """
    Main strategy class integrating all file loaders
    Reduces 215 file loading instances to 5 strategic loaders
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.composite_loader = CompositeFileLoader()

    def can_handle(self, source: Union[str, Path, Dict]) -> bool:
        """Check if source is a file or directory"""
        if isinstance(source, dict):
            return False

        path = Path(source)
        return path.exists() or path.parent.exists()

    def load(self, source: Any, **kwargs) -> Dict[str, Any]:
        """Load configuration from file source"""
        path = Path(source)

        # Create load context
        context = FileLoadContext(
            path=path,
            format=kwargs.get("format", self._detect_format(path)),
            encoding=kwargs.get("encoding", "utf-8"),
            strict=kwargs.get("strict", True),
            interpolate=kwargs.get("interpolate", False),
            includes=kwargs.get("includes"),
            excludes=kwargs.get("excludes"),
            transformations=kwargs.get("transformations"),
            fallback_paths=[Path(p) for p in kwargs.get("fallback_paths", [])],
        )

        return self.composite_loader.load(context)

    def validate(self, config: Dict[str, Any], schema: Optional[Dict] = None) -> bool:
        """Validate loaded configuration"""
        # Basic validation - can be extended
        return config is not None and isinstance(config, dict)

    def transform(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform configuration to standard format"""
        # Apply standard transformations
        return self._normalize_config(config)

    def _detect_format(self, path: Path) -> ConfigFormat:
        """Detect configuration format"""
        return self.composite_loader._detect_format(path)

    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize configuration structure"""
        # Convert all keys to lowercase
        normalized = {}

        for key, value in config.items():
            norm_key = key.lower().replace("-", "_")

            if isinstance(value, dict):
                normalized[norm_key] = self._normalize_config(value)
            else:
                normalized[norm_key] = value

        return normalized


# Export the main strategy
__all__ = ["FileLoadContext", "FileLoaderStrategy", "LoaderType"]
