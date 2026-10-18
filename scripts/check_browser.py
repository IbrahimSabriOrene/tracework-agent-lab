"""Optional browser smoke check. Start the app first; see --help for replay checks."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--pdf", action="store_true", help="Exercise a real prepared MinerU worker")
    args = parser.parse_args()
    shots = Path("docs/images")
    shots.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#mode-banner")).to_contain_text(
            "Interactive replay" if args.replay else "Local application"
        )
        page.locator("#review-button").click()
        expect(page.locator("#review-status")).to_contain_text("Awaiting")
        expect(page.locator(".finding")).to_have_count(3)
        page.locator(".evidence-link").first.click()
        expect(page.locator(".source-line.highlighted")).to_have_count(1)
        page.locator("#trace-panel").evaluate("element => element.open = true")
        page.screenshot(
            path=str(shots / ("replay.png" if args.replay else "workspace.png")), full_page=True
        )
        page.locator("#approve-button").click()
        expect(page.locator("#review-status")).to_contain_text(
            "Replay report ready" if args.replay else "Published locally"
        )
        with page.expect_download() as download:
            page.locator("#download-button").click()
        assert download.value.suggested_filename == "tracework-review.json"
        page.locator("#document-select").select_option("cedar-handoff")
        page.locator("#review-button").click()
        expect(page.locator(".finding")).to_have_count(2)
        page.locator("#reject-button").click()
        expect(page.locator("#review-status")).to_contain_text("rejected")
        page.get_by_role("button", name="Harness experiments", exact=True).click()
        expect(page.locator(".metric")).to_have_count(2)
        if args.replay:
            page.locator("#experiment-button").click()
            expect(page.locator("#experiment-results")).to_contain_text("Recorded experiment")
        page.screenshot(path=str(shots / "experiments.png"), full_page=True)
        page.get_by_role("button", name="How it works", exact=True).click()
        expect(page.locator("#guide-view")).to_be_visible()
        page.get_by_role("button", name="Review workspace", exact=True).click()
        if not args.replay:
            page.locator("#edit-toggle").click()
            page.locator("#document-editor").fill(
                '# Test document\nOwner: TBD. <img src=x onerror="window.injected=true">'
            )
            page.locator("#edit-toggle").click()
            page.locator("#review-button").click()
            expect(page.locator("#review-status")).to_contain_text("Awaiting")
            assert page.evaluate("window.injected === undefined")
        if args.replay:
            expect(page.locator("#pdf-import-button")).to_be_disabled()
            expect(page.locator("#pdf-file")).to_be_disabled()
        if args.pdf:
            assert not args.replay, "PDF OCR requires the local application"
            expect(page.locator("#pdf-import-button")).to_be_enabled()
            sample = Path(__file__).resolve().parent.parent / "web/samples/atlas-scan.pdf"
            page.locator("#pdf-file").set_input_files(sample)
            with page.expect_response(
                lambda response: response.url.endswith("/api/pdf/extract"), timeout=610000
            ) as extraction:
                page.locator("#pdf-import-button").click()
            assert extraction.value.status == 201, extraction.value.text()
            expect(page.locator("#pdf-status")).to_contain_text("Check the text")
            expect(page.locator("#source-kind")).to_have_text("Local PDF")
            expect(page.locator("#source-provenance")).to_contain_text("MinerU 4.0.12")
            page.locator("#review-button").click()
            expect(page.locator("#review-status")).to_contain_text("Awaiting")
            expect(page.locator(".finding")).to_have_count(3)
            page.locator(".evidence-link").first.click()
            page.screenshot(path=str(shots / "pdf-import.png"), full_page=True)
            page.locator("#approve-button").click()
            expect(page.locator("#review-status")).to_contain_text("Published locally")
            with page.expect_download() as download:
                page.locator("#download-button").click()
            assert download.value.suggested_filename == "tracework-review.json"
            report = json.loads(Path(download.value.path()).read_text("utf-8"))
            assert report["source"]["parser_version"] == "4.0.12"
            assert report["source"]["local_only"] and not report["source"]["text_edited"]
            assert len(report["source"]["pdf_sha256"]) == 64
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#document-select").select_option("atlas-launch")
        page.locator("#review-button").click()
        expect(page.locator("#review-status")).to_contain_text("Awaiting")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(shots / "mobile.png"), full_page=True)
        page.goto(args.url.rstrip("/") + "/animation.html")
        expect(page.locator("#chapters button")).to_have_count(8)
        page.set_viewport_size({"width": 1440, "height": 1100})
        for index in range(8):
            page.locator("#chapters button").nth(index).click()
            assert page.evaluate("window.traceworkAnimation.position") == index * 6000
            overflow = page.locator("#film").evaluate(
                "svg => [...svg.querySelectorAll('text')].filter(t => {"
                "const b=t.getBBox(); return b.x<0 || b.x+b.width>1600;"
                "}).map(t => t.textContent)"
            )
            assert not overflow, overflow
        page.locator("#restart").click()
        page.locator("#play").click()
        expect(page.locator("#time")).to_have_text("00:01 / 00:48")
        page.locator("#play").click()
        assert not page.evaluate("window.traceworkAnimation.playing")
        page.locator("#timeline").fill("33000")
        expect(page.locator("#scene-description")).to_contain_text("Harness²")
        assert page.evaluate("window.traceworkAnimation.position") == 33000
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.emulate_media(reduced_motion="reduce")
        page.goto(args.url.rstrip("/") + "/animation.html?autoplay=1")
        assert not page.evaluate("window.traceworkAnimation.playing")
        assert not errors, errors
        browser.close()
    print(
        "Browser checks passed: review, evidence, decisions, export, navigation, mobile, animation."
    )


if __name__ == "__main__":
    main()
