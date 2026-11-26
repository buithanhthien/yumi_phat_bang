#!/usr/bin/env python3
"""Common UI utility functions"""
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox, QTextEdit
from PyQt6.QtCore import QTimer, Qt


def format_log_message(message):
    """Format a log message with timestamp and color coding
    
    Returns:
        str: HTML-formatted log message
    """
    ts = datetime.now().strftime("%H:%M:%S")
    
    # Determine color based on message content
    if "[ERROR]" in message or "✗" in message:
        color = "#ef4444"
    elif "[WARN]" in message or "WARNING" in message or "[CẢNH BÁO]" in message:
        color = "#f59e0b"
    elif "✓" in message or "completed" in message.lower() or "restored" in message or "thành công" in message:
        color = "#22c55e"
    else:
        color = "#1a2a5e"
    
    return f'<span style="color:#8fa3cc">[{ts}]</span> <span style="color:{color}">{message}</span>'


def append_log(log_widget: QTextEdit, message: str):
    """Append a formatted log message to a QTextEdit widget
    
    Args:
        log_widget: QTextEdit widget to append to
        message: Message to log
    """
    log_widget.append(format_log_message(message))


def get_current_time_string():
    """Get current time as HH:MM:SS string"""
    return datetime.now().strftime("%H:%M:%S")


def setup_clock_timer(label, interval_ms=1000):
    """Setup a QTimer to update a clock label
    
    Args:
        label: QLabel to update with time
        interval_ms: Update interval in milliseconds
    
    Returns:
        QTimer: The created timer (already started)
    """
    def update():
        label.setText(get_current_time_string())
    
    timer = QTimer()
    timer.timeout.connect(update)
    timer.start(interval_ms)
    update()  # Initial update
    return timer


def _message_box(parent, title, text, icon):
    box = QMessageBox(parent)
    box.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    box.setWindowTitle(title)
    box.setIcon(icon)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(title)
    box.setInformativeText(text)
    return box


def warning_dialog(parent, title, text):
    box = _message_box(parent, title, text, QMessageBox.Icon.Warning)
    back = box.addButton('Quay lại', QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(back)
    box.setEscapeButton(back)
    box.exec()


def confirm_dialog(parent, title, text):
    box = _message_box(parent, title, text, QMessageBox.Icon.Question)
    confirm = box.addButton('Xác nhận', QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton('Hủy', QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    return box.clickedButton() is confirm
