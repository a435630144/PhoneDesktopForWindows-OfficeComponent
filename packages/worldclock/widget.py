# -*- coding: utf-8 -*-
"""世界时钟（组件商店示例组件，v1.0.0）。

只依赖宿主 SDK（`deskorg`），不 import 主程序内部模块——这是商店组件
能独立升级的前提：主程序改内部结构不该让已上架的组件全废。

绘制约定（与 `docs/组件开发指南.md` 一致）：
  - 所有尺寸按容器比例算，2×2 / 4×2 / 2×4 都成立；
  - 颜色只用 `style` 里用户配好的值（text / dim / faint / accent），
    不写死主题色，否则「组件设置 ▸ 外观」对这个组件就无效；
  - 绘制抽成 `draw_content()`，组件库预览与桌面共用同一份。
"""
from PySide6.QtCore import QDateTime, QRectF, Qt, QTimer
from PySide6.QtGui import QColor

from deskorg import theme
from deskorg.widget_glass import GlassWidget


def _settings(entry) -> dict:
    return (entry or {}).get("settings") or {}


def _lines(settings: dict):
    """(标题, 时间字符串, 日期字符串)。"""
    off = 0
    try:
        off = int(settings.get("offset", 0))
    except (TypeError, ValueError):
        off = 0
    now = QDateTime.currentDateTimeUtc().addSecs(off * 3600)
    return (str(settings.get("title") or ""),
            now.toString("HH:mm"),
            now.toString("M月d日 ddd"))


def draw_content(painter, rect, settings, style):
    r = QRectF(rect)
    if r.width() <= 8 or r.height() <= 8:
        return
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
    title, hhmm, date = _lines(settings)
    pad = max(12.0, min(r.width(), r.height()) * 0.09)

    # 强调色竖条（用户强调色，不写死）
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(style.accent))
    bar_w = max(3.0, r.width() * 0.02)
    painter.drawRoundedRect(QRectF(r.left() + pad, r.top() + pad,
                                   bar_w, r.height() - pad * 2), bar_w / 2, bar_w / 2)

    left = r.left() + pad + bar_w + pad * 0.7
    avail_w = max(10.0, r.right() - pad - left)

    painter.setPen(QColor(style.dim))
    painter.setFont(theme.ui_font(max(9, int(min(r.height() * 0.09, 12)))))
    painter.drawText(QRectF(left, r.top() + pad, avail_w, r.height() * 0.18),
                     Qt.AlignLeft | Qt.AlignVCenter, title)

    fs = max(18, int(min(r.height() * 0.34, r.width() * 0.22)))
    painter.setPen(QColor(style.text))
    painter.setFont(theme.ui_font(fs, bold=True))
    painter.drawText(QRectF(left, r.top() + r.height() * 0.26, avail_w, fs * 1.25),
                     Qt.AlignLeft | Qt.AlignVCenter, hhmm)

    if bool(settings.get("date", True)):
        painter.setPen(QColor(style.faint))
        painter.setFont(theme.ui_font(max(9, int(min(r.height() * 0.085, 12)))))
        painter.drawText(QRectF(left, r.bottom() - pad - r.height() * 0.20,
                                avail_w, r.height() * 0.18),
                         Qt.AlignLeft | Qt.AlignVCenter, date)


def draw_preview(painter, rect, dpr=1.0):
    """组件库缩略图：同一个 `draw_content()`，只是喂一份默认设置。"""
    from deskorg.widget_style import DEFAULT_STYLE
    from deskorg.widget_glass import paint_glass
    r = QRectF(rect)
    paint_glass(painter, r, 14.0)
    inner = r.adjusted(10, 10, -10, -10)
    draw_content(painter, inner, {"title": "伦敦", "offset": 0, "date": True},
                 DEFAULT_STYLE)


class WorldClockWidget(GlassWidget):
    """世界时钟组件（每 10 秒重绘一次——分钟精度，不需要 1 秒一跳）。"""

    TYPE = "worldclock"

    def __init__(self, storage, entry):
        super().__init__(storage, entry)
        self._timer = QTimer(self)
        self._timer.setInterval(10_000)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def paint_content(self, painter):
        draw_content(painter, self.card_rect(), _settings(self.entry), self.style)

    def on_settings_changed(self):
        super().on_settings_changed()
        self.update()

    def closeEvent(self, e):
        timer = getattr(self, "_timer", None)
        if timer is not None:
            timer.stop()
        super().closeEvent(e)
