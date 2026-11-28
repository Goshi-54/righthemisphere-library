"""編集者向けの公開用ビルドを取り込み、キャラクターの入口データを出力する。"""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARIES = {
    "depure": "でぷれさん素材ライブラリ",
    "common": "共通素材ライブラリ",
}


def assemble(libraries):
    sources = {section: libraries / name / "公開用" for section, name in LIBRARIES.items()}
    for source in sources.values():
        for required in ("index.html", "data/library.json"):
            if not (source / required).is_file():
                raise SystemExit(f"公開用ビルドがありません: {source / required}")
    if not (sources["common"] / "studio/index.html").is_file():
        raise SystemExit("共通素材の公開用ビルドに studio がありません")

    for section, source in sources.items():
        destination = ROOT / section
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git", ".DS_Store"))


def write_characters():
    public = ROOT / "depure/data/library.json"
    character = json.loads(public.read_text(encoding="utf-8"))["キャラ"]
    data = {"キャラ": [{"id": "depure", "名前": character["名前"]}]}
    path = ROOT / "data/characters.json"
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libraries", type=Path, default=ROOT.parent / "work/sns/instagram")
    parser.add_argument("--top-only", action="store_true", help="既存の公開用データから入口データだけを更新する")
    args = parser.parse_args()
    if not args.top_only:
        assemble(args.libraries)
    write_characters()
