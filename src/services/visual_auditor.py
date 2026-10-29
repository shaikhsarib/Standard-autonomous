import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class VisualAuditor:
    """
    Headless browser visual auditor inspired by Chrome DevTools Protocol / REA.
    Uses Playwright to capture authentic mobile viewport screenshots and verify rendering.
    """

    def __init__(self, output_dir: str = "data/screenshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture_mobile_snapshot(self, url: str, lead_id: str, timeout_ms: int = 10000) -> Optional[str]:
        """
        Captures a realistic mobile viewport screenshot of the prospect's site.
        Returns the relative file path to the saved screenshot, or None on failure.
        """
        if not url:
            return None

        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        filename = f"{lead_id}.png"
        filepath = self.output_dir / filename

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                # Emulate modern mobile device (iPhone 14 / modern smartphone)
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=2,
                    is_mobile=True,
                    has_touch=True,
                    user_agent=(
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                    )
                )
                page = context.new_page()
                page.set_default_timeout(timeout_ms)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    # Brief settling time for animations/fonts
                    page.wait_for_timeout(1000)
                    page.screenshot(path=str(filepath), full_page=False)
                    logger.info(f"Captured visual audit screenshot for {url} -> {filepath}")
                    return f"data/screenshots/{filename}"
                except Exception as page_err:
                    logger.warning(f"Failed to navigate to {url} during visual audit: {page_err}")
                    return None
                finally:
                    browser.close()

        except Exception as e:
            logger.warning(f"Playwright screenshot capture unavailable or failed: {e}")
            return None

visual_auditor = VisualAuditor()
