"""
Speaker-transcript alignment pipeline.
"""
from typing import List, Dict
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def calculate_overlap(start1: float, end1: float, start2: float, end2: float) -> float:
    """
    Calculate the overlap duration between two time intervals.

    Args:
        start1: Start time of first interval
        end1: End time of first interval
        start2: Start time of second interval
        end2: End time of second interval

    Returns:
        Overlap duration in seconds
    """
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    return max(0, overlap_end - overlap_start)


def align_speakers_with_transcript(
    diarization_segments: List[Dict],
    transcript_segments: List[Dict]
) -> List[Dict]:
    """
    Align speaker labels with transcript segments based on time overlap.

    Args:
        diarization_segments: List of speaker segments with 'speaker', 'start', 'end'
        transcript_segments: List of transcript segments with 'start', 'end', 'text'

    Returns:
        List of aligned segments with speaker labels and text
    """
    logger.info(
        f"Aligning {len(diarization_segments)} speaker segments "
        f"with {len(transcript_segments)} transcript segments"
    )

    aligned_segments = []

    for transcript_seg in transcript_segments:
        t_start = transcript_seg['start']
        t_end = transcript_seg['end']
        t_text = transcript_seg['text']

        # Find the speaker with maximum overlap for this transcript segment
        best_speaker = None
        max_overlap = 0

        for diar_seg in diarization_segments:
            d_start = diar_seg['start']
            d_end = diar_seg['end']
            d_speaker = diar_seg['speaker']

            overlap = calculate_overlap(t_start, t_end, d_start, d_end)

            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = d_speaker

        # If no overlap found, assign to "UNKNOWN"
        if best_speaker is None or max_overlap == 0:
            best_speaker = "UNKNOWN"
            logger.warning(
                f"No speaker found for transcript segment at {t_start:.2f}s - {t_end:.2f}s"
            )

        aligned_segments.append({
            'speaker': best_speaker,
            'start': t_start,
            'end': t_end,
            'text': t_text
        })

    # Merge consecutive segments from the same speaker
    merged_segments = merge_consecutive_segments(aligned_segments)

    logger.info(f"Alignment complete. Created {len(merged_segments)} aligned segments")

    return merged_segments


def merge_consecutive_segments(segments: List[Dict]) -> List[Dict]:
    """
    Merge consecutive segments from the same speaker.

    Args:
        segments: List of segments with 'speaker', 'start', 'end', 'text'

    Returns:
        List of merged segments
    """
    if not segments:
        return []

    merged = []
    current = segments[0].copy()

    for segment in segments[1:]:
        # If same speaker and close in time (within 1 second), merge
        if (segment['speaker'] == current['speaker'] and
            segment['start'] - current['end'] <= 1.0):
            # Merge text and update end time
            current['text'] += ' ' + segment['text']
            current['end'] = segment['end']
        else:
            # Different speaker or gap too large, save current and start new
            merged.append(current)
            current = segment.copy()

    # Don't forget the last segment
    merged.append(current)

    logger.debug(f"Merged {len(segments)} segments into {len(merged)} segments")

    return merged


def get_speaker_statistics(segments: List[Dict]) -> Dict:
    """
    Calculate statistics about speakers in the segments.

    Args:
        segments: List of segments with 'speaker', 'start', 'end', 'text'

    Returns:
        Dictionary with speaker statistics
    """
    if not segments:
        return {
            'total_speakers': 0,
            'speakers': {}
        }

    speaker_stats = {}

    for segment in segments:
        speaker = segment['speaker']
        duration = segment['end'] - segment['start']

        if speaker not in speaker_stats:
            speaker_stats[speaker] = {
                'segment_count': 0,
                'total_duration': 0.0,
                'word_count': 0
            }

        speaker_stats[speaker]['segment_count'] += 1
        speaker_stats[speaker]['total_duration'] += duration
        speaker_stats[speaker]['word_count'] += len(segment['text'].split())

    return {
        'total_speakers': len(speaker_stats),
        'speakers': speaker_stats
    }
