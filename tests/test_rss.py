"""Tests for RSS feed parsing."""
import pytest
from app.services.rss import fetch_feed, _extract_mp3_url, _parse_duration, ParsedEpisode

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Test Podcast</title>
    <item>
      <title>Episode 1: Hello World</title>
      <guid>ep-001</guid>
      <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
      <itunes:duration>45:30</itunes:duration>
      <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" length="12345678"/>
      <description>Show notes for episode 1.</description>
    </item>
    <item>
      <title>Episode 2: Special Characters: Colon &amp; "Quotes"</title>
      <guid>ep-002</guid>
      <pubDate>Mon, 08 Jan 2024 12:00:00 +0000</pubDate>
      <itunes:duration>1:02:15</itunes:duration>
      <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg" length="99999999"/>
    </item>
    <item>
      <title>No Audio Item</title>
      <guid>no-audio</guid>
    </item>
  </channel>
</rss>"""


def test_fetch_feed_from_string(tmp_path):
    """Test feed parsing from a file URL."""
    feed_file = tmp_path / "feed.xml"
    feed_file.write_text(SAMPLE_RSS)
    episodes = fetch_feed(str(feed_file))

    assert len(episodes) == 2  # No-audio item excluded
    assert episodes[0].guid == "ep-001"
    assert episodes[0].title == "Episode 1: Hello World"
    assert episodes[0].mp3_url == "https://example.com/ep1.mp3"
    assert episodes[0].duration_secs == 45 * 60 + 30


def test_parse_duration_formats():
    assert _parse_duration(type("E", (), {"itunes_duration": "45:30"})()) == 2730
    assert _parse_duration(type("E", (), {"itunes_duration": "1:02:15"})()) == 3735
    assert _parse_duration(type("E", (), {"itunes_duration": "3600"})()) == 3600


def test_special_chars_in_title(tmp_path):
    feed_file = tmp_path / "feed.xml"
    feed_file.write_text(SAMPLE_RSS)
    episodes = fetch_feed(str(feed_file))
    ep2 = next(e for e in episodes if e.guid == "ep-002")
    assert "Colon" in ep2.title
    assert ep2.duration_secs == 3600 + 2 * 60 + 15
