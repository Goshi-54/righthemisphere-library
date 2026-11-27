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
# 11/18 本人「…「保留」は僕生成の保留が多くなりそうなので、別口で「要望素材」みたいなカテゴリを素材ライブラリに用意してそこに格納したい。…各キャラクターページそれぞれに「要望素材」があるイメージ。後、…僕の保留に関してはもう一つ上の階層のところにデータも含めておいて、採用となったら各ページに下ろしたい。」
#   （意思決定DB 41cc12971e278179b8c0c7d8a228e510）
#   → 本人の保留：台帳は一つ上の階層（共通素材 common の library.json の「保留」）、ドライブは 2.素材ライブラリ/90_保留/。組に「キャラ」を持つ
#   → 要望素材（Chatworkの要望で作った物）：receive に --先 要望素材。台帳は各キャラの library.json の「要望素材」、ドライブは <キャラ>/91_要望素材/。組のIDは q…
#   → promote は、保留・要望素材のどちらからでも、正式な場所（キャラのページ、共通素材）へ下ろす。今はアイコン・イメージ強化・Vtuber（--時期）
# 11/19 本人「後で写す」（意思決定DB 41cc12971e2781aab2f3eec80f673509）：Chatworkの自動の流れ（3分おきの定時の作業）はドライブを開けない。
#   DRV_LATER（ドライブ待ちの置き場。ドライブと同じ並びで置き、あとで chatwork/本番の準備/drive_sync.py が写す）と
#   DRV_REF（見本の写し。drive_sync.py がドライブから写した、種類ごとの見本とそのコマ）を渡すと、ドライブの代わりにそこを使う
# 試し運転：環境変数 DRV_OVERRIDE（ドライブの代わりのフォルダ）と LIB_OVERRIDE（ライブラリの元フォルダの代わり。共通素材は LIB_OVERRIDE_common）
import os, sys, csv, json, shutil, hashlib, argparse, subprocess, datetime, re
HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
CHARS = json.load(open(f"{HERE}/chars.json", encoding="utf-8"))
import glob
_roots = glob.glob(f"{HOME}/Library/CloudStorage/GoogleDrive-*/マイドライブ")
DRIVE_ROOT = os.path.dirname(_roots[0]) if _roots else ""   # このMacのGoogleドライブ（アカウント名をコードに書かない）
HOLD = "90_保留"
REQ = "91_要望素材"
LIBROOT_PLACE = "マイドライブ/1. クリエイティブ/2.素材ライブラリ"   # 本人の保留はこの直下の 90_保留

LATER = os.environ.get("DRV_LATER", "").rstrip("/")
REF = os.environ.get("DRV_REF", "").rstrip("/")

def hold_root():
    o = os.environ.get("DRV_OVERRIDE")
    return f"{o}/_素材ライブラリ" if o else f"{LATER or DRIVE_ROOT}/{LIBROOT_PLACE}"

def ref_of(d):
    """ドライブ待ちの置き場の道を、見本の写しの道に読み替える（見本の写しが無いときはそのまま）"""
    return REF + d[len(LATER):] if LATER and REF and d.startswith(LATER + "/") else d
STATES = ("保留", "採用", "仮置き", "直し", "見送り")
now = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def paths(char):
    c = CHARS[char]
    lib = os.environ.get(f"LIB_OVERRIDE_{char}") or (os.environ.get("LIB_OVERRIDE") if not c.get("共通素材") else None) or os.path.expanduser(c["lib"])
    D = json.load(open(f"{lib}/data/library.json", encoding="utf-8"))
    place = D["キャラ"]["ドライブの場所"] if "キャラ" in D else D["ドライブの場所"]   # 共通素材の台帳は「キャラ」を持たない
    drv = os.environ.get("DRV_OVERRIDE") or f"{LATER or DRIVE_ROOT}/{place.rstrip('/')}"
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

def _gif_box(src):
    """透過GIFの全コマを合わせた絵のある範囲（x, y, 幅, 高さ）。絵が画面の4割より小さいときだけ返す（それ以外は None）
    11/19 Vtuberの届いた版（1024×2048の上の方に人物）が、札の中で小さく見えた。全コマの動きが収まる範囲で切り、周りに4％の余白を残す"""
    r = subprocess.run([FF, "-v", "info", "-i", src, "-vf", "format=rgba,alphaextract,bbox=min_val=128", "-f", "null", "-"], capture_output=True, text=True)
    bs = re.findall(r"x1:(\d+) x2:(\d+) y1:(\d+) y2:(\d+)", r.stderr)
    m = re.search(r"Stream #0:0.*?, (\d+)x(\d+)", r.stderr)
    if not bs or not m: return None
    W, H = int(m.group(1)), int(m.group(2))
    x1 = min(int(b[0]) for b in bs); x2 = max(int(b[1]) for b in bs); y1 = min(int(b[2]) for b in bs); y2 = max(int(b[3]) for b in bs)
    if (x2 - x1 + 1) * (y2 - y1 + 1) >= 0.4 * W * H: return None
    pad = round(0.04 * max(x2 - x1, y2 - y1))
    x1, y1, x2, y2 = max(0, x1 - pad), max(0, y1 - pad), min(W - 1, x2 + pad), min(H - 1, y2 + pad)
    return x1, y1, x2 - x1 + 1, y2 - y1 + 1

