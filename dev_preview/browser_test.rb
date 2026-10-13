# Run with the Firefox + Selenium already included in trmnlp.
$LOAD_PATH.unshift('/app/lib')
require 'trmnlp/firefox_driver'
require 'net/http'
require 'json'
require 'fileutils'
require 'time'

def refresh(date: '2026-10-13', scenario: 'family', weather: 'mock')
  uri = URI('http://preview:8080/api/refresh')
  response = Net::HTTP.post(uri, { selected_date: date, scenario:, weather_mode: weather }.to_json,
                           'Content-Type' => 'application/json')
  raise "Refresh failed: #{response.code}" unless response.code == '200'
end

def assert(value, message)
  raise message unless value
end

driver = TRMNLP::FirefoxDriver.build
wait = Selenium::WebDriver::Wait.new(timeout: 15)
out = ENV.fetch('SCREENSHOT_DIR', '/tmp/screenshots')
FileUtils.mkdir_p(out)
begin
  # Production-shaped exchanges still work with no preview metadata/backend.
  native_start = Time.now.strftime('%Y-%m-%d') + 'T10:00:00' + Time.now.strftime('%:z')
  [1, 2, 3].each do |number|
    payload = { "source_#{number}" => [{ 'events' => [{ 'summary' => "Native source #{number}", 'start_at' => native_start, 'location' => '' }] }] }
    response = Net::HTTP.post(URI('http://renderer:4567/render'), payload.to_json,
                             'Content-Type' => 'application/json')
    assert(response.code == '200' && response.body.include?("Native source #{number}"), "Native source #{number} compatibility failed")
    assert(response.body.include?('screen screen--og') && response.body.include?('view view--full'), 'Required Terminus wrappers missing')
  end
  refresh
  driver.bidi.send_cmd('browsingContext.setViewport', context: driver.window_handle,
                       viewport: { width: 800, height: 480 })
  driver.navigate.to('http://preview:8080/preview')
  wait.until { driver.execute_script('return document.fonts.status === "loaded"') }
  assert(driver.execute_script('return [...document.fonts].some(font => font.family === "Manrope" && font.status === "loaded")'), 'Embedded Manrope did not load')
  assert(driver.find_element(css: '.pc-day').text == 'Tuesday', 'Simulated weekday failed')
  assert(driver.find_element(css: '.pc-date').text == '13 October', 'Simulated date failed')
  assert(driver.find_elements(css: '.pc-event').length == 4, 'Expected four Today cards')
  assert(driver.find_elements(css: '.pc-all-day').length == 1, 'All-day classification failed')
  assert(driver.find_elements(css: '.pc-week-card').length == 3, 'Later this week missing')
  assert(driver.find_elements(css: '.pc-forecast-icon svg').length == 3, 'Forecast icons missing')
  sizes = driver.execute_script('return [document.querySelector(".pc").getBoundingClientRect().width, document.querySelector(".pc").getBoundingClientRect().height, window.innerWidth, window.innerHeight]')
  assert(sizes == [800, 480, 800, 480], "Wrong canvas: #{sizes}")
  assert(driver.execute_script('return getComputedStyle(document.querySelector(".pc-all-day")).backgroundColor') == 'rgb(170, 170, 170)', 'All-day grey styling failed')
  assert(driver.execute_script('return getComputedStyle(document.querySelector(".pc-event-inner")).justifyContent') == 'center', 'Event centring failed')
  # All browser subresources must be local, including fonts.
  resources = driver.execute_script('return performance.getEntriesByType("resource").map(e => e.name)')
  assert(resources.all? { |url| url.start_with?('http://preview:8080/') }, "External browser requests: #{resources}")
  driver.save_screenshot("#{out}/mock-preview.png")
  assert(File.binread('/plugin/docs/mock-preview.png') == File.binread("#{out}/mock-preview.png"), 'Mock screenshot differs from committed baseline; inspect the artifact before updating docs/mock-preview.png')
  # Repeat the exact fixture and assert the pixels remain deterministic.
  driver.navigate.refresh
  wait.until { driver.execute_script('return document.fonts.status === "loaded"') }
  driver.save_screenshot("#{out}/mock-repeat.png")
  assert(File.binread("#{out}/mock-preview.png") == File.binread("#{out}/mock-repeat.png"), 'Repeated mock screenshot changed')

  # Count across sources, including all-day events, and reserve real space for overflow.
  [[4, 3, 0], [7, 6, 0], [7, 6, 5]].each do |today_count, later_count, all_day_count|
    events = Array.new(today_count) do |i|
      { summary: "Today event #{i + 1}", start_at: "2026-10-13T#{format('%02d', i + 8)}:00:00+01:00", all_day: i < all_day_count, location: '' }
    end
    events += Array.new(later_count) do |i|
      { summary: "Later event #{i + 1}", start_at: "2026-10-14T#{format('%02d', i + 8)}:00:00+01:00", location: '' }
    end
    payload = { source_1: [{ events: events.take(2) }], source_2: [{ events: events.drop(2) }],
                preview_now: '2026-10-13T00:00:00+01:00', preview_week_end: '2026-10-19T00:00:00+01:00' }
    response = Net::HTTP.post(URI('http://renderer:4567/render'), payload.to_json, 'Content-Type' => 'application/json')
    assert(response.code == '200', 'Overflow fixture render failed')
    driver.execute_script('document.open(); document.write(arguments[0]); document.close();', response.body)
    wait.until { driver.execute_script('return document.fonts.status === "loaded"') }
    assert(driver.find_elements(css: '.pc-event').length == 4, 'Today card limit changed')
    assert(driver.find_elements(css: '.pc-week-card').length == 3, 'Upcoming card limit changed')
    if today_count == 4
      assert(driver.find_elements(css: '.pc-more').empty?, 'Overflow shown at exact capacity')
    else
      assert(driver.find_element(css: '.pc-today-more').text == '+3 more', 'Today hidden count incorrect')
      assert(driver.find_element(css: '.pc-later-more').text == '+3 more', 'Upcoming hidden count incorrect')
      assert(driver.find_element(css: '.pc-footer-left').text.include?('7 events today'), 'Footer must count all Today events')
      assert(driver.execute_script('const more=document.querySelector(".pc-today-more").getBoundingClientRect(); const cards=[...document.querySelectorAll(".pc-event")]; return more.top >= cards.at(-1).getBoundingClientRect().bottom && more.bottom <= document.querySelector(".pc-footer").getBoundingClientRect().top;'), 'Today overflow overlaps cards or footer')
    end
  end

  refresh(date: '2026-10-16')
  driver.navigate.refresh
  assert(driver.find_element(css: '.pc-day').text == 'Friday', 'Date change failed')
  assert(driver.find_elements(css: '.pc-event-title').any? { |e| e.text.include?('Continues: Overnight travel') }, 'Cross-midnight continuation missing')
  refresh(date: '2026-10-25', scenario: 'autumn-dst')
  driver.navigate.refresh
  assert(driver.find_elements(css: '.pc-event').length == 3, 'DST occurrences missing')
  refresh(scenario: 'empty', weather: 'disabled')
  driver.navigate.refresh
  assert(driver.find_element(css: '.pc-empty').text == 'No events today', 'Empty state missing')
  assert(driver.find_element(css: '.pc-weather-condition').text == 'Weather unavailable', 'Disabled weather missing')

  # Exercise actual dashboard controls and its iframe, including simulation.
  refresh
  driver.bidi.send_cmd('browsingContext.setViewport', context: driver.window_handle,
                       viewport: { width: 1100, height: 850 })
  driver.navigate.to('http://preview:8080/')
  wait.until { driver.find_element(id: 'diagnostics').text.include?('event_count') }
  assert(driver.execute_script('return getComputedStyle(document.getElementById("screen")).filter.includes("four-shades")'), 'Permanent four-shade simulation missing')
  driver.switch_to.frame(driver.find_element(id: 'screen'))
  wait.until { driver.find_elements(css: '.pc-event').length == 4 }
  driver.switch_to.default_content
  driver.save_screenshot("#{out}/dashboard.png")
  puts 'Native Firefox layout, controls, offline assets and deterministic screenshot checks passed.'
ensure
  driver.quit
end
