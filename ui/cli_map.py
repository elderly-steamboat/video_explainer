"""Pure mapping from (step, options) to a CLI argv list. No I/O."""
import sys

STEPS = ["script", "narration", "scenes", "voiceover", "storyboard", "render"]

# UI label -> (render --resolution value, add --short)
RESOLUTION_PRESETS = {
    "4K": ("4k", False),
    "1080p": ("1080p", False),
    "720p": ("720p", False),
    "Vertical 1080": ("1080p", True),
    "Vertical 720": ("720p", True),
}


def build_argv(step: str, project: str, options: dict) -> list[str]:
    """Return the argv list to run a pipeline step for a project."""
    if step not in STEPS:
        raise ValueError(f"Unknown step: {step}")
    argv = [sys.executable, "-m", "src.cli", step, project]

    if step == "script":
        if options.get("url"):
            argv += ["--url", options["url"]]
        elif options.get("input"):
            argv += ["-i", options["input"]]
        if options.get("mock"):
            argv += ["--mock"]
    elif step in ("narration", "scenes"):
        if options.get("force"):
            argv += ["--force"]
        if step == "narration" and options.get("mock"):
            argv += ["--mock"]
    elif step == "voiceover":
        if options.get("provider"):
            argv += ["--provider", options["provider"]]
    elif step == "render":
        label = options.get("resolution", "1080p")
        value, is_short = RESOLUTION_PRESETS.get(label, ("1080p", False))
        argv += ["--resolution", value]
        if is_short:
            argv += ["--short"]
        if options.get("fast"):
            argv += ["--fast"]
        if options.get("concurrency"):
            argv += ["--concurrency", str(options["concurrency"])]

    return argv