def thumb(src, lib, key):
    """見本の画像を media/hold/ に作る。静止画は avif（長い辺480）、GIF はそのまま（3MBまで）、動画は1コマ目
    11/14 3MBを超える動くGIF（等身大の作り直しなど）は、動きと画質を見られるように mp4 にする（透過の余白を切り、長い辺720まで、白地、コマの速さはそのまま）
    11/19 本人「小さなアイコンも嫌だし、透過素材なのに白いものの上も嫌。素材として見やすいようにバランスとって」（意思決定DB 41dc12971e278162ab04d0a1f806c3cb）
      → mp4（白地・余白を切って大きく見える）をやめ、3MBを超えるGIFも、余白を切らずに長い辺480の透過のGIFにする（ほかのGIFと同じ見え方にそろえる）"""
    ext = os.path.splitext(src)[1].lower()
    h = hashlib.sha1(key.encode()).hexdigest()[:14]
    os.makedirs(f"{lib}/media/hold", exist_ok=True)
    box = _gif_box(src) if ext == ".gif" else None
    if ext == ".gif" and os.path.getsize(src) <= 3_000_000 and not box:
        out = f"media/hold/{h}.gif"; shutil.copyfile(src, f"{lib}/{out}")
    elif ext == ".gif":
        out = f"media/hold/{h}.gif"
        for side in (480, 360, 270):   # ページが重くならないよう、3MBに収まるまで長い辺を下げる
            vf = ("crop=%d:%d:%d:%d," % (box[2], box[3], box[0], box[1]) if box else "") + f"scale='if(gt(iw,ih),min({side},iw),-2)':'if(gt(iw,ih),-2,min({side},ih))':flags=lanczos"
            subprocess.run([FF, "-y", "-loglevel", "error", "-i", src,
                            "-filter_complex", f"[0:v]{vf},split[a][b];[a]palettegen=reserve_transparent=1:stats_mode=full[p];[b][p]paletteuse=dither=none:alpha_threshold=128",
                            "-gifflags", "-offsetting", f"{lib}/{out}"], check=True)
            if os.path.getsize(f"{lib}/{out}") <= 3_000_000: break
    elif ext in (".mp4", ".mov", ".webm"):
        out = f"media/hold/{h}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-frames:v", "1", "-vf", "scale='min(480,iw)':-2", f"{lib}/{out}"], check=True)
    else:
        out = f"media/hold/{h}.avif"
        subprocess.run(["sips", "-Z", "480", "-s", "format", "avif", src, "--out", f"{lib}/{out}"], check=True, capture_output=True)
    return out

