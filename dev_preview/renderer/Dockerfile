FROM trmnl/trmnlp@sha256:e5b0505fdbefd86a305b1eea207bde086494f7753c43271680f9d2de966e5d61
USER root
COPY cache_assets.rb /preview/cache_assets.rb
RUN ruby /preview/cache_assets.rb
COPY server.rb /preview/server.rb
WORKDIR /app
ENTRYPOINT []
CMD ["ruby", "/preview/server.rb"]
