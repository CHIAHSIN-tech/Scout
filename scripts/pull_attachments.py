#!/usr/bin/env python3
"""把 Cloudflare KV 上的附件抓回本機，供離線單檔嵌入。

為什麼要抓回來：離線單檔的規矩是「不連外」（規格 A9）。附件留在 KV 上，
飛機上就打不開；所以建置前先落地成檔案，建置時再嵌成 data: URI。

PDF 在這裡就先轉成 PNG。理由有二：
  1. 手機瀏覽器對 data: 的 PDF 支援很差（iOS Safari 直接擋掉頂層導覽），
     圖片則到處都能顯示。
  2. 轉檔放在抓取階段、結果存成檔案，建置就仍然是純函式——
     同一份輸入建兩次還是位元相同（A7）。

用法：python scripts/pull_attachments.py 2026-09-kr-seoul
"""
import json, os, pathlib, re, subprocess, sys

NS = "492ce5e92c12460a9923ccf2610061af"   # ATTACHMENTS，見 wrangler.toml
ROOT = pathlib.Path(__file__).resolve().parents[1]
DIR_RE = re.compile(r"^\d{4}-\d{2}-[a-z]{2}-[a-z0-9-]+$")
PDF_DPI = 110          # 手機上看得清楚，又不會讓單檔爆掉
MAX_W = 1000           # 內嵌用的最大寬度：手機螢幕撐死 430pt，再大只是浪費頻寬
JPEG_Q = 78            # 訂位截圖與行程單在這個品質下都還讀得清楚


def wrangler(*args):
    # shell=True：Windows 上 npx 是 .cmd，沒有 shell 叫不起來
    cmd = "npx wrangler " + " ".join(args)
    # --use-system-ca：本機有 Avast 在攔 HTTPS，不用系統憑證庫會被擋成認證錯誤
    env = dict(os.environ, NODE_OPTIONS="--use-system-ca")
    p = subprocess.run(cmd, shell=True, capture_output=True, cwd=ROOT, env=env)
    if p.returncode != 0:
        sys.exit(f"wrangler 失敗：{p.stderr.decode('utf-8', 'replace')[-800:]}")
    return p.stdout


def main(slug):
    if not DIR_RE.match(slug):
        sys.exit(f"旅程資料夾名稱格式錯誤：{slug}")
    out = ROOT / "trips" / slug / "attachments"
    out.mkdir(parents=True, exist_ok=True)

    raw = wrangler("kv key list", "--namespace-id", NS, "--remote").decode("utf-8")
    keys = [k for k in json.loads(raw[raw.index("["):]) if k["name"].startswith(f"{slug}/")]
    # 依 key 排序：清單順序固定，建置結果才穩定
    keys.sort(key=lambda k: k["name"])

    index = []
    for k in keys:
        meta = k.get("metadata") or {}
        kid = k["name"].split("/", 1)[1]
        blob = out / kid
        if not blob.exists():
            # kv key get 會把二進位原樣吐到 stdout
            blob.write_bytes(wrangler("kv key get", f'"{k["name"]}"',
                                      "--namespace-id", NS, "--remote"))
        pages = [blob.name]
        if (meta.get("type") == "application/pdf") or blob.suffix.lower() == ".pdf":
            pages = rasterize(blob, out)
        pages = [shrink(out / n, out) for n in pages]
        index.append({
            "id": k["name"], "label": meta.get("label") or "",
            "name": meta.get("name") or kid, "type": meta.get("type") or "",
            "at": meta.get("at") or "", "pages": pages,
        })

    (out / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    total = sum((out / p).stat().st_size for e in index for p in e["pages"])
    print(f"{len(index)} 個附件、{sum(len(e['pages']) for e in index)} 張圖，"
          f"共 {total // 1024} KB → {out}")


def rasterize(pdf, out):
    """PDF → 每頁一張 PNG。已經轉過就不再轉（轉檔結果本身進版控）。"""
    import fitz
    names = []
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc, 1):
            png = out / f"{pdf.stem}-p{i}.png"
            if not png.exists():
                page.get_pixmap(dpi=PDF_DPI).save(png)
            names.append(png.name)
    return names


def shrink(src, out):
    """縮到手機看得清楚就好的大小，轉成 JPEG。

    為什麼要這一步：iPhone 截圖是 1179 px 寬的 PNG，一張就 450 KB；十一份附件
    原樣內嵌會讓單檔變成 6 MB，在飯店 wifi 上等於打不開。縮到 1000 px、
    JPEG 78 之後總量降到五分之一，訂位編號與時間仍然讀得清楚。

    原檔留著不動（它們在 .gitignore 裡），要重新調參數隨時可以再產一次。
    """
    from PIL import Image

    dst = out / f"{src.stem}-w.jpg"
    if dst.exists():
        return dst.name
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
    return dst.name


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sys.exit("要給旅程資料夾名稱"))
