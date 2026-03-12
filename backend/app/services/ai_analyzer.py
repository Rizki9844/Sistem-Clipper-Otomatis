"""
AI Highlight Analyzer Service — Advanced
============================================
Multi-pass LLM analysis:
  Pass 1: Coarse scan (identify candidate regions)
  Pass 2: Fine analysis (precise timestamps + scoring)
  Pass 3: Hook optimization (rewrite hooks for each clip)

Uses Google Gemini (free tier: 1M tokens/day) with JSON output.
"""

import json
import time
from typing import Optional

import google.generativeai as genai
from pydantic import BaseModel, Field

from app.config import settings
from app.logging_config import get_logger
from app.exceptions import AIAnalysisError, InvalidLLMResponseError, LLMRateLimitError

logger = get_logger("ai_analyzer")


# ---- Structured Output Schemas ----

class HighlightSegment(BaseModel):
    """A single highlight segment identified by the AI."""
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    score: float = Field(ge=0.0, le=10.0, description="Viral potential score 0-10")
    hook_text: str = Field(description="The hook/key phrase that makes this viral")
    category: str = Field(description="Category: hook, punchline, emotional, informational, controversial, viral, story")
    reasoning: str = Field(description="Why this segment has high potential")
    suggested_title: str = Field(default="", description="Suggested title for the clip")
    hashtags: list[str] = Field(default_factory=list, description="Suggested hashtags")


class AnalysisResult(BaseModel):
    """Complete analysis result from the AI."""
    total_segments_found: int
    segments: list[HighlightSegment]
    overall_summary: str
    content_themes: list[str]
    content_type: str = Field(default="general", description="podcast, tutorial, vlog, interview, etc.")
    language: str = Field(default="en", description="Detected content language")
    audience_level: str = Field(default="general", description="beginner, intermediate, advanced, general")


# ---- System Prompts ----

COARSE_SCAN_PROMPT = """You are an expert viral content analyst. Perform a COARSE SCAN of this transcript.
Identify REGIONS (not exact timestamps) where interesting content exists.

For each region, provide:
- approximate_start: rough start time in seconds
- approximate_end: rough end time in seconds
- topic: what's being discussed
- potential: high/medium/low
- reason: brief explanation

Return JSON:
{{
    "content_type": "<podcast|tutorial|vlog|interview|lecture|comedy|news|other>",
    "language": "<detected language code>",
    "audience_level": "<beginner|intermediate|advanced|general>",
    "themes": ["theme1", "theme2"],
    "regions": [
        {{
            "approximate_start": <float>,
            "approximate_end": <float>,
            "topic": "<topic>",
            "potential": "<high|medium|low>",
            "reason": "<why interesting>"
        }}
    ]
}}"""

FINE_ANALYSIS_PROMPT = """You are an expert viral content analyst and video editor.
Analyze these HIGH-POTENTIAL REGIONS from a video transcript and extract PRECISE clip segments.

## SCORING CRITERIA (0-10):
- **Hook Power (0-3)**: Does it start with an attention-grabbing hook?
  - 3: "Wait, WHAT?!" level hook — stops scrolling instantly
  - 2: Strong curiosity or emotional trigger
  - 1: Mild interest
  - 0: No hook at all
- **Emotional Impact (0-2)**: Surprise, humor, inspiration, controversy?
- **Information Density (0-2)**: Actionable insights or unique knowledge?
- **Shareability (0-2)**: Would someone DM this or repost?
- **Completeness (0-1)**: Is it self-contained? Understandable without context?

## CRITICAL RULES:
1. Segments MUST be {min_duration}-{max_duration} seconds
2. Start 1-2s BEFORE the hook (build-up matters)
3. End AFTER a natural pause or conclusion (never mid-sentence!)
4. The FIRST 3 SECONDS of each clip decide if viewers stay — optimize for this
5. Score HONESTLY — mediocre content should get 3-5, not 7-8
6. Maximum {max_segments} segments
7. For each segment, write a scroll-stopping HOOK TEXT (the one-liner that would work as a caption)
8. Suggest a title and 3-5 hashtags per clip

## TIMESTAMP FORMAT:
Use SECONDS as float values matching the transcript timestamps exactly.

## OUTPUT (JSON):
{{
    "total_segments_found": <int>,
    "segments": [
        {{
            "start_time": <float>,
            "end_time": <float>,
            "score": <float 0-10>,
            "hook_text": "<scroll-stopping one-liner>",
            "category": "<hook|punchline|emotional|informational|controversial|viral|story>",
            "reasoning": "<why this is worth clipping, be specific>",
            "suggested_title": "<short title for the clip>",
            "hashtags": ["tag1", "tag2", "tag3"]
        }}
    ],
    "overall_summary": "<2-3 sentence summary of the content>",
    "content_themes": ["theme1", "theme2"]
}}"""


