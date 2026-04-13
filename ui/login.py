# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QApplication, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor
from core.vault import has_master_password, set_master_password, verify_master_password, wipe_all
try:
    import core.audit as _login_audit
except Exception:
    class _login_audit:
        @staticmethod
        def log(a, d=""): pass


class LoginWindow(QWidget):

    def __init__(self, icon: QIcon = None):
        super().__init__()
        self.setWindowTitle("FluxKey")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if icon and not icon.isNull():
            self.setWindowIcon(icon)
        self._drag_pos  = None
        self._icon      = icon
        self._first_run = not has_master_password()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        # ── Card ─────────────────────────────────────────────────────
        self._card = QWidget()
        self._card.setObjectName("loginCard")
        self._card.setStyleSheet(
            "QWidget#loginCard{"
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #1A1630,stop:1 #0E0C1E);"
            "border:1px solid rgba(109,40,217,0.22);"
            "border-radius:20px;}"
        )
        card_l = QVBoxLayout(self._card)
        card_l.setContentsMargins(0, 0, 0, 0)
        card_l.setSpacing(0)

        # ── Title bar ────────────────────────────────────────────────
        tbar = QWidget()
        tbar.setFixedHeight(48)
        tbar.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1A1428,stop:1 #12101A);"
            "border-top-left-radius:19px;border-top-right-radius:19px;"
            "border-bottom:1px solid rgba(109,40,217,0.18);"
        )
        tbl = QHBoxLayout(tbar)
        tbl.setContentsMargins(18, 0, 14, 0)
        tbl.setSpacing(8)

        badge = QLabel("FK")
        badge.setFixedSize(30, 30)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "border-radius:8px;color:white;font-size:11px;"
            "font-weight:800;letter-spacing:0.5px;"
        )
        lbl = QLabel("FluxKey")
        lbl.setStyleSheet(
            "color:white;font-size:13px;font-weight:800;"
            "letter-spacing:2.5px;background:transparent;"
        )
        tbl.addWidget(badge)
        tbl.addSpacing(6)
        tbl.addWidget(lbl)
        tbl.addStretch()

        # Close button — solid hover only (Qt6 cannot parse gradient in :hover)
        xbtn = QPushButton("✕")
        xbtn.setFixedSize(30, 30)
        xbtn.setCursor(Qt.PointingHandCursor)
        xbtn.setStyleSheet(
            "QPushButton{background:transparent;color:#3D2A58;border:none;"
            "font-size:12px;border-radius:8px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;}"
        )
        xbtn.clicked.connect(QApplication.quit)
        tbl.addWidget(xbtn)
        card_l.addWidget(tbar)

        # Gradient divider rule
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 transparent,stop:0.3 #7C3AED,"
            "stop:0.7 rgba(139,92,246,0.5),stop:1 transparent);"
            "border:none;"
        )
        card_l.addWidget(rule)

        # ── Body ─────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(32, 18, 32, 22)
        bl.setSpacing(0)

        # FluxKey title
        title = QLabel("FluxKey")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color:white;font-size:30px;font-weight:800;"
            "letter-spacing:5px;background:transparent;"
        )
        bl.addWidget(title)
        bl.addSpacing(4)

        # Subtitle — typewriter animated
        self._sub = QLabel(
            "CYBER VAULT" if not self._first_run else "CREATE MASTER PASSWORD"
        )
        self._sub.setAlignment(Qt.AlignCenter)
        self._sub.setStyleSheet(
            "color:#6D28D9;font-size:10px;letter-spacing:3.5px;"
            "font-weight:600;background:transparent;"
        )
        bl.addWidget(self._sub)
        bl.addSpacing(18)

        # Status / error label
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setFixedHeight(18)
        self._status.setStyleSheet(
            "color:#f87171;font-size:11px;background:transparent;font-weight:600;"
        )
        bl.addWidget(self._status)
        bl.addSpacing(4)

        # MASTER PASSWORD label
        pwd_lbl = QLabel("MASTER PASSWORD")
        pwd_lbl.setStyleSheet(
            "color:#6D28D9;font-size:9px;font-weight:700;"
            "letter-spacing:2px;background:transparent;"
        )
        bl.addWidget(pwd_lbl)
        bl.addSpacing(5)

        # Shared field style — no gradient in :focus pseudo-state issue here
        _field_style = (
            "QLineEdit{background:#0c091e;border:1px solid #1e1540;"
            "border-radius:13px;padding:0 18px;color:#e2d5f8;font-size:14px;"
            "letter-spacing:1px;}"
            "QLineEdit:focus{border:1.5px solid #7C3AED;background:#110e28;}"
            "QLineEdit::placeholder{color:#3a2a60;font-size:13px;}"
        )

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Enter your master password…")
        self.pwd.setEchoMode(QLineEdit.Password)
        self.pwd.setFixedHeight(48)
        self.pwd.setStyleSheet(_field_style)
        self.pwd.returnPressed.connect(self._action)
        bl.addWidget(self.pwd)
        bl.addSpacing(10)

        # Confirm field (first-run only)
        self.confirm = QLineEdit()
        self.confirm.setPlaceholderText("Confirm password…")
        self.confirm.setEchoMode(QLineEdit.Password)
        self.confirm.setFixedHeight(48)
        self.confirm.setStyleSheet(_field_style)
        self.confirm.returnPressed.connect(self._action)
        self.confirm.setVisible(self._first_run)
        bl.addWidget(self.confirm)
        if self._first_run:
            bl.addSpacing(10)

        # Unlock / Create button
        # CRITICAL: only solid colors in :hover/:pressed — Qt6 on Windows
        # throws "Could not parse stylesheet" for qlineargradient in pseudo-states
        self.btn = QPushButton(
            "Create Vault" if self._first_run else "Unlock Vault"
        )
        self.btn.setFixedHeight(52)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #5b1fcc,stop:0.5 #8b30f0,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:14px;"
            "font-size:15px;font-weight:800;letter-spacing:1.5px;}"
            "QPushButton:hover{background:#7C3AED;}"
            "QPushButton:pressed{background:#4a10aa;}"
        )
        self.btn.clicked.connect(self._action)
        bl.addWidget(self.btn)
        bl.addSpacing(14)

        # Wipe vault link
        self._wipe_btn = QPushButton("Wipe vault and start over")
        self._wipe_btn.setCursor(Qt.PointingHandCursor)
        self._wipe_btn.setVisible(not self._first_run)
        self._wipe_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#3D2A58;"
            "border:none;font-size:11px;}"
            "QPushButton:hover{color:#f87171;}"
        )
        self._wipe_btn.clicked.connect(self._wipe)
        bl.addWidget(self._wipe_btn, 0, Qt.AlignCenter)

        card_l.addWidget(body)
        outer.addWidget(self._card)

        self._resize_for_mode()
        QTimer.singleShot(400, self._typewriter)
        QTimer.singleShot(600, self._create_shortcut)

    # ── Typewriter subtitle ───────────────────────────────────────────
    def _typewriter(self):
        full = "CYBER VAULT" if not self._first_run else "CREATE MASTER PASSWORD"
        self._sub.setText("")
        step = [0]
        def tick():
            step[0] += 1
            self._sub.setText(full[:step[0]] + ("_" if step[0] < len(full) else ""))
            if step[0] < len(full):
                QTimer.singleShot(65, tick)
            else:
                QTimer.singleShot(600, lambda: self._sub.setText(full))
        QTimer.singleShot(65, tick)

    def _resize_for_mode(self):
        h = 530 if self._first_run else 480
        self.setFixedSize(400, h)

    # ── Drag to move ─────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 62:
            self._drag_pos = (
                e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ── Desktop shortcut (Windows only) ─────────────────────────────
    def _create_shortcut(self):
        import sys, os, subprocess
        if sys.platform != "win32": return
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, "FluxKey.lnk")
            if os.path.exists(shortcut_path): return
            if hasattr(sys, "_MEIPASS"):
                exe = sys.executable
                ico_path = os.path.join(sys._MEIPASS, "fluxkey.ico")
                ps = (f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut_path}");'
                      f'$s.TargetPath="{exe}";$s.IconLocation="{ico_path}";'
                      f'$s.Description="FluxKey Password Manager";$s.Save()')
            else:
                exe = sys.executable
                main_py = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "main.py")
                )
                ps = (f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut_path}");'
                      f'$s.TargetPath="{exe}";$s.Arguments=\\"{main_py}\\";'
                      f'$s.Description="FluxKey Password Manager";$s.Save()')
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                creationflags=0x08000000, timeout=10
            )
        except Exception:
            pass

    # ── Login / create action ────────────────────────────────────────
    def _action(self):
        pw = self.pwd.text()
        if not pw:
            self._shake_status("Password cannot be empty.")
            return
        if self._first_run:
            if pw != self.confirm.text():
                self._shake_status("Passwords do not match.")
                return
            if len(pw) < 4:
                self._shake_status("Minimum 4 characters.")
                return
            set_master_password(pw)
            self._open_dashboard()
        else:
            ok, msg, _ = verify_master_password(pw)
            if ok:
                _login_audit.log("login_success", "vault_unlocked")
                self._open_dashboard()
            else:
                _login_audit.log("login_failed", "bad_password")
                self._shake_status(msg)
                self.pwd.clear()

    def _shake_status(self, msg):
        self._status.setText(msg)
        orig_x = self._card.x()
        steps = [6, -10, 8, -6, 4, -2, 0]
        def do_shake(i=0):
            if i < len(steps):
                self._card.move(orig_x + steps[i], self._card.y())
                QTimer.singleShot(40, lambda: do_shake(i + 1))
            else:
                self._card.move(orig_x, self._card.y())
        do_shake()

    def _open_dashboard(self):
        try:
            from ui.dashboard import Dashboard
            self._dash = Dashboard(self._icon)
            self._dash.show()
            self.close()
        except Exception as ex:
            import traceback
            self._status.setText(f"Error: {str(ex)[:60]}")
            traceback.print_exc()

    def _wipe(self):
        box = QMessageBox(self)
        box.setWindowTitle("Wipe Vault")
        box.setText(
            "Permanently delete ALL vault entries and master password?"
            "\n\nThis CANNOT be undone."
        )
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        box.setStyleSheet(
            "QMessageBox{background:#12101A;}"
            "QLabel{color:#C4B8E8;font-size:13px;}"
            "QPushButton{background:#1C1438;color:#C4B8E8;"
            "border:1px solid #261840;border-radius:7px;"
            "padding:7px 20px;font-weight:600;min-width:70px;}"
            "QPushButton:hover{background:#7C3AED;color:white;border-color:#7C3AED;}"
        )
        if box.exec() == QMessageBox.Yes:
            wipe_all()
            self._first_run = True
            self._sub.setText("CREATE MASTER PASSWORD")
            self._status.setText("")
            self.pwd.clear()
            self.confirm.clear()
            self.confirm.setVisible(True)
            self.btn.setText("Create Vault")
            self.btn.setStyleSheet(
                "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #5b1fcc,stop:0.5 #8b30f0,stop:1 #8B5CF6);"
                "color:white;border:none;border-radius:14px;"
                "font-size:15px;font-weight:800;letter-spacing:1.5px;}"
                "QPushButton:hover{background:#7C3AED;}"
                "QPushButton:pressed{background:#4a10aa;}"
            )
            self._wipe_btn.setVisible(False)
            self._resize_for_mode()