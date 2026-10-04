# Target hardware and audio sizing

Status: **not measured yet.** The model choice and limits below are starting values until
`scripts/bench_audio.py` has been run on the target machine (plan P0/P3).

## Target machine (reported by the owner, 2026-10-04)

| part | value |
|---|---|
| CPU | AMD, model not yet recorded |
| RAM | 64 GB |
| GPU | NVIDIA, 12 GB VRAM |
| Disk | at least 500 GB |
| Host OS | not yet recorded (GPU containers need the NVIDIA Container Toolkit on Linux, or Docker Desktop + WSL2 on Windows) |
| Learners | up to 5 profiles, rarely practising at the same time |

The 12 GB of VRAM will be shared between Whisper and the local LLM planned for P4, so the
benchmark records peak GPU memory per Whisper model.

## Starting configuration

| setting | value | why |
|---|---|---|
| `WHISPER_MODEL` | `small` (CPU) / `large-v3-turbo` candidate (GPU) | to be decided from the benchmark |
| `WHISPER_DEVICE` | `auto` (CUDA when visible, else CPU) | CPU keeps working on machines without a GPU |
| `WHISPER_MAX_SECONDS` | 30 | a drill answer is a word or a sentence |
| `WHISPER_MAX_UPLOAD_BYTES` | 5 MiB | about 30 s of compressed browser audio with margin |
| `WHISPER_CONCURRENCY` | 1 | requests queue instead of competing for the GPU/CPU |

## How to measure

```sh
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile audio up -d --build
nvidia-smi                     # on the host: the GPU is visible
curl -s localhost:9000/healthz # "device": "cuda"
python3 scripts/bench_audio.py --out docs/bench/$(hostname)-small-$(date +%F).md

# repeat per candidate model, e.g.
WHISPER_MODEL=large-v3-turbo docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile audio up -d
python3 scripts/bench_audio.py --out docs/bench/$(hostname)-large-v3-turbo-$(date +%F).md
```

Run the script on the host itself (it reads `nvidia-smi`, `/proc` and `docker stats`). Commit the
reports under `docs/bench/` and fill in the decision below.

## Decision (after measuring)

- Whisper model and device: _pending_
- p95 target for single-word speaking feedback: proposed 2 s with 2 parallel learners, _pending_
- Concurrency and limits: _pending_
