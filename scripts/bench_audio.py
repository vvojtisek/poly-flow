#!/usr/bin/env python3
"""Measure TTS (Piper) and STT (Whisper) latency on the machine that runs the audio profile.

    docker compose --profile audio up -d --build
    python3 scripts/bench_audio.py --out docs/bench/$(hostname)-$(date +%F).md

Run it once per Whisper model you want to compare (restart the stack with WHISPER_MODEL=...).
Speech is Piper's own output, i.e. clean synthetic audio: real microphone recordings, children's
voices and noisy rooms will be slower to decode and less accurate. Treat the accuracy column as a
sanity check, not as a quality score.

--smoke runs one request per case and exits non-zero on an error or low accuracy (used by CI).
Standard library only.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import threading
import time
import unicodedata
import urllib.request
import uuid
import wave
from io import BytesIO
from pathlib import Path

CASES = {
    "de": {
        "voice": "de_DE-thorsten-medium",
        "word": "der Hund",
        "sentence": "Am Wochenende fahren wir mit dem Zug in die Berge, weil das Wetter schön "
        "sein soll und die Kinder gern wandern.",
    },
    "fr": {
        "voice": "fr_FR-siwis-medium",
        "word": "le chien",
        "sentence": "Ce week-end, nous prenons le train pour aller à la montagne, parce qu'il "
        "doit faire beau et que les enfants aiment marcher.",
    },
    "it": {
        "voice": "it_IT-paola-medium",
        "word": "il cane",
        "sentence": "Questo fine settimana prendiamo il treno per andare in montagna, perché "
        "dovrebbe fare bel tempo e ai bambini piace camminare.",
    },
}


def _post(url: str, body: bytes, content_type: str, timeout: float = 300) -> bytes:
    req = urllib.request.Request(url, data=body, headers={"Content-Type": content_type})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


def synthesize(piper: str, voice: str, text: str) -> tuple[bytes, float]:
    started = time.perf_counter()
    audio = _post(
        f"{piper}/synthesize",
        json.dumps({"text": text, "voice": voice}).encode(),
        "application/json",
    )
    return audio, time.perf_counter() - started


def wav_seconds(audio: bytes) -> float:
    with wave.open(BytesIO(audio)) as w:
        return w.getnframes() / w.getframerate()


def transcribe(whisper: str, audio: bytes, language: str) -> tuple[dict, float]:
    boundary = uuid.uuid4().hex
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\n{language}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="a.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode()
        + audio
        + f"\r\n--{boundary}--\r\n".encode()
    )
    started = time.perf_counter()
    raw = _post(f"{whisper}/v1/transcribe", body, f"multipart/form-data; boundary={boundary}")
    return json.loads(raw), time.perf_counter() - started


def _words(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text.lower()).replace("\u2019", "'")
    return re.findall(r"\w+", text)


def accuracy(expected: str, got: str) -> float:
    """Share of expected words found in the transcript (order-insensitive, a sanity check only)."""
    want, have = _words(expected), _words(got)
    pool = list(have)
    hits = 0
    for w in want:
        if w in pool:
            pool.remove(w)
            hits += 1
    return hits / len(want) if want else 1.0


def pct(values: list[float], q: float) -> float:
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[q - 1]


class GpuSampler:
    """Peak GPU memory via nvidia-smi while a block runs (no-op without nvidia-smi)."""

    def __init__(self) -> None:
        self.available = shutil.which("nvidia-smi") is not None
        self.peak_mib: int | None = None
        self._stop = threading.Event()

    def _read(self) -> int | None:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout
            return sum(int(x) for x in out.split())
        except (subprocess.SubprocessError, ValueError):
            return None

    def _loop(self) -> None:
        while not self._stop.is_set():
            if (v := self._read()) is not None:
                self.peak_mib = max(self.peak_mib or 0, v)
            self._stop.wait(0.25)

    def __enter__(self) -> GpuSampler:
        if self.available:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        if self.available:
            self._stop.set()
            self._thread.join()


def host_info() -> list[str]:
    lines = [f"- Host: {platform.node()} ({platform.system()} {platform.release()})"]
    try:
        cpu = next(
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        )
        lines.append(f"- CPU: {cpu}, {os.cpu_count()} logical cores")
        kb = int(Path("/proc/meminfo").read_text().split()[1])
        lines.append(f"- RAM: {kb / 1024 / 1024:.1f} GiB")
    except (OSError, StopIteration, ValueError):
        lines.append(f"- CPU: {platform.processor() or 'unknown'}, {os.cpu_count()} logical cores")
    if shutil.which("nvidia-smi"):
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        lines.append(f"- GPU: {out or 'nvidia-smi failed'}")
    else:
        lines.append("- GPU: none visible to this script (nvidia-smi not found)")
    return lines


def container_memory() -> list[str]:
    if not shutil.which("docker"):
        return []
    out = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [f"- {line}" for line in out.splitlines() if "piper" in line or "whisper" in line]


def run(args: argparse.Namespace) -> int:
    health = _get_json(f"{args.whisper}/healthz")
    voices = _get_json(f"{args.piper}/voices")
    report = [f"# Audio benchmark {time.strftime('%Y-%m-%d %H:%M')}", "", *host_info()]
    report.append(
        f"- Whisper: model `{health.get('model')}`, device `{health.get('device')}`, "
        f"compute `{health.get('compute_type')}`, service concurrency {health.get('concurrency')}"
    )
    report += [
        "",
        "## Piper TTS",
        "",
        "| lang | text | cold s | warm p50 s | warm p95 s | audio s |",
        "|---|---|---|---|---|---|",
    ]

    failures: list[str] = []
    clips: dict[tuple[str, str], bytes] = {}
    runs = 1 if args.smoke else args.runs
    for lang in args.languages:
        case = CASES[lang]
        if case["voice"] not in voices:
            failures.append(f"{lang}: voice {case['voice']} not served by piper")
            continue
        for kind in ("word", "sentence", "paragraph"):
            text = case["sentence"] if kind != "word" else case["word"]
            if kind == "paragraph":
                text = " ".join([text] * 4)
            audio, cold = synthesize(args.piper, case["voice"], text)
            warm = [synthesize(args.piper, case["voice"], text)[1] for _ in range(runs)]
            clips[(lang, kind)] = audio
            report.append(
                f"| {lang} | {kind} | {cold:.2f} | {pct(warm, 50):.2f} | {pct(warm, 95):.2f} | "
                f"{wav_seconds(audio):.1f} |"
            )

    report += [
        "",
        "## Whisper STT",
        "",
        "| lang | clip | parallel | requests | p50 s | p95 s | real-time factor (p50) | accuracy |",
        "|---|---|---|---|---|---|---|---|",
    ]
    levels = [1] if args.smoke else args.concurrency
    with GpuSampler() as gpu:
        for lang in args.languages:
            for kind in ("word", "sentence"):
                audio = clips.get((lang, kind))
                if audio is None:
                    continue
                seconds = wav_seconds(audio)
                transcribe(args.whisper, audio, lang)  # warm-up, not counted
                for parallel in levels:
                    n = runs * parallel
                    with cf.ThreadPoolExecutor(parallel) as pool:
                        futures = [
                            pool.submit(transcribe, args.whisper, audio, lang) for _ in range(n)
                        ]
                        results = [f.result() for f in futures]
                    latencies = [r[1] for r in results]
                    p50, p95 = pct(latencies, 50), pct(latencies, 95)
                    acc = min(accuracy(CASES[lang][kind], r[0]["text"]) for r in results)
                    report.append(
                        f"| {lang} | {kind} ({seconds:.1f} s) | {parallel} | {n} | {p50:.2f} | "
                        f"{p95:.2f} | {p50 / seconds:.2f} | {acc:.0%} |"
                    )
                    if kind == "sentence" and parallel == levels[0] and acc < args.min_accuracy:
                        failures.append(
                            f"{lang}: sentence accuracy {acc:.0%} < {args.min_accuracy:.0%}"
                        )
    report += ["", "## Memory", ""]
    report.append(
        f"- Peak GPU memory used during STT: {gpu.peak_mib} MiB"
        if gpu.available
        else "- GPU: not sampled"
    )
    report += container_memory() or [
        "- Container memory: `docker stats` not available to this script"
    ]
    if failures:
        report += ["", "## Failures", "", *[f"- {f}" for f in failures]]

    text = "\n".join(report) + "\n"
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--piper", default="http://127.0.0.1:5000")
    parser.add_argument("--whisper", default="http://127.0.0.1:9000")
    parser.add_argument("--languages", nargs="+", default=list(CASES), choices=list(CASES))
    parser.add_argument("--runs", type=int, default=5, help="requests per case and parallel level")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--min-accuracy", type=float, default=0.5)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--out", type=Path)
    raise SystemExit(run(parser.parse_args()))


if __name__ == "__main__":
    main()
