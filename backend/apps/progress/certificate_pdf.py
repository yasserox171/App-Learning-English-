"""Dependency-free certificate PDF renderer (UX prompt 1.2).

The certificate endpoint must work on the Termux deployment, where reportlab
is deliberately not installed (see requirements-termux.txt). This module
builds the PDF file by hand — one landscape A4 page using only the standard
Type-1 fonts every PDF viewer ships with — so certificate downloads work on
every install with zero extra dependencies.

Design: full-page gradient tinted by CEFR level, white parchment card with a
double gold border and corner accents, serif display type, an embossed-style
seal with ribbons, and date / signature rules in the footer.
"""

from __future__ import annotations

import zlib
from typing import Iterable

# --- Page geometry (landscape A4, points) ---------------------------------- #
W, H = 842.0, 595.0

# --- Palette ---------------------------------------------------------------- #
_INK = (0.13, 0.17, 0.23)  # near-black slate for display text
_MUTED = (0.42, 0.45, 0.50)  # secondary text
_GOLD = (0.76, 0.60, 0.24)  # border / seal metalwork
_GOLD_DARK = (0.58, 0.44, 0.15)
_PAPER = (1.0, 0.998, 0.99)  # warm white card

# Per-level gradient (start, end) + accent used for the level line and seal.
_LEVEL_THEMES = {
    "A1": ((0.86, 0.97, 0.90), (0.18, 0.71, 0.49), (0.09, 0.55, 0.36)),
    "A2": ((0.85, 0.96, 0.96), (0.11, 0.62, 0.64), (0.05, 0.47, 0.49)),
    "B1": ((0.85, 0.95, 0.99), (0.00, 0.64, 0.85), (0.00, 0.47, 0.66)),
    "B2": ((0.87, 0.91, 0.99), (0.24, 0.42, 0.83), (0.16, 0.30, 0.65)),
    "C1": ((0.92, 0.89, 0.99), (0.47, 0.32, 0.83), (0.34, 0.21, 0.65)),
    "C2": ((0.99, 0.94, 0.83), (0.79, 0.58, 0.16), (0.60, 0.42, 0.08)),
}
_DEFAULT_THEME = _LEVEL_THEMES["B1"]

# --- Standard-14 font metrics (widths per 1000 em, chars 32..126) ----------- #
# fmt: off
_HELVETICA_W = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_HELVETICA_BOLD_W = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]
_TIMES_BOLD_W = [250, 333, 555, 500, 500, 1000, 833, 278, 333, 333, 500, 570, 250, 333, 250, 278, 500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 333, 333, 570, 570, 570, 500, 930, 722, 667, 722, 722, 667, 611, 778, 778, 389, 500, 778, 667, 944, 722, 778, 611, 778, 722, 556, 667, 722, 722, 1000, 722, 722, 667, 333, 278, 333, 581, 500, 333, 500, 556, 444, 556, 444, 333, 500, 556, 278, 333, 556, 278, 833, 556, 500, 556, 556, 444, 389, 333, 556, 500, 722, 500, 500, 444, 394, 220, 394, 520]
_TIMES_ITALIC_W = [250, 333, 420, 500, 500, 833, 778, 214, 333, 333, 500, 675, 250, 333, 250, 278, 500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 333, 333, 675, 675, 675, 500, 920, 611, 611, 667, 722, 611, 611, 722, 722, 333, 444, 667, 556, 833, 667, 722, 611, 722, 611, 500, 556, 722, 611, 833, 611, 556, 556, 389, 278, 389, 422, 500, 333, 500, 500, 444, 500, 444, 278, 500, 500, 278, 278, 444, 278, 722, 500, 500, 500, 500, 389, 389, 278, 500, 444, 667, 444, 444, 389, 400, 275, 400, 541]
# fmt: on

_FONTS = {
    # resource name -> (base font, width table)
    "F1": ("Helvetica", _HELVETICA_W),
    "F2": ("Helvetica-Bold", _HELVETICA_BOLD_W),
    "F3": ("Times-Bold", _TIMES_BOLD_W),
    "F4": ("Times-Italic", _TIMES_ITALIC_W),
}


def _text_width(text: str, font: str, size: float, spacing: float = 0.0) -> float:
    widths = _FONTS[font][1]
    units = sum(widths[ord(c) - 32] if 32 <= ord(c) < 127 else 600 for c in text)
    return units * size / 1000.0 + spacing * max(len(text) - 1, 0)


