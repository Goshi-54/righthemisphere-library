# 素材ライブラリの上の階層（キャラの一覧・メタ環境・制作レシピ・作業ログ）を組む
# 11/14 本人「素材ライブラリはもう一つ上の階層を作る／そこに各キャラクター配置していく／キャラクター用のメタ情報もここで管理（リファレンスシートとかも）」
# 11/13 本人「等身大とマイクラはリファレンスシートはライブラリに載せなくていい」→ リファレンスシートは素材のタブではなく、ここ（上の階層・メタ環境）に置く
# 11/27-28 本人：確定正本格納庫（Vtuber v5 26枚・ミニキャラ v5 61枚・マイクラ v8 66枚・Claudeステッカー Master5点+全16ポーズ）、
#   作り方・システム要件・判断軸、Chatwork自動生成対応状況、着手前リサーチ・分解3項目ゲート、横断作業ログを上階層で見える化する
import os, json, shutil, re

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(HERE, ".."))
META_ROOT = os.path.join(CODE_ROOT, "systems", "library", "メタ環境")

# ---------- キャラの一覧（上の階層で管理するキャラ・ステッカー系統）----------
CHARS = [{
    "id": "depure",
    "lib": os.path.join(CODE_ROOT, "work", "sns", "instagram", "でぷれさん素材ライブラリ"),
    "名前": "でぷれさん",
    "出どころ": "Instagram協業の出演者（協業先のキャラ）",
    "公開": "公開中（2026-11-12〜。本人の「公開してよい」で承認）",
    "声": {
        "中身": "ElevenLabsで複製したでぷれさんの声（1回目の声）",
        "設定": ["似せる強さ 0.90・安定性 0.40", "前置き文を付けて生成し、あとで切る（B方式）", "間：段落 0.48秒・行 0.22秒", "音量：-18 LUFS にそろえる"],
        "作り方": "Skill「goshi-narration-voice」",
    },
    "直し待ち": [
        {"何": "Vtuber動画化×GIF併用ハイブリッド展開", "本人": "口パク・目・表情を中心にしつつ、手元の動き等はv5正本ベースの厳選Vtuber GIF切替と組み合わせてアスレ重畳・ワイプ等へ展開する（06_全体計画承認済）。"},
        {"何": "ミニキャラ C1-01 等 素直な5〜6コマ構成への統一", "本人": "36コマ自動補間モーフィングや0px完全固定の暴走をやめ、承認済パイロット（P03〜P05 v2）と同じ5〜6コマの自然な動き最優先で制作する。"},
    ],
}]

# ---------- 棚（キャラに紐づかないもの：既存2棚を完全維持）----------
SHELVES = [{
    "棚": "編集",
    "名前": "編集の名前帳",
    "説明": "テロップ・動き・切り替え・エフェクト・色の名前に番号（E01-01 など）を付けた一覧。9タブ・153項目。",
    "注意": ["非公開のページです。開けるのは共有された人だけです。", "見本の見た目は確認前の試作です。"],
    "リンク": None,  # filled from previous characters.json if present
}, {
    "棚": "動画生成",
    "名前": "生成素材の調整ツール",
    "説明": "生成した動画や画像を開き、明るさや質感をスライダーで動かして、元と並べて見る道具。決めた設定は、書き出し用のスクリプトで動画全体にかけられる（30fps化も選べる）。",
    "注意": ["開いたファイルはこのブラウザの中だけで使い、どこにも送りません。"],
    "リンク": "adjust/",
    "ボタン": "調整ツールを開く",
    "外部": False,
}]

# Preserve exact external link for 編集の名前帳 from existing data/characters.json
prev_chars_json = os.path.join(HERE, "data", "characters.json")
if os.path.isfile(prev_chars_json):
    try:
        prev_d = json.load(open(prev_chars_json, encoding="utf-8"))
        for sh in prev_d.get("棚", []):
            if sh.get("名前") == "編集の名前帳" and sh.get("リンク"):
                SHELVES[0]["リンク"] = sh["リンク"]
    except Exception:
        pass

COMMON = {"id": "common", "lib": os.path.join(CODE_ROOT, "work", "sns", "instagram", "共通素材ライブラリ")}

