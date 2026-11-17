# 素材を足す共通の道具
# 11/14 本人「保留の素材はChatwork経由での依頼のけんもこちらに含まれていますかね？その場合はもう一つの案の方がいいです。そのほかは推奨で問題ないです。」
#   （意思決定DBに登録済み）
# 流れ：（Codexへ頼む）→ 受け取る（納品メモつき）→ 保留に置く（ドライブの 90_保留、ライブラリの「保留」タブ）→ 本人が採否 → 足す → 履歴に1行
# 納品メモの書き方は tools/納品メモの書き方.md
#
# 使い方（ライブラリの元フォルダで build_public.py、ここで make_top.py を流して公開する）：
#   python3 tools/assets.py request <キャラ> --種類 口パク --依頼 "依頼の短い名前" --中身 "1点目;2点目;…" [--原文 "依頼の原文"] [--条件 "品質の条件;…"] [--出どころ "Chatwork【…】など"] [--作業ID WK-…]
#       Codexへの依頼文（転送文）を作って表示する。元フォルダの 依頼文/ に保存し、履歴に「依頼」の行。受け取るときは receive に --依頼のID を付ける
#   python3 tools/assets.py receive <キャラ> <納品メモ.csv> --依頼 "依頼の短い名前" --出どころ "Chatwork【…】／Codex など" [--原文 "依頼の原文"] [--依頼のID r…]
#       納品メモの素材を 90_保留/<日付>_<依頼>/ に写し、ライブラリの「保留」に足す。履歴に「受け取り」の行
#   python3 tools/assets.py decide <キャラ> <保留のID> <素材の名前|*> <採用|仮置き|直し|見送り> [--本人 "本人の言葉の原文"] [--決定 意思決定DBのページID]
#       採否を記録する。履歴に「採否」の行
#   python3 tools/assets.py promote <キャラ> <保留のID> <素材の名前|*> <アイコン|イメージ強化> [--組 <アイコンの組>]
#       採用・仮置きの素材を正式な場所に移す（今はアイコンとイメージ強化。ほかの種類は最初に実際に足すときに作る）。履歴に「追加」の行
#       11/18 アイコン・イメージ強化（と背景）は、キャラをまたぐ共通素材（chars.json の common）のドライブと台帳へ移す
#       （本人「素材は最終的にはどのキャラクターページにも表示するものになりそうなので、大元はもう一つ上の階層に保管。…」「一覧のとおり進めて」）
#   python3 tools/assets.py list <キャラ>
# 試し運転：環境変数 DRV_OVERRIDE（ドライブの代わりのフォルダ）と LIB_OVERRIDE（ライブラリの元フォルダの代わり。共通素材は LIB_OVERRIDE_common）
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
    lib = os.environ.get(f"LIB_OVERRIDE_{char}") or (os.environ.get("LIB_OVERRIDE") if not c.get("共通素材") else None) or os.path.expanduser(c["lib"])
    D = json.load(open(f"{lib}/data/library.json", encoding="utf-8"))
    place = D["キャラ"]["ドライブの場所"] if "キャラ" in D else D["ドライブの場所"]   # 共通素材の台帳は「キャラ」を持たない
    drv = os.environ.get("DRV_OVERRIDE") or f"{DRIVE_ROOT}/{place.rstrip('/')}"
    if os.environ.get("DRV_OVERRIDE") and "キャラ" not in D: drv = f"{drv}/_共通素材"   # 試し運転で、キャラと共通素材の置き場を分ける
    return lib, drv, D

def kind_of(char, 種類):
    """種類の置き場（chars.json の1項目）・ドライブ・その種類を持つキャラ（共通素材なら common）"""
    k = CHARS[char].get("種類", {}).get(種類)
    if not k: return None, None, None
    owner = "common" if k.get("共通") else char
    if owner != char: k = CHARS["common"]["種類"][種類]
    return k, paths(owner)[1], owner

