import unittest

from dark_reposter.text_adapt import adapt_for_platform, remove_control_tags, target_platforms


class TextAdaptTests(unittest.TestCase):
    def test_remove_control_tags(self):
        self.assertNotIn("#noauto", remove_control_tags("hello #noauto"))
        self.assertNotIn("#xonly", remove_control_tags("test #xonly message"))

    def test_target_platforms_xonly(self):
        self.assertEqual(target_platforms("hello #xonly", ["x", "linkedin"]), ["x"])

    def test_adapt_fits_limit(self):
        text = " ".join(["Очень длинный текст"] * 80)
        result = adapt_for_platform(text, "x", 280)
        self.assertLessEqual(len(result), 280)

    def test_preserves_url_and_rich_content(self):
        post = """🛰️ Breaking out of the walled garden: Meet DARK Reposter!

Telegram is great for tech blogs, but staying only here keeps us in an echo chamber while the open web thrives on X (Twitter), Bluesky, and Mastodon.

Manual copy-pasting is a pain. That’s why we built and open-sourced DARK Reposter.

⚡️ How it works:
Post in your Telegram channel — the bot instantly adapts and broadcasts it to all your socials via the Buffer GraphQL API.

🔥 Features:
• Smart Adaptation: Fits text limits for X (280c), Bluesky (300c), and Mastodon (500c).
• Zero-Config Media: Photos & albums sent via Telegram CDN (no public IP or proxy needed).

⭐️ GitHub: https://github.com/Dark-city-beta/dark-reposter

#opensource #python #telegram #bluesky #twitter #mastodon"""

        for platform, limit in [("x", 280), ("bluesky", 300), ("mastodon", 500)]:
            adapted = adapt_for_platform(post, platform, limit)
            self.assertLessEqual(len(adapted), limit)
            self.assertIn("https://github.com/Dark-city-beta/dark-reposter", adapted)
            if platform == "mastodon":
                self.assertGreater(len(adapted), 350, "Mastodon should utilize its 500-char budget richly")


if __name__ == "__main__":
    unittest.main()
