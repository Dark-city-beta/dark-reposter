import unittest

from dark_reposter.text_adapt import adapt_for_platform, remove_control_tags, target_platforms


class TextAdaptTests(unittest.TestCase):
    def test_remove_control_tags(self):
        self.assertNotIn("#noauto", remove_control_tags("hello #noauto"))

    def test_target_platforms_xonly(self):
        self.assertEqual(target_platforms("hello #xonly", ["x", "linkedin"]), ["x"])

    def test_adapt_fits_limit(self):
        text = " ".join(["Очень длинный текст"] * 80)
        result = adapt_for_platform(text, "x", 280)
        self.assertLessEqual(len(result), 280)


if __name__ == "__main__":
    unittest.main()
