"""Startup-only visual language; shared screens/dialog styles stay independent."""
from PyQt6.QtWidgets import QWidget

# IUH brand handbook, colour specification (page 5):
# https://www.senviet.art/wp-content/uploads/2025/11/So-tay-thuong-hieu-IUH-moi-chinh-thuc.pdf
# Dark Blue RGB(33, 64, 154), Yellow RGB(253, 185, 36), White RGB(255, 255, 255).
PALETTE = dict(bg="#f5f7fc", surface="#ffffff", ink="#21409a", muted="#526580",
               line="#d7e0ec", sidebar="#ffffff", blue="#21409a", yellow="#fdb924",
               blue_hover="#19327b", blue_tint="#f3f6ff", yellow_tint="#fff5db",
               red="#b42332", amber="#865d10")

STARTUP_STYLESHEET = """
QWidget#startup-root, QWidget#content-panel { background: %(bg)s; }
QWidget#startup-root { color: %(ink)s; font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 14px; }
QWidget#startup-root QLabel { background: transparent; color: %(ink)s; }
QWidget#left-panel { background: %(sidebar)s; border-right: 1px solid %(line)s; }
QWidget#left-panel QLabel#wordmark { color: %(blue)s; font-size: 22px; font-weight: 700; padding: 4px 8px 12px 8px; }
QWidget#left-panel QLabel#section-label { color: %(muted)s; font-size: 11px; padding: 8px 10px; }
QWidget#startup-root QPushButton { min-height: 44px; border: 1px solid %(line)s; border-radius: 8px; padding: 0 12px; background: white; color: %(ink)s; font-size: 14px; }
QWidget#startup-root QPushButton:hover { background: #eaf0fc; border-color: %(blue)s; }
QWidget#startup-root QPushButton:pressed { background: #dce7fc; }
QWidget#startup-root QPushButton:focus { border: 2px solid %(blue)s; }
QWidget#startup-root QPushButton:disabled { background: #e8edf4; color: #63738a; border-color: %(line)s; }
QWidget#left-panel QPushButton#mode-btn { background: transparent; color: %(muted)s; border: 2px solid transparent; text-align: left; padding: 0 12px; }
QWidget#left-panel QPushButton#mode-btn:hover { background: %(yellow_tint)s; color: %(blue)s; }
QWidget#left-panel QPushButton#mode-btn:focus { border-color: %(yellow)s; }
QWidget#left-panel QPushButton#mode-btn:pressed { background: #ffe293; color: %(blue)s; }
QWidget#left-panel QPushButton#mode-btn:disabled { color: #91a2ba; }
QWidget#startup-root QLabel#header-title { font-size: 26px; font-weight: 700; }
QWidget#startup-root QLabel#panel-title { font-size: 18px; font-weight: 700;  }
QWidget#startup-root QLabel#muted, QWidget#startup-root QLabel#clock { color: %(muted)s; font-size: 13px; }
QWidget#startup-root QWidget#voice-panel, QWidget#startup-root QWidget#conversation-panel,
QWidget#startup-root QWidget#status-card { background: %(surface)s; border: 1px solid %(line)s; border-radius: 16px; }
QWidget#startup-root QLabel#device-name { color: %(muted)s; font-size: 13px; }
QWidget#startup-root QLabel#device-state { font-size: 13px; font-weight: 600; padding: 5px 8px; border-radius: 6px; background: %(blue_tint)s; }
QWidget#startup-root QWidget#status-card[state="checking"] QLabel#device-state,
QWidget#startup-root QWidget#status-card[state="checking"] QLabel#status-dot { color: %(amber)s; }
QWidget#startup-root QWidget#status-card[state="online"] QLabel#device-state,
QWidget#startup-root QWidget#status-card[state="online"] QLabel#status-dot { color: %(blue)s; }
QWidget#startup-root QWidget#status-card[state="offline"] QLabel#device-state,
QWidget#startup-root QWidget#status-card[state="offline"] QLabel#status-dot { color: %(red)s; }
QWidget#startup-root QPushButton#voice-btn { background: %(yellow)s; color: %(blue)s; min-height: 56px; font-size: 20px; font-weight: 700; border: 2px solid %(yellow)s; border-radius: 12px; }
QWidget#startup-root QPushButton#voice-btn:hover { background: #ffe293; }
QWidget#startup-root QPushButton#voice-btn:checked { background: %(blue)s; color: white; border-color: %(blue)s; }
QWidget#startup-root QPushButton#voice-btn:disabled { background: %(yellow)s; color: %(blue)s; border-color: %(yellow)s; }
QWidget#startup-root QPushButton#interrupt-btn { background: %(red)s; color: white; border: 2px solid %(red)s; min-height: 48px; font-size: 23px; font-weight: 700; border-radius: 12px; }
QWidget#startup-root QPushButton#interrupt-btn:hover { background: #941a28; }
QWidget#startup-root QPushButton#interrupt-btn:pressed { background: #711320; border-color: #ffb8c0; }
QWidget#startup-root QPushButton#interrupt-btn:focus, QWidget#startup-root QPushButton#voice-btn:focus { border-color: %(yellow)s; }
QWidget#startup-root QPushButton#send-btn { background: %(yellow)s; color: %(blue)s; border-color: %(yellow)s; font-weight: 600; }
QWidget#startup-root QPushButton#send-btn:hover { background: #ffe293; }
QWidget#startup-root QPushButton#keyboard-toggle:checked { background: %(yellow_tint)s; border-color: %(yellow)s; }
QWidget#startup-root QTextEdit#chat-history { background: white; color: %(ink)s; border: none; border-radius: 8px; padding: 8px; font-size: 16px; }
QWidget#startup-root QLineEdit#chat-input { background: white; color: %(ink)s; border: 1px solid %(line)s; border-radius: 8px; padding: 0 12px; font-size: 15px; selection-background-color: %(blue)s; }
QWidget#startup-root QLineEdit#chat-input:focus { border: 2px solid %(blue)s; }
QWidget#startup-root QScrollBar:vertical { background: #edf1f6; width: 10px; }
QWidget#startup-root QScrollBar::handle:vertical { background: #a8b8cc; min-height: 28px; border-radius: 4px; }
QWidget#startup-root QScrollBar::add-line:vertical, QWidget#startup-root QScrollBar::sub-line:vertical { height: 0; }
QWidget#left-panel QLabel#overview-label { background: %(blue)s; color: white; border-left: 4px solid %(yellow)s; border-radius: 10px; padding: 0 14px; font-weight: 600; }
QWidget#startup-root QLabel#device-icon { background: %(yellow_tint)s; border-radius: 12px; }
QWidget#startup-root QWidget#voice-panel { background: %(blue)s; border: 1px solid %(blue)s; }
QWidget#startup-root QWidget#voice-panel QLabel#panel-title { color: white; }
QWidget#startup-root QWidget#voice-panel QLabel#muted { color: #e2e9fc; }
QWidget#startup-root QWidget#voice-panel QLabel { color: white; }
QWidget#startup-root QPushButton#voice-btn:checked { background: %(yellow)s; color: %(blue)s; border-color: %(yellow)s; }
QWidget#startup-root QPushButton#voice-btn:pressed { background: #ffe293; color: %(blue)s; }
QWidget#startup-root QLabel#clock { background: white; border: 1px solid %(line)s; border-radius: 8px; padding: 12px; }
""" % PALETTE

TEXT = dict(checking='Đang kiểm tra', online='Hoạt động', offline='Mất kết nối',
    front='LiDAR trước', rear='LiDAR sau', diagnostics='Trạng thái STM32')

def startup_text(language=None):
    return TEXT

def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
