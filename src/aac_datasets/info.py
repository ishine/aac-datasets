#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform
import sys

from pathlib import Path
from typing import Dict

import torch
import torchaudio
import yaml

import aac_datasets


def get_package_repository_path() -> str:
    return str(Path(__file__).parent.parent.parent)


def get_install_info() -> Dict[str, str]:
    """Return a dictionary containing the version python, the os name, the architecture name and the versions of the following packages: aac_datasets, torch, torchaudio."""
    return {
        "aac_datasets": aac_datasets.__version__,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os": platform.system(),
        "architecture": platform.architecture()[0],
        "torch": str(torch.__version__),
        "torchaudio": torchaudio.__version__,
        "package_path": get_package_repository_path(),
    }


def print_install_info() -> None:
    """Show main packages versions."""
    install_info = get_install_info()
    print(yaml.dump(install_info, sort_keys=False))


if __name__ == "__main__":
    print_install_info()
