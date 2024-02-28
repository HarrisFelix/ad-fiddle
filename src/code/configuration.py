# -*- coding: utf-8 -*-
"""Management of the configuration of Raptor.

Ability to import settings from Raptor 2.X.X as made by Vincent KIEFFER.
"""

import ruamel.yaml
import cattrs
import re
import filesystem

from dataclasses import dataclass
from src.config import system_config as sy
from src.config import teacher_config as te
from src.config import student_config as st
from src.config import workings_config as wo


@dataclass
class DefaultConfig:
    """Factory settings."""
    systeme: sy.Config
    professeurs: te.Config
    eleves: st.Config
    fonctionnement: wo.Config


class Config:
    """Management of the configuration.

    Attributes:
        yaml: Class instance to manipulate YAML files (read, write).
        path: Path of the config file.
        dict: YAML file in the form of a Python dictionary.
    """

    def __init__(self, path: str = 'Config/parametres.yaml') -> None:
        """Turns an existing YAML file into an instance. Or creates one with default settings.

        Args:
            path: Path of the config file.
        """
        self.yaml: ruamel.yaml.YAML = ruamel.yaml.YAML()
        self.path: str = path
        self.dict: dict[str] = self.config_to_dict()

        if not self.dict:
            self.setup_default_config()

    def setup_default_config(self) -> None:
        """Sets the config to default."""
        config = DefaultConfig(sy.Config(), te.Config(), st.Config(), wo.Config())
        config_dict = cattrs.unstructure(config)

        with open(self.path, 'w') as stream:
            self.yaml.dump(config_dict, stream)

        self.dict = config_dict

    def _backup_config(self) -> None:
        """Backs up config file."""
        filesystem.copy_to(self.path, f'{self.path}.old', overwrite=True)

    def config_to_dict(self):
        """Turns config file into a dictionary."""
        try:
            with open(self.path) as stream:
                config = self.yaml.load(stream)

            return config
        except FileNotFoundError:
            return {}

    def dict_to_config(self, config_dict: dict[str], backup=False) -> None:
        """Writes dictionary to config file."""
        if backup:
            self._backup_config()

        with open(self.path, 'w') as stream:
            self.yaml.dump(config_dict, stream)

        self.dict = config_dict

    @staticmethod
    def _format(line: str) -> str:
        """Transforms #foo# into [foo]."""
        return re.sub(r'(#.*?)#', r'\1]', line).replace('#', '[')

    def use_old_config(self, txt_config_path: str, backup: bool = True) -> None:
        """Imports settings from Raptor 2.X.X. File must exist.

        Args:
            txt_config_path: Path to the old config file.
            backup: Whether to back up current config (True) or not (False).

        Returns:
            None.
        """
        if backup:
            self._backup_config()

        new_config = {}

        with open(txt_config_path) as old_config:
            lines = old_config.readlines()

            for line in lines:
                formatted_line = line.strip().split(';')

                if len(formatted_line) >= 4:
                    new_config[formatted_line[0]] = formatted_line[1].lower(), formatted_line[-1]

        for key, (category, value) in new_config.items():
            if key in self.dict[category]:
                self.dict[category][key]['value'] = self._format(value)

        self.dict_to_config(self.dict)
