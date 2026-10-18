"""Export the deterministic browser storyboard to H.264 MP4. No live model calls.

Start the app/static server first, then:
uv run --with playwright --with imageio-ffmpeg python scripts/export_animation.py
"""

import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8088/animation.html")
    parser.add_argument("--fps", type=int, default=24, choices=[12, 24, 30])
    parser.add_argument("--output", type=Path, default=Path("web/media/tracework-flow.mp4"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-loglevel",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "-framerate",
        str(args.fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1344, "height": 1100}, device_scale_factor=1)
        page.goto(args.url)
        expect(page.locator("#chapters button")).to_have_count(8)
        # 1280 × 720 at the existing responsive 16:9 stage.
        page.add_style_tag(
            content="main{max-width:none;padding:0}"
            "#stage{position:fixed;left:0;top:0;width:1280px;height:720px;"
            "border:0;border-radius:0}"
        )
        stage = page.locator("#stage")
        assert stage.bounding_box()["width"] == 1280
        assert stage.bounding_box()["height"] == 720
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            try:
                for frame in range(48 * args.fps):
                    ms = frame * 1000 / args.fps
                    page.evaluate("ms => window.traceworkAnimation.seek(ms)", ms)
                    encoder.stdin.write(stage.screenshot(animations="disabled"))
                    if frame % (6 * args.fps) == 0:
                        print(f"Scene {frame // (6 * args.fps) + 1}/8", flush=True)
                encoder.stdin.close()
                if encoder.wait() != 0:
                    raise RuntimeError("Video encoding failed")
            except BaseException:
                encoder.kill()
                raise
        page.evaluate("window.traceworkAnimation.seek(15000)")
        poster = Path("docs/images/animation.png")
        poster.parent.mkdir(parents=True, exist_ok=True)
        stage.screenshot(path=str(poster))
        browser.close()
    print(f"Exported {args.output}: 1280x720, 48 seconds, {args.fps} fps, silent H.264.")


if __name__ == "__main__":
    main()
