"""2つの編集者向けライブラリをコピーして、公開ルートの案内を作る。"""
import argparse
import filecmp
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARIES = {"depure": "でぷれさん素材ライブラリ", "common": "共通素材ライブラリ"}
INDEX = """<!doctype html>
<html lang="ja">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>素材ライブラリ</title>
<main>
  <h1>素材ライブラリ</h1>
  <ul>
    <li><a href="depure/">でぷれさん素材ライブラリ</a></li>
    <li><a href="common/">共通素材ライブラリ</a></li>
  </ul>
</main>
</html>
"""


def assemble(libraries):
    sources = {section: libraries / name / "公開用" for section, name in LIBRARIES.items()}
    for source in sources.values():
        for required in ("index.html", "data/library.json"):
            if not (source / required).is_file():
                raise SystemExit(f"公開用ビルドがありません: {source / required}")
    for private in (sources["depure"] / "media/mc_seihon", sources["common"] / "studio"):
        if private.exists():
            raise SystemExit(f"公開用ビルドに除外対象が残っています: {private}")

    # 公開ツリー上で並行制作中の未追跡ファイルを上書き・消去しない。
    legacy = ("data/characters.json", "media/depure")
    if (ROOT / ".git").exists():
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z", "--", *sources, *legacy],
            cwd=ROOT,
        )
        for raw in untracked.split(b"\0"):
            if not raw:
                continue
            path = Path(raw.decode("utf-8"))
            section = path.parts[0]
            incoming = sources[section].joinpath(*path.parts[1:]) if section in sources else None
            if not incoming or not incoming.is_file() or not filecmp.cmp(ROOT / path, incoming, shallow=False):
                raise SystemExit(f"未追跡ファイルを保全してから再実行してください: {path}")

    for section, source in sources.items():
        dest = ROOT / section
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".git", ".DS_Store"))
    if (ROOT / legacy[0]).exists():
        (ROOT / legacy[0]).unlink()
    if (ROOT / legacy[1]).exists():
        shutil.rmtree(ROOT / legacy[1])
    (ROOT / "index.html").write_text(INDEX, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libraries", type=Path, default=Path.home() / "Code/work/sns/instagram")
    assemble(parser.parse_args().libraries)
