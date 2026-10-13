# Cache the official Framework CSS and its fonts during image build.
require 'net/http'
require 'uri'
require 'fileutils'
require 'digest'

def download(url, remaining = 4)
  raise 'Asset redirect limit exceeded' if remaining.zero?
  uri = URI(url)
  raise 'HTTPS asset required' unless uri.scheme == 'https'
  response = Net::HTTP.get_response(uri)
  return download(URI.join(url, response['location']).to_s, remaining - 1) if response.is_a?(Net::HTTPRedirection)
  raise "Asset download failed: #{response.code}" unless response.is_a?(Net::HTTPSuccess)
  response.body
end

base = 'https://trmnl.com/css/3.2.0/plugins.css'
FileUtils.mkdir_p('/preview/assets')
css = download(base).gsub(/url\(['"]?([^)'"\s]+)['"]?\)/) do |match|
  reference = Regexp.last_match(1)
  next match if reference.start_with?('data:', '#')
  url = URI.join(base, reference).to_s
  filename = Digest::SHA256.hexdigest(url)[0, 20] + File.extname(URI(url).path)
  File.binwrite("/preview/assets/#{filename}", download(url))
  "url('/assets/#{filename}')"
end
File.write('/preview/assets/plugins.css', css)
