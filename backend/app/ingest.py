# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownParameterType=false
import io
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from typing import Any, TypedDict, cast

try:
    import fitz  # type: ignore[reportMissingImports]
except Exception:
    fitz = None  # type: ignore[assignment]

try:
    from PIL import Image as PILImageModule  # type: ignore[reportMissingImports]
except Exception:
    PILImageModule = None  # type: ignore[assignment]

try:
    import whisper  # type: ignore[reportMissingImports]
except Exception:
    whisper = None  # type: ignore[assignment]

try:
    import torch  # type: ignore[reportMissingImports]
except Exception:
    torch = None  # type: ignore[assignment]

PILImage = Any


class AudioBackendStatus(TypedDict):
    device: str
    whisper_model: str
    ffmpeg: str
    temp_dir: str


if torch is not None:
    device = "cuda" if bool(torch.cuda.is_available()) else "cpu"
else:
    device = "cpu"
logger = logging.getLogger(__name__)
_whisper_model: Any | bool | None = None
_whisper_lock = threading.Lock()
_ffmpeg_ready: bool | None = None
_ffmpeg_lock = threading.Lock()


def _ensure_ffmpeg() -> bool:
    global _ffmpeg_ready
    if _ffmpeg_ready is not None:
        return _ffmpeg_ready

    with _ffmpeg_lock:
        if _ffmpeg_ready is not None:
            return _ffmpeg_ready

        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            _ffmpeg_ready = True
            return True
        except Exception:
            pass

        try:
            import imageio_ffmpeg

            imageio_ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            ffmpeg_dir = os.path.dirname(imageio_ffmpeg_exe)
            ffmpeg_bin = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
            ffmpeg_shim_path = os.path.join(ffmpeg_dir, ffmpeg_bin)
            if not os.path.exists(ffmpeg_shim_path):
                shutil.copy2(imageio_ffmpeg_exe, ffmpeg_shim_path)

            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            _ffmpeg_ready = True
            logger.info("ffmpeg is ready using imageio-ffmpeg binary.")
            return True
        except Exception as exc:
            logger.warning("ffmpeg is unavailable for audio transcription: %s", exc)
            _ffmpeg_ready = False
            return False


def _get_whisper_model() -> Any | None:
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model if _whisper_model is not False else None
    with _whisper_lock:
        if _whisper_model is not None:
            return _whisper_model if _whisper_model is not False else None
        try:
            if whisper is None:
                raise RuntimeError("whisper package is unavailable")
            model_name = "tiny" if device == "cpu" else "base"
            _whisper_model = whisper.load_model(model_name, device=device)
        except Exception as exc:
            logger.warning("Whisper model unavailable: %s", exc)
            _whisper_model = False
    return _whisper_model if _whisper_model is not False else None


def process_pdf(file_bytes: bytes) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is unavailable in this environment.")
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text.strip()


def process_image(file_bytes: bytes) -> PILImage:
    if PILImageModule is None:
        raise RuntimeError("Pillow (PIL) is unavailable in this environment.")
    return cast("PILImage", PILImageModule.open(io.BytesIO(file_bytes)).convert("RGB"))


def process_audio(file_bytes: bytes, filename: str) -> str:
    import subprocess
    
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in {".m4a", ".mp3", ".wav"}:
        ext = ".wav"
    ext_without_dot = ext[1:] if ext.startswith(".") else ext
    logger.info("Processing audio file: %s, ext: %s (without dot: %s), size: %d bytes", filename, ext, ext_without_dot, len(file_bytes))

    app_temp_dir = os.path.abspath(
        os.getenv("MEDIRAG_TMP_DIR", os.path.join(os.path.dirname(__file__), "..", ".tmp"))
    )
    os.makedirs(app_temp_dir, exist_ok=True)

    temp_path = ""
    wav_path = ""
    try:
        if not _ensure_ffmpeg():
            raise RuntimeError("Audio transcription is unavailable: ffmpeg is missing.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=app_temp_dir) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name
        
        logger.info("Wrote audio to temp file: %s", temp_path)
        audio_to_transcribe = temp_path
        
        if ext in {".m4a", ".mp3"}:
            wav_path = tempfile.mktemp(suffix=".wav", dir=app_temp_dir)
            convert_cmd = ["ffmpeg", "-y", "-i", temp_path, "-ar", "16000", "-ac", "1", "-threads", "1", wav_path]
            logger.info("Converting audio with command: %s", " ".join(convert_cmd))
            try:
                result = subprocess.run(convert_cmd, check=True, capture_output=True, timeout=60)
                audio_to_transcribe = wav_path
                logger.info("Successfully converted %s to wav", ext)
            except subprocess.CalledProcessError as conv_err:
                logger.error("Audio conversion failed: %s, stderr: %s", conv_err, conv_err.stderr)
                raise RuntimeError(f"Audio conversion failed: {conv_err.stderr}")
            except subprocess.TimeoutExpired:
                raise RuntimeError("Audio conversion timed out")

        logger.info("Loading whisper model...")
        whisper_model = _get_whisper_model()
        if whisper_model is None:
            raise RuntimeError("Audio transcription is unavailable: Whisper model failed to load.")
        
        transcribe_opts = {
            "fp16": device == "cuda",
            "language": "en",
        }
        
        logger.info("Starting transcription with opts: %s", transcribe_opts)
        result = cast(dict[str, Any], whisper_model.transcribe(audio_to_transcribe, **transcribe_opts))
        transcript = str(result.get("text", "")).strip()
        
        if not transcript:
            logger.warning("Empty transcript for %s", filename)
            return ""
            
        logger.info("Audio transcript for %s: %s", filename, transcript[:200])
        return transcript
    except Exception as exc:
        logger.error("Audio transcription FAILED for %s: %s", filename, exc, exc_info=True)
        raise RuntimeError(f"Audio processing failed: {exc}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass


def get_audio_backend_status() -> AudioBackendStatus:
    return {
        "device": device,
        "whisper_model": (
            "failed" if _whisper_model is False else "loaded" if _whisper_model is not None else "not_loaded"
        ),
        "ffmpeg": (
            "unavailable" if _ffmpeg_ready is False else "available" if _ffmpeg_ready is True else "unknown"
        ),
        "temp_dir": os.path.abspath(
            os.getenv("MEDIRAG_TMP_DIR", os.path.join(os.path.dirname(__file__), "..", ".tmp"))
        ),
    }