def compare(it, char, lib):
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
    req = a.先 in ("要望素材", "Claude Codeキャラの要望素材")
    # 11/19 共通素材の中の「Claude Codeキャラ」（意思決定DB 41dc12971e278192a110e40da35606b2）：Claude Codeキャラの要望は、共通素材の台帳と 共通素材/91_要望素材 に置く
    cc = a.先 == "Claude Codeキャラの要望素材"
    # 本人の保留は一つ上の階層（common の台帳・2.素材ライブラリ/90_保留）、要望素材はキャラの台帳・<キャラ>/91_要望素材
    if cc: owner, (olib, root, OD), key, pre, top = "common", paths("common"), "Claude Codeキャラの要望素材", "qc", REQ
    elif req: owner, olib, OD, root, key, pre, top = a.char, lib, D, drv, "要望素材", "q", REQ
    else: owner, (olib, _, OD), root, key, pre, top = "common", paths("common"), hold_root(), "保留", "h", HOLD
    base = os.path.dirname(os.path.abspath(a.memo))
    rows = list(csv.DictReader(open(a.memo, encoding="utf-8-sig")))
    if not rows: sys.exit("納品メモに行がない")
    for need in ("名前", "ファイル", "種類"):
        if need not in rows[0]: sys.exit(f"納品メモに「{need}」の列がない")
    day = datetime.date.today().strftime("%Y%m%d")
    folder = f"{top}/{day}_{slug(a.依頼)}"
    # 11/20 c20261119-22：同じ日に同じ中身の依頼（口パクと全身の動き）が来て、2件目が「既にある」で止まった。
    #   前の物は触らず、後から来た方の置き場に「_2」「_3」…を付ける（意思決定DB 41ec12971e278154885ce8894c8d4c4f）
    n = 1
    while os.path.exists(f"{root}/{folder}" if n == 1 else f"{root}/{folder}_{n}"): n += 1
    if n > 1: folder = f"{folder}_{n}"
    dst = f"{root}/{folder}"
    OD.setdefault(key, [])
    gid = f"{pre}{day}-{len([g for g in OD[key] if g['id'].startswith(pre + day)]) + 1:02d}"
    items = []
    others = lambda r: [x.strip() for x in re.split(r"[;；]", r.get("ほかのファイル") or "") if x.strip()]
    for r in rows:
        for f in [r["ファイル"]] + others(r):
            src = os.path.join(base, f)
            if not os.path.isfile(src): sys.exit(f"ファイルがない：{src}")
    os.makedirs(dst)
    for r in rows:
        src = os.path.join(base, r["ファイル"])
        name = no_tojin(os.path.basename(r["ファイル"]))
        if os.path.exists(f"{dst}/{name}"): sys.exit(f"同じ名前のファイルが2つある：{name}")
        shutil.copyfile(src, f"{dst}/{name}")
        # 11/19 ほかのファイル：同じ素材の別の版（通常版に対するループ版など。段階2が納品メモに書く）。同じフォルダに置き、ダウンロードにも出す。
        #   公開ページの見本は、ループ版があればそちらで作る（1回再生の通常版だと、ページで止まって見えるため）
        more = []
        for f in others(r):
            m = no_tojin(os.path.basename(f))
            if os.path.exists(f"{dst}/{m}"): sys.exit(f"同じ名前のファイルが2つある：{m}")
            shutil.copyfile(os.path.join(base, f), f"{dst}/{m}"); more.append(m)
        show = next((os.path.join(base, f) for f in others(r) if "_ループ" in f), src)
        it = {"名前": no_tojin(r["名前"]), "種類": "Vtuber" if r["種類"] == "等身大" else r["種類"], "ファイル": name, "場所": f"{folder}/{name}", "src": thumb(show, olib, f"{folder}/{name}"), "状態": "要望" if req else "保留"}
        if more: it["ほかのファイル"] = more
        if r.get("メモ"): it["メモ"] = r["メモ"]
        compare(it, a.char, olib)
        if r.get("コマのフォルダ"):
            kd = os.path.join(base, r["コマのフォルダ"]); kname = f"{os.path.splitext(name)[0]}_コマ"
            shutil.copytree(kd, f"{dst}/{kname}"); it["コマのフォルダ"] = f"{folder}/{kname}"
            for f in os.listdir(f"{dst}/{kname}"):
                if no_tojin(f) != f: os.rename(f"{dst}/{kname}/{f}", f"{dst}/{kname}/{no_tojin(f)}")
        items.append(it)
    g = {"id": gid, "依頼": a.依頼, "出どころ": a.出どころ, "届いた日": now(), "フォルダ": folder, "キャラ": a.char, "キャラ名": "Claude Code" if cc else CHARS[a.char]["名前"], "素材": items}
    if a.原文: g["依頼の原文"] = a.原文
    if a.依頼のID: g["依頼のID"] = a.依頼のID
    if a.受付: g["受付番号"] = a.受付
    OD[key].append(g)
    r = row("受け取り", f"{a.依頼}（{len(items)}点）を{key}に置いた［{gid}{'・' + a.依頼のID if a.依頼のID else ''}］", key, 出どころ=a.出どころ, ドライブ=folder)
    save(olib, OD, [r])
    if owner != a.char: save(lib, D, [r])   # キャラの履歴にも残す（入口の更新の記録に出る）
    print(f"{key}に置いた", gid, len(items), "点 →", dst)
    print(f"ページ：{SITE}/{CHARS[owner]['ページ']}/#{gid}")

SITE = "https://goshi-54.github.io/righthemisphere-library"
MEMO_URL = "https://github.com/Goshi-54/righthemisphere-library/blob/main/tools/納品メモの書き方.md"

def examples(drv, folder, n=2):
    """同じ種類の今ある素材から、名前と大きさの例を取る"""
    out = []
    d = ref_of(f"{drv}/{folder}")
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
         f"出所：{a.出どころ or '本人の依頼'}を、Claude Code（素材ライブラリ）が整理した。依頼のID {rid}" + (f"／作業ID {a.作業ID}" if a.作業ID else ""),
         f"依頼：{name}の{a.種類}を{len(items)}点（{a.依頼}）", ""]
    L += ["■ 作ってほしいもの"] + [f"{i}. {s}" for i, s in enumerate(items, 1)]
    if a.原文: L += [f"依頼の原文：「{a.原文}」" + (f"（{a.出どころ}）" if a.出どころ else "")]
    conds = [s.strip() for s in re.split(r"[;\n；]", a.条件 or "") if s.strip()]
    if conds: L += ["", "■ 求める品質・条件"] + [f"- {s}" for s in conds]
    L += ["", "■ 見た目のもと（ここに合わせる）",
          *([] if a.キャラなし else ["- キャラ情報とリファレンス：このMacの ~/Code/systems/library/メタ環境/ から、依頼に対応する系統の 01_確定リファレンス と 02_仕様書と制作判断軸.md を確認する。",
          "  「採用」と出ているリファレンスを正とする。「採否未確認」は参考まで。「直し待ち」に書いてある失敗をくり返さない。"]),
          f"- 同じ種類の今ある素材：{SITE}/{CHARS[owner]['ページ']}/#{k['タブ']}",
          (f"  本体はGoogleドライブ（このMacのマイドライブ）の「{place}/{k['フォルダ']}/」。" if not (LATER and REF) else
           f"  本体はGoogleドライブの「{place}/{k['フォルダ']}/」。この作業からはドライブを開けないので、見本の写し「{ref_of(kdrv + '/' + k['フォルダ'])}/」を見る。")
          # 11/19 本人「アイコンやイメージ強化素材もClaude Codeキャラと同様に変に縛られたりしないで作れるようにして。」：共通素材系は参考どまり
          + ("大きさ・形式・線・色・動きの速さの参考にする（そろえることは求めない。中身に合う形で作る）。" if owner == "common" else "大きさ・形式・線・色・動きの速さをこれにそろえる。")
          + ("「求める品質・条件」と食い違うときは、条件を優先する。" if conds else "")]
    if ex: L += ["  例：" + "、".join(ex)]
    if k.get("コマ"): L += [f"  もとのコマのPNGは「{place}/{k['コマ']}/」。" if not (LATER and REF) else f"  もとのコマのPNG（見本の分だけ）は「{ref_of(kdrv + '/' + k['コマ'])}/」。"]
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

