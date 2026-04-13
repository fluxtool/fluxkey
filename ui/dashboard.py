# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QCheckBox, QLineEdit, QApplication, QInputDialog,
    QFrame, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QDialog, QMessageBox, QSizePolicy, QFileDialog
)
from PySide6.QtCore import (
    Qt, QRectF, QTimer, QPoint, QRect,
    QPropertyAnimation, QEasingCurve, QObject, Signal,
)
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QPen,
    QRadialGradient, QPainterPath, QIcon, QFont
)
import math
import re
import random
import hashlib
import os
import threading
import urllib.request
import webbrowser
import time
import json
import colorsys
import datetime
import string
from core.password_generator import PasswordGenerator
from core.vault import (
    Vault, set_master_password, verify_master_password, wipe_all,
    VAULT_FILE, add_to_history, load_history,
    clear_history, get_auto_lock_minutes, set_auto_lock_minutes,
    check_integrity, get_lockout_remaining,
    get_all_groups, create_group, update_group, delete_group,
    get_group_by_id, DEFAULT_VAULT_ID, DEFAULT_VAULT_NAME, DEFAULT_AVATARS,
)
from core.license import is_plus, set_plus, vault_limit, FREE_VAULT_LIMIT
from core.notes import get_notes, save_note, delete_note, NOTES_FILE
import core.audit as audit
import secrets
try:
    from core.profile import (load_profile, save_profile, PROFILE_EMOJIS,
        load_profiles, create_profile, delete_profile, get_current_profile_id,
        set_current_profile_id, _profile_vault_path)
except ImportError:
    PROFILE_EMOJIS = ["🦊","🐺","🐉","🦁","🐯","🐻","🐼","🦝","🦋","🌙","⚡","🔥","❄️","🌊","🌪️","💎","🗡️","🛡️","⚔️","🔮"]
    def load_profile(pid=None): return {"id":"default","username": "FluxUser", "avatar": "🦊"}
    def save_profile(u, a, pid=None): pass
    def load_profiles(): return [{"id":"default","username":"FluxUser","avatar":"🦊"}]
    def create_profile(u,a): return "default"
    def delete_profile(pid): pass
    def get_current_profile_id(): return "default"
    def set_current_profile_id(pid): pass
    def _profile_vault_path(pid): return ""


# ── PLUS Badge ─────────────────────────────────────────────────────────────
class PlusBadge(QWidget):
    """Animated PLUS wordmark — no background, shimmer glow on the text."""
    def __init__(self):
        super().__init__()
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)  # 20fps — gentle, low CPU
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.setFixedHeight(30)
        self.setFixedWidth(80)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")

    def _tick(self):
        self._phase = (self._phase + 0.04) % (2 * math.pi)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        pulse = 0.5 + 0.5 * math.sin(self._phase)

        # Scale fonts to widget height
        star_pt = H * 0.30
        text_pt = H * 0.28
        star_w  = int(H * 0.55)

        # ✦ star in bright purple
        star_f = p.font()
        star_f.setPointSizeF(star_pt); star_f.setBold(True)
        p.setFont(star_f)
        star_col = QColor(int(180 + 50*pulse), int(100 + 40*pulse), 255, 255)
        p.setPen(star_col)
        p.drawText(QRect(0, 0, star_w, H), Qt.AlignCenter, "✦")

        # PLUS text with shimmer
        txt_f = p.font()
        txt_f.setPointSizeF(text_pt); txt_f.setWeight(QFont.Weight.Black)
        txt_f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, H * 0.09)
        p.setFont(txt_f)

        # Shimmer gradient across text
        shimmer_x = (self._phase / (2 * math.pi)) * (W + 30) - 15
        tg = QLinearGradient(shimmer_x - 20, 0, shimmer_x + 20, 0)
        tg.setColorAt(0.0, QColor(160, 80, 255, 220))
        tg.setColorAt(0.4, QColor(200, 140, 255, 220))
        tg.setColorAt(0.5, QColor(240, 210, 255, 255))
        tg.setColorAt(0.6, QColor(200, 140, 255, 220))
        tg.setColorAt(1.0, QColor(160, 80, 255, 220))
        p.setPen(QColor(180, 100, 255, 230))
        p.drawText(QRect(star_w - 2, 0, W - star_w + 2, H), Qt.AlignVCenter | Qt.AlignLeft, "PLUS")
        p.end()


# ── Theme Toggle Button (sun/moon) ───────────────────────────────────────────

# ── Discord button ────────────────────────────────────────────────────────────

class DiscordButton(QPushButton):
    """
    Accurate Discord logo — drawn from the official SVG path geometry.
    Shape: wide rounded-rect body, two circular bumps on top corners,
    concave sides, two oval eyes cut out.
    """
    def __init__(self):
        super().__init__()
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self.setAttribute(Qt.WA_TranslucentBackground)

    def enterEvent(self, e): self._hover = True;  self.update()
    def leaveEvent(self, e): self._hover = False; self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Hover pill background
        if self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(88, 101, 242, 38))
            p.drawRoundedRect(1, 1, W - 2, H - 2, 7, 7)

        col = QColor(114, 137, 218) if self._hover else QColor(88, 101, 242)

        # ── Draw the Discord logo scaled into a 22x16 box centred in widget ──
        # Official Discord logo proportions (normalised from SVG viewBox 0 0 71 55):
        # We'll trace the key shape manually at our scale.
        #
        # The logo is:
        #   - A wide rounded rect body (bottom ~60% of height)
        #   - Two large circular bumps at top-left and top-right corners
        #   - Slightly concave sides (achieved with bezier curves)
        #   - Two oval "eyes" punched out in white/bg colour

        LW = 22.0   # logo width
        LH = 16.0   # logo height
        ox = (W - LW) / 2.0
        oy = (H - LH) / 2.0 + 0.5

        # Proportions (relative to LW/LH):
        bump_r   = LH * 0.42      # radius of ear bumps
        body_top = LH * 0.38      # y where body starts
        body_r   = LH * 0.30      # corner radius of body rect

        # ── Build the outer silhouette path ──────────────────────────────────
        outer = QPainterPath()

        # Left bump circle
        outer.addEllipse(
            QRectF(ox,
                   oy,
                   bump_r * 2, bump_r * 2)
        )
        # Right bump circle
        outer.addEllipse(
            QRectF(ox + LW - bump_r * 2,
                   oy,
                   bump_r * 2, bump_r * 2)
        )
        # Body rounded rect (overlaps lower part of bumps to merge them)
        outer.addRoundedRect(
            QRectF(ox, oy + body_top, LW, LH - body_top),
            body_r, body_r
        )

        # Unite all into one filled silhouette
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawPath(outer.simplified())

        # ── Eyes — two vertical ovals punched out ────────────────────────────
        eye_w  = LW * 0.18
        eye_h  = LH * 0.30
        eye_y  = oy + LH * 0.42
        leye_x = ox + LW * 0.18
        reye_x = ox + LW * 0.64

        bg = QColor(30, 20, 60)   # near-black to match app bg, looks like cutout
        p.setBrush(bg)
        p.drawEllipse(QRectF(leye_x, eye_y, eye_w, eye_h))
        p.drawEllipse(QRectF(reye_x, eye_y, eye_w, eye_h))

        p.end()


# ── Gear button (Settings) ────────────────────────────────────────────────────

class GearButton(QPushButton):
    """New v7 Settings gear — larger, cleaner, with purple accent ring on hover."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._angle = 0.0
        self._spin = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self.setAttribute(Qt.WA_TranslucentBackground)

    def _tick(self):
        self._spin = (self._spin + 2.5) % 360
        self.update()

    def enterEvent(self, e):
        self._hover = True; self._timer.start(30)

    def leaveEvent(self, e):
        self._hover = False; self._timer.stop(); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        teeth, r_o, r_i, tooth_h = 8, 9.5, 6.0, 3.2
        col = QColor("#A78BFA") if self._hover else QColor("#6D28D9")
        hole = QColor("#F8F6FF") if self._hover else QColor("#1C1830")

        p.translate(cx, cy)
        if self._hover:
            p.rotate(self._spin)

        path = QPainterPath()
        for i in range(teeth * 2):
            angle = math.radians(i * 180 / teeth)
            r = r_o + tooth_h if i % 2 == 0 else r_o
            x, y = r * math.cos(angle), r * math.sin(angle)
            if i == 0: path.moveTo(x, y)
            else: path.lineTo(x, y)
        path.closeSubpath()

        # Outer gear body
        p.setPen(Qt.NoPen); p.setBrush(col)
        p.drawPath(path)
        p.drawEllipse(QRect(int(-r_o), int(-r_o), int(r_o * 2), int(r_o * 2)))

        # Centre hole
        p.setBrush(hole)
        p.drawEllipse(QRect(int(-r_i), int(-r_i), int(r_i * 2), int(r_i * 2)))
        p.end()


# ── XP Progress Bar — custom painted, always perfectly rounded ───────────────
class XpBar(QWidget):
    """
    Smooth XP progress bar.
    Painted directly — no child QFrame clipping issues.
    Both left and right caps are always rounded regardless of fill %.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(10)
        self._pct = 0.0   # 0.0 – 1.0

    def set_pct(self, pct: float) -> None:
        self._pct = max(0.0, min(1.0, pct))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        rad = H / 2.0

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(109, 40, 217, 38))
        p.drawRoundedRect(QRectF(0, 0, W, H), rad, rad)

        # Fill — minimum visible pill width so it's never a sharp stub
        if self._pct > 0:
            fill_w = max(H, self._pct * W)   # at least as wide as it is tall
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.00, QColor(76,  29, 149))   # deep purple
            grad.setColorAt(0.40, QColor(124, 58, 237))   # violet
            grad.setColorAt(0.75, QColor(139, 92, 246))   # medium purple
            grad.setColorAt(1.00, QColor(167, 139, 250))  # lavender tip
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(0, 0, fill_w, H), rad, rad)

            # Subtle top sheen
            sheen = QLinearGradient(0, 0, 0, H)
            sheen.setColorAt(0.0, QColor(255, 255, 255, 28))
            sheen.setColorAt(0.5, QColor(255, 255, 255, 0))
            p.setBrush(sheen)
            p.drawRoundedRect(QRectF(0, 0, fill_w, H / 2), rad, rad)

        p.end()


# ── Strength meter — liquid wobble ────────────────────────────────────────
class StrengthMeter(QWidget):
    """
    Premium segmented strength meter.
    5 glowing capsule segments, each lights up in sequence with colour shift.
    Uses smooth lerp animation — no spring physics to keep it fast.
    """
    SEGS = 5
    SEG_COLS = [
        (239, 68,  68),   # Weak   — red
        (249, 115, 22),   # Fair   — orange
        (234, 179,  8),   # Good   — amber
        ( 34, 197, 94),   # Strong — green
        (168, 85, 247),   # Max    — purple
    ]

    def __init__(self, height=8):
        super().__init__()
        self.setFixedHeight(height)
        self._target = 0.0   # 0.0 – 1.0 (fraction of max)
        self._disp   = [0.0] * self.SEGS  # per-segment brightness 0-1
        self._phase  = 0.0   # shimmer phase
        self._timer  = QTimer(self)
        self._timer.setInterval(16)  # 60fps
        self._timer.timeout.connect(self._tick)

    def set_value(self, v):
        """v is 0-100."""
        self._target = max(0.0, min(1.0, v / 100.0))
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self):
        self._phase = (self._phase + 0.08) % (2 * 3.14159)
        changed = False
        for i in range(self.SEGS):
            seg_thresh = (i + 1) / self.SEGS
            want = 1.0 if self._target >= seg_thresh else (
                max(0.0, (self._target - i/self.SEGS) * self.SEGS)
            )
            diff = want - self._disp[i]
            if abs(diff) > 0.004:
                self._disp[i] += diff * 0.14
                changed = True
            else:
                self._disp[i] = want
        if not changed:
            self._timer.stop()
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        gap   = 4
        seg_w = (W - gap * (self.SEGS - 1)) / self.SEGS
        rad   = H / 2
        p.setPen(Qt.NoPen)

        shimmer = 0.5 + 0.5 * math.sin(self._phase)

        for i in range(self.SEGS):
            x   = i * (seg_w + gap)
            br  = self._disp[i]
            r, g, b = self.SEG_COLS[i]

            # Track (dark)
            p.setBrush(QColor(r//6, g//6, b//6, 120))
            p.drawRoundedRect(int(x), 0, int(seg_w), H, rad, rad)

            if br > 0.01:
                # Filled segment
                fill_g = QLinearGradient(x, 0, x + seg_w, 0)
                alpha  = int(200 * br)
                fill_g.setColorAt(0.0, QColor(r, g, b, alpha))
                fill_g.setColorAt(0.5, QColor(
                    min(255, r + int(50 * shimmer * br)),
                    min(255, g + int(50 * shimmer * br)),
                    min(255, b + int(60 * shimmer * br)),
                    alpha))
                fill_g.setColorAt(1.0, QColor(r, g, b, alpha))
                p.setBrush(fill_g)
                p.drawRoundedRect(int(x), 0, int(seg_w * br + 0.5), H, rad, rad)

                # Glow overlay
                if br > 0.5:
                    glow_a = int(80 * br * shimmer)
                    p.setBrush(QColor(min(255,r+60), min(255,g+60), min(255,b+60), glow_a))
                    p.drawRoundedRect(int(x), 1, int(seg_w * br), max(1, H-2), rad, rad)


# ── Copy flash overlay — lightweight border flash ─────────────────────────
class CopyFlashOverlay(QWidget):
    """Lightweight green border flash on the output field — zero particle lag."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._alpha = 0
        self._timer = QTimer(self); self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def trigger(self):
        self._alpha = 255
        self.show(); self.raise_(); self._timer.start()

    def _tick(self):
        self._alpha = max(0, self._alpha - 18)
        if self._alpha == 0:
            self._timer.stop(); self.hide()
        self.update()

    def paintEvent(self, e):
        if self._alpha <= 0: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(74, 222, 128, self._alpha)); pen.setWidthF(2.5)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 10, 10)
        p.end()


# ── Generate button — clean, fast, no heavy animations ────────────────────
class GenChargeBtn(QPushButton):
    """
    Clean Generate button — breathing border glow only.
    No particles, no shockwaves, no scan laser. Fast and smooth.
    """
    def __init__(self, text="  GENERATE"):
        super().__init__(text)
        self.setObjectName("btnPrimary")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)  # 30fps — plenty for a breathing glow
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._phase = (self._phase + 0.04) % (2 * math.pi)
        self.update()

    def trigger_burst(self):
        pass  # no-op — animation removed for performance

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        pulse = 0.5 + 0.5 * math.sin(self._phase)
        rad = 14.0

        # Outer halo
        halo_pen = QPen(QColor(139, 92, 246, int(25 + 30 * pulse)))
        halo_pen.setWidthF(5.0)
        p.setPen(halo_pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(2, 2, W-4, H-4, rad+1, rad+1)

        # Sharp animated border
        border_pen = QPen(QColor(167, 139, 250, int(140 + 80 * pulse)))
        border_pen.setWidthF(1.5)
        p.setPen(border_pen)
        p.drawRoundedRect(1, 1, W-2, H-2, rad, rad)
        p.end()
# ── EQ widget ──────────────────────────────────────────────────────────────
class EQWidget(QWidget):
    """
    FluxKey EQ v5 — Dual-mode neon visualiser.

    Performance architecture:
      • 30fps physics tick (33ms), NOT tied to paintEvent
      • QPixmap double-buffer: physics writes → pixmap, paintEvent blits
      • 24 bars only (not 32) — halves gradient work
      • NO per-bar radial gradients (killed the old lag source)
      • Colour palette pre-baked as QColor tuples
      • Idle mode: gentle breathing sine wave, barely any CPU

    Visual design — two modes:
      IDLE  : 24 thin neon bars, slow breathing wave, deep purple ambiance
      ACTIVE: bars spring-physics driven with beat kicks, bright violet→white
               tips, mirror reflection, horizontal pulse ring, scan laser
    """

    BARS = 24

    # Pre-baked colour stops  (r,g,b)  — floor → tip
    _COL = [
        (12,  3, 40),
        (55, 10,140),
        (100, 25,210),
        (150, 55,255),
        (200,110,255),
        (240,200,255),
    ]

    def __init__(self):
        super().__init__()
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_OpaquePaintEvent)   # skip transparent fill

        self._on     = False
        self._fade   = 0.0
        self._phase  = 0.0
        self._scan   = 0.0
        self._beat   = 0.0
        self._pulse  = 0.0   # horizontal pulse ring radius (0→1)

        N = self.BARS
        self._h  = [0.04] * N
        self._v  = [0.0]  * N
        self._t  = [random.uniform(0.03, 0.50) for _ in range(N)]
        self._nt = [random.uniform(0.10, 0.60) for _ in range(N)]

        self._buf = None   # QPixmap double-buffer

        # Physics tick at 30fps — cheap
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(33)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

    def set_on(self, v: bool):
        self._on = v

    # ── colour helper — no QColor allocation in hot loop ────────────────────
    @staticmethod
    def _lerp(pal, t):
        n  = len(pal) - 1
        s  = max(0.0, min(1.0, t)) * n
        lo = int(s); hi = min(lo + 1, n); fr = s - lo
        r  = int(pal[lo][0] * (1-fr) + pal[hi][0] * fr)
        g  = int(pal[lo][1] * (1-fr) + pal[hi][1] * fr)
        b  = int(pal[lo][2] * (1-fr) + pal[hi][2] * fr)
        return r, g, b

    # ── physics tick ─────────────────────────────────────────────────────────
    def _tick(self):
        dt  = 0.033
        PI2 = 6.28318
        self._phase = (self._phase + dt * 0.35) % PI2

        if self._on:
            self._fade  = min(1.0, self._fade + dt * 5.0)
            self._scan  = (self._scan + dt * 0.55) % 1.0
            self._pulse = (self._pulse + dt * 0.38) % 1.0

            self._beat -= dt
            if self._beat <= 0:
                self._beat = 0.32 + random.uniform(0, 0.22)
                for _ in range(random.randint(2, 4)):
                    idx = random.randint(0, self.BARS - 1)
                    self._t[idx]  = random.uniform(0.72, 0.97)
                    self._nt[idx] = random.uniform(0.04, 0.14)

            for i in range(self.BARS):
                self._nt[i] -= dt
                if self._nt[i] <= 0:
                    self._t[i]  = random.uniform(0.03, 0.92)
                    self._nt[i] = random.uniform(0.07, 0.55)
                f = 20.0 * (self._t[i] - self._h[i]) - 7.5 * self._v[i]
                self._v[i] += f * dt
                self._h[i]  = max(0.02, min(0.97, self._h[i] + self._v[i] * dt))
        else:
            self._fade  = max(0.0, self._fade - dt * 3.5)
            self._scan  = 0.0
            self._pulse = 0.0
            for i in range(self.BARS):
                rest = 0.04 + 0.025 * math.sin(self._phase + i * 0.42)
                f    = 9.0 * (rest - self._h[i]) - 5.5 * self._v[i]
                self._v[i] += f * dt
                self._h[i]  = max(0.02, self._h[i] + self._v[i] * dt)

        self._redraw()   # write to pixmap
        self.update()    # queue a blit — near-zero cost

    # ── redraw into pixmap buffer ─────────────────────────────────────────────
    def _redraw(self):
        W, H = self.width(), self.height()
        if W < 2 or H < 2:
            return
        if self._buf is None or self._buf.size().width() != W or self._buf.size().height() != H:
            from PySide6.QtGui import QPixmap
            self._buf = QPixmap(W, H)

        p = QPainter(self._buf)
        p.setRenderHint(QPainter.Antialiasing, False)   # no AA on background
        pal  = self._COL
        a    = max(0.12, self._fade)
        REFL = max(8, H // 8)
        FLOOR = H - REFL

        # ── Background ────────────────────────────────────────────────────
        p.fillRect(0, 0, W, H, QColor(5, 2, 14))

        # Subtle floor ambient glow (cheap — one gradient rect)
        breathe = 0.35 + 0.65 * math.sin(self._phase)
        idle_a  = int(28 * breathe * max(0.2, 1.0 - self._fade))
        if idle_a > 3:
            ag = QLinearGradient(0, FLOOR, 0, 0)
            ag.setColorAt(0.0, QColor(80, 20, 200, idle_a))
            ag.setColorAt(1.0, QColor(40,  8, 120, 0))
            p.setPen(Qt.NoPen); p.setBrush(ag)
            p.drawRect(0, 0, W, H)

        # ── Bars ───────────────────────────────────────────────────────────
        bw  = W / self.BARS
        gap = max(1.0, bw * 0.14)
        pw  = bw - gap
        rad = min(pw / 2.0, 3.0)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)

        for i in range(self.BARS):
            bh   = self._h[i]
            bht  = FLOOR * bh
            bx   = i * bw + gap * 0.5
            by   = FLOOR - bht
            iw   = max(2, int(pw))
            ih   = max(2, int(bht))
            ix   = int(bx)
            iy   = int(by)

            # Bar gradient (floor=dark, tip=bright)
            gr = QLinearGradient(bx, float(FLOOR), bx, float(by))
            r0,g0,b0 = self._lerp(pal, 0.0);  gr.setColorAt(0.0, QColor(r0,g0,b0, int(25 * a)))
            r3,g3,b3 = self._lerp(pal, 0.35); gr.setColorAt(0.3, QColor(r3,g3,b3, int(85 * a)))
            r7,g7,b7 = self._lerp(pal, 0.72); gr.setColorAt(0.7, QColor(r7,g7,b7, int(175 * a)))
            r1,g1,b1 = self._lerp(pal, 1.0);  gr.setColorAt(1.0, QColor(r1,g1,b1, int(235 * a)))
            p.setBrush(gr)
            p.drawRoundedRect(ix, iy, iw, ih, rad, rad)


            # Floor reflection (1 rect, no AA needed)
            rh = min(REFL - 1, int(bht * 0.28))
            if rh > 1 and a > 0.12:
                p.setRenderHint(QPainter.Antialiasing, False)
                rr,rg,rb = self._lerp(pal, 0.85)
                rg2 = QLinearGradient(0, float(FLOOR), 0, float(FLOOR + rh))
                rg2.setColorAt(0.0, QColor(rr,rg,rb, int(70 * a * bh)))
                rg2.setColorAt(1.0, QColor(0,0,0,0))
                p.setBrush(rg2)
                p.drawRect(ix, FLOOR, iw, rh)
                p.setRenderHint(QPainter.Antialiasing, True)

        # ── Floor hairline ────────────────────────────────────────────────
        fl = QLinearGradient(0, FLOOR, W, FLOOR)
        fl.setColorAt(0.0, QColor(80, 20, 200, 0))
        fl.setColorAt(0.3, QColor(192,120,252, int(140 * a)))
        fl.setColorAt(0.7, QColor(160, 80,220, int(120 * a)))
        fl.setColorAt(1.0, QColor(80, 20,200, 0))
        fp = QPen(); fp.setBrush(fl); fp.setWidthF(1.2)
        p.setPen(fp); p.setBrush(Qt.NoBrush)
        p.drawLine(0, FLOOR, W, FLOOR)

        # ── Horizontal pulse ring (active only) ───────────────────────────
        if self._fade > 0.08:
            pr = self._pulse
            py_ = FLOOR * (1.0 - pr * 0.9)   # sweeps upward
            pulse_a = int(self._fade * 90 * (1.0 - pr))
            if pulse_a > 3:
                pp = QPen(QColor(210, 140, 255, pulse_a))
                pp.setWidthF(1.0)
                p.setPen(pp); p.setBrush(Qt.NoBrush)
                p.drawLine(0, int(py_), W, int(py_))


        # ── Reflection fade-out overlay ───────────────────────────────────
        p.setRenderHint(QPainter.Antialiasing, False)
        rc = QLinearGradient(0, FLOOR, 0, H)
        rc.setColorAt(0.0, QColor(0,0,0,0))
        rc.setColorAt(0.5, QColor(5,2,14,120))
        rc.setColorAt(1.0, QColor(5,2,14,220))
        p.setPen(Qt.NoPen); p.setBrush(rc)
        p.drawRect(0, FLOOR, W, REFL)

        p.end()

    # ── blit only ─────────────────────────────────────────────────────────────
    def paintEvent(self, ev):
        """No custom border glow — plain static border only."""
        super().paintEvent(ev)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._buf = None   # invalidate buffer on resize
        self._redraw()


# ── Power button ───────────────────────────────────────────────────────────
class PowerBtn(QPushButton):
    """
    Premium circular power button.
    - No OS frame — fully custom-painted circle
    - OFF: dark glass sphere, subtle purple rim, dim power icon
    - ON:  lit violet sphere, outer glow aura, orbiting spark dots,
           three counter-rotating dashed plasma rings
    """
    SIZE = 76

    def __init__(self):
        super().__init__()
        self.setFixedSize(self.SIZE, self.SIZE)
        # Remove ALL default OS button styling so nothing square shows
        self.setFlat(True)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._on          = False
        self._ring_phase  = 0.0
        self._pulse       = 0.0
        self._spark_phase = 0.0
        self._hover       = False
        self._hover_glow  = 0.0   # 0→1 lerp
        self.setCursor(Qt.PointingHandCursor)

        self._timer = QTimer(self)
        self._timer.setInterval(16)   # 60 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def enterEvent(self, e):
        self._hover = True
    def leaveEvent(self, e):
        self._hover = False

    def _tick(self):
        PI2 = 6.28318
        if self._on:
            self._ring_phase  = (self._ring_phase  + 0.045) % PI2
            self._pulse       = (self._pulse        + 0.032) % PI2
            self._spark_phase = (self._spark_phase  + 0.075) % PI2
        # Lerp hover glow
        target = 1.0 if self._hover else 0.0
        self._hover_glow += (target - self._hover_glow) * 0.12
        self.update()

    def toggle(self):
        self._on = not self._on
        self.update()

    @property
    def active(self): return self._on

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        W = H = self.SIZE
        cx = cy = W / 2.0
        R  = W / 2.0 - 6      # sphere radius (leaves room for glow rings)
        PI = math.pi

        # Clip everything to a circle — nothing square can ever bleed outside
        clip = QPainterPath()
        clip.addEllipse(0, 0, W, H)
        p.setClipPath(clip)

        pulse   = 0.5 + 0.5 * math.sin(self._pulse)
        hg      = self._hover_glow

        # ── OFF-state hover ring ──────────────────────────────────────
        if not self._on and hg > 0.01:
            hr_pen = QPen(QColor(168, 85, 247, int(60 * hg)))
            hr_pen.setWidthF(1.5)
            p.setPen(hr_pen); p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(cx - R - 6), int(cy - R - 6),
                          int((R+6)*2), int((R+6)*2))

        # ── ON-state: outer plasma aura ───────────────────────────────
        if self._on:
            aura_r = R + 18 + 4 * math.sin(self._pulse)
            aura = QRadialGradient(cx, cy, aura_r)
            aura.setColorAt(0.0, QColor(168, 85, 247, 0))
            aura.setColorAt(0.45, QColor(168, 85, 247, int(38 * pulse)))
            aura.setColorAt(0.72, QColor(220, 60, 255, int(22 * pulse)))
            aura.setColorAt(1.0,  QColor(168, 85, 247, 0))
            p.setPen(Qt.NoPen); p.setBrush(aura)
            p.drawEllipse(int(cx - aura_r), int(cy - aura_r),
                          int(aura_r * 2), int(aura_r * 2))

            # Three plasma rings at different radii, speeds, styles
            for ring_r, spd, alpha, dash in [
                (R + 9,  1.0,  80, True),
                (R + 14, -0.65, 55, True),
                (R + 19,  0.38, 35, False),
            ]:
                rpen = QPen(QColor(192, 132, 252, int(alpha * (0.6 + 0.4*pulse))))
                rpen.setWidthF(1.3)
                if dash: rpen.setStyle(Qt.DashLine)
                p.setPen(rpen); p.setBrush(Qt.NoBrush)
                p.save()
                p.translate(cx, cy)
                p.rotate(math.degrees(self._ring_phase * spd))
                p.drawEllipse(int(-ring_r), int(-ring_r), int(ring_r*2), int(ring_r*2))
                p.restore()

            # Five orbiting spark dots
            for si in range(5):
                sa  = self._spark_phase + si * (2*PI/5)
                sr  = R + 11 + 3 * math.sin(self._pulse + si)
                sx  = cx + sr * math.cos(sa)
                sy  = cy + sr * math.sin(sa)
                dot_a = int(180 + 60 * math.sin(self._pulse + si*1.2))
                sc  = QRadialGradient(sx, sy, 5)
                sc.setColorAt(0,   QColor(248, 200, 255, dot_a))
                sc.setColorAt(0.5, QColor(192, 100, 255, dot_a // 2))
                sc.setColorAt(1,   QColor(140, 40, 220, 0))
                p.setPen(Qt.NoPen); p.setBrush(sc)
                p.drawEllipse(int(sx-5), int(sy-5), 10, 10)

        # ── Main sphere ───────────────────────────────────────────────
        # Radial gradient: off-centre highlight for 3-D gloss effect
        sphere = QRadialGradient(cx - R*0.35, cy - R*0.35, R * 1.55)
        if self._on:
            sphere.setColorAt(0.0,  QColor(248, 220, 255))
            sphere.setColorAt(0.18, QColor(210, 130, 255))
            sphere.setColorAt(0.50, QColor(140,  45, 255))
            sphere.setColorAt(0.82, QColor( 80,  10, 180))
            sphere.setColorAt(1.0,  QColor( 30,   4,  80))
        else:
            sphere.setColorAt(0.0,  QColor( 60,  35,  90))
            sphere.setColorAt(0.30, QColor( 28,  16,  55))
            sphere.setColorAt(0.70, QColor( 16,   8,  32))
            sphere.setColorAt(1.0,  QColor(  8,   3,  18))

        # Subtle hover brightening on OFF state
        if not self._on and hg > 0.01:
            sphere2 = QRadialGradient(cx - R*0.35, cy - R*0.35, R * 1.55)
            sphere2.setColorAt(0.0,  QColor( 90, 55, 130, int(120*hg)))
            sphere2.setColorAt(1.0,  QColor(  0,  0,   0, 0))

        # Rim / border
        rim_col = QColor(210, 140, 255) if self._on else QColor(60, 30, 100)
        if self._on:
            rim_alpha = int(200 + 55 * pulse)
            rim_col.setAlpha(rim_alpha)
        rim_pen = QPen(rim_col)
        rim_pen.setWidthF(2.2 if self._on else 1.4)

        p.setPen(rim_pen); p.setBrush(sphere)
        p.drawEllipse(int(cx - R), int(cy - R), int(R*2), int(R*2))

        # Hover overlay on OFF state
        if not self._on and hg > 0.01:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(120, 60, 200, int(30 * hg)))
            p.drawEllipse(int(cx-R), int(cy-R), int(R*2), int(R*2))

        # Inner gloss highlight — top-left bright crescent
        gloss = QRadialGradient(cx - R*0.3, cy - R*0.4, R * 0.55)
        gloss_a = int((160 if self._on else 60) * (1 + 0.3*pulse if self._on else 1))
        gloss.setColorAt(0.0, QColor(255, 245, 255, gloss_a))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(gloss); p.setPen(Qt.NoPen)
        p.drawEllipse(int(cx-R), int(cy-R), int(R*2), int(R*2))

        # ── Power icon ────────────────────────────────────────────────
        arc_r = int(R * 0.42)
        icon_col = QColor(255, 255, 255, 220) if self._on else QColor(130, 80, 190, 160)
        ic = QPen(icon_col)
        ic.setWidthF(2.8 if self._on else 2.0)
        ic.setCapStyle(Qt.RoundCap)
        p.setPen(ic); p.setBrush(Qt.NoBrush)

        # Arc (leave gap at top for the stem)
        p.drawArc(int(cx - arc_r), int(cy - arc_r + 3),
                  arc_r * 2, arc_r * 2, 50 * 16, 260 * 16)
        # Stem
        stem_top = int(cy - arc_r - 5)
        stem_bot = int(cy - arc_r + 6)
        p.drawLine(int(cx), stem_top, int(cx), stem_bot)

        p.end()


# ── Scan indicator ─────────────────────────────────────────────────────────
class ScanIndicator(QWidget):
    """Animated vault integrity indicator shown in the title bar."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(20, 20)
        self._status = "idle"
        self._angle  = 0.0
        self._pulse  = 0.0
        self._timer  = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        self._angle = (self._angle + 4.5) % 360
        self._pulse = (self._pulse + 0.08) % (2 * 3.14159)
        self.update()

    def set_scanning(self, v):
        if v:
            self._timer.start()
        else:
            self._timer.stop()
            self.update()

    def set_status(self, s):
        self._status = s
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W = H = self.width()
        cx = cy = W / 2.0
        r = W / 2.0 - 2

        pulse = 0.5 + 0.5 * math.sin(self._pulse)

        if self._status == "scanning":
            # Dark track ring
            tp = QPen(QColor(80, 20, 160, 60)); tp.setWidthF(2.2)
            p.setPen(tp); p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(cx-r), int(cy-r), int(r*2), int(r*2))
            # Spinning bright arc
            sp = QPen(QColor(168, 85, 247, 220)); sp.setWidthF(2.2)
            sp.setCapStyle(Qt.RoundCap)
            p.setPen(sp)
            p.drawArc(int(cx-r), int(cy-r), int(r*2), int(r*2),
                      int(-self._angle * 16), 270 * 16)
            # Centre dot
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(192, 100, 255, int(140 + 80 * pulse)))
            p.drawEllipse(int(cx-2), int(cy-2), 4, 4)

        elif self._status == "ok":
            # Pulsing green ring
            a = int(160 + 80 * pulse)
            gp = QPen(QColor(34, 197, 94, a)); gp.setWidthF(2.0)
            p.setPen(gp); p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(cx-r), int(cy-r), int(r*2), int(r*2))
            # Check mark
            p.setPen(QPen(QColor(34, 197, 94, a), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(int(cx-3), int(cy+1), int(cx-1), int(cy+3))
            p.drawLine(int(cx-1), int(cy+3), int(cx+4), int(cy-3))

        elif self._status == "warn":
            # Red pulsing ring
            a = int(160 + 80 * pulse)
            rp = QPen(QColor(239, 68, 68, a)); rp.setWidthF(2.0)
            p.setPen(rp); p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(cx-r), int(cy-r), int(r*2), int(r*2))
            # ! mark
            p.setPen(QPen(QColor(239, 68, 68, a), 2.0, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(cx), int(cy-4), int(cx), int(cy+1))
            p.drawPoint(int(cx), int(cy+4))

        else:  # idle
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(60, 30, 100, 80))
            p.drawEllipse(int(cx-r), int(cy-r), int(r*2), int(r*2))

        p.end()



# ── Password view dialog — matches edit dialog style exactly ───────────────
class PasswordViewDialog(QDialog):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.setWindowTitle("View Entry")
        self.setFixedWidth(400)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("fluxDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 26)
        layout.setSpacing(12)

        # Header row — site avatar + name
        hdr_row = QHBoxLayout(); hdr_row.setSpacing(12)
        _site = entry.get("site", "?")
        _h = int(hashlib.md5(_site.encode()).hexdigest()[:6], 16)
        _hue1 = _h % 360
        _hue2 = (_hue1 + 40) % 360
        def _hsl(h, s=70, l=45):
            r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        _c1, _c2 = _hsl(_hue1), _hsl(_hue2)
        av = QLabel(_site[:1].upper()); av.setFixedSize(36, 36); av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {_c1},stop:1 {_c2});"
            "border-radius:9px;color:white;font-weight:800;font-size:14px;"
        )
        site_col = QVBoxLayout(); site_col.setSpacing(2)
        s1 = QLabel(_site); s1.setStyleSheet("color:white;font-size:14px;font-weight:700;letter-spacing:0.3px;")
        s2 = QLabel(entry.get("username", "")); s2.setStyleSheet("color:#5A4070;font-size:11px;")
        site_col.addWidget(s1); site_col.addWidget(s2)
        hdr_row.addWidget(av); hdr_row.addLayout(site_col); hdr_row.addStretch()
        layout.addLayout(hdr_row)

        # Divider
        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#1C1438;max-height:1px;border:none;")
        layout.addWidget(div)

        # Username field (read-only)
        user_lbl = QLabel("USERNAME")
        user_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(user_lbl)
        self._user_field = QLineEdit(entry.get("username", ""))
        self._user_field.setReadOnly(True)
        self._user_field.setFixedHeight(40)
        self._user_field.setStyleSheet(
            "QLineEdit{background:#110e20;border:1px solid #261840;border-radius:9px;"
            "padding:0 14px;color:#c4b4d8;font-size:13px;}"
        )
        layout.addWidget(self._user_field)

        # Password field (read-only, hidden by default)
        pwd_lbl = QLabel("PASSWORD")
        pwd_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(pwd_lbl)
        self._pwd_field = QLineEdit(entry.get("password", ""))
        self._pwd_field.setReadOnly(True)
        self._pwd_field.setEchoMode(QLineEdit.Password)
        self._pwd_field.setFixedHeight(40)
        self._pwd_field.setStyleSheet(
            "QLineEdit{background:#110e20;border:1px solid #261840;border-radius:9px;"
            "padding:0 14px;color:#c084fc;"
            "font-family:'JetBrains Mono','Consolas',monospace;font-size:14px;letter-spacing:2px;}"
            "QLineEdit:focus{border-color:#7C3AED;}"
        )
        layout.addWidget(self._pwd_field)

        # Show/Hide toggle
        self._show_btn = QPushButton("Show Password")
        self._show_btn.setFixedHeight(34); self._show_btn.setCursor(Qt.PointingHandCursor)
        self._show_btn.setStyleSheet(
            "QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;"
            "border-radius:8px;font-size:11px;}"
            "QPushButton:hover{color:#8B5CF6;border-color:#7C3AED;}"
        )
        self._showing = False
        self._show_btn.clicked.connect(self._toggle_show)
        layout.addWidget(self._show_btn)

        layout.addSpacing(4)

        # Copy + Close buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self._copy_btn = QPushButton("Copy Password")
        close_btn = QPushButton("Close")
        for b in (self._copy_btn, close_btn):
            b.setFixedHeight(42); b.setCursor(Qt.PointingHandCursor)
        self._copy_btn.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:10px;font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )
        close_btn.setStyleSheet(
            "QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;"
            "border-radius:10px;font-weight:600;font-size:13px;}"
            "QPushButton:hover{color:white;border-color:#7C3AED;}"
        )
        self._copy_btn.clicked.connect(self._copy)
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._copy_btn); btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._password = entry.get("password", "")

    def _toggle_show(self):
        self._showing = not self._showing
        self._pwd_field.setEchoMode(
            QLineEdit.Normal if self._showing else QLineEdit.Password
        )
        self._show_btn.setText("Hide Password" if self._showing else "Show Password")

    def _copy(self):
        QApplication.clipboard().setText(self._password)
        old = self._copy_btn.text()
        self._copy_btn.setText("Copied ✓")
        self._copy_btn.setStyleSheet(
            "QPushButton{background:#0d1f14;color:#4ade80;"
            "border:1px solid #166534;border-radius:10px;"
            "font-weight:700;font-size:13px;}"
        )
        QTimer.singleShot(1500, lambda: (
            self._copy_btn.setText(old),
            self._copy_btn.setStyleSheet(
                "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #6D28D9,stop:1 #8B5CF6);"
                "color:white;border:none;border-radius:10px;font-weight:700;font-size:13px;}"
                "QPushButton:hover{background:#7C3AED;}"
            )
        ))


