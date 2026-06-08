"""Generate an updated Homebrew formula with release artifact URLs and SHA256s.

Usage:
    python scripts/update_formula.py <version> <artifacts_dir>

Prints the updated formula to stdout. Redirect to the formula file:
    python scripts/update_formula.py 0.2.0 artifacts/ > Formula/mem-cli.rb
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

GITHUB_REPO = "jleivas/mem-cli"

FORMULA_TEMPLATE = """\
class MemCli < Formula
  desc "Local token observability and agent memory for Claude and Codex"
  homepage "https://github.com/{repo}"
  version "{version}"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "{base_url}/mem-darwin-arm64.tar.gz"
      sha256 "{darwin_arm64}"
    else
      url "{base_url}/mem-darwin-amd64.tar.gz"
      sha256 "{darwin_amd64}"
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url "{base_url}/mem-linux-arm64.tar.gz"
      sha256 "{linux_arm64}"
    else
      url "{base_url}/mem-linux-amd64.tar.gz"
      sha256 "{linux_amd64}"
    end
  end

  def install
    libexec.install Dir["*"]
    bin.install_symlink libexec/"mem"
  end

  test do
    system bin/"mem", "--version"
  end
end
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <version> <artifacts_dir>", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1].lstrip("v")
    artifacts = Path(sys.argv[2])
    base_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}"

    print(FORMULA_TEMPLATE.format(
        repo=GITHUB_REPO,
        version=version,
        base_url=base_url,
        darwin_arm64=sha256(artifacts / "mem-darwin-arm64.tar.gz"),
        darwin_amd64=sha256(artifacts / "mem-darwin-amd64.tar.gz"),
        linux_arm64=sha256(artifacts / "mem-linux-arm64.tar.gz"),
        linux_amd64=sha256(artifacts / "mem-linux-amd64.tar.gz"),
    ), end="")


if __name__ == "__main__":
    main()
