# 素材を足す共通の道具
# 11/14 本人「保留の素材はChatwork経由での依頼のけんもこちらに含まれていますかね？その場合はもう一つの案の方がいいです。そのほかは推奨で問題ないです。」
#   （意思決定DB 417c12971e2781498223c4d6630ebdf5）
# 流れ：受け取る（納品メモつき）→ 保留に置く（ドライブの 90_保留、ライブラリの「保留」タブ）→ 本人が採否 → 足す → 履歴に1行
# 納品メモの書き方は tools/納品メモの書き方.md
#
# 使い方（ライブラリの元フォルダで build_public.py、ここで make_top.py を流して公開する）：
#   python3 tools/assets.py receive <キャラ> <納品メモ.csv> --依頼 "依頼の短い名前" --出どころ "Chatwork【…】／Codex など" [--原文 "依頼の原文"]
#       納品メモの素材を 90_保留/<日付>_<依頼>/ に写し、ライブラリの「保留」に足す。履歴に「受け取り」の行
#   python3 tools/assets.py decide <キャラ> <依頼のID> <素材の名前|*> <採用|仮置き|直し|見送り> [--本人 "本人の言葉の原文"] [--決定 意思決定DBのページID]
#       採否を記録する。履歴に「採否」の行
#   python3 tools/assets.py promote <キャラ> <依頼のID> <素材の名前|*> アイコン --組 <アイコンの組>
#       採用・仮置きの素材を正式な場所に移す（今はアイコンだけ。ほかの種類は最初に実際に足すときに作る）。履歴に「追加」の行
#   python3 tools/assets.py list <キャラ>
# 試し運転：環境変数 DRV_OVERRIDE（ドライブの代わりのフォルダ）と LIB_OVERRIDE（ライブラリの元フォルダの代わり）
import os, sys, csv, json, shutil, hashlib, argparse, subprocess, datetime, re
HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
CHARS = json.load(open(f"{HERE}/chars.json", encoding="utf-8"))
import glob
_roots = glob.glob(f"{HOME}/Library/CloudStorage/GoogleDrive-*/マイドライブ")
DRIVE_ROOT = os.path.dirname(_roots[0]) if _roots else ""   # このMacのGoogleドライブ（アカウント名をコードに書かない）
HOLD = "90_保留"
STATES = ("保留", "採用", "仮置き", "直し", "見送り")
now = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def paths(char):
    c = CHARS[char]
    lib = os.environ.get("LIB_OVERRIDE", os.path.expanduser(c["lib"]))
    D = json.load(open(f"{lib}/data/library.json", encoding="utf-8"))
    drv = os.environ.get("DRV_OVERRIDE") or f"{DRIVE_ROOT}/{D['キャラ']['ドライブの場所'].rstrip('/')}"
    return lib, drv, D

