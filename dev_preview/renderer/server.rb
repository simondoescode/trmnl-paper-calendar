# Use the installed trmnlp renderer, filters and config, never a second Liquid engine.
$LOAD_PATH.unshift('/app/lib')
require 'trmnlp'
require 'sinatra/base'

class PreviewRenderer < Sinatra::Base
  set :bind, '0.0.0.0'
  set :port, 4567
  set :public_folder, '/preview'
  set :host_authorization, { permitted_hosts: ['renderer', 'localhost', '127.0.0.1'] }
  set :show_exceptions, false

  post '/render' do
    halt 413 if request.content_length.to_i > 100_000
    payload = JSON.parse(request.body.read(100_001))
    context = TRMNLP::Context.new('/plugin', cache_dir: '/tmp/preview-cache', source_data: payload)
    page = context.renderer.render_full_page('full', screen_classes: 'screen screen--og')
    # The plugin carries the wrappers required by Terminus. Remove trmnlp's
    # additional wrapper so the same markup occupies exactly one device canvas.
    page.sub!(/<div class="screen[^\"]*">\s*<div class="view view--full">/, '')
    page.sub!(/\s*<\/div>\s*<\/div>\s*<\/body>/, '</body>')
    # This layout uses CSS/SVG, no framework JS. Remove external font/CDN calls.
    page.gsub!(/<link[^>]*>/, '')
    page.gsub!(/<script[^>]*src=[^>]*><\/script>/, '')
    page.sub!('</head>', '<link rel="stylesheet" href="/assets/plugins.css"><style>html,body{margin:0;width:800px;height:480px;overflow:hidden}.screen.screen--og,.view.view--full{padding:0;margin:0;width:800px;height:480px}</style></head>')
    content_type 'text/html', charset: 'utf-8'
    page
  rescue StandardError
    halt 422, 'Native preview rendering failed'
  end

  get('/health') { 'ok' }
  run! if app_file == $PROGRAM_NAME
end
