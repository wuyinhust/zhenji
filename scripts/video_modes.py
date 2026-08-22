"""Video mode definitions and simple routing for Zhenji.

四档体系（v1，2026-08-22 引入「浮光」）：

浮光  fuguang  无本地副本，仅 iOS 真机/屏幕陪看抓取若干关键帧画面 + 页面事实
                 用于快速知道「这条大概是什么」，不消耗下载/转录/场景分析成本
掠影  lueying  本地 480p + 均匀关键帧，不转录
                 用于大样本初筛、推荐流、搜索研究
听澜  tinglan  本地 720p + 完整音频转录 + 8-12 关键帧
                 用于日常 90% 视频（口播、知识、测评、剧情解说）
观澜  guanlan  本地 best 质量 + 完整转录 + 场景检测 + 音画时间轴对齐 + video_structure_json
                 用于置顶 / 高表现 / 关键复刻样本 / 用户明示要求

路由优先级：观澜 > 听澜 > 掠影 > 浮光。
- 高价值/复刻样本 → 观澜
- 普通理解需求 → 听澜
- 大批量扫描 → 掠影
- 只要看一眼/很快决定是否值得升级 → 浮光

依赖：
- 浮光：phone-harness / iPhone Mirroring（无需 yt-dlp）
- 掠影/听澜/观澜：yt-dlp + ffmpeg + faster-whisper + Mac Chrome cookies-from-browser
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMode:
    key: str
    zh_name: str
    purpose: str
    keyframes_min: int
    keyframes_max: int
    transcript: str
    scene_detection: bool
    requires_local_copy: bool
    local_quality: str  # 'none' | '480p' | '720p' | 'best'


FUGUANG = VideoMode(
    key="fuguang",
    zh_name="浮光",
    purpose="真机陪看抽帧，无需本地副本",
    keyframes_min=4,
    keyframes_max=10,
    transcript="none",
    scene_detection=False,
    requires_local_copy=False,
    local_quality="none",
)
LUEYING = VideoMode(
    key="lueying",
    zh_name="掠影",
    purpose="效率模式",
    keyframes_min=6,
    keyframes_max=12,
    transcript="none_or_partial",
    scene_detection=False,
    requires_local_copy=True,
    local_quality="480p",
)
TINGLAN = VideoMode(
    key="tinglan",
    zh_name="听澜",
    purpose="基本模式",
    keyframes_min=6,
    keyframes_max=16,
    transcript="full_if_available",
    scene_detection=False,
    requires_local_copy=True,
    local_quality="720p",
)
GUANLAN = VideoMode(
    key="guanlan",
    zh_name="观澜",
    purpose="完整模式",
    keyframes_min=10,
    keyframes_max=40,
    transcript="full_if_available",
    scene_detection=True,
    requires_local_copy=True,
    local_quality="best",
)

MODES = {m.key: m for m in (FUGUANG, LUEYING, TINGLAN, GUANLAN)}

# Priority from highest to lowest
MODE_PRIORITY = ("guanlan", "tinglan", "lueying", "fuguang")


def choose_mode(
    *,
    explicit: str | None = None,
    requires_timeline: bool = False,
    requires_full_understanding: bool = False,
    high_value: bool = False,
    rapid_scan_only: bool = False,
) -> VideoMode:
    """Choose a video mode by explicit request or by hints.

    Setting rapid_scan_only=True forces fuguang regardless of other hints.
    """
    if explicit:
        return MODES[explicit]
    if rapid_scan_only:
        return FUGUANG
    if requires_timeline:
        return GUANLAN
    if requires_full_understanding or high_value:
        return TINGLAN
    return LUEYING
