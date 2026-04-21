from mem import APP_NAME
from mem import APP_VERSION
from mem import __version__


def test_package_version_contract_is_exported() -> None:
    assert APP_NAME == "mem-cli"
    assert APP_VERSION
    assert __version__ == APP_VERSION
