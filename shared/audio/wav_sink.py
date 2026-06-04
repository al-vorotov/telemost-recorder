import struct
import wave
from pathlib import Path


class WavAudioSink:
    """Накопление PCM float32 [-1,1] → WAV 16 kHz mono."""

    def __init__(self, output_path: Path, sample_rate: int = 16000) -> None:
        self._path = output_path
        self._sample_rate = sample_rate
        self._samples: list[float] = []

    async def write_float32(self, samples: list[float]) -> None:
        self._samples.extend(samples)

    async def finalize(self) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        pcm = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * 32767.0)))) for s in self._samples
        )
        if not pcm:
            pcm = struct.pack("<h", 0)

        with wave.open(str(self._path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self._sample_rate)
            wf.writeframes(pcm)
        return self._path
