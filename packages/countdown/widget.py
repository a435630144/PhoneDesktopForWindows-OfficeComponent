# -*- coding: utf-8 -*-
"""倒计时（组件商店示例组件，v1.0.0）。

日期解析刻意"宽进"：接受 `YYYY-MM-DD` / `YYYY/MM/DD` / `MM-DD`（按今年），
解析不出来就显示"填个日期"而不是抛异常——组件在桌面上常驻，一个脏输入
不该让它变成一块空白卡片。

只依赖 `deskorg` SDK；绘制抽成 `draw_content()` 供预览复用。
"""
import datetime

from PySide6.QtCore import QDate, QRectF, Qt, QTimer
from PySide6.QtGui import QColor

from deskorg import theme
from deskorg.widget_glass import GlassWidget


def _settings(entry) -> dict:
    return (entry or {}).get("settings") or {}


def parse_target(text) -> datetime.date | None:
    """宽松解析目标日期；空/非法都返回 None（调用方显示提示）。"""
    s = str(text or "").strip().replace("/", "-").replace(".", "-")
    if not s:
        return None
    parts = [p for p in s.split("-") if p.strip()]
    try:
        if len(parts) == 3:
            y, m, d = (int(p) for p in parts)
        elif len(parts) == 2:
            y = datetime.date.today().year
            m, d = (int(p) for p in parts)
        else:
            return None
        return datetime.date(y, m, d)
    except (TypeError, ValueError):
        return None


def _numbers(settings: dict):
    """(标题, 数值字符串, 单位, 说明文字, 是否已过)。"""
    target = parse_target(settings.get("date"))
    title = str(settings.get("title") or "")
    if target is None:
        return title, "--", "", "填个日期", False
    today = datetime.date.today()
    delta = (target - today).days
    unit = str(settings.get("unit") or "day")
    if unit == "week":
        value, label = abs(delta) // 7, "周"
    else:
        value, label = abs(delta), "天"
    if delta > 0:
        note = "还剩"
    elif delta == 0:
        note, value = "就是今天", 0
    else:
        note = "已过"
    return title, str(value), label, note, delta < 0


def draw_content(painter, rect, settings, style):
    r = QRectF(rect)
    if r.width() <= 8 or r.height() <= 8:
        return
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
    title, value, unit, note, past = _numbers(settings)
    pad = max(12.0, min(r.width(), r.height()) * 0.09)

    painter.setPen(QColor(style.dim))
    painter.setFont(theme.ui_font(max(9, int(min(r.height() * 0.085, 12)))))
    painter.drawText(QRectF(r.left() + pad, r.top() + pad,
                            r.width() - pad * 2, r.height() * 0.16),
                     Qt.AlignLeft | Qt.AlignVCenter, title)

    # 主数字：已过用弱色，未到用强调色（一眼分辨"还剩"与"已过"）
    accent = QColor(style.faint if past else style.accent)
    fs = max(20, int(min(r.height() * 0.40, r.width() * 0.26)))
    painter.setPen(accent)
    painter.setFont(theme.ui_font(fs, bold=True))
    num_rect = QRectF(r.left() + pad, r.top() + r.height() * 0.24,
                      r.width() - pad * 2, fs * 1.2)
    painter.drawText(num_rect, Qt.AlignLeft | Qt.AlignVCenter, value)

    if unit:
        painter.setPen(QColor(style.dim))
        painter.setFont(theme.ui_font(max(10, int(fs * 0.42))))
        painter.drawText(QRectF(num_rect.left() + painter.fontMetrics()
                                .horizontalAdvance(value) + 6,
                                num_rect.top(), 60, num_rect.height()),
                         Qt.AlignLeft | Qt.AlignVCenter, unit)

    painter.setPen(QColor(style.faint))
    painter.setFont(theme.ui_font(max(9, int(min(r.height() * 0.08, 11)))))
    painter.drawText(QRectF(r.left() + pad, r.bottom() - pad - r.height() * 0.16,
                            r.width() - pad * 2, r.height() * 0.16),
                     Qt.AlignLeft | Qt.AlignVCenter, note)


def draw_preview(painter, rect, dpr=1.0):
    from deskorg.widget_style import DEFAULT_STYLE
    from deskorg.widget_glass import paint_glass
    r = QRectF(rect)
    paint_glass(painter, r, 14.0)
    draw_content(painter, r.adjusted(10, 10, -10, -10),
                 {"title": "年假", "date": "", "unit": "day"}, DEFAULT_STYLE)


class CountdownWidget(GlassWidget):
    """倒计时组件：跨天才会变，但用 1 小时定时器兜住"开着过夜"的场景。"""

    TYPE = "countdown"

    def __init__(self, storage, entry):
        super().__init__(storage, entry)
        self._timer = QTimer(self)
        self._timer.setInterval(60 * 60 * 1000)
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