# ── Vault row ──────────────────────────────────────────────────────────────


# ── Vault entry metadata (pin + order) — sidecar JSON ────────────────────────
class VaultMeta:
    """
    Persists pin flags and custom sort order for vault entries.
    Keyed by (site, username) tuples so it survives vault re-encryption.
    Stored next to VAULT_FILE as  fluxkey_vault_meta_{profile_id}.json
    """
    def __init__(self):
        self._data: dict = {}   # { "site\x00user": {"pinned": bool, "order": int} }
        self._path: str  = ""
        self._load()

    def _get_path(self) -> str:
        try:
            pid  = get_current_profile_id()
        except Exception:
            pid  = "default"
        return os.path.join(os.path.dirname(VAULT_FILE),
                            f"fluxkey_vault_meta_{pid}.json")

    def _load(self):
        self._path = self._get_path()
        try:
            with open(self._path) as f:
                self._data = json.load(f)
        except Exception:
            self._data = {}

    def _save(self):
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _key(entry: dict) -> str:
        return f"{entry.get('site','')}\x00{entry.get('username','')}"

    def is_pinned(self, entry: dict) -> bool:
        return self._data.get(self._key(entry), {}).get("pinned", False)

    def set_pinned(self, entry: dict, pinned: bool):
        k = self._key(entry)
        if k not in self._data:
            self._data[k] = {}
        self._data[k]["pinned"] = pinned
        self._save()

    def is_group_pinned(self, gid: str) -> bool:
        return self._data.get(f"__group__{gid}", {}).get("pinned", False)

    def set_group_pinned(self, gid: str, pinned: bool):
        k = f"__group__{gid}"
        if k not in self._data:
            self._data[k] = {}
        self._data[k]["pinned"] = pinned
        self._save()

    def get_order(self, entry: dict) -> int:
        return self._data.get(self._key(entry), {}).get("order", 9999)

    def set_order(self, entry: dict, order: int):
        k = self._key(entry)
        if k not in self._data:
            self._data[k] = {}
        self._data[k]["order"] = order
        self._save()

    def sort_entries(self, indexed_entries: list) -> list:
        """Sort (real_idx, entry) list: pinned first, then by custom order, then original index."""
        def _key(item):
            _, e = item
            pinned = 0 if self.is_pinned(e) else 1
            order  = self.get_order(e)
            return (pinned, order)
        return sorted(indexed_entries, key=_key)

    def move_up(self, entry: dict, all_entries: list):
        """Shift this entry one position up in its group."""
        sorted_e = self.sort_entries([(i, e) for i, e in all_entries])
        keys = [self._key(e) for _, e in sorted_e]
        k = self._key(entry)
        idx = keys.index(k) if k in keys else -1
        if idx > 0:
            # Swap orders with the item above
            above_entry = sorted_e[idx - 1][1]
            o1 = self.get_order(entry)
            o2 = self.get_order(above_entry)
            self.set_order(entry, min(o1, o2) - 1)
            self._save()

    def move_down(self, entry: dict, all_entries: list):
        """Shift this entry one position down in its group."""
        sorted_e = self.sort_entries([(i, e) for i, e in all_entries])
        keys = [self._key(e) for _, e in sorted_e]
        k = self._key(entry)
        idx = keys.index(k) if k in keys else -1
        if 0 <= idx < len(sorted_e) - 1:
            below_entry = sorted_e[idx + 1][1]
            o1 = self.get_order(entry)
            o2 = self.get_order(below_entry)
            self.set_order(entry, max(o1, o2) + 1)
            self._save()


class VaultRow(QFrame):
    """
    Premium vault entry card — v5 redesign.
    - Taller card (80px) with breathing room
    - Thick left accent bar (6px) with colour derived from site name
    - Rounded avatar with gloss highlight
    - Site name bold white, username dimmed
    - Right-side: minimal icon-only action buttons revealed on chevron click
    - Action tray: 6 slim rounded icon buttons, no text labels cluttering them
    - Hover: soft purple glow emanates from left accent
    - Open: accent brightens, info panel slides left, tray slides in from right
    """

    BTN_W = 300   # tray width when open (wider for extra buttons)

    def __init__(self, index, entry, vault, refresh_cb, meta=None, all_members=None):
        super().__init__()
        self._index      = index
        self._entry      = entry
        self._vault      = vault
        self._refresh    = refresh_cb
        self._meta       = meta
        self._all_members = all_members or []
        self._open       = False
        self._pinned     = meta.is_pinned(entry) if meta else False
        self.setObjectName("vaultRow")
        self.setFixedHeight(76)

        # Hover animation
        self._hover_glow  = 0.0
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(25)
        self._hover_timer.timeout.connect(self._tick_hover)
        self._hovering    = False

        # ── Derive unique colours from site name ──────────────────────
        # ── Derive unique colours from site name ──────────────────────
        _site = entry.get("site", "?")
        _h    = int(hashlib.md5(_site.encode()).hexdigest()[:6], 16)
        _hue1 = _h % 360
        _hue2 = (_hue1 + 42) % 360

        def _hsl(h, s=0.70, l=0.48):
            r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
            return (int(r * 255), int(g * 255), int(b * 255))

        self._rgb1 = _hsl(_hue1)
        self._rgb2 = _hsl(_hue2)
        r1,g1,b1  = self._rgb1
        r2,g2,b2  = self._rgb2
        _c1 = f"#{r1:02x}{g1:02x}{b1:02x}"
        _c2 = f"#{r2:02x}{g2:02x}{b2:02x}"

        # ── Thick accent bar (left edge, 6px) ─────────────────────────
        self._accent = QWidget(self)
        self._accent.setGeometry(0, 0, 6, 76)
        self._accent.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {_c1},stop:1 {_c2});"
            "border-top-left-radius:15px;border-bottom-left-radius:15px;"
        )
        self._accent.raise_()

        # ── Info widget (left side) ───────────────────────────────────
        self._info_w = QWidget(self)
        info_l = QHBoxLayout(self._info_w)
        info_l.setContentsMargins(18, 0, 10, 0)
        info_l.setSpacing(14)

        # Avatar circle — letter + gradient background
        fav_wrap = QWidget()
        fav_wrap.setFixedSize(46, 46)
        fav_wrap.setStyleSheet("background:transparent;")
        fav = QLabel(_site[:1].upper(), fav_wrap)
        fav.setGeometry(0, 0, 46, 46)
        fav.setAlignment(Qt.AlignCenter)
        fav.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {_c1},stop:1 {_c2});"
            "border-radius:14px;color:white;font-weight:900;font-size:18px;"
            "font-family:'Outfit','Segoe UI',sans-serif;border:none;"
        )
        # Gloss highlight overlay
        gloss = QLabel(fav_wrap)
        gloss.setGeometry(4, 3, 22, 18)
        gloss.setStyleSheet(
            "background:rgba(255,255,255,0.15);"
            "border-radius:7px;border:none;"
        )
        gloss.setAttribute(Qt.WA_TransparentForMouseEvents)
        info_l.addWidget(fav_wrap)

        # Text block — site name + username
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setContentsMargins(0, 0, 0, 0)

        site_row = QHBoxLayout(); site_row.setSpacing(5); site_row.setContentsMargins(0,0,0,0)
        site_lbl = QLabel(_site)
        site_lbl.setStyleSheet(
            "color:#f2eeff;font-weight:700;font-size:13px;"
            "background:transparent;border:none;letter-spacing:0.3px;"
        )
        self._pin_badge = QLabel("📌")
        self._pin_badge.setStyleSheet("font-size:10px;background:transparent;border:none;")
        self._pin_badge.setVisible(self._pinned)
        site_row.addWidget(site_lbl)
        site_row.addWidget(self._pin_badge)
        site_row.addStretch()

        _user = entry.get("username", "")
        user_lbl = QLabel(_user if _user else "No username set")
        user_lbl.setStyleSheet(
            "color:#4a3870;font-size:11px;background:transparent;border:none;"
        )
        text_col.addLayout(site_row)
        text_col.addWidget(user_lbl)
        info_l.addLayout(text_col)
        info_l.addStretch()

        # AES badge — compact
        enc_badge = QLabel("AES-256")
        enc_badge.setFixedHeight(18)
        enc_badge.setAlignment(Qt.AlignCenter)
        enc_badge.setStyleSheet(
            "color:#6b2fe0;font-size:7px;font-weight:800;letter-spacing:1.5px;"
            "background:rgba(107,47,224,0.10);border:1px solid rgba(107,47,224,0.25);"
            "border-radius:4px;padding:0 5px;"
        )
        info_l.addWidget(enc_badge, 0, Qt.AlignVCenter)
        info_l.addSpacing(6)

        # Chevron — slim, pill-shaped
        self._chev = QPushButton("›")
        self._chev.setFixedSize(28, 28)
        self._chev.setCursor(Qt.PointingHandCursor)
        self._chev.setStyleSheet(
            "QPushButton{background:rgba(123,47,255,0.10);color:#5a3888;"
            "border:1px solid rgba(109,40,217,0.18);border-radius:8px;"
            "font-size:16px;font-weight:700;padding-bottom:1px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.22);color:#c084fc;"
            "border-color:rgba(139,92,246,0.5);}"
        )
        self._chev.clicked.connect(self._toggle)
        info_l.addWidget(self._chev, 0, Qt.AlignVCenter)

        # ── Action tray (right side, hidden until open) ───────────────
        self._tray = QWidget(self)
        tray_l = QHBoxLayout(self._tray)
        tray_l.setContentsMargins(6, 10, 8, 10)
        tray_l.setSpacing(5)

        def _mk_btn(icon, fn, danger=False):
            """Slim icon-only square button with rounded corners."""
            b = QPushButton(icon)
            b.setFixedSize(34, 34) if not danger else b.setFixedSize(36, 34)
            b.setCursor(Qt.PointingHandCursor)
            if danger:
                b.setStyleSheet(
                    "QPushButton{background:rgba(180,20,45,0.12);"
                    "color:#c06070;border:1px solid rgba(200,30,55,0.25);"
                    "border-radius:9px;font-size:15px;}"
                    "QPushButton:hover{background:rgba(220,30,60,0.30);"
                    "color:#ff8898;border-color:rgba(255,50,80,0.55);}"
                )
            else:
                b.setStyleSheet(
                    "QPushButton{background:rgba(100,40,200,0.10);"
                    "color:#9070c8;border:1px solid rgba(123,47,255,0.20);"
                    "border-radius:9px;font-size:15px;}"
                    "QPushButton:hover{background:rgba(150,70,255,0.24);"
                    "color:#e0c8ff;border-color:rgba(180,100,255,0.55);}"
                )
            b.clicked.connect(fn)
            return b

        for icon, fn, danger in [
            ("👁",  self._view,      False),
            ("👤",  self._copy_user, False),
            ("📋",  self._copy,      False),
            ("✏️",  self._edit,      False),
            ("📂",  self._move,      False),
            ("🗑",  self._delete,    True),
        ]:
            tray_l.addWidget(_mk_btn(icon, fn, danger))

        # ── Slide animations ──────────────────────────────────────────
        self._tray_anim = QPropertyAnimation(self._tray, b"geometry")
        self._tray_anim.setDuration(200)
        self._tray_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._info_anim = QPropertyAnimation(self._info_w, b"geometry")
        self._info_anim.setDuration(200)
        self._info_anim.setEasingCurve(QEasingCurve.OutCubic)

    # ── Geometry ──────────────────────────────────────────────────────────

    def resizeEvent(self, e):
        super().resizeEvent(e)
        h = self.height(); w = self.width()
        self._accent.setGeometry(0, 0, 6, h)
        if self._open:
            self._tray.setGeometry(0, 0, w, h)
            self._info_w.setVisible(False)
        else:
            self._tray.setGeometry(w, 0, self.BTN_W, h)
            self._info_w.setGeometry(0, 0, w, h)
            self._info_w.setVisible(True)

    def _toggle(self):
        self._open = not self._open
        self._chev.setText("‹" if self._open else "›")
        w = self.width(); h = self.height()

        # Brighten accent strip when open
        _site = self._entry.get("site", "?")
        _h2   = int(hashlib.md5(_site.encode()).hexdigest()[:6], 16)
        _hue1 = _h2 % 360
        _hue2 = (_hue1 + 42) % 360
        def _hsl2(h, s=0.70, l=0.44):
            r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        l_val = 0.62 if self._open else 0.48
        c1 = _hsl2(_hue1, l=l_val)
        c2 = _hsl2(_hue2, l=l_val)
        self._accent.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {c1},stop:1 {c2});"
            "border-top-left-radius:15px;border-bottom-left-radius:15px;"
        )

        if self._open:
            self._info_w.setVisible(False)
            self._tray_anim.setStartValue(self._tray.geometry())
            self._tray_anim.setEndValue(QRect(0, 0, w, h))
        else:
            self._info_w.setVisible(True)
            self._tray_anim.setStartValue(self._tray.geometry())
            self._tray_anim.setEndValue(QRect(w, 0, self.BTN_W, h))
            self._info_anim.setStartValue(self._info_w.geometry())
            self._info_anim.setEndValue(QRect(0, 0, w, h))
        self._tray_anim.start()
        if not self._open:
            self._info_anim.start()

    def _tick_hover(self):
        target = 1.0 if self._hovering else 0.0
        self._hover_glow += (target - self._hover_glow) * 0.14
        if abs(self._hover_glow - target) < 0.01:
            self._hover_glow = target
            self._hover_timer.stop()
        self.update()

    def enterEvent(self, e):
        super().enterEvent(e)
        self._hovering = True; self._hover_timer.start()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self._hovering = False; self._hover_timer.start()
        if self._open: self._toggle()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._hover_glow < 0.01: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r1,g1,b1 = self._rgb1
        # Accent side glow — fans out from left edge
        glow = QLinearGradient(0, 0, 40, 0)
        glow.setColorAt(0.0, QColor(r1, g1, b1, int(100 * self._hover_glow)))
        glow.setColorAt(1.0, QColor(r1, g1, b1, 0))
        p.setPen(Qt.NoPen); p.setBrush(glow)
        p.drawRoundedRect(0, 0, 40, self.height(), 15, 15)
        p.end()

    # ── Actions ───────────────────────────────────────────────────────────

    def _toggle_pin(self):
        if not self._meta:
            return
        self._pinned = not self._pinned
        self._meta.set_pinned(self._entry, self._pinned)
        self._pin_badge.setVisible(self._pinned)
        self._pin_btn.setText("📍" if self._pinned else "📌")
        self._refresh()

    def _move_up(self):
        if self._meta:
            self._meta.move_up(self._entry, self._all_members)
            self._refresh()

    def _move_down(self):
        if self._meta:
            self._meta.move_down(self._entry, self._all_members)
            self._refresh()

    def _view(self):
        dlg = PasswordViewDialog(self._entry, self); dlg.exec()

    def _copy_user(self):
        QApplication.clipboard().setText(self._entry.get("username", ""))

    def _copy(self):
        QApplication.clipboard().setText(self._entry.get("password", ""))

    def _edit(self):
        dlg = EditEntryDialog(self._entry, self)
        if dlg.exec() == QDialog.Accepted:
            s, u, pw = dlg.get_values()
            self._vault.update_entry(self._index, s, u, pw)
            self._refresh()

    def _move(self):
        dlg = MoveVaultDialog(self._index, self._entry, self._vault, self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh()

    def _delete(self):
        box = QMessageBox(self)
        box.setWindowTitle("Delete Entry")
        box.setText(f"Delete '{self._entry.get('site', '')}' from vault?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        _style_msgbox(box)
        if box.exec() == QMessageBox.Yes:
            self._vault.delete_entry(self._index)
            self._refresh()

# ── Edit entry dialog ──────────────────────────────────────────────────────
class EditEntryDialog(QDialog):
    def __init__(self,entry,parent=None):
        super().__init__(parent); self.setWindowTitle("Edit Entry"); self.setFixedWidth(380)
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint); self.setObjectName("fluxDialog")
        layout=QVBoxLayout(self); layout.setContentsMargins(26,22,26,26); layout.setSpacing(12)
        hdr=QLabel("Edit Vault Entry"); hdr.setStyleSheet("color:#8B5CF6;font-size:14px;font-weight:700;letter-spacing:2px;"); layout.addWidget(hdr)
        self._site=QLineEdit(entry.get("site","")); self._site.setPlaceholderText("Website / App"); self._site.setFixedHeight(40)
        self._user=QLineEdit(entry.get("username","")); self._user.setPlaceholderText("Username / Email"); self._user.setFixedHeight(40)
        self._pwd=QLineEdit(entry.get("password","")); self._pwd.setPlaceholderText("Password"); self._pwd.setEchoMode(QLineEdit.Password); self._pwd.setFixedHeight(40)
        show_btn=QPushButton("Show / Hide"); show_btn.setFixedHeight(34); show_btn.setCursor(Qt.PointingHandCursor)
        show_btn.setStyleSheet("QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;border-radius:8px;font-size:11px;}QPushButton:hover{color:#8B5CF6;border-color:#7C3AED;}")
        show_btn.clicked.connect(lambda:self._pwd.setEchoMode(QLineEdit.Normal if self._pwd.echoMode()==QLineEdit.Password else QLineEdit.Password))
        for w in (self._site,self._user,self._pwd,show_btn): layout.addWidget(w)
        layout.addSpacing(6)
        btn_row=QHBoxLayout(); btn_row.setSpacing(10)
        cancel=QPushButton("Cancel"); save=QPushButton("Save Changes")
        for b in (cancel,save): b.setFixedHeight(40); b.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7C3AED,stop:1 #8B5CF6);color:white;border:none;border-radius:9px;font-weight:700;}QPushButton:hover{background:#8b5cf6;}")
        cancel.setStyleSheet("QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;border-radius:9px;font-weight:600;}QPushButton:hover{color:white;border-color:#7C3AED;}")
        cancel.clicked.connect(self.reject); save.clicked.connect(self.accept)
        btn_row.addWidget(cancel); btn_row.addWidget(save); layout.addLayout(btn_row)

    def get_values(self): return self._site.text(),self._user.text(),self._pwd.text()


# ── Settings dialog ────────────────────────────────────────────────────────



class SettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedWidth(460)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14,14,14,14)

        # One unified card — no detached header pill
        card = QWidget()
        card.setStyleSheet(
            "QWidget#settingsCard{"
            "background:#0F0D1E;"
            "border:1px solid rgba(109,40,217,0.4);"
            "border-radius:18px;}"
        )
        card.setObjectName("settingsCard")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(0,0,0,0)
        card_l.setSpacing(0)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(46); shadow.setOffset(0,5)
        shadow.setColor(QColor(109,40,217,150))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        # ── Header — flush inside card, same radius ───────────────────
        hdr = QWidget()
        hdr.setFixedHeight(62)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1A1428,stop:1 #0F0D1E);"
            "border-top-left-radius:17px;border-top-right-radius:17px;"
            "border-bottom:1px solid rgba(109,40,217,0.18);"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,16,0); hl.setSpacing(12)

        badge = QLabel("FK"); badge.setFixedSize(36,36); badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "border-radius:10px;color:white;"
            "font-size:12px;font-weight:800;letter-spacing:0.5px;"
            "border:none;"
        )

        title = QLabel("Settings")
        title.setStyleSheet(
            "color:white;font-size:16px;font-weight:800;"
            "letter-spacing:2px;background:transparent;border:none;"
        )

        xbtn = QPushButton("✕"); xbtn.setFixedSize(32,32)
        xbtn.setCursor(Qt.PointingHandCursor)
        xbtn.setStyleSheet(
            "QPushButton{background:transparent;color:#4A3370;"
            "border:none;font-size:14px;border-radius:9px;font-weight:700;}"
            "QPushButton:hover{background:#ff2d6f;color:white;}"
        )
        xbtn.clicked.connect(self.reject)
        hl.addWidget(badge); hl.addSpacing(2); hl.addWidget(title)
        hl.addStretch(); hl.addWidget(xbtn)
        card_l.addWidget(hdr)

        # Gradient divider
        rule = QFrame(); rule.setFixedHeight(1)
        rule.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(109,40,217,0.5),stop:0.6 rgba(109,40,217,0.14),"
            "stop:1 transparent);border:none;"
        )
        card_l.addWidget(rule)

        # ── Scroll area ───────────────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(520)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
            "QScrollBar:vertical{background:transparent;width:3px;border-radius:2px;}"
            "QScrollBar::handle:vertical{background:#2A1F45;border-radius:2px;min-height:20px;}"
            "QScrollBar::handle:vertical:hover{background:#7C3AED;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(20,20,20,24); bl.setSpacing(16)


        # ── SECURITY ─────────────────────────────────────────────────
        bl.addWidget(self._slbl("SECURITY"))

        sec = self._card_frame()
        sc = QVBoxLayout(sec); sc.setContentsMargins(18,16,18,16); sc.setSpacing(16)

        # Auto-lock row
        lr = QHBoxLayout(); lr.setSpacing(0)
        ll = QLabel("Auto-lock after")
        ll.setStyleSheet("color:#c4b4d8;font-size:13px;font-weight:600;background:transparent;border:none;")
        self._lock_combo = self._cmb(["Disabled","1 min","5 min","10 min","30 min"])
        mins_map = {0:0,1:1,2:5,3:10,4:30}
        cur_mins = get_auto_lock_minutes()
        for k,v in mins_map.items():
            if v==cur_mins: self._lock_combo.setCurrentIndex(k); break
        self._lock_combo.currentIndexChanged.connect(lambda i: set_auto_lock_minutes(mins_map.get(i,0)))
        lr.addWidget(ll); lr.addStretch(); lr.addWidget(self._lock_combo)
        sc.addLayout(lr)

        sep = QFrame(); sep.setObjectName("s1"); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("QFrame#s1{background:rgba(109,40,217,0.12);max-height:1px;border:none;}")
        sc.addWidget(sep)

        # Clipboard row
        cr = QHBoxLayout(); cr.setSpacing(0)
        cl = QVBoxLayout(); cl.setSpacing(3)
        cla = QLabel("Auto-clear clipboard")
        cla.setStyleSheet("color:#c4b4d8;font-size:13px;font-weight:600;background:transparent;border:none;")
        clb = QLabel("Clears copied passwords after 30 seconds")
        clb.setStyleSheet("color:#3D2A58;font-size:10px;background:transparent;border:none;")
        cl.addWidget(cla); cl.addWidget(clb)
        from core.vault import _load_config
        cfg = _load_config()
        self._clip_tog = self._tog(cfg.get("auto_clear_clipboard",True))
        self._clip_tog.clicked.connect(self._do_clip)
        cr.addLayout(cl); cr.addStretch(); cr.addWidget(self._clip_tog)
        sc.addLayout(cr)
        bl.addWidget(sec)

        bl.addWidget(self._slbl("CHANGE MASTER PASSWORD"))

        pw = self._card_frame()
        pc = QVBoxLayout(pw); pc.setContentsMargins(18,16,18,16); pc.setSpacing(10)
        self._cur  = self._fld("Current password")
        self._new1 = self._fld("New password")
        self._new2 = self._fld("Confirm new password")
        self._pmsg = QLabel(""); self._pmsg.setFixedHeight(15)
        self._pmsg.setStyleSheet("font-size:11px;background:transparent;border:none;padding-left:2px;")
        for w in (self._cur,self._new1,self._new2,self._pmsg): pc.addWidget(w)
        upd = QPushButton("Update Password"); upd.setFixedHeight(44)
        upd.setCursor(Qt.PointingHandCursor)
        upd.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:12px;"
            "font-weight:700;font-size:13px;letter-spacing:0.5px;}"
            "QPushButton:hover{background:#7C3AED;}"
            "QPushButton:pressed{background:#4a1aaa;}"
        )
        upd.clicked.connect(self._chpw); pc.addWidget(upd)
        bl.addWidget(pw)

        # ── DANGER ZONE ───────────────────────────────────────────────
        bl.addWidget(self._slbl("DANGER ZONE", danger=True))

        dz = QFrame(); dz.setObjectName("dzCard")
        dz.setStyleSheet(
            "QFrame#dzCard{background:rgba(220,20,50,0.06);"
            "border:1px solid rgba(220,30,60,0.2);"
            "border-radius:14px;}"
            "QFrame#dzCard QLabel{background:transparent;border:none;}"
        )
        dzl = QVBoxLayout(dz); dzl.setContentsMargins(18,16,18,16); dzl.setSpacing(12)
        wr = QHBoxLayout(); wr.setSpacing(12)
        wi = QLabel("!"); wi.setFixedSize(30,30); wi.setAlignment(Qt.AlignCenter)
        wi.setStyleSheet(
            "background:rgba(220,30,60,0.12);border:1px solid rgba(220,30,60,0.3);"
            "border-radius:9px;color:#f87171;font-weight:800;font-size:14px;"
        )
        wt = QLabel("Permanently deletes all passwords and your master password. Cannot be undone.")
        wt.setWordWrap(True)
        wt.setStyleSheet("color:#5A4060;font-size:11px;line-height:1.5;background:transparent;border:none;")
        wr.addWidget(wi,0,Qt.AlignTop); wr.addWidget(wt); dzl.addLayout(wr)
        wipe = QPushButton("Wipe Vault and Reset Everything"); wipe.setFixedHeight(44)
        wipe.setCursor(Qt.PointingHandCursor)
        wipe.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.25);border-radius:12px;"
            "font-weight:700;font-size:12px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;border-color:#ff2d6f;}"
            "QPushButton:pressed{background:#cc1050;}"
        )
        wipe.clicked.connect(self._wipe); dzl.addWidget(wipe)
        bl.addWidget(dz)

        scroll.setWidget(body); card_l.addWidget(scroll)

    # ── Drag ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton and e.position().y()<76:
            self._drag_pos=e.globalPosition().toPoint()-self.frameGeometry().topLeft()

    def mouseMoveEvent(self,e):
        if self._drag_pos and e.buttons()==Qt.LeftButton:
            self.move(e.globalPosition().toPoint()-self._drag_pos)

    def mouseReleaseEvent(self,e): self._drag_pos=None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _card_frame(self):
        """Standard inner card with correct objectName scoping."""
        name = f"icard_{random.randint(10000, 99999)}"
        f = QFrame(); f.setObjectName(name)
        f.setStyleSheet(
            f"QFrame#{name}{{background:#16132A;"
            "border:1px solid rgba(109,40,217,0.18);border-radius:14px;}"
            f"QFrame#{name} QLabel{{background:transparent;border:none;}}"
            f"QFrame#{name} QWidget{{background:transparent;}}"
        )
        return f

    def _slbl(self, text, danger=False):
        """Section label — dot + caps text + faint hairline."""
        col = "#f87171" if danger else "#8B5CF6"
        a   = "rgba(220,30,60,0.15)" if danger else "rgba(109,40,217,0.14)"
        w = QWidget(); w.setStyleSheet("background:transparent;")
        r = QHBoxLayout(w); r.setContentsMargins(0,0,0,0); r.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(6,6)
        dot.setStyleSheet(f"background:{col};border-radius:3px;border:none;padding:0;margin:0;")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{col};font-size:10px;font-weight:700;letter-spacing:2.5px;background:transparent;border:none;")
        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{a};border:none;")
        r.addWidget(dot,0,Qt.AlignVCenter); r.addWidget(lbl,0,Qt.AlignVCenter); r.addWidget(line)
        return w

    def _fld(self, ph):
        f = QLineEdit(); f.setPlaceholderText(ph); f.setFixedHeight(44)
        f.setEchoMode(QLineEdit.Password)
        f.setStyleSheet(
            "QLineEdit{background:#0E0C1E;border:1px solid #1E1A35;"
            "border-radius:12px;padding:0 14px;color:#D4CCEE;font-size:13px;}"
            "QLineEdit:focus{border:1.5px solid #7C3AED;background:#13102A;}"
            "QLineEdit::placeholder{color:#3A2A55;}"
        )
        return f

    def _cmb(self, opts):
        from PySide6.QtWidgets import QComboBox
        c = QComboBox(); [c.addItem(o) for o in opts]
        c.setFixedHeight(38); c.setFixedWidth(120)
        c.setStyleSheet(
            "QComboBox{background:#0E0C1E;border:1px solid #1E1A35;"
            "border-radius:11px;padding:0 12px;color:#c4b4d8;font-size:12px;}"
            "QComboBox::drop-down{border:none;width:20px;}"
            "QComboBox QAbstractItemView{background:#16132A;"
            "border:1px solid #261840;color:#c4b4d8;"
            "selection-background-color:#7C3AED;outline:none;}"
        )
        return c

    def _tog(self, active):
        b = QPushButton("ON" if active else "OFF")
        b.setFixedSize(60,32); b.setCursor(Qt.PointingHandCursor)
        self._stog(b,active); return b

    def _stog(self, btn, active):
        btn.setText("ON" if active else "OFF")
        if active:
            btn.setStyleSheet(
                "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #6D28D9,stop:1 #8B5CF6);"
                "color:white;border:none;border-radius:10px;"
                "font-size:11px;font-weight:700;}"
                "QPushButton:hover{background:#7C3AED;}"
            )
        else:
            btn.setStyleSheet(
                "QPushButton{background:#110e20;color:#3D2A58;"
                "border:1px solid #1c1530;border-radius:10px;"
                "font-size:11px;font-weight:600;}"
                "QPushButton:hover{border-color:#7C3AED;color:#8B5CF6;}"
            )

    def _do_clip(self):
        from core.vault import _load_config,_save_config
        cfg=_load_config(); v=cfg.get("auto_clear_clipboard",True)
        cfg["auto_clear_clipboard"]=not v; _save_config(cfg)
        self._stog(self._clip_tog,not v)

    def _do_plus(self):
        new_val = not is_plus()
        set_plus(new_val)
        self._stog(self._plus_tog, new_val)
        # Tell parent dashboard to update PLUS UI
        if self.parent() and hasattr(self.parent(), '_refresh_plus_ui'):
            self.parent()._refresh_plus_ui()

    def _open_audit_from_settings(self):
        if not is_plus():
            box = QMessageBox(self)
            box.setWindowTitle("PLUS Feature")
            box.setText("Enable FluxKey PLUS to access the Audit Log.")
            box.exec(); return
        dlg = AuditLogDialog(self); dlg.exec()

    def _chpw(self):
        cur,n1,n2=self._cur.text(),self._new1.text(),self._new2.text()
        def st(m,ok=False):
            self._pmsg.setStyleSheet(f"color:{'#8B5CF6' if ok else '#f87171'};font-size:11px;background:transparent;border:none;padding-left:2px;")
            self._pmsg.setText(m)
        ok,msg,_=verify_master_password(cur)
        if not ok: return st(msg)
        if not n1: return st("New password cannot be empty.")
        if n1!=n2: return st("Passwords do not match.")
        if len(n1)<4: return st("Minimum 4 characters.")
        set_master_password(n1); self._cur.clear(); self._new1.clear(); self._new2.clear()
        st("Password updated.", ok=True)

    def _wipe(self):
        box=QMessageBox(self); box.setWindowTitle("Wipe Vault")
        box.setText("Permanently delete ALL vault entries and master password?\n\nThis CANNOT be undone.")
        box.setStandardButtons(QMessageBox.Yes|QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        _style_msgbox(box)
        if box.exec()==QMessageBox.Yes: wipe_all(); self.done(2)


def _style_msgbox(box):
    box.setStyleSheet(
        "QMessageBox{background:#0d0b16;}QLabel{color:#c4b4d8;font-size:13px;}"
        "QPushButton{background:#1C1438;color:#c4b4d8;border:1px solid #261840;border-radius:7px;padding:7px 20px;font-weight:600;min-width:70px;}"
        "QPushButton:hover{background:#7C3AED;color:white;border-color:#7C3AED;}"
    )


# ── Update dialog ──────────────────────────────────────────────────────────
class UpdateDialog(QDialog):
    def __init__(self,current,latest,download_url,parent=None,error=None):
        super().__init__(parent); self.setWindowTitle("FluxKey Update"); self.setFixedWidth(400)
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint); self.setObjectName("fluxDialog")
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        header=QWidget(); header.setFixedHeight(52)
        if error: header.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3a0a0a,stop:1 #1e0f0f);border-top-left-radius:14px;border-top-right-radius:14px;")
        else: header.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0d3320,stop:1 #1C1438);border-top-left-radius:14px;border-top-right-radius:14px;")
        hl=QHBoxLayout(header); hl.setContentsMargins(20,0,12,0)
        icon=QLabel("!" if error else ("NEW" if latest and latest!=current else "OK"))
        _,col={"!":("!","#ff4466"),"NEW":("NEW","#22c55e"),"OK":("OK","#8B5CF6")}.get(icon.text(),("?","#8B5CF6"))
        icon.setStyleSheet(f"color:{col};font-size:12px;font-weight:800;")
        title=QLabel("Update Check"); title.setStyleSheet("color:white;font-size:14px;font-weight:700;letter-spacing:2px;")
        close_btn=QPushButton("X"); close_btn.setFixedSize(26,26); close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:#5A4070;border:none;font-size:12px;border-radius:5px;}QPushButton:hover{background:#ff2d6f;color:white;}")
        close_btn.clicked.connect(self.reject)
        hl.addWidget(icon); hl.addSpacing(10); hl.addWidget(title); hl.addStretch(); hl.addWidget(close_btn)
        layout.addWidget(header)
        body=QWidget(); body.setObjectName("settingsBody")
        bl=QVBoxLayout(body); bl.setContentsMargins(24,22,24,24); bl.setSpacing(14)
        ver_row=QHBoxLayout(); ver_row.setSpacing(10)
        cur_badge=QLabel(f"Installed  v{current}")
        cur_badge.setStyleSheet("color:#8B5CF6;font-size:11px;font-weight:700;background:#1C1438;border:1px solid #3D2A58;border-radius:6px;padding:5px 12px;font-family:'Consolas',monospace;")
        ver_row.addWidget(cur_badge)
        if latest and latest!=current:
            arr=QLabel("  ->  "); arr.setStyleSheet("color:#3D2A58;font-size:13px;")
            lb=QLabel(f"Latest  v{latest}")
            lb.setStyleSheet("color:#22c55e;font-size:11px;font-weight:700;background:#0d1f14;border:1px solid #166534;border-radius:6px;padding:5px 12px;font-family:'Consolas',monospace;")
            ver_row.addWidget(arr); ver_row.addWidget(lb)
        ver_row.addStretch(); bl.addLayout(ver_row)
        if error:
            msg=QLabel(f"Could not reach SourceForge.\n\n{error[:120]}"); msg.setWordWrap(True); msg.setStyleSheet("color:#6b5a8a;font-size:12px;line-height:1.5;"); bl.addWidget(msg)
            ok_btn=QPushButton("Close"); ok_btn.setFixedHeight(38); ok_btn.setCursor(Qt.PointingHandCursor)
            ok_btn.setStyleSheet("QPushButton{background:#181030;color:#6A5580;border:1px solid #261840;border-radius:9px;font-weight:600;}QPushButton:hover{color:white;border-color:#7C3AED;}")
            ok_btn.clicked.connect(self.reject); bl.addWidget(ok_btn)
        elif latest is None or latest==current:
            msg=QLabel(f"You are on the latest version  v{current}." if latest==current else "Connected but could not parse version. Visit SourceForge to check manually.")
            msg.setWordWrap(True); msg.setStyleSheet("color:#6b5a8a;font-size:12px;"); bl.addWidget(msg)
            ok_btn=QPushButton("Up to date  ✓"); ok_btn.setFixedHeight(38); ok_btn.setCursor(Qt.PointingHandCursor)
            ok_btn.setStyleSheet("QPushButton{background:#0d1f14;color:#22c55e;border:1px solid #166534;border-radius:9px;font-weight:700;}QPushButton:hover{background:#166534;color:white;}")
            ok_btn.clicked.connect(self.accept); bl.addWidget(ok_btn)
        else:
            msg=QLabel(f"A new version of FluxKey is available!\n\nv{current}  ->  v{latest}\n\nClick below to download the installer from SourceForge.")
            msg.setWordWrap(True); msg.setStyleSheet("color:#9988bb;font-size:12px;line-height:1.6;"); bl.addWidget(msg)
            dl_btn=QPushButton("  Download Update"); dl_btn.setFixedHeight(44); dl_btn.setCursor(Qt.PointingHandCursor)
            dl_btn.setStyleSheet("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #14532d,stop:1 #166534);color:#4ade80;border:1px solid #22c55e;border-radius:10px;font-size:13px;font-weight:700;}QPushButton:hover{background:#22c55e;color:white;border-color:#22c55e;}")
            dl_btn.clicked.connect(lambda: (webbrowser.open(download_url), self.accept())); bl.addWidget(dl_btn)
            skip_btn=QPushButton("Skip for now"); skip_btn.setFixedHeight(34); skip_btn.setCursor(Qt.PointingHandCursor)
            skip_btn.setStyleSheet("QPushButton{background:transparent;color:#3D2A58;border:none;font-size:11px;}QPushButton:hover{color:#8B5CF6;}")
            skip_btn.clicked.connect(self.reject); bl.addWidget(skip_btn)
        layout.addWidget(body)


