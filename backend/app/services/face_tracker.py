"""
Face Tracker Service
======================
MediaPipe-based face detection for smart video cropping.
Determines face positions to center the crop window.
"""

import os
import tempfile
import subprocess
from typing import Optional

from app.config import settings


class FaceTracker:
    """
    Detect and track faces in video segments
    for intelligent portrait cropping.
    """

    def __init__(self, min_detection_confidence: float = 0.5):
        import mediapipe as mp
        self.mp_face_detection = mp.solutions.face_detection
        self.min_confidence = min_detection_confidence

    async def detect_faces_in_segment(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        sample_interval: float = 0.5,  # Sample every 0.5 seconds
    ) -> list[dict]:
        """
        Detect face positions at intervals within a video segment.

        Args:
            video_path: Path to the video file
            start_time: Segment start in seconds
            end_time: Segment end in seconds
            sample_interval: How often to sample frames (seconds)

        Returns:
            List of {"timestamp", "center_x", "center_y", "width", "height"}
            All positions are normalized (0.0 - 1.0)
        """
        face_positions = []

        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        with self.mp_face_detection.FaceDetection(
            model_selection=1,  # Full range model
            min_detection_confidence=self.min_confidence,
        ) as face_detection:

            current_time = start_time
            while current_time <= end_time:
                frame_num = int(current_time * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

                ret, frame = cap.read()
                if not ret:
                    break

                # Convert BGR to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_frame)

                if results.detections:
                    # Use the most prominent face (highest confidence)
                    best_detection = max(
                        results.detections,
                        key=lambda d: d.score[0]
                    )
                    bbox = best_detection.location_data.relative_bounding_box

                    face_positions.append({
                        "timestamp": current_time,
                        "center_x": bbox.xmin + bbox.width / 2,
                        "center_y": bbox.ymin + bbox.height / 2,
                        "width": bbox.width,
                        "height": bbox.height,
                        "confidence": best_detection.score[0],
                    })

                current_time += sample_interval

        cap.release()
        return face_positions

    def calculate_optimal_crop_x(
        self,
        face_positions: list[dict],
        source_width: int,
        crop_width: int,
        smoothing: bool = True,
    ) -> int:
        """
        Calculate the optimal X offset for cropping based on face positions.

        Args:
            face_positions: Face data from detect_faces_in_segment
            source_width: Width of source video
            crop_width: Width of the crop window
            smoothing: Apply temporal smoothing to reduce jitter

        Returns:
            X offset in pixels for the crop
        """
        if not face_positions:
            # Default: center crop
            return (source_width - crop_width) // 2

        # Get average face center X position
        x_positions = [fp["center_x"] for fp in face_positions]

        if smoothing and len(x_positions) > 3:
            # Simple moving average for smoothing
            import numpy as np
            kernel_size = min(5, len(x_positions))
            x_positions = np.convolve(
                x_positions,
                np.ones(kernel_size) / kernel_size,
                mode="valid"
            ).tolist()

        avg_x = sum(x_positions) / len(x_positions)
        x_pixel = int(avg_x * source_width)

        # Center the crop on the face
        x_offset = x_pixel - crop_width // 2

        # Clamp to video bounds
        x_offset = max(0, min(x_offset, source_width - crop_width))

        return x_offset