def save(lib, D, rows=None):
    json.dump(D, open(f"{lib}/data/library.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if rows is not None:
        hp = f"{lib}/data/history.json"
        H = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else []
        H += rows
        json.dump(H, open(hp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def row(種類, 中身, 状態="", 本人="", 決定="", 出どころ="", ドライブ=""):
    return dict(日時=now(), 種類=種類, 中身=中身, 状態=状態, 本人=本人, 決定=決定, 出どころ=出どころ, ドライブ=ドライブ, 公開="")

FF = shutil.which("ffmpeg") or f"{HOME}/.local/bin/ffmpeg"

def alpha_box(src, pad=16):
    """全コマを通して透過でない範囲（x, y, 幅, 高さ）。測れないときは None"""
    r = subprocess.run([FF, "-v", "info", "-i", src, "-vf", "alphaextract,bbox=min_val=8", "-f", "null", "-"], capture_output=True, text=True)
    bs = [tuple(map(int, m)) for m in re.findall(r"x1:(\d+) x2:(\d+) y1:(\d+) y2:(\d+)", r.stderr)]
    if not bs: return None
    w0, h0 = map(int, re.search(r", (\d+)x(\d+)", r.stderr).groups())
    x1 = max(0, min(b[0] for b in bs) - pad); x2 = min(w0, max(b[1] for b in bs) + pad)
    y1 = max(0, min(b[2] for b in bs) - pad); y2 = min(h0, max(b[3] for b in bs) + pad)
    w, h = (x2 - x1) // 2 * 2, (y2 - y1) // 2 * 2
    return x1, y1, w, h

def thumb(src, lib, key):
    """見本の画像を media/hold/ に作る。静止画は avif（長い辺480）、GIF はそのまま（3MBまで）、動画は1コマ目
    11/14 3MBを超える動くGIF（等身大の作り直しなど）は、動きと画質を見られるように mp4 にする（透過の余白を切り、長い辺720まで、白地、コマの速さはそのまま）"""
    ext = os.path.splitext(src)[1].lower()
    h = hashlib.sha1(key.encode()).hexdigest()[:14]
    os.makedirs(f"{lib}/media/hold", exist_ok=True)
    if ext == ".gif" and os.path.getsize(src) <= 3_000_000:
        out = f"media/hold/{h}.gif"; shutil.copyfile(src, f"{lib}/{out}")
    elif ext == ".gif":
        out = f"media/hold/{h}.mp4"
        b = alpha_box(src)
        crop = f"crop={b[2]}:{b[3]}:{b[0]}:{b[1]}," if b else ""
        vf = f"{crop}scale='if(gt(iw,ih),min(720,iw),-2)':'if(gt(iw,ih),-2,min(720,ih))':flags=lanczos"
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", src,
                        "-filter_complex", f"[0:v]{vf},format=rgba,split[a][b];[a]drawbox=c=white:t=fill[bg];[bg][b]overlay,format=yuv420p",
                        "-c:v", "h264_videotoolbox", "-b:v", "3M", "-an", "-movflags", "+faststart", f"{lib}/{out}"], check=True)
    elif ext in (".mp4", ".mov", ".webm"):
        out = f"media/hold/{h}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-frames:v", "1", "-vf", "scale='min(480,iw)':-2", f"{lib}/{out}"], check=True)
    else:
        out = f"media/hold/{h}.avif"
        subprocess.run(["sips", "-Z", "480", "-s", "format", "avif", src, "--out", f"{lib}/{out}"], check=True, capture_output=True)
    return out

def compare(it, char, drv, lib):
    """11/14 同じ名前の素材が正式な場所に既にあるとき（差し替えの候補）、今の版の見本を「比べる」に付ける"""
    k, kdrv, _ = kind_of(char, it["種類"])
    old = f"{kdrv}/{k['フォルダ']}/{it['ファイル']}" if k else ""
    if old and os.path.isfile(old):
        it["比べる"] = thumb(old, lib, f"今の版/{k['フォルダ']}/{it['ファイル']}")

def slug(s):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")[:40]

# 11/18 本人「だから等身大って言葉自体使わないって等身大をVtuberの呼び方に変える。…」「外して」「自動で外して」（意思決定DB 41bc12971e2781619d3aefb8106d3c2c・41bc12971e2781569640d0661b4362c8・41bc12971e27814bbc3ff8e946ee76ff）
#   受け取るとき、Codexが付けた名前の「等身大」を外す。ファイル名・コマのフォルダ名・名前は「等身大_」を外す。組の名前（依頼）は「等身大」をVtuberにする
def no_tojin(s):
    s = re.sub(r"^等身大_?|(?<=_)等身大_", "", s)
    return s.replace("等身大", "Vtuber")
def no_tojin_group(s):
    return re.sub(r"等身大_?", "Vtuber_", s)

