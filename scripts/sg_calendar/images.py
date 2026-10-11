"""
投稿画像の検証とストーリーズ画像の生成

フィード: Canva 正式エクスポート (PNG, pro, 1080x1350) を1・2ページそのまま使う (2枚カルーセル)。
ストーリーズ: 各ページを切り抜かず、1080x1920 のキャンバス中央に等倍で配置する。
余白はデザイン背景色 (#f6f4f1) で塗る。
"""
import os

from PIL import Image

FEED_SIZE = (1080, 1350)
STORY_SIZE = (1080, 1920)
DESIGN_BG = (0xF6, 0xF4, 0xF1)
EDGE = 24          # この幅の外周に文字が掛かっていたら「文字欠け」とみなす
TOLERANCE = 12


def _near_bg(px):
    return all(abs(a - b) <= TOLERANCE for a, b in zip(px[:3], DESIGN_BG))


def check_margins(im):
    """Return the fraction of non-background pixels in the outer EDGE band (0 = clean)."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    boxes = [(0, 0, w, EDGE), (0, h - EDGE, w, h), (0, 0, EDGE, h), (w - EDGE, 0, w, h)]
    total = bad = 0
    for box in boxes:
        raw = rgb.crop(box).tobytes()
        for i in range(0, len(raw), 3):
            total += 1
            bad += not _near_bg(raw[i:i + 3])
    return bad / total


def verify_feed(path):
    """Raise if the image is not a full-size export or content touches the edges."""
    with Image.open(path) as im:
        if im.size != FEED_SIZE:
            raise ValueError(f"{path}: {im.size}, expected {FEED_SIZE} (thumbnail?)")
        if im.format != "PNG":
            raise ValueError(f"{path}: {im.format}, expected PNG")
        lo, hi = im.convert("L").getextrema()
        if lo == hi:
            raise ValueError(f"{path}: single flat colour")
        edge = check_margins(im)
        if edge > 0.001:
            raise ValueError(f"{path}: {edge:.2%} of the edge band is not background (cut-off content?)")
    return True


def make_story(feed_path, story_path, bg=DESIGN_BG):
    with Image.open(feed_path) as feed:
        feed = feed.convert("RGB")
        if feed.size != FEED_SIZE:
            raise ValueError(f"feed image is {feed.size}, expected {FEED_SIZE}")
        story = Image.new("RGB", STORY_SIZE, bg)
        story.paste(feed, (0, (STORY_SIZE[1] - FEED_SIZE[1]) // 2))
        story.save(story_path, "PNG")
    verify_story(story_path, feed_path)
    return story_path


def verify_story(story_path, feed_path):
    """Story must be 1080x1920 and contain the feed image pixel-for-pixel (no crop/scale)."""
    with Image.open(story_path) as s, Image.open(feed_path) as f:
        if s.size != STORY_SIZE:
            raise ValueError(f"story image is {s.size}, expected {STORY_SIZE}")
        top = (STORY_SIZE[1] - FEED_SIZE[1]) // 2
        region = s.convert("RGB").crop((0, top, FEED_SIZE[0], top + FEED_SIZE[1]))
        if region.tobytes() != f.convert("RGB").tobytes():
            raise ValueError("story does not contain the full, unscaled feed image")
    return True


# ── JPEG (Instagram の画像投稿は JPEG のみ) ──────────────────────────────────

JPEG_QUALITY = 95
MIN_PSNR = 38.0          # dB。これを下回る劣化は「高画質ではない」とみなす
MAX_BYTES = 8 * 1024 * 1024


def psnr(a, b):
    import math
    a, b = a.convert("RGB"), b.convert("RGB")
    if a.size != b.size:
        return 0.0
    diff = bytes(abs(x - y) for x, y in zip(a.tobytes(), b.tobytes()))
    mse = sum(d * d for d in diff) / len(diff)
    return float("inf") if mse == 0 else 10 * math.log10(255 ** 2 / mse)


def to_jpeg(src_path, dst_path):
    """High-quality JPEG (4:4:4, q95) and proof that it still matches the source."""
    with Image.open(src_path) as im:
        rgb = im.convert("RGB")
        rgb.save(dst_path, "JPEG", quality=JPEG_QUALITY, subsampling=0, optimize=True)
    with Image.open(dst_path) as out, Image.open(src_path) as src:
        if out.format != "JPEG" or out.size != src.size:
            raise ValueError(f"{dst_path}: bad JPEG ({out.format} {out.size})")
        score = psnr(src, out)
    if score < MIN_PSNR:
        raise ValueError(f"{dst_path}: JPEG quality too low (PSNR {score:.1f} dB)")
    size = os.path.getsize(dst_path)
    if size > MAX_BYTES:
        raise ValueError(f"{dst_path}: {size} bytes exceeds Instagram's 8 MB limit")
    return round(score, 1)


def assert_pages_differ(a_path, b_path):
    """Guard against exporting the same page twice."""
    with Image.open(a_path) as a, Image.open(b_path) as b:
        if a.convert("RGB").tobytes() == b.convert("RGB").tobytes():
            raise ValueError("page 1 and page 2 exports are identical")