# Drive folder IDs (resolved using same prefix as D["キャラ"]["ドライブ"])
META_IDS = {
    "root": "1ljAiln6FzNJMV0f6FgKHu9jVSlefKxDA",
    "vtuber": "19aTHMQJReF19rXepjZvB_2Ujfv0d5BAi",
    "minichara": "19klI0cUA3EIHWHtPmGTLO4amMd9M4Uoe",
    "minecraft": "1IVrYdhSgKgmSJNQBzuiFQOf7O__r4T4f",
    "yt_rec": "1vJWjn5UdwyGdzZQrzMw_s8HIdxI8KBb5",
    "sticker": "1ciG-ASRfZs0HX-PyaILE1emkH8mBtyRQ",
    "img_boost": "1KsVALfpWNMG8LH0IcDvZ4c5tHBN_iSMJ",
}
EDITOR_IDS = {
    "root": "1LzKpR0tWz4JgIxCRhKIpbGXE9pQjK11J",
    "depure_root": "1hTbeo7D78qSA-xcqhe_Unfukd7Kppz5Y",
    "minichara": "1U78OxQfpOzBszHPl3_CXxnv9AM1PSFML",
    "vtuber": "1k2apz-r2qCkVLZmUry0kn9f31x95YwOh",
    "yt_rec": "1zj1U58tQfblO9PWL7IaMSEqQl9t5IGW3",
    "common_root": "1XGb0ErAl6te_XqjaiOipMSc_VmfTSVIY",
    "img_boost": "1fYhS-OTfRbxciF2e0Cw3uQb9In3iFXQ4",
    "sticker": "112wA_Zbov-7Xy1ZfUwBdtIVSWL3QpxrJ",
}

# Extract sheet URL from meta-library-top HTML if available
SHEET_URL = ""
meta_html_p = os.path.join(CODE_ROOT, "ai-company", "docs", "meta-library-top-20261127.html")
if os.path.isfile(meta_html_p):
    m_sh = re.search(r'href="([^"]*1aMagbFv4_615XRbPUcYS1tsEbtsrKQbyooWNXyP_-cQ[^"]*)"', open(meta_html_p, encoding="utf-8").read())
    if m_sh:
        SHEET_URL = m_sh.group(1)

MC_NAMES = {
    "01": "01 正面", "02": "02 左斜め前", "03": "03 右斜め前", "04": "04 左真横",
    "05": "05 右真横", "06": "06 左斜め後ろ", "07": "07 右斜め後ろ", "08": "08 背面",
    "p07": "P07 笑顔・口開け", "p08": "P08 頭部パーツ",
    "09_01": "09_01 表情（驚き）", "09_02": "09_02 表情（困り・考え中）", "09_03": "09_03 表情（ニッコリ）",
    "10": "10 グレーブロック持ち", "11": "11 Mac風シルバーPC作業", "11a": "11A Mac風シルバーPC作業",
    "12_03": "12_03 基本小物セット", "13_01": "13_01 歩幅01（正面）", "13_02": "13_02 歩幅02（左斜め前）",
    "14_01": "14_01 歩幅01（正面）", "14_02": "14_02 歩幅02（左斜め前）",
    "14a": "14A 白ブロック（n）", "14b": "14B 白本（n）", "15": "15 白本（n）持ち",
    "15a": "15A 白ブロック（n）", "15b": "15B 白本（n）", "16": "16 白本（n）持ち",
    "16a": "16A Geminiブロック", "16b": "16B Xブロック", "16c": "16C Instagramブロック",
    "16d": "16D Threadsブロック", "16e": "16E Claudeブロック", "16f": "16F ChatGPT白ブロック", "16g": "16G 青AIブロック",
    "17_pc": "17 Mac風シルバーPC単体",
    "17a": "17A Geminiブロック", "17b": "17B Xブロック", "17c": "17C Instagramブロック",
    "17d": "17D Threadsブロック", "17e": "17E Claudeブロック", "17f": "17F ChatGPT白ブロック", "17g": "17G 青AIブロック",
    "18_pc": "18 Mac風シルバーPC単体",
    "18a_cat": "18A 相棒猫（立ち）", "18b_cat": "18B 相棒猫（お座り）",
    "19a_cat": "19A 猫01", "19b_cat": "19B 猫02", "19c_cat": "19C 猫03",
    "20a_cat": "20A 茶トラ猫", "20b_cat": "20B 三毛猫", "20c_cat": "20C シャム猫",
}