def _esc(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


# --- Low-level content-stream helpers --------------------------------------- #
def _rgb(color, stroke=False) -> str:
    op = "RG" if stroke else "rg"
    return "%.3f %.3f %.3f %s" % (*color, op)


def _text(
    x: float,
    y: float,
    text: str,
    font: str = "F1",
    size: float = 12.0,
    color=_INK,
    spacing: float = 0.0,
    center: bool = False,
) -> str:
    if center:
        x -= _text_width(text, font, size, spacing) / 2
    parts = ["BT", _rgb(color), f"/{font} {size:.1f} Tf"]
    if spacing:
        parts.append(f"{spacing:.2f} Tc")
    parts.append(f"{x:.1f} {y:.1f} Td ({_esc(text)}) Tj")
    if spacing:
        parts.append("0 Tc")
    parts.append("ET")
    return " ".join(parts)


def _line(x1, y1, x2, y2, color=_GOLD, width=1.0) -> str:
    return (
        f"{_rgb(color, stroke=True)} {width:.2f} w "
        f"{x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S"
    )


def _rect(x, y, w, h, color=_GOLD, width=1.0, fill=False) -> str:
    if fill:
        return f"{_rgb(color)} {x:.1f} {y:.1f} {w:.1f} {h:.1f} re f"
    return (
        f"{_rgb(color, stroke=True)} {width:.2f} w "
        f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re S"
    )


def _circle(cx, cy, r, color=_GOLD, width=1.5, fill=False) -> str:
    """Circle from four Bézier arcs (k = 0.5523)."""
    k = 0.5523 * r
    path = (
        f"{cx + r:.1f} {cy:.1f} m "
        f"{cx + r:.1f} {cy + k:.1f} {cx + k:.1f} {cy + r:.1f} {cx:.1f} {cy + r:.1f} c "
        f"{cx - k:.1f} {cy + r:.1f} {cx - r:.1f} {cy + k:.1f} {cx - r:.1f} {cy:.1f} c "
        f"{cx - r:.1f} {cy - k:.1f} {cx - k:.1f} {cy - r:.1f} {cx:.1f} {cy - r:.1f} c "
        f"{cx + k:.1f} {cy - r:.1f} {cx + r:.1f} {cy - k:.1f} {cx + r:.1f} {cy:.1f} c "
    )
    if fill:
        return f"{_rgb(color)} {path} f"
    return f"{_rgb(color, stroke=True)} {width:.2f} w {path} S"


def _polygon(points: Iterable[tuple], color) -> str:
    pts = list(points)
    path = f"{pts[0][0]:.1f} {pts[0][1]:.1f} m " + " ".join(
        f"{x:.1f} {y:.1f} l" for x, y in pts[1:]
    )
    return f"{_rgb(color)} {path} f"


def _corner(x, y, dx, dy, color) -> str:
    """L-shaped corner accent; (dx, dy) point inward."""
    arm, thick = 26.0, 3.0
    return (
        _rect(min(x, x + dx * arm), min(y, y + dy * thick),
              arm, thick, color=color, fill=True)
        + " "
        + _rect(min(x, x + dx * thick), min(y, y + dy * arm),
                thick, arm, color=color, fill=True)
    )


def _seal(cx: float, cy: float, code: str, accent) -> str:
    ribbon_l = [(cx - 16, cy - 34), (cx - 30, cy - 74), (cx - 8, cy - 60), (cx - 2, cy - 40)]
    ribbon_r = [(cx + 16, cy - 34), (cx + 30, cy - 74), (cx + 8, cy - 60), (cx + 2, cy - 40)]
    return " ".join(
        [
            _polygon(ribbon_l, _GOLD_DARK),
            _polygon(ribbon_r, _GOLD_DARK),
            _circle(cx, cy, 46, color=_GOLD, width=2.5),
            _circle(cx, cy, 40, color=_GOLD, width=1.0),
            _circle(cx, cy, 34, color=accent, fill=True),
            _text(cx, cy - 6, code, font="F2", size=24, color=(1, 1, 1), center=True),
            _text(cx, cy - 20, "CEFR", font="F1", size=7, color=(1, 1, 1),
                  spacing=1.5, center=True),
            _text(cx, cy + 52, "* OFFICIAL SEAL *", font="F1", size=6,
                  color=_GOLD_DARK, spacing=1.2, center=True),
        ]
    )


def _display_name(certificate) -> str:
    """Best printable name: the standard PDF fonts only cover Latin-1, so a
    fully non-Latin name (e.g. Arabic script) falls back to the email handle."""
    name = (certificate.user.full_name or "").strip()
    try:
        name.encode("latin-1")
    except UnicodeEncodeError:
        name = ""
    if not name:
        name = certificate.user.email.split("@")[0]
    return name[:48]


def _content_stream(certificate) -> bytes:
    level = certificate.level
    code = (level.code or "").upper()
    theme = _LEVEL_THEMES.get(code, _DEFAULT_THEME)
    _grad_start, _grad_end, accent = theme
    name = _display_name(certificate)
    cx = W / 2

    ops = [
        # Gradient background (axial shading defined in page resources).
        "q /Sh1 sh Q",
        # Parchment card + double gold frame.
        _rect(30, 30, W - 60, H - 60, color=_PAPER, fill=True),
        _rect(40, 40, W - 80, H - 80, color=_GOLD, width=2.6),
        _rect(47, 47, W - 94, H - 94, color=_GOLD, width=0.8),
        # Corner accents in the level color.
        _corner(56, 56, +1, +1, accent),
        _corner(W - 56, 56, -1, +1, accent),
        _corner(56, H - 56, +1, -1, accent),
        _corner(W - 56, H - 56, -1, -1, accent),
        # Header: school branding.
        _text(cx, H - 78, "FOCUS LANGUAGES", font="F2", size=13,
              color=accent, spacing=4.0, center=True),
        _text(cx, H - 94, "ENGLISH MASTER ACADEMY", font="F1", size=8,
              color=_MUTED, spacing=3.0, center=True),
        _line(cx - 70, H - 104, cx + 70, H - 104, color=_GOLD, width=1.0),
        # Title.
        _text(cx, H - 158, "CERTIFICATE", font="F3", size=46,
              color=_INK, spacing=6.0, center=True),
        _text(cx, H - 182, "OF ACHIEVEMENT", font="F1", size=13,
              color=_GOLD_DARK, spacing=6.0, center=True),
        # Recipient.
        _text(cx, H - 226, "This is to certify that", font="F4", size=15,
              color=_MUTED, center=True),
        _text(cx, H - 266, name, font="F3", size=32, color=_INK, center=True),
        _line(cx - 170, H - 278, cx + 170, H - 278, color=_GOLD, width=1.0),
        # Achievement.
        _text(cx, H - 306, "has successfully completed all requirements of the English course",
              font="F4", size=14, color=_MUTED, center=True),
        _text(cx, H - 340, f"LEVEL {code} - {level.name.upper()}",
              font="F2", size=22, color=accent, spacing=1.5, center=True),
        _text(cx, H - 360, "Common European Framework of Reference for Languages (CEFR)",
              font="F1", size=10, color=_MUTED, center=True),
        # Seal.
        _seal(cx, 152, code, accent),
        # Footer: date (left) and signature (right) over rules.
        _text(190, 132, f"{certificate.issued_at:%B %d, %Y}", font="F1",
              size=12, color=_INK, center=True),
        _line(110, 122, 270, 122, color=_GOLD_DARK, width=1.0),
        _text(190, 106, "DATE", font="F1", size=8, color=_MUTED,
              spacing=2.5, center=True),
        _text(W - 190, 130, "Focus Languages", font="F4", size=19,
              color=_INK, center=True),
        _line(W - 270, 122, W - 110, 122, color=_GOLD_DARK, width=1.0),
        _text(W - 190, 106, "DIRECTOR", font="F1", size=8, color=_MUTED,
              spacing=2.5, center=True),
        # Certificate number.
        _text(cx, 66, f"Certificate No. {certificate.certificate_number}",
              font="F1", size=9, color=_MUTED, spacing=0.5, center=True),
    ]
    return "\n".join(ops).encode("latin-1")


def generate_certificate_pdf(certificate) -> bytes:
    """Build the complete single-page PDF and return its bytes."""
    code = (certificate.level.code or "").upper()
    grad_start, grad_end, _accent = _LEVEL_THEMES.get(code, _DEFAULT_THEME)

    content = _content_stream(certificate)
    compressed = zlib.compress(content)

    shading = (
        "<< /ShadingType 2 /ColorSpace /DeviceRGB "
        f"/Coords [0 {H:.0f} {W:.0f} 0] /Extend [true true] "
        "/Function << /FunctionType 2 /Domain [0 1] "
        f"/C0 [{grad_start[0]:.3f} {grad_start[1]:.3f} {grad_start[2]:.3f}] "
        f"/C1 [{grad_end[0]:.3f} {grad_end[1]:.3f} {grad_end[2]:.3f}] /N 1 >> >>"
    )
    font_res = " ".join(f"/{k} {5 + i} 0 R" for i, k in enumerate(_FONTS))

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W:.0f} {H:.0f}] "
            f"/Resources << /Font << {font_res} >> /Shading << /Sh1 {shading} >> >> "
            "/Contents 4 0 R >>"
        ).encode(),
        (
            f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode()
            + compressed
            + b"\nendstream"
        ),
    ] + [
        (
            f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} "
            "/Encoding /WinAnsiEncoding >>"
        ).encode()
        for base, _w in _FONTS.values()
    ]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)
