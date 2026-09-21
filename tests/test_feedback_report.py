"""Tests the pain and the intensity fields of a feedback log."""

import unittest

import pydantic

from main import FeedbackLog


def log_with(**extra):
    return FeedbackLog(
        log_id="S01",
        filename="left_hand.svg",
        feedbackLocation={"chosenPoints": {"row": [], "col": []}},
        **extra,
    )


class FeedbackReportTests(unittest.TestCase):
    def test_a_sensation_carries_the_pain_and_the_intensity(self):
        log = log_with(felt=True, pain=True, intensity=7)
        self.assertTrue(log.pain)
        self.assertEqual(log.intensity, 7)

    def test_a_painting_without_a_report_leaves_both_unset(self):
        log = log_with()
        self.assertIsNone(log.pain)
        self.assertIsNone(log.intensity)

    def test_nothing_felt_carries_the_pain_without_an_intensity(self):
        log = log_with(felt=False, pain=True, intensity=None)
        self.assertTrue(log.pain)
        self.assertIsNone(log.intensity)

    def test_an_intensity_above_ten_is_refused(self):
        with self.assertRaises(pydantic.ValidationError):
            log_with(intensity=11)

    def test_an_intensity_below_zero_is_refused(self):
        with self.assertRaises(pydantic.ValidationError):
            log_with(intensity=-1)


if __name__ == "__main__":
    unittest.main()