def copy_meta_refs(subdir, src_folder, exts=(".png", ".svg")):
    dst_dir = os.path.join(HERE, "media", "meta_refs", subdir)
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(dst_dir, exist_ok=True)
    out = []
    if not os.path.isdir(src_folder):
        return out
    for fn in sorted(os.listdir(src_folder)):
        if fn.endswith(exts) and not fn.endswith(("_f1.png", "_f2.png", "_f3.png", "_animated.png")):
            shutil.copy2(os.path.join(src_folder, fn), os.path.join(dst_dir, fn))
            out.append((fn, f"media/meta_refs/{subdir}/{fn}"))
    return out

out_chars = []
DRV_PREFIX = ""

for c in CHARS:
    D = json.load(open(os.path.join(c["lib"], "data", "library.json"), encoding="utf-8"))
    DRV_PREFIX = D["キャラ"]["ドライブ"].rsplit("/", 1)[0] + "/"
    drv = lambda fid: DRV_PREFIX + fid

    pub = os.path.join(c["lib"], "公開用")
    dst = os.path.join(HERE, c["id"])
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(pub, dst, ignore=shutil.ignore_patterns(".git", ".DS_Store"))

    # Legacy 11/12-11/13 refs (kept intact in media/depure/ so 0 files disappear)
    os.makedirs(os.path.join(HERE, "media", c["id"]), exist_ok=True)
    def take(src):
        name = src.replace("/", "_")
        shutil.copyfile(os.path.join(c["lib"], src), os.path.join(HERE, "media", c["id"], name))
        return f"media/{c['id']}/{name}"
    adopted = {"基準_正面顔.jpg": "採用（本人「こちらベースで」）"}
    legacy_refs = [
        {"画風": "旧控え：ミニキャラ初期参照（11/12・5枚）", "ドライブ": D["キャラ"]["ドライブ"], "説明": "11/12公開当初の参照シート控え（現在は上の確定正本 v5 全61枚を使用）",
         "画像": [{"名前": x["label"], "src": take(x["src"]), "状態": "旧控え"} for x in D["キャラ"]["参照シート"]]},
        {"画風": "旧控え：Vtuber初期仮置き（11/13・16枚）", "ドライブ": D["等身大のドライブ"], "説明": "11/12〜13試作時の控え（現在は上の確定正本 v5 全26枚を使用）",
         "画像": [{"名前": x["名前"], "src": take(x["src"]), "状態": adopted.get(x["ファイル"], "旧控え")} for x in D["等身大"]["静止画"]]},
        {"画風": "旧控え：マイクラ初期仮置き（11/13・10枚）", "ドライブ": D["マイクラのドライブ"], "説明": "初期試作時の控え（現在は上の確定正本 v8 全66枚を使用）",
         "画像": [{"名前": x["名前"], "src": take(x["src"]), "状態": "旧控え"} for x in D["マイクラ"]["静止画"]]},
    ]

    # Confirmed Meta-Environment Reference Sheets
    vt_files = copy_meta_refs("vtuber", os.path.join(META_ROOT, "でぷれさん_Vtuber", "01_確定リファレンス"), (".png",))
    mini_files = copy_meta_refs("minichara", os.path.join(META_ROOT, "でぷれさん_ミニキャラ", "01_確定リファレンス"), (".png",))
    mc_files = copy_meta_refs("minecraft", os.path.join(META_ROOT, "でぷれさん_マイクラ", "01_確定リファレンス"), (".png",))

    mc_a = [(fn, src) for fn, src in mc_files if fn.startswith("a_")]
    mc_b = [(fn, src) for fn, src in mc_files if fn.startswith("b_")]
    def clean_label(fn):
        s = os.path.splitext(fn)[0]
        s = re.sub(r"_透過$", "", s)
        return s

    def mc_label(prefix, fn):
        key = os.path.splitext(fn)[0][2:]
        if prefix == "A" and key in ("19a_cat", "19b_cat"):
            return "19A 相棒猫（立ち）" if key == "19a_cat" else "19B 相棒猫（お座り）"
        return f"{prefix}版 " + MC_NAMES.get(key, key)

    refs = [
        {
            "画風": f"Vtuber 確定正本 v5（全{len(vt_files)}枚）",
            "ドライブ": drv(META_IDS["vtuber"]),
            "編集者ドライブ": drv(EDITOR_IDS["vtuber"]),
            "説明": "2026-11-27 本人最終OK確定。新規ポーズ・表情生成時は組シート丸投げを禁止し、構図に対応する単体透過PNGを個別添付する。",
            "画像": [{"名前": clean_label(fn), "src": src, "状態": "採用・正本確定"} for fn, src in vt_files],
        },
        {
            "画風": f"ミニキャラ 確定正本 v5（全{len(mini_files)}枚）",
            "ドライブ": drv(META_IDS["minichara"]),
            "編集者ドライブ": drv(EDITOR_IDS["minichara"]),
            "説明": "2026-11-25 本人最終OK確定（全身8面・表情・ポーズ・顔アップ・ハーフリム眼鏡統一）。Chatwork自動生成の基準正本。",
            "画像": [{"名前": clean_label(fn), "src": src, "状態": "採用・正本確定"} for fn, src in mini_files],
        },
        {
            "画風": f"マイクラ 確定正本 v8 — A版（でぷれ寄せ立体ボクセル・{len(mc_a)}枚）",
            "ドライブ": drv(META_IDS["minecraft"]),
            "編集者ドライブ": drv(EDITOR_IDS["depure_root"]),
            "説明": "2026-11-27 v8確定正本（主軸：四角寄り頭部＋控えめトップ跳ね毛・直線1ブロック腕・PC作業・SNS/AIブロック・相棒猫）。編集者ページには載せずメタ環境で管理。",
            "画像": [{"名前": mc_label("A", fn), "src": src, "状態": "採用・v8確定"} for fn, src in mc_a],
        },
        {
            "画風": f"マイクラ 確定正本 v8 — B版（マイクラ寄せ純正8bitドット・{len(mc_b)}枚）",
            "ドライブ": drv(META_IDS["minecraft"]),
            "編集者ドライブ": drv(EDITOR_IDS["depure_root"]),
            "説明": "2026-11-27 v8確定正本（表現幅用：純正8bitドット統一33枚）。",
            "画像": [{"名前": mc_label("B", fn), "src": src, "状態": "採用・v8確定"} for fn, src in mc_b],
        },
    ]

    recipes = [
        {
            "系統": "ミニキャラ（v5確定・61枚）",
            "chatwork": "対応済",
            "chatwork_state": "ok",
            "編集者ドライブ": drv(EDITOR_IDS["minichara"]),
            "メタドライブ": drv(META_IDS["minichara"]),
            "要件": "承認済パイロット（P03〜P05 v2）と同じ5〜6コマ素直なコマアニメ構造（例：300/230/270/400/420/280ms）＋口パク固定ベース（c20261120-19/run.log）。",
            "判断軸": "動画素材としての自然な動きと腕のつながりを最優先。36F自動中割りモーフィング補間は気持ち悪くなるため厳禁・0px完全固定の数値暴走も禁止。ハーフリム眼鏡統一。",
        },
        {
            "系統": "Vtuber（v5確定・26枚）",
            "chatwork": "リファレンス確定・自動生成未接続",
            "chatwork_state": "wait",
            "編集者ドライブ": drv(EDITOR_IDS["vtuber"]),
            "メタドライブ": drv(META_IDS["vtuber"]),
            "要件": "01_確定リファレンス内の対応する単体透過PNG（1カット1ファイル）を必ず個別添付。A層（R&D-2 口パク・目・表情特化）× B層（v5正本ベース厳選Vtuber GIF切替）のハイブリッド運用（アスレ重畳・小窓ワイプ・メイン語り対応）。",
            "判断軸": "インナー実測色 #4C4CA6〜#5357AA（V≈60%）、シルバー眼鏡チェーン耳後ろ1ループ、向かって右のみ軽シャツイン＆背面両裾アウト、背面襟足 y=467..472（立ち襟オーバーラップ・うなじ露出ゼロ）、素爪・指リングなし、不自然な手元後乗せ禁止。",
        },
        {
            "系統": "マイクラ（v8確定・66枚：A版33＋B版33）",
            "chatwork": "リファレンス確定・自動生成未接続",
            "chatwork_state": "wait",
            "編集者ドライブ": drv(EDITOR_IDS["depure_root"]),
            "メタドライブ": drv(META_IDS["minecraft"]),
            "要件": "A版（立体ボクセル主軸33枚）＋B版（8bitドット33枚）の確定単体PNGを参照してコマ展開（左右斜め2アングル対応）。",
            "判断軸": "肘を曲げない直線1ブロック腕（肩回転のみ）、自然なPC対面構図（a_11 / b_11a 基準）、逆アングル展開時のブロックロゴ・文字反転防止を徹底。",
        },
        {
            "系統": "YouTube収録素材（57件：PNG47＋note2＋MOV8）",
            "chatwork": "収録・切り出し系（自動生成対象外）",
            "chatwork_state": "na",
            "編集者ドライブ": drv(EDITOR_IDS["yt_rec"]),
            "メタドライブ": drv(META_IDS["yt_rec"]),
            "要件": "元YouTube収録 .mp4 を直接確認して切り出し（build_clean_edit_assets.sh）。静止画47件＋公式note注意書き2件は角丸RGBA透過PNG、主要実演8本はWeb確認用MP4＋編集投入用 Apple ProRes 4444 透過 .mov のペア格納。",
            "判断軸": "文字情報だけで切り出さず必ず実動画フレームを確認。角丸外の白残りゼロ・ProRes 4444 アルファチャンネル実透過を確認してから格納。",
        },
    ]

    counts = [["口パク", len(D["口パク"])], ["全身の動き", len(D["全身"])], ["掛け合い", len(D["掛け合い"])],
              ["Vtuber（仮置き）", len(D["等身大"]["動作"])], ["マイクラ（仮置き）", len(D["マイクラ"]["動作"])],
              ["保留", sum(len(g["素材"]) for g in D.get("保留", []))]] + ([["収録素材", len(D["収録素材"])]] if D.get("収録素材") else []) + [["台本", len(D["台本"])]]
    H = json.load(open(os.path.join(c["lib"], "data", "history.json"), encoding="utf-8"))
    hist = [{k: h[k] for k in ("日時", "種類", "中身", "状態", "本人") if h.get(k)} for h in reversed(H)]
    frames = [dict(f, src=f"{c['id']}/{f['src']}") for f in D["口パク"][0]["向き"]["正面"]]
    out_chars.append({k: v for k, v in c.items() if k != "lib"} | {
        "ライブラリ": f"{c['id']}/",
        "ドライブ": D["キャラ"]["ドライブ"],
        "メタドライブ": drv(META_IDS["root"]),
        "画風": "ミニキャラ（v5確定61枚）・Vtuber（v5確定26枚）・マイクラ（v8確定66枚）・収録素材（57件）",
        "chatwork要約": "ミニキャラ：Chatwork自動生成対応済 ／ Vtuber・マイクラ：リファレンス確定（自動生成未接続）",
        "見本": frames,
        "件数": counts,
        "制作レシピ": recipes,
        "リファレンス": refs,
        "旧リファレンス": legacy_refs,
        "履歴": hist,
    })

