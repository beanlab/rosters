from datetime import datetime
from pathlib import Path

from myteam.workflow import run_agent
from myteam.workflow.models import StepResult

AGENT = 'pi'

ERRORS_DESCRIPTION = (
    "if this task cannot be accomplished (e.g. the file doesn't exist)"
    "set unfillable outputs to null and explain the problem here; "
    "otherwise set this to null"
)


def raise_on_error(results: StepResult):
    if errors := results.output['errors']:
        raise RuntimeError(errors)


def format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%S")


def listen(
        model_size: str = "base",
        language: str | None = None,
        sample_rate: int = 16_000,
        chunk_duration: float = 1.0,
) -> str:
    """Record microphone audio until Ctrl-C, then transcribe it.

    Requires the optional runtime dependencies `faster-whisper`, `sounddevice`,
    and `numpy`.
    """
    try:
        import numpy as np
        import sounddevice as sd
        from faster_whisper import WhisperModel
    except ImportError as exc:
        missing_package = exc.name or "an optional dependency"
        raise ImportError(
            "listen() requires faster-whisper, sounddevice, and numpy. "
            f"Missing package: {missing_package!r}."
        ) from exc

    chunk_size = int(sample_rate * chunk_duration)
    if chunk_size <= 0:
        raise ValueError("chunk_duration must be positive")

    chunks = []
    print("Listening. Press Ctrl-C to stop recording and transcribe.")

    try:
        with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
        ) as stream:
            while True:
                audio_chunk, overflowed = stream.read(chunk_size)
                if overflowed:
                    print("Warning: microphone input overflowed; audio may be missing.")
                chunks.append(audio_chunk.copy())
    except KeyboardInterrupt:
        print("\nRecording stopped. Transcribing...")

    if not chunks:
        return ""

    audio = np.concatenate(chunks, axis=0).reshape(-1)
    model = WhisperModel(model_size, device="auto")
    segments, _ = model.transcribe(audio, language=language)

    return "".join(segment.text for segment in segments).strip()


def save_transcript(transcript: str, timestamp: str, transcripts_dir: Path) -> Path:
    results = run_agent(
        agent=AGENT,
        prompt=f"""
        What follows is a raw transcription. Please clean it up:
        - Add punctuation
        - Create paragraphs
        - Correct transcription errors
        - Remove filler words
        
        If something is unclear, mark it with square braces `[ ]`.
        
        As much as possible, preserve the original language and meanings.
        
        Return only the improved transcription.
        
        -------
        {transcript}
        """,
        output={
            "cleaned_transcript": "the text of the cleaned transcript",
            "errors": ERRORS_DESCRIPTION
        }
    )
    
    raise_on_error(results)
    
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    path = transcripts_dir / f"{timestamp}.raw.txt"
    path.write_text(results.output['cleaned_transcript'], encoding="utf-8")
    return path


def save_notes(notes: str, timestamp: str, notes_dir: Path) -> Path:
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = notes_dir / f"{timestamp}.md"
    path.write_text(notes, encoding="utf-8")
    return path


def prepare_notes(transcript: str) -> str:
    run_agent(
        agent=AGENT,
        prompt="""
        Your task is to summarize the following transcript into effective notes.
        
        These are t 
        """
    )


def main(notes_dir: Path, transcripts_dir: Path):
    timestamp = format_timestamp()
    transcript = listen()
    save_transcript(transcript, timestamp, transcripts_dir)

    notes = prepare_notes(transcript)
    save_notes(notes, timestamp, notes_dir)
