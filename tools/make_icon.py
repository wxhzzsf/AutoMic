"""生成 assets/automic.ico (供 exe 和安装包使用)。运行: python tools/make_icon.py"""

import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "automic.ico")


def draw(size: int) -> Image.Image:
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, s - 8, s - 8), fill=(52, 152, 219, 255))  # 蓝底
    w = (255, 255, 255, 255)
    # 麦克风主体
    d.rounded_rectangle((104, 56, 152, 150), radius=24, fill=w)
    # 麦克风支架(弧)
    d.arc((84, 104, 172, 180), start=0, end=180, fill=w, width=12)
    # 杆
    d.line((128, 180, 128, 204), fill=w, width=12)
    # 底座
    d.line((100, 204, 156, 204), fill=w, width=12)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base = draw(256)
    base.save(OUT, format="ICO",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
