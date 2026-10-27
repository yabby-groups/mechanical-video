# TripoSR optional compatibility assessment

Host is macOS arm64, M3, 16GB unified memory. Upstream VAST-AI-Research/TripoSR README and requirements were fetched on 2026-10-27. Upstream documents ~6GB VRAM for a default single-image run and CUDA/PyTorch version coupling. Its torchmcubes native extension and texture/rasterization dependencies require platform-specific verification. This is not evidence of working Apple Metal inference.

Status: **not runtime-validated on this host, disabled**. No weights or heavyweight runtime were installed. No claim of ARM64 compatibility is made. To enable later, create a separate project-local environment, build/import every native extension, execute a real input on CPU/MPS within the memory budget, and record timings/output. Never run it concurrently with Blender. Whole-object reconstructions cannot replace independently modeled mechanical parts.

The baseline CAD → Blender → H.264 path has no TripoSR dependency.