# 共通素材：公開用の一式を common/ に写す
CD = json.load(open(os.path.join(COMMON["lib"], "data", "library.json"), encoding="utf-8"))
dst = os.path.join(HERE, COMMON["id"])
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(os.path.join(COMMON["lib"], "公開用"), dst, ignore=shutil.ignore_patterns(".git", ".DS_Store"))

drv = lambda fid: DRV_PREFIX + fid

# 2つ目のキャラクター／メタ環境カード：Claude Code_ステッカー（2Dドット cc-v4 とは完全別枠）
st_masters = copy_meta_refs("sticker_master", os.path.join(META_ROOT, "Claude Code_ステッカー", "01_確定リファレンス"), (".svg",))
st_masters = [(fn, src) for fn, src in st_masters if fn.startswith("master_")]
MASTER_LABELS = {
    "master_01_claude_square_1024.svg": "Master 01｜主役Claude（#DC6847・内2脚#B85238・E1目#111111・4本脚・白縁）",
    "master_02_chatgpt_square_1024.svg": "Master 02｜相棒ChatGPT白（#F3F5F8・7°ハの字脚・黒6弁ロゴ）",
    "master_03_codex_square_1024.svg": "Master 03｜相棒Codex青（#3D70FF・胸 >_ 記号）",
    "master_04_claude_multiview_sheet.svg": "Master 04｜Claude多面・比率基準シート",
    "master_05_claude_expressions_sheet.svg": "Master 05｜表情基準シート（E1〜E4固定）",
}
sticker_list = CD.get("Claude Code_ステッカー", [])
out_chars.append({
    "id": "sticker_claude",
    "名前": "Claude Code_ステッカー",
    "出どころ": "IGイメージ強化・AI訴求用 白フチダイカットステッカー系統（2Dドット絵 cc-v4 / p01 とは完全別口管理）",
    "公開": "公開中（2026-11-28 全16ポーズ P01〜P16 本人目視OK確定・共通素材の別棚へ登録）",
    "ライブラリ": "common/#ccsticker",
    "ボタン名": "ステッカー棚を開く",
    "ドライブ": drv(EDITOR_IDS["sticker"]),
    "メタドライブ": drv(META_IDS["sticker"]),
    "画風": "Master v1 正本5資産 ＋ 全16ポーズ確定（32-bit透過APNG・静止画PNG・SVG）",
    "chatwork要約": "Chatwork自動生成：リファレンス確定・自動生成未接続（CodexでStickerBuilder直接実行可）",
    "見本": [{"src": f"common/{sticker_list[0]['src']}", "ms": 3000}] if sticker_list else [],
    "件数": [["Claude Code_ステッカー", len(sticker_list)]],
    "件数リンク先": "common/#ccsticker",
    "制作レシピ": [{
        "系統": "Claude Code_ステッカー（Master v1 ＋ P01〜P16）",
        "chatwork": "リファレンス確定・自動生成未接続（Codex直接制作可）",
        "chatwork_state": "wait",
        "編集者ドライブ": drv(EDITOR_IDS["sticker"]),
        "メタドライブ": drv(META_IDS["sticker"]),
        "要件": "Python（cv2＋numpy）の StickerBuilder で Master v1 座標をプログラム固定し、SS=2（2倍スーパーサンプリング）＋ border_radius=34px 純白ダイカット縁取りで描画。APNGは標準 struct＋zlib で 320ms×3コマ（f1〜f3）無限ループ出力（generate_pilot_poses / solo_batch_a / pair_batch_b / batch_c / batch_d / build_apng_loops.py）。",
        "判断軸": "①全身画像生成ガチャ禁止（Master座標固定） ／ ②物理整合（P04ゲームパッド面・P13 PC画面はキャラ向き、P07手つなぎは奥の手が少し下に覗く交差握り） ／ ③目・四角い耳・黒6弁ロゴを絶対に潰さない（両手挙げP12/P16は腕を必ず四角い耳の下から生やす・勝手な口/眉/白ハイライト禁止・緑色ロゴ不使用） ／ ④不要な黄色3本線（キラッ）は静止画・APNGとも付けない ／ ⑤原寸＆3背景検品必須・旧版退避（2Dドット cc-v4 との混在厳禁）。",
    }],
    "リファレンス": [
        {
            "画風": f"Master v1 正本（{len(st_masters)}資産：色・骨格・表情E1〜E4固定基準）",
            "ドライブ": drv(META_IDS["sticker"]),
            "編集者ドライブ": drv(EDITOR_IDS["sticker"]),
            "説明": "すべてのポーズ生成で座標固定参照するベクター正本。Claude(#DC6847)・ChatGPT白(#F3F5F8)・Codex青(#3D70FF)。",
            "画像": [{"名前": MASTER_LABELS.get(fn, fn), "src": src, "状態": "Master v1 正本"} for fn, src in st_masters],
        },
        {
            "画風": f"確定ポーズ 全{len(sticker_list)}種（P01〜P16・32-bit透過APNGループ）",
            "ドライブ": drv(META_IDS["sticker"]),
            "編集者ドライブ": drv(EDITOR_IDS["sticker"]),
            "説明": "2026-11-28 本人目視OKロック済みの全16ポーズ。編集者向けDL棚（common/#ccsticker）とは分離して正本一覧として保持。",
            "画像": [{"名前": x["名前"], "src": f"common/{x['src']}", "状態": "採用・ロック済"} for x in sticker_list],
        },
    ],
    "直し待ち": [],
    "履歴": [
        {"日時": "2026-11-28 02:33", "種類": "全16ポーズ確定・登録", "中身": "P01〜P16全16ポーズ＋Master v1正本5資産を確定し、5大判断軸・APNGレシピをメタ環境へ格納、共通素材別棚（#ccsticker）へ公開", "状態": "採用"},
        {"日時": "2026-11-27 15:47", "種類": "P07・P08確定", "中身": "P07交差握り化・P07/P08の不要な黄色3本線削除を反映して確定ロック", "状態": "採用"},
    ],
})

