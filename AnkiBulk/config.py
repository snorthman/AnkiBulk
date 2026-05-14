from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar

from aqt import mw

T = TypeVar('T')


class ConfigField(Generic[T]):
    @staticmethod
    def _get_config(defaults: bool = False) -> dict:
        if defaults:
            config = mw.addonManager.addonConfigDefaults(__package__) or {}
        else:
            config = mw.addonManager.getConfig(__package__) or {}
        return config

    def __init__(self, default: T | type):
        self._default = default

    def __set_name__(self, owner, name: str) -> None:
        self._name = name

    @property
    def value(self) -> T:
        user = self._get_config()
        if self._name in user:
            return user[self._name]
        defaults = self._get_config(defaults=True)
        if self._name in defaults:
            return defaults[self._name]
        return self._default() if callable(self._default) else self._default

    @value.setter
    def value(self, value: T) -> None:
        self.setter(value)

    def setter(self, value: T) -> None:
        config = self._get_config()
        config[self._name] = value
        mw.addonManager.writeConfig(__package__, config)


@dataclass
class Preset:
    """Per-notetype settings for the Raw tab."""
    FORMATS: ClassVar[list[str]] = ["YAML", "JSON", "XML", "CSV", "TSV"]
    copy_format: str = "YAML"
    include_examples: bool = True
    mark_examples: bool = True
    mark_tag: str = "example_card"
    additional_text: str = ""

    def to_dict(self) -> dict:
        return {
            "copy_format": self.copy_format,
            "include_examples": self.include_examples,
            "mark_examples": self.mark_examples,
            "mark_tag": self.mark_tag,
            "additional_text": self.additional_text,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Preset':
        return cls(
            copy_format=d.get("copy_format", "YAML"),
            include_examples=d.get("include_examples", True),
            mark_examples=d.get("mark_examples", True),
            mark_tag=d.get("mark_tag", "example_card"),
            additional_text=d.get("additional_text", ""),
        )


class _AnkiBulkConfig:
    # Show first-time-use hint until the user visits Text view
    first_time_use: ConfigField[bool] = ConfigField(True)
    # Per-notetype column visibility: {notetype_id_str: [hidden_field_names]}
    column_visibility: ConfigField[dict[str, list[str]]] = ConfigField(dict)
    # Per-notetype presets: {notetype_id_str: Preset dict}
    presets: ConfigField[dict[str, dict]] = ConfigField(dict)

    def __setattr__(self, key, value):
        attr = self.__class__.__dict__.get(key)
        if isinstance(attr, ConfigField):
            attr.setter(value)
        else:
            super().__setattr__(key, value)

    def get_preset(self, notetype_id: int) -> Preset:
        """Get the Preset for a notetype, or a default one."""
        raw = self.presets.value.get(str(notetype_id))
        if raw:
            return Preset.from_dict(raw)
        return Preset()

    def save_preset(self, notetype_id: int, preset: Preset) -> None:
        """Save a Preset for a notetype."""
        all_presets = self.presets.value
        all_presets[str(notetype_id)] = preset.to_dict()
        self.presets = all_presets


AnkiBulkConfig = _AnkiBulkConfig()