def receive(a):
    lib, drv, D = paths(a.char)
    a.依頼 = no_tojin_group(a.依頼)
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
        name = no_tojin(os.path.basename(r["ファイル"]))
        if os.path.exists(f"{dst}/{name}"): sys.exit(f"同じ名前のファイルが2つある：{name}")
        shutil.copyfile(src, f"{dst}/{name}")
        it = {"名前": no_tojin(r["名前"]), "種類": "Vtuber" if r["種類"] == "等身大" else r["種類"], "ファイル": name, "場所": f"{folder}/{name}", "src": thumb(src, lib, f"{folder}/{name}"), "状態": "保留"}
        if r.get("メモ"): it["メモ"] = r["メモ"]
        compare(it, a.char, drv, lib)
        if r.get("コマのフォルダ"):
            kd = os.path.join(base, r["コマのフォルダ"]); kname = f"{os.path.splitext(name)[0]}_コマ"
            shutil.copytree(kd, f"{dst}/{kname}"); it["コマのフォルダ"] = f"{folder}/{kname}"
            for f in os.listdir(f"{dst}/{kname}"):
                if no_tojin(f) != f: os.rename(f"{dst}/{kname}/{f}", f"{dst}/{kname}/{no_tojin(f)}")
        items.append(it)
    g = {"id": gid, "依頼": a.依頼, "出どころ": a.出どころ, "届いた日": now(), "フォルダ": folder, "素材": items}
    if a.原文: g["依頼の原文"] = a.原文
    if a.依頼のID: g["依頼のID"] = a.依頼のID
    D["保留"].append(g)
    save(lib, D, [row("受け取り", f"{a.依頼}（{len(items)}点）を保留に置いた［{gid}{'・' + a.依頼のID if a.依頼のID else ''}］", "保留", 出どころ=a.出どころ, ドライブ=folder)])
    print("保留に置いた", gid, len(items), "点 →", dst)

SITE = "https://goshi-54.github.io/righthemisphere-library"
MEMO_URL = "https://github.com/Goshi-54/righthemisphere-library/blob/main/tools/納品メモの書き方.md"

def examples(drv, folder, n=2):
    """同じ種類の今ある素材から、名前と大きさの例を取る"""
    out = []
    d = f"{drv}/{folder}"
    if not os.path.isdir(d): return out
    order = {".gif": 0, ".mp4": 1, ".png": 2, ".jpg": 3}   # 動くものを先に
    for f in sorted(os.listdir(d), key=lambda f: (order.get(os.path.splitext(f)[1].lower(), 9), f)):
        if os.path.splitext(f)[1].lower() not in order: continue
        r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", f"{d}/{f}"], capture_output=True, text=True).stdout
        wh = re.findall(r"pixel(?:Width|Height): (\d+)", r)
        out.append(f"{f}（{'×'.join(wh) if len(wh) == 2 else '大きさ不明'}・{os.path.splitext(f)[1][1:].upper()}）")
        if len(out) >= n: break
    return out

