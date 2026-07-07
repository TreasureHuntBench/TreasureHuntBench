"""YouTube artifact generator.

Videos are synthetic: timed text cards (rendered with Pillow) plus matching
WebVTT captions. Every video always gets a **local mirror** under
``<root>/media_mirror/<ref>/`` containing metadata, captions, per-segment
frames, and (optionally) an assembled mp4. The harness, oracle solver, and
evaluator read the mirror; uploading the mp4 as *unlisted* to the
@TreasureHuntBench channel is a separate publish-time step that requires
local OAuth credentials (never committed).

Clue content in videos is structured (``repository=...``, ``document=...``)
— never generic clue language.
"""

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw

from ..artifacts.files import write_json

VIDEO_SIZE = (1280, 720)
BG_COLOR = (16, 24, 38)
FG_COLOR = (222, 230, 240)


@dataclass
class Segment:
    start: int                 # seconds, inclusive
    end: int                   # seconds, exclusive
    lines: List[str]


@dataclass
class VideoSpec:
    ref: str                   # internal reference id, e.g. video_L5S1_7C3
    title: str
    description: str
    segments: List[Segment]
    tags: List[str] = field(default_factory=list)
    privacy: str = "unlisted"

    @property
    def duration(self) -> int:
        return max(seg.end for seg in self.segments)


@dataclass
class PlaylistSpec:
    ref: str
    title: str
    video_refs: List[str]      # ordered
    video_titles: List[str]


def _ts(seconds: int) -> str:
    return "%02d:%02d:%02d.000" % (seconds // 3600, (seconds % 3600) // 60,
                                   seconds % 60)


def mmss(seconds: int) -> str:
    return "%02d:%02d" % (seconds // 60, seconds % 60)


def captions_vtt(spec: VideoSpec) -> str:
    parts = ["WEBVTT", ""]
    for seg in spec.segments:
        parts.append("%s --> %s" % (_ts(seg.start), _ts(seg.end)))
        parts.extend(seg.lines)
        parts.append("")
    return "\n".join(parts)


def _render_card(lines: List[str], path: str) -> None:
    img = Image.new("RGB", VIDEO_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    # default bitmap font scaled by drawing at multiple; keep it simple and
    # crisp: draw text large by scaling up a small render
    small = Image.new("RGB", (VIDEO_SIZE[0] // 4, VIDEO_SIZE[1] // 4),
                      BG_COLOR)
    sdraw = ImageDraw.Draw(small)
    y = small.height // 2 - 7 * len(lines)
    for line in lines:
        w = sdraw.textlength(line)
        sdraw.text(((small.width - w) // 2, y), line, fill=FG_COLOR)
        y += 14
    img = small.resize(VIDEO_SIZE, Image.NEAREST)
    img.save(path)


class YouTubeMirror:
    """Local mirror builder + reader."""

    def __init__(self, root: str):
        self.root = os.path.join(root, "media_mirror")

    def video_dir(self, ref: str) -> str:
        return os.path.join(self.root, ref)

    def build_video(self, spec: VideoSpec, make_mp4: bool = False) -> str:
        vdir = self.video_dir(spec.ref)
        frames_dir = os.path.join(vdir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        for i, seg in enumerate(spec.segments):
            _render_card(seg.lines,
                         os.path.join(frames_dir, "seg%02d.png" % i))
        with open(os.path.join(vdir, "captions.vtt"), "w",
                  encoding="utf-8") as fh:
            fh.write(captions_vtt(spec))
        write_json(os.path.join(vdir, "metadata.json"), {
            "ref": spec.ref, "title": spec.title,
            "description": spec.description, "tags": spec.tags,
            "privacy": spec.privacy, "duration_seconds": spec.duration,
            "segments": [{"start": s.start, "end": s.end, "lines": s.lines}
                         for s in spec.segments],
        })
        if make_mp4:
            self._assemble_mp4(spec, vdir, frames_dir)
        return vdir

    @staticmethod
    def _assemble_mp4(spec: VideoSpec, vdir: str, frames_dir: str) -> None:
        concat_lines = []
        for i, seg in enumerate(spec.segments):
            concat_lines.append("file '%s'"
                                % os.path.join(frames_dir, "seg%02d.png" % i))
            concat_lines.append("duration %d" % (seg.end - seg.start))
        # ffmpeg concat demuxer needs the last file repeated
        concat_lines.append(concat_lines[-2])
        concat_path = os.path.join(vdir, "frames.concat")
        with open(concat_path, "w") as fh:
            fh.write("\n".join(concat_lines))
        out = os.path.join(vdir, "video.mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
               "-safe", "0", "-i", concat_path, "-vf", "fps=1",
               "-pix_fmt", "yuv420p", out]
        subprocess.run(cmd, check=True, capture_output=True)

    def build_playlist(self, spec: PlaylistSpec) -> str:
        pdir = os.path.join(self.root, spec.ref)
        os.makedirs(pdir, exist_ok=True)
        write_json(os.path.join(pdir, "playlist.json"), {
            "ref": spec.ref, "title": spec.title,
            "video_refs": spec.video_refs,
            "video_titles": spec.video_titles,
        })
        return pdir

    # ---- reader side (used by harness/oracle) -------------------------

    def metadata(self, ref: str) -> Dict[str, Any]:
        with open(os.path.join(self.video_dir(ref), "metadata.json"),
                  encoding="utf-8") as fh:
            return json.load(fh)

    def text_at(self, ref: str, timestamp: str) -> List[str]:
        """Displayed lines at 'MM:SS' (frame text == caption text)."""
        minute, second = timestamp.split(":")
        t = int(minute) * 60 + int(second)
        for seg in self.metadata(ref)["segments"]:
            if seg["start"] <= t < seg["end"]:
                return seg["lines"]
        return []

    def playlist(self, ref: str) -> Dict[str, Any]:
        with open(os.path.join(self.root, ref, "playlist.json"),
                  encoding="utf-8") as fh:
            return json.load(fh)


def video_reference_file(mirror_ref: str, note: str = "") -> Dict[str, Any]:
    """Content of the JSON file that points an agent at one video.

    The published form carries the unlisted YouTube URL; the generated form
    carries the mirror reference, which the publish step later rewrites.
    """
    return {"video_ref": mirror_ref, "platform": "youtube",
            "channel": "@TreasureHuntBench", "url": "", "note": note}


# ---- optional live upload (publish phase; requires local OAuth) --------

def upload_unlisted(video_dir: str, client_secret_path: str,
                    token_path: str) -> Optional[str]:
    """Upload mirror's video.mp4 as unlisted. Returns the video URL.

    Needs a stored OAuth token (interactive consent must have happened
    beforehand). Returns None when credentials or the mp4 are missing.
    """
    mp4 = os.path.join(video_dir, "video.mp4")
    if not (os.path.exists(mp4) and os.path.exists(client_secret_path)):
        return None
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        return None
    if not os.path.exists(token_path):
        return None
    creds = Credentials.from_authorized_user_file(
        token_path, ["https://www.googleapis.com/auth/youtube.upload"])
    with open(os.path.join(video_dir, "metadata.json"),
              encoding="utf-8") as fh:
        meta = json.load(fh)
    youtube = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": meta["title"],
                        "description": meta["description"],
                        "tags": meta.get("tags", [])},
            "status": {"privacyStatus": meta.get("privacy", "unlisted")}}
    request = youtube.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(mp4, mimetype="video/mp4"))
    response = request.execute()
    return "https://www.youtube.com/watch?v=%s" % response["id"]
