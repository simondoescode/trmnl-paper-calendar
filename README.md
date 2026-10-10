# TRMNL Paper Calendar

A self-hostable family calendar screen for the TRMNL 7.5-inch OG DIY Kit (800 × 480, four greys). This repository starts with a **Hello World** TRMNL plugin and a Docker-powered local preview.

## Requirements

- Docker Desktop (with Docker Compose)
- VS Code and the optional Dev Containers extension

No local Ruby, Node, or hardware is required for the initial preview.

## Start the preview

```bash
git clone https://github.com/simondoescode/trmnl-paper-calendar.git
cd trmnl-paper-calendar
docker compose up
```

Open **http://localhost:4567**. Edit `src/full.liquid` and refresh the preview (the preview server also watches files). Use `Ctrl+C` to stop.

Lint the plugin:

```bash
docker compose run --rm trmnlp lint
```

## VS Code

Open the repository in VS Code. Install the **Dev Containers** extension, then run **Dev Containers: Reopen in Container**. The container has the TRMNL preview tooling and forwards port 4567.

## Layout

- `src/full.liquid`: full-size TRMNL screen, initially Hello World.
- `src/settings.yml`: plugin settings.
- `.trmnlp.yml`: preview configuration.
- `compose.yaml`: standalone local preview service.
- `.devcontainer/devcontainer.json`: VS Code setup.

## Framework and Tailwind

TRMNL plugins are Liquid templates styled with the **TRMNL Design Framework**. This includes grid, spacing, and type utility classes familiar to Tailwind users. **It is not a general-purpose Tailwind CSS build**: the preview uses TRMNL's real device-oriented framework so the generated screen will match the hardware renderer more closely. We can introduce a Tailwind compilation step later for custom CSS if necessary.

## Self-hosting with Terminus

The preview runs fully locally and does **not** require a TRMNL cloud account. For a complete self-hosted TRMNL server, use [Terminus](https://github.com/usetrmnl/terminus) separately. Terminus has its own database and container setup and is not required to build the plugin. The Hello World example is a local proof of layout, **not** yet connected to Terminus or Google Calendar.

## Next steps

Add Google Calendar ICS retrieval, configuration, UK timezone rendering, Today / This Week columns, weather, and e-ink-safe four-shade layout. Keep credentials and private calendar URLs outside this repository.

Useful references: [trmnlp](https://github.com/usetrmnl/trmnlp), [TRMNL Framework](https://github.com/usetrmnl/trmnl-framework), [Terminus](https://github.com/usetrmnl/terminus).
