# -*- coding: utf-8 -*-
"""组件仓库打包器：`packages/*` -> `dist/*.zip` + `index.json`。

用法：
    python tools/build.py                # 打包全部 + 刷新 index.json
    python tools/build.py countdown      # 只打一个（仍会刷新整份清单）
    python tools/build.py --check        # 只校验，不写文件（CI / 提交前）

三条规矩（与 `docs/组件开发指南.md` §7 同源）：

1. **manifest.json 在 zip 根目录**：导入器也接受"整体套一层目录"，但那依赖
   "只有一个顶层目录"，多一个空目录就会打乱；根目录最稳。
2. **只收白名单后缀**：与 `widget_plugin.ALLOWED_EXT` 完全一致——多收一个
   `.exe` 用户那边就是"打得开、装不上"。
3. **index.json 是唯一商店清单**：app 只认它列出的包名 + sha256；手改 dist
   目录而不重跑本脚本，客户端会因 sha256 不符拒绝安装（这是刻意的）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "packages"
DIST_DIR = ROOT / "dist"
INDEX = ROOT / "index.json"

# 与 widget_plugin.ALLOWED_EXT 对齐（这里复制一份而不是 import：本仓库要能
# 在没装 PySide6 的机器上独立打包）
ALLOWED_EXT = {".py", ".json", ".md", ".txt", ".png", ".jpg", ".jpeg",
               ".gif", ".svg", ".ico", ".webp"}
ID_RX = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
SCHEMA = 1


def die(msg: str) -> None:
    print("ERROR " + msg)
    sys.exit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(folder: Path) -> dict:
    path = folder / "manifest.json"
    if not path.is_file():
        die("%s 缺 manifest.json" % folder.name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:      # noqa: BLE001
        die("%s/manifest.json 不是合法 JSON：%s" % (folder.name, exc))
    if not isinstance(data, dict):
        die("%s/manifest.json 必须是对象" % folder.name)
    wid = str(data.get("id") or "").strip()
    if not ID_RX.match(wid):
        die("%s：id %r 不合法（小写字母开头，a-z 0-9 _，2~31 位）"
            % (folder.name, wid))
    if wid != folder.name:
        die("%s：目录名与 id 不一致（id=%s）——商店按 id 安装，必须同名"
            % (folder.name, wid))
    for key in ("name", "factory"):
        if not str(data.get(key) or "").strip():
            die("%s：manifest 缺 %s" % (folder.name, key))
    module = str(data.get("module") or "widget.py")
    if not (folder / module).is_file():
        die("%s：module %r 指向的文件不存在" % (folder.name, module))
    return data


def collect(folder: Path):
    """要打进 zip 的文件（跳过缓存/隐藏/多余后缀）。"""
    out = []
    for p in sorted(folder.rglob("*")):
        if p.is_dir():
            continue
        if "__pycache__" in p.parts or p.name.startswith("."):
            continue
        if p.suffix.lower() not in ALLOWED_EXT:
            print("  skip %s（后缀不在白名单）" % p.relative_to(folder))
            continue
        out.append(p)
    return out


def pack(folder: Path, manifest: dict) -> Path:
    version = str(manifest.get("version") or "0.0.0")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    target = DIST_DIR / ("%s-%s.zip" % (folder.name, version))
    files = collect(folder)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, p.relative_to(folder).as_posix())
    print("  -> %s（%d 个文件，%d 字节）"
          % (target.relative_to(ROOT), len(files), target.stat().st_size))
    return target


def build_index(folders) -> dict:
    widgets = []
    for folder in sorted(folders):
        print("[%s]" % folder.name)
        manifest = load_manifest(folder)
        zip_path = pack(folder, manifest)
        widgets.append({
            "type": manifest["id"],
            "name": str(manifest.get("name") or ""),
            "summary": str(manifest.get("summary") or ""),
            "category": str(manifest.get("category") or "其他"),
            "version": str(manifest.get("version") or "0.0.0"),
            "spans": manifest.get("spans") or [[2, 2]],
            # 必须写**仓库内完整相对路径**（含 dist/ 前缀）：客户端是
            # `base + "/" + package` 直接拼 URL 的。旧版只写文件名，
            # 于是 raw/master/countdown-1.0.0.zip 一律 404（根目录没有 zip，
            # zip 在 dist/ 下）——v10 反馈 28 实机报"gitee: HTTP Error 404"。
            "package": zip_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(zip_path),
            "size": zip_path.stat().st_size,
            "author": str(manifest.get("author") or ""),
            "min_app": str(manifest.get("min_app") or ""),
        })
    widgets.sort(key=lambda w: (w["category"], w["type"]))
    return {"schema": SCHEMA, "widgets": widgets}


def main() -> int:
    ap = argparse.ArgumentParser(description="组件仓库打包器")
    ap.add_argument("names", nargs="*", help="只打这些目录（默认全部）")
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = ap.parse_args()

    if not PKG_DIR.is_dir():
        die("找不到 packages/ 目录")
    folders = [p for p in sorted(PKG_DIR.iterdir()) if p.is_dir()]
    if args.names:
        wanted = set(args.names)
        folders = [f for f in folders if f.name in wanted]
        missing = wanted - {f.name for f in folders}
        if missing:
            die("不存在的组件目录：%s" % ", ".join(sorted(missing)))
    if not folders:
        die("packages/ 下没有组件")

    if args.check:
        for folder in folders:
            load_manifest(folder)
        print("OK：%d 个组件的 manifest 校验通过" % len(folders))
        return 0

    index = build_index(folders)
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print("\nindex.json：%d 个组件" % len(index["widgets"]))
    for w in index["widgets"]:
        print("  %-12s %-10s v%-8s %s" % (w["type"], w["name"], w["version"],
                                          w["package"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
