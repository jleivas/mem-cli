"""Generate an updated Homebrew formula with release artifact URLs and SHA256s.

Usage:
    python scripts/update_formula.py <version> <artifacts_dir>

Prints the updated formula to stdout. Redirect to the formula file:
    python scripts/update_formula.py 0.2.0 artifacts/ > Formula/mem-cli.rb

ARM/Linux platforms use pre-built binaries from the release artifacts.
Intel Mac uses the GitHub source archive + pip install (no binary runner needed).
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

GITHUB_REPO = "jleivas/mem-cli"
GITHUB_ARCHIVE_URL = "https://github.com/{repo}/archive/refs/tags/v{version}.tar.gz"

FORMULA_TEMPLATE = """\
class MemCli < Formula
  desc "Local token observability and agent memory for Claude and Codex"
  homepage "https://github.com/{repo}"
  version "{version}"
  license "MIT"

  on_macos do
    on_arm do
      url "{base_url}/mem-darwin-arm64.tar.gz"
      sha256 "{darwin_arm64}"
    end
    on_intel do
      url "{source_url}"
      sha256 "{source_sha256}"
      depends_on "python@3.11"
    end
  end

  on_linux do
    url "{base_url}/mem-linux-amd64.tar.gz"
    sha256 "{linux_amd64}"
  end

  def install
    if OS.mac? && Hardware::CPU.intel?
      system "python3.11", "-m", "venv", libexec/"venv"
      system "\#{{libexec}}/venv/bin/pip", "install", "."
      bin.install_symlink libexec/"venv/bin/mem"
    else
      libexec.install Dir["*"]
      bin.install_symlink libexec/"mem"
    end
  end

  test do
    system bin/"mem", "--version"
  end
end
"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_url(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return hashlib.sha256(response.read()).hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <version> <artifacts_dir>", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1].lstrip("v")
    artifacts = Path(sys.argv[2])
    base_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}"
    source_url = GITHUB_ARCHIVE_URL.format(repo=GITHUB_REPO, version=version)

    print(f"Fetching source archive sha256 from {source_url} ...", file=sys.stderr)

    print(FORMULA_TEMPLATE.format(
        repo=GITHUB_REPO,
        version=version,
        base_url=base_url,
        source_url=source_url,
        darwin_arm64=sha256_file(artifacts / "mem-darwin-arm64.tar.gz"),
        source_sha256=sha256_url(source_url),
        linux_amd64=sha256_file(artifacts / "mem-linux-amd64.tar.gz"),
    ), end="")


if __name__ == "__main__":
    main()
