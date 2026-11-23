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


USER_BUBBLE = (43, 82, 140)
BOT_BUBBLE = (37, 51, 89)


def bubble(draw, img, text, y, *, outgoing, icon=None):
    """Chat xabari: outgoing — o'ngda (foydalanuvchi), aks holda chapda (bot)."""
    text_font = font('Regular', 28)
    width = draw.textlength(text, font=text_font) + 48 + (44 if icon else 0)
    x0 = 1200 - width if outgoing else 700
    draw.rounded_rectangle(
        (x0, y, x0 + width, y + 60), radius=20, fill=USER_BUBBLE if outgoing else BOT_BUBBLE
    )
    left = x0 + 24
    if icon:
        emoji(img, icon, (round(left), y + 15), 30)
        left += 44
    draw.text((left, y + 30), text, font=text_font, fill=WHITE, anchor='lm')


def main() -> None:
    img = gradient()
    draw = ImageDraw.Draw(img)

    # chap tomon: faqat nom va g'oya. Imkoniyatlar ro'yxati bot tavsifida bor — takrorlanmaydi
    draw.text((80, 230), 'Eslatuvchi', font=font('Bold', 68), fill=WHITE)
    draw.text((80, 306), 'vazifalar boti', font=font('Bold', 68), fill=ACCENT)
    draw.text((80, 420), 'Bir marta yozasiz —', font=font('Regular', 32), fill=MUTED)
    draw.text((80, 462), 'qolganini bot eslab qoladi', font=font('Regular', 32), fill=MUTED)

    # o'ng tomon: qanday ishlashi — chat namunasi
    bubble(draw, img, 'Hisobot topshirish', 70, outgoing=True)
    bubble(draw, img, 'Muddat qachon?', 148, outgoing=False, icon='📅')
    bubble(draw, img, 'ertaga 15:00', 226, outgoing=True)

    note_font = font('Regular', 22)
    note = 'ertasi kuni, 15:00'
    draw.text((950, 333), note, font=note_font, fill=MUTED, anchor='mm')
    note_w = draw.textlength(note, font=note_font)
    for x_start, x_end in ((700, 950 - note_w / 2 - 16), (950 + note_w / 2 + 16, 1200)):
        draw.line((x_start, 333, x_end, 333), fill=CARD_LINE, width=2)

    x0, y0, x1 = 700, 370, 1200
    draw.rounded_rectangle((x0, y0, x1, 650), radius=24, fill=CARD, outline=CARD_LINE, width=2)
    emoji(img, '⏰', (x0 + 28, y0 + 26), 36)
    draw.text((x0 + 76, y0 + 24), 'Eslatma', font=font('Bold', 30), fill=WHITE)
    draw.text((x0 + 28, y0 + 82), 'Hisobot topshirish', font=font('Regular', 28), fill=WHITE)
    draw.text((x0 + 28, y0 + 126), 'Muddat: bugun 15:00', font=font('Regular', 24), fill=MUTED)

    buttons = [((x0 + 20, y0 + 178, x1 - 20, y0 + 222), '✅', 'Bajarildi')]
    third = (x1 - x0 - 40 - 20) // 3
    for i, label in enumerate(['+15 daq', '+1 soat', 'Ertaga']):
        left = x0 + 20 + i * (third + 10)
        buttons.append(((left, y0 + 232, left + third, y0 + 268), '⏰', label))
    for box, icon, label in buttons:
        draw.rounded_rectangle(box, radius=12, fill=BUTTON)
        big = box[3] - box[1] > 40
        size = 24 if big else 19
        icon_size = 24 if big else 18
        label_font = font('SemiBold', size)
        gap = icon_size + 8
        text_w = draw.textlength(label, font=label_font) + gap
        left = box[0] + (box[2] - box[0] - text_w) / 2
        mid = (box[1] + box[3]) / 2
        emoji(img, icon, (round(left), round(mid - icon_size / 2)), icon_size)
        draw.text((left + gap, mid), label, font=label_font, fill=WHITE, anchor='lm')

    OUT.parent.mkdir(exist_ok=True)
    img.convert('RGB').save(OUT, optimize=True)
    print(f'Saqlandi: {OUT} ({W}x{H})')


if __name__ == '__main__':
    main()
