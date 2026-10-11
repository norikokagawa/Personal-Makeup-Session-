"""
投稿画像の検証とストーリーズ画像の生成

フィード: Canva 正式エクスポート (PNG, pro, 1080x1350) を1・2ページそのまま使う (2枚カルーセル)。
ストーリーズ: 各ページを切り抜かず、1080x1920 のキャンバス中央に等倍で配置する。
余白はデザイン背景色 (#f6f4f1) で塗る。
"""
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
