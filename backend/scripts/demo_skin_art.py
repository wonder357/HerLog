"""合成皮肤近照：给展示数据造一批可解码、可过 quality 校验的 JPEG。

纯 Pillow 实现，不引入额外依赖；同一 seed 输出同一张图。
产出的是“柔焦皮肤特写”风格的纹理合成图，不是真人照片，只用于演示皮肤观察流程。
"""

from __future__ import annotations

import io
import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

SIZE = (960, 1200)
QUALITY_MIN_CONTRAST = 19.0
QUALITY_BRIGHTNESS = (60.0, 225.0)


@dataclass(frozen=True)
class SkinLook:
    """一个部位的外观参数。"""

    tone: tuple[int, int, int]
    pores: float
    blemishes: int
    redness: float
    shine: float
    creases: int = 2
    fold: bool = False


LOOKS: dict[str, SkinLook] = {
    "脸颊": SkinLook(tone=(229, 184, 170), pores=1.0, blemishes=3, redness=0.45, shine=0.30, creases=2),
    "额头": SkinLook(tone=(227, 182, 168), pores=0.8, blemishes=3, redness=0.28, shine=0.60, creases=1),
    "下巴": SkinLook(tone=(227, 180, 166), pores=1.3, blemishes=5, redness=0.52, shine=0.22, creases=2),
    "颈部": SkinLook(tone=(224, 180, 168), pores=0.55, blemishes=1, redness=0.18, shine=0.18, creases=1, fold=True),
    "面部": SkinLook(tone=(230, 186, 172), pores=1.05, blemishes=3, redness=0.42, shine=0.40, creases=3),
    "背部": SkinLook(tone=(222, 174, 160), pores=0.9, blemishes=6, redness=0.46, shine=0.12, creases=2),
}


def _noise_image(rng: random.Random, cells: int) -> Image.Image:
    small = Image.new("L", (max(2, cells), max(2, cells)))
    small.putdata([rng.randint(0, 255) for _ in range(small.width * small.height)])
    return small


def _smooth_field(rng: random.Random, size: tuple[int, int], cells: int, blur: float) -> Image.Image:
    """低频场：小尺寸随机噪声放大后模糊，用来做光照、血运和油光。"""

    return _noise_image(rng, cells).resize(size, Image.Resampling.BICUBIC).filter(
        ImageFilter.GaussianBlur(blur)
    )


def _tinted(tone: tuple[int, int, int], light: Image.Image, warmth: Image.Image) -> Image.Image:
    """以肤色为基准，用光照场和色温场轻微调制三通道。"""

    channels = []
    for index, base in enumerate(tone):
        gain = (1.04, 1.0, 0.97)[index]
        mapped = light.point(
            lambda value, b=base, k=gain: max(0, min(255, int(b * (0.93 + value / 255 * 0.13) * k)))
        )
        mix = warmth.point(lambda value, b=base: max(0, min(255, int(b + (value - 128) * 0.06))))
        channels.append(Image.blend(mapped, mix, 0.3))
    return Image.merge("RGB", channels)


def _top_light(image: Image.Image) -> Image.Image:
    """上方主光：上亮下暗，接近日常室内自然光。"""

    gradient = Image.linear_gradient("L").resize(image.size).point(lambda v: int(214 + v * 0.15))
    return ImageChops.multiply(image, Image.merge("RGB", (gradient, gradient, gradient)))


def _pores(image: Image.Image, rng: random.Random, density: float) -> Image.Image:
    """毛孔：大量 1~2px 的浅影，柔焦后是一层细颗粒而不是噪点。"""

    layer = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(layer)
    for _ in range(int(1800 * density)):
        x = rng.randrange(image.width)
        y = rng.randrange(image.height)
        radius = rng.choice((1, 1, 2))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=rng.randint(105, 175))
    layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    shade = Image.new("RGB", image.size, (150, 112, 100))
    return Image.composite(shade, image, layer.point(lambda v: int(v * 0.24)))


