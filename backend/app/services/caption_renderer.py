"""
Dynamic Caption Renderer Service 🎨
=======================================
Generates ASS (Advanced SubStation Alpha) subtitles
with word-by-word highlighting — Alex Hormozi style.

Supports:
- Word-by-word color highlight animation
- Pop-in / bounce / fade effects
- Customizable fonts, colors, positioning
- Template-based styles
"""

from typing import Optional
from app.models.transcript import WordTimestamp
from app.models.style import CaptionStyle, FontConfig, ColorConfig, AnimationConfig, PositionConfig


class CaptionRenderer:
    """
    Generates dynamic ASS subtitle files for FFmpeg rendering.
    Uses word-level timestamps for precise word-by-word animation.
    """

    # ASS header template
    ASS_HEADER = """[Script Info]
Title: AutoClipper Dynamic Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_family},{font_size},{primary_color},{highlight_color},{outline_color},{shadow_color},{bold},{italic},0,0,100,100,0,0,1,{outline_width},{shadow_depth},{alignment},{margin_l},{margin_r},{margin_v},1
Style: Highlight,{font_family},{highlight_size},{highlight_color},{primary_color},{outline_color},{shadow_color},{bold},{italic},0,0,100,100,0,0,1,{outline_width},{shadow_depth},{alignment},{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def __init__(self, style: Optional[CaptionStyle] = None):
        """Initialize with a caption style (or use defaults)."""
        self.style = style or CaptionStyle(
            name="Default Hormozi",
            font=FontConfig(),
            colors=ColorConfig(),
            animation=AnimationConfig(),
            position=PositionConfig(),
        )

    def generate_ass_file(
        self,
        words: list[WordTimestamp],
        output_path: str,
        clip_start_offset: float = 0.0,
    ) -> str:
        """
        Generate an ASS subtitle file with word-by-word highlighting.

        Args:
            words: List of WordTimestamp with precise timing
            output_path: Path to save the .ass file
            clip_start_offset: Offset to subtract (if using trimmed clip)

        Returns:
            Path to the generated ASS file
        """
        font = self.style.font
        colors = self.style.colors
        anim = self.style.animation
        pos = self.style.position

        # Generate header
        ass_content = self.ASS_HEADER.format(
            play_res_x=1080 if pos.alignment else 1920,
            play_res_y=1920 if pos.alignment else 1080,
            font_family=font.family,
            font_size=font.size,
            primary_color=self._hex_to_ass_color(colors.primary_text),
            highlight_color=self._hex_to_ass_color(colors.highlight_text),
            outline_color=self._hex_to_ass_color(colors.outline),
            shadow_color=self._hex_to_ass_color(colors.shadow),
            bold=-1 if font.bold else 0,
            italic=-1 if font.italic else 0,
            outline_width=font.outline_width,
            shadow_depth=font.shadow_depth,
            alignment=self._get_ass_alignment(pos.alignment),
            margin_l=pos.margin_x,
            margin_r=pos.margin_x,
            margin_v=pos.margin_y,
            highlight_size=int(font.size * anim.scale_factor),
        )

        # Group words into displayable chunks
        word_groups = self._group_words(words, anim.words_per_group)

        # Generate dialogue events
        for group in word_groups:
            if not group:
                continue

            group_start = group[0].start - clip_start_offset
            group_end = group[-1].end - clip_start_offset

            if group_start < 0:
                continue

            # Generate word-by-word highlight events
            events = self._generate_highlight_events(
                group, group_start, group_end, clip_start_offset, anim
            )
            ass_content += events

        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        return output_path

    def _generate_highlight_events(
        self,
        words: list[WordTimestamp],
        group_start: float,
        group_end: float,
        offset: float,
        anim: AnimationConfig,
    ) -> str:
        """Generate ASS events for word-by-word highlighting."""
        events = ""

        for i, word in enumerate(words):
            word_start = word.start - offset
            word_end = word.end - offset

            # Build text with current word highlighted
            parts = []
            for j, w in enumerate(words):
                text = w.word.upper() if anim.use_uppercase else w.word
                if j == i:
                    # Highlighted word (different color + optional scale)
                    if anim.style == "word_highlight":
                        parts.append(
                            f"{{\\c{self._hex_to_ass_color(self.style.colors.highlight_text)}"
                            f"\\fscx{int(anim.scale_factor * 100)}"
                            f"\\fscy{int(anim.scale_factor * 100)}}}"
                            f"{text}"
                            f"{{\\c{self._hex_to_ass_color(self.style.colors.primary_text)}"
                            f"\\fscx100\\fscy100}}"
                        )
                    elif anim.style == "pop_in":
                        parts.append(
                            f"{{\\t(0,{anim.highlight_duration_ms},"
                            f"\\fscx{int(anim.scale_factor * 100)}"
                            f"\\fscy{int(anim.scale_factor * 100)})"
                            f"\\c{self._hex_to_ass_color(self.style.colors.highlight_text)}}}"
                            f"{text}"
                            f"{{\\r}}"
                        )
                    elif anim.style == "karaoke":
                        duration_cs = int((word_end - word_start) * 100)
                        parts.append(f"{{\\kf{duration_cs}}}{text}")
                    else:
                        parts.append(
                            f"{{\\c{self._hex_to_ass_color(self.style.colors.highlight_text)}}}"
                            f"{text}"
                            f"{{\\c{self._hex_to_ass_color(self.style.colors.primary_text)}}}"
                        )
                else:
                    parts.append(text)

            line_text = " ".join(parts)

            # Determine event timing
            if i < len(words) - 1:
                event_end = words[i + 1].start - offset
            else:
                event_end = group_end

            start_ts = self._seconds_to_ass_time(max(0, word_start))
            end_ts = self._seconds_to_ass_time(max(0, event_end))

            events += f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{line_text}\n"

        return events

    def _group_words(
        self, words: list[WordTimestamp], group_size: int
    ) -> list[list[WordTimestamp]]:
        """Split words into display groups."""
        groups = []
        for i in range(0, len(words), group_size):
            groups.append(words[i:i + group_size])
        return groups

    @staticmethod
    def _hex_to_ass_color(hex_color: str) -> str:
        """
        Convert hex color (#RRGGBB) to ASS color format (&HBBGGRR&).
        ASS uses BGR order with &H prefix.
        """
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H00{b}{g}{r}&"
        return "&H00FFFFFF&"

    @staticmethod
    def _get_ass_alignment(alignment: str) -> int:
        """Convert position string to ASS numpad alignment."""
        alignments = {
            "bottom_left": 1, "bottom_center": 2, "bottom_right": 3,
            "center_left": 4, "center": 5, "center_right": 6,
            "top_left": 7, "top_center": 8, "top_right": 9,
        }
        return alignments.get(alignment, 2)

    @staticmethod
    def _seconds_to_ass_time(seconds: float) -> str:
        """Convert seconds to ASS timestamp (H:MM:SS.cs)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        centiseconds = int((secs % 1) * 100)
        return f"{hours}:{minutes:02d}:{int(secs):02d}.{centiseconds:02d}"


def generate_hormozi_captions(
    words: list[WordTimestamp],
    output_path: str,
    clip_start_offset: float = 0.0,
    style: Optional[CaptionStyle] = None,
) -> str:
    """
    Convenience function to generate Hormozi-style captions.

    Usage:
        from app.services.caption_renderer import generate_hormozi_captions
        ass_path = generate_hormozi_captions(words, "/tmp/captions.ass")
    """
    renderer = CaptionRenderer(style)
    return renderer.generate_ass_file(words, output_path, clip_start_offset)