def request(a):
    """Codexへの依頼文（転送文）を作る。元フォルダの 依頼文/ に保存し、履歴に「依頼」の行を入れる"""
    lib, drv, D = paths(a.char)
    c = CHARS[a.char]; K = c.get("種類", {})
    if a.種類 not in K: sys.exit(f"種類は {list(K)} のどれか（tools/chars.json に足す）")
    k, kdrv, owner = kind_of(a.char, a.種類)
    items = [s.strip() for s in re.split(r"[;\n；]", a.中身) if s.strip()]
    if not items: sys.exit("--中身 に作ってほしいものを書く（;で区切る）")
    day = datetime.date.today().strftime("%Y%m%d")
    os.makedirs(f"{lib}/依頼文", exist_ok=True)
    rid = f"r{day}-{len([f for f in os.listdir(f'{lib}/依頼文') if f.startswith('r' + day)]) + 1:02d}"
    name = D["キャラ"]["名前"] if "キャラ" in D else c["名前"]
    kD = D if owner == a.char else paths(owner)[2]
    place = (kD["キャラ"]["ドライブの場所"] if "キャラ" in kD else kD["ドライブの場所"]).rstrip("/").replace("マイドライブ/", "")
    ex = examples(kdrv, k["フォルダ"])
    L = ["宛先：Codex",
         f"出所：本人の依頼を、Claude Code「素材のGoogleドライブ格納とWebツール化」が整理した。依頼のID {rid}" + (f"／作業ID {a.作業ID}" if a.作業ID else ""),
         f"依頼：{name}の{a.種類}を{len(items)}点（{a.依頼}）", ""]
    L += ["■ 作ってほしいもの"] + [f"{i}. {s}" for i, s in enumerate(items, 1)]
    if a.原文: L += [f"依頼の原文：「{a.原文}」" + (f"（{a.出どころ}）" if a.出どころ else "")]
    conds = [s.strip() for s in re.split(r"[;\n；]", a.条件 or "") if s.strip()]
    if conds: L += ["", "■ 求める品質・条件"] + [f"- {s}" for s in conds]
    L += ["", "■ 見た目のもと（ここに合わせる）",
          f"- キャラ情報とリファレンス：{SITE}/#{c['ページ']}",
          "  「採用」と出ているリファレンスを正とする。「採否未確認」は参考まで。「直し待ち」に書いてある失敗をくり返さない。",
          f"- 同じ種類の今ある素材：{SITE}/{CHARS[owner]['ページ']}/#{k['タブ']}",
          f"  本体はGoogleドライブ（このMacのマイドライブ）の「{place}/{k['フォルダ']}/」。大きさ・形式・線・色・動きの速さをこれにそろえる。" + ("「求める品質・条件」と食い違うときは、条件を優先する。" if conds else "")]
    if ex: L += ["  例：" + "、".join(ex)]
    if k.get("コマ"): L += [f"  もとのコマのPNGは「{place}/{k['コマ']}/」。"]
    L += ["", "■ 納品のしかた",
          f"- 作業フォルダの中に「納品_{rid}」フォルダを作り、素材のファイルと「納品メモ.csv」を置く。",
          f"- 納品メモの書き方：{MEMO_URL}（このMacでは ~/Code/righthemisphere-library/tools/納品メモの書き方.md）",
          f"  列は 名前,ファイル,種類,コマのフォルダ,メモ（UTF-8・1行に1点）。種類の列は「{a.種類}」。名前は何をしているかが分かる短い日本語。"]
    if k.get("コマ"): L += ["- GIF・動画には、もとのコマのPNGをフォルダごと付け、「コマのフォルダ」の列に書く。"]
    L += ["- 終わったら返信の最初に、納品フォルダの絶対パス、点数、自分で確かめたこと（大きさ・コマ数・ループのつなぎ目・透過・見た目がリファレンスとずれていないか）を書く。作れなかったものと理由も書く。",
          "", "■ 許可の範囲",
          "- 許可：上のものを、この作業フォルダの中で作ること。",
          "- 範囲外：Googleドライブ・素材ライブラリ・公開ページへの書き込み。受け取りは Claude Code が行い、採否は本人が決める。",
          "", "■ してはいけないこと",
          "- クレジットを使う生成サービス（Runway・Topview など）を使わない。生成サービスをブラウザや画面操作で動かさない。",
          "- 採用済みのリファレンスから、顔・髪・眼鏡・服・色を変えない。",
          "- ファイルを消さない。今ある素材を上書きしない。",
          "- 外部へ送信・公開・投稿しない。",
          "", "■ まだしていないこと",
          "- この素材は、まだ素材ライブラリの「保留」にも置いていない。納品のあと Claude Code が受け取って保留に置き、本人の採否で正式に足す。"]
    text = "\n".join(L)
    fn = f"{lib}/依頼文/{rid}_{slug(a.依頼)}.md"
    open(fn, "w", encoding="utf-8").write(f"# {rid} {a.依頼}\n\n- 作った日：{now()}\n- 種類：{a.種類}\n\n```text\n{text}\n```\n")
    save(lib, D, [row("依頼", f"Codexへの依頼文を作った：{a.種類}{len(items)}点（{a.依頼}）［{rid}］", "依頼文", 出どころ=a.出どころ or "")])
    print(text); print(f"\n（保存：{fn}）")

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

def media_for(src, lib, sub, nid, kind):
    """正式な素材の見本を media/<sub>/ に作る。アイコンは長い辺256のPNG。イメージ強化は、GIF（3MBまで）はそのまま、ほかは長い辺480のPNG"""
    os.makedirs(f"{lib}/media/{sub}", exist_ok=True)
    if kind == "イメージ強化" and src.lower().endswith(".gif") and os.path.getsize(src) <= 3_000_000:
        out = f"media/{sub}/{nid}.gif"; shutil.copyfile(src, f"{lib}/{out}"); return out
    out = f"media/{sub}/{nid}.png"
    subprocess.run(["sips", "-Z", "256" if kind == "アイコン" else "480", "-s", "format", "png", src, "--out", f"{lib}/{out}"], check=True, capture_output=True)
    return out