common_recipes = [
    {
        "系統": "IGイメージ強化UI（全22本：U01〜U21＋U20枠のみ）",
        "chatwork": "収録・UI録画系（自動生成対象外）",
        "chatwork_state": "na",
        "編集者ドライブ": drv(EDITOR_IDS["img_boost"]),
        "メタドライブ": drv(META_IDS["img_boost"]),
        "要件": "参考リール .mp4 を直接確認して設計した実動スタジオHTML（common/studio/）から、Playwright omit_background=True でRGBA連番キャプチャ → 背景完全透過GIF89a（Web主表示・主DL）＋ Apple ProRes 4444 透過 .mov 出力。",
        "判断軸": "緑バック（クロマキー）MP4のまま放置せず必ず実透過GIF/MOVで納品する。市松・暗背景・明背景の3背景で白フチ欠けや文字潰れがないか検品し、IGセーフゾーン（上14%・下21%・右17%）干渉を回避する。",
    },
    {
        "系統": "Claude Codeキャラ（2Dドット絵・cc-v4 / p01・正式49点）",
        "chatwork": "対応済",
        "chatwork_state": "ok",
        "編集者ドライブ": CD.get("アイコンのドライブ", CD["ドライブ"]),
        "メタドライブ": drv(META_IDS["root"]),
        "要件": "p01基準の原寸ピクセルアート＆役割別スーツ差分（cc-v4）。Chatwork要望素材（種類なし受付）から自動生成・比較表示に対応。",
        "判断軸": "白フチダイカットの「Claude Code_ステッカー」系統とは完全に別物として分離管理する（混在厳禁）。",
    },
    {
        "系統": "マイクラ アスレ背景動画生成パック（第1弾・7枚＋プロンプト）",
        "chatwork": "リファレンス・プロンプト提供型",
        "chatwork_state": "wait",
        "編集者ドライブ": CD.get("背景のドライブ", CD["ドライブ"]),
        "メタドライブ": drv(META_IDS["root"]),
        "要件": "common/#bg にキーフレームPNG 7枚と Runway / Topview 用の英語・日本語プロンプトおよび全6区間（00〜60秒）マップを格納。",
        "判断軸": "1カットごとのリファレンスPNGを添付し、区間マップどおりのカメラ進行で生成する。",
    },
]