# ── Length Stepper ────────────────────────────────────────────────────────
# ── Length Stepper ────────────────────────────────────────────────────────
class LengthStepper(QWidget):
    """◀ [number] ▶ stepper — clean pill design with SVG chevron arrows."""

    valueChanged = Signal(int)
    MIN_VAL = 8
    MAX_VAL = 145

    def __init__(self, initial: int = 20, parent=None):
        super().__init__(parent)
        self._val = initial
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Outer pill container
        pill_style = (
            "background:rgba(109,40,217,0.12);"
            "border:1px solid rgba(109,40,217,0.30);"
            "border-radius:10px;"
        )
        self.setStyleSheet(pill_style)

        btn_style = (
            "QPushButton{background:transparent;color:#9070CC;"
            "border:none;border-radius:8px;"
            "font-size:11px;font-weight:900;padding:0;}"
            "QPushButton:hover{background:rgba(139,92,246,0.20);color:#C4A8FF;}"
            "QPushButton:pressed{background:rgba(139,92,246,0.35);color:#EDE0FF;}"
        )

        self._dec = QPushButton()
        self._dec.setFixedSize(28, 28)
        self._dec.setCursor(Qt.PointingHandCursor)
        self._dec.setStyleSheet(btn_style)
        # Draw left chevron via paintEvent override (no emoji, clean SVG-style)
        self._dec.paintEvent = lambda e, b=self._dec: self._draw_arrow(e, b, left=True)

        self._num = QLabel(str(self._val))
        self._num.setAlignment(Qt.AlignCenter)
        self._num.setFixedWidth(34)
        self._num.setStyleSheet(
            "color:#D0B8F8;font-size:13px;font-weight:800;"
            "background:transparent;border:none;letter-spacing:0.5px;"
        )

        self._inc = QPushButton()
        self._inc.setFixedSize(28, 28)
        self._inc.setCursor(Qt.PointingHandCursor)
        self._inc.setStyleSheet(btn_style)
        self._inc.paintEvent = lambda e, b=self._inc: self._draw_arrow(e, b, left=False)

        layout.addWidget(self._dec)
        layout.addWidget(self._num)
        layout.addWidget(self._inc)

        # Auto-repeat timer — created ONCE in __init__, not in paintEvent
        self._repeat_timer = QTimer(self)
        self._repeat_timer.setInterval(80)
        self._repeat_dir = 0
        self._repeat_timer.timeout.connect(self._do_repeat)
        self._dec.pressed.connect(lambda: self._start_repeat(-1))
        self._inc.pressed.connect(lambda: self._start_repeat(1))
        self._dec.released.connect(self._repeat_timer.stop)
        self._inc.released.connect(self._repeat_timer.stop)

    def _draw_arrow(self, e, btn, left=True):
        """Draw a clean minimal chevron arrow."""
        from PySide6.QtWidgets import QStyleOption, QStyle
        opt = QStyleOption(); opt.initFrom(btn)
        p = QPainter(btn); p.setRenderHint(QPainter.Antialiasing)
        # Draw base button background (hover/press from QSS)
        btn.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, btn)
        W, H = btn.width(), btn.height()
        cx, cy = W/2, H/2
        s = 4.5  # chevron size
        pen = QPen(QColor(167, 139, 250, 220)); pen.setWidthF(2.0)
        pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        if left:
            p.drawLine(int(cx+s*0.4), int(cy-s), int(cx-s*0.4), int(cy))
            p.drawLine(int(cx-s*0.4), int(cy), int(cx+s*0.4), int(cy+s))
        else:
            p.drawLine(int(cx-s*0.4), int(cy-s), int(cx+s*0.4), int(cy))
            p.drawLine(int(cx+s*0.4), int(cy), int(cx-s*0.4), int(cy+s))
        p.end()


    STEP = 5

    def _start_repeat(self, direction):
        self._repeat_dir = direction
        self.setValue(self._val + direction * self.STEP)
        self._repeat_timer.start()

    def _do_repeat(self):
        self.setValue(self._val + self._repeat_dir * self.STEP)

    def value(self):
        return self._val

    def setValue(self, v, animate=True):
        v = max(self.MIN_VAL, min(self.MAX_VAL, v))
        if v == self._val:
            return
        self._val = v
        self._num.setText(str(v))
        self.valueChanged.emit(v)


# ── Vault Group Header ─────────────────────────────────────────────────────
class VaultGroupHeader(QFrame):
    """
    Collapsible section header for a vault group.
    Starts COLLAPSED by default — click the chevron or anywhere on the row
    to expand/collapse.  The header manages its own child VaultRow widgets
    by showing/hiding them via the parent scroll layout.
    """

    # Signal emitted when collapse state changes so Dashboard can reflow
    toggled = None  # we use a callback instead

    def __init__(self, group: dict, members: list, vault, refresh_cb,
                 collapsed: bool = True, meta=None):
        super().__init__()
        self._group      = group
        self._members    = members   # list of (real_idx, entry)
        self._vault      = vault
        self._refresh    = refresh_cb
        self._collapsed  = collapsed
        self._meta       = meta
        self._row_widgets: list = []   # populated by Dashboard after construction

        self.setObjectName("vaultGroupHdr")
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 10, 0)
        layout.setSpacing(10)

        # Collapse chevron
        self._chev = QLabel("▶" if collapsed else "▼")
        self._chev.setFixedSize(16, 16)
        self._chev.setAlignment(Qt.AlignCenter)
        self._chev.setStyleSheet(
            "color:#5a3a8a;font-size:10px;background:transparent;border:none;"
        )
        layout.addWidget(self._chev)

        # Avatar emoji
        av = QLabel(group.get("avatar", "🔑"))
        av.setFixedSize(30, 30)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet(
            "font-size:17px;background:rgba(109,40,217,0.14);"
            "border-radius:9px;border:1px solid rgba(109,40,217,0.22);"
        )
        layout.addWidget(av)

        # Name + description
        name_col = QVBoxLayout(); name_col.setSpacing(1)
        name_lbl = QLabel(group.get("name", "Vault"))
        name_lbl.setStyleSheet(
            "color:#e2d5f8;font-size:12px;font-weight:700;letter-spacing:0.3px;"
            "background:transparent;border:none;"
        )
        desc = group.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(
                "color:#4A3370;font-size:10px;background:transparent;border:none;"
            )
            name_col.addWidget(name_lbl); name_col.addWidget(desc_lbl)
        else:
            name_lbl.setAlignment(Qt.AlignVCenter)
            name_col.addWidget(name_lbl)
        layout.addLayout(name_col)
        layout.addStretch()

        # Entry count badge
        n = len(members)
        cnt = QLabel(str(n))
        cnt.setFixedSize(24, 24)
        cnt.setAlignment(Qt.AlignCenter)
        cnt.setStyleSheet(
            "color:#8B5CF6;font-size:10px;font-weight:800;"
            "background:rgba(109,40,217,0.14);border-radius:12px;"
            "border:1px solid rgba(123,47,255,0.25);"
        )
        layout.addWidget(cnt)

        # Edit button (not for default group)
        if group.get("id") != DEFAULT_VAULT_ID:
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(28, 28)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(
                "QPushButton{background:transparent;color:#4A3370;border:none;"
                "font-size:14px;border-radius:7px;}"
                "QPushButton:hover{background:rgba(123,47,255,0.2);}"
            )
            edit_btn.clicked.connect(self._edit_group)
            layout.addWidget(edit_btn)

        # Pin button — available for all vaults including default
        _pinned_now = meta.is_group_pinned(group["id"]) if meta else False
        self._grp_pin_btn = QPushButton("📍" if _pinned_now else "📌")
        self._grp_pin_btn.setFixedSize(28, 28)
        self._grp_pin_btn.setCursor(Qt.PointingHandCursor)

        self._grp_pin_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#f59e0b;border:none;"
            "font-size:14px;border-radius:7px;}"
            "QPushButton:hover{background:rgba(245,158,11,0.2);}"
        )
        self._grp_pin_btn.clicked.connect(self._toggle_group_pin)
        layout.addWidget(self._grp_pin_btn)

    # ── styling ─────────────────────────────────────────────────────────────

    def _apply_style(self):
        if self._collapsed:
            self.setStyleSheet(
                "QFrame#vaultGroupHdr{background:rgba(123,47,255,0.05);"
                "border:1px solid rgba(123,47,255,0.14);border-radius:10px;}"
                "QFrame#vaultGroupHdr:hover{background:rgba(123,47,255,0.10);"
                "border-color:rgba(123,47,255,0.28);}"
                "QFrame#vaultGroupHdr QLabel{background:transparent;border:none;}"
            )
        else:
            self.setStyleSheet(
                "QFrame#vaultGroupHdr{background:rgba(123,47,255,0.10);"
                "border:1px solid rgba(123,47,255,0.28);"
                "border-bottom-left-radius:0px;border-bottom-right-radius:0px;"
                "border-top-left-radius:10px;border-top-right-radius:10px;}"
                "QFrame#vaultGroupHdr QLabel{background:transparent;border:none;}"
            )

    # ── toggle ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        # Don't collapse/expand when the user clicks the pin button
        if self._grp_pin_btn.geometry().contains(e.position().toPoint()):
            super().mousePressEvent(e)
            return
        super().mousePressEvent(e)
        self._toggle()

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._chev.setText("▶" if self._collapsed else "▼")
        self._apply_style()
        if self._collapsed:
            # Instant hide
            for row in self._row_widgets:
                row.setVisible(False)
        else:
            # Cascade reveal — each row appears 45ms after the previous
            for row in self._row_widgets:
                row.setVisible(False)
                row.setGraphicsEffect(None)
            for i, row in enumerate(self._row_widgets):
                delay = i * 45
                QTimer.singleShot(delay, lambda r=row, idx=i: self._reveal_row(r, idx))

    def _reveal_row(self, row, idx):
        """Slide a vault row in from slightly below with a fade."""
        row.setVisible(True)
        # Use opacity effect for fade-in
        effect = QGraphicsDropShadowEffect(row)
        effect.setBlurRadius(0); effect.setOffset(0, 0)
        effect.setColor(QColor(0, 0, 0, 0))
        row.setGraphicsEffect(effect)
        step = [0]
        def tick():
            step[0] += 1
            t = min(1.0, step[0] / 8)
            if t >= 1.0:
                row.setGraphicsEffect(None)
                return
            QTimer.singleShot(16, tick)
        QTimer.singleShot(16, tick)

    def set_row_widgets(self, rows: list):
        """Called by Dashboard after child VaultRows are created."""
        self._row_widgets = rows
        # Apply initial collapsed state
        for row in rows:
            row.setVisible(not self._collapsed)

    def _edit_group(self):
        dlg = EditVaultDialog(self._group, self._vault, self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh()

    def _toggle_group_pin(self):
        if not self._meta:
            return
        gid = self._group["id"]
        currently = self._meta.is_group_pinned(gid)
        self._meta.set_group_pinned(gid, not currently)
        self._grp_pin_btn.setText("📍" if not currently else "📌")
        self._refresh()


# ── Create Vault Dialog ────────────────────────────────────────────────────
class CreateVaultDialog(QDialog):
    """Dialog to create a new vault group with name, description, avatar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Vault")
        self.setFixedWidth(420)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("fluxDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)

        hdr = QLabel("CREATE NEW VAULT")
        hdr.setStyleSheet(
            "color:#8B5CF6;font-size:11px;font-weight:800;letter-spacing:3px;"
        )
        layout.addWidget(hdr)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#1C1438;max-height:1px;border:none;")
        layout.addWidget(div)

        # Avatar picker
        av_lbl = QLabel("ICON")
        av_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(av_lbl)

        self._selected_avatar = DEFAULT_AVATARS[0]
        av_grid = QGridLayout(); av_grid.setSpacing(6)
        self._av_btns = []
        for idx, emoji in enumerate(DEFAULT_AVATARS):
            btn = QPushButton(emoji)
            btn.setFixedSize(38, 38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._av_style(False))
            btn.clicked.connect(lambda _, e=emoji, b=btn: self._pick_avatar(e, b))
            av_grid.addWidget(btn, idx // 6, idx % 6)
            self._av_btns.append((emoji, btn))
        layout.addLayout(av_grid)
        # Select first by default
        self._av_btns[0][1].setStyleSheet(self._av_style(True))

        # Name field
        name_lbl = QLabel("VAULT NAME")
        name_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(name_lbl)
        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. Work, Personal, Gaming…")
        self._name.setFixedHeight(42)
        self._name.setStyleSheet(
            "QLineEdit{background:#0d0a1e;border:1px solid #261840;border-radius:10px;"
            "padding:0 14px;color:#e2d5f8;font-size:13px;}"
            "QLineEdit:focus{border-color:#7C3AED;background:#110e24;}"
            "QLineEdit::placeholder{color:#3A2A55;}"
        )
        layout.addWidget(self._name)

        # Description field
        desc_lbl = QLabel("DESCRIPTION  (optional)")
        desc_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(desc_lbl)
        self._desc = QLineEdit()
        self._desc.setPlaceholderText("Short description of this vault…")
        self._desc.setFixedHeight(42)
        self._desc.setStyleSheet(self._name.styleSheet())
        layout.addWidget(self._desc)

        self._err = QLabel("")
        self._err.setStyleSheet("color:#f87171;font-size:11px;")
        layout.addWidget(self._err)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel = QPushButton("Cancel")
        create = QPushButton("Create Vault")
        for b in (cancel, create):
            b.setFixedHeight(42); b.setCursor(Qt.PointingHandCursor)
        create.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:10px;font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )
        cancel.setStyleSheet(
            "QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;"
            "border-radius:10px;font-weight:600;font-size:13px;}"
            "QPushButton:hover{color:white;border-color:#7C3AED;}"
        )
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self._do_create)
        btn_row.addWidget(cancel); btn_row.addWidget(create)
        layout.addLayout(btn_row)

    def _av_style(self, selected: bool) -> str:
        if selected:
            return (
                "QPushButton{background:rgba(139,92,246,0.25);border:2px solid #8B5CF6;"
                "border-radius:10px;font-size:18px;}"
            )
        return (
            "QPushButton{background:rgba(123,47,255,0.08);border:1px solid rgba(123,47,255,0.2);"
            "border-radius:10px;font-size:18px;}"
            "QPushButton:hover{background:rgba(123,47,255,0.2);border-color:#7C3AED;}"
        )

    def _pick_avatar(self, emoji: str, clicked_btn):
        self._selected_avatar = emoji
        for _, btn in self._av_btns:
            btn.setStyleSheet(self._av_style(btn is clicked_btn))

    def _do_create(self):
        name = self._name.text().strip()
        if not name:
            self._err.setText("Vault name is required.")
            return
        create_group(name, self._desc.text().strip(), self._selected_avatar)
        self.accept()


# ── Edit Vault Dialog ──────────────────────────────────────────────────────
class EditVaultDialog(QDialog):
    """Edit an existing vault group's name, description, avatar, or delete it."""

    def __init__(self, group: dict, vault, parent=None):
        super().__init__(parent)
        self._group = group
        self._vault = vault
        self.setWindowTitle("Edit Vault")
        self.setFixedWidth(420)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("fluxDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)

        hdr = QLabel("EDIT VAULT")
        hdr.setStyleSheet(
            "color:#8B5CF6;font-size:11px;font-weight:800;letter-spacing:3px;"
        )
        layout.addWidget(hdr)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#1C1438;max-height:1px;border:none;")
        layout.addWidget(div)

        # Avatar picker
        av_lbl = QLabel("ICON")
        av_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(av_lbl)

        self._selected_avatar = group.get("avatar", DEFAULT_AVATARS[0])
        av_grid = QGridLayout(); av_grid.setSpacing(6)
        self._av_btns = []
        for idx, emoji in enumerate(DEFAULT_AVATARS):
            btn = QPushButton(emoji)
            btn.setFixedSize(38, 38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._av_style(emoji == self._selected_avatar))
            btn.clicked.connect(lambda _, e=emoji, b=btn: self._pick_avatar(e, b))
            av_grid.addWidget(btn, idx // 6, idx % 6)
            self._av_btns.append((emoji, btn))
        layout.addLayout(av_grid)

        # Name field
        name_lbl = QLabel("VAULT NAME")
        name_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(name_lbl)
        self._name = QLineEdit(group.get("name", ""))
        self._name.setFixedHeight(42)
        self._name.setStyleSheet(
            "QLineEdit{background:#0d0a1e;border:1px solid #261840;border-radius:10px;"
            "padding:0 14px;color:#e2d5f8;font-size:13px;}"
            "QLineEdit:focus{border-color:#7C3AED;background:#110e24;}"
        )
        layout.addWidget(self._name)

        # Description field
        desc_lbl = QLabel("DESCRIPTION  (optional)")
        desc_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(desc_lbl)
        self._desc = QLineEdit(group.get("description", ""))
        self._desc.setFixedHeight(42)
        self._desc.setStyleSheet(self._name.styleSheet())
        layout.addWidget(self._desc)

        self._err = QLabel("")
        self._err.setStyleSheet("color:#f87171;font-size:11px;")
        layout.addWidget(self._err)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel  = QPushButton("Cancel")
        save    = QPushButton("Save Changes")
        for b in (cancel, save):
            b.setFixedHeight(42); b.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:10px;font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )
        cancel.setStyleSheet(
            "QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;"
            "border-radius:10px;font-weight:600;font-size:13px;}"
            "QPushButton:hover{color:white;border-color:#7C3AED;}"
        )
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._do_save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        layout.addLayout(btn_row)

        # Delete vault (danger)
        del_btn = QPushButton("Delete This Vault")
        del_btn.setFixedHeight(36); del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.06);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.2);border-radius:9px;"
            "font-size:11px;font-weight:600;}"
            "QPushButton:hover{background:#ff2d6f;color:white;border-color:#ff2d6f;}"
        )
        del_btn.clicked.connect(self._do_delete)
        layout.addWidget(del_btn)

    def _av_style(self, selected: bool) -> str:
        if selected:
            return (
                "QPushButton{background:rgba(139,92,246,0.25);border:2px solid #8B5CF6;"
                "border-radius:10px;font-size:18px;}"
            )
        return (
            "QPushButton{background:rgba(123,47,255,0.08);border:1px solid rgba(123,47,255,0.2);"
            "border-radius:10px;font-size:18px;}"
            "QPushButton:hover{background:rgba(123,47,255,0.2);border-color:#7C3AED;}"
        )

    def _pick_avatar(self, emoji: str, clicked_btn):
        self._selected_avatar = emoji
        for _, btn in self._av_btns:
            btn.setStyleSheet(self._av_style(btn is clicked_btn))

    def _do_save(self):
        name = self._name.text().strip()
        if not name:
            self._err.setText("Vault name is required.")
            return
        update_group(self._group["id"], name=name,
                     description=self._desc.text().strip(),
                     avatar=self._selected_avatar)
        self.accept()

    def _do_delete(self):
        box = QMessageBox(self)
        box.setWindowTitle("Delete Vault")
        box.setText(
            f"Delete vault '{self._group.get('name', '')}' ?\n\n"
            "All entries will be moved to  'Not Stored Yet'."
        )
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        _style_msgbox(box)
        if box.exec() == QMessageBox.Yes:
            delete_group(self._group["id"])
            self.accept()


# ── Save to Vault Dialog ───────────────────────────────────────────────────
class SaveToVaultDialog(QDialog):
    """Ask site/username then pick which vault to save into."""

    def __init__(self, vault, password: str, parent=None):
        super().__init__(parent)
        self._vault    = vault
        self._password = password
        self.setWindowTitle("Save to Vault")
        self.setFixedWidth(440)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("fluxDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)

        hdr = QLabel("SAVE TO VAULT")
        hdr.setStyleSheet(
            "color:#8B5CF6;font-size:11px;font-weight:800;letter-spacing:3px;"
        )
        layout.addWidget(hdr)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#1C1438;max-height:1px;border:none;")
        layout.addWidget(div)

        # Site
        site_lbl = QLabel("WEBSITE / APP")
        site_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(site_lbl)
        self._site = QLineEdit()
        self._site.setPlaceholderText("e.g. github.com, Netflix…")
        self._site.setFixedHeight(42)
        self._site.setStyleSheet(self._field_style())
        layout.addWidget(self._site)

        # Username
        user_lbl = QLabel("USERNAME / EMAIL")
        user_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(user_lbl)
        self._user = QLineEdit()
        self._user.setPlaceholderText("username or email (optional)")
        self._user.setFixedHeight(42)
        self._user.setStyleSheet(self._field_style())
        layout.addWidget(self._user)

        # Vault picker
        vault_lbl = QLabel("SAVE INTO VAULT")
        vault_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;")
        layout.addWidget(vault_lbl)

        self._groups = get_all_groups()
        # Filter out "Not Stored Yet" from top picks; add it at the end
        user_groups = [g for g in self._groups if g["id"] != DEFAULT_VAULT_ID]
        fallback    = next((g for g in self._groups if g["id"] == DEFAULT_VAULT_ID), None)

        self._selected_gid = DEFAULT_VAULT_ID
        self._vault_btns   = []

        scroll_w  = QWidget()
        scroll_l  = QVBoxLayout(scroll_w)
        scroll_l.setContentsMargins(0, 0, 0, 0)
        scroll_l.setSpacing(6)

        for group in user_groups + ([fallback] if fallback else []):
            btn = self._make_vault_btn(group)
            scroll_l.addWidget(btn)
            self._vault_btns.append((group["id"], btn))

        # New vault option
        new_btn = QPushButton("  + Create New Vault")
        new_btn.setFixedHeight(44)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton{background:rgba(139,92,246,0.07);color:#8B5CF6;"
            "border:1px dashed rgba(139,92,246,0.35);border-radius:10px;"
            "font-size:12px;font-weight:700;text-align:left;padding-left:14px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.15);color:#c084fc;"
            "border-color:#8B5CF6;}"
        )
        new_btn.clicked.connect(self._create_and_select)
        scroll_l.addWidget(new_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(220)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:transparent;width:3px;}"
            "QScrollBar::handle:vertical{background:#2A1F45;border-radius:2px;}"
            "QScrollBar::handle:vertical:hover{background:#7C3AED;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        scroll.setWidget(scroll_w)
        layout.addWidget(scroll)

        # Select first user group if available
        if user_groups:
            self._select_vault(user_groups[0]["id"])
        elif fallback:
            self._select_vault(DEFAULT_VAULT_ID)

        self._err = QLabel("")
        self._err.setStyleSheet("color:#f87171;font-size:11px;")
        layout.addWidget(self._err)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel = QPushButton("Cancel")
        save   = QPushButton("Save Password")
        for b in (cancel, save):
            b.setFixedHeight(42); b.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:10px;font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )
        cancel.setStyleSheet(
            "QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;"
            "border-radius:10px;font-weight:600;font-size:13px;}"
            "QPushButton:hover{color:white;border-color:#7C3AED;}"
        )
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._do_save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _field_style(self) -> str:
        return (
            "QLineEdit{background:#0d0a1e;border:1px solid #261840;border-radius:10px;"
            "padding:0 14px;color:#e2d5f8;font-size:13px;}"
            "QLineEdit:focus{border-color:#7C3AED;background:#110e24;}"
            "QLineEdit::placeholder{color:#3A2A55;}"
        )

    def _make_vault_btn(self, group: dict) -> QPushButton:
        gid    = group["id"]
        avatar = group.get("avatar", "🔑")
        name   = group.get("name", "Vault")
        desc   = group.get("description", "")
        label  = f"{avatar}  {name}" + (f"  —  {desc}" if desc else "")
        btn = QPushButton(label)
        btn.setFixedHeight(44)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(self._vault_btn_style(False))
        btn.clicked.connect(lambda _, g=gid: self._select_vault(g))
        return btn

    def _vault_btn_style(self, selected: bool) -> str:
        if selected:
            return (
                "QPushButton{background:rgba(123,47,255,0.22);color:#e2d5f8;"
                "border:1.5px solid #7C3AED;border-radius:10px;"
                "font-size:12px;font-weight:700;text-align:left;padding-left:14px;}"
            )
        return (
            "QPushButton{background:rgba(123,47,255,0.06);color:#8870aa;"
            "border:1px solid rgba(109,40,217,0.18);border-radius:10px;"
            "font-size:12px;font-weight:600;text-align:left;padding-left:14px;}"
            "QPushButton:hover{background:rgba(123,47,255,0.14);color:#c084fc;"
            "border-color:rgba(109,40,217,0.4);}"
        )

    def _select_vault(self, gid: str):
        self._selected_gid = gid
        for g_id, btn in self._vault_btns:
            btn.setStyleSheet(self._vault_btn_style(g_id == gid))

    def _create_and_select(self):
        dlg = CreateVaultDialog(self)
        if dlg.exec() == QDialog.Accepted:
            # Refresh groups
            self._groups = get_all_groups()
            # The newest group is last (excluding default)
            user_groups = [g for g in self._groups if g["id"] != DEFAULT_VAULT_ID]
            if user_groups:
                newest = user_groups[-1]
                self._selected_gid = newest["id"]
                # Add a button for it
                btn = self._make_vault_btn(newest)
                btn.setStyleSheet(self._vault_btn_style(True))
                # Insert before the last widget in scroll
                parent_layout = self._vault_btns[-1][1].parent().layout() if self._vault_btns else None
                if parent_layout:
                    parent_layout.insertWidget(parent_layout.count() - 1, btn)
                self._vault_btns.append((newest["id"], btn))
                # Deselect others
                for g_id, b in self._vault_btns[:-1]:
                    b.setStyleSheet(self._vault_btn_style(False))

    def _do_save(self):
        site = self._site.text().strip()
        if not site:
            self._err.setText("Website / App name is required.")
            return
        self._vault.save_entry(site, self._user.text().strip(),
                               self._password, self._selected_gid)
        self.accept()


# ── Move Vault Dialog ──────────────────────────────────────────────────────
class MoveVaultDialog(QDialog):
    """Move an entry to a different vault group."""

    def __init__(self, index: int, entry: dict, vault, parent=None):
        super().__init__(parent)
        self._index = index
        self._entry = entry
        self._vault = vault
        self._current_gid = entry.get("vault_id", DEFAULT_VAULT_ID)
        self.setWindowTitle("Move to Vault")
        self.setFixedWidth(400)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("fluxDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)

        hdr = QLabel("MOVE TO VAULT")
        hdr.setStyleSheet("color:#8B5CF6;font-size:11px;font-weight:800;letter-spacing:3px;")
        layout.addWidget(hdr)

        site = entry.get("site", "?")
        sub = QLabel(f"Moving: {site}")
        sub.setStyleSheet("color:#5A4070;font-size:12px;")
        layout.addWidget(sub)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#1C1438;max-height:1px;border:none;")
        layout.addWidget(div)

        self._groups = get_all_groups()
        self._selected_gid = self._current_gid
        self._vault_btns   = []

        for group in self._groups:
            gid    = group["id"]
            avatar = group.get("avatar", "🔑")
            name   = group.get("name", "Vault")
            desc   = group.get("description", "")
            label  = f"{avatar}  {name}" + (f"  —  {desc}" if desc else "")
            btn = QPushButton(label)
            btn.setFixedHeight(44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._style(gid == self._current_gid))
            btn.clicked.connect(lambda _, g=gid: self._pick(g))
            layout.addWidget(btn)
            self._vault_btns.append((gid, btn))

        # Create new vault shortcut
        new_btn = QPushButton("  + Create New Vault")
        new_btn.setFixedHeight(40)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton{background:rgba(139,92,246,0.07);color:#8B5CF6;"
            "border:1px dashed rgba(139,92,246,0.3);border-radius:10px;"
            "font-size:12px;font-weight:700;text-align:left;padding-left:14px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.15);color:#c084fc;}"
        )
        new_btn.clicked.connect(self._create_and_pick)
        layout.addWidget(new_btn)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel = QPushButton("Cancel")
        move   = QPushButton("Move Here")
        for b in (cancel, move):
            b.setFixedHeight(42); b.setCursor(Qt.PointingHandCursor)
        move.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:10px;font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )
        cancel.setStyleSheet(
            "QPushButton{background:#181030;color:#5A4070;border:1px solid #261840;"
            "border-radius:10px;font-weight:600;font-size:13px;}"
            "QPushButton:hover{color:white;border-color:#7C3AED;}"
        )
        cancel.clicked.connect(self.reject)
        move.clicked.connect(self._do_move)
        btn_row.addWidget(cancel); btn_row.addWidget(move)
        layout.addLayout(btn_row)

    def _style(self, selected: bool) -> str:
        if selected:
            return (
                "QPushButton{background:rgba(123,47,255,0.22);color:#e2d5f8;"
                "border:1.5px solid #7C3AED;border-radius:10px;"
                "font-size:12px;font-weight:700;text-align:left;padding-left:14px;}"
            )
        return (
            "QPushButton{background:rgba(123,47,255,0.06);color:#8870aa;"
            "border:1px solid rgba(109,40,217,0.18);border-radius:10px;"
            "font-size:12px;font-weight:600;text-align:left;padding-left:14px;}"
            "QPushButton:hover{background:rgba(123,47,255,0.14);color:#c084fc;"
            "border-color:rgba(109,40,217,0.4);}"
        )

    def _pick(self, gid: str):
        self._selected_gid = gid
        for g_id, btn in self._vault_btns:
            btn.setStyleSheet(self._style(g_id == gid))

    def _create_and_pick(self):
        dlg = CreateVaultDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._groups = get_all_groups()
            user_groups = [g for g in self._groups if g["id"] != DEFAULT_VAULT_ID]
            if user_groups:
                newest = user_groups[-1]
                gid = newest["id"]
                label = f"{newest.get('avatar','🔑')}  {newest.get('name','Vault')}"
                btn = QPushButton(label)
                btn.setFixedHeight(44); btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(self._style(True))
                btn.clicked.connect(lambda _, g=gid: self._pick(g))
                # Insert above the new vault button (last widget)
                layout = self.layout()
                layout.insertWidget(layout.count() - 2, btn)
                self._vault_btns.append((gid, btn))
                self._pick(gid)

    def _do_move(self):
        if self._selected_gid != self._current_gid:
            self._vault.move_entry(self._index, self._selected_gid)
        self.accept()


# ── Animated Note Button ──────────────────────────────────────────────────
# ── Note Button ──────────────────────────────────────────────────────────
class NoteButton(QPushButton):
    """Gear-style — drawn icon, animates on hover, click always works."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton{background:transparent;border:none;border-radius:8px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.12);}"
            "QPushButton:pressed{background:rgba(139,92,246,0.22);}"
        )
        self._hover = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        self._phase = (self._phase + 0.06) % (2 * 3.14159)
        self.update()

    def enterEvent(self, e):
        self._hover = True; self._timer.start(16); self.update()

    def leaveEvent(self, e):
        self._hover = False; self._timer.stop(); self.update()

    def paintEvent(self, e):
        # Draw default button first (handles pressed state)
        super().paintEvent(e)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        col = QColor("#8B5CF6") if self._hover else QColor("#4A3370")
        cx, cy = self.width()/2, self.height()/2

        # Note page icon
        p.translate(cx - 5, cy - 7)
        path = QPainterPath()
        path.moveTo(0, 0); path.lineTo(7, 0); path.lineTo(10, 3)
        path.lineTo(10, 14); path.lineTo(0, 14); path.closeSubpath()
        p.setPen(QPen(col, 1.4)); p.setBrush(QColor(col.red(), col.green(), col.blue(), 35))
        p.drawPath(path)
        # Fold corner
        fold = QPainterPath()
        fold.moveTo(7, 0); fold.lineTo(7, 3); fold.lineTo(10, 3)
        p.setBrush(Qt.NoBrush); p.drawPath(fold)
        # Lines
        p.setPen(QPen(col, 1.1))
        for ly in (5, 8, 11):
            p.drawLine(2, ly, 8, ly)
        p.end()


# ── Audit Button ──────────────────────────────────────────────────────────
class AuditButton(QPushButton):
    """Gear-style — drawn magnifier, scan animation on hover, click works."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton{background:transparent;border:none;border-radius:8px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.12);}"
            "QPushButton:pressed{background:rgba(139,92,246,0.22);}"
        )
        self._hover = False
        self._phase = 0.0
        self._scan  = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        self._phase = (self._phase + 0.05) % (2 * 3.14159)
        self._scan  = (self._scan  + 0.03)  % 1.0
        self.update()

    def enterEvent(self, e):
        self._hover = True; self._timer.start(16); self.update()

    def leaveEvent(self, e):
        self._hover = False; self._timer.stop(); self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        col = QColor("#8B5CF6") if self._hover else QColor("#4A3370")
        pulse = 0.5 + 0.5 * math.sin(self._phase)
        cx, cy = self.width()/2 - 1, self.height()/2 - 1

        # Magnifier circle
        p.setPen(QPen(col, 1.8)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(int(cx-7), int(cy-7), 12, 12)
        # Handle
        p.setPen(QPen(col, 2.0))
        p.drawLine(int(cx+3), int(cy+3), int(cx+8), int(cy+8))

        # Animated scan line (only when hovered)
        if self._hover:
            scan_y = int((cy - 6) + self._scan * 10)
            sp = QPen(QColor(192, 132, 252, int(180 * pulse))); sp.setWidthF(1.2)
            p.setPen(sp); p.drawLine(int(cx-6), scan_y, int(cx+3), scan_y)
        p.end()


class AuditLogDialog(QDialog):
    """PLUS: Full audit log — logins, failures, vault ops, with search/filter."""

    ACTION_META = {
        "copy":           ("📋", "#4ade80",  "Security"),
        "generate":       ("⚡", "#c084fc",  "Generate"),
        "save_entry":     ("💾", "#60a5fa",  "Vault"),
        "delete_entry":   ("🗑", "#f87171",  "Vault"),
        "note_saved":     ("📝", "#a78bfa",  "Notes"),
        "vault_unlock":   ("🔓", "#34d399",  "Auth"),
        "login_success":  ("✅", "#22c55e",  "Auth"),
        "login_failed":   ("❌", "#ef4444",  "Auth"),
        "logout":         ("🔐", "#fb923c",  "Auth"),
        "move_entry":     ("📂", "#fb923c",  "Vault"),
        "vault_created":  ("📁", "#f9a8d4",  "Vault"),
        "profile_switch": ("", "#38bdf8",  "Profile"),
        "theme_change":   ("🎨", "#e879f9",  "Settings"),
        "master_changed": ("🔑", "#fbbf24",  "Security"),
        "vault_scan":     ("🛡", "#34d399",  "Security"),
        "clipboard_clear":("🧹","#94a3b8",  "Security"),
    }
    CATEGORIES = ["All", "Auth", "Vault", "Generate", "Security", "Notes", "Profile", "Settings"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audit Log")
        self.setFixedSize(580, 620)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos   = None
        self._filter_cat = "All"
        self._search_txt = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self._card = QWidget(); self._card.setObjectName("auditCard")
        self._card.setStyleSheet(
            "QWidget#auditCard{background:#0F0D1E;"
            "border:1px solid rgba(109,40,217,0.40);border-radius:18px;}"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36); shadow.setOffset(0, 4)
        shadow.setColor(QColor(109, 40, 217, 130))
        self._card.setGraphicsEffect(shadow)
        outer.addWidget(self._card)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        hdr = QWidget(); hdr.setFixedHeight(56)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1A1428,stop:1 #0F0D1E);"
            "border-top-left-radius:17px;border-top-right-radius:17px;"
            "border-bottom:1px solid rgba(109,40,217,0.22);"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(18, 0, 14, 0); hl.setSpacing(10)
        title = QLabel("🔍  Activity Log")
        title.setStyleSheet(
            "color:#EDE8FF;font-size:15px;font-weight:800;letter-spacing:1px;"
            "background:transparent;border:none;"
        )
        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedHeight(26); clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.22);border-radius:7px;"
            "font-size:11px;font-weight:600;padding:0 10px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;border-color:#ff2d6f;}"
        )
        clear_btn.clicked.connect(self._clear)
        xbtn = QPushButton("✕"); xbtn.setFixedSize(28, 28); xbtn.setCursor(Qt.PointingHandCursor)
        xbtn.setStyleSheet(
            "QPushButton{background:transparent;color:#4A3370;border:none;font-size:13px;border-radius:7px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;}"
        )
        xbtn.clicked.connect(self.reject)
        hl.addWidget(title); hl.addStretch(); hl.addWidget(clear_btn); hl.addSpacing(6); hl.addWidget(xbtn)
        layout.addWidget(hdr)

        # ── Search + filter bar ──────────────────────────────────────
        filter_row = QWidget(); filter_row.setFixedHeight(46)
        filter_row.setStyleSheet("background:#110F22;border:none;")
        fr = QHBoxLayout(filter_row); fr.setContentsMargins(14, 0, 14, 0); fr.setSpacing(8)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search actions or details...")
        self._search_edit.setFixedHeight(28)
        self._search_edit.setStyleSheet(
            "QLineEdit{background:#0F0D1E;border:1px solid rgba(109,40,217,0.28);"
            "border-radius:8px;padding:0 10px;color:#C4B8E8;font-size:12px;}"
            "QLineEdit:focus{border-color:#7C3AED;}"
            "QLineEdit::placeholder{color:#3D2A58;}"
        )
        self._search_edit.textChanged.connect(self._on_search)
        fr.addWidget(self._search_edit, 1)

        self._cat_btns = {}
        for cat in self.CATEGORIES:
            b = QPushButton(cat); b.setFixedHeight(26); b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True); b.setChecked(cat == "All")
            b.setStyleSheet(self._cat_style(cat == "All"))
            b.clicked.connect(lambda _, c=cat, btn=b: self._set_cat(c))
            fr.addWidget(b)
            self._cat_btns[cat] = b
        layout.addWidget(filter_row)

        # Divider
        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet("background:rgba(109,40,217,0.18);border:none;")
        layout.addWidget(div)

        # ── Stats bar ────────────────────────────────────────────────
        self._stats_lbl = QLabel("")
        self._stats_lbl.setFixedHeight(28)
        self._stats_lbl.setAlignment(Qt.AlignCenter)
        self._stats_lbl.setStyleSheet(
            "color:#6B5A8A;font-size:10px;font-weight:600;letter-spacing:1px;"
            "background:#0D0B1A;border:none;"
        )
        layout.addWidget(self._stats_lbl)

        # ── Log scroll ───────────────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;"
            "border-bottom-left-radius:18px;border-bottom-right-radius:18px;}"
            "QScrollBar:vertical{background:transparent;width:3px;}"
            "QScrollBar::handle:vertical{background:rgba(109,40,217,0.35);border-radius:2px;}"
            "QScrollBar::handle:vertical:hover{background:#7C3AED;}"
        )
        self._log_w = QWidget(); self._log_w.setStyleSheet("background:transparent;")
        self._log_l = QVBoxLayout(self._log_w)
        self._log_l.setContentsMargins(12, 10, 12, 12); self._log_l.setSpacing(5)
        self._log_l.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._log_w)
        layout.addWidget(scroll)
        self._populate()

    def _cat_style(self, active):
        if active:
            return ("QPushButton{background:rgba(109,40,217,0.30);color:#A78BFA;"
                    "border:1px solid rgba(109,40,217,0.50);border-radius:7px;"
                    "font-size:10px;font-weight:700;padding:0 8px;}")
        return ("QPushButton{background:transparent;color:#4A3370;border:none;"
                "border-radius:7px;font-size:10px;font-weight:600;padding:0 8px;}"
                "QPushButton:hover{background:rgba(109,40,217,0.15);color:#8B5CF6;}")

    def _set_cat(self, cat):
        self._filter_cat = cat
        for c, b in self._cat_btns.items():
            b.setChecked(c == cat)
            b.setStyleSheet(self._cat_style(c == cat))
        self._populate()

    def _on_search(self, txt):
        self._search_txt = txt.lower()
        self._populate()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 70:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos = None

    def _populate(self):
        for i in reversed(range(self._log_l.count())):
            w = self._log_l.itemAt(i).widget()
            if w: w.deleteLater()

        all_entries = audit.load()

        # Compute stats before filtering
        total   = len(all_entries)
        logins  = sum(1 for e in all_entries if e.get("action") == "login_success")
        fails   = sum(1 for e in all_entries if e.get("action") == "login_failed")
        gens    = sum(1 for e in all_entries if e.get("action") == "generate")
        self._stats_lbl.setText(
            f"Total: {total}   ·   Logins: {logins}   ·   Failed: {fails}   ·   Generated: {gens}"
        )

        # Filter
        entries = []
        for e in all_entries:
            action = e.get("action", "unknown")
            _, _, cat = self.ACTION_META.get(action, ("•", "#8B5CF6", "Other"))
            if self._filter_cat != "All" and cat != self._filter_cat:
                continue
            if self._search_txt:
                haystack = (action + " " + e.get("detail","")).lower()
                if self._search_txt not in haystack:
                    continue
            entries.append(e)

        if not entries:
            lbl = QLabel("No matching entries.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color:#3A2A55;font-size:13px;padding:30px;"
                "background:transparent;font-style:italic;"
            )
            self._log_l.addWidget(lbl)
            return

        prev_date = None
        for entry in entries:
            action = entry.get("action", "unknown")
            icon, colour, cat = self.ACTION_META.get(action, ("•", "#8B5CF6", "Other"))
            ts_val = entry.get("ts", 0)
            dt = datetime.datetime.fromtimestamp(ts_val)
            date_str = dt.strftime("%a %d %b %Y")

            # Date separator
            if date_str != prev_date:
                prev_date = date_str
                sep_w = QWidget(); sep_w.setStyleSheet("background:transparent;")
                sep_l = QHBoxLayout(sep_w); sep_l.setContentsMargins(0,4,0,2); sep_l.setSpacing(8)
                line1 = QFrame(); line1.setFrameShape(QFrame.HLine)
                line1.setStyleSheet("background:rgba(109,40,217,0.15);max-height:1px;border:none;")
                date_lbl = QLabel(date_str)
                date_lbl.setStyleSheet("color:#4A3370;font-size:9px;font-weight:700;letter-spacing:1.5px;background:transparent;border:none;")
                line2 = QFrame(); line2.setFrameShape(QFrame.HLine)
                line2.setStyleSheet("background:rgba(109,40,217,0.15);max-height:1px;border:none;")
                sep_l.addWidget(line1,1); sep_l.addWidget(date_lbl); sep_l.addWidget(line2,1)
                self._log_l.addWidget(sep_w)

            row = QFrame()
            is_fail = action == "login_failed"
            row_bg = "rgba(220,30,60,0.06)" if is_fail else "rgba(109,40,217,0.06)"
            row_border = "rgba(220,30,60,0.14)" if is_fail else "rgba(109,40,217,0.14)"
            row.setStyleSheet(
                f"QFrame{{background:{row_bg};"
                f"border:1px solid {row_border};"
                f"border-left:3px solid {colour};"
                f"border-radius:9px;}}"
                "QFrame QLabel{background:transparent;border:none;}"
            )
            row.setFixedHeight(46)
            rl = QHBoxLayout(row); rl.setContentsMargins(10, 0, 12, 0); rl.setSpacing(8)

            # Icon
            icon_lbl = QLabel(icon); icon_lbl.setFixedWidth(22)
            icon_lbl.setStyleSheet("font-size:15px;background:transparent;")

            # Action + detail column
            info_col = QVBoxLayout(); info_col.setSpacing(1)
            act_lbl = QLabel(action.replace("_", " ").title())
            act_lbl.setStyleSheet(f"color:{colour};font-size:12px;font-weight:700;")
            detail = entry.get("detail","")
            if detail:
                det_lbl = QLabel(detail[:40] + ("…" if len(detail)>40 else ""))
                det_lbl.setStyleSheet("color:#5A4070;font-size:10px;")
                info_col.addWidget(act_lbl); info_col.addWidget(det_lbl)
            else:
                info_col.addWidget(act_lbl)

            # Category pill
            cat_lbl = QLabel(cat)
            cat_lbl.setStyleSheet(
                f"color:{colour};font-size:9px;font-weight:800;letter-spacing:1px;"
                f"background:rgba(109,40,217,0.12);border:1px solid {colour}33;"
                "border-radius:5px;padding:1px 6px;"
            )

            # Time
            time_lbl = QLabel(dt.strftime("%H:%M:%S"))
            time_lbl.setStyleSheet("color:#4A3370;font-size:10px;letter-spacing:0.5px;")
            time_lbl.setFixedWidth(60); time_lbl.setAlignment(Qt.AlignRight)

            rl.addWidget(icon_lbl)
            rl.addLayout(info_col, 1)
            rl.addWidget(cat_lbl)
            rl.addWidget(time_lbl)
            self._log_l.addWidget(row)

    def _clear(self):
        audit.clear(); self._populate()


