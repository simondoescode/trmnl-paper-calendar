# frozen_string_literal: true

require "minitest/autorun"
require_relative "normalizer"

class NormalizerTest < Minitest::Test
  def setup
    @normalizer = PaperCalendar::Normalizer.new(today: Date.new(2026, 10, 10), timezone: "+01:00")
  end

  def test_empty
    assert_equal [], @normalizer.call([])[:today]
  end

  def test_sorts_all_day_before_timed
    result = @normalizer.call([{events: [
      {summary: "School run", start_at: "2026-10-10T08:30:00+01:00"},
      {summary: "Birthday", start_at: "2026-10-10"}
    ]}])
    assert_equal ["Birthday", "School run"], result[:today].map { |e| e[:title] }
  end

  def test_local_date_conversion
    result = @normalizer.call([{events: [
      {summary: "Late event", start_at: "2026-10-09T23:30:00Z"}
    ]}])
    assert_equal "00:30", result[:today].first[:time]
  end

  def test_excludes_far_future
    result = @normalizer.call([{events: [
      {summary: "Next month", start_at: "2026-11-15T10:00:00Z"}
    ]}])
    assert_empty result[:week]
  end

  def test_explicitly_skips_recurring_until_expansion_exists
    result = @normalizer.call([{events: [
      {summary: "Weekly class", start_at: "2026-10-10T09:00:00Z",
       recurrence_rule: [{"frequency" => "WEEKLY"}]}
    ]}])
    assert_empty result[:today]
    assert_equal 1, result[:warnings][:skipped_recurring_events]
  end
end
