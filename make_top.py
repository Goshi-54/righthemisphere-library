# 素材ライブラリの上の階層（キャラの一覧とキャラ情報）を組む
# 11/14 本人「素材ライブラリはもう一つ上の階層を作る／そこに各キャラクター配置していく／キャラクター用のメタ情報もここで管理（リファレンスシートとかも）」
#   （意思決定DBに登録済み）。URL は新しい公開リポジトリ、公開ページに載せるのは使用許可を確かめたキャラだけ、最初はでぷれさんだけ
#   （意思決定DBに登録済み）
# 11/13 本人「等身大とマイクラはリファレンスシートはライブラリに載せなくていい」→ リファレンスシートは素材のタブではなく、ここ（キャラ情報）に置く
# 11/18 本人「素材は最終的にはどのキャラクターページにも表示するものになりそうなので、大元はもう一つ上の階層に保管。で、リンクだけでぷれさん素材ライブラリに表示するなどの形式を取りたいです。」
#   「一覧のとおり進めて」（意思決定DB 41bc12971e27813e92cfd78db77296b0）→ 背景・アイコン・イメージ強化は共通素材（common/）に置き、キャラのページからはリンクだけ
# 使い方：python3 make_top.py   （各キャラのライブラリと共通素材ライブラリで build_public.py を流したあとに流す）
import os, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")

# ---------- キャラの一覧（公開してよいキャラだけ）----------
CHARS = [{
    "id": "depure",
    "lib": f"{HOME}/Code/work/sns/instagram/でぷれさん素材ライブラリ",   # ライブラリの元
    "名前": "でぷれさん",
    "出どころ": "Instagram協業の出演者（協業先のキャラ）",
    "公開": "公開中（2026-11-12〜。本人の「公開してよい」で承認）",
    "声": {
        "中身": "ElevenLabsで複製したでぷれさんの声（1回目の声）",
        "設定": ["似せる強さ 0.90・安定性 0.40", "前置き文を付けて生成し、あとで切る（B方式）", "間：段落 0.48秒・行 0.22秒", "音量：-18 LUFS にそろえる"],
        "作り方": "Claude Code の Skill「goshi-narration-voice」",
    },
    "直し待ち": [
        {"何": "Vtuberの動作14種", "本人": "動作14種の画質、クオリティが悪いのが気になっています。"},
        {"何": "掛け合い D21〜D26", "本人": "ChatGPTとの掛け合いなどの品質が落ちてない？"},
    ],
}]

# ---------- 棚（キャラに紐づかないもの）----------
# 11/14 本人「リンクだけ置く」（意思決定DBに登録済み）：名前帳は中身を公開ページに載せず、非公開のアーティファクトへのリンクだけ置く
SHELVES = [{
    "棚": "編集",
    "名前": "編集の名前帳",
    "説明": "テロップ・動き・切り替え・エフェクト・色の名前に番号（E01-01 など）を付けた一覧。9タブ・153項目。",
    "注意": ["非公開のページです。開けるのは共有された人だけです。", "見本の見た目は確認前の試作です。"],
    "リンク": "https://claude.ai/artifact/Gq1dGzo4nk8wjXxXChk5jM",
}, {
    # 11/18 本人「webツールとして素材ライブラリに合流させたい。Web上で使いごごちをみたい。」（意思決定DB 41cc12971e2781ab9dbff3eac78a5564）
    # 調整ツールの元：~/Code/work/sns/instagram/案件/AI素材女性の生成/成果物/MTG1117_動画生成の検証/調整ツール/（apply.py は手元だけ。公開しない）
    "棚": "動画生成",
    "名前": "生成素材の調整ツール",
    "説明": "生成した動画や画像を開き、明るさや質感をスライダーで動かして、元と並べて見る道具。決めた設定は、書き出し用のスクリプトで動画全体にかけられる（30fps化も選べる）。",
    "注意": ["開いたファイルはこのブラウザの中だけで使い、どこにも送りません。"],
    "リンク": "adjust/",
    "ボタン": "調整ツールを開く",
    "外部": False,
}]

# ---------- 共通素材（キャラをまたぐ素材）----------
COMMON = {"id": "common", "lib": f"{HOME}/Code/work/sns/instagram/共通素材ライブラリ"}