# ── Animated Note Button ───────────────────────────────────────────────────
class SecureNotesDialog(QDialog):
    """PLUS: Secure notes — same open mechanism as AuditLogDialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Secure Notes")
        self.setFixedSize(700, 540)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._current_id = None
        self._drag_pos   = None
        self._glow_phase = 0.0

        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(50)
        self._glow_timer.timeout.connect(self._tick_glow)
        self._glow_timer.start()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self._card = QWidget()
        self._card.setObjectName("noteCard")
        self._card.setStyleSheet("QWidget#noteCard{background:#07041a;border-radius:18px;}")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40); shadow.setOffset(0, 0)
        shadow.setColor(QColor(168, 85, 247, 160))
        self._card.setGraphicsEffect(shadow)
        outer.addWidget(self._card)

        root = QVBoxLayout(self._card)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        hdr = QWidget(); hdr.setFixedHeight(58)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #110830,stop:1 #08041a);"
            "border-top-left-radius:16px;border-top-right-radius:16px;"
            "border-bottom:1px solid rgba(139,92,246,0.35);"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20, 0, 14, 0); hl.setSpacing(10)

        icon_l = QLabel("📓")
        icon_l.setStyleSheet("color:#c084fc;font-size:20px;background:transparent;border:none;")
        title_l = QLabel("Secure Notes")
        title_l.setStyleSheet(
            "color:#f0eaff;font-size:15px;font-weight:800;letter-spacing:1.5px;"
            "background:transparent;border:none;"
        )
        xbtn = QPushButton("\u2715"); xbtn.setFixedSize(28, 28); xbtn.setCursor(Qt.PointingHandCursor)
        xbtn.setStyleSheet(
            "QPushButton{background:transparent;color:#4A3370;border:none;font-size:13px;border-radius:7px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;}"
        )
        xbtn.clicked.connect(self.reject)
        hl.addWidget(icon_l); hl.addWidget(title_l)
        hl.addStretch(); hl.addWidget(xbtn)
        root.addWidget(hdr)

        # ── Body ──────────────────────────────────────────────────────
        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)

        # Left sidebar
        lp = QFrame(); lp.setFixedWidth(210)
        lp.setStyleSheet("background:#080614;border-right:1px solid rgba(109,40,217,0.18);border-bottom-left-radius:18px;")
        lpl = QVBoxLayout(lp); lpl.setContentsMargins(10, 14, 10, 12); lpl.setSpacing(8)

        new_btn = QPushButton("+ New Note")
        new_btn.setFixedHeight(36); new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.14);color:#c084fc;"
            "border:1px solid rgba(139,92,246,0.4);border-radius:9px;font-weight:700;font-size:12px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.28);color:#e2d5f8;border-color:#c084fc;}"
        )
        new_btn.clicked.connect(self._new_note)
        lpl.addWidget(new_btn)

        self._note_list = QScrollArea(); self._note_list.setWidgetResizable(True)
        self._note_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._note_list.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:transparent;width:3px;}"
            "QScrollBar::handle:vertical{background:rgba(123,47,255,0.3);border-radius:2px;}"
        )
        self._note_list_w = QWidget(); self._note_list_w.setStyleSheet("background:transparent;")
        self._note_list_l = QVBoxLayout(self._note_list_w)
        self._note_list_l.setContentsMargins(0, 0, 0, 0); self._note_list_l.setSpacing(4)
        self._note_list_l.setAlignment(Qt.AlignTop)
        self._note_list.setWidget(self._note_list_w)
        lpl.addWidget(self._note_list)
        body.addWidget(lp)

        # Right editor
        from PySide6.QtWidgets import QTextEdit
        ep = QFrame(); ep.setStyleSheet("background:#06040f;border-bottom-left-radius:18px;border-bottom-right-radius:18px;")
        epl = QVBoxLayout(ep); epl.setContentsMargins(16, 14, 16, 14); epl.setSpacing(10)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Note title\u2026")
        self._title_edit.setFixedHeight(40)
        self._title_edit.setStyleSheet(
            "QLineEdit{background:#0d0a20;border:none;"
            "border-bottom:2px solid rgba(123,47,255,0.3);"
            "color:#e2d5f8;font-size:15px;font-weight:700;padding:0 4px;}"
            "QLineEdit:focus{border-bottom-color:#c084fc;background:#110e28;}"
            "QLineEdit::placeholder{color:#3a2550;}"
        )

        self._body_edit = QTextEdit()
        self._body_edit.setPlaceholderText("Start writing your secure note\u2026")
        self._body_edit.setStyleSheet(
            "QTextEdit{background:#08061a;border:1px solid rgba(109,40,217,0.14);"
            "border-radius:10px;color:#d0c8e8;font-size:13px;padding:10px 12px;}"
            "QTextEdit:focus{border-color:rgba(139,92,246,0.4);background:#0a0820;}"
        )

        bot = QHBoxLayout(); bot.setSpacing(8)
        del_btn = QPushButton("Delete")
        self._save_btn = QPushButton("Save Note")
        for b in (del_btn, self._save_btn): b.setFixedHeight(36); b.setCursor(Qt.PointingHandCursor)
        self._save_btn.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.18);color:#c084fc;"
            "border:1px solid rgba(139,92,246,0.45);border-radius:9px;font-weight:700;font-size:12px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.32);color:white;}"
        )
        del_btn.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.07);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.2);border-radius:9px;font-size:12px;}"
            "QPushButton:hover{background:rgba(220,30,60,0.2);color:white;}"
        )
        self._ts_lbl = QLabel("")
        self._ts_lbl.setStyleSheet("color:#3a2a55;font-size:10px;background:transparent;border:none;")
        bot.addWidget(self._ts_lbl); bot.addStretch()
        bot.addWidget(del_btn); bot.addWidget(self._save_btn)

        self._save_btn.clicked.connect(self._save_note)
        del_btn.clicked.connect(self._delete_note)

        epl.addWidget(self._title_edit)
        epl.addWidget(self._body_edit)
        epl.addLayout(bot)
        body.addWidget(ep)

        root.addLayout(body)
        self._refresh_list()
        self._set_editor_enabled(False)

    def _tick_glow(self):
        self._glow_phase = (self._glow_phase + 0.03) % (2 * math.pi)
        if hasattr(self, "_card") and self._card.graphicsEffect():
            pulse = 0.55 + 0.45 * math.sin(self._glow_phase)
            self._card.graphicsEffect().setColor(QColor(168, 85, 247, int(120 + 100 * pulse)))

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height(); m = 10
        pulse = 0.5 + 0.5 * math.sin(self._glow_phase)
        for width, alpha in [(10, int(18*pulse)), (5, int(45*pulse)), (2, int(90*pulse))]:
            pen = QPen(QColor(168, 85, 247, alpha)); pen.setWidthF(width)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(m, m, W-m*2, H-m*2, 16, 16)
        pen2 = QPen(QColor(200, 150, 255, int(170 + 60*pulse))); pen2.setWidthF(1.5)
        p.setPen(pen2); p.drawRoundedRect(m, m, W-m*2, H-m*2, 16, 16); p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 70:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos = None

    def _set_editor_enabled(self, en):
        self._title_edit.setEnabled(en); self._body_edit.setEnabled(en)
        self._save_btn.setEnabled(en)

    def _refresh_list(self):
        for i in reversed(range(self._note_list_l.count())):
            w = self._note_list_l.itemAt(i).widget()
            if w: w.deleteLater()
        for note in get_notes():
            btn = QPushButton(note["title"] or "Untitled")
            btn.setFixedHeight(38); btn.setCursor(Qt.PointingHandCursor)
            active = note["id"] == self._current_id
            btn.setStyleSheet(
                f"QPushButton{{background:{'rgba(109,40,217,0.18)' if active else 'rgba(255,255,255,0.03)'};"
                f"color:{'#c084fc' if active else '#7060a0'};"
                "border:none;border-radius:8px;text-align:left;padding-left:12px;"
                "font-size:12px;font-weight:600;}}"
                "QPushButton:hover{background:rgba(123,47,255,0.14);color:#c084fc;}"
            )
            btn.clicked.connect(lambda _, n=note: self._load_note(n))
            self._note_list_l.addWidget(btn)

    def _load_note(self, note):
        self._current_id = note["id"]
        self._title_edit.setText(note.get("title", ""))
        self._body_edit.setPlainText(note.get("body", ""))
        ts = datetime.datetime.fromtimestamp(note.get("updated", 0)).strftime("%b %d, %Y  %H:%M")
        self._ts_lbl.setText(f"Last saved {ts}")
        self._set_editor_enabled(True)
        self._refresh_list()

    def _new_note(self):
        self._current_id = secrets.token_hex(8)
        self._title_edit.clear(); self._body_edit.clear()
        self._ts_lbl.setText("New note")
        self._set_editor_enabled(True)
        self._title_edit.setFocus()
        self._refresh_list()

    def _save_note(self):
        if not self._current_id: return
        title = self._title_edit.text().strip() or "Untitled"
        save_note(self._current_id, title, self._body_edit.toPlainText())
        audit.log("note_saved", title)
        self._refresh_list()
        self._ts_lbl.setText("Saved \u2713")

    def _delete_note(self):
        if not self._current_id: return
        delete_note(self._current_id)
        self._current_id = None
        self._title_edit.clear(); self._body_edit.clear()
        self._set_editor_enabled(False)
        self._refresh_list()




# ── Profile Dialog ─────────────────────────────────────────────────────────
class ProfileDialog(QDialog):
    """Local-only user profile: username + paged emoji avatar picker."""
    PAGE_SIZE = 40   # emojis per page (5 cols × 8 rows)
    COLS      = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Profile")
        self.setFixedWidth(480)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None
        self._page = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(0)

        # Card with drop shadow
        self._card = QFrame(); self._card.setObjectName("profOuter")
        self._card.setStyleSheet(
            "QFrame#profOuter{background:#0F0D1E;"
            "border:1px solid rgba(109,40,217,0.55);"
            "border-radius:20px;}"
            "QFrame#profOuter QWidget{background:transparent;}"
            "QFrame#profOuter QLabel{background:transparent;border:none;}"
        )
        shadow = QGraphicsDropShadowEffect(self._card)
        shadow.setBlurRadius(40); shadow.setOffset(0, 4)
        shadow.setColor(QColor(109, 40, 217, 160))
        self._card.setGraphicsEffect(shadow)
        root.addWidget(self._card)

        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)

        # ── Header ──
        hdr = QWidget(); hdr.setFixedHeight(58)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1A1428,stop:1 #0F0D1E);"
            "border-top-left-radius:19px;border-top-right-radius:19px;"
            "border-bottom:1px solid rgba(109,40,217,0.22);"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20, 0, 14, 0); hl.setSpacing(10)
        title = QLabel("👤  My Profile")
        title.setStyleSheet(
            "color:#EDE8FF;font-size:15px;font-weight:800;letter-spacing:1.5px;"
            "background:transparent;border:none;"
        )
        badge = QLabel("LOCAL ONLY")
        badge.setStyleSheet(
            "color:#8B5CF6;font-size:8px;font-weight:800;letter-spacing:2px;"
            "background:rgba(109,40,217,0.14);border:1px solid rgba(109,40,217,0.35);"
            "border-radius:5px;padding:2px 8px;"
        )
        xbtn = QPushButton("✕"); xbtn.setFixedSize(28, 28)
        xbtn.setCursor(Qt.PointingHandCursor)
        xbtn.setStyleSheet(
            "QPushButton{background:transparent;color:#4A3370;border:none;"
            "font-size:13px;border-radius:7px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;}"
        )
        xbtn.clicked.connect(self.reject)
        hl.addWidget(title); hl.addWidget(badge); hl.addStretch(); hl.addWidget(xbtn)
        cl.addWidget(hdr)

        # ── Body ──
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(22, 18, 22, 22); bl.setSpacing(16)

        prof = load_profile()
        self._avatar = prof.get("avatar", "🦊")

        # Avatar preview + name
        top_row = QHBoxLayout(); top_row.setSpacing(16)
        self._preview_lbl = QLabel(self._avatar)
        self._preview_lbl.setFixedSize(72, 72)
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setStyleSheet(
            "font-size:42px;background:rgba(109,40,217,0.14);"
            "border:2px solid rgba(109,40,217,0.50);border-radius:18px;"
        )
        rc = QVBoxLayout(); rc.setSpacing(6)
        hint = QLabel("DISPLAY NAME")
        hint.setStyleSheet(
            "color:#4A3370;font-size:10px;font-weight:700;letter-spacing:2px;"
            "background:transparent;border:none;"
        )
        self._usr_edit = QLineEdit(prof.get("username", "FluxUser"))
        self._usr_edit.setFixedHeight(42)
        self._usr_edit.setStyleSheet(
            "QLineEdit{background:#0E0C1E;border:1px solid rgba(109,40,217,0.28);"
            "border-radius:11px;padding:0 14px;color:#E0D8FF;font-size:14px;font-weight:600;}"
            "QLineEdit:focus{border-color:#8B5CF6;background:#13112A;}"
            "QLineEdit::placeholder{color:#3A2A55;}"
        )
        rc.addWidget(hint); rc.addWidget(self._usr_edit)
        top_row.addWidget(self._preview_lbl); top_row.addLayout(rc)
        bl.addLayout(top_row)

        # ── Paged emoji picker header ──
        picker_hdr = QHBoxLayout()
        self._page_lbl = QLabel()
        self._page_lbl.setStyleSheet(
            "color:#6B5A8A;font-size:10px;font-weight:700;letter-spacing:2px;"
            "background:transparent;border:none;"
        )
        self._prev_btn = QPushButton("‹")
        self._next_btn = QPushButton("›")
        for pb in (self._prev_btn, self._next_btn):
            pb.setFixedSize(32, 28); pb.setCursor(Qt.PointingHandCursor)
            pb.setStyleSheet(
                "QPushButton{background:rgba(109,40,217,0.14);color:#8B5CF6;"
                "border:1px solid rgba(109,40,217,0.30);border-radius:8px;"
                "font-size:16px;font-weight:700;}"
                "QPushButton:hover{background:rgba(109,40,217,0.30);color:#EDE0FF;}"
                "QPushButton:disabled{opacity:0.3;color:#3D2A58;}"
            )
        self._prev_btn.clicked.connect(lambda: self._turn_page(-1))
        self._next_btn.clicked.connect(lambda: self._turn_page(1))

        # Category dots
        total_pages = math.ceil(len(PROFILE_EMOJIS) / self.PAGE_SIZE)
        self._dot_row = QHBoxLayout(); self._dot_row.setSpacing(6)
        self._dots = []
        for i in range(total_pages):
            d = QPushButton(); d.setFixedSize(8, 8)
            d.setCursor(Qt.PointingHandCursor)
            d.clicked.connect(lambda _, pg=i: self._go_page(pg))
            self._dots.append(d)
            self._dot_row.addWidget(d)

        picker_hdr.addWidget(self._page_lbl)
        picker_hdr.addStretch()
        picker_hdr.addLayout(self._dot_row)
        picker_hdr.addSpacing(8)
        picker_hdr.addWidget(self._prev_btn)
        picker_hdr.addWidget(self._next_btn)
        bl.addLayout(picker_hdr)

        # ── Emoji grid (paged) ──
        self._grid_wrap = QFrame()
        self._grid_wrap.setStyleSheet(
            "QFrame{background:rgba(109,40,217,0.06);"
            "border:1px solid rgba(109,40,217,0.16);border-radius:14px;}"
            "QFrame QWidget{background:transparent;}"
        )
        self._grid_layout = QGridLayout(self._grid_wrap)
        self._grid_layout.setContentsMargins(10, 10, 10, 10)
        self._grid_layout.setSpacing(6)
        bl.addWidget(self._grid_wrap)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel = QPushButton("Cancel")
        save   = QPushButton("Save Profile")
        for b in (cancel, save): b.setFixedHeight(42); b.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:11px;font-weight:800;font-size:13px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )
        cancel.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.10);color:#6B5A8A;"
            "border:1px solid rgba(109,40,217,0.22);"
            "border-radius:11px;font-weight:600;font-size:13px;}"
            "QPushButton:hover{color:#EDE0FF;border-color:#7C3AED;}"
        )
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        bl.addLayout(btn_row)

        cl.addWidget(body)
        self._render_page()

    def _dot_style(self, active):
        if active:
            return ("QPushButton{background:#8B5CF6;border:none;border-radius:4px;}"
                    "QPushButton:hover{background:#A78BFA;}")
        return ("QPushButton{background:rgba(109,40,217,0.22);border:none;border-radius:4px;}"
                "QPushButton:hover{background:rgba(109,40,217,0.40);}")

    def _render_page(self):
        # Clear grid
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(PROFILE_EMOJIS)
        total_pages = math.ceil(total / self.PAGE_SIZE)
        self._page = max(0, min(self._page, total_pages - 1))

        start = self._page * self.PAGE_SIZE
        page_emojis = PROFILE_EMOJIS[start:start + self.PAGE_SIZE]

        for idx, em in enumerate(page_emojis):
            btn = QPushButton(em)
            btn.setFixedSize(44, 42)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._em_style(em == self._avatar))
            btn.clicked.connect(lambda _, e=em, b=btn: self._pick(e, b))
            self._grid_layout.addWidget(btn, idx // self.COLS, idx % self.COLS)

        # Update pagination controls
        self._page_lbl.setText(
            f"PAGE  {self._page + 1}  /  {total_pages}"
            f"   ·   {start + 1}–{min(start + self.PAGE_SIZE, total)} of {total}"
        )
        self._prev_btn.setEnabled(self._page > 0)
        self._next_btn.setEnabled(self._page < total_pages - 1)

        for i, d in enumerate(self._dots):
            d.setStyleSheet(self._dot_style(i == self._page))

    def _turn_page(self, delta):
        self._page += delta
        self._render_page()

    def _go_page(self, pg):
        self._page = pg
        self._render_page()

    def _em_style(self, sel):
        if sel:
            return ("QPushButton{background:rgba(139,92,246,0.35);"
                    "border:2px solid #8B5CF6;border-radius:10px;font-size:20px;}")
        return ("QPushButton{background:rgba(109,40,217,0.08);"
                "border:1px solid rgba(109,40,217,0.18);border-radius:10px;font-size:20px;}"
                "QPushButton:hover{background:rgba(109,40,217,0.24);border-color:#7C3AED;}")

    def _pick(self, em, clicked_btn):
        self._avatar = em
        self._preview_lbl.setText(em)
        # Update styles on current page
        for i in range(self._grid_layout.count()):
            w = self._grid_layout.itemAt(i).widget()
            if isinstance(w, QPushButton):
                w.setStyleSheet(self._em_style(w.text() == em))

    def _save(self):
        save_profile(self._usr_edit.text().strip() or "FluxUser", self._avatar)
        self.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 62:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos = None


# ── Right Nav Panel ────────────────────────────────────────────────────────
# ── Discord-style Switch button ────────────────────────────────────────────
class DiscordNavButton(QPushButton):
    """Nav button that shows the Discord logo (blurple) + 'Switch' label."""
    def __init__(self, label="Switch"):
        super().__init__()
        self._label = label
        self._active = False
        self._hover = False
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self.setAttribute(Qt.WA_Hover)

    def set_active(self, v):
        self._active = v; self.update()

    def enterEvent(self, e): self._hover = True; self.update()
    def leaveEvent(self, e): self._hover = False; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Background (active / hover)
        if self._active:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(109, 40, 217, 55))
            p.drawRoundedRect(0, 0, W, H, 12, 12)
        elif self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(109, 40, 217, 30))
            p.drawRoundedRect(0, 0, W, H, 12, 12)

        # Draw icon + label text
        text_col = QColor("#E0D8FF") if self._active else (QColor("#A090CC") if self._hover else QColor("#6B5A8A"))
        p.setPen(text_col)
        font = p.font()
        font.setPixelSize(13)
        font.setWeight(QFont.Bold)
        p.setFont(font)
        from PySide6.QtCore import QRect as _QRect
        p.drawText(_QRect(12, 0, W - 12, H), Qt.AlignVCenter | Qt.AlignLeft, "  " + self._label)


# ── New Profile Dialog ────────────────────────────────────────────────────
class NewProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Profile")
        self.setFixedSize(380, 480)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.result_name   = "FluxUser"
        self.result_avatar = "🦊"
        self._selected_av  = "🦊"
        self._drag_pos     = None

        outer = QVBoxLayout(self); outer.setContentsMargins(12,12,12,12)
        card = QWidget(); card.setObjectName("fluxDialog")
        card.setStyleSheet(
            "QWidget#fluxDialog{background:#0F0D1E;"
            "border:1px solid rgba(109,40,217,0.45);"
            "border-radius:18px;}"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40); shadow.setOffset(0,4)
        shadow.setColor(QColor(109,40,217,160))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        cl = QVBoxLayout(card); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)

        # Header
        hdr = QWidget(); hdr.setFixedHeight(52)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1A1428,stop:1 #0F0D1E);"
            "border-top-left-radius:17px;border-top-right-radius:17px;"
            "border-bottom:1px solid rgba(109,40,217,0.20);"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(18,0,14,0); hl.setSpacing(10)
        title = QLabel("New Profile")
        title.setStyleSheet("color:#EDE8FF;font-size:15px;font-weight:800;letter-spacing:1.5px;background:transparent;border:none;")
        xbtn = QPushButton("✕"); xbtn.setFixedSize(28,28); xbtn.setCursor(Qt.PointingHandCursor)
        xbtn.setStyleSheet("QPushButton{background:transparent;color:#4A3370;border:none;font-size:13px;border-radius:7px;}QPushButton:hover{background:#ff2d6f;color:white;}")
        xbtn.clicked.connect(self.reject)
        hl.addWidget(title); hl.addStretch(); hl.addWidget(xbtn)
        cl.addWidget(hdr)

        body = QWidget(); bl = QVBoxLayout(body); bl.setContentsMargins(18,16,18,18); bl.setSpacing(12)

        # Avatar preview + name
        top_row = QHBoxLayout(); top_row.setSpacing(14)
        self._av_preview = QLabel("🦊"); self._av_preview.setFixedSize(56,56)
        self._av_preview.setAlignment(Qt.AlignCenter)
        self._av_preview.setStyleSheet(
            "font-size:32px;background:rgba(109,40,217,0.14);"
            "border:2px solid rgba(109,40,217,0.38);border-radius:14px;"
        )
        right_col = QVBoxLayout(); right_col.setSpacing(6)
        name_hint = QLabel("Username")
        name_hint.setStyleSheet("color:#6B5A8A;font-size:10px;font-weight:700;letter-spacing:1.5px;background:transparent;border:none;")
        self._name_edit = QLineEdit(); self._name_edit.setPlaceholderText("FluxUser"); self._name_edit.setFixedHeight(38)
        self._name_edit.setStyleSheet(
            "QLineEdit{background:#0E0C1E;border:1px solid rgba(109,40,217,0.28);"
            "border-radius:10px;padding:0 12px;color:#E0D8FF;font-size:13px;}"
            "QLineEdit:focus{border:1.5px solid #7C3AED;}"
        )
        right_col.addWidget(name_hint); right_col.addWidget(self._name_edit)
        top_row.addWidget(self._av_preview); top_row.addLayout(right_col)
        bl.addLayout(top_row)

        # Emoji grid
        try:
            from core.profile import PROFILE_EMOJIS as _EMOJIS
        except Exception:
            _EMOJIS = ["🦊","🐺","🐉","🦁","🐯","🐻","🐼","🦝","🤖","👾"]
        grid_wrap = QFrame()
        grid_wrap.setStyleSheet(
            "QFrame{background:rgba(109,40,217,0.06);"
            "border:1px solid rgba(109,40,217,0.14);border-radius:12px;}"
            "QFrame QWidget{background:transparent;}"
        )
        grid = QGridLayout(grid_wrap); grid.setContentsMargins(8,8,8,8); grid.setSpacing(4)
        cols = 10
        for idx, em in enumerate(_EMOJIS[:120]):
            btn = QPushButton(em); btn.setFixedSize(30,28); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{background:transparent;border:none;border-radius:6px;font-size:14px;}"
                "QPushButton:hover{background:rgba(109,40,217,0.20);}"
            )
            btn.clicked.connect(lambda _, e=em: self._pick_av(e))
            grid.addWidget(btn, idx // cols, idx % cols)
        bl.addWidget(grid_wrap)

        # Save / Cancel
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel = QPushButton("Cancel"); save = QPushButton("Create Profile")
        for b in (cancel, save): b.setFixedHeight(40); b.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet("QPushButton{background:rgba(109,40,217,0.10);color:#9888C0;border:1px solid rgba(109,40,217,0.25);border-radius:11px;font-weight:700;}QPushButton:hover{background:rgba(109,40,217,0.20);color:#EDE0FF;}")
        save.setStyleSheet("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6D28D9,stop:1 #8B5CF6);color:white;border:none;border-radius:11px;font-weight:700;}QPushButton:hover{background:#7C3AED;}")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        bl.addLayout(btn_row)
        cl.addWidget(body)

    def _pick_av(self, em):
        self._selected_av = em
        self._av_preview.setText(em)

    def _save(self):
        self.result_name   = self._name_edit.text().strip() or "FluxUser"
        self.result_avatar = self._selected_av
        self.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 60:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos = None


class NavPanel(QFrame):
    """
    Collapsible RIGHT-side navigation panel — 1Password style.
    Collapses to 52px icon strip, expands to 200px on toggle.
    Pages: Dashboard | Vault | Reports | Account
    """
    W_COL = 52
    W_EXP = 200

    PAGES_ALL = [
        ("", "Dashboard",  "dashboard",  False),
        ("", "Generate",   "generate",   False),
        ("", "Vault",      "vault",      False),
        ("", "Reports",    "reports",    False),
        ("", "Notes",      "notes",      True),   # PLUS only
        ("", "Audit Log",  "audit",      True),   # PLUS only
        ("", "Settings",   "settings",   False),
        ("", "Account",    "account",    False),
        ("", "Switch",     "switch",     False),
    ]
    @property
    def PAGES(self):
        plus = is_plus()
        return [(icon,label,page) for icon,label,page,plus_only in self.PAGES_ALL
                if not plus_only or plus]

    def __init__(self, on_page, is_plus=False):
        super().__init__()
        self._on_page   = on_page
        self._is_plus   = is_plus
        self._current   = "dashboard"
        self._expanded  = True
        self._anim_w    = self.W_EXP
        self._target_w  = self.W_EXP

        self.setFixedWidth(self.W_EXP)
        self.setObjectName("navPanel")
        self.setStyleSheet(
            "QFrame#navPanel{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #181430,stop:1 #12101E);"
            "border-left:1px solid rgba(109,40,217,0.20);"
            "border-top-right-radius:16px;"
            "border-bottom-right-radius:16px;}"
            "QFrame#navPanel QWidget{background:transparent;}"
            "QFrame#navPanel QLabel{background:transparent;border:none;}"
        )

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(10)
        self._anim_timer.timeout.connect(self._tick)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 12, 6, 12)
        root.setSpacing(3)

        # Profile mini button (top)
        self._prof_btn = QPushButton()
        self._prof_btn.setFixedHeight(44)
        self._prof_btn.setCursor(Qt.PointingHandCursor)
        self._prof_btn.clicked.connect(self._open_profile)
        self._refresh_prof()
        root.addWidget(self._prof_btn)

        # Hairline
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:rgba(109,40,217,0.18);max-height:1px;border:none;")
        root.addWidget(sep)
        root.addSpacing(4)

        # Nav buttons
        self._btns = {}
        self._nav_root = root
        for icon, label, page in self.PAGES:
            b = self._mk_btn(icon, label, page)
            root.addWidget(b)
            self._btns[page] = b

        root.addStretch()

        # ── Bottom separator ──
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background:rgba(109,40,217,0.18);max-height:1px;border:none;")
        root.addWidget(sep2)
        root.addSpacing(4)

        # ── Lock button ──
        self._lock_btn = QPushButton("🔒  Lock")
        self._lock_btn.setFixedHeight(38)
        self._lock_btn.setCursor(Qt.PointingHandCursor)
        self._lock_btn.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.20);border-radius:11px;"
            "font-size:12px;font-weight:700;text-align:left;padding-left:12px;}"
            "QPushButton:hover{background:rgba(220,30,60,0.20);color:#ff6b8a;"
            "border-color:rgba(220,30,60,0.45);}"
        )
        root.addWidget(self._lock_btn)
        root.addSpacing(2)

        self._set_active("dashboard")
        self._update_labels()   # always show text
        # Glow tracker for active button
        self._glow_phase = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(60)
        self._glow_timer.timeout.connect(self._tick_glow)
        self._glow_timer.start()

    def rebuild_nav_buttons(self):
        """
        Completely rebuild the nav button list from PAGES.
        Called after PLUS is activated so Notes/Audit appear in the correct order,
        with no duplicates.
        """
        # Remove all existing nav buttons from layout and destroy them
        for page, btn in list(self._btns.items()):
            self._nav_root.removeWidget(btn)
            btn.deleteLater()
        self._btns.clear()

        # Find the stretch item index — buttons must be inserted before it
        stretch_idx = None
        for i in range(self._nav_root.count()):
            item = self._nav_root.itemAt(i)
            if item and item.spacerItem():
                stretch_idx = i
                break
        if stretch_idx is None:
            stretch_idx = max(0, self._nav_root.count() - 3)

        # Re-insert all buttons in the correct PAGES_ALL order
        for offset, (icon, label, page) in enumerate(self.PAGES):
            b = self._mk_btn(icon, label, page)
            self._nav_root.insertWidget(stretch_idx + offset, b)
            self._btns[page] = b

        self._set_active(self._current)
        self._update_labels()

    def _tick_glow(self):
        self._glow_phase = (self._glow_phase + 0.05) % (2 * 3.14159)
        for page, btn in self._btns.items():
            if page == self._current:
                btn.update()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _mk_btn(self, icon, label, page):
        if page == "switch":
            b = DiscordNavButton(label)
        else:
            b = QPushButton(icon + "  " + label if icon else label)
            b.setFixedHeight(40)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(self._btn_style(False))
        b.clicked.connect(lambda _, p=page: self._nav(p))
        return b

    def _btn_style(self, active):
        if active:
            return (
                "QPushButton{"
                "background:rgba(109,40,217,0.22);"
                "color:#E0D8FF;"
                "border:none;"
                "border-radius:12px;"
                "font-size:13px;"
                "font-weight:700;"
                "text-align:left;"
                "padding-left:12px;"
                "}"
            )
        return (
            "QPushButton{"
            "background:transparent;"
            "color:#6B5A8A;"
            "border:none;"
            "border-radius:12px;"
            "font-size:13px;"
            "font-weight:600;"
            "text-align:left;"
            "padding-left:12px;"
            "}"
            "QPushButton:hover{"
            "background:rgba(109,40,217,0.12);"
            "color:#A090CC;"
            "}"
        )

    def _set_active(self, page):
        self._current = page
        for pg, b in self._btns.items():
            if isinstance(b, DiscordNavButton):
                b.set_active(pg == page)
            else:
                b.setStyleSheet(self._btn_style(pg == page))

    def _nav(self, page):
        self._set_active(page)
        self._on_page(page)

    def _refresh_prof(self):
        prof = load_profile()
        av   = prof.get("avatar", "🦊")
        name = prof.get("username", "FluxUser")
        self._prof_btn.setText(f"{av}  {name}")
        self._prof_btn.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.12);color:#c4b4d8;"
            "border:1px solid rgba(109,40,217,0.22);border-radius:11px;"
            "font-size:13px;font-weight:700;text-align:left;padding-left:10px;}"
            "QPushButton:hover{background:rgba(123,47,255,0.22);color:#e2d5f8;}"
        )

    def _open_profile(self):
        dlg = ProfileDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_prof()

    def _toggle(self):
        self._expanded = not self._expanded
        self._target_w = self.W_EXP if self._expanded else self.W_COL
        self._tog.setText("‹" if self._expanded else "›")
        self._anim_timer.start()
        self._update_labels()

    def _update_labels(self):
        """Show/hide text labels in buttons when expanded."""
        pages = self.PAGES
        for i, (pg, btn) in enumerate(self._btns.items()):
            if isinstance(btn, DiscordNavButton):
                btn.set_active(pg == self._current)
            elif i < len(pages):
                icon, label, page = pages[i]
                btn.setText(f"{icon}  {label}")
                btn.setStyleSheet(self._btn_style(pg == self._current))
        self._refresh_prof()

    def _tick(self):
        diff = self._target_w - self._anim_w
        self._anim_w += diff * 0.22
        if abs(diff) < 0.8:
            self._anim_w = self._target_w
            self._anim_timer.stop()
        self.setFixedWidth(int(self._anim_w))


# ── Dashboard ──────────────────────────────────────────────────────────────

# ── Enter PLUS Code Dialog ────────────────────────────────────────────────────
class EnterCodeDialog(QDialog):
    """
    Clean dialog for entering a one-time PLUS activation code.
    Format: FLUX-XXXX-XXXX-XXXX
    Validates via HMAC — no internet required.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activate FluxKey PLUS")
        self.setFixedWidth(440)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("fluxDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        hdr_row = QHBoxLayout(); hdr_row.setSpacing(12)
        badge = QLabel("✦")
        badge.setFixedSize(42, 42); badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #5b21b6,stop:1 #7c3aed);"
            "border-radius:12px;color:white;font-size:20px;font-weight:900;"
        )
        hdr_txt = QVBoxLayout(); hdr_txt.setSpacing(2)
        hdr_title = QLabel("Activate FluxKey PLUS")
        hdr_title.setStyleSheet(
            "color:#e2d5f8;font-size:16px;font-weight:800;letter-spacing:0.3px;"
        )
        hdr_sub = QLabel("Enter your one-time activation code below")
        hdr_sub.setStyleSheet("color:#4A3370;font-size:11px;")
        hdr_txt.addWidget(hdr_title); hdr_txt.addWidget(hdr_sub)
        hdr_row.addWidget(badge); hdr_row.addLayout(hdr_txt); hdr_row.addStretch()
        layout.addLayout(hdr_row)
        layout.addSpacing(24)

        # ── Code format hint ─────────────────────────────────────────────
        fmt_lbl = QLabel("FORMAT:  FLUX-XXXX-XXXX-XXXX-XXXX")
        fmt_lbl.setStyleSheet(
            "color:#4A3370;font-size:9px;font-weight:800;letter-spacing:2.5px;"
        )
        layout.addWidget(fmt_lbl)
        layout.addSpacing(6)

        # ── Code input ───────────────────────────────────────────────────
        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("FLUX-XXXX-XXXX-XXXX-XXXX")
        self._code_input.setFixedHeight(52)
        self._code_input.setMaxLength(24)  # FLUX- (5) + 4*4 chars + 3 dashes = 24
        self._code_input.setAlignment(Qt.AlignCenter)
        self._code_input.setStyleSheet(
            "QLineEdit{background:#0d0a1e;border:2px solid #261840;"
            "border-radius:12px;padding:0 16px;"
            "color:#a78bfa;font-size:16px;font-weight:700;"
            "font-family:'JetBrains Mono','Consolas',monospace;"
            "letter-spacing:2px;}"
            "QLineEdit:focus{border-color:#7C3AED;background:#110e24;"
            "color:#c4b4d8;}"
            "QLineEdit::placeholder{color:#2a1f45;font-size:13px;letter-spacing:1px;}"
        )
        # Auto-format as user types: insert dashes at correct positions
        self._code_input.textChanged.connect(self._auto_format)
        layout.addWidget(self._code_input)
        layout.addSpacing(10)

        # ── Status message ───────────────────────────────────────────────
        self._msg_lbl = QLabel("")
        self._msg_lbl.setFixedHeight(18)
        self._msg_lbl.setAlignment(Qt.AlignCenter)
        self._msg_lbl.setStyleSheet("font-size:11px;font-weight:600;background:transparent;border:none;")
        layout.addWidget(self._msg_lbl)
        layout.addSpacing(20)

        # ── Buttons ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(44); cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton{background:#0d0a1e;color:#5A4070;"
            "border:1px solid #261840;border-radius:11px;"
            "font-weight:600;font-size:13px;}"
            "QPushButton:hover{color:#e2d5f8;border-color:#7C3AED;}"
        )
        cancel_btn.clicked.connect(self.reject)
        # Disable default/autodefault so Enter never triggers either button
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)

        self._activate_btn = QPushButton("✦  Activate PLUS")
        self._activate_btn.setFixedHeight(44); self._activate_btn.setCursor(Qt.PointingHandCursor)
        self._activate_btn.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #5b21b6,stop:1 #7c3aed);"
            "color:white;border:none;border-radius:11px;"
            "font-weight:800;font-size:13px;letter-spacing:0.5px;}"
            "QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6d28d9,stop:1 #8b5cf6);}"
            "QPushButton:pressed{background:#4c1d95;}"
            "QPushButton:disabled{background:#1a1530;color:#3d2a58;}"
        )
        self._activate_btn.setDefault(False)
        self._activate_btn.setAutoDefault(False)
        self._activate_btn.clicked.connect(self._do_activate)

        btn_row.addWidget(cancel_btn, 1)
        btn_row.addWidget(self._activate_btn, 2)
        layout.addLayout(btn_row)

        self._formatting = False   # guard against recursive textChanged

    def keyPressEvent(self, e):
        """Block Enter/Return from triggering anything in this dialog."""
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            e.ignore()
            return
        super().keyPressEvent(e)

    def _auto_format(self, text: str):
        """Auto-insert FLUX- prefix and dashes as user types. Format: FLUX-XXXX-XXXX-XXXX-XXXX"""
        if self._formatting:
            return
        self._formatting = True
        # Strip to alphanumeric only, uppercase
        raw = "".join(c for c in text.upper() if c.isalnum())
        # Remove FLUX prefix if user typed it
        if raw.startswith("FLUX"):
            raw = raw[4:]
        # Cap at 16 chars (4 groups × 4)
        raw = raw[:16]
        # Chunk into groups of 4
        chunks = [raw[i:i+4] for i in range(0, len(raw), 4)]
        formatted = "FLUX-" + "-".join(chunks) if chunks else ""
        cursor_pos = len(formatted)
        self._code_input.setText(formatted)
        self._code_input.setCursorPosition(cursor_pos)
        self._msg_lbl.setText("")
        self._formatting = False

    def _do_activate(self):
        code = self._code_input.text().strip()
        if not code:
            self._set_msg("Please enter your activation code.", error=True)
            return

        self._activate_btn.setEnabled(False)
        self._activate_btn.setText("Checking…")

        try:
            from core.license_codes import validate_and_activate, CodeResult
            result, message = validate_and_activate(code)
        except ImportError:
            self._set_msg("license_codes module not found.", error=True)
            self._activate_btn.setEnabled(True)
            self._activate_btn.setText("✦  Activate PLUS")
            return

        if result == CodeResult.OK:
            self._set_msg("✓  Activated! Updating…", error=False)
            self._activate_btn.setText("✓  Done")
            QTimer.singleShot(600, self.accept)
        else:
            self._set_msg(message, error=True)
            self._activate_btn.setEnabled(True)
            self._activate_btn.setText("✦  Activate PLUS")

    def _set_msg(self, text: str, error: bool = True):
        col = "#f87171" if error else "#22c55e"
        self._msg_lbl.setStyleSheet(
            f"color:{col};font-size:11px;font-weight:600;"
            "background:transparent;border:none;"
        )
        self._msg_lbl.setText(text)


