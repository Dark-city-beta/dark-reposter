import unittest

from dark_reposter.text_adapt import adapt_for_platform, remove_control_tags, target_platforms


class TextAdaptTests(unittest.IsolatedAsyncioTestCase):
    def test_remove_control_tags(self):
        self.assertNotIn("#noauto", remove_control_tags("hello #noauto"))

    def test_target_platforms_xonly(self):
        self.assertEqual(target_platforms("hello #xonly", ["x", "linkedin"]), ["x"])

    async def test_adapt_fits_limit(self):
        text = " ".join(["Очень длинный текст"] * 80)
        result = await adapt_for_platform(text, "x", 280)
        self.assertLessEqual(len(result), 280)

    async def test_preserves_url_and_rich_content(self):
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
            adapted = await adapt_for_platform(post, platform, limit)
            self.assertLessEqual(len(adapted), limit)
            self.assertIn("https://github.com/Dark-city-beta/dark-reposter", adapted)
            if platform == "mastodon":
                self.assertGreater(len(adapted), 350, "Mastodon should utilize its 500-char budget richly")

    async def test_user_photoshoot_post_adaptation(self):
        post = """Neural Networks vs. Expensive Optics: An Experiment at MUZA Studio

A persistent myth in production claims that high-end shots require camera gear worth thousands of dollars. In 2026, AI tools erase this barrier.

I tested this hypothesis at Uncle Valera's photo project (https://t.me/vartinnert1) at MUZA Studio (https://muzaphoto.ru/) on the "Vampire Castle" set. To keep the tone light, I joined as the satirical persona "François Jos Pen from Bataysia."

The core hypothesis:

Shooting on basic gear. A vintage point-and-shoot or standard smartphone is plenty. The focus stays on composition and directing models.

AI post-processing. Retouching, color grading, fine details, and effects are delegated to neural networks and precise prompts.

Raw assets are gathered. Next up, I will break down the pipeline: turning noisy compact-camera frames into magazine-grade visuals, with prompts and before/after comparisons."""

        for platform, limit in [("x", 280), ("bluesky", 300), ("mastodon", 500)]:
            adapted = await adapt_for_platform(post, platform, limit)
            self.assertLessEqual(len(adapted), limit)
            # Never leave broken URL brackets or stray parenthesis in CTA link
            self.assertNotIn("( at MUZA Studio", adapted)
            self.assertNotIn("🔗 https://t.me/vartinnert1)", adapted)
            # Never leave isolated stubs without explanation
            self.assertNotIn("Shooting on basic gear.\n\nAI post-processing.", adapted)
            self.assertNotIn("Shooting on basic gear.\n\n🔗", adapted)
            # Must preserve the main headline and thesis
            self.assertIn("Neural Networks vs. Expensive Optics", adapted)
            self.assertIn("A persistent myth in production", adapted)

    def test_positive_platform_routing(self):
        all_platforms = ["x", "bluesky", "mastodon", "threads", "linkedin"]
        # Single positive tag
        self.assertEqual(target_platforms("Hello world #x", all_platforms), ["x"])
        self.assertEqual(target_platforms("Hello world #bsky", all_platforms), ["bluesky"])
        self.assertEqual(target_platforms("Hello world #masto", all_platforms), ["mastodon"])
        self.assertEqual(target_platforms("Hello world #threads", all_platforms), ["threads"])
        self.assertEqual(target_platforms("Hello world #in", all_platforms), ["linkedin"])

        # Multiple positive tags
        self.assertEqual(
            target_platforms("Multi post #bsky #masto", all_platforms),
            ["bluesky", "mastodon"],
        )

        # Positive + Negative conflict (negative wins)
        self.assertEqual(
            target_platforms("Post #x #bsky #nox", all_platforms),
            ["bluesky"],
        )

        # No positive tags: all configured platforms except negative
        self.assertEqual(
            target_platforms("General post #nomastodon", all_platforms),
            ["x", "bluesky", "threads", "linkedin"],
        )

    def test_strip_control_tags_at_tail_only(self):
        text = "Talking about #x and #bsky features in this post.\n\n#masto"
        cleaned = remove_control_tags(text)
        # Body mention of #x and #bsky should be preserved
        self.assertIn("#x", cleaned)
        self.assertIn("#bsky", cleaned)
        # Tail routing tag #masto should be removed
        self.assertNotIn("#masto", cleaned)


if __name__ == "__main__":
    unittest.main()