out_chars = []
for c in CHARS:
    D = json.load(open(f"{c['lib']}/data/library.json", encoding="utf-8"))
    pub = f"{c['lib']}/公開用"
    dst = f"{HERE}/{c['id']}"
    # 素材ライブラリ（公開用の一式）を写す
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(pub, dst, ignore=shutil.ignore_patterns(".git", ".DS_Store"))
    # リファレンス：画風ごと。見本の画像はライブラリの media から写す
    os.makedirs(f"{HERE}/media/{c['id']}", exist_ok=True)
    def take(src):
        name = src.replace("/", "_")
        shutil.copyfile(f"{c['lib']}/{src}", f"{HERE}/media/{c['id']}/{name}")
        return f"media/{c['id']}/{name}"
    adopted = {"基準_正面顔.jpg": "採用（本人「こちらベースで」）"}
    refs = [
        {"画風": "ミニキャラ", "ドライブ": D["キャラ"]["ドライブ"], "説明": "ライブラリを公開したとき（11/12）から載せている参照シート",
         "画像": [{"名前": x["label"], "src": take(x["src"]), "状態": ""} for x in D["キャラ"]["参照シート"]]},
        {"画風": "Vtuber（仮置き）", "ドライブ": D["等身大のドライブ"], "説明": "Codexで作ったもの（11/12〜13）。本人が採用を伝えたのは正面顔だけ。ほかは採否を確かめていない",
         "画像": [{"名前": x["名前"], "src": take(x["src"]), "状態": adopted.get(x["ファイル"], "採否未確認")} for x in D["等身大"]["静止画"]]},
        {"画風": "その他・マイクラ（仮置き）", "ドライブ": D["マイクラのドライブ"], "説明": "Codexで作ったもの。採否を確かめていない",
         "画像": [{"名前": x["名前"], "src": take(x["src"]), "状態": "採否未確認"} for x in D["マイクラ"]["静止画"]]},
    ]
    counts = [["口パク", len(D["口パク"])], ["全身の動き", len(D["全身"])], ["掛け合い", len(D["掛け合い"])],
              ["Vtuber（仮置き）", len(D["等身大"]["動作"])], ["マイクラ（仮置き）", len(D["マイクラ"]["動作"])],
              ["保留", sum(len(g["素材"]) for g in D.get("保留", []))], ["台本", len(D["台本"])]]
    # 履歴：キャラごとの履歴のファイル（正本。11/14 本人、意思決定DBに登録済み）。決定（意思決定DBのページID）は公開しない。新しい順
    H = json.load(open(f"{c['lib']}/data/history.json", encoding="utf-8"))
    hist = [{k: h[k] for k in ("日時", "種類", "中身", "状態", "本人") if h.get(k)} for h in reversed(H)]
    frames = [dict(f, src=f"{c['id']}/{f['src']}") for f in D["口パク"][0]["向き"]["正面"]]
    out_chars.append({k: v for k, v in c.items() if k != "lib"} | {
        "ライブラリ": f"{c['id']}/", "ドライブ": D["キャラ"]["ドライブ"], "画風": "ミニキャラ・Vtuber（仮置き）・その他（マイクラ・仮置き）",
        "見本": frames, "件数": counts, "リファレンス": refs, "履歴": hist})

# 共通素材：公開用の一式を common/ に写し、入口のカードの情報を作る
CD = json.load(open(f"{COMMON['lib']}/data/library.json", encoding="utf-8"))
dst = f"{HERE}/{COMMON['id']}"
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(f"{COMMON['lib']}/公開用", dst, ignore=shutil.ignore_patterns(".git", ".DS_Store"))
common = {"名前": CD["ページ名"], "ページ": f"{COMMON['id']}/", "ドライブ": CD["ドライブ"],
          "件数": [["背景", len(CD["背景"])], ["アイコン", len(CD["アイコン"])], ["イメージ強化", len(CD["イメージ強化"])]],
          "見本": [f"{COMMON['id']}/{x['src']}" for x in CD["アイコン"][:6]]}

os.makedirs(f"{HERE}/data", exist_ok=True)
json.dump({"キャラ": out_chars, "共通素材": common, "棚": SHELVES}, open(f"{HERE}/data/characters.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("キャラ", len(out_chars), [c["名前"] for c in out_chars])
