"""剪映草稿生成——广告语彩色大字卡 + 滤镜 + 转场"""

import os, random, re
from pathlib import Path

FURNITURE_FILTERS = [
    "原木", "原木自然", "清透", "自然", "自然II",
    "暖调", "暖色", "胶片", "日系", "森山",
]


def create_capcut_draft(
    draft_name: str,
    script_text: str,
    audio_path: str,
    image_paths: list[str],
    output_dir: str | None = None,
    brand: str = "圣栎美家",
):
    """生成剪映草稿：广告语彩色大字卡 + 半透明黑底 + 滤镜 + 叠化转场"""

    from pyJianYingDraft import (
        DraftFolder, trange, TrackType, VideoSegment,
        TextSegment, FilterType, TransitionType, TextStyle,
        AudioSegment, TextBackground,
    )

    if output_dir is None:
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
        output_dir = os.path.join(appdata, "JianyingPro", "User Data", "Projects", "com.lveditor.draft")

    folder = DraftFolder(output_dir)
    sc = folder.create_draft(draft_name, 720, 1280, 25, allow_replace=True)

    sc.add_track(TrackType.video)
    sc.add_track(TrackType.audio)
    sc.add_track(TrackType.text)

    from app.utils.ffmpeg_utils import get_media_duration
    total_dur = get_media_duration(Path(audio_path)) - 0.1
    td = max(total_dur - 0.1, 1.0)
    img_count = max(len(image_paths), 1)
    per_img = min(td / img_count, 8.0)

    # 1. 图片 + 滤镜 + 转场
    for i, img_path in enumerate(image_paths[:8]):
        start = i * per_img
        end = min(start + per_img, td) - 0.02
        if end <= start: break
        seg = VideoSegment(img_path.replace("\\", "/"), trange(f"{start:.2f}s", f"{end:.2f}s"))
        sc.add_segment(seg)
        try:
            seg.add_filter(getattr(FilterType, random.choice(FURNITURE_FILTERS)))
        except Exception:
            pass

    video_track = sc.tracks.get("video")
    if video_track and len(video_track.segments) > 1:
        try:
            for i in range(len(video_track.segments) - 1):
                video_track.segments[i].add_transition(TransitionType.叠化)
        except Exception:
            pass

    # 2. 音频
    sc.add_segment(AudioSegment(audio_path.replace("\\", "/"), trange("0s", f"{td:.2f}s")))

    # 3. 广告语卡片（每条单独timeline，不重叠）
    cards = _ad_cards(script_text)
    if cards:
        gap = 0.3  # 卡片间距
        per_card = (td - gap * (len(cards) - 1)) / len(cards)
        for i, card in enumerate(cards):
            start = i * (per_card + gap)
            end = min(start + per_card, td - 0.05)
            if end <= start: continue

            # 根据文字长度智能调整字号（720px宽竖屏，中文约16px/pt）
            text_len = len(card["text"])
            if text_len <= 8:
                font_size = min(card.get("size", 40), 44)
            elif text_len <= 16:
                font_size = min(card.get("size", 40), 36)
            elif text_len <= 24:
                font_size = min(card.get("size", 40), 28)
            else:
                font_size = min(card.get("size", 40), 24)

            txt = TextSegment(card["text"], trange(f"{start:.2f}s", f"{end:.2f}s"))
            txt.style = TextStyle(size=font_size, bold=card.get("bold", False),
                                  color=card.get("color", (1.0, 1.0, 1.0)),
                                  auto_wrapping=True, max_line_width=0.85, align=1)
            txt.pos_x = 0.5; txt.pos_y = 0.45
            if card.get("bg"):
                txt.background = TextBackground(color="#000000", alpha=0.55, height=0.10, round_radius=0.05)
            try:
                sc.add_segment(txt)
            except Exception:
                pass

    sc.dump(sc.save_path)
    return sc.save_path


def _ad_cards(text: str) -> list[dict]:
    """把文案转成3-5条广告语大字卡"""
    raw = [s.strip() for s in re.split(r"[。！？\n]", text) if s.strip() and len(s.strip()) > 3]
    cards = []
    for s in raw:
        s = s.replace("，", " ").replace("、", " ").strip()
        has_price = bool(re.search(r"\d+元|\d+每平|仅需|出厂价|报价", s))
        is_cta = any(w in s for w in ["留言", "咨询", "索取", "私信", "评论"])
        if has_price:
            cards.append({"text": s, "size": 48, "bold": True, "color": (1.0, 0.75, 0.0), "y": 0.40, "bg": True})
        elif is_cta:
            cards.append({"text": s, "size": 38, "bold": True, "color": (1.0, 0.5, 0.2), "y": 0.52})
        else:
            cards.append({"text": s, "size": 38, "color": (1.0, 1.0, 1.0)})
    if not cards:
        return [{"text": text[:30], "size": 40, "color": (1.0, 1.0, 1.0)}]
    if len(cards) > 5:
        cards = [cards[0]] + cards[-4:]  # 钩子 + 最后4条
    return cards