def promote(a):
    lib, drv, D = paths(a.char)
    g, its = pick(D, a.gid, a.name)
    its = [x for x in its if x["状態"] in ("採用", "仮置き")]
    if not its: sys.exit("採用・仮置きの素材がない（先に decide で採否を記録する）")
    if a.kind not in ("アイコン", "イメージ強化"): sys.exit("今はアイコンとイメージ強化だけ。ほかの種類は、最初に実際に足すときに作る")
    if a.kind == "アイコン" and not a.組: sys.exit("アイコンは --組 が要る（アプリ・文字バッジ・ドット絵 など）")
    k, kdrv, owner = kind_of(a.char, a.kind)
    if not k: sys.exit(f"tools/chars.json の {a.char} に「{a.kind}」がない")
    klib, _, KD = (lib, drv, D) if owner == a.char else paths(owner)
    folder, sub, pre = k["フォルダ"], ("icon" if a.kind == "アイコン" else "img"), ("n" if a.kind == "アイコン" else "m")
    n = max([int(x["id"][1:]) for x in KD[a.kind] if re.fullmatch(pre + r"\d+", x.get("id", ""))] or [0])
    for x in its:
        dst = f"{kdrv}/{folder}/{x['ファイル']}"
        if os.path.exists(dst): sys.exit(f"既にある：{dst}")
    for x in its:
        n += 1; nid = f"{pre}{n:03d}"
        dst = f"{kdrv}/{folder}/{x['ファイル']}"
        shutil.move(f"{drv}/{x['場所']}", dst)
        it = {"id": nid, "名前": os.path.splitext(x["ファイル"])[0], "src": media_for(dst, klib, sub, nid, a.kind), "場所": f"{folder}/{x['ファイル']}", "ファイル": x["ファイル"]}
        if a.組: it["組"] = a.組
        if a.kind == "アイコン": it["暗い背景"] = False
        if x["状態"] == "仮置き": it["仮置き"] = True
        if owner != a.char: it["出どころのキャラ"] = a.char
        KD[a.kind].append(it)
        g["素材"].remove(x)
    if not g["素材"]: D["保留"].remove(g)
    names = "・".join(x["名前"] for x in its)
    st = "・".join(sorted({x['状態'] for x in its})); hon = "・".join(x.get("本人", "") for x in its if x.get("本人"))
    where = f"{a.kind}" + (f"（{a.組}）" if a.組 else "")
    if owner != a.char:
        save(klib, KD, [row("追加", f"{where}：{names}［{CHARS[a.char]['名前']}の{g['id']}から］", st, hon, "", g["出どころ"], folder)])
        save(lib, D, [row("追加", f"{where}を共通素材へ移した：{names}［{g['id']}から］", st, hon, "", g["出どころ"], f"共通素材/{folder}")])
    else:
        save(lib, D, [row("追加", f"{where}：{names}［{g['id']}から］", st, hon, "", g["出どころ"], folder)])
    print(f"{a.kind}に足した", len(its), "点。add_download_ids.py → build_public.py を、" + ("キャラと共通素材の両方の元フォルダで" if owner != a.char else "元フォルダで") + "流し、make_top.py を流す")

def lst(a):
    lib, drv, D = paths(a.char)
    for g in D.get("保留", []):
        print(g["id"], g["依頼"], g["出どころ"], g["届いた日"])
        for x in g["素材"]: print("  ", x["状態"], x["種類"], x["名前"], x["ファイル"])
    if not D.get("保留"): print("保留はない")

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
p = sp.add_parser("receive"); p.add_argument("char"); p.add_argument("memo"); p.add_argument("--依頼", required=True); p.add_argument("--出どころ", required=True); p.add_argument("--原文"); p.add_argument("--依頼のID")
p = sp.add_parser("request"); p.add_argument("char"); p.add_argument("--種類", required=True); p.add_argument("--依頼", required=True); p.add_argument("--中身", required=True); p.add_argument("--原文"); p.add_argument("--出どころ"); p.add_argument("--作業ID"); p.add_argument("--条件")
p = sp.add_parser("decide"); p.add_argument("char"); p.add_argument("gid"); p.add_argument("name"); p.add_argument("state"); p.add_argument("--本人"); p.add_argument("--決定")
p = sp.add_parser("promote"); p.add_argument("char"); p.add_argument("gid"); p.add_argument("name"); p.add_argument("kind"); p.add_argument("--組", default="")
p = sp.add_parser("list"); p.add_argument("char")
a = ap.parse_args()
{"request": request, "receive": receive, "decide": decide, "promote": promote, "list": lst}[a.cmd](a)