common = {
    "名前": CD["ページ名"],
    "ページ": f"{COMMON['id']}/",
    "ドライブ": CD["ドライブ"],
    "メタドライブ": drv(META_IDS["img_boost"]),
    "件数": [["背景", len(CD["背景"])], ["アイコン", len(CD["アイコン"])], ["イメージ強化", len(CD["イメージ強化"])]]
            + ([["Claude Codeキャラ", len(CD["Claude Codeキャラ"]) + sum(len(g["素材"]) for g in CD.get("Claude Codeキャラの要望素材", []))]] if CD.get("Claude Codeキャラ") else [])
            + ([["Claude Code_ステッカー", len(CD["Claude Code_ステッカー"])]] if CD.get("Claude Code_ステッカー") else []),
    "見本": [f"{COMMON['id']}/{x['src']}" for x in CD["アイコン"][:6]],
    "制作レシピ": common_recipes,
}

hold_items = [x for g in CD.get("保留", []) for x in g.get("素材", [])]
hold_chars = sorted({g.get("キャラ名", "") for g in CD.get("保留", []) if g.get("キャラ名")})
hold = {
    "名前": "保留",
    "説明": "ゴーシさんが作って、まだ採否を決めていない素材" + (f"（今は{'・'.join(hold_chars)}の物）" if hold_chars else "") + "。採否を決めたものは、そのキャラのページの種類のタブに移す。採否を待つ間も、種類のタブの最後に「未採用」の印で出している。",
    "組": len(CD.get("保留", [])),
    "点": len(hold_items),
    "ページ": f"{COMMON['id']}/#hold",
    "ドライブ": CD.get("保留のドライブ", ""),
    "見本": [f"{COMMON['id']}/{x['src']}" for x in hold_items if not x["src"].lower().endswith((".mp4", ".mov"))][:6],
}

