# frozen_string_literal: true

require "date"
require "time"

module PaperCalendar
  # Prototype for Terminus after Source.from_calendar has parsed text/calendar.
  #
  # Terminus already supplies an array of calendar hashes. This class deliberately
  # DOES NOT fetch URLs or execute arbitrary scripts. It handles single occurrences
  # only; recurring entries require a proper RFC 5545 recurrence engine before release.
  class Normalizer
    def initialize(timezone: "+01:00", today: Date.today, days: 7)
      raise ArgumentError, "days must be 1..31" unless (1..31).cover?(days)
      @timezone = timezone
      @today = today
      @days = days
    end

    def call(calendars)
      raise ArgumentError, "expected parsed calendar array" unless calendars.is_a?(Array)

      events = []
      skipped_recurring = 0

      calendars.each do |calendar|
        Array(calendar.fetch(:events, calendar.fetch("events", []))).each do |event|
          event = event.transform_keys(&:to_s)
          if Array(event["recurrence_rule"]).any? || Array(event["recurrences"]).any? ||
             Array(event["exceptions"]).any? || !event["recurrence_id"].to_s.empty?
            skipped_recurring += 1
            next
          end

          start_value = event["start_at"].to_s
          next if start_value.empty?

          all_day = start_value.match?(/\A\d{4}-\d{2}-\d{2}\z/)
          started = all_day ? Date.iso8601(start_value) : Time.iso8601(start_value).getlocal(@timezone).to_date
          next unless (@today...(@today + @days)).cover?(started)

          events << {
            title: event["summary"].to_s.empty? ? "Untitled event" : event["summary"].to_s,
            date: started.iso8601,
            time: all_day ? "All day" : Time.iso8601(start_value).getlocal(@timezone).strftime("%H:%M"),
            all_day: all_day
          }
        rescue Date::Error, ArgumentError, TypeError
          next # Invalid event does not cause an entire calendar to fail.
        end
      end

      events.sort_by! { |e| [e[:date], e[:all_day] ? 0 : 1, e[:time], e[:title]] }
      {
        today: events.select { |e| e[:date] == @today.iso8601 },
        week: events.reject { |e| e[:date] == @today.iso8601 }.map do |e|
          {day: Date.iso8601(e[:date]).strftime("%A"), title: e[:title]}
        end,
        warnings: {skipped_recurring_events: skipped_recurring}
      }
    end
  end
end