def save(lib, D, rows=None):
    json.dump(D, open(f"{lib}/data/library.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if rows is not None:
        hp = f"{lib}/data/history.json"
        H = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else []
        H += rows
        json.dump(H, open(hp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def row(種類, 中身, 状態="", 本人="", 決定="", 出どころ="", ドライブ=""):
    return dict(日時=now(), 種類=種類, 中身=中身, 状態=状態, 本人=本人, 決定=決定, 出どころ=出どころ, ドライブ=ドライブ, 公開="")

def thumb(src, lib, key):
    """見本の画像を media/hold/ に作る。静止画は avif（長い辺480）、GIF はそのまま（3MBまで）、動画は1コマ目"""
    ext = os.path.splitext(src)[1].lower()
    h = hashlib.sha1(key.encode()).hexdigest()[:14]
    os.makedirs(f"{lib}/media/hold", exist_ok=True)
    if ext == ".gif" and os.path.getsize(src) <= 3_000_000:
        out = f"media/hold/{h}.gif"; shutil.copyfile(src, f"{lib}/{out}")
    elif ext in (".mp4", ".mov", ".webm"):
        out = f"media/hold/{h}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-frames:v", "1", "-vf", "scale='min(480,iw)':-2", f"{lib}/{out}"], check=True)
    else:
        out = f"media/hold/{h}.avif"
        subprocess.run(["sips", "-Z", "480", "-s", "format", "avif", src, "--out", f"{lib}/{out}"], check=True, capture_output=True)
    return out

def slug(s):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")[:40]

def receive(a):
    lib, drv, D = paths(a.char)
    base = os.path.dirname(os.path.abspath(a.memo))
    rows = list(csv.DictReader(open(a.memo, encoding="utf-8-sig")))
    if not rows: sys.exit("納品メモに行がない")
    for need in ("名前", "ファイル", "種類"):
        if need not in rows[0]: sys.exit(f"納品メモに「{need}」の列がない")
    day = datetime.date.today().strftime("%Y%m%d")
    folder = f"{HOLD}/{day}_{slug(a.依頼)}"
    dst = f"{drv}/{folder}"
    if os.path.exists(dst): sys.exit(f"既にある：{dst}")
    D.setdefault("保留", [])
    gid = f"h{day}-{len([g for g in D['保留'] if g['id'].startswith('h' + day)]) + 1:02d}"
    items = []
    for r in rows:
        src = os.path.join(base, r["ファイル"])
        if not os.path.isfile(src): sys.exit(f"ファイルがない：{src}")
    os.makedirs(dst)
    for r in rows:
        src = os.path.join(base, r["ファイル"])
        name = os.path.basename(r["ファイル"])
        if os.path.exists(f"{dst}/{name}"): sys.exit(f"同じ名前のファイルが2つある：{name}")
        shutil.copyfile(src, f"{dst}/{name}")
        it = {"名前": r["名前"], "種類": r["種類"], "ファイル": name, "場所": f"{folder}/{name}", "src": thumb(src, lib, f"{folder}/{name}"), "状態": "保留"}
        if r.get("メモ"): it["メモ"] = r["メモ"]
        if r.get("コマのフォルダ"):
            kd = os.path.join(base, r["コマのフォルダ"]); kname = f"{os.path.splitext(name)[0]}_コマ"
            shutil.copytree(kd, f"{dst}/{kname}"); it["コマのフォルダ"] = f"{folder}/{kname}"
        items.append(it)
    g = {"id": gid, "依頼": a.依頼, "出どころ": a.出どころ, "届いた日": now(), "フォルダ": folder, "素材": items}
    if a.原文: g["依頼の原文"] = a.原文
    D["保留"].append(g)
    save(lib, D, [row("受け取り", f"{a.依頼}（{len(items)}点）を保留に置いた［{gid}］", "保留", 出どころ=a.出どころ, ドライブ=folder)])
    print("保留に置いた", gid, len(items), "点 →", dst)

def pick(D, gid, name):
    g = next((g for g in D.get("保留", []) if g["id"] == gid), None)
    if not g: sys.exit(f"保留にない：{gid}")
    its = g["素材"] if name == "*" else [x for x in g["素材"] if x["名前"] == name]
    if not its: sys.exit(f"素材がない：{name}")
    return g, its

def decide(a):
    if a.state not in STATES[1:]: sys.exit(f"状態は {STATES[1:]} のどれか")
    lib, drv, D = paths(a.char)
    g, its = pick(D, a.gid, a.name)
    for x in its:
        x["状態"] = a.state
        if a.本人: x["本人"] = a.本人
    names = "・".join(x["名前"] for x in its)
    save(lib, D, [row("採否", f"{g['依頼']}：{names}［{g['id']}］", a.state, a.本人 or "", a.決定 or "", g["出どころ"], g["フォルダ"])])
    print(a.state, len(its), "点")

def promote(a):
    lib, drv, D = paths(a.char)
    g, its = pick(D, a.gid, a.name)
    its = [x for x in its if x["状態"] in ("採用", "仮置き")]
    if not its: sys.exit("採用・仮置きの素材がない（先に decide で採否を記録する）")
    if a.kind != "アイコン": sys.exit("今はアイコンだけ。ほかの種類は、最初に実際に足すときに作る")
    folder = "06_共通アイコン"
    n = max(int(x["id"][1:]) for x in D["アイコン"] if re.fullmatch(r"n\d+", x.get("id", "")))
    os.makedirs(f"{lib}/media/icon", exist_ok=True)
    for x in its:
        dst = f"{drv}/{folder}/{x['ファイル']}"
        if os.path.exists(dst): sys.exit(f"既にある：{dst}")
    for x in its:
        n += 1; nid = f"n{n:03d}"
        shutil.move(f"{drv}/{x['場所']}", f"{drv}/{folder}/{x['ファイル']}")
        src = f"media/icon/{nid}.png"
        subprocess.run(["sips", "-Z", "256", "-s", "format", "png", f"{drv}/{folder}/{x['ファイル']}", "--out", f"{lib}/{src}"], check=True, capture_output=True)
        it = {"id": nid, "名前": os.path.splitext(x["ファイル"])[0], "組": a.組, "src": src, "場所": f"{folder}/{x['ファイル']}", "ファイル": x["ファイル"], "暗い背景": False}
        if x["状態"] == "仮置き": it["仮置き"] = True
        D["アイコン"].append(it)
        g["素材"].remove(x)
    if not g["素材"]: D["保留"].remove(g)
    names = "・".join(x["名前"] for x in its)
    save(lib, D, [row("追加", f"アイコン（{a.組}）：{names}［{g['id']}から］", "・".join(sorted({x['状態'] for x in its})), "・".join(x.get("本人", "") for x in its if x.get("本人")), "", g["出どころ"], folder)])
    print("アイコンに足した", len(its), "点。add_download_ids.py → build_public.py → make_top.py の順に流す")

def lst(a):
    lib, drv, D = paths(a.char)
    for g in D.get("保留", []):
        print(g["id"], g["依頼"], g["出どころ"], g["届いた日"])
        for x in g["素材"]: print("  ", x["状態"], x["種類"], x["名前"], x["ファイル"])
    if not D.get("保留"): print("保留はない")

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
p = sp.add_parser("receive"); p.add_argument("char"); p.add_argument("memo"); p.add_argument("--依頼", required=True); p.add_argument("--出どころ", required=True); p.add_argument("--原文")
p = sp.add_parser("decide"); p.add_argument("char"); p.add_argument("gid"); p.add_argument("name"); p.add_argument("state"); p.add_argument("--本人"); p.add_argument("--決定")
p = sp.add_parser("promote"); p.add_argument("char"); p.add_argument("gid"); p.add_argument("name"); p.add_argument("kind"); p.add_argument("--組", required=True)
p = sp.add_parser("list"); p.add_argument("char")
a = ap.parse_args()
{"receive": receive, "decide": decide, "promote": promote, "list": lst}[a.cmd](a)