# 横断メタ環境情報（ドライブ格納庫・着手前3項目ゲート・横断作業ログ）
worklogs = []
tsv_path = os.path.join(META_ROOT, "00_作業ログ_素材制作・改修台帳.tsv")
if os.path.isfile(tsv_path):
    lines = [l for l in open(tsv_path, encoding="utf-8").read().splitlines() if l.strip()]
    for row in reversed(lines[1:]):
        cols = row.split("\t")
        if len(cols) >= 7:
            # Support both 7-col and 9-col rows cleanly, sanitizing local absolute paths
            sanitize = lambda s: re.sub(r"/Users/[^/\s]+/Code/", "", s)
            if len(cols) >= 9:
                worklogs.append({
                    "日時": cols[0], "ID": cols[1], "対象": cols[2], "種別": cols[3],
                    "担当": cols[4], "内容": sanitize(f"参照: {cols[5]} ／ {cols[7]}"), "状態": cols[8],
                })
            else:
                worklogs.append({
                    "日時": cols[0], "ID": cols[1], "対象": cols[2], "種別": cols[3],
                    "担当": cols[4], "内容": sanitize(cols[5]), "状態": cols[6],
                })

meta_env = {
    "編集者ドライブ": drv(EDITOR_IDS["root"]),
    "メタドライブ": drv(META_IDS["root"]),
    "作業ログシート": SHEET_URL,
    "フォルダ一覧": [
        {"名前": "でぷれさん_Vtuber（26枚）", "url": drv(META_IDS["vtuber"])},
        {"名前": "でぷれさん_ミニキャラ（61枚）", "url": drv(META_IDS["minichara"])},
        {"名前": "でぷれさん_マイクラ（66枚）", "url": drv(META_IDS["minecraft"])},
        {"名前": "でぷれさん_YouTube収録素材", "url": drv(META_IDS["yt_rec"])},
        {"名前": "Claude Code_ステッカー（Master5＋16種）", "url": drv(META_IDS["sticker"])},
        {"名前": "IGイメージ強化UI（透過22本）", "url": drv(META_IDS["img_boost"])},
    ],
    "着手前ゲート": [
        {"題": "① 一次実物の直接確認（文章だけで処理しない）", "文": "メモや文字情報だけで作業に入らず、必ず元動画（.mp4）・確定リファレンスの単体透過PNG・既存の透過GIF/APNG実物を直接開いて目で確認する。"},
        {"題": "② 過去の作り方・レシピ・判断軸の逆引き", "文": "ブラッシュアップや追加制作の前に、各画風の「作り方・システム要件・判断軸」を確認し、その素材がどのスクリプト・構造・色コードで作られたかを把握してから着手する（36F補間NG・組シート丸投げNG・緑バック放置NG）。"},
        {"題": "③ 3背景（市松・暗・明）原寸検品 ＆ 作業ログ更新", "文": "提出前に市松・暗背景・明背景の3背景と原寸拡大で透過漏れ・白フチ欠け・小物の向き・耳や目の潰れがないか検品し、旧版は削除せず退避した上で作業ログを更新する。"},
    ],
    "作業ログ": worklogs,
}

os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
json.dump(
    {"キャラ": out_chars, "保留": hold, "共通素材": common, "棚": SHELVES, "メタ環境": meta_env},
    open(os.path.join(HERE, "data", "characters.json"), "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=1,
)
print("キャラ", len(out_chars), [c["名前"] for c in out_chars], "作業ログ", len(worklogs))
