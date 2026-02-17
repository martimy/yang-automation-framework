"""
Abstract base classes for the translation layer.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from jinja2 import Template, Environment, FileSystemLoader

# Type variable for intent types
T = TypeVar("T")


class BaseTranslator(ABC, Generic[T]):
    """
    Generic abstract base class for all translators.

    Type parameter T represents the specific intent type this translator handles.
    """

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the translator with optional template directory.

        Args:
            template_dir: Path to directory containing Jinja2 templates
        """
        self.template_dir = template_dir
        self._template = None

    @property
    def template(self) -> Optional[Template]:
        """Get the Jinja2 template."""
        return self._template

    @template.setter
    def template(self, value: Template):
        """Set the Jinja2 template."""
        self._template = value

    # def load_template(self, template_path: str) -> Template:
    #     """
    #     Load a Jinja2 template from file.

    #     Args:
    #         template_path: Path to the template file

    #     Returns:
    #         Template: Loaded Jinja2 template
    #     """
    #     if self.template_dir:
    #         env = Environment(loader=FileSystemLoader(self.template_dir))
    #         return env.get_template(template_path)
    #     else:
    #         with open(template_path, "r") as f:
    #             return Template(f.read())

    def _load_template(self, template_name: str) -> Template:
        if not self.template_dir.exists():
            raise FileNotFoundError(
                f"Template directory not found: {self.template_dir}"
            )

        env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        env.trim_blocks = True
        env.lstrip_blocks = True
        env.keep_trailing_newline = False

        return env.get_template(template_name)

    @abstractmethod
    def translate(self, intent: T, payload_format: str = 'xml') -> str | dict:
        """
        Translate an intent into a vendor-specific YANG payload.

        Args:
            intent: The intent object to translate
            payload_format: The desired output format ('xml' or 'json')

        Returns:
            str | dict: The generated payload (string for XML, dict for JSON)
        """

    def _render_template(self, template: Template, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with the given context.

        Args:
            template: The Jinja2 template to render
            context: Dictionary of variables to pass to the template

        Returns:
            str: The rendered template
        """
        return template.render(**context)


class RoutingTranslator(BaseTranslator):
    """Abstract base class for routing intent translators."""

    @abstractmethod
    def translate(self, intent: Any, payload_format: str = 'xml') -> str | dict:
        """Translate a routing intent into YANG payload."""


class NetworkInstanceTranslator(BaseTranslator):
    """Abstract base class for network instance translators."""

    @abstractmethod
    def translate(self, intent: Any, payload_format: str = 'xml') -> str | dict:
        """Translate a network instance intent into YANG payload."""


class NtpTranslator(BaseTranslator):
    """Abstract base class for NTP intent translators."""

    @abstractmethod
    def translate(self, intent: Any, payload_format: str = 'xml') -> str | dict:
        """Translate an NTP intent into YANG payload."""


class SnmpTranslator(BaseTranslator):
    """Abstract base class for SNMP intent translators."""

    @abstractmethod
    def translate(self, intent: Any, payload_format: str = 'xml') -> str | dict:
        """Translate an SNMP intent into YANG payload."""


# Vendor-specific base classes (optional, but can be useful)


class CeosTranslator(BaseTranslator):
    """Base class for all cEOS translators."""

    def __init__(self):
        super().__init__(template_dir="translation/templates/ceos")


class SrlinuxTranslator(BaseTranslator):
    """Base class for all SR Linux translators."""

    def __init__(self):
        super().__init__(template_dir="translation/templates/srlinux")
