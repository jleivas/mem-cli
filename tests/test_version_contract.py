import re

from mem import APP_NAME
from mem import APP_VERSION
from mem import __version__

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def test_package_version_contract_is_exported() -> None:
    assert APP_NAME == "mem-cli"
    assert _SEMVER_RE.match(APP_VERSION), f"APP_VERSION must be semver, got {APP_VERSION!r}"
    assert APP_VERSION != "0.0.0", "version resolved to fallback sentinel — metadata or CHANGELOG lookup failed"
    assert __version__ == APP_VERSION
