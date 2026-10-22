# PhoneDesktop 组件仓库（Widget Components）

主程序 **不内置** 组件商店的组件包：桌面小组件的分发走这个独立仓库。
app 里的「设置 ▸ 组件库 ▸ 组件商店」按 `index.json` 拉清单，从 `dist/` 下
载 zip 安装到用户目录（`%APPDATA%\PhoneDesktop\widgets\<id>`）。

## 双镜像是刻意的

app 侧顺序 **gitee → github → jsDelivr**（`src/widget_store.py` 的 `MIRRORS`）：

| 线路 | 地址 | 分支 |
| --- | --- | --- |
| gitee（优先） | <https://gitee.com/suibianwanwanay/phone-desktop-for-windows-office-component> | `master` |
| github（兜底） | <https://github.com/a435630144/PhoneDesktopForWindows-OfficeComponent> | `main` |
| jsDelivr（GitHub 的 CDN 镜像，第三条） | `https://cdn.jsdelivr.net/gh/a435630144/PhoneDesktopForWindows-OfficeComponent@main` | `main` |

上次成功的线路会被记进 app 的缓存，下次先问它——避免每次都在超时上白等。
**两个仓库必须同时推**，否则国内用户拉不到更新（或海外用户兜底失效）。

## 目录

```
Component/
├── index.json          # 商店清单（唯一真相；app 只认它）
├── packages/           # 组件源码（一个目录一个组件，目录名 == manifest.id）
│   ├── countdown/
│   └── worldclock/
├── dist/               # 打好的 zip（提交进 git，app 走 raw 直链下载）
└── tools/build.py      # 打包 + 算 sha256 + 重写 index.json
```

## 发布一个新版本（三步）

```bash
# 1) 改 packages/<id>/ 里的源码，并在 manifest.json 里抬 version
# 2) 打包 + 刷清单
python tools/build.py            # 或 python tools/build.py countdown
# 3) 两个远端一起推
git add -A && git commit -m "worldclock 1.1.0：支持自定义标题"
git push gitee main:master && git push github main
```

> 只提 `packages/` 而不跑 `build.py`，app 端会因 sha256 不符**拒绝安装**
> （这是刻意的：宁可装不上，也不要装一个和清单对不上的包）。

## 组件包规范

与主程序 `docs/组件开发指南.md` 完全一致，要点：

- `manifest.json` 在包**根目录**（不要套一层目录）；
- 只收 `.py .json .md .txt .png .jpg .jpeg .gif .svg .ico .webp`，其它后缀
  会让整包被 app 拒绝（安全白名单）；
- `id` 不能与内置组件同名（`clock` `notes` `panel` `monitor` `todo`
  `calendar` `weather` `music` 已被占用）；
- 组件只 import `deskorg` 命名空间（宿主 SDK），**不要** import 主程序内部
  模块——否则主程序一次内部重构就会让已上架的组件全废。

## 许可

组件源码随主程序一同发布，见仓库根 `LICENSE`。
