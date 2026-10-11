"""
投稿画像の検証とストーリーズ画像の生成

フィード: Canva 正式エクスポート (PNG, pro, 1080x1350) をそのまま使う。
ストーリーズ: フィード画像を切り抜かず、1080x1920 のキャンバス中央に等倍で配置する。
余白はデザイン背景色 (#f6f4f1) で塗る。
"""
from PIL import Image

FEED_SIZE = (1080, 1350)
STORY_SIZE = (1080, 1920)
DESIGN_BG = (0xF6, 0xF4, 0xF1)


def verify_feed(path):
    """Raise if the image is not a full-size export (e.g. a Canva thumbnail)."""
    with Image.open(path) as im:
        if im.size != FEED_SIZE:
            raise ValueError(f"feed image is {im.size}, expected {FEED_SIZE}")
        if im.format != "PNG":
            raise ValueError(f"feed image is {im.format}, expected PNG")
        extrema = im.convert("L").getextrema()
        if extrema[0] == extrema[1]:
            raise ValueError("feed image is a single flat colour")
    return True


def make_story(feed_path, story_path, bg=DESIGN_BG):
    with Image.open(feed_path) as feed:
        feed = feed.convert("RGB")
        if feed.size != FEED_SIZE:
            raise ValueError(f"feed image is {feed.size}, expected {FEED_SIZE}")
        story = Image.new("RGB", STORY_SIZE, bg)
        top = (STORY_SIZE[1] - FEED_SIZE[1]) // 2
        story.paste(feed, (0, top))
        story.save(story_path, "PNG", optimize=False)
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