def find(char, gid, where=None):
    """組を探す。本人の保留は一つ上の階層（common）、要望素材はキャラの台帳。返すのは（台帳の持ち主, 台帳の元, 台帳, 置き場の根, 組の一覧の名前, 組）
    where＝「common:Claude Codeキャラの要望素材」のように一覧を指すと、そこだけ探す（11/20 q20261119-22 が、でぷれさんの要望素材とClaude Codeキャラの要望素材の両方にある）"""
    order = (("common", "保留"), (char, "要望素材"), (char, "保留"), ("common", "Claude Codeキャラの要望素材"), ("common", "要望素材"))
    if where: order = (tuple(where.split(":", 1)),)
    for owner, key in order:
        lib, drv, D = paths(owner)
        g = next((g for g in D.get(key, []) if g["id"] == gid), None)
        if g: return owner, lib, D, (hold_root() if (owner == "common" and key == "保留") else drv), key, g
    sys.exit(f"保留にも要望素材にもない：{gid}")

def pick(g, name):
    its = list(g["素材"]) if name == "*" else [x for x in g["素材"] if x["名前"] == name]   # 写しを返す（組の一覧を直接いじらない）
    if not its: sys.exit(f"素材がない：{name}")
    return its

def decide(a):
    if a.state not in STATES[1:]: sys.exit(f"状態は {STATES[1:]} のどれか")
    owner, lib, D, root, key, g = find(a.char, a.gid, getattr(a, "where", None))
    its = pick(g, a.name)
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
    howner, hlib, HD, hroot, hkey, g = find(a.char, a.gid, getattr(a, "where", None))
    a.char = g.get("キャラ", a.char)   # 下ろす先は組のキャラ
    its = [x for x in pick(g, a.name) if x["状態"] in ("採用", "仮置き")]
    if not its: sys.exit("採用・仮置きの素材がない（先に decide で採否を記録する）")
    if a.kind == "Vtuber": return promote_vtuber(a, howner, hlib, HD, hroot, hkey, g, its)
    # 11/20 本人「おすすめで作る」（意思決定DB 41ec12971e278191a188c6f94f4f8484）：口パク・全身の動き・掛け合い・マイクラ・Claude Codeキャラも下ろせるようにした
    if a.kind in MOTION: return promote_motion(a, howner, hlib, HD, hroot, hkey, g, its)
    if a.kind == "Claude Codeキャラ" or hkey == "Claude Codeキャラの要望素材": return promote_cc(a, howner, hlib, HD, hroot, hkey, g, its)
    if a.kind == "背景": return promote_bg(a, howner, hlib, HD, hroot, hkey, g, its)
    if a.kind not in ("アイコン", "イメージ強化"): sys.exit("下ろせる種類：アイコン・イメージ強化・背景・Vtuber・口パク・全身の動き・掛け合い・マイクラ・Claude Codeキャラ")
    lib, drv, D = paths(a.char)
    if howner == a.char: D = HD   # 同じ台帳を2回読まない（片方の保存で、もう片方の変更が消えるのを防ぐ）
    if a.kind == "アイコン" and not a.組: sys.exit("アイコンは --組 が要る（アプリ・文字バッジ・ドット絵 など）")
    k, kdrv, owner = kind_of(a.char, a.kind)
    if not k: sys.exit(f"tools/chars.json の {a.char} に「{a.kind}」がない")
    klib, _, KD = (lib, drv, D) if owner == a.char else paths(owner)
    if howner == owner: KD = HD
    folder, sub, pre = k["フォルダ"], ("icon" if a.kind == "アイコン" else "img"), ("n" if a.kind == "アイコン" else "m")
    n = max([int(x["id"][1:]) for x in KD[a.kind] if re.fullmatch(pre + r"\d+", x.get("id", ""))] or [0])
    for x in its:
        dst = f"{kdrv}/{folder}/{x['ファイル']}"
        if os.path.exists(dst): sys.exit(f"既にある：{dst}")
    for x in its:
        n += 1; nid = f"{pre}{n:03d}"
        dst = f"{kdrv}/{folder}/{x['ファイル']}"
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.move(f"{hroot}/{x['場所']}", dst)
        it = {"id": nid, "名前": os.path.splitext(x["ファイル"])[0], "src": media_for(dst, klib, sub, nid, a.kind), "場所": f"{folder}/{x['ファイル']}", "ファイル": x["ファイル"]}
        if a.組: it["組"] = a.組
        if a.kind == "アイコン": it["暗い背景"] = False
        if x["状態"] == "仮置き": it["仮置き"] = True
        if owner != a.char: it["出どころのキャラ"] = a.char
        KD[a.kind].append(it)
        g["素材"].remove(x)
    if not g["素材"]: HD[hkey].remove(g)
    if howner not in (owner, a.char): save(hlib, HD)
    names = "・".join(x["名前"] for x in its)
    st = "・".join(sorted({x['状態'] for x in its})); hon = "・".join(x.get("本人", "") for x in its if x.get("本人"))
    where = f"{a.kind}" + (f"（{a.組}）" if a.組 else "")
    if owner != a.char:
        save(klib, KD, [row("追加", f"{where}：{names}［{CHARS[a.char]['名前']}の{g['id']}から］", st, hon, "", g["出どころ"], folder)])
        save(lib, D, [row("追加", f"{where}を共通素材へ移した：{names}［{g['id']}から］", st, hon, "", g["出どころ"], f"共通素材/{folder}")])
    else:
        save(lib, D, [row("追加", f"{where}：{names}［{g['id']}から］", st, hon, "", g["出どころ"], folder)])
    print(f"{a.kind}に足した", len(its), "点。add_download_ids.py → build_public.py を、" + ("キャラと共通素材の両方の元フォルダで" if owner != a.char else "元フォルダで") + "流し、make_top.py を流す")

