"""
Abstract base classes for the translation layer.
"""

import json
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
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
    def translate(self, intent: T, payload_format: str = "xml") -> str | dict:
        """
        Translate an intent into a vendor-specific YANG payload.

        Args:
            intent: The intent object to translate
            payload_format: The desired output format ('xml' or 'json')

        Returns:
            str | dict: The generated payload (string for XML, dict for JSON)
        """

    # def _render_template(self, template: Template, context: Dict[str, Any]) -> str:
    #     """
    #     Render a Jinja2 template with the given context.

    #     Args:
    #         template: The Jinja2 template to render
    #         context: Dictionary of variables to pass to the template

    #     Returns:
    #         str: The rendered template
    #     """
    #     return template.render(**context)

    def _render_and_validate_xml(
        self, data_list: list[dict], template_file: str
    ) -> str:
        template = self._load_template(template_file)
        rendered = template.render(interfaces=data_list)
        xmltodict.parse(rendered)
        return rendered

    def _render_and_validate_json(
        self, data_list: list[dict], template_file: str
    ) -> str:
        template = self._load_template(template_file)
        rendered = template.render(interfaces=data_list)
        return json.loads(rendered)  # returns a dict
        # return rendered
