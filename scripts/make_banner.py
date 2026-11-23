"""Bot uchun rasm (assets/welcome.png) yaratadi: /start xabari va @BotFather description rasmi.

Ishga tushirish (Pillow loyiha kutubxonalariga qo'shilmaydi, faqat shu skript uchun):
    uv run --with pillow python scripts/make_banner.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FONTS = Path('/usr/share/fonts/truetype/noto')
OUT = Path(__file__).resolve().parent.parent / 'assets' / 'welcome.png'

BG_TOP, BG_BOTTOM = (17, 24, 39), (30, 41, 82)
WHITE, MUTED, ACCENT = (248, 250, 252), (165, 180, 205), (96, 165, 250)
CARD, CARD_LINE, BUTTON = (37, 51, 89), (59, 77, 125), (51, 70, 120)


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f'NotoSans-{weight}.ttf'), size)


_EMOJI = ImageFont.truetype(str(FONTS / 'NotoColorEmoji.ttf'), 109)  # bitmap shrift: faqat 109


def emoji(canvas: Image.Image, char: str, xy: tuple[int, int], size: int) -> None:
    tile = Image.new('RGBA', (136, 128), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((0, 0), char, font=_EMOJI, embedded_color=True)
    tile = tile.crop(tile.getbbox()).resize((size, size), Image.LANCZOS)
    canvas.alpha_composite(tile, xy)


def gradient() -> Image.Image:
    img = Image.new('RGBA', (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        color = tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM, strict=True))
        draw.line([(0, y), (W, y)], fill=color)
    return img


def main() -> None:
    img = gradient()
    draw = ImageDraw.Draw(img)

    # chap tomon: nom, shior, imkoniyatlar
    draw.text((80, 78), 'Eslatuvchi', font=font('Bold', 64), fill=WHITE)
    draw.text((80, 150), 'vazifalar boti', font=font('Bold', 64), fill=ACCENT)
    draw.text(
        (80, 248), "Yozing — vaqti kelganda o'zim eslataman", font=font('Regular', 30), fill=MUTED
    )

    features = [
        ('⏰', 'Aniq vaqtda eslatma'),
        ('☀️', 'Har kuni ertalab bugungi reja'),
        ('🔁', 'Takrorlanuvchi vazifalar'),
        ('📊', 'Statistika va progress'),
    ]
    for i, (icon, text) in enumerate(features):
        y = 330 + i * 78
        emoji(img, icon, (80, y), 46)
        draw.text((146, y + 2), text, font=font('SemiBold', 32), fill=WHITE)

    draw.text(
        (80, 652),
        "Ilova o'rnatish shart emas — hammasi Telegram'ning o'zida",
        font=font('Regular', 24),
        fill=MUTED,
    )

    # o'ng tomon: eslatma xabari namunasi
    x0, y0, x1, y1 = 790, 190, 1200, 536
    draw.rounded_rectangle((x0, y0, x1, y1), radius=28, fill=CARD, outline=CARD_LINE, width=2)
    emoji(img, '⏰', (x0 + 32, y0 + 32), 40)
    draw.text((x0 + 86, y0 + 32), 'Eslatma', font=font('Bold', 32), fill=WHITE)
    draw.text((x0 + 32, y0 + 100), 'Hisobot topshirish', font=font('Regular', 30), fill=WHITE)
    draw.text((x0 + 32, y0 + 152), 'Muddat: bugun 15:00', font=font('Regular', 26), fill=MUTED)

    buttons = [((x0 + 24, y0 + 220, x1 - 24, y0 + 272), '✅', 'Bajarildi')]
    third = (x1 - x0 - 48 - 20) // 3
    for i, label in enumerate(['+15 daq', '+1 soat', 'Ertaga']):
        left = x0 + 24 + i * (third + 10)
        buttons.append(((left, y0 + 282, left + third, y0 + 322), None, label))
    for box, icon, label in buttons:
        draw.rounded_rectangle(box, radius=12, fill=BUTTON)
        size = 26 if icon else 20
        label_font = font('SemiBold', size)
        text_w = draw.textlength(label, font=label_font) + (36 if icon else 0)
        left = box[0] + (box[2] - box[0] - text_w) / 2
        mid = (box[1] + box[3]) / 2
        if icon:
            emoji(img, icon, (round(left), round(mid - 13)), 26)
            left += 36
        draw.text((left, mid), label, font=label_font, fill=WHITE, anchor='lm')

    OUT.parent.mkdir(exist_ok=True)
    img.convert('RGB').save(OUT, optimize=True)
    print(f'Saqlandi: {OUT} ({W}x{H})')


if __name__ == '__main__':
    main()