class AIAnalyzer:
    """
    Multi-pass AI highlight detector.
    Pass 1: Coarse scan → regions of interest
    Pass 2: Fine analysis → precise timestamps + scoring
    """

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )

    async def analyze_transcript(
        self,
        transcript_text: str,
        transcript_segments: list[dict],
        video_duration: float,
        max_segments: int = 10,
        min_clip_duration: float = None,
        max_clip_duration: float = None,
        multi_pass: bool = True,
    ) -> AnalysisResult:
        """
        Analyze transcript with optional multi-pass processing.

        Pass 1 (coarse): Identify candidate regions
        Pass 2 (fine): Extract precise segments from regions

        For short transcripts (<5 minutes), single-pass is used.
        """
        min_dur = min_clip_duration or settings.CLIP_MIN_DURATION_SECONDS
        max_dur = max_clip_duration or settings.CLIP_MAX_DURATION_SECONDS

        start_time = time.time()

        # Short videos: single pass
        if video_duration < 300 or not multi_pass:
            result = await self._single_pass_analysis(
                transcript_text, transcript_segments,
                video_duration, max_segments, min_dur, max_dur,
            )
        else:
            # Long videos: multi-pass
            result = await self._multi_pass_analysis(
                transcript_text, transcript_segments,
                video_duration, max_segments, min_dur, max_dur,
            )

        elapsed = time.time() - start_time
        logger.info(
            "Analysis complete",
            segments=len(result.segments),
            duration=round(elapsed, 1),
            content_type=result.content_type,
            themes=result.content_themes,
        )

        return result

    async def _multi_pass_analysis(
        self,
        transcript_text: str,
        transcript_segments: list[dict],
        video_duration: float,
        max_segments: int,
        min_dur: float,
        max_dur: float,
    ) -> AnalysisResult:
        """
        Multi-pass analysis for long videos.

        Pass 1: Coarse scan to identify regions of interest
        Pass 2: Fine analysis on each region
        """
        logger.info("Starting multi-pass analysis", duration=video_duration)

        # ---- PASS 1: Coarse Scan ----
        segments_text = self._format_segments_for_llm(transcript_segments)

        coarse_response = await self._call_llm(
            system_prompt=COARSE_SCAN_PROMPT,
            user_message=f"## VIDEO ({video_duration/60:.0f} minutes)\n\n{segments_text}",
            max_tokens=2048,
        )

        coarse_data = json.loads(coarse_response)
        high_regions = [
            r for r in coarse_data.get("regions", [])
            if r.get("potential") in ("high", "medium")
        ]

        logger.info(
            "Coarse scan complete",
            total_regions=len(coarse_data.get("regions", [])),
            high_potential=len(high_regions),
            content_type=coarse_data.get("content_type", "unknown"),
        )

        if not high_regions:
            return AnalysisResult(
                total_segments_found=0,
                segments=[],
                overall_summary="No high-potential regions found in this content.",
                content_themes=coarse_data.get("themes", []),
                content_type=coarse_data.get("content_type", "general"),
                language=coarse_data.get("language", "en"),
            )

        # ---- PASS 2: Fine Analysis on Regions ----
        # Extract only the transcript segments within high-potential regions
        focused_segments = []
        for region in high_regions:
            approx_start = region.get("approximate_start", 0)
            approx_end = region.get("approximate_end", 0)
            # Add buffer
            start = max(0, approx_start - 5)
            end = min(video_duration, approx_end + 5)

            region_segs = [
                s for s in transcript_segments
                if s.get("start", 0) >= start and s.get("end", 0) <= end
            ]
            focused_segments.extend(region_segs)

        # Deduplicate
        seen = set()
        unique_segments = []
        for seg in focused_segments:
            key = (seg.get("start"), seg.get("end"))
            if key not in seen:
                seen.add(key)
                unique_segments.append(seg)

        focused_text = self._format_segments_for_llm(unique_segments)

        system_prompt = FINE_ANALYSIS_PROMPT.format(
            min_duration=min_dur,
            max_duration=max_dur,
            max_segments=max_segments,
        )

        fine_response = await self._call_llm(
            system_prompt=system_prompt,
            user_message=(
                f"## HIGH-POTENTIAL REGIONS\n"
                f"Video duration: {video_duration:.0f}s ({video_duration/60:.0f} min)\n\n"
                f"## FOCUSED TRANSCRIPT (regions of interest only)\n{focused_text}\n\n"
                f"Extract the best {max_segments} clips as precise segments."
            ),
            max_tokens=4096,
        )

        result_data = json.loads(fine_response)
        analysis = AnalysisResult(
            **result_data,
            content_type=coarse_data.get("content_type", "general"),
            language=coarse_data.get("language", "en"),
            audience_level=coarse_data.get("audience_level", "general"),
        )

        # Validate and clean
        analysis.segments = self._validate_segments(
            analysis.segments, video_duration, min_dur, max_dur
        )
        analysis.segments.sort(key=lambda s: s.score, reverse=True)
        analysis.total_segments_found = len(analysis.segments)

        return analysis

    async def _single_pass_analysis(
        self,
        transcript_text: str,
        transcript_segments: list[dict],
        video_duration: float,
        max_segments: int,
        min_dur: float,
        max_dur: float,
    ) -> AnalysisResult:
        """Single-pass analysis for short videos."""
        logger.info("Starting single-pass analysis", duration=video_duration)

        segments_text = self._format_segments_for_llm(transcript_segments)

        system_prompt = FINE_ANALYSIS_PROMPT.format(
            min_duration=min_dur,
            max_duration=max_dur,
            max_segments=max_segments,
        )

        user_message = f"""## VIDEO INFORMATION
- Total Duration: {video_duration:.1f} seconds ({video_duration/60:.1f} minutes)
- Clip Duration Range: {min_dur}-{max_dur} seconds

## TRANSCRIPT WITH TIMESTAMPS
{segments_text}

## TASK
Analyze the transcript and identify the most viral/engaging segments.
Return your analysis as valid JSON."""

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=4096,
        )

        result_data = json.loads(response)
        analysis = AnalysisResult(**result_data)

        analysis.segments = self._validate_segments(
            analysis.segments, video_duration, min_dur, max_dur
        )
        analysis.segments.sort(key=lambda s: s.score, reverse=True)
        analysis.total_segments_found = len(analysis.segments)

        return analysis

    async def _call_llm(self, system_prompt: str, user_message: str,
                        max_tokens: int = 4096, retries: int = 3) -> str:
        """Call Gemini LLM with retry logic and error handling."""
        import asyncio

        combined_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

        for attempt in range(retries):
            try:
                # Gemini SDK is sync, run in executor for async compat
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(combined_prompt),
                )
                return response.text

            except Exception as e:
                error_str = str(e).lower()
                if "resource_exhausted" in error_str or "429" in error_str or "quota" in error_str:
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"Rate limited, waiting {wait_time}s", attempt=attempt)
                    await asyncio.sleep(wait_time)
                    if attempt == retries - 1:
                        raise LLMRateLimitError(
                            "Gemini API rate limit exceeded after retries",
                            details={"model": settings.GEMINI_MODEL, "attempts": retries},
                        )
                elif attempt == retries - 1:
                    raise AIAnalysisError(
                        f"Gemini call failed: {str(e)}",
                        details={"model": settings.GEMINI_MODEL, "attempt": attempt},
                    )
                else:
                    logger.warning(f"Gemini call failed, retrying", attempt=attempt, error=str(e))
                    await asyncio.sleep(5)

    def _format_segments_for_llm(self, segments: list[dict]) -> str:
        """Format transcript segments with timestamps."""
        lines = []
        for seg in segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            start_ts = self._seconds_to_timestamp(start)
            end_ts = self._seconds_to_timestamp(end)
            text = seg.get("text", "").strip()
            lines.append(f"[{start_ts} → {end_ts}] ({start:.1f}s-{end:.1f}s) {text}")
        return "\n".join(lines)

    def _seconds_to_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"

    def _validate_segments(
        self,
        segments: list[HighlightSegment],
        video_duration: float,
        min_duration: float,
        max_duration: float,
    ) -> list[HighlightSegment]:
        """Validate, adjust, and clean AI-generated segments."""
        valid = []
        for seg in segments:
            seg.start_time = max(0, seg.start_time)
            seg.end_time = min(video_duration, seg.end_time)

            duration = seg.end_time - seg.start_time

            # Auto-adjust duration
            if duration < min_duration:
                seg.end_time = min(seg.start_time + min_duration, video_duration)
            elif duration > max_duration:
                seg.end_time = seg.start_time + max_duration

            duration = seg.end_time - seg.start_time
            if min_duration <= duration <= max_duration and seg.start_time < seg.end_time:
                # Clamp score
                seg.score = max(0.0, min(10.0, seg.score))
                valid.append(seg)

        return self._remove_overlaps(valid)

    def _remove_overlaps(self, segments: list[HighlightSegment]) -> list[HighlightSegment]:
        """Remove overlapping segments, keeping highest scored."""
        if not segments:
            return []

        segments.sort(key=lambda s: s.score, reverse=True)
        result = [segments[0]]

        for seg in segments[1:]:
            overlap = False
            for kept in result:
                overlap_start = max(seg.start_time, kept.start_time)
                overlap_end = min(seg.end_time, kept.end_time)
                if overlap_end > overlap_start:
                    overlap_duration = overlap_end - overlap_start
                    seg_duration = seg.end_time - seg.start_time
                    if overlap_duration / seg_duration > 0.5:
                        overlap = True
                        break
            if not overlap:
                result.append(seg)

        return result
