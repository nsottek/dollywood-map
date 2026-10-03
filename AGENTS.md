# Dollywood Map — Agent Context

## Goal

Build an interactive web app for planning a Dollywood visit. The app has two views:

- **Map view**: an interactive map of the park showing attraction locations, filterable by area and type. Attractions are plotted as pins/markers on a park map image. Clicking a pin shows details about that attraction.
- **List view**: a filterable, sortable list of all attractions organized by area and type. Useful for trip planning — e.g. "show me all roller coasters" or "what's in Wildwood Grove."

Both views should share the same filter state so switching between them is seamless.

## Current state

`dollywood2.html` is the main app — a single-file HTML/CSS/JS implementation with no build step. It already has a dark theme, DM Sans/DM Serif Display typography, and area color coding. `gen_dollywood2.py` is a helper script used to generate or assist with the HTML.

## Attractions data — `dollywood_attractions.json`

The data file is the source of truth for all park attractions. It has three top-level arrays:

### `rides`
Each ride has:
- `mapId` — numeric ID corresponding to the official Dollywood park map (may be `null` for some attractions)
- `name` — display name
- `area` — park area (e.g. `"Wildwood Grove"`, `"Timber Canyon"`, `"Country Fair"`)
- `type` — category: `"roller_coaster"`, `"thrill"`, `"water"`, `"family"`, `"pre_k"`, `"attraction"`, `"show"`
- `timeSaver` — boolean; whether a TimeSaver (skip-the-line) pass is available
- `timeSaverType` — `"premium"` for premium TimeSaver rides (optional, present only when applicable)
- `heightMin` — minimum height in inches (optional)
- `heightMax` — maximum height in inches for kiddie rides (optional)

### `entertainment`
Each entry has `mapId`, `name`, `area`, `venue`, `type`, and optionally:
- `seasonal` — boolean
- `seasonDates` — string like `"9/14–10/31"` when seasonal

Types include: `"venue"`, `"show"`, `"film"`, `"interactive_experience"`, `"character_meet"`, `"dance_party"`, `"music"`

### `dining`
Each entry has `mapId`, `name`, `area`, `type`, and optionally `temporarilyClosed`.

Types include: `"restaurant"`, `"bakery"`, `"snack"`, `"ice_cream"`, `"event_space"`, etc.

## Park areas

The park is divided into themed areas, each with a distinct color in the UI:
- Showstreet, Timber Canyon, Wilderness Pass, Craftsman's Valley, Owens Farm, The Village, Country Fair, Rivertown Junction, Jukebox Junction, Dolly Parton Experience, Wildwood Grove

## Design notes

- Single-file HTML with no build tooling; keep it that way unless there's a compelling reason to change
- Mobile-first — most users will be on their phones at the park
- The app uses CSS custom properties for theming (`--bg`, `--surface`, `--txt`, etc.) and supports both light and dark mode