def _creases(image: Image.Image, rng: random.Random, count: int) -> Image.Image:
    if count <= 0:
        return image
    lines = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(lines)
    for _ in range(count):
        x = rng.randint(-80, image.width // 4)
        y = rng.randint(int(image.height * 0.15), int(image.height * 0.9))
        length = rng.randint(image.width // 3, image.width)
        points = [(x, y)]
        for step in range(1, 9):
            points.append((x + length * step // 8, y + rng.randint(-22, 22)))
        draw.line(points, fill=rng.randint(80, 130), width=rng.choice((2, 3)))
    lines = lines.filter(ImageFilter.GaussianBlur(3.2))
    shade = Image.new("RGB", image.size, (172, 132, 120))
    return Image.composite(shade, image, lines.point(lambda v: int(v * 0.30)))


def _blemishes(image: Image.Image, rng: random.Random, count: int, redness: float) -> Image.Image:
    """零星的红点/痘印：软边红晕 + 略深的核心。"""

    spots = Image.new("L", image.size, 0)
    cores = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(spots)
    core = ImageDraw.Draw(cores)
    for _ in range(count):
        x = rng.randint(int(image.width * 0.12), int(image.width * 0.88))
        y = rng.randint(int(image.height * 0.1), int(image.height * 0.9))
        radius = rng.randint(8, 22)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=rng.randint(130, 195))
        inner = max(2, radius // 3)
        core.ellipse((x - inner, y - inner, x + inner, y + inner), fill=rng.randint(150, 225))
    spots = spots.filter(ImageFilter.GaussianBlur(4))
    cores = cores.filter(ImageFilter.GaussianBlur(1.4))
    red = Image.new("RGB", image.size, (198, 126, 116))
    dark = Image.new("RGB", image.size, (162, 96, 90))
    result = Image.composite(red, image, spots.point(lambda v: int(v * (0.38 + redness * 0.32))))
    return Image.composite(dark, result, cores.point(lambda v: int(v * 0.42)))


def _blush(image: Image.Image, rng: random.Random, strength: float) -> Image.Image:
    """面颊血运：大面积淡淡的粉红。"""

    if strength <= 0:
        return image
    patch = _smooth_field(rng, image.size, 4, 60)
    return Image.composite(
        Image.new("RGB", image.size, (214, 150, 140)), image, patch.point(lambda v: int(max(0, v - 122) * strength))
    )


def _shine(image: Image.Image, rng: random.Random, strength: float) -> Image.Image:
    """油光：局部高光带。"""

    if strength <= 0:
        return image
    glare = _smooth_field(rng, image.size, 6, 60).point(lambda v: int(max(0, v - 198) * strength * 2.0))
    return Image.composite(Image.new("RGB", image.size, (255, 248, 242)), image, glare)


def _fold(image: Image.Image, rng: random.Random) -> Image.Image:
    """颈部皮纹：一条横向浅折痕。"""

    line = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(line)
    y0 = int(image.height * 0.66)
    points = [(0, y0)]
    for step in range(1, 13):
        x = int(image.width * step / 12)
        points.append((x, y0 + int(math.sin(step * 0.7 + rng.random()) * 14) + rng.randint(-3, 3)))
    draw.line(points, fill=110, width=6)
    line = line.filter(ImageFilter.GaussianBlur(5))
    shade = Image.new("RGB", image.size, (170, 132, 120))
    return Image.composite(shade, image, line.point(lambda v: int(v * 0.42)))


def _edge_depth(image: Image.Image) -> Image.Image:
    """浅景深：画面边缘轻微虚化。"""

    mask = Image.new("L", (64, 80), 0)
    ImageDraw.Draw(mask).ellipse((-10, -10, 74, 90), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(10)).resize(image.size, Image.Resampling.BICUBIC)
    return Image.composite(image, image.filter(ImageFilter.GaussianBlur(3.2)), mask)


def measure(image: Image.Image) -> tuple[float, float]:
    """与 image_validation.inspect_image 同口径的亮度/对比度。"""

    values = list(image.convert("L").resize((64, 64)).tobytes())
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, variance**0.5


def _tune(image: Image.Image) -> Image.Image:
    """把亮度和对比度推进 quality=good 的区间，避免历史页显示“画面偏暗/对比度较低”。"""

    for _ in range(8):
        mean, contrast = measure(image)
        if contrast < QUALITY_MIN_CONTRAST:
            image = ImageEnhance.Contrast(image).enhance(1.10)
            continue
        if mean < QUALITY_BRIGHTNESS[0]:
            image = ImageEnhance.Brightness(image).enhance(1.08)
            continue
        if mean > QUALITY_BRIGHTNESS[1]:
            image = ImageEnhance.Brightness(image).enhance(0.94)
            continue
        break
    return image


def build_skin_photo(
    site: str,
    seed: int,
    *,
    size: tuple[int, int] = SIZE,
    severity: str = "mild",
    tone_shift: tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """severity: mild 平稳 / flare 泛红爆痘；tone_shift 用来区分不同账号的肤色。"""

    rng = random.Random(seed * 977 + sum(map(ord, site)))
    look = LOOKS.get(site, LOOKS["面部"])
    tone = tuple(max(0, min(255, base + shift)) for base, shift in zip(look.tone, tone_shift))
    bump = 1.0 if severity == "mild" else 1.8
    light = _smooth_field(rng, size, 6, 34)
    warmth = _smooth_field(rng, size, 4, 45)
    image = _tinted(tone, light, warmth)
    image = _top_light(image)
    image = _pores(image, rng, look.pores)
    grain = Image.effect_noise(size, 6).filter(ImageFilter.GaussianBlur(1.6)).convert("RGB")
    image = Image.blend(image, ImageChops.overlay(image, grain), 0.07)
    image = _blush(image, rng, look.redness * 0.5 * bump)
    image = _creases(image, rng, look.creases)
    image = _blemishes(image, rng, int(round(look.blemishes * bump)), look.redness)
    image = _shine(image, rng, look.shine)
    if look.fold:
        image = _fold(image, rng)
    image = _edge_depth(image)
    image = ImageEnhance.Color(image).enhance(0.85)
    image = ImageEnhance.Contrast(image).enhance(1.04)
    return _tune(image)


def photo_bytes(
    site: str, seed: int, *, severity: str = "mild", tone_shift: tuple[int, int, int] = (0, 0, 0)
) -> bytes:
    buffer = io.BytesIO()
    build_skin_photo(site, seed, severity=severity, tone_shift=tone_shift).save(
        buffer, format="JPEG", quality=90, optimize=True
    )
    return buffer.getvalue()


def write_demo_photos(out_dir: Path, plan: list[dict]) -> list[dict]:
    """plan 每项：{site, seed, severity?, tone_shift?, name?}；同时落盘便于肉眼检查。"""

    out_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict] = []
    for item in plan:
        data = photo_bytes(
            item["site"],
            item["seed"],
            severity=item.get("severity", "mild"),
            tone_shift=item.get("tone_shift", (0, 0, 0)),
        )
        name = item.get("name") or f"{item['site']}-{item['seed']}"
        (out_dir / f"{name}.jpg").write_bytes(data)
        shots.append({**item, "name": name, "image": data})
    return shots


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "demo_assets" / "skin"
    write_demo_photos(target, [{"site": site, "seed": 1} for site in LOOKS])
    print(f"written to {target}")