class Dashboard(QWidget):

    def __init__(self, icon: QIcon = None):
        super().__init__()
        self.generator = PasswordGenerator()
        self.vault = Vault()
        self._vault_meta = VaultMeta()
        self._drag_pos = None
        self._icon = icon
        self._scan_active = False
        self._closing = False          # set True in _logout to silence timer callbacks
        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._run_scan)
        self._last_vault_hash = ""
        self._vault_page = 0
        self._vault_page_size = 5
        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.setSingleShot(True)
        self._clipboard_timer.timeout.connect(self._clear_clipboard)
        self._last_activity = time.time()
        self._lock_warned    = False   # have we shown the 30s warning?

        # 1-second ticker drives countdown + warning
        self._auto_lock_timer = QTimer(self)
        self._auto_lock_timer.timeout.connect(self._tick_auto_lock)
        self._auto_lock_timer.start(1000)

        # Passive XP timer — started after UI is ready
        QTimer.singleShot(0, self._start_xp_timers)

        self.setWindowTitle("FluxKey Plus")
        self.resize(940, 620)
        self.setMinimumSize(860, 560)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if icon and not icon.isNull():
            self.setWindowIcon(icon)

        # Margins give the custom border glow room to draw without clipping
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10,10,10,10)

        self._card = QWidget(); self._card.setObjectName("dashCard")
        self._card.setStyleSheet(
            "QWidget#dashCard{background:#060410;border:none;border-radius:18px;}"
        )
        card_l = QVBoxLayout(self._card); card_l.setContentsMargins(0,0,0,0); card_l.setSpacing(0)
        self._border_hue = 0.0
        # Animated border glow — 30fps breathing purple ring
        self._border_phase = 0.0
        self._border_timer = QTimer(self)
        self._border_timer.setInterval(33)
        self._border_timer.timeout.connect(self._tick_border)
        self._border_timer.start()
        outer.addWidget(self._card)

        # Title bar
        tbar=QWidget(); tbar.setFixedHeight(40); tbar.setObjectName("titleBar")
        tbl=QHBoxLayout(tbar); tbl.setContentsMargins(16,0,12,0); tbl.setSpacing(8)

        # FK badge — compact
        hex_lbl=QLabel("FK"); hex_lbl.setFixedSize(26,26); hex_lbl.setAlignment(Qt.AlignCenter)
        hex_lbl.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #6D28D9,stop:1 #8B5CF6);"
            "border-radius:7px;color:white;font-size:10px;font-weight:800;letter-spacing:1px;border:none;"
        )
        title_lbl=QLabel("FluxKey"); title_lbl.setStyleSheet("color:white;font-size:16px;font-weight:800;letter-spacing:3px;background:transparent;")
        # PLUS badge — animated shimmer wordmark, no background
        plus_lbl = PlusBadge()
        plus_lbl.setVisible(is_plus())
        plus_lbl.setVisible(is_plus())
        self._plus_lbl = plus_lbl
        tbl.addWidget(hex_lbl); tbl.addSpacing(4); tbl.addWidget(title_lbl); tbl.addSpacing(6); tbl.addWidget(plus_lbl); tbl.addStretch()

        # Update available button (hidden until needed)
        self._update_btn=QPushButton("  Update Available")
        self._update_btn.setFixedHeight(28); self._update_btn.setCursor(Qt.PointingHandCursor)
        self._update_btn.setVisible(False)
        self._update_btn.setStyleSheet("QPushButton{background:#0d1a0d;color:#4ade80;border:1px solid #166534;border-radius:7px;font-size:11px;font-weight:700;padding:0 12px;}QPushButton:hover{background:#166534;color:white;}")
        self._update_btn.clicked.connect(self._open_update_dialog)
        self._latest_version=None
        tbl.addWidget(self._update_btn); tbl.addSpacing(6)

        # Scan status pill
        self._scan_dot = ScanIndicator()
        self._scan_dot.set_status("idle")
        self._scan_dot.setVisible(False)
        self._scan_lbl = self._scan_dot
        tbl.addWidget(self._scan_dot)
        tbl.addSpacing(4)

        # Auto-lock countdown label — hidden until warning phase
        self._lock_countdown_lbl = QLabel("")
        self._lock_countdown_lbl.setVisible(False)
        self._lock_countdown_lbl.setStyleSheet(
            "color:#f59e0b;font-size:11px;font-weight:700;letter-spacing:0.5px;"
        )
        tbl.addWidget(self._lock_countdown_lbl)
        tbl.addSpacing(12)

       # Discord button — house emoji
        self._discord_btn = QPushButton("🎁")
        self._discord_btn.setFixedSize(30, 30)
        self._discord_btn.setCursor(Qt.PointingHandCursor)
        self._discord_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;font-size:16px;border-radius:7px;}"
            "QPushButton:hover{background:rgba(109,40,217,0.18);}"
        )
        self._discord_btn.clicked.connect(lambda: webbrowser.open("https://discord.gg/Nxj2upuyj8"))
        tbl.addWidget(self._discord_btn); tbl.addSpacing(2)
        self._gear_btn=GearButton(); self._gear_btn.clicked.connect(self._open_settings); tbl.addWidget(self._gear_btn); tbl.addSpacing(8)

        for sym, tip, fn, is_close in [("-", "Minimise", self.showMinimized, False), ("X", "Close", self.close, True)]:
            b = QPushButton(sym); b.setFixedSize(34, 30); b.setCursor(Qt.PointingHandCursor)
            hcol = "#ff2d6f" if is_close else "#7C3AED"
            b.setStyleSheet(f"QPushButton{{background:transparent;color:#5B3A88;border:none;font-size:11px;border-radius:7px;}}QPushButton:hover{{background:{hcol};color:white;}}")
            b.clicked.connect(fn); tbl.addWidget(b)
        card_l.addWidget(tbar)

        # Body
        body_w=QWidget(); body_w.setObjectName("dashBody")
        body=QHBoxLayout(body_w); body.setContentsMargins(8,6,8,10); body.setSpacing(8)

        # LEFT PANEL
        left=QFrame(); left.setObjectName("panel"); left.setFixedWidth(210)
        ll=QVBoxLayout(left); ll.setContentsMargins(10,10,10,10); ll.setSpacing(6)

        # ── Generator / Character Size card ──────────────────────────────
        char_wrap = QFrame(); char_wrap.setObjectName("charCard")
        char_wrap.setStyleSheet(
            "QFrame#charCard{background:transparent;border:none;}"
            "QFrame#charCard QLabel{background:transparent;border:none;}"
        )
        char_l = QVBoxLayout(char_wrap); char_l.setContentsMargins(12,10,12,10); char_l.setSpacing(8)
        char_l.addWidget(self._sec("GENERATOR"))
        char_l.addWidget(self._lbl("Character Size"))
        arrow_row = QHBoxLayout(); arrow_row.setSpacing(6)
        arrow_row.addStretch()
        self.len_sl = LengthStepper(initial=16)
        self.len_val = self.len_sl
        self.len_sl.valueChanged.connect(self._update_strength)
        self.len_sl.valueChanged.connect(lambda _: self._activity())
        arrow_row.addWidget(self.len_sl)
        arrow_row.addStretch()
        char_l.addLayout(arrow_row)
        ll.addWidget(char_wrap)

        # ── Control surface card ────────────────────────────────────────
        ctrl=QFrame(); ctrl.setObjectName("ctrlCard")
        ctrl.setStyleSheet(
            "QFrame#ctrlCard{background:transparent;border:none;}"
            "QFrame#ctrlCard QLabel{background:transparent;border:none;}"
        )
        ctl=QVBoxLayout(ctrl); ctl.setContentsMargins(8, 7, 8, 7); ctl.setSpacing(8)

        s1=QFrame(); s1.setObjectName("cs1"); s1.setFrameShape(QFrame.HLine)
        s1.setStyleSheet("QFrame#cs1{background:rgba(123,47,255,0.14);max-height:1px;border:none;}")
        ctl.addWidget(s1)
        ctl.addSpacing(2)

        self.upper=self._cb("Uppercase  A-Z")
        self.numbers=self._cb("Numbers  0-9")
        self.symbols=self._cb("Symbols  !@#$")
        self.no_amb=self._cb("No Ambiguous  (0Ol1I)")
        self.no_amb.setChecked(False)
        self.no_rep=self._cb("No Repeats")
        self.no_rep.setChecked(False)
        self.keyphrase_cb=self._cb("Keyphrase Mode")
        self.keyphrase_cb.setChecked(False)
        for cb in (self.upper, self.numbers, self.symbols, self.no_amb, self.no_rep, self.keyphrase_cb):
            ctl.addWidget(cb)
        for cb in (self.upper, self.numbers, self.symbols, self.no_amb, self.no_rep, self.keyphrase_cb):
            cb.stateChanged.connect(self._update_strength)
            cb.stateChanged.connect(lambda _: self._activity())

        # Custom keyphrase input — shown only when Keyphrase Mode is checked
        self._keyphrase_input = QLineEdit()
        self._keyphrase_input.setPlaceholderText("Custom keyphrase (optional)…")
        self._keyphrase_input.setFixedHeight(26)
        self._keyphrase_input.setVisible(False)
        self._keyphrase_input.setStyleSheet(
            "QLineEdit{background:#06030f;border:1px solid rgba(123,47,255,0.35);"
            "border-radius:8px;padding:0 10px;color:#c084fc;"
            "font-family:'JetBrains Mono','Consolas',monospace;font-size:11px;}"
            "QLineEdit:focus{border-color:#8B5CF6;background:#0a0618;}"
            "QLineEdit::placeholder{color:#3a2255;}"
        )
        self._keyphrase_input.textChanged.connect(lambda _: self._activity())
        ctl.addWidget(self._keyphrase_input)
        self.keyphrase_cb.stateChanged.connect(self._toggle_keyphrase_input)

        s2=QFrame(); s2.setObjectName("cs2"); s2.setFrameShape(QFrame.HLine)
        s2.setStyleSheet("QFrame#cs2{background:rgba(123,47,255,0.14);max-height:1px;border:none;}")
        ctl.addWidget(s2)

        str_hdr=QHBoxLayout(); str_hdr.setSpacing(0)
        self.str_lbl=QLabel("STRENGTH")
        self.str_lbl.setStyleSheet(
            "color:#3a2a55;font-size:9px;letter-spacing:2px;font-weight:800;"
            "background:transparent;border:none;"
        )
        self.str_val_lbl=QLabel("Weak")
        self.str_val_lbl.setStyleSheet(
            "color:#f59e0b;font-size:10px;font-weight:800;letter-spacing:0.5px;"
            "background:transparent;border:none;"
        )
        str_hdr.addWidget(self.str_lbl); str_hdr.addStretch(); str_hdr.addWidget(self.str_val_lbl)
        ctl.addLayout(str_hdr)
        self.str_bar=StrengthMeter(height=5); ctl.addWidget(self.str_bar)
        self._str_hint=QLabel("")
        self._str_hint.setStyleSheet(
            "color:#3a2550;font-size:10px;font-style:italic;background:transparent;border:none;"
        )
        self._str_hint.setWordWrap(True)
        ctl.addWidget(self._str_hint)
        ll.addWidget(ctrl)
        ll.addStretch()

        # Power button with Vault Scan label
        self.power = PowerBtn()
        self.power.clicked.connect(self._toggle_power)
        pw_col = QVBoxLayout(); pw_col.setSpacing(5); pw_col.setContentsMargins(0,0,0,0)
        pw_col.setAlignment(Qt.AlignCenter)
        pw_col.addWidget(self.power, 0, Qt.AlignHCenter)
        self._pw_title_lbl = QLabel("Vault Scan")
        self._pw_title_lbl.setAlignment(Qt.AlignCenter)
        self._pw_title_lbl.setStyleSheet("color:#9060c8;font-size:11px;font-weight:700;"
            "letter-spacing:1px;background:transparent;border:none;")
        self._pw_sub_lbl = QLabel("Press to scan vault")
        self._pw_sub_lbl.setAlignment(Qt.AlignCenter)
        self._pw_sub_lbl.setStyleSheet("color:#3D2A58;font-size:9px;"
            "letter-spacing:0.5px;background:transparent;border:none;")
        pw_col.addWidget(self._pw_title_lbl)
        pw_col.addWidget(self._pw_sub_lbl)
        pw_row = QHBoxLayout()
        pw_row.addStretch(); pw_row.addLayout(pw_col); pw_row.addStretch()
        ll.addLayout(pw_row)

        # RIGHT PANEL — Generate page (centred card layout)
        # ── Generate page — clean, premium redesign ──────────────────
        right = QFrame(); right.setObjectName("panel")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(32, 28, 32, 28)
        rl.setSpacing(0)

        # ── TOP: Section header ───────────────────────────────────────
        rl.addWidget(self._sec("GENERATOR"))
        rl.addSpacing(20)

        # ── Output card — large, prominent ───────────────────────────
        of = QFrame(); of.setObjectName("outputFrame")
        of.setFixedHeight(120)
        of.setStyleSheet(
            "QFrame#outputFrame{"
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #1A1630,stop:1 #110E25);"
            "border:2px solid rgba(109,40,217,0.55);"
            "border-radius:18px;}"
            "QFrame#outputFrame QLabel{background:transparent;border:none;}"
        )
        ofl = QVBoxLayout(of); ofl.setContentsMargins(20,14,20,14); ofl.setSpacing(10)

        out_hdr = QHBoxLayout()
        lbl_pw = QLabel("GENERATED PASSWORD")
        lbl_pw.setStyleSheet(
            "color:#5A4A7A;font-size:9px;font-weight:800;letter-spacing:3px;"
            "background:transparent;border:none;"
        )
        enc = QLabel("AES-256")
        enc.setStyleSheet(
            "color:#8B5CF6;font-size:9px;font-weight:800;letter-spacing:1.5px;"
            "background:rgba(109,40,217,0.14);border:1px solid rgba(109,40,217,0.35);"
            "border-radius:6px;padding:3px 10px;"
        )
        out_hdr.addWidget(lbl_pw); out_hdr.addStretch(); out_hdr.addWidget(enc)
        ofl.addLayout(out_hdr)

        self.output = QLineEdit()
        self.output.setPlaceholderText("Click  Generate  below...")
        self.output.setReadOnly(True)
        self.output.setObjectName("outputField")
        self.output.setFixedHeight(44)
        self.output.setStyleSheet(
            "QLineEdit#outputField{"
            "background:#0C0A1E;"
            "border:1.5px solid rgba(109,40,217,0.65);"
            "border-radius:10px;padding:0 16px;"
            "color:#C4A8FF;"
            "font-family:'JetBrains Mono','Consolas',monospace;"
            "font-size:16px;letter-spacing:2.5px;}"
            "QLineEdit#outputField:hover{border-color:rgba(139,92,246,0.85);}"
        )
        ofl.addWidget(self.output)
        self._copy_flash = CopyFlashOverlay(self.output)
        rl.addWidget(of)
        rl.addSpacing(12)

        # ── Strength meter ────────────────────────────────────────────
        str_row = QHBoxLayout()
        str_lbl = QLabel("STRENGTH")
        str_lbl.setStyleSheet(
            "color:#4A3370;font-size:9px;font-weight:800;letter-spacing:2px;"
            "background:transparent;border:none;"
        )
        self._str_val_lbl2 = QLabel("—")
        self._str_val_lbl2.setStyleSheet(
            "color:#8B5CF6;font-size:9px;font-weight:800;letter-spacing:1px;"
            "background:transparent;border:none;"
        )
        str_row.addWidget(str_lbl); str_row.addStretch(); str_row.addWidget(self._str_val_lbl2)
        rl.addLayout(str_row)
        rl.addSpacing(4)
        self.str_bar2 = StrengthMeter(height=6)
        rl.addWidget(self.str_bar2)
        rl.addSpacing(24)

        # ── GENERATE button — full width, prominent ───────────────────
        self.gen_btn = GenChargeBtn("⚡   GENERATE   ⚡")
        self.gen_btn.setFixedHeight(54)
        self.gen_btn.setStyleSheet(
            "QPushButton#btnPrimary{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #4C1D95,stop:0.35 #7C3AED,stop:0.65 #8B5CF6,stop:1 #9F67FF);"
            "color:white;border:none;border-radius:16px;"
            "font-size:16px;font-weight:900;letter-spacing:4px;"
            "border-top:1px solid rgba(255,255,255,0.18);}"
            "QPushButton#btnPrimary:hover{background:#7C3AED;}"
            "QPushButton#btnPrimary:pressed{background:#3B0E8C;}"
        )
        self.gen_btn.clicked.connect(self.generate)
        rl.addWidget(self.gen_btn)
        rl.addSpacing(14)

        # ── Action row: Copy + Save ───────────────────────────────────
        act_row = QHBoxLayout(); act_row.setSpacing(10)

        self.copy_btn = QPushButton("📋   Copy")
        self.copy_btn.setObjectName("genCopyBtn")
        self.copy_btn.setFixedHeight(44)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self._copy_btn_default_style = (
            "QPushButton#genCopyBtn{background:rgba(109,40,217,0.14);"
            "color:#A78BFA;border:1.5px solid rgba(109,40,217,0.40);"
            "border-radius:12px;font-size:13px;font-weight:700;}"
            "QPushButton#genCopyBtn:hover{background:rgba(109,40,217,0.28);color:#EDE0FF;"
            "border-color:rgba(139,92,246,0.70);}"
            "QPushButton#genCopyBtn:pressed{background:rgba(109,40,217,0.40);}"
        )
        self.copy_btn.setStyleSheet(self._copy_btn_default_style)
        self.copy_btn.clicked.connect(self.copy_pwd)

        self.save_btn = QPushButton("💾   Save to Vault")
        self.save_btn.setObjectName("genSaveBtn")
        self.save_btn.setFixedHeight(44)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn_default_style = (
            "QPushButton#genSaveBtn{background:rgba(34,197,94,0.10);"
            "color:#4ADE80;border:1.5px solid rgba(34,197,94,0.30);"
            "border-radius:12px;font-size:13px;font-weight:700;}"
            "QPushButton#genSaveBtn:hover{background:rgba(34,197,94,0.20);color:#86EFAC;"
            "border-color:rgba(34,197,94,0.55);}"
            "QPushButton#genSaveBtn:pressed{background:rgba(34,197,94,0.30);}"
        )
        self.save_btn.setStyleSheet(self._save_btn_default_style)
        self.save_btn.clicked.connect(self.save_pwd)

        act_row.addWidget(self.copy_btn); act_row.addWidget(self.save_btn)
        rl.addLayout(act_row)
        rl.addSpacing(10)

        # ── Show / Hide ───────────────────────────────────────────────
        self.show_btn = QPushButton("👁   Show / Hide Password")
        self.show_btn.setFixedHeight(38)
        self.show_btn.setCursor(Qt.PointingHandCursor)
        self.show_btn.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.07);"
            "color:#6B5A8A;border:1px solid rgba(109,40,217,0.18);"
            "border-radius:10px;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:rgba(109,40,217,0.14);color:#A090CC;"
            "border-color:rgba(109,40,217,0.35);}"
        )
        self.show_btn.clicked.connect(self._toggle_show)
        rl.addWidget(self.show_btn)
        rl.addSpacing(20)

        # ── Password info chips ───────────────────────────────────────
        chips_row = QHBoxLayout(); chips_row.setSpacing(8)
        for chip_text in ["🔒 Encrypted locally", "📋 Never transmitted", "⚡ Instant"]:
            chip = QLabel(chip_text)
            chip.setStyleSheet(
                "color:#4A3370;font-size:10px;font-weight:600;"
                "background:rgba(109,40,217,0.07);"
                "border:1px solid rgba(109,40,217,0.14);"
                "border-radius:8px;padding:4px 10px;"
            )
            chips_row.addWidget(chip)
        chips_row.addStretch()
        rl.addLayout(chips_row)

        rl.addStretch()

        # ── Stacked right pages (Vault is the right panel; others swap in) ──
        from PySide6.QtWidgets import QStackedWidget
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:transparent;")

        # Page 0 — Generate (password panel only)
        self._stack.addWidget(right)

        # Page 1 — Reports
        self._reports_page = self._build_reports_page()
        self._stack.addWidget(self._reports_page)

        # Page 2 — Account
        self._account_page = self._build_account_page()
        self._stack.addWidget(self._account_page)

        # Page 3 — Dashboard home
        self._dashboard_page = self._build_dashboard_page()
        self._stack.addWidget(self._dashboard_page)

        # Page 4 — Vault (dedicated vault-only page)
        self._vault_page_widget = self._build_vault_page()
        self._stack.addWidget(self._vault_page_widget)

        # Page 5 — Switch Profiles
        self._switch_page = self._build_switch_page()
        self._stack.addWidget(self._switch_page)

        # Page 6 — Notes (inline)
        self._notes_page = self._build_notes_page()
        self._stack.addWidget(self._notes_page)

        # Page 7 — Settings (inline)
        self._settings_page = self._build_settings_page()
        self._stack.addWidget(self._settings_page)

        # Page 8 — Audit Log (inline)
        self._audit_page = self._build_audit_page()
        self._stack.addWidget(self._audit_page)

        # Nav panel (right side)
        self._nav_panel = NavPanel(self._on_nav_page, is_plus=is_plus())
        self._nav_panel._lock_btn.clicked.connect(self._logout)

        body.addWidget(left)
        body.addWidget(self._stack)
        body.addWidget(self._nav_panel)
        card_l.addWidget(body_w)

        self._refresh_vault()
        self._update_strength()
        # Start on Dashboard page
        QTimer.singleShot(0, lambda: (self._stack.setCurrentIndex(3), self._refresh_dashboard_page()))

        # Apply saved theme


        QTimer.singleShot(2000,self._check_update)


    def paintEvent(self, ev):
        """No custom border glow — plain static border only."""
        super().paintEvent(ev)

    def showEvent(self, e):
        super().showEvent(e)
        self.setWindowOpacity(1.0)  # no fade — instant, no lag

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Keep flash overlay covering the output field
        if hasattr(self, '_copy_flash') and hasattr(self, 'output'):
            self._copy_flash.setGeometry(self.output.rect())
        # Reflow XP bar fill width whenever the window is resized
        if hasattr(self, '_xp_bar') and hasattr(self, '_xp_level_lbl'):
            self._refresh_xp_card()

    def _tick_border(self) -> None:
        if getattr(self, '_closing', False):
            return
        self._border_phase = (self._border_phase + 0.035) % (2 * math.pi)
        self.update()

    def paintEvent(self, e) -> None:
        """Draw an animated glowing purple border around the whole window."""
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        pulse = 0.5 + 0.5 * math.sin(self._border_phase)

        # The card sits inside 10px margins with border-radius:18px.
        # Border is drawn at m=5px from the window edge → radius = 18 + (10-5) = 23
        m = 5.0
        r = 23.0

        rect = QRectF(m, m, W - 2*m, H - 2*m)

        # ── Outer halo — wide, soft, low opacity ──────────────────────────
        halo_pen = QPen(QColor(109, 40, 217, int(30 + 20 * pulse)))
        halo_pen.setWidthF(9.0)
        p.setPen(halo_pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, r + 3, r + 3)

        # ── Mid glow — medium width, brighter ────────────────────────────
        mid_pen = QPen(QColor(139, 92, 246, int(70 + 40 * pulse)))
        mid_pen.setWidthF(3.0)
        p.setPen(mid_pen)
        p.drawRoundedRect(rect, r, r)

        # ── Sharp crisp inner border — always solid purple ────────────────
        sharp_pen = QPen(QColor(167, 139, 250, int(200 + 55 * pulse)))
        sharp_pen.setWidthF(1.5)
        p.setPen(sharp_pen)
        p.drawRoundedRect(rect, r, r)

        p.end()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _make_section_label(self, text: str, colour: str = "#8B5CF6") -> QWidget:
        """Thin section divider label for the vault view."""
        w = QWidget(); w.setStyleSheet("background:transparent;")
        row = QHBoxLayout(w); row.setContentsMargins(4, 6, 4, 2); row.setSpacing(8)
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{colour};font-size:9px;font-weight:800;letter-spacing:2px;"
            "background:transparent;border:none;"
        )
        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background:rgba(109,40,217,0.15);max-height:1px;border:none;")
        row.addWidget(lbl)
        row.addWidget(line, 1)
        return w

    def _sec(self, t):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        row = QHBoxLayout(w); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(5, 5)
        dot.setStyleSheet("background:#8B5CF6;border-radius:2px;border:none;")
        lbl = QLabel(t)
        lbl.setStyleSheet(
            "color:#8B5CF6;font-size:8px;font-weight:800;letter-spacing:3px;"
            "background:transparent;border:none;"
        )
        row.addWidget(dot, 0, Qt.AlignVCenter)
        row.addWidget(lbl, 0, Qt.AlignVCenter)
        row.addStretch()
        return w

    def _lbl(self, t):
        l = QLabel(t)
        l.setStyleSheet(
            "color:#7060a0;font-size:10px;font-weight:600;"
            "background:transparent;border:none;"
        )
        return l

    def _cb(self, t):
        c = QCheckBox(t); c.setChecked(True)
        c.setStyleSheet(
            "QCheckBox{color:#a090c8;font-size:11px;spacing:8px;background:transparent;font-weight:500;}"
            "QCheckBox::indicator{width:14px;height:14px;border-radius:5px;"
            "border:1.5px solid rgba(123,47,255,0.38);background:#06030f;}"
            "QCheckBox::indicator:checked{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #c060ff,stop:1 #6b10d0);border-color:#c084fc;}"
            "QCheckBox::indicator:hover{border-color:#8B5CF6;}"
        )
        return c

    def _abtn(self,txt,grad=False,height=40):
        b=QPushButton(txt); b.setFixedHeight(height); b.setCursor(Qt.PointingHandCursor)
        b.setObjectName("btnPrimary" if grad else "btnSecondary")
        return b

    def _update_strength(self):
        v=self.len_sl.value()
        has_upper=self.upper.isChecked(); has_num=self.numbers.isChecked(); has_sym=self.symbols.isChecked()
        char_pool = 26*(1+has_upper) + 10*has_num + 32*has_sym
        if char_pool < 1: char_pool = 26
        entropy = v * math.log2(max(char_pool, 2))
        if entropy < 40:
            label, col, score = "Weak", "#ef4444", max(5, int(entropy / 40 * 30))
        elif entropy < 65:
            label, col, score = "Fair", "#f97316", 30 + int((entropy - 40) / 25 * 20)
        elif entropy < 90:
            label, col, score = "Good", "#eab308", 50 + int((entropy - 65) / 25 * 20)
        elif entropy < 128:
            label, col, score = "Strong", "#22c55e", 70 + int((entropy - 90) / 38 * 20)
        else:
            label, col, score = "Unbreakable", "#8B5CF6", 100
        self.str_bar.set_value(score); self.str_bar2.set_value(score)
        self.str_val_lbl.setText(label)
        self.str_val_lbl.setStyleSheet(f"color:{col};font-size:10px;font-weight:800;letter-spacing:0.5px;background:transparent;border:none;")
        hints=[]
        if v<16: hints.append("increase length")
        if not has_upper: hints.append("add uppercase")
        if not has_num: hints.append("add numbers")
        if not has_sym: hints.append("add symbols")
        if hints: self._str_hint.setText("Tip: " + ", ".join(hints))
        else: self._str_hint.setText("")

    def _toggle_power(self):
        self.power.toggle(); active = self.power.active
        if active:
            self._pw_sub_lbl.setText("Scanning vault...")
            self._pw_sub_lbl.setStyleSheet("color:#8B5CF6;font-size:9px;"
                "letter-spacing:0.5px;background:transparent;border:none;")
            self._scan_active = True
            self._scan_dot.set_status("scanning")
            self._scan_dot.setVisible(True)
            self._scan_timer.start(3000); self._run_scan()
        else:
            self._pw_sub_lbl.setText("Press to scan vault")
            self._pw_sub_lbl.setStyleSheet("color:#3D2A58;font-size:9px;"
                "letter-spacing:0.5px;background:transparent;border:none;")
            self._scan_active = False; self._scan_timer.stop()
            self._scan_dot.set_status("idle")
            self._scan_dot.setVisible(False)

    def _toggle_show(self):
        mode=QLineEdit.Password if self.output.echoMode()==QLineEdit.Normal else QLineEdit.Normal
        self.output.setEchoMode(mode)

    def _toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _on_search_changed(self):
        self._vault_page = 0
        self._refresh_vault()

    def _vault_prev_page(self):
        self._vault_page = max(0, self._vault_page - 1)
        self._refresh_vault()

    def _vault_next_page(self):
        self._vault_page += 1
        self._refresh_vault()

    def _refresh_vault(self):
        query = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        for i in reversed(range(self.vault_l.count())):
            w = self.vault_l.itemAt(i).widget()
            if w:
                w.deleteLater()

        entries = self.vault.load()
        groups  = get_all_groups()
        meta    = self._vault_meta
        PZ      = self._vault_page_size  # pages of vault GROUPS

        # ── Search mode ───────────────────────────────────────────────────
        if query:
            filtered = [(i, e) for i, e in enumerate(entries)
                        if query in e.get("site", "").lower() or
                           query in e.get("username", "").lower()]
            count = len(filtered)
            self._entry_count.setText(f"{count} {'entry' if count==1 else 'entries'}")
            if not filtered:
                lbl = QLabel("No entries found.")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color:#3A2A55;font-size:12px;padding:24px;")
                self.vault_l.addWidget(lbl)
                self._page_bar.setVisible(False)
                return
            filtered = meta.sort_entries(filtered)
            total_pages = max(1, (len(filtered) + PZ - 1) // PZ)
            self._vault_page = max(0, min(self._vault_page, total_pages - 1))
            page_items = filtered[self._vault_page * PZ : (self._vault_page + 1) * PZ]
            for real_idx, entry in page_items:
                row = VaultRow(real_idx, entry, self.vault, self._refresh_vault,
                               meta=meta, all_members=filtered)
                self.vault_l.addWidget(row)
            self._update_page_bar(self._vault_page, total_pages)
            return

        # ── Normal grouped view ───────────────────────────────────────────
        total       = 0
        page_groups = []
        all_indexed = list(enumerate(entries))

        # ── PINNED SECTION — shown at top, always visible ─────────────────
        pinned_all = [(i, e) for i, e in all_indexed if meta.is_pinned(e)]
        pinned_all = meta.sort_entries(pinned_all)

        if pinned_all:
            pin_hdr = self._make_section_label("📌  PINNED", "#f59e0b")
            self.vault_l.addWidget(pin_hdr)
            for real_idx, entry in pinned_all:
                row = VaultRow(real_idx, entry, self.vault, self._refresh_vault,
                               meta=meta, all_members=all_indexed)
                self.vault_l.addWidget(row)
            # Hairline separator
            sep = QFrame(); sep.setFixedHeight(1)
            sep.setStyleSheet("background:rgba(109,40,217,0.18);border:none;")
            self.vault_l.addWidget(sep)

        # ── ALL VAULTS — paginated by group ──────────────────────────────
        for group in groups:
            gid     = group["id"]
            members = [(i, e) for i, e in all_indexed
                       if e.get("vault_id", DEFAULT_VAULT_ID) == gid]
            if gid == DEFAULT_VAULT_ID and not members:
                continue
            total += len(members)
            members = meta.sort_entries(members)
            page_groups.append((group, members))

        # Sort so pinned vaults appear first in the list
        page_groups.sort(key=lambda gm: (0 if meta.is_group_pinned(gm[0]["id"]) else 1))

        if page_groups:
            all_hdr = self._make_section_label("🗄  ALL VAULTS", "#60a5fa")
            self.vault_l.addWidget(all_hdr)

        total_pages = max(1, (len(page_groups) + PZ - 1) // PZ)
        self._vault_page = max(0, min(self._vault_page, total_pages - 1))
        page_slice = page_groups[self._vault_page * PZ : (self._vault_page + 1) * PZ]

        for group, members in page_slice:
            hdr = VaultGroupHeader(group, members, self.vault, self._refresh_vault,
                                   collapsed=True, meta=meta)
            self.vault_l.addWidget(hdr)
            child_rows = []
            for real_idx, entry in members:
                row = VaultRow(real_idx, entry, self.vault, self._refresh_vault,
                               meta=meta, all_members=members)
                self.vault_l.addWidget(row)
                child_rows.append(row)
            hdr.set_row_widgets(child_rows)

        self._entry_count.setText(f"{total} {'entry' if total==1 else 'entries'}")
        self._update_page_bar(self._vault_page, total_pages)

        if total == 0 and not pinned_all:
            lbl = QLabel("No passwords saved yet.\nGenerate one above and click Save to Vault.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color:#3A2A55;font-size:12px;padding:24px;")
            self.vault_l.addWidget(lbl)

    def _update_page_bar(self, page, total_pages):
        show = total_pages > 1
        self._page_bar.setVisible(show)
        if show:
            self._pg_lbl.setText(f"Page {page + 1} / {total_pages}")
            self._pg_prev.setEnabled(page > 0)
            self._pg_next.setEnabled(page < total_pages - 1)

    def _run_scan(self):
        def _set_sub(text, color, bold=False):
            weight = "font-weight:700;" if bold else ""
            self._pw_sub_lbl.setText(text)
            self._pw_sub_lbl.setStyleSheet(
                f"color:{color};font-size:9px;letter-spacing:0.5px;"
                f"background:transparent;border:none;{weight}")
        if not os.path.exists(VAULT_FILE):
            self._scan_dot.set_status("ok"); _set_sub("Vault empty", "#22c55e"); return
        ok = check_integrity()
        if ok:
            self._scan_dot.set_status("ok"); _set_sub("Vault verified ✓", "#22c55e")
        else:
            self._scan_dot.set_status("warn"); _set_sub("Tamper detected!", "#ef4444", bold=True)

    # ── Auto-lock ─────────────────────────────────────────────────────────────

    def _activity(self):
        """Call on any user interaction to reset the idle timer."""
        if getattr(self, '_closing', False):
            return
        self._last_activity = time.time()
        if self._lock_warned:
            self._lock_warned = False
            try:
                self._lock_countdown_lbl.setVisible(False)
                self._lock_countdown_lbl.setText("")
                self._card.setStyleSheet("")
            except RuntimeError:
                pass

    def _tick_auto_lock(self):
        """Called every second. Manages countdown display and triggers lock."""
        if getattr(self, '_closing', False):
            return
        try:
            mins = get_auto_lock_minutes()
            if mins <= 0:
                if self._lock_countdown_lbl.isVisible():
                    self._lock_countdown_lbl.setVisible(False)
                    self._lock_warned = False
                return

            idle_secs  = time.time() - self._last_activity
            total_secs = mins * 60
            remaining  = max(0, int(total_secs - idle_secs))
            warn_at    = 30

            if remaining <= 0:
                self._lock_countdown_lbl.setVisible(False)
                self._lock_warned = False
                self._logout()
                return

            if remaining <= warn_at:
                self._lock_warned = True
                self._lock_countdown_lbl.setVisible(True)
                if remaining <= 10:
                    self._lock_countdown_lbl.setStyleSheet(
                        "color:#ef4444;font-size:11px;font-weight:800;letter-spacing:0.5px;"
                    )
                else:
                    self._lock_countdown_lbl.setStyleSheet(
                        "color:#f59e0b;font-size:11px;font-weight:700;letter-spacing:0.5px;"
                    )
                self._lock_countdown_lbl.setText(f"  Locking in {remaining}s")
            else:
                if self._lock_countdown_lbl.isVisible():
                    self._lock_countdown_lbl.setVisible(False)
                    self._lock_warned = False
        except RuntimeError:
            # Widget already destroyed — stop the timer gracefully
            self._auto_lock_timer.stop()

    def mousePressEvent(self,e):
        self._activity()
        if e.button()==Qt.LeftButton and e.position().y()<54:
            self._drag_pos=e.globalPosition().toPoint()-self.frameGeometry().topLeft()

    def mouseMoveEvent(self,e):
        self._activity()
        if self._drag_pos and e.buttons()==Qt.LeftButton:
            self.move(e.globalPosition().toPoint()-self._drag_pos)

    def mouseReleaseEvent(self,e): self._drag_pos=None

    def keyPressEvent(self,e):
        self._activity()
        if e.modifiers()==Qt.ControlModifier:
            if e.key()==Qt.Key_G: self.generate()
            elif e.key()==Qt.Key_S: self.save_pwd()
            elif e.key()==Qt.Key_C and self.output.text(): self.copy_pwd()

    def _tick_border(self):
        """Removed — no border glow."""
        pass

    def _clear_clipboard(self):
        QApplication.clipboard().clear()

    def _open_enter_code(self):
        """Open the PLUS activation code dialog."""
        dlg = EnterCodeDialog(self)
        if dlg.exec() == QDialog.Accepted:
            # Defer all UI refresh until after the dialog is fully destroyed
            # and the event loop is clean — prevents nav overlap glitch
            QTimer.singleShot(0, self._apply_plus_activation)

    def _apply_plus_activation(self):
        """Run after dialog closes — silently refresh all PLUS UI."""
        self._refresh_plus_ui()
        # Navigate to dashboard so user immediately sees PLUS badge and new nav items
        self._on_nav_page("dashboard")
        if hasattr(self, '_nav_panel'):
            self._nav_panel._set_active("dashboard")

    def _open_settings(self):
        self._stack.setCurrentIndex(7)
        if hasattr(self, '_nav_panel'):
            self._nav_panel._set_active("settings")

    def _logout(self):
        self._closing = True                 # guard all timer callbacks
        self._auto_lock_timer.stop()
        self._scan_timer.stop()
        self._clipboard_timer.stop()
        if hasattr(self, '_border_timer'):
            self._border_timer.stop()
        if hasattr(self, '_xp_passive_timer'):
            self._xp_passive_timer.stop()
        try:
            audit.log("logout", "manual_lock")
        except Exception: pass
        from ui.login import LoginWindow
        self._login_win = LoginWindow(self._icon)
        self._login_win.show()
        self.close()

    def _show_history(self):
        dlg=HistoryDialog(self)
        if dlg.exec()==QDialog.Accepted and hasattr(dlg,"selected"):
            self.output.setEchoMode(QLineEdit.Normal); self.output.setText(dlg.selected)

    def _refresh_plus_ui(self):
        """
        Called after PLUS is activated. Updates every part of the UI
        synchronously so changes are visible immediately without a restart.
        """
        plus = is_plus()

        # 1. Title-bar PLUS badge
        self._plus_lbl.setVisible(plus)

        # 2. Left-panel note / audit quick-access buttons
        if hasattr(self, '_note_btn'):
            self._note_btn.setVisible(plus)
        if hasattr(self, '_audit_btn'):
            self._audit_btn.setVisible(plus)

        # 3. Rebuild nav buttons in correct order — no duplicates, no wrong positions
        if hasattr(self, '_nav_panel'):
            self._nav_panel.rebuild_nav_buttons()

        # 4. Hide gate overlays on Notes and Audit pages immediately
        if hasattr(self, '_notes_gate'):
            self._notes_gate.setVisible(not plus)
        if hasattr(self, '_audit_gate'):
            self._audit_gate.setVisible(not plus)

        # 5. Refresh notes/audit content now that gates are gone
        if plus:
            self._refresh_notes_page()
            self._refresh_audit_page()

        # 6. Rebuild settings page in-place so "Enter Code" btn disappears
        if hasattr(self, '_stack'):
            cur = self._stack.currentIndex()
            old = self._stack.widget(7)
            new_page = self._build_settings_page()
            self._stack.insertWidget(7, new_page)
            self._stack.removeWidget(old)
            old.deleteLater()
            # Restore current page
            self._stack.setCurrentIndex(cur)

        # 7. Force repaint
        self.update()

    def _open_notes(self):
        self._stack.setCurrentIndex(6)
        if hasattr(self, '_nav_panel'):
            self._nav_panel._set_active("notes")
        self._refresh_notes_page()

    def _open_audit(self):
        self._stack.setCurrentIndex(8)
        if hasattr(self, '_nav_panel'):
            self._nav_panel._set_active("audit")
        self._refresh_audit_page()

    def _create_new_vault(self):
        if not is_plus():
            user_groups = [g for g in get_all_groups()
                          if g["id"] != DEFAULT_VAULT_ID]
            if len(user_groups) >= FREE_VAULT_LIMIT:
                box = QMessageBox(self)
                box.setWindowTitle("FluxKey PLUS")
                box.setText(
                    f"Free accounts can have up to {FREE_VAULT_LIMIT} vaults.\n\n"
                    "Upgrade to FluxKey PLUS for unlimited vaults."
                )
                _style_msgbox(box); box.exec()
                return
        dlg = CreateVaultDialog(self)
        if dlg.exec() == QDialog.Accepted:
            audit.log("vault_created")
            self._refresh_vault()

    def _import_vault(self):
        path,_=QFileDialog.getOpenFileName(self,"Import Vault","","JSON Files (*.json)")
        if not path: return
        imp,skip,err=self.vault.import_json(path)
        box=QMessageBox(self); box.setWindowTitle("Import Complete")
        if err: box.setText(f"Import failed:\n{err}")
        else: box.setText(f"Imported {imp} entries.\nSkipped {skip} (duplicates or invalid).")
        _style_msgbox(box); box.exec(); self._refresh_vault()

    def _export_vault(self):
        path,_=QFileDialog.getSaveFileName(self,"Export Vault","FluxKey_backup.json","JSON Files (*.json)")
        if not path: return
        ok=self.vault.export_json(path)
        box=QMessageBox(self); box.setWindowTitle("Export")
        box.setText("Vault exported successfully." if ok else "Export failed.")
        _style_msgbox(box); box.exec()

    def _check_update(self):
        def worker():
            CURRENT = "1.0.0"
            SF_RSS = "https://sourceforge.net/projects/fluxkey/rss?path=/"
            try:
                req = urllib.request.Request(SF_RSS, headers={"User-Agent": "FluxKey/1.0"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    xml = r.read().decode("utf-8", errors="ignore")
                titles = (
                    re.findall(r"FluxKey[^<]*?(\d+\.\d+\.\d+)", xml, re.IGNORECASE)
                    or re.findall(r"/(\d+\.\d+\.\d+)/", xml)
                )
                latest = titles[0].strip() if titles else None
                if latest and latest != CURRENT:
                    def show():
                        self._latest_version = latest
                        self._update_btn.setVisible(True)
                    QTimer.singleShot(0, show)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _open_update_dialog(self):
        SF_DOWNLOAD="https://sourceforge.net/projects/fluxkey/files/latest/download"
        dlg=UpdateDialog("1.0.0",self._latest_version,SF_DOWNLOAD,self)
        if dlg.exec()==QDialog.Accepted: self._update_btn.setVisible(False)

    # ── actions ───────────────────────────────────────────────────────────────

    def _toggle_keyphrase_input(self):
        """Show/hide custom keyphrase text field when Keyphrase Mode toggled."""
        visible = self.keyphrase_cb.isChecked()
        self._keyphrase_input.setVisible(visible)
        if visible:
            self._keyphrase_input.setFocus()
        else:
            self._keyphrase_input.clear()

    def generate(self):
        # Anti-spam: ignore clicks within 800ms of last generate
        now = time.monotonic()
        if now - getattr(self, '_last_generate_ts', 0) < 0.8:
            return
        self._last_generate_ts = now
        # Briefly disable button to prevent double-click
        self.gen_btn.setEnabled(False)
        QTimer.singleShot(800, lambda: self.gen_btn.setEnabled(True))
        self._activity()
        if hasattr(self, 'keyphrase_cb') and self.keyphrase_cb.isChecked():
            custom = self._keyphrase_input.text().strip() if hasattr(self, '_keyphrase_input') else ""
            if custom:
                # Build a varied passphrase using the custom phrase as a seed
                words = custom.split() if " " in custom else [custom]
                parts = [w.capitalize() for w in words]
                parts.append(str(secrets.randbelow(9000) + 100))
                parts.append(secrets.choice("!@#$&*?"))
                pwd = "".join(parts)
                target = self.len_sl.value()
                if len(pwd) > target:
                    pwd = pwd[:target]
            else:
                pwd = self.generator.generate_keyphrase(self.len_sl.value())
        else:
            pwd = self.generator.generate(
                self.len_sl.value(),
                self.upper.isChecked(),
                self.numbers.isChecked(),
                self.symbols.isChecked(),
                no_ambiguous=hasattr(self,'no_amb') and self.no_amb.isChecked(),
                no_repeats=hasattr(self,'no_rep') and self.no_rep.isChecked(),
            )
        add_to_history(pwd)
        self._animate_password(pwd)

        audit.log("generate", f"length={self.len_sl.value()}")



    def _animate_password(self, final_pwd: str):
        """Scramble animation — rapidly cycles random chars then settles on final password."""
        CHARSET = string.ascii_letters + string.digits + "!@#$%^&*-_=+?"
        steps = 10
        interval = 35
        length = len(final_pwd)

        def _frame(step):
            if step >= steps:
                self.output.setText(final_pwd)
                self._flash_output()
                self._update_strength()
                return
            revealed = int(length * step / steps)
            scrambled = (
                final_pwd[:revealed] +
                "".join(random.choice(CHARSET) for _ in range(length - revealed))
            )
            self.output.setText(scrambled)
            QTimer.singleShot(interval, lambda: _frame(step + 1))

        self.output.setEchoMode(QLineEdit.Normal)
        _frame(0)

    def _flash_output(self):
        """Instant green border flash on generate — no lag."""
        self.output.setStyleSheet(
            "QLineEdit#outputField{background:#0C0A1E;border:2px solid #22C55E;"
            "border-radius:10px;padding:0 14px;color:#C4A8FF;"
            "font-family:'JetBrains Mono','Consolas',monospace;font-size:15px;letter-spacing:2px;}"
        )
        QTimer.singleShot(220, lambda: self.output.setStyleSheet(
            "QLineEdit#outputField{background:#0C0A1E;border:1.5px solid #7C3AED;"
            "border-radius:10px;padding:0 14px;color:#C4A8FF;"
            "font-family:'JetBrains Mono','Consolas',monospace;font-size:15px;letter-spacing:2px;}"
        ))

    def copy_pwd(self):
        now = time.monotonic()
        if now - getattr(self, '_last_copy_ts', 0) < 0.5:
            return
        self._last_copy_ts = now
        self._activity()
        txt=self.output.text()
        if not txt: return
        QApplication.clipboard().setText(txt)
        # Purple particle burst
        self._copy_flash.setGeometry(0, 0, self.output.width(), self.output.height())
        self._copy_flash.trigger()
        audit.log("copy")
        old=self.copy_btn.text(); self.copy_btn.setText("  ✓ Copied!")
        self.copy_btn.setStyleSheet(
            "QPushButton#btnSecondary{background:#0d1f14;color:#22c55e;"
            "border:1px solid #166534;border-radius:9px;font-size:13px;font-weight:700;}"
        )
        # Flash output field green briefly
        self.output.setStyleSheet(
            "QLineEdit#outputField{background:#080614;border:1.5px solid #22c55e;"
            "border-radius:10px;padding:0 14px;color:#4ade80;"
            "font-family:'JetBrains Mono','Consolas',monospace;font-size:15px;letter-spacing:2px;}"
        )
        def restore():
            self.copy_btn.setText(old)
            self.copy_btn.setStyleSheet(getattr(self, "_copy_btn_default_style", ""))
            self.output.setStyleSheet(
                "QLineEdit#outputField{background:#080614;border:1.5px solid #7C3AED;"
                "border-radius:10px;padding:0 14px;color:#c084fc;"
                "font-family:'JetBrains Mono','Consolas',monospace;font-size:15px;letter-spacing:2px;}"
            )
        QTimer.singleShot(1500, restore)
        # Auto-clear clipboard after 30s if enabled
        from core.vault import _load_config
        if _load_config().get("auto_clear_clipboard",True):
            self._clipboard_timer.start(30000)

    def save_pwd(self):
        now = time.monotonic()
        if now - getattr(self, '_last_save_ts', 0) < 1.0:
            return
        self._last_save_ts = now
        self._activity()
        if not self.output.text():
            return
        dlg = SaveToVaultDialog(self.vault, self.output.text(), self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_vault()
            self.on_password_saved_to_vault()  # +25 XP for saving a password



    # ── Nav panel routing ──────────────────────────────────────────────────
    def _on_nav_page(self, page: str):
        self._activity()
        if page == "dashboard":
            self._stack.setCurrentIndex(3)
            self._refresh_dashboard_page()
        elif page == "generate":
            self._stack.setCurrentIndex(0)
        elif page == "vault":
            self._stack.setCurrentIndex(4)
            self._refresh_vault()
        elif page == "reports":
            self._stack.setCurrentIndex(1)
            self._refresh_reports()
        elif page == "account":
            self._stack.setCurrentIndex(2)
            self._refresh_account_page()
        elif page == "switch":
            self._stack.setCurrentIndex(5)
            self._refresh_switch_page()
        elif page == "notes":
            self._stack.setCurrentIndex(6)
            self._refresh_notes_page()
        elif page == "settings":
            self._stack.setCurrentIndex(7)
        elif page == "audit":
            self._stack.setCurrentIndex(8)
            self._refresh_audit_page()


    # ── Dashboard home page ──────────────────────────────────────────────────


    def _build_vault_page(self):
        """Dedicated Vault page — shows all entries grouped by vault with custom vault name displayed."""
        page = QFrame(); page.setObjectName("panel")
        vl = QVBoxLayout(page); vl.setContentsMargins(10,10,10,10); vl.setSpacing(6)

        # ── Header row ────────────────────────────────────────────────
        hdr_row = QHBoxLayout(); hdr_row.setSpacing(8)
        hdr_row.addWidget(self._sec("VAULT"))

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search entries...")
        self._search.setFixedHeight(26)
        self._search.setStyleSheet(
            "QLineEdit{background:#16132A;"
            "border:1px solid rgba(123,47,255,0.28);"
            "border-radius:8px;padding:0 12px;"
            "color:#c4b4d8;font-size:12px;}"
            "QLineEdit:focus{border:1.5px solid #7C3AED;background:#110e24;}"
            "QLineEdit::placeholder{color:#3D2A58;}"
        )
        self._search.textChanged.connect(self._on_search_changed)
        self._search.textChanged.connect(lambda _: self._activity())

        self._entry_count = QLabel("0 entries")
        self._entry_count.setStyleSheet(
            "color:#6040a0;font-size:10px;font-weight:600;"
            "background:rgba(109,40,217,0.12);"
            "border:1px solid rgba(123,47,255,0.25);"
            "border-radius:6px;padding:2px 9px;"
        )
        hdr_row.addStretch()
        hdr_row.addWidget(self._search)
        hdr_row.addWidget(self._entry_count)
        vl.addLayout(hdr_row)

        # ── Action buttons row ────────────────────────────────────────
        ie_row = QHBoxLayout(); ie_row.setSpacing(8)
        imp_btn = QPushButton("Import"); exp_btn = QPushButton("Export")
        new_vault_btn = QPushButton("+ New Vault")
        for b in (imp_btn, exp_btn, new_vault_btn):
            b.setFixedHeight(22); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton{background:rgba(123,47,255,0.07);color:#7b5090;"
                "border:1px solid rgba(123,47,255,0.2);border-radius:7px;"
                "font-size:11px;font-weight:600;padding:0 10px;}"
                "QPushButton:hover{background:rgba(109,40,217,0.14);color:white;"
                "border-color:rgba(123,47,255,0.45);}"
            )
        new_vault_btn.setStyleSheet(
            "QPushButton{background:rgba(139,92,246,0.12);color:#c084fc;"
            "border:1px solid rgba(139,92,246,0.3);border-radius:7px;"
            "font-size:11px;font-weight:700;padding:0 10px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.25);color:white;border-color:#8B5CF6;}"
        )
        imp_btn.clicked.connect(self._import_vault)
        exp_btn.clicked.connect(self._export_vault)
        new_vault_btn.clicked.connect(self._create_new_vault)
        ie_row.addStretch()
        ie_row.addWidget(new_vault_btn)
        ie_row.addWidget(imp_btn)
        ie_row.addWidget(exp_btn)
        vl.addLayout(ie_row)

        # ── Scroll area for vault entries ─────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("vaultScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea>QWidget{background:transparent;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
            "QScrollBar:vertical{background:transparent;width:4px;}"
            "QScrollBar::handle:vertical{background:rgba(123,47,255,0.3);border-radius:2px;min-height:24px;}"
            "QScrollBar::handle:vertical:hover{background:#7C3AED;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        self.vault_w = QWidget()
        self.vault_w.setStyleSheet("background:transparent;")
        self.vault_l = QVBoxLayout(self.vault_w)
        self.vault_l.setSpacing(7)
        self.vault_l.setContentsMargins(0,4,0,8)
        self.vault_l.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.vault_w)
        vl.addWidget(scroll)

        # ── Pagination bar ────────────────────────────────────────────
        self._page_bar = QWidget()
        self._page_bar.setStyleSheet("background:transparent;")
        pb_l = QHBoxLayout(self._page_bar)
        pb_l.setContentsMargins(0,2,0,0); pb_l.setSpacing(8)
        self._pg_prev = QPushButton("⟨")
        self._pg_next = QPushButton("⟩")
        self._pg_lbl  = QLabel("Page 1")
        _pg_style = (
            "QPushButton{background:rgba(123,47,255,0.12);color:#9060d0;"
            "border:1px solid rgba(123,47,255,0.28);border-radius:8px;"
            "font-size:14px;font-weight:700;padding:0 10px;min-height:24px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.28);color:#d0a0ff;"
            "border-color:rgba(139,92,246,0.6);}"
            "QPushButton:disabled{background:rgba(40,20,80,0.1);color:#3A2A55;"
            "border-color:rgba(60,30,120,0.15);}"
        )
        self._pg_prev.setStyleSheet(_pg_style)
        self._pg_next.setStyleSheet(_pg_style)
        self._pg_lbl.setStyleSheet(
            "color:#5a3a8a;font-size:11px;font-weight:600;background:transparent;"
        )
        self._pg_prev.setCursor(Qt.PointingHandCursor)
        self._pg_next.setCursor(Qt.PointingHandCursor)
        self._pg_prev.clicked.connect(self._vault_prev_page)
        self._pg_next.clicked.connect(self._vault_next_page)
        pb_l.addStretch()
        pb_l.addWidget(self._pg_prev)
        pb_l.addWidget(self._pg_lbl)
        pb_l.addWidget(self._pg_next)
        pb_l.addStretch()
        vl.addWidget(self._page_bar)
        self._page_bar.setVisible(False)

        return page

    def _build_dashboard_page(self):
        """Premium home dashboard — hero banner + stat cards + alerts + actions."""
        from PySide6.QtWidgets import QRubberBand
        page = QFrame(); page.setObjectName("panel")
        pl = QVBoxLayout(page); pl.setContentsMargins(22, 20, 22, 20); pl.setSpacing(16)

        # ── Hero banner ──────────────────────────────────────────────────
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #12082c,stop:0.5 #0c0620,stop:1 #060318);"
            "border:1px solid rgba(140,60,255,0.28);border-radius:18px;}"
            "QFrame QLabel{background:transparent;border:none;}"
            "QFrame QWidget{background:transparent;}"
        )
        banner.setFixedHeight(94)
        bl = QHBoxLayout(banner); bl.setContentsMargins(22, 0, 22, 0); bl.setSpacing(18)

        # Avatar
        self._db_avatar = QLabel("🦊")
        self._db_avatar.setFixedSize(60, 60)
        self._db_avatar.setAlignment(Qt.AlignCenter)
        self._db_avatar.setStyleSheet(
            "font-size:34px;background:rgba(110,35,220,0.22);"
            "border:1.5px solid rgba(150,80,255,0.45);border-radius:16px;"
        )

        # Greeting + name
        txt = QVBoxLayout(); txt.setSpacing(3); txt.setAlignment(Qt.AlignVCenter)
        self._db_greet = QLabel("Welcome back,")
        self._db_greet.setStyleSheet(
            "color:#4a3870;font-size:10px;font-weight:600;letter-spacing:1px;"
        )
        self._db_username = QLabel("FluxUser")
        self._db_username.setStyleSheet(
            "color:#f0eaff;font-size:22px;font-weight:800;letter-spacing:-0.3px;"
        )
        txt.addWidget(self._db_greet); txt.addWidget(self._db_username)
        bl.addWidget(self._db_avatar); bl.addLayout(txt); bl.addStretch()

        # Security score circle
        score_col = QVBoxLayout(); score_col.setSpacing(4); score_col.setAlignment(Qt.AlignCenter)
        self._db_score_lbl = QLabel("—")
        self._db_score_lbl.setFixedSize(62, 62)
        self._db_score_lbl.setAlignment(Qt.AlignCenter)
        self._db_score_lbl.setStyleSheet(
            "color:#8B5CF6;font-size:20px;font-weight:900;"
            "background:rgba(110,35,220,0.15);"
            "border:2px solid rgba(150,80,255,0.40);border-radius:31px;"
        )
        score_sub = QLabel("SECURITY")
        score_sub.setAlignment(Qt.AlignCenter)
        score_sub.setStyleSheet(
            "color:#3a2860;font-size:7px;font-weight:800;letter-spacing:2.5px;"
        )
        score_col.addWidget(self._db_score_lbl); score_col.addWidget(score_sub)
        bl.addLayout(score_col)
        pl.addWidget(banner)

        # ── Stat cards (3 equal columns) ─────────────────────────────────
        self._db_stat_cards = {}
        stats_row = QHBoxLayout(); stats_row.setSpacing(10)
        stat_defs = [
            ("🔐", "Passwords", "0",  "#8B5CF6", "rgba(110,35,220,0.10)", "rgba(110,35,220,0.28)"),
            ("🗄️", "Vaults",    "0",  "#60a5fa", "rgba(29,78,216,0.10)",  "rgba(29,78,216,0.28)"),
            ("💪", "Avg Strength","—", "#34d399", "rgba(5,120,80,0.10)",   "rgba(5,120,80,0.28)"),
        ]
        for icon, label, val, col, bg, border in stat_defs:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:{bg};border:1px solid {border};"
                f"border-radius:14px;}}QFrame QLabel{{background:transparent;border:none;}}"
            )
            cl = QVBoxLayout(card); cl.setContentsMargins(18, 14, 18, 14); cl.setSpacing(5)
            ic = QLabel(icon); ic.setStyleSheet("font-size:22px;")
            vl = QLabel(val)
            vl.setStyleSheet(f"color:{col};font-size:26px;font-weight:900;letter-spacing:-0.5px;")
            lb = QLabel(label)
            lb.setStyleSheet("color:#5a4080;font-size:9px;font-weight:700;letter-spacing:2px;")
            cl.addWidget(ic); cl.addWidget(vl); cl.addWidget(lb)
            stats_row.addWidget(card)
            self._db_stat_cards[label] = vl
        pl.addLayout(stats_row)

        # ── Security alerts ───────────────────────────────────────────────
        pl.addWidget(self._sec("SECURITY ALERTS"))
        self._db_alerts_l = QVBoxLayout(); self._db_alerts_l.setSpacing(6)
        pl.addLayout(self._db_alerts_l)

        # ── Level / XP card ───────────────────────────────────────────────
        pl.addWidget(self._sec("VAULT RANK"))
        self._xp_card = QFrame()
        self._xp_card.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #12082c,stop:0.5 #0c0620,stop:1 #060318);"
            "border:1px solid rgba(139,92,246,0.30);border-radius:18px;}"
            "QFrame QLabel{background:transparent;border:none;}"
            "QFrame QWidget{background:transparent;}"
        )
        xp_l = QVBoxLayout(self._xp_card)
        xp_l.setContentsMargins(20, 16, 20, 16); xp_l.setSpacing(10)

        # ── Top row: level circle + badge + info + XP count ──────────────
        xp_top = QHBoxLayout(); xp_top.setSpacing(16)

        # Rank badge emoji
        self._xp_badge = QLabel("⚔️")
        self._xp_badge.setFixedSize(46, 46)
        self._xp_badge.setAlignment(Qt.AlignCenter)
        self._xp_badge.setStyleSheet(
            "font-size:26px;background:rgba(109,40,217,0.22);"
            "border:1.5px solid rgba(139,92,246,0.45);border-radius:12px;"
        )

        # Level name + rank title
        xp_info = QVBoxLayout(); xp_info.setSpacing(3); xp_info.setAlignment(Qt.AlignVCenter)
        self._xp_level_lbl = QLabel("Level 1")
        self._xp_level_lbl.setStyleSheet(
            "color:#f0eaff;font-size:18px;font-weight:900;letter-spacing:-0.3px;"
        )
        self._xp_title_lbl = QLabel("Initiate")
        self._xp_title_lbl.setStyleSheet(
            "color:#7c3aed;font-size:11px;font-weight:700;"
        )
        xp_info.addWidget(self._xp_level_lbl)
        xp_info.addWidget(self._xp_title_lbl)
        xp_top.addWidget(self._xp_badge)
        xp_top.addLayout(xp_info)
        xp_top.addStretch()

        # XP count circle — mirrors the security score circle on the banner
        xp_circle_col = QVBoxLayout()
        xp_circle_col.setSpacing(4)
        xp_circle_col.setAlignment(Qt.AlignCenter)
        self._xp_count_lbl = QLabel("0 XP")
        self._xp_count_lbl.setFixedSize(62, 62)
        self._xp_count_lbl.setAlignment(Qt.AlignCenter)
        self._xp_count_lbl.setStyleSheet(
            "color:#8B5CF6;font-size:13px;font-weight:900;letter-spacing:-0.5px;"
            "background:rgba(110,35,220,0.15);"
            "border:2px solid rgba(150,80,255,0.40);border-radius:31px;"
        )
        xp_circle_sub = QLabel("XP")
        xp_circle_sub.setAlignment(Qt.AlignCenter)
        xp_circle_sub.setStyleSheet(
            "color:#3a2860;font-size:7px;font-weight:800;letter-spacing:2.5px;"
        )
        xp_circle_col.addWidget(self._xp_count_lbl)
        xp_circle_col.addWidget(xp_circle_sub)
        xp_top.addLayout(xp_circle_col)
        xp_l.addLayout(xp_top)

        # ── XP progress bar (custom painted — perfect rounded caps) ──────
        self._xp_bar = XpBar()
        xp_l.addWidget(self._xp_bar)

        # ── Bottom row: pct + next level hint ────────────────────────────
        bar_bot = QHBoxLayout()
        self._xp_pct_lbl = QLabel("0%")
        self._xp_pct_lbl.setStyleSheet(
            "color:#6d28d9;font-size:9px;font-weight:700;"
        )
        self._xp_next_lbl = QLabel("Next level: 80 XP needed")
        self._xp_next_lbl.setAlignment(Qt.AlignRight)
        self._xp_next_lbl.setStyleSheet(
            "color:#3d2a58;font-size:9px;font-weight:600;"
        )
        bar_bot.addWidget(self._xp_pct_lbl)
        bar_bot.addStretch()
        bar_bot.addWidget(self._xp_next_lbl)
        xp_l.addLayout(bar_bot)

        pl.addWidget(self._xp_card)

        pl.addStretch()
        return page

    def _refresh_dashboard_page(self):
        prof = load_profile()
        self._db_avatar.setText(prof.get("avatar","🦊"))
        self._db_username.setText(prof.get("username","FluxUser"))
        entries = self.vault.load()
        groups  = get_all_groups()
        user_groups = [g for g in groups if g["id"] != DEFAULT_VAULT_ID]
        self._db_stat_cards["Passwords"].setText(str(len(entries)))
        self._db_stat_cards["Vaults"].setText(str(len(user_groups)))
        if entries:
            scores = []
            for entry in entries:
                pw = entry.get("password","")
                pool = sum([26 if any(c.isupper() for c in pw) else 0,
                            26 if any(c.islower() for c in pw) else 0,
                            10 if any(c.isdigit() for c in pw) else 0,
                            32 if any(not c.isalnum() for c in pw) else 0])
                ent = len(pw) * math.log2(max(pool, 2))
                scores.append(min(100, int(ent / 1.28)))
            avg = sum(scores)//max(1,len(scores))
            if avg>=80: slabel,sc="Strong","#22c55e"
            elif avg>=60: slabel,sc="Good","#8B5CF6"
            elif avg>=40: slabel,sc="Fair","#f59e0b"
            else: slabel,sc="Weak","#ef4444"
            self._db_stat_cards["Avg Strength"].setText(slabel)
            self._db_score_lbl.setText(str(avg))
            self._db_score_lbl.setStyleSheet(f"color:{sc};font-size:17px;font-weight:900;background:rgba(123,47,255,0.12);border:2px solid {sc}66;border-radius:29px;")
        else:
            self._db_stat_cards["Avg Strength"].setText("--")
            self._db_score_lbl.setText("--")
            self._db_score_lbl.setStyleSheet("color:#8B5CF6;font-size:17px;font-weight:900;background:rgba(123,47,255,0.12);border:2px solid rgba(139,92,246,0.4);border-radius:29px;")
        for i in reversed(range(self._db_alerts_l.count())):
            item = self._db_alerts_l.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()
        alerts = []
        if entries:
            wk = sum(1 for e in entries if len(e.get("password",""))<10)
            if wk: alerts.append(("⚠️",f"{wk} password{'s' if wk>1 else ''} with fewer than 10 chars",(245,158,11)))
            ns = sum(1 for e in entries if not any(not c.isalnum() for c in e.get("password","")))
            if ns: alerts.append(("🔓",f"{ns} password{'s' if ns>1 else ''} without symbols",(239,68,68)))
        if not alerts: alerts.append(("✅","No issues detected — your vault looks secure!",(34,197,94)))
        for icon, msg, rgb in alerts:
            r2,g2,b2 = rgb
            row = QFrame()
            row.setStyleSheet(f"QFrame{{background:rgba({r2},{g2},{b2},0.07);border:1px solid rgba({r2},{g2},{b2},0.22);border-radius:9px;}}QFrame QLabel{{background:transparent;border:none;}}")
            rl = QHBoxLayout(row); rl.setContentsMargins(12,8,12,8); rl.setSpacing(10)
            ic=QLabel(icon); ic.setStyleSheet("font-size:14px;")
            ml=QLabel(msg); ml.setWordWrap(True); ml.setStyleSheet(f"color:rgb({r2},{g2},{b2});font-size:11px;font-weight:600;")
            rl.addWidget(ic,0,Qt.AlignTop); rl.addWidget(ml,1)
            self._db_alerts_l.addWidget(row)

        # Refresh the XP card while we're here
        self._refresh_xp_card()

    # ── XP / Level system ─────────────────────────────────────────────────────
    #
    #  Persistence  : JSON sidecar next to VAULT_FILE  →  fluxkey_xp_{pid}.json
    #  Passive XP   : +1 XP every 60 s the app is open
    #  Vault save   : +25 XP per new password saved
    #  Max level    : 999
    #
    #  Formula      : XP to reach level N  =  N² × 20
    #  Level 2  =   80 XP  |  Level 10  =  2,000 XP  |  Level 999  ≈  19.96 M

    _XP_FILE = os.path.join(os.path.dirname(VAULT_FILE), "fluxkey_xp.json")
    _MAX_LEVEL = 999

    # Rank titles — one per tier of ~100 levels
    _RANK_TIERS = [
    (1, '⚔️', 'Initiate'),
    (2, '⚔️', 'Initiate I'),
    (3, '⚔️', 'Initiate II'),
    (4, '⚔️', 'Initiate III'),
    (5, '⚔️', 'Initiate IV'),
    (6, '⚔️', 'Initiate V'),
    (7, '⚔️', 'Initiate VI'),
    (8, '⚔️', 'Initiate VII'),
    (9, '⚔️', 'Initiate VIII'),
    (10, '⚔️', 'Initiate IX'),
    (11, '🤓', 'Pioneer'),
    (12, '🤓', 'Pioneer I'),
    (13, '🤓', 'Pioneer II'),
    (14, '🤓', 'Pioneer III'),
    (15, '🤓', 'Pioneer IV'),
    (16, '🤓', 'Pioneer V'),
    (17, '🤓', 'Pioneer VI'),
    (18, '🤓', 'Pioneer VII'),
    (19, '🤓', 'Pioneer VIII'),
    (20, '🤓', 'Pioneer IX'),
    (21, '🗡️', 'Apprentice'),
    (22, '🗡️', 'Apprentice I'),
    (23, '🗡️', 'Apprentice II'),
    (24, '🗡️', 'Apprentice III'),
    (25, '🗡️', 'Apprentice IV'),
    (26, '🗡️', 'Apprentice V'),
    (27, '🗡️', 'Apprentice VI'),
    (28, '🗡️', 'Apprentice VII'),
    (29, '🗡️', 'Apprentice VIII'),
    (30, '🗡️', 'Apprentice IX'),
    (31, '🗺️', 'Journeyman'),
    (32, '🗺️', 'Journeyman I'),
    (33, '🗺️', 'Journeyman II'),
    (34, '🗺️', 'Journeyman III'),
    (35, '🗺️', 'Journeyman IV'),
    (36, '🗺️', 'Journeyman V'),
    (37, '🗺️', 'Journeyman VI'),
    (38, '🗺️', 'Journeyman VII'),
    (39, '🗺️', 'Journeyman VIII'),
    (40, '🗺️', 'Journeyman IX'),
    (41, '🛡️', 'Defender'),
    (42, '🛡️', 'Defender I'),
    (43, '🛡️', 'Defender II'),
    (44, '🛡️', 'Defender III'),
    (45, '🛡️', 'Defender IV'),
    (46, '🛡️', 'Defender V'),
    (47, '🛡️', 'Defender VI'),
    (48, '🛡️', 'Defender VII'),
    (49, '🛡️', 'Defender VIII'),
    (50, '🛡️', 'Defender IX'),
    (51, '🔮', 'Arcanist'),
    (52, '🔮', 'Arcanist I'),
    (53, '🔮', 'Arcanist II'),
    (54, '🔮', 'Arcanist III'),
    (55, '🔮', 'Arcanist IV'),
    (56, '🔮', 'Arcanist V'),
    (57, '🔮', 'Arcanist VI'),
    (58, '🔮', 'Arcanist VII'),
    (59, '🔮', 'Arcanist VIII'),
    (60, '🔮', 'Arcanist IX'),
    (61, '🌙', 'Shadowblade'),
    (62, '🌙', 'Shadowblade I'),
    (63, '🌙', 'Shadowblade II'),
    (64, '🌙', 'Shadowblade III'),
    (65, '🌙', 'Shadowblade IV'),
    (66, '🌙', 'Shadowblade V'),
    (67, '🌙', 'Shadowblade VI'),
    (68, '🌙', 'Shadowblade VII'),
    (69, '🌙', 'Shadowblade VIII'),
    (70, '🌙', 'Shadowblade IX'),
    (71, '⚡', 'Stormcaller'),
    (72, '⚡', 'Stormcaller I'),
    (73, '⚡', 'Stormcaller II'),
    (74, '⚡', 'Stormcaller III'),
    (75, '⚡', 'Stormcaller IV'),
    (76, '⚡', 'Stormcaller V'),
    (77, '⚡', 'Stormcaller VI'),
    (78, '⚡', 'Stormcaller VII'),
    (79, '⚡', 'Stormcaller VIII'),
    (80, '⚡', 'Stormcaller IX'),
    (81, '🔥', 'Infernal'),
    (82, '🔥', 'Infernal I'),
    (83, '🔥', 'Infernal II'),
    (84, '🔥', 'Infernal III'),
    (85, '🔥', 'Infernal IV'),
    (86, '🔥', 'Infernal V'),
    (87, '🔥', 'Infernal VI'),
    (88, '🔥', 'Infernal VII'),
    (89, '🔥', 'Infernal VIII'),
    (90, '🔥', 'Infernal IX'),
    (91, '❄️', 'Frostweaver'),
    (92, '❄️', 'Frostweaver I'),
    (93, '❄️', 'Frostweaver II'),
    (94, '❄️', 'Frostweaver III'),
    (95, '❄️', 'Frostweaver IV'),
    (96, '❄️', 'Frostweaver V'),
    (97, '❄️', 'Frostweaver VI'),
    (98, '❄️', 'Frostweaver VII'),
    (99, '❄️', 'Frostweaver VIII'),
    (100, '❄️', 'Frostweaver IX'),
    (101, '🌊', 'Tidecaster'),
    (102, '🌊', 'Tidecaster I'),
    (103, '🌊', 'Tidecaster II'),
    (104, '🌊', 'Tidecaster III'),
    (105, '🌊', 'Tidecaster IV'),
    (106, '🌊', 'Tidecaster V'),
    (107, '🌊', 'Tidecaster VI'),
    (108, '🌊', 'Tidecaster VII'),
    (109, '🌊', 'Tidecaster VIII'),
    (110, '🌊', 'Tidecaster IX'),
    (111, '🦋', 'Ascendant'),
    (112, '🦋', 'Ascendant I'),
    (113, '🦋', 'Ascendant II'),
    (114, '🦋', 'Ascendant III'),
    (115, '🦋', 'Ascendant IV'),
    (116, '🦋', 'Ascendant V'),
    (117, '🦋', 'Ascendant VI'),
    (118, '🦋', 'Ascendant VII'),
    (119, '🦋', 'Ascendant VIII'),
    (120, '🦋', 'Ascendant IX'),
    (121, '💎', 'Crystalline'),
    (122, '💎', 'Crystalline I'),
    (123, '💎', 'Crystalline II'),
    (124, '💎', 'Crystalline III'),
    (125, '💎', 'Crystalline IV'),
    (126, '💎', 'Crystalline V'),
    (127, '💎', 'Crystalline VI'),
    (128, '💎', 'Crystalline VII'),
    (129, '💎', 'Crystalline VIII'),
    (130, '💎', 'Crystalline IX'),
    (155, '🌪️', 'Voidwalker'),
    (160, '🌪️', 'Voidwalker I'),
    (170, '🌪️', 'Voidwalker II'),
    (180, '🌪️', 'Voidwalker III'),
    (200, '🌪️', 'Voidwalker IV'),
    (230, '🌪️', 'Voidwalker V'),
    (250, '🌪️', 'Voidwalker VI'),
    (280, '🌪️', 'Voidwalker VII'),
    (310, '🌪️', 'Voidwalker VIII'),
    (340, '🌪️', 'Voidwalker IX'),
    (425, '🐉', 'Dragonbound'),
    (450, '🐉', 'Dragonbound I'),
    (480, '🐉', 'Dragonbound II'),
    (500, '🐉', 'Dragonbound III'),
    (520, '🐉', 'Dragonbound IV'),
    (550, '🐉', 'Dragonbound V'),
    (580, '🐉', 'Dragonbound VI'),
    (620, '🐉', 'Dragonbound VII'),
    (640, '🐉', 'Dragonbound VIII'),
    (660, '🐉', 'Dragonbound IX'),
    (730, '🦁', 'Apex'),
    (770, '🦁', 'Apex I'),
    (790, '🦁', 'Apex II'),
    (800, '🦁', 'Apex III'),
    (820, '🦁', 'Apex IV'),
    (840, '🦁', 'Apex V'),
    (860, '🦁', 'Apex VI'),
    (870, '🦁', 'Apex VII'),
    (880, '🦁', 'Apex VIII'),
    (890, '🦁', 'Apex IX'),
    (900, '🦁', 'Phoenix'),
    (920, '🦁', 'Phoenix I'),
    (930, '🦁', 'Phoenix II'),
    (940, '🦁', 'Phoenix III'),
    (950, '🦁', 'Phoenix IV'),
    (960, '🦁', 'Phoenix V'),
    (975, '🦁', 'Phoenix VI'),
    (980, '🦁', 'Phoenix VII'),
    (985, '🦁', 'Phoenix VIII'),
    (990, '🦁', 'Phoenix IX'),
    (999, '🌌', 'Legendary'),
    ]

    def _xp_file_path(self) -> str:
        """Return path to XP save file, scoped to current profile."""
        pid = get_current_profile_id()
        base = os.path.dirname(VAULT_FILE)
        return os.path.join(base, f"fluxkey_xp_{pid}.json")

    def _load_xp(self) -> dict:
        try:
            with open(self._xp_file_path(), "r") as f:
                data = json.load(f)
                return {"xp": int(data.get("xp", 0))}
        except Exception:
            return {"xp": 0}

    def _save_xp(self, xp: int) -> None:
        try:
            with open(self._xp_file_path(), "w") as f:
                json.dump({"xp": max(0, xp)}, f)
        except Exception:
            pass

    @staticmethod
    def _xp_for_level(level: int) -> int:
        """Total XP required to *reach* this level (cumulative). N² × 20."""
        return level * level * 20

    @staticmethod
    def _level_from_xp(xp: int) -> int:
        """Derive current level from total XP. Max 999."""
        if xp <= 0:
            return 1
        level = int(math.sqrt(xp / 20))
        level = max(1, min(level, Dashboard._MAX_LEVEL))
        return level

    def _rank_for_level(self, level: int) -> tuple:
        """Return (emoji, title) for the given level."""
        badge, title = "⚔️", "Initiate"
        for threshold, em, t in self._RANK_TIERS:
            if level >= threshold:
                badge, title = em, t
        return badge, title

    def add_xp(self, amount: int) -> None:
        """Award XP, save, refresh the card, and show a level-up toast if needed."""
        data = self._load_xp()
        old_xp = data["xp"]
        old_level = self._level_from_xp(old_xp)

        new_xp = old_xp + amount
        # Cap total XP at max-level threshold so the bar stays full at 999
        new_xp = min(new_xp, self._xp_for_level(self._MAX_LEVEL) + self._xp_for_level(1) - 1)
        new_level = self._level_from_xp(new_xp)

        self._save_xp(new_xp)

        if new_level > old_level:
            badge, title = self._rank_for_level(new_level)
            self._xp_toast(new_level, badge, title)

        # Live-refresh the card if dashboard is visible
        if hasattr(self, "_xp_level_lbl"):
            self._refresh_xp_card()

    def _refresh_xp_card(self) -> None:
        """Re-draw the XP card widgets from saved data."""
        if not hasattr(self, "_xp_level_lbl"):
            return
        data = self._load_xp()
        xp = data["xp"]
        level = self._level_from_xp(xp)
        badge, title = self._rank_for_level(level)

        if level >= self._MAX_LEVEL:
            pct = 1.0
            pct_txt = "100%"
            next_txt = "MAX LEVEL REACHED  👑"
        else:
            xp_this = self._xp_for_level(level)
            xp_next = self._xp_for_level(level + 1)
            span = max(1, xp_next - xp_this)
            pct = min(1.0, (xp - xp_this) / span)
            needed = xp_next - xp
            pct_txt = f"{int(pct * 100)}%"
            next_txt = f"Next level: {needed:,} XP needed"

        # Colour scheme by tier
        if level >= 900:   col, bcol = "#f59e0b", "#f59e0b66"
        elif level >= 500: col, bcol = "#a78bfa", "#a78bfa66"
        elif level >= 200: col, bcol = "#22c55e", "#22c55e66"
        elif level >= 100: col, bcol = "#60a5fa", "#60a5fa66"
        else:              col, bcol = "#8B5CF6", "rgba(150,80,255,0.40)"

        # Text widgets
        self._xp_badge.setText(badge)
        self._xp_level_lbl.setText(f"Level {level:,}")
        self._xp_title_lbl.setText(title)
        # XP circle: show compact number, scale font for large values
        xp_font = "11" if xp >= 10000 else "13"
        self._xp_count_lbl.setText(f"{xp:,}")
        self._xp_count_lbl.setStyleSheet(
            f"color:{col};font-size:{xp_font}px;font-weight:900;letter-spacing:-0.5px;"
            f"background:rgba(110,35,220,0.15);"
            f"border:2px solid {bcol};border-radius:31px;"
        )
        self._xp_next_lbl.setText(next_txt)
        self._xp_pct_lbl.setText(pct_txt)

        self._xp_level_lbl.setStyleSheet(
            f"color:{col};font-size:18px;font-weight:900;letter-spacing:-0.3px;"
        )

        # XP bar — always perfectly rounded via custom XpBar widget
        self._xp_bar.set_pct(pct)


    def _xp_toast(self, level: int, badge: str, title: str) -> None:
        """Flash a level-up message in the window title for 3 seconds."""
        old = self.window().windowTitle()
        self.window().setWindowTitle(f"{badge}  LEVEL UP!  Level {level} — {title}")
        QTimer.singleShot(3000, lambda: self.window().setWindowTitle(old))

    def _start_xp_timers(self) -> None:
        """Call once after UI is built. Starts passive XP tick."""
        self._xp_passive_timer = QTimer(self)
        # +1 XP every 60 seconds the app is open
        self._xp_passive_timer.setInterval(60_000)
        self._xp_passive_timer.timeout.connect(lambda: self.add_xp(1))
        self._xp_passive_timer.start()

    def on_password_saved_to_vault(self) -> None:
        """Call this whenever a password is successfully saved. Awards 25 XP."""
        self.add_xp(25)

    def _build_reports_page(self):
        """Reports / statistics page."""
        page = QFrame(); page.setObjectName("panel")
        pl = QVBoxLayout(page); pl.setContentsMargins(18, 16, 18, 16); pl.setSpacing(14)

        # Header
        hdr_row = QHBoxLayout()
        sec_lbl = self._sec("REPORTS")
        hdr_row.addWidget(sec_lbl); hdr_row.addStretch()
        pl.addLayout(hdr_row)

        # Stats grid
        self._stat_cards = {}
        grid = QGridLayout(); grid.setSpacing(10)
        stats = [
            ("Total Saved", "0", "#8B5CF6", "🔐"),
            ("Generated",   "0", "#22c55e", "⚡"),
            ("Copied",      "0", "#f59e0b", "📋"),
            ("Vaults",      "0", "#3b82f6", "🗄️"),
        ]
        for i, (label, val, color, icon) in enumerate(stats):
            card = QFrame(); card.setObjectName(f"statCard{i}")
            card.setStyleSheet(
                f"QFrame#statCard{i}{{background:rgba(123,47,255,0.06);"
                f"border:1px solid rgba(109,40,217,0.18);border-radius:14px;}}"
                f"QFrame#statCard{i} QLabel{{background:transparent;border:none;}}"
            )
            cl = QVBoxLayout(card); cl.setContentsMargins(16, 14, 16, 14); cl.setSpacing(4)
            ic_lbl = QLabel(icon); ic_lbl.setStyleSheet("font-size:22px;")
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(
                f"color:{color};font-size:26px;font-weight:800;letter-spacing:-0.5px;"
            )
            lbl_lbl = QLabel(label)
            lbl_lbl.setStyleSheet("color:#4A3370;font-size:10px;font-weight:700;letter-spacing:1.5px;")
            cl.addWidget(ic_lbl); cl.addWidget(val_lbl); cl.addWidget(lbl_lbl)
            grid.addWidget(card, i // 2, i % 2)
            self._stat_cards[label] = val_lbl
        pl.addLayout(grid)

        # Strength distribution
        pl.addWidget(self._sec("STRENGTH DISTRIBUTION"))
        self._strength_bars_w = QWidget()
        self._strength_bars_w.setStyleSheet("background:transparent;")
        self._strength_bars_l = QVBoxLayout(self._strength_bars_w)
        self._strength_bars_l.setContentsMargins(0,0,0,0); self._strength_bars_l.setSpacing(8)
        pl.addWidget(self._strength_bars_w)

        pl.addStretch()
        return page

    def _refresh_reports(self):
        """Populate the reports page with live data."""
        entries = self.vault.load()
        groups  = get_all_groups()

        # Update stat cards
        try:
            al = audit.load()
            gen_count  = sum(1 for e in al if e.get("action") == "generate")
            copy_count = sum(1 for e in al if e.get("action") == "copy")
        except Exception:
            gen_count = copy_count = 0

        vals = {
            "Total Saved": str(len(entries)),
            "Generated":   str(gen_count),
            "Copied":      str(copy_count),
            "Vaults":      str(len([g for g in groups if g["id"] != DEFAULT_VAULT_ID])),
        }
        for k, v in vals.items():
            if k in self._stat_cards:
                self._stat_cards[k].setText(v)

        # Strength distribution bars
        for i in reversed(range(self._strength_bars_l.count())):
            w = self._strength_bars_l.itemAt(i).widget()
            if w: w.deleteLater()

        strength_counts = {"Weak": 0, "Fair": 0, "Good": 0, "Strong": 0, "Very Strong": 0}
        for entry in entries:
            pw = entry.get("password", "")
            pool = (26 if any(c.isupper() for c in pw) else 0 +
                    26 if any(c.islower() for c in pw) else 0 +
                    10 if any(c.isdigit() for c in pw) else 0 +
                    32 if any(not c.isalnum() for c in pw) else 0)
            ent = len(pw) * (7 if pool > 60 else 5 if pool > 36 else 3.5)
            if ent < 28: strength_counts["Weak"] += 1
            elif ent < 45: strength_counts["Fair"] += 1
            elif ent < 65: strength_counts["Good"] += 1
            elif ent < 90: strength_counts["Strong"] += 1
            else: strength_counts["Very Strong"] += 1

        colors = {"Weak": "#ef4444", "Fair": "#f97316", "Good": "#eab308",
                  "Strong": "#22c55e", "Very Strong": "#8B5CF6"}
        total = max(1, sum(strength_counts.values()))
        max_count = max(1, max(strength_counts.values()))
        for label, count in strength_counts.items():
            row = QWidget(); row.setStyleSheet("background:transparent;")
            rl  = QHBoxLayout(row); rl.setContentsMargins(0,0,0,0); rl.setSpacing(10)
            lbl = QLabel(label); lbl.setFixedWidth(78)
            lbl.setStyleSheet(f"color:#9888C0;font-size:11px;font-weight:600;background:transparent;border:none;")
            # Bar container uses a proportional stylesheet width trick
            bar_wrap = QFrame(); bar_wrap.setFixedHeight(10)
            bar_wrap.setStyleSheet("QFrame{background:rgba(109,40,217,0.12);border-radius:5px;border:none;}")
            pct = int(count / max_count * 100) if max_count > 0 else 0
            # Inner fill via a nested frame — width set as fraction of 200px base
            bar_fill = QFrame(bar_wrap)
            bar_fill.setFixedHeight(10)
            # We animate width via a fixed pixel width using a 200px baseline
            fill_w = max(0, int(pct / 100 * 200)) if count > 0 else 0
            bar_fill.setFixedWidth(fill_w)
            bar_fill.setStyleSheet(
                f"QFrame{{background:{colors[label]};border-radius:5px;border:none;}}"
            )
            # Store reference for resize
            bar_fill.setObjectName(f"bar_{label}")
            cnt_lbl = QLabel(str(count))
            cnt_lbl.setFixedWidth(28)
            cnt_lbl.setAlignment(Qt.AlignRight)
            cnt_lbl.setStyleSheet(
                f"color:{colors[label]};font-size:11px;font-weight:700;"
                "background:transparent;border:none;"
            )
            rl.addWidget(lbl); rl.addWidget(bar_wrap, 1); rl.addWidget(cnt_lbl)
            self._strength_bars_l.addWidget(row)
            # Delayed resize so bar fills actual track width
            def _resize_bar(fill=bar_fill, track=bar_wrap, c=count, mx=max_count):
                tw = track.width()
                if tw > 10:
                    fill.setFixedWidth(max(0, int(c / mx * tw)) if mx > 0 else 0)
            QTimer.singleShot(50, _resize_bar)

        # Recent activity section removed

    def _build_account_page(self):
        """Account / profile management page."""
        page = QFrame(); page.setObjectName("panel")
        pl = QVBoxLayout(page); pl.setContentsMargins(18, 16, 18, 16); pl.setSpacing(16)

        pl.addWidget(self._sec("ACCOUNT"))

        # Profile card
        prof_card = QFrame(); prof_card.setObjectName("profCard")
        prof_card.setStyleSheet(
            "QFrame#profCard{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #100c28,stop:1 #08061a);"
            "border:1px solid rgba(123,47,255,0.28);border-radius:16px;}"
            "QFrame#profCard QLabel{background:transparent;border:none;}"
        )
        pcl = QHBoxLayout(prof_card); pcl.setContentsMargins(18, 16, 18, 16); pcl.setSpacing(16)

        self._acc_avatar = QLabel("🦊")
        self._acc_avatar.setFixedSize(60, 60)
        self._acc_avatar.setAlignment(Qt.AlignCenter)
        self._acc_avatar.setStyleSheet(
            "font-size:34px;background:rgba(109,40,217,0.14);"
            "border:2px solid rgba(109,40,217,0.4);border-radius:16px;"
        )
        self._acc_name = QLabel("FluxUser")
        self._acc_name.setStyleSheet(
            "color:#e2d5f8;font-size:18px;font-weight:800;letter-spacing:0.5px;"
        )
        acc_sub = QLabel("Local Profile  ·  This device only")
        acc_sub.setStyleSheet("color:#4A3370;font-size:10px;")

        txt_col = QVBoxLayout(); txt_col.setSpacing(4)
        txt_col.addWidget(self._acc_name); txt_col.addWidget(acc_sub)

        edit_prof_btn = QPushButton("Edit Profile")
        edit_prof_btn.setFixedHeight(36); edit_prof_btn.setCursor(Qt.PointingHandCursor)
        edit_prof_btn.setStyleSheet(
            "QPushButton{background:rgba(123,47,255,0.14);color:#8B5CF6;"
            "border:1px solid rgba(123,47,255,0.3);border-radius:9px;"
            "font-size:12px;font-weight:700;padding:0 14px;}"
            "QPushButton:hover{background:rgba(123,47,255,0.28);color:#e2d5f8;}"
        )
        edit_prof_btn.clicked.connect(self._edit_profile_from_account)

        pcl.addWidget(self._acc_avatar)
        pcl.addLayout(txt_col)
        pcl.addStretch()
        pcl.addWidget(edit_prof_btn)
        pl.addWidget(prof_card)

        # Quick stats
        pl.addWidget(self._sec("VAULT SUMMARY"))
        self._acc_stats_l = QVBoxLayout()
        self._acc_stats_l.setSpacing(6)
        pl.addLayout(self._acc_stats_l)

        # Settings quick link
        pl.addWidget(self._sec("SETTINGS"))
        settings_btn = QPushButton("⚙  Open Settings")
        settings_btn.setFixedHeight(44); settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet(
            "QPushButton{background:rgba(123,47,255,0.08);color:#9b60d0;"
            "border:1px solid rgba(123,47,255,0.2);border-radius:11px;"
            "font-size:13px;font-weight:700;text-align:left;padding-left:16px;}"
            "QPushButton:hover{background:rgba(109,40,217,0.18);color:#e2d5f8;}"
        )
        settings_btn.clicked.connect(lambda: self._on_nav_page("settings"))
        pl.addWidget(settings_btn)

        pl.addStretch()
        return page

    # ── Switch Profiles page ────────────────────────────────────────────────

    def _build_switch_page(self):
        """Multi-profile switcher page."""
        page = QFrame(); page.setObjectName("panel")
        pl = QVBoxLayout(page); pl.setContentsMargins(18, 16, 18, 16); pl.setSpacing(14)
        pl.addWidget(self._sec("SWITCH PROFILE"))

        # Subtitle
        sub = QLabel("Each profile has its own vault, passwords and settings.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#6B5A8A;font-size:11px;background:transparent;border:none;")
        pl.addWidget(sub)

        # Profile list container
        self._switch_scroll = QScrollArea(); self._switch_scroll.setWidgetResizable(True)
        self._switch_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:transparent;width:3px;}"
            "QScrollBar::handle:vertical{background:rgba(109,40,217,0.30);border-radius:2px;}"
        )
        self._switch_list_w = QWidget(); self._switch_list_w.setStyleSheet("background:transparent;")
        self._switch_list_l = QVBoxLayout(self._switch_list_w)
        self._switch_list_l.setContentsMargins(0,0,0,0); self._switch_list_l.setSpacing(8)
        self._switch_list_l.setAlignment(Qt.AlignTop)
        self._switch_scroll.setWidget(self._switch_list_w)
        pl.addWidget(self._switch_scroll, 1)

        # New profile button
        max_profiles = 10 if is_plus() else 2
        lim_lbl = QLabel(f"Profile limit: {max_profiles}  ({'PLUS' if is_plus() else 'FREE'})")
        lim_lbl.setStyleSheet(
            f"color:{'#f9a8d4' if is_plus() else '#fbbf24'};font-size:10px;font-weight:700;"
            "background:transparent;border:none;letter-spacing:1px;"
        )
        pl.addWidget(lim_lbl)

        self._new_profile_btn = QPushButton("＋  Create New Profile")
        self._new_profile_btn.setFixedHeight(44); self._new_profile_btn.setCursor(Qt.PointingHandCursor)
        self._new_profile_btn.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #4C1D95,stop:1 #7C3AED);color:white;border:none;"
            "border-radius:12px;font-size:13px;font-weight:700;letter-spacing:0.5px;}"
            "QPushButton:hover{background:#6D28D9;}"
            "QPushButton:pressed{background:#3B0E8C;}"
        )
        self._new_profile_btn.clicked.connect(self._create_new_profile)
        pl.addWidget(self._new_profile_btn)
        return page

    # ── INLINE NOTES PAGE ────────────────────────────────────────────────────

    def _build_notes_page(self):
        from PySide6.QtWidgets import QTextEdit
        page = QFrame(); page.setObjectName("panel")
        pl = QVBoxLayout(page); pl.setContentsMargins(12, 12, 12, 12); pl.setSpacing(0)

        # Rounded inner container — matches Settings/Audit dark theme
        inner = QFrame(); inner.setObjectName("notesInner")
        inner.setStyleSheet(
            "QFrame#notesInner{background:#0F0D1E;"
            "border:1px solid rgba(109,40,217,0.25);border-radius:14px;}"
        )
        il = QVBoxLayout(inner); il.setContentsMargins(0, 0, 0, 0); il.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QWidget(); hdr.setFixedHeight(54)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1A1428,stop:1 #0F0D1E);"
            "border-bottom:1px solid rgba(109,40,217,0.22);"
            "border-top-left-radius:14px;border-top-right-radius:14px;"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20, 0, 18, 0); hl.setSpacing(10)
        icon_l = QLabel("📓")
        icon_l.setStyleSheet("font-size:18px;background:transparent;border:none;")
        title_l = QLabel("SECURE NOTES")
        title_l.setStyleSheet(
            "color:#EDE8FF;font-size:13px;font-weight:800;letter-spacing:2.5px;"
            "background:transparent;border:none;"
        )
        hl.addWidget(icon_l); hl.addWidget(title_l); hl.addStretch()
        il.addWidget(hdr)

        # ── Body: sidebar + editor ────────────────────────────────────────────
        body_w = QWidget(); body_w.setStyleSheet("background:transparent;")
        body = QHBoxLayout(body_w); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)

        # Left sidebar — matches panel dark
        lp = QFrame(); lp.setFixedWidth(200)
        lp.setStyleSheet(
            "background:#110F22;"
            "border-right:1px solid rgba(109,40,217,0.18);"
            "border-bottom-left-radius:14px;"
        )
        lpl = QVBoxLayout(lp); lpl.setContentsMargins(10, 12, 10, 12); lpl.setSpacing(8)

        # ＋ New Note emoji button
        new_btn = QPushButton("📝  New Note")
        new_btn.setFixedHeight(36); new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.18);color:#A78BFA;"
            "border:1px solid rgba(139,92,246,0.35);border-radius:9px;"
            "font-weight:700;font-size:12px;}"
            "QPushButton:hover{background:rgba(139,92,246,0.30);color:#EDE8FF;"
            "border-color:#8B5CF6;}"
        )
        new_btn.clicked.connect(self._notes_new)
        lpl.addWidget(new_btn)

        self._notes_list_scroll = QScrollArea(); self._notes_list_scroll.setWidgetResizable(True)
        self._notes_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._notes_list_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:transparent;width:3px;}"
            "QScrollBar::handle:vertical{background:rgba(109,40,217,0.35);border-radius:2px;}"
            "QScrollBar::handle:vertical:hover{background:#7C3AED;}"
        )
        self._notes_list_w = QWidget(); self._notes_list_w.setStyleSheet("background:transparent;")
        self._notes_list_l = QVBoxLayout(self._notes_list_w)
        self._notes_list_l.setContentsMargins(0, 0, 0, 0); self._notes_list_l.setSpacing(4)
        self._notes_list_l.setAlignment(Qt.AlignTop)
        self._notes_list_scroll.setWidget(self._notes_list_w)
        lpl.addWidget(self._notes_list_scroll)
        body.addWidget(lp)

        # Right editor panel
        ep = QFrame(); ep.setObjectName("notesEditor")
        ep.setStyleSheet(
            "QFrame#notesEditor{background:#0D0B1E;border-bottom-right-radius:14px;}"
        )
        epl = QVBoxLayout(ep); epl.setContentsMargins(18, 16, 18, 14); epl.setSpacing(10)

        self._note_title_edit = QLineEdit()
        self._note_title_edit.setPlaceholderText("Note title…")
        self._note_title_edit.setFixedHeight(42)
        self._note_title_edit.setStyleSheet(
            "QLineEdit{background:transparent;border:none;"
            "border-bottom:2px solid rgba(109,40,217,0.30);"
            "color:#EDE8FF;font-size:15px;font-weight:700;padding:0 4px;}"
            "QLineEdit:focus{border-bottom-color:#8B5CF6;}"
            "QLineEdit::placeholder{color:#3A2A55;}"
        )

        self._note_body_edit = QTextEdit()
        self._note_body_edit.setPlaceholderText("Start writing your secure note…")
        self._note_body_edit.setStyleSheet(
            "QTextEdit{background:#13112A;border:1px solid rgba(109,40,217,0.20);"
            "border-radius:10px;color:#C4B8E8;font-size:13px;padding:10px 12px;}"
            "QTextEdit:focus{border-color:rgba(139,92,246,0.45);background:#16132E;}"
        )

        # Bottom row — timestamp + emoji buttons
        bot_row = QHBoxLayout(); bot_row.setSpacing(8)
        self._note_ts_lbl = QLabel("")
        self._note_ts_lbl.setStyleSheet(
            "color:#3A2A55;font-size:10px;background:transparent;border:none;"
        )

        self._note_del_btn = QPushButton("🗑")
        self._note_del_btn.setFixedSize(34, 34); self._note_del_btn.setCursor(Qt.PointingHandCursor)
        self._note_del_btn.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.25);border-radius:9px;font-size:15px;}"
            "QPushButton:hover{background:rgba(220,30,60,0.22);color:white;"
            "border:1px solid #f87171;}"
        )

        self._note_save_btn = QPushButton("💾")
        self._note_save_btn.setFixedSize(34, 34); self._note_save_btn.setCursor(Qt.PointingHandCursor)
        self._note_save_btn.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);color:white;border:none;"
            "border-radius:9px;font-size:15px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )

        self._note_save_btn.clicked.connect(self._notes_save)
        self._note_del_btn.clicked.connect(self._notes_delete)
        bot_row.addWidget(self._note_ts_lbl); bot_row.addStretch()
        bot_row.addWidget(self._note_del_btn); bot_row.addWidget(self._note_save_btn)

        epl.addWidget(self._note_title_edit)
        epl.addWidget(self._note_body_edit)
        epl.addLayout(bot_row)
        body.addWidget(ep, 1)
        il.addWidget(body_w, 1)
        pl.addWidget(inner, 1)

        # PLUS gate overlay
        self._notes_gate = QWidget(page)
        self._notes_gate.setStyleSheet("background:rgba(6,4,15,0.92);")
        gate_l = QVBoxLayout(self._notes_gate); gate_l.setAlignment(Qt.AlignCenter)
        gate_icon = QLabel("✦"); gate_icon.setAlignment(Qt.AlignCenter)
        gate_icon.setStyleSheet("font-size:48px;color:#a78bfa;background:transparent;border:none;")
        gate_title = QLabel("FluxKey PLUS Feature")
        gate_title.setAlignment(Qt.AlignCenter)
        gate_title.setStyleSheet("color:#e2d5f8;font-size:18px;font-weight:800;background:transparent;border:none;")
        gate_sub = QLabel("Secure Notes requires FluxKey PLUS.")
        gate_sub.setAlignment(Qt.AlignCenter)
        gate_sub.setStyleSheet("color:#6B5A8A;font-size:12px;background:transparent;border:none;")
        gate_l.addWidget(gate_icon); gate_l.addSpacing(8)
        gate_l.addWidget(gate_title); gate_l.addSpacing(4); gate_l.addWidget(gate_sub)
        self._notes_gate.setVisible(not is_plus())
        QTimer.singleShot(0, lambda: self._notes_gate.setGeometry(self._notes_gate.parent().rect()) if self._notes_gate.parent() else None)

        self._notes_current_id = None
        return page

    def _refresh_notes_page(self):
        if hasattr(self, '_notes_gate'):
            self._notes_gate.setVisible(not is_plus())
        if not is_plus():
            return
        for i in reversed(range(self._notes_list_l.count())):
            w = self._notes_list_l.itemAt(i).widget()
            if w: w.deleteLater()
        notes = get_notes()
        for note in notes:
            nid = note["id"]
            title = note.get("title", "Untitled") or "Untitled"
            btn = QPushButton(title)
            btn.setFixedHeight(34); btn.setCursor(Qt.PointingHandCursor)
            is_sel = (nid == getattr(self, "_notes_current_id", None))
            bg  = "rgba(109,40,217,0.22)" if is_sel else "rgba(109,40,217,0.06)"
            col = "#e2d5f8" if is_sel else "#9888C0"
            btn.setStyleSheet(
                f"QPushButton{{background:{bg};color:{col};"
                "border:none;border-radius:8px;font-size:12px;font-weight:600;"
                "text-align:left;padding-left:10px;}"
                "QPushButton:hover{background:rgba(109,40,217,0.18);color:#c4b4d8;}"
            )
            btn.clicked.connect(lambda _, n=note: self._notes_load(n))
            self._notes_list_l.addWidget(btn)
        if notes and self._notes_current_id is None:
            self._notes_load(notes[0])

    def _notes_load(self, note):
        self._notes_current_id = note["id"]
        self._note_title_edit.setText(note.get("title", ""))
        self._note_body_edit.setPlainText(note.get("body", ""))
        ts = note.get("updated", note.get("created", 0))
        self._note_ts_lbl.setText(datetime.datetime.fromtimestamp(ts).strftime("Updated %Y-%m-%d %H:%M") if ts else "")
        self._refresh_notes_page()

    def _notes_new(self):
        self._notes_current_id = secrets.token_hex(8)
        self._note_title_edit.clear(); self._note_body_edit.clear()
        self._note_ts_lbl.setText("New note")

    def _notes_save(self):
        if not hasattr(self, "_notes_current_id") or not self._notes_current_id:
            self._notes_new()
        title = self._note_title_edit.text().strip() or "Untitled"
        save_note(self._notes_current_id, title, self._note_body_edit.toPlainText())
        try: audit.log("note_saved", title)
        except Exception: pass
        self._refresh_notes_page()

    def _notes_delete(self):
        if not getattr(self, "_notes_current_id", None): return
        box = QMessageBox(self); box.setWindowTitle("Delete Note")
        box.setText("Delete this note? This cannot be undone.")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        _style_msgbox(box)
        if box.exec() == QMessageBox.Yes:
            delete_note(self._notes_current_id)
            self._notes_current_id = None
            self._note_title_edit.clear(); self._note_body_edit.clear()
            self._note_ts_lbl.setText("")
            self._refresh_notes_page()

    # ── INLINE SETTINGS PAGE ─────────────────────────────────────────────────

    def _build_settings_page(self):
        from PySide6.QtWidgets import QComboBox
        page = QFrame(); page.setObjectName("panel")
        pl = QVBoxLayout(page); pl.setContentsMargins(12, 12, 12, 12); pl.setSpacing(0)

        # Rounded inner container
        inner_wrap = QFrame()
        inner_wrap.setStyleSheet(
            "QFrame{background:#0F0D1E;border:1px solid rgba(109,40,217,0.22);"
            "border-radius:14px;}"
        )
        iw_l = QVBoxLayout(inner_wrap); iw_l.setContentsMargins(0, 0, 0, 0); iw_l.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────────────
        hdr = QWidget(); hdr.setFixedHeight(58)
        hdr.setStyleSheet(
            "background:#0F0D1E;"
            "border-bottom:1px solid rgba(109,40,217,0.28);"
            "border-top-left-radius:14px;border-top-right-radius:14px;"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(22, 0, 20, 0); hl.setSpacing(14)

        # Gear icon pill
        gear_pill = QLabel("⚙")
        gear_pill.setFixedSize(34, 34)
        gear_pill.setAlignment(Qt.AlignCenter)
        gear_pill.setStyleSheet(
            "background:rgba(109,40,217,0.18);border:1px solid rgba(139,92,246,0.35);"
            "border-radius:10px;color:#a78bfa;font-size:16px;"
        )
        title_l = QLabel("SETTINGS")
        title_l.setStyleSheet(
            "color:#EDE8FF;font-size:14px;font-weight:800;letter-spacing:3px;"
            "background:transparent;border:none;"
        )
        hl.addWidget(gear_pill); hl.addWidget(title_l); hl.addStretch()
        iw_l.addWidget(hdr)

        # Thin accent line under header
        accent = QFrame(); accent.setFixedHeight(2)
        accent.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #7C3AED,stop:0.5 rgba(139,92,246,0.4),stop:1 transparent);"
            "border:none;"
        )
        iw_l.addWidget(accent)

        # ── Scroll area ───────────────────────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
            "QScrollBar:vertical{background:transparent;width:4px;border-radius:2px;}"
            "QScrollBar::handle:vertical{background:#2A1F45;border-radius:2px;min-height:24px;}"
            "QScrollBar::handle:vertical:hover{background:#7C3AED;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        body = QWidget(); body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(16, 18, 16, 30); bl.setSpacing(20)

        # ── Helpers ───────────────────────────────────────────────────────────
        def section_label(text, danger=False):
            col = "#f87171" if danger else "#8B5CF6"
            dim = "rgba(220,30,60,0.15)" if danger else "rgba(109,40,217,0.14)"
            w = QWidget(); w.setStyleSheet("background:transparent;")
            r = QHBoxLayout(w); r.setContentsMargins(0, 0, 0, 0); r.setSpacing(8)
            dot = QLabel(); dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background:{col};border-radius:3px;border:none;")
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color:{col};font-size:10px;font-weight:800;letter-spacing:2.5px;"
                "background:transparent;border:none;"
            )
            line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFixedHeight(1)
            line.setStyleSheet(f"background:{dim};border:none;")
            r.addWidget(dot, 0, Qt.AlignVCenter)
            r.addWidget(lbl, 0, Qt.AlignVCenter)
            r.addWidget(line)
            return w

        def make_card(danger=False):
            nm = f"sc_{random.randint(10000, 99999)}"
            f = QFrame(); f.setObjectName(nm)
            if danger:
                f.setStyleSheet(
                    f"QFrame#{nm}{{background:rgba(220,20,50,0.05);"
                    "border:1px solid rgba(220,30,60,0.22);border-radius:16px;}"
                    f"QFrame#{nm} QLabel{{background:transparent;border:none;}}"
                    f"QFrame#{nm} QWidget{{background:transparent;}}"
                )
            else:
                f.setStyleSheet(
                    f"QFrame#{nm}{{background:#13112A;"
                    "border:1px solid rgba(109,40,217,0.20);border-radius:16px;}"
                    f"QFrame#{nm} QLabel{{background:transparent;border:none;}}"
                    f"QFrame#{nm} QWidget{{background:transparent;}}"
                )
            return f

        def row_sep():
            s = QFrame(); s.setFrameShape(QFrame.HLine)
            s.setStyleSheet("background:rgba(109,40,217,0.10);max-height:1px;border:none;")
            return s

        def mk_toggle(active):
            b = QPushButton("ON" if active else "OFF")
            b.setFixedSize(62, 30); b.setCursor(Qt.PointingHandCursor)
            set_tog(b, active); return b

        def set_tog(btn, active):
            btn.setText("ON" if active else "OFF")
            if active:
                btn.setStyleSheet(
                    "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    "stop:0 #6D28D9,stop:1 #8B5CF6);color:white;border:none;"
                    "border-radius:9px;font-size:11px;font-weight:700;}"
                    "QPushButton:hover{background:#7C3AED;}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton{background:#0d0b1c;color:#3D2A58;"
                    "border:1px solid #1c1530;border-radius:9px;"
                    "font-size:11px;font-weight:600;}"
                    "QPushButton:hover{border-color:#7C3AED;color:#8B5CF6;}"
                )

        def mk_fld(ph):
            f = QLineEdit(); f.setPlaceholderText(ph); f.setFixedHeight(42)
            f.setEchoMode(QLineEdit.Password)
            f.setStyleSheet(
                "QLineEdit{background:#0C0A1E;border:1px solid #1A1730;"
                "border-radius:11px;padding:0 14px;color:#D4CCEE;font-size:13px;}"
                "QLineEdit:focus{border:1.5px solid #7C3AED;background:#11102A;}"
                "QLineEdit::placeholder{color:#3A2A55;}"
            )
            return f

        def setting_row(label, sublabel=None, widget=None, card_layout=None):
            """Add a labelled setting row with optional sublabel and right-side widget."""
            row = QHBoxLayout(); row.setSpacing(0)
            txt = QVBoxLayout(); txt.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color:#c4b4d8;font-size:13px;font-weight:600;background:transparent;border:none;")
            txt.addWidget(lbl)
            if sublabel:
                sub = QLabel(sublabel)
                sub.setStyleSheet("color:#3D2A58;font-size:10px;background:transparent;border:none;")
                txt.addWidget(sub)
            row.addLayout(txt); row.addStretch()
            if widget:
                row.addWidget(widget)
            if card_layout is not None:
                card_layout.addLayout(row)
            return row

        # ── SECTION: SECURITY ─────────────────────────────────────────────────
        bl.addWidget(section_label("SECURITY"))
        sec = make_card()
        sc = QVBoxLayout(sec); sc.setContentsMargins(20, 18, 20, 18); sc.setSpacing(0)

        # Auto-lock row
        from PySide6.QtWidgets import QComboBox
        self._s_lock_combo = QComboBox()
        for o in ["Disabled", "1 min", "5 min", "10 min", "30 min"]:
            self._s_lock_combo.addItem(o)
        self._s_lock_combo.setFixedHeight(36); self._s_lock_combo.setFixedWidth(116)
        self._s_lock_combo.setStyleSheet(
            "QComboBox{background:#0C0A1E;border:1px solid #1A1730;"
            "border-radius:10px;padding:0 12px;color:#c4b4d8;font-size:12px;}"
            "QComboBox::drop-down{border:none;width:18px;}"
            "QComboBox QAbstractItemView{background:#16132A;border:1px solid #261840;"
            "color:#c4b4d8;selection-background-color:#7C3AED;outline:none;}"
        )
        mins_map = {0: 0, 1: 1, 2: 5, 3: 10, 4: 30}
        cur_mins = get_auto_lock_minutes()
        for k, v in mins_map.items():
            if v == cur_mins:
                self._s_lock_combo.setCurrentIndex(k); break
        self._s_lock_combo.currentIndexChanged.connect(
            lambda i: set_auto_lock_minutes(mins_map.get(i, 0))
        )
        setting_row("Auto-lock after", None, self._s_lock_combo, sc)

        sc.addSpacing(14); sc.addWidget(row_sep()); sc.addSpacing(14)

        # Clipboard row
        from core.vault import _load_config, _save_config
        cfg = _load_config()
        self._s_clip_tog = mk_toggle(cfg.get("auto_clear_clipboard", True))
        def do_clip():
            c = _load_config(); v = c.get("auto_clear_clipboard", True)
            c["auto_clear_clipboard"] = not v; _save_config(c)
            set_tog(self._s_clip_tog, not v)
        self._s_clip_tog.clicked.connect(do_clip)
        setting_row("Auto-clear clipboard", "Clears copied passwords after 30 seconds",
                    self._s_clip_tog, sc)

        bl.addWidget(sec)

        # ── SECTION: CHANGE MASTER PASSWORD ──────────────────────────────────
        bl.addWidget(section_label("CHANGE MASTER PASSWORD"))
        pw_card = make_card()
        pc = QVBoxLayout(pw_card); pc.setContentsMargins(20, 18, 20, 18); pc.setSpacing(10)

        self._s_cur  = mk_fld("Current password")
        self._s_new1 = mk_fld("New password")
        self._s_new2 = mk_fld("Confirm new password")
        self._s_pmsg = QLabel(""); self._s_pmsg.setFixedHeight(14)
        self._s_pmsg.setStyleSheet(
            "font-size:11px;background:transparent;border:none;padding-left:2px;"
        )
        for w in (self._s_cur, self._s_new1, self._s_new2, self._s_pmsg):
            pc.addWidget(w)

        # Divider before button
        pc.addSpacing(4)
        div2 = QFrame(); div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet("background:rgba(109,40,217,0.10);max-height:1px;border:none;")
        pc.addWidget(div2); pc.addSpacing(4)

        upd = QPushButton("Update Password"); upd.setFixedHeight(42)
        upd.setCursor(Qt.PointingHandCursor)
        upd.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);color:white;border:none;"
            "border-radius:11px;font-weight:700;font-size:13px;letter-spacing:0.5px;}"
            "QPushButton:hover{background:#7C3AED;}"
            "QPushButton:pressed{background:#4a1aaa;}"
        )
        upd.clicked.connect(self._settings_chpw)
        pc.addWidget(upd)
        bl.addWidget(pw_card)

        # ── SECTION: FLUXKEY PLUS ─────────────────────────────────────────────
        bl.addWidget(section_label("FLUXKEY PLUS"))
        plus_card = make_card()
        plc = QVBoxLayout(plus_card); plc.setContentsMargins(20, 18, 20, 18); plc.setSpacing(14)

        # Status row
        plus_status_row = QHBoxLayout(); plus_status_row.setSpacing(14)
        plus_icon = QLabel("✦")
        plus_icon.setFixedSize(36, 36); plus_icon.setAlignment(Qt.AlignCenter)
        plus_icon.setStyleSheet(
            "background:rgba(139,92,246,0.18);border:1.5px solid rgba(139,92,246,0.40);"
            "border-radius:10px;color:#a78bfa;font-size:16px;font-weight:900;"
        )
        plus_txt = QVBoxLayout(); plus_txt.setSpacing(2)
        plus_title = QLabel("FluxKey PLUS" if is_plus() else "Upgrade to PLUS")
        plus_title.setStyleSheet(
            "color:#e2d5f8;font-size:13px;font-weight:700;background:transparent;border:none;"
        )
        plus_sub = QLabel(
            "✓ Active — Notes, Audit Log & unlimited vaults unlocked" if is_plus()
            else "Unlock Secure Notes, Audit Log and unlimited vaults"
        )
        plus_sub.setWordWrap(True)
        plus_sub.setStyleSheet(
            f"color:{'#22c55e' if is_plus() else '#4A3370'};"
            "font-size:10px;background:transparent;border:none;"
        )
        plus_txt.addWidget(plus_title); plus_txt.addWidget(plus_sub)
        plus_status_row.addWidget(plus_icon); plus_status_row.addLayout(plus_txt)
        plc.addLayout(plus_status_row)

        if not is_plus():
            # Enter code button
            enter_code_btn = QPushButton("✦  Enter PLUS Code")
            enter_code_btn.setFixedHeight(44); enter_code_btn.setCursor(Qt.PointingHandCursor)
            enter_code_btn.setStyleSheet(
                "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #5b21b6,stop:1 #7c3aed);"
                "color:white;border:none;border-radius:11px;"
                "font-weight:800;font-size:13px;letter-spacing:1px;}"
                "QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #6d28d9,stop:1 #8b5cf6);}"
                "QPushButton:pressed{background:#4c1d95;}"
            )
            enter_code_btn.clicked.connect(self._open_enter_code)
            plc.addWidget(enter_code_btn)

        bl.addWidget(plus_card)

        # ── SECTION: DANGER ZONE ──────────────────────────────────────────────
        bl.addWidget(section_label("DANGER ZONE", danger=True))
        dz = make_card(danger=True)
        dzl = QVBoxLayout(dz); dzl.setContentsMargins(20, 18, 20, 18); dzl.setSpacing(14)

        # Warning info row
        warn_row = QHBoxLayout(); warn_row.setSpacing(14)
        wi = QLabel("!")
        wi.setFixedSize(32, 32); wi.setAlignment(Qt.AlignCenter)
        wi.setStyleSheet(
            "background:rgba(220,30,60,0.12);border:1px solid rgba(220,30,60,0.30);"
            "border-radius:10px;color:#f87171;font-weight:800;font-size:15px;"
        )
        wt = QLabel("Permanently deletes all passwords and your master password. This cannot be undone.")
        wt.setWordWrap(True)
        wt.setStyleSheet(
            "color:#5A4060;font-size:11px;line-height:1.6;background:transparent;border:none;"
        )
        warn_row.addWidget(wi, 0, Qt.AlignTop); warn_row.addWidget(wt)
        dzl.addLayout(warn_row)

        wipe = QPushButton("Wipe Vault & Reset Everything"); wipe.setFixedHeight(42)
        wipe.setCursor(Qt.PointingHandCursor)
        wipe.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.28);border-radius:11px;"
            "font-weight:700;font-size:12px;letter-spacing:0.3px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;border-color:#ff2d6f;}"
            "QPushButton:pressed{background:#cc1050;}"
        )
        wipe.clicked.connect(self._settings_wipe)
        dzl.addWidget(wipe)
        bl.addWidget(dz)
        bl.addStretch()

        scroll.setWidget(body)
        iw_l.addWidget(scroll, 1)
        pl.addWidget(inner_wrap, 1)
        return page

    def _settings_chpw(self):
        cur,n1,n2 = self._s_cur.text(), self._s_new1.text(), self._s_new2.text()
        def st(m, ok=False):
            self._s_pmsg.setStyleSheet(
                f"color:{'#8B5CF6' if ok else '#f87171'};"
                "font-size:11px;background:transparent;border:none;padding-left:2px;"
            )
            self._s_pmsg.setText(m)
        ok, msg, _ = verify_master_password(cur)
        if not ok: return st(msg)
        if not n1: return st("New password cannot be empty.")
        if n1 != n2: return st("Passwords do not match.")
        if len(n1) < 4: return st("Minimum 4 characters.")
        set_master_password(n1)
        self._s_cur.clear(); self._s_new1.clear(); self._s_new2.clear()
        st("Password updated.", ok=True)

    def _settings_wipe(self):
        box = QMessageBox(self); box.setWindowTitle("Wipe Vault")
        box.setText("Permanently delete ALL vault entries and master password?\n\nThis CANNOT be undone.")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        _style_msgbox(box)
        if box.exec() == QMessageBox.Yes:
            wipe_all(); self._logout()

    # ── INLINE AUDIT LOG PAGE ────────────────────────────────────────────────

    _AUDIT_ACTION_META = {
        "copy":           ("📋", "#4ade80",  "Security"),
        "generate":       ("⚡", "#c084fc",  "Generate"),
        "save_entry":     ("💾", "#60a5fa",  "Vault"),
        "delete_entry":   ("🗑", "#f87171",  "Vault"),
        "note_saved":     ("📝", "#a78bfa",  "Notes"),
        "vault_unlock":   ("🔓", "#34d399",  "Auth"),
        "login_success":  ("✅", "#22c55e",  "Auth"),
        "login_failed":   ("❌", "#ef4444",  "Auth"),
        "logout":         ("🔐", "#fb923c",  "Auth"),
        "move_entry":     ("📂", "#fb923c",  "Vault"),
        "vault_created":  ("📁", "#f9a8d4",  "Vault"),
        "profile_switch": ("🔄", "#38bdf8",  "Profile"),
        "master_changed": ("🔑", "#fbbf24",  "Security"),
        "vault_scan":     ("🛡", "#34d399",  "Security"),
        "clipboard_clear":("🧹", "#94a3b8",  "Security"),
    }
    _AUDIT_CATEGORIES = ["All","Auth","Vault","Generate","Security","Notes","Profile","Settings"]

    def _build_audit_page(self):
        page = QFrame(); page.setObjectName("panel")
        pl = QVBoxLayout(page); pl.setContentsMargins(12, 12, 12, 12); pl.setSpacing(0)

        # Rounded inner container
        inner = QFrame()
        inner.setStyleSheet(
            "QFrame{background:#0F0D1E;border:1px solid rgba(109,40,217,0.25);"
            "border-radius:14px;}"
        )
        il = QVBoxLayout(inner); il.setContentsMargins(0, 0, 0, 0); il.setSpacing(0)

        hdr = QWidget(); hdr.setFixedHeight(54)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1A1428,stop:1 #0F0D1E);"
            "border-bottom:1px solid rgba(109,40,217,0.22);"
            "border-top-left-radius:14px;border-top-right-radius:14px;"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(18,0,14,0); hl.setSpacing(10)
        title_l = QLabel("🔍  ACTIVITY LOG")
        title_l.setStyleSheet("color:#EDE8FF;font-size:13px;font-weight:800;letter-spacing:2px;background:transparent;border:none;")
        self._audit_clear_btn = QPushButton("Clear All")
        self._audit_clear_btn.setFixedHeight(28); self._audit_clear_btn.setCursor(Qt.PointingHandCursor)
        self._audit_clear_btn.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.22);border-radius:7px;"
            "font-size:11px;font-weight:600;padding:0 12px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;border-color:#ff2d6f;}"
        )
        self._audit_clear_btn.clicked.connect(self._audit_clear)
        hl.addWidget(title_l); hl.addStretch()
        hl.addWidget(self._audit_clear_btn)
        il.addWidget(hdr)

        filter_row = QWidget(); filter_row.setFixedHeight(46)
        filter_row.setStyleSheet("background:#110F22;border:none;")
        fr = QHBoxLayout(filter_row); fr.setContentsMargins(14,0,14,0); fr.setSpacing(6)
        self._audit_search = QLineEdit()
        self._audit_search.setPlaceholderText("Search actions or details...")
        self._audit_search.setFixedHeight(28)
        self._audit_search.setStyleSheet(
            "QLineEdit{background:#0F0D1E;border:1px solid rgba(109,40,217,0.28);"
            "border-radius:8px;padding:0 10px;color:#C4B8E8;font-size:12px;}"
            "QLineEdit:focus{border-color:#7C3AED;}"
            "QLineEdit::placeholder{color:#3D2A58;}"
        )
        self._audit_search.textChanged.connect(self._audit_filter)
        fr.addWidget(self._audit_search, 1)

        self._audit_cat_btns = {}
        self._audit_filter_cat = "All"
        for cat in self._AUDIT_CATEGORIES:
            b = QPushButton(cat); b.setFixedHeight(26); b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True); b.setChecked(cat == "All")
            b.setStyleSheet(self._audit_cat_style(cat == "All"))
            b.clicked.connect(lambda _, c=cat: self._audit_set_cat(c))
            fr.addWidget(b)
            self._audit_cat_btns[cat] = b
        il.addWidget(filter_row)

        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet("background:rgba(109,40,217,0.18);border:none;")
        il.addWidget(div)

        self._audit_stats_lbl = QLabel("")
        self._audit_stats_lbl.setFixedHeight(28)
        self._audit_stats_lbl.setAlignment(Qt.AlignCenter)
        self._audit_stats_lbl.setStyleSheet(
            "color:#6B5A8A;font-size:10px;font-weight:600;letter-spacing:1px;"
            "background:#0D0B1A;border:none;"
        )
        il.addWidget(self._audit_stats_lbl)

        self._audit_scroll = QScrollArea(); self._audit_scroll.setWidgetResizable(True)
        self._audit_scroll.setStyleSheet(
            "QScrollArea{background:#080614;border:none;"
            "border-bottom-left-radius:14px;border-bottom-right-radius:14px;}"
            "QScrollBar:vertical{background:transparent;width:4px;}"
            "QScrollBar::handle:vertical{background:rgba(109,40,217,0.35);border-radius:2px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        self._audit_list_w = QWidget(); self._audit_list_w.setStyleSheet("background:transparent;")
        self._audit_list_l = QVBoxLayout(self._audit_list_w)
        self._audit_list_l.setContentsMargins(10,8,10,8); self._audit_list_l.setSpacing(3)
        self._audit_list_l.setAlignment(Qt.AlignTop)
        self._audit_scroll.setWidget(self._audit_list_w)
        il.addWidget(self._audit_scroll, 1)

        pl.addWidget(inner, 1)

        # PLUS gate
        self._audit_gate = QWidget(page)
        self._audit_gate.setStyleSheet("background:rgba(6,4,15,0.92);border-radius:14px;")
        gate_l = QVBoxLayout(self._audit_gate); gate_l.setAlignment(Qt.AlignCenter)
        gate_icon = QLabel("🔍"); gate_icon.setAlignment(Qt.AlignCenter)
        gate_icon.setStyleSheet("font-size:48px;background:transparent;border:none;")
        gate_title = QLabel("FluxKey PLUS Feature")
        gate_title.setAlignment(Qt.AlignCenter)
        gate_title.setStyleSheet("color:#e2d5f8;font-size:18px;font-weight:800;background:transparent;border:none;")
        gate_sub = QLabel("Audit Log requires FluxKey PLUS.")
        gate_sub.setAlignment(Qt.AlignCenter)
        gate_sub.setStyleSheet("color:#6B5A8A;font-size:12px;background:transparent;border:none;")
        gate_l.addWidget(gate_icon); gate_l.addSpacing(8)
        gate_l.addWidget(gate_title); gate_l.addSpacing(4); gate_l.addWidget(gate_sub)
        self._audit_gate.setVisible(not is_plus())
        QTimer.singleShot(0, lambda: self._audit_gate.setGeometry(self._audit_gate.parent().rect()) if self._audit_gate.parent() else None)

        self._audit_all_entries = []
        return page

    def _audit_cat_style(self, active):
        if active:
            return (
                "QPushButton{background:rgba(109,40,217,0.35);color:#E0D8FF;"
                "border:1px solid rgba(139,92,246,0.6);border-radius:7px;"
                "font-size:10px;font-weight:700;padding:0 8px;}"
            )
        return (
            "QPushButton{background:transparent;color:#4A3370;border:none;"
            "border-radius:7px;font-size:10px;font-weight:600;padding:0 8px;}"
            "QPushButton:hover{background:rgba(109,40,217,0.15);color:#A090CC;}"
        )

    def _audit_set_cat(self, cat):
        self._audit_filter_cat = cat
        for c, b in self._audit_cat_btns.items():
            b.setChecked(c == cat); b.setStyleSheet(self._audit_cat_style(c == cat))
        self._audit_render()

    def _audit_filter(self): self._audit_render()

    def _audit_render(self):
        for i in reversed(range(self._audit_list_l.count())):
            w = self._audit_list_l.itemAt(i).widget()
            if w: w.deleteLater()
        search = self._audit_search.text().lower()
        cat_f  = self._audit_filter_cat
        filtered = []
        for e in self._audit_all_entries:
            action = e.get("action","")
            detail = e.get("detail","")
            _, _, cat = self._AUDIT_ACTION_META.get(action, ("•","#6B5A8A","Other"))
            if cat_f != "All" and cat != cat_f: continue
            if search and search not in action.lower() and search not in detail.lower(): continue
            filtered.append(e)
        total = len(self._audit_all_entries); shown = len(filtered)
        self._audit_stats_lbl.setText(
            f"SHOWING {shown} OF {total} EVENTS  •  "
            f"{'ALL CATEGORIES' if cat_f == 'All' else cat_f.upper()}"
        )
        for e in filtered:
            action = e.get("action","unknown")
            detail = e.get("detail","")
            ts     = e.get("ts",0)
            icon, color, _ = self._AUDIT_ACTION_META.get(action, ("•","#6B5A8A","Other"))
            time_str = datetime.datetime.fromtimestamp(ts).strftime("%m/%d %H:%M") if ts else "—"
            row = QFrame(); row.setFixedHeight(44)
            row.setStyleSheet(
                "QFrame{background:rgba(109,40,217,0.04);"
                "border:1px solid rgba(109,40,217,0.10);border-radius:9px;}"
                "QFrame QLabel{background:transparent;border:none;}"
                "QFrame:hover{background:rgba(109,40,217,0.10);"
                "border-color:rgba(139,92,246,0.25);}"
            )
            rl = QHBoxLayout(row); rl.setContentsMargins(10,0,12,0); rl.setSpacing(10)
            ico_l = QLabel(icon); ico_l.setFixedWidth(22); ico_l.setAlignment(Qt.AlignCenter)
            ico_l.setStyleSheet(f"font-size:14px;color:{color};")
            act_l = QLabel(action.replace("_"," ").title())
            act_l.setStyleSheet(f"color:{color};font-size:12px;font-weight:700;")
            act_l.setFixedWidth(130)
            det_l = QLabel(detail[:60] + ("…" if len(detail)>60 else ""))
            det_l.setStyleSheet("color:#4A3A6A;font-size:11px;")
            ts_l = QLabel(time_str)
            ts_l.setStyleSheet("color:#2E2248;font-size:10px;font-weight:600;")
            ts_l.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            rl.addWidget(ico_l); rl.addWidget(act_l); rl.addWidget(det_l,1); rl.addWidget(ts_l)
            self._audit_list_l.addWidget(row)
        if not filtered:
            empty = QLabel("No events found")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#2E2248;font-size:13px;font-weight:600;background:transparent;border:none;")
            self._audit_list_l.addWidget(empty)

    def _refresh_audit_page(self):
        if hasattr(self, '_audit_gate'):
            self._audit_gate.setVisible(not is_plus())
        if not is_plus(): return
        self._audit_all_entries = audit.load()
        self._audit_search.clear()
        self._audit_filter_cat = "All"
        for c, b in self._audit_cat_btns.items():
            b.setChecked(c == "All"); b.setStyleSheet(self._audit_cat_style(c == "All"))
        self._audit_render()

    def _audit_clear(self):
        box = QMessageBox(self); box.setWindowTitle("Clear Audit Log")
        box.setText("Clear all audit log entries? This cannot be undone.")
        box.setStandardButtons(QMessageBox.Yes|QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        _style_msgbox(box)
        if box.exec() == QMessageBox.Yes:
            audit.clear(); self._refresh_audit_page()

    def _refresh_switch_page(self):
        """Repopulate profile list."""
        for i in reversed(range(self._switch_list_l.count())):
            w = self._switch_list_l.itemAt(i).widget()
            if w: w.deleteLater()

        profiles = load_profiles()
        current_id = get_current_profile_id()
        max_profiles = 10 if is_plus() else 2

        for prof in profiles:
            pid   = prof.get("id", "default")
            name  = prof.get("username", "FluxUser")
            av    = prof.get("avatar", "🦊")
            active = (pid == current_id)

            row = QFrame()
            row.setStyleSheet(
                f"QFrame{{background:{'rgba(109,40,217,0.18)' if active else 'rgba(109,40,217,0.06)'};"
                f"border:{'2px solid rgba(139,92,246,0.70)' if active else '1px solid rgba(109,40,217,0.18)'};"
                "border-radius:13px;}"
                "QFrame QLabel{background:transparent;border:none;}"
            )
            row.setFixedHeight(58)
            rl = QHBoxLayout(row); rl.setContentsMargins(14,0,14,0); rl.setSpacing(12)

            av_lbl = QLabel(av); av_lbl.setFixedSize(34,34)
            av_lbl.setAlignment(Qt.AlignCenter)
            av_lbl.setStyleSheet("font-size:20px;background:transparent;")

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(
                f"color:{'#E0D8FF' if active else '#9888C0'};"
                "font-size:13px;font-weight:700;"
            )
            badge = QLabel("")
            badge.setVisible(False)

            rl.addWidget(av_lbl)
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(name_lbl); col.addWidget(badge)
            rl.addLayout(col); rl.addStretch()

            if not active:
                sw_btn = QPushButton("Switch →")
                sw_btn.setFixedSize(76, 28); sw_btn.setCursor(Qt.PointingHandCursor)
                sw_btn.setStyleSheet(
                    "QPushButton{background:rgba(109,40,217,0.20);color:#A78BFA;"
                    "border:1px solid rgba(109,40,217,0.40);border-radius:8px;"
                    "font-size:11px;font-weight:700;}"
                    "QPushButton:hover{background:rgba(109,40,217,0.38);color:#EDE0FF;}"
                )
                sw_btn.clicked.connect(lambda _, p=pid: self._switch_to_profile(p))
                rl.addWidget(sw_btn)

            if pid != "default":
                del_btn = QPushButton("✕")
                del_btn.setFixedSize(26, 26); del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setStyleSheet(
                    "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
                    "border:1px solid rgba(220,30,60,0.20);border-radius:7px;font-weight:700;}"
                    "QPushButton:hover{background:#ff2d6f;color:white;border-color:#ff2d6f;}"
                )
                del_btn.clicked.connect(lambda _, p=pid: self._delete_profile(p))
                rl.addWidget(del_btn)

            self._switch_list_l.addWidget(row)

        # Disable new profile button if at limit
        count = len(profiles)
        self._new_profile_btn.setEnabled(count < max_profiles)
        self._new_profile_btn.setStyleSheet(
            self._new_profile_btn.styleSheet() if count < max_profiles else
            "QPushButton{background:rgba(109,40,217,0.10);color:#4A3370;border:none;"
            "border-radius:12px;font-size:13px;font-weight:700;}"
        )

    def _switch_to_profile(self, pid: str):
        """Switch active profile — reloads vault + groups from that profile's files."""
        set_current_profile_id(pid)
        try:
            audit.log("profile_switch", pid)
        except Exception: pass
        from core.vault import Vault, set_active_profile
        set_active_profile(pid)
        vpath = _profile_vault_path(pid)
        self.vault = Vault(vault_file=vpath if vpath else None, profile_id=pid)
        self._refresh_vault()
        self._nav_panel._refresh_prof()
        if hasattr(self, '_switch_page'):
            self._refresh_switch_page()

    def _delete_profile(self, pid: str):
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(self); box.setWindowTitle("Delete Profile")
        box.setText(f"Delete this profile and all its passwords?\nThis cannot be undone.")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        _style_msgbox(box)
        if box.exec() == QMessageBox.Yes:
            current = get_current_profile_id()
            delete_profile(pid)
            if current == pid:
                set_current_profile_id("default")
                from core.vault import Vault as _V
                self.vault = _V()
            self._refresh_switch_page()
            self._nav_panel._refresh_prof()

    def _create_new_profile(self):
        """Open dialog to create a new profile."""
        profiles = load_profiles()
        max_p = 10 if is_plus() else 2
        if len(profiles) >= max_p:
            return
        dlg = NewProfileDialog(self)
        if dlg.exec() == QDialog.Accepted:
            name, avatar = dlg.result_name, dlg.result_avatar
            pid = create_profile(name, avatar)
            self._refresh_switch_page()

    def _refresh_account_page(self):
        """Populate the account page with current profile data."""
        prof = load_profile()
        self._acc_avatar.setText(prof.get("avatar", "🦊"))
        self._acc_name.setText(prof.get("username", "FluxUser"))

        # Clear and repopulate stats
        for i in reversed(range(self._acc_stats_l.count())):
            item = self._acc_stats_l.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        entries = self.vault.load()
        groups  = get_all_groups()
        user_groups = [g for g in groups if g["id"] != DEFAULT_VAULT_ID]

        stat_rows = [
            ("Passwords saved", str(len(entries)), "#8B5CF6"),
            ("Vaults",          str(len(user_groups)), "#3b82f6"),
            ("Account type",    "PLUS" if is_plus() else "FREE", "#fbbf24" if is_plus() else "#6b5a8a"),
        ]
        for label, val, color in stat_rows:
            row = QFrame()
            row.setStyleSheet(
                "QFrame{background:rgba(123,47,255,0.05);"
                "border:1px solid rgba(123,47,255,0.14);border-radius:10px;}"
                "QFrame QLabel{background:transparent;border:none;}"
            )
            rl = QHBoxLayout(row); rl.setContentsMargins(14, 10, 14, 10)
            lbl = QLabel(label); lbl.setStyleSheet("color:#7060a0;font-size:12px;font-weight:600;")
            val_l = QLabel(val); val_l.setStyleSheet(f"color:{color};font-size:13px;font-weight:800;")
            rl.addWidget(lbl); rl.addStretch(); rl.addWidget(val_l)
            self._acc_stats_l.addWidget(row)

    def _edit_profile_from_account(self):
        dlg = ProfileDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_account_page()
            if hasattr(self, "_nav_panel"):
                self._nav_panel._refresh_prof()


# ── History dialog — carousel design ─────────────────────────────────────
class HistoryDialog(QDialog):
    """Horizontal carousel — one password per card, auto-slides every 3s."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password History")
        self.setFixedWidth(460)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("fluxDialog")
        self.selected = None

        self._history = load_history()
        self._idx     = 0
        self._total   = len(self._history)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        hdr = QLabel("Recent Passwords")
        hdr.setStyleSheet(
            "color:#8B5CF6;font-size:15px;font-weight:800;letter-spacing:1px;"
        )
        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedHeight(28); clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            "QPushButton{background:rgba(220,30,60,0.08);color:#f87171;"
            "border:1px solid rgba(220,30,60,0.25);border-radius:8px;"
            "font-size:11px;padding:0 12px;}"
            "QPushButton:hover{background:#ff2d6f;color:white;}"
        )
        clear_btn.clicked.connect(lambda: (clear_history(), self.reject()))
        hdr_row.addWidget(hdr); hdr_row.addStretch(); hdr_row.addWidget(clear_btn)
        layout.addLayout(hdr_row)

        if not self._history:
            empty = QLabel("No history yet.\nGenerate a password to start tracking.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#3A2A55;font-size:12px;padding:28px;")
            layout.addWidget(empty)
            close = QPushButton("Close"); close.setFixedHeight(38)
            close.setCursor(Qt.PointingHandCursor)
            close.setStyleSheet(
                "QPushButton{background:#181030;color:#5A4070;"
                "border:1px solid #261840;border-radius:9px;font-weight:600;}"
                "QPushButton:hover{color:white;border-color:#7C3AED;}"
            )
            close.clicked.connect(self.reject); layout.addWidget(close)
            return

        # ── Counter ────────────────────────────────────────────────────
        self._counter = QLabel(f"1 / {self._total}")
        self._counter.setAlignment(Qt.AlignCenter)
        self._counter.setStyleSheet("color:#3D2A58;font-size:11px;")
        layout.addWidget(self._counter)

        # ── Card area ──────────────────────────────────────────────────
        self._card = QFrame()
        self._card.setObjectName("histCard")
        self._card.setFixedHeight(130)
        self._card.setStyleSheet(
            "QFrame#histCard{background:#0d0b1a;"
            "border:1px solid rgba(123,47,255,0.3);border-radius:16px;}"
        )
        card_l = QVBoxLayout(self._card)
        card_l.setContentsMargins(20,16,20,16); card_l.setSpacing(8)

        # Timestamp
        self._ts_lbl = QLabel("")
        self._ts_lbl.setStyleSheet("color:#3D2A58;font-size:10px;letter-spacing:0.5px;")
        card_l.addWidget(self._ts_lbl)

        # Password
        self._pwd_lbl = QLabel("")
        self._pwd_lbl.setStyleSheet(
            "color:#c084fc;"
            "font-family:'JetBrains Mono','Consolas',monospace;"
            "font-size:13px;letter-spacing:1.5px;"
        )
        self._pwd_lbl.setWordWrap(True)
        card_l.addWidget(self._pwd_lbl)
        layout.addWidget(self._card)

        # ── Dot indicators ────────────────────────────────────────────
        self._dots_row = QHBoxLayout()
        self._dots_row.setSpacing(6)
        self._dots_row.addStretch()
        self._dots = []
        for i in range(min(self._total, 10)):
            dot = QLabel()
            dot.setFixedSize(8, 8)
            self._dots.append(dot)
            self._dots_row.addWidget(dot)
        self._dots_row.addStretch()
        layout.addLayout(self._dots_row)

        # ── Nav + action buttons ──────────────────────────────────────
        nav_row = QHBoxLayout(); nav_row.setSpacing(10)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedSize(40, 40); self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.12);color:#8B5CF6;"
            "border:1px solid rgba(123,47,255,0.25);border-radius:10px;font-size:14px;}"
            "QPushButton:hover{background:rgba(123,47,255,0.25);color:white;}"
        )
        self._prev_btn.clicked.connect(self._prev)

        self._use_btn = QPushButton("Use This Password")
        self._use_btn.setFixedHeight(40); self._use_btn.setCursor(Qt.PointingHandCursor)
        self._use_btn.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6D28D9,stop:1 #8B5CF6);"
            "color:white;border:none;border-radius:10px;"
            "font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:#7C3AED;}"
        )
        self._use_btn.clicked.connect(self._use)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedSize(40, 40); self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.setStyleSheet(self._prev_btn.styleSheet())
        self._next_btn.clicked.connect(self._next)

        nav_row.addWidget(self._prev_btn); nav_row.addWidget(self._use_btn)
        nav_row.addWidget(self._next_btn)
        layout.addLayout(nav_row)

        # Copy + Close row
        bot_row = QHBoxLayout(); bot_row.setSpacing(10)
        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setFixedHeight(36); self._copy_btn.setCursor(Qt.PointingHandCursor)
        self._copy_btn.setStyleSheet(
            "QPushButton{background:rgba(109,40,217,0.12);color:#8B5CF6;"
            "border:1px solid rgba(123,47,255,0.25);border-radius:9px;"
            "font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:rgba(123,47,255,0.22);color:white;}"
        )
        self._copy_btn.clicked.connect(self._copy)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36); close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton{background:#110e20;color:#5A4070;"
            "border:1px solid #1c1530;border-radius:9px;"
            "font-size:12px;font-weight:600;}"
            "QPushButton:hover{color:white;border-color:#7C3AED;}"
        )
        close_btn.clicked.connect(self.reject)
        bot_row.addWidget(self._copy_btn); bot_row.addWidget(close_btn)
        layout.addLayout(bot_row)

        # Auto-slide timer
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._next)
        self._auto_timer.start(3000)

        # Pause auto-slide on user interaction
        self._prev_btn.clicked.connect(self._pause_auto)
        self._next_btn.clicked.connect(self._pause_auto)
        self._use_btn.clicked.connect(self._pause_auto)

        self._update_card()

    def _update_card(self):
        if not self._history: return
        item = self._history[self._idx]
        ts = datetime.datetime.fromtimestamp(item.get("created", 0)).strftime("%b %d  %H:%M")
        self._ts_lbl.setText(ts)
        pwd = item["password"]
        self._pwd_lbl.setText(pwd if len(pwd)<=36 else pwd[:34]+"…")
        self._counter.setText(f"{self._idx+1} / {self._total}")
        # Update dots
        for i, dot in enumerate(self._dots):
            if i == self._idx % len(self._dots):
                dot.setStyleSheet("background:#8B5CF6;border-radius:4px;")
            else:
                dot.setStyleSheet("background:rgba(123,47,255,0.2);border-radius:4px;")

    def _prev(self):
        self._idx = (self._idx - 1) % self._total
        self._update_card()

    def _next(self):
        self._idx = (self._idx + 1) % self._total
        self._update_card()

    def _pause_auto(self):
        """Pause auto-slide for 8s then resume."""
        self._auto_timer.stop()
        QTimer.singleShot(8000, lambda: self._auto_timer.start(3000))

    def _use(self):
        if self._history:
            self.selected = self._history[self._idx]["password"]
            self._auto_timer.stop()
            self.accept()

    def _copy(self):
        if self._history:
            QApplication.clipboard().setText(self._history[self._idx]["password"])
            old = self._copy_btn.text()
            self._copy_btn.setText("Copied ✓")
            QTimer.singleShot(1500, lambda: self._copy_btn.setText(old))

    def closeEvent(self, e):
        self._auto_timer.stop(); super().closeEvent(e)