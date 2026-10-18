"""Optional browser smoke check. Start the app first; see --help for replay checks."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--replay", action="store_true")
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
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#document-select").select_option("atlas-launch")
        page.locator("#review-button").click()
        expect(page.locator("#review-status")).to_contain_text("Awaiting")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(shots / "mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    print(
        "Browser checks passed: review, evidence, approval/rejection, export, navigation, mobile."
    )


if __name__ == "__main__":
    main()