def promote_vtuber(a, howner, hlib, HD, hroot, hkey, g, its):
    """Vtuberの素材を、キャラのページの生成時期のタブ（--時期 t1117 など）へ下ろす。ドライブは 02_Vtuber/<時期>/ に移す"""
    lib, drv, D = paths(a.char)
    if howner == a.char: D = HD
    # 11/20 --時期 が無いときは、組の届いた日の時期（Vtuberのタブは生成時期別。11/18 本人）。その時期のタブが無ければ作る
    if not a.時期: a.時期 = "t" + g["届いた日"][5:7] + g["届いた日"][8:10]
    p = next((p for p in D["等身大"]["時期"] if p["id"] == a.時期), None)
    if not p:
        md = a.時期[1:]
        p = {"id": a.時期, "名前": f"{int(md[:2])}/{int(md[2:])}", "タブ名": f"{int(md[:2])}/{int(md[2:])}", "素材": [], "場所": f"02_Vtuber/{md}"}
        D["等身大"]["時期"].append(p); D["等身大"]["時期"].sort(key=lambda q: q["id"], reverse=True)
    if p.get("今の版"): sys.exit("今の版の時期へは下ろさない（別の作りのため）")
    folder = p.get("場所") or f"02_Vtuber/{a.時期[1:]}"
    for x in its:
        if os.path.exists(f"{drv}/{folder}/{x['ファイル']}"): sys.exit(f"既にある：{drv}/{folder}/{x['ファイル']}")
    os.makedirs(f"{drv}/{folder}", exist_ok=True)
    for x in its:
        shutil.move(f"{hroot}/{x['場所']}", f"{drv}/{folder}/{x['ファイル']}")
        it = {k: x[k] for k in ("名前", "ファイル", "メモ", "dl") if k in x}
        it["場所"] = f"{folder}/{x['ファイル']}"
        if x.get("コマのフォルダ"):
            kname = os.path.basename(x["コマのフォルダ"]); shutil.move(f"{hroot}/{x['コマのフォルダ']}", f"{drv}/{folder}/{kname}"); it["コマのフォルダ"] = f"{folder}/{kname}"
        if howner != a.char and x["src"].startswith("media/"):   # 見本を、キャラのページの側へ写す
            os.makedirs(os.path.dirname(f"{lib}/{x['src']}"), exist_ok=True); shutil.copyfile(f"{hlib}/{x['src']}", f"{lib}/{x['src']}")
        it["src"] = x["src"]
        if x["状態"] == "仮置き": it["仮置き"] = True
        p.setdefault("素材", []).append(it)
        g["素材"].remove(x)
    p["場所"] = folder; p.pop("非表示", None); p.pop("保留のID", None)
    if not g["素材"]: HD[hkey].remove(g)
    names = "・".join(x["名前"] for x in its); st = "・".join(sorted({x['状態'] for x in its}))
    r = row("追加", f"Vtuber（{p.get('タブ名', a.時期)}）：{names}［{g['id']}から］", st, "", "", g["出どころ"], folder)
    save(lib, D, [r])
    if howner != a.char: save(hlib, HD, [r])
    print(f"Vtuber（{p.get('タブ名', a.時期)}）に下ろした", len(its), "点。add_download_ids.py → build_public.py を流し、make_top.py を流す")


# 11/20 本人「おすすめで作る」（意思決定DB 41ec12971e278191a188c6f94f4f8484）：待っている素材（保留・要望素材）を、採否を決めて種類のタブへ移す
MOTION = {"口パク": "口パク", "全身の動き": "全身", "掛け合い": "掛け合い", "マイクラ": "マイクラ"}   # 種類 → 台帳の項目
FP = shutil.which("ffprobe") or f"{HOME}/.local/bin/ffprobe"

