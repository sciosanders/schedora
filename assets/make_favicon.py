"""Genera favicon.png a partir de la geometría de schedora-icono.svg (solo requiere Pillow).

Pillow no lee SVG; este script redibuja el mismo icono. Si cambias el SVG, ajusta aquí.
"""
import os
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
K, OFF, LADO = 4, 7, 416  # supermuestreo, traslación del grupo, tamaño del viewBox


def dibujar(tam: int) -> Image.Image:
    grande = Image.new("RGBA", (LADO * K, LADO * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(grande)

    def rr(x, y, w, h, r, fill):
        d.rounded_rectangle([(x + OFF) * K, (y + OFF) * K, (x + w + OFF) * K - 1, (y + h + OFF) * K - 1], radius=r * K, fill=fill)

    def circ(cx, cy, r, fill):
        d.ellipse([(cx + OFF - r) * K, (cy + OFF - r) * K, (cx + OFF + r) * K, (cy + OFF + r) * K], fill=fill)

    rr(30, 70, 290, 260, 48, "#0D7377")
    rr(58, 132, 234, 170, 22, "#FFFDF8")
    for x in (94, 228):  # clavijas: anillo crema (4.5 px) y cuerpo oscuro
        rr(x - 4.5, 40 - 4.5, 28 + 9, 72 + 9, 14 + 4.5, "#F7F3E9")
        rr(x, 40, 28, 72, 14, "#264653")
    for x, y, c in [(82, 160, "#14919B"), (152, 160, "#A8D5BA"), (222, 160, "#E9C46A"), (82, 224, "#A8D5BA"), (152, 224, "#14919B")]:
        rr(x, y, 54, 42, 11, c)
    circ(300, 290, 86, "#F7F3E9")
    circ(300, 290, 72, "#264653")
    circ(300, 290, 48, "#FFFDF8")
    pts = [((300 + OFF) * K, (262 + OFF) * K), ((300 + OFF) * K, (290 + OFF) * K), ((320 + OFF) * K, (304 + OFF) * K)]
    d.line(pts, fill="#264653", width=11 * K, joint="curve")
    for x, y in (pts[0], pts[2]):  # puntas redondeadas
        d.ellipse([x - 5.5 * K, y - 5.5 * K, x + 5.5 * K, y + 5.5 * K], fill="#264653")
    circ(300, 290, 7, "#E9C46A")
    return grande.crop((0, 0, (LADO) * K, (LADO) * K)).resize((tam, tam), Image.LANCZOS)


if __name__ == "__main__":
    dibujar(64).save(os.path.join(AQUI, "favicon.png"))
    dibujar(512).save(os.path.join(AQUI, "icono-512.png"))
    print("favicon.png e icono-512.png generados")