def gif_frames(src, lib):
    """GIFのコマを、ページのコマ送り用の見本（長い辺320のavif）と表示時間（ms）にする。同じ絵は同じファイルにまとめる"""
    import tempfile
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=duration_time,pkt_duration_time", "-of", "json", src], capture_output=True, text=True, check=True)
    ms = [round(float(f.get("duration_time") or f.get("pkt_duration_time") or 0.1) * 1000) for f in json.loads(r.stdout).get("frames", [])]
    out = []
    os.makedirs(f"{lib}/media/f", exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        subprocess.run([FF, "-v", "error", "-i", src, "-fps_mode", "passthrough", f"{t}/%04d.png"], check=True, capture_output=True)
        for i, p in enumerate(sorted(os.listdir(t))):
            av = f"media/f/{hashlib.sha1(open(f'{t}/{p}', 'rb').read()).hexdigest()[:12]}.avif"
            if not os.path.exists(f"{lib}/{av}"):
                subprocess.run(["sips", "-Z", "320", "-s", "format", "avif", f"{t}/{p}", "--out", f"{lib}/{av}"], check=True, capture_output=True)
            out.append({"src": av, "ms": ms[i] if i < len(ms) else 100})
    if not out: sys.exit(f"GIFのコマが取れなかった：{src}")
    return out

def promote_motion(a, howner, hlib, HD, hroot, hkey, g, its):
    """口パク・全身の動き・掛け合い・マイクラを、キャラのページの種類のタブとドライブの種類のフォルダへ下ろす。
    口パクは「<名前>」（正面）と「<名前>_斜め」を1つの素材にまとめる。コマのPNGは種類のコマのフォルダへ「<名前>_<コマ>(_斜め).png」で移す"""
    key = MOTION[a.kind]
    lib, drv, D = paths(a.char)
    if howner == a.char: D = HD
    k = CHARS[a.char].get("種類", {}).get(a.kind)
    if not k or not k.get("フォルダ"): sys.exit(f"tools/chars.json の {a.char} に「{a.kind}」の置き場がない")
    main = [x for x in its if not x["名前"].endswith("_斜め")]
    if len(main) != 1: sys.exit(f"{a.kind}は、1回に1つの素材を下ろす（_斜めは正面と一緒に下ろす）")
    m = main[0]; stem = os.path.splitext(m["ファイル"])[0]
    side = next((x for x in g["素材"] if x["名前"] == m["名前"] + "_斜め"), None) if a.kind == "口パク" else None
    parts = [("正面", m)] + ([("斜め角度", side)] if side else [])
    moves, files, koma, frames = [], {}, [], {}
    for muki, x in parts:
        names = [x["ファイル"]] + x.get("ほかのファイル", [])
        files[muki] = names
        for n in names: moves.append((f"{hroot}/{os.path.dirname(x['場所'])}/{n}", f"{drv}/{k['フォルダ']}/{n}"))
        if x.get("コマのフォルダ"):
            kd = f"{hroot}/{x['コマのフォルダ']}"
            if not os.path.isdir(kd): sys.exit(f"コマのフォルダがない（ドライブにまだ写っていないかも。drive_sync.py を先に）：{kd}")
            for f in sorted(os.listdir(kd)):
                if f.startswith(".") or not f.lower().endswith(".png"): continue
                o = os.path.splitext(f)[0].replace(f"_{stem}_", "_").replace(f"{stem}_", "")   # 元の名前に素材名が入っていれば外す（01_<名前>_立ち姿 → 01_立ち姿）
                new = f"{stem}_{o}" + ("_斜め" if muki == "斜め角度" and not o.endswith("_斜め") else "") + ".png"
                moves.append((f"{kd}/{f}", f"{drv}/{k['コマ']}/{new}")); koma.append(new)
    for s_, d_ in moves:
        if not os.path.exists(s_): sys.exit(f"もとのファイルがない（ドライブにまだ写っていないかも。drive_sync.py を先に）：{s_}")
        if os.path.exists(d_): sys.exit(f"既にある：{d_}")
    for muki, x in parts: frames[muki] = gif_frames(f"{hroot}/{x['場所']}", lib)
    lst_ = D["マイクラ"]["動作"] if key == "マイクラ" else D[key]
    sample = lst_[0] if lst_ else {}
    nid = {"口パク": "lip", "全身": "body", "掛け合い": "duet", "マイクラ": "mc"}[key] + "-" + g["id"] + "-" + hashlib.sha1(m["名前"].encode()).hexdigest()[:4]
    it = {"id": nid, "名前": m["名前"], "区分": "保留から" if hkey == "保留" else "要望素材から", "出どころ": g["出どころ"], "採用の日": now(),
          "置き場": {"種類": "drive", "url": (sample.get("置き場") or {}).get("url", ""), "場所": f"{k['フォルダ']}/{m['ファイル']}"}}
    if a.kind == "口パク":
        it["向き"] = {"正面": frames["正面"], "斜め角度": frames.get("斜め角度", frames["正面"])}
        it["ファイル"] = {"正面": files["正面"], "斜め角度": files.get("斜め角度", [])}
        if not side: it["斜めなし"] = True
        it["コマのドライブ"] = sample.get("コマのドライブ", "")
    else:
        it["コマ"] = frames["正面"]; it["ファイル"] = files["正面"]
        if key == "マイクラ": it["系統"] = "要望素材から"
    it["コマのファイル"] = koma; it["コマのフォルダ"] = k["コマ"]
    if any(x["状態"] == "仮置き" for _, x in parts): it["仮置き"] = True
    if m.get("メモ"): it["メモ"] = m["メモ"]
    it["dl"] = [d for _, x in parts for d in x.get("dl", []) if d[2] == "本体"]   # 本体のIDは引き継ぐ。コマは名前が変わるので add_download_ids.py が付け直す
    for s_, d_ in moves:
        os.makedirs(os.path.dirname(d_), exist_ok=True); shutil.move(s_, d_)
    lst_.append(it)
    for _, x in parts: g["素材"].remove(x)
    if not g["素材"]: HD[hkey].remove(g)
    st = "・".join(sorted({x["状態"] for _, x in parts})); hon = "・".join(x.get("本人", "") for _, x in parts if x.get("本人"))
    r = row("追加", f"{a.kind}：{m['名前']}" + ("（正面・斜め）" if side else "") + f"［{g['id']}から］", st, hon, "", g["出どころ"], k["フォルダ"])
    save(lib, D, [r])
    if howner != a.char: save(hlib, HD, [r])
    print(f"{a.kind}に下ろした：{m['名前']}" + ("（正面・斜め）" if side else ""), len(moves), "ファイルを移した")

def promote_cc(a, howner, hlib, HD, hroot, hkey, g, its):
    """Claude Codeキャラの要望素材を、共通素材の「Claude Codeキャラ」の一覧へ下ろす。
    Claude Codeキャラ専用のドライブのフォルダはまだ無いので、ファイルは今の場所に置いたまま（11/19 の保留からの合流と同じ）"""
    lib, drv, D = paths("common")
    if howner == "common": D = HD
    for x in its:
        it = {"id": "cc-" + g["id"] + "-" + hashlib.sha1(x["名前"].encode()).hexdigest()[:4], "名前": x["名前"], "組": "要望素材から", "src": x["src"],
              "場所": x["場所"], "ファイル": x["ファイル"], "合流": f"{g['id']} {g['依頼']}（{g['届いた日']} {g['出どころ']}）"}
        for k_ in ("メモ", "dl", "ほかのファイル"):
            if x.get(k_): it[k_] = x[k_]
        if x["状態"] == "仮置き": it["仮置き"] = True
        D["Claude Codeキャラ"].append(it); g["素材"].remove(x)
    if not g["素材"]: HD[hkey].remove(g)
    names = "・".join(x["名前"] for x in its)
    save(lib, D, [row("追加", f"Claude Codeキャラ：{names}［{g['id']}から］", "・".join(sorted({x['状態'] for x in its})), "", "", g["出どころ"], g["フォルダ"])])
    print("Claude Codeキャラに下ろした", len(its), "点（ファイルは今の場所のまま）")

def promote_bg(a, howner, hlib, HD, hroot, hkey, g, its):
    """背景（動く背景のmp4・静止画）を、共通素材の「背景」へ下ろす。ドライブは 01_背景/ に移す"""
    k, kdrv, owner = kind_of(a.char, "背景")
    klib, _, KD = paths(owner)
    if howner == owner: KD = HD
    for x in its:
        if os.path.exists(f"{kdrv}/{k['フォルダ']}/{x['ファイル']}"): sys.exit(f"既にある：{kdrv}/{k['フォルダ']}/{x['ファイル']}")
    os.makedirs(f"{klib}/media/bg", exist_ok=True)
    for x in its:
        dst = f"{kdrv}/{k['フォルダ']}/{x['ファイル']}"
        shutil.move(f"{hroot}/{x['場所']}", dst)
        nid = "b" + g["id"][1:] + "-" + hashlib.sha1(x["名前"].encode()).hexdigest()[:4]
        it = {"id": nid, "名前": x["名前"], "場所": f"{k['フォルダ']}/{x['ファイル']}", "ファイル": x["ファイル"], "中身": x.get("メモ", ""),
              "根拠": f"{g['出どころ']}（{g['届いた日']}）", "url": (KD["背景"][0] if KD["背景"] else {}).get("url", "")}
        poster = f"media/bg/{nid}.jpg"; shutil.copyfile(f"{hlib}/{x['src']}", f"{klib}/{poster}")
        if dst.lower().endswith(".mp4") and os.path.getsize(dst) <= 8_000_000:
            it["src"] = f"media/bg/{nid}.mp4"; shutil.copyfile(dst, f"{klib}/{it['src']}"); it["poster"] = poster
        else:
            it["src"] = poster
        if x.get("dl"): it["dl"] = x["dl"]
        if x["状態"] == "仮置き": it["仮置き"] = True
        if owner != a.char: it["出どころのキャラ"] = a.char
        KD["背景"].append(it); g["素材"].remove(x)
    if not g["素材"]: HD[hkey].remove(g)
    r = row("追加", f"背景：{'・'.join(x['名前'] for x in its)}［{g['id']}から］", "・".join(sorted({x['状態'] for x in its})), "", "", g["出どころ"], k["フォルダ"])
    save(klib, KD, [r])
    if howner != owner: save(hlib, HD, [r])
    print("背景に下ろした", len(its), "点")

def reject(gid, name, memo="", where=None):
    """不採用（11/18 の案A）：台帳の「前の版・非採用」に、ドライブの場所とページのURLだけを残し、待っている一覧から外す。ファイルは消さない"""
    owner, lib, D, root, key, g = find(next(iter(CHARS)), gid, where)
    its = pick(g, name)
    its += [x for x in g["素材"] if x["名前"] in {y["名前"] + "_斜め" for y in its} and x not in its]   # 口パクの斜めは正面と一緒に
    D.setdefault("前の版・非採用", [])
    for x in its:
        D["前の版・非採用"].append({"名前": x["名前"], "種類": x["種類"], "場所": x["場所"], "組のID": g["id"], "依頼": g["依頼"], "出どころ": g["出どころ"],
                                 "届いた日": g["届いた日"], "決めた日": now(), "メモ": memo, "dl": x.get("dl", [])})
        g["素材"].remove(x)
    if not g["素材"]: D[key].remove(g)
    save(lib, D, [row("採否", f"{g['依頼']}：{'・'.join(x['名前'] for x in its)}［{g['id']}］", "見送り（前の版・非採用へ）", memo, "", g["出どころ"], g["フォルダ"])])
    print("不採用にした", len(its), "点（ファイルはドライブのまま）")

def apply_decisions(a):
    """採否を決めるページの答え（JSON の一覧）を、台帳とドライブに当てる。
    1行：{"組のID": "...", "名前": "...", "判定": "採用|仮置き|不採用|直す", "メモ": "...", "本人": "（押した人の言葉）"}
    採用・仮置き：採否を記録して種類のタブへ下ろす／不採用：前の版・非採用へ／直す：採否を「直し」にし、メモを残す（作り直しの依頼は段階2が受け持つ）"""
    rows = json.load(open(a.json, encoding="utf-8"))
    done, failed = [], []
    for d in rows:
        gid, name, j, where = d["組のID"], d["名前"], d["判定"], d.get("一覧")
        try:
            owner, lib, D, root, key, g = find(next(iter(CHARS)), gid, where)
            char = g.get("キャラ") or ("common" if key.startswith("Claude Code") else next(iter(CHARS)))
            if j == "不採用":
                reject(gid, name, d.get("メモ", ""), where)
            else:
                st = {"採用": "採用", "仮置き": "仮置き", "直す": "直し"}[j]
                names = [name] + [x["名前"] for x in g["素材"] if x["名前"] == name + "_斜め"]
                for n in names:
                    decide(argparse.Namespace(char=char, gid=gid, name=n, state=st, 本人=d.get("本人") or d.get("メモ") or None, 決定=d.get("決定"), where=where))
                if st != "直し":
                    kind = next(x["種類"] for x in g["素材"] if name == "*" or x["名前"] == name)
                    promote(argparse.Namespace(char=char, gid=gid, name=name, kind=kind, 組=d.get("組", "要望素材から" if kind == "アイコン" else ""), 時期=d.get("時期"), where=where))
            done.append(f"{gid} {name}：{j}")
        except (SystemExit, Exception) as e:   # 1件が止まっても、ほかの件は続ける
            failed.append(f"{gid} {name}：{j} → 止まった：{e}")
    print("当てた", len(done)); [print(" ", x) for x in done]
    if failed: print("止まった", len(failed)); [print(" ", x) for x in failed]

def lst(a):
    for owner, key in (("common", "保留"), (a.char, "要望素材")):
        lib, drv, D = paths(owner)
        gs = [g for g in D.get(key, []) if owner != "common" or g.get("キャラ", a.char) == a.char]
        print(f"■ {key}（{len(gs)}組）")
        for g in gs:
            print(g["id"], g["依頼"], g["出どころ"], g["届いた日"])
            for x in g["素材"]: print("  ", x["状態"], x["種類"], x["名前"], x["ファイル"])

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
p = sp.add_parser("receive"); p.add_argument("char"); p.add_argument("memo"); p.add_argument("--依頼", required=True); p.add_argument("--出どころ", required=True); p.add_argument("--原文"); p.add_argument("--依頼のID"); p.add_argument("--先", choices=["保留", "要望素材", "Claude Codeキャラの要望素材"], default="保留"); p.add_argument("--受付")
p = sp.add_parser("request"); p.add_argument("char"); p.add_argument("--種類", required=True); p.add_argument("--依頼", required=True); p.add_argument("--中身", required=True); p.add_argument("--原文"); p.add_argument("--出どころ"); p.add_argument("--作業ID"); p.add_argument("--条件"); p.add_argument("--キャラなし", action="store_true")   # 11/19 キャラの出ない素材（キャラ情報とリファレンスを入れない）
p = sp.add_parser("decide"); p.add_argument("char"); p.add_argument("gid"); p.add_argument("name"); p.add_argument("state"); p.add_argument("--本人"); p.add_argument("--決定"); p.add_argument("--一覧", dest="where")
p = sp.add_parser("promote"); p.add_argument("char"); p.add_argument("gid"); p.add_argument("name"); p.add_argument("kind"); p.add_argument("--組", default=""); p.add_argument("--時期"); p.add_argument("--一覧", dest="where")
p = sp.add_parser("list"); p.add_argument("char")
p = sp.add_parser("apply"); p.add_argument("json")   # 11/20 採否を決めるページの答えを当てる
a = ap.parse_args()
{"request": request, "receive": receive, "decide": decide, "promote": promote, "list": lst, "apply": apply_decisions}[a.cmd](a)
