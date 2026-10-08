# _source

`build_assets.py` generates every SVG in `../assets` and the root `../README.md`.

## How it stays live
`.github/workflows/update-profile.yml` runs `python3 _source/build_assets.py --live` every 3 hours
(and whenever you edit this folder, or press "Run workflow"). It reads your real public repos
(names, descriptions, commit counts, stars, last push), repaints the project cards, and commits the result.

## Controlling what shows up (all on GitHub, no code)
- **Which projects are featured:** pin repos on your profile ("Customize your pins"). Pinned repos come
  first, then the most recently pushed.
- **A project's text:** fill in the repo's "About" description on GitHub. Until you do, the hand-written
  fallback in `CURATED` is used (or "Description coming soon.").
- **Main spotlight project:** `MAIN_PROJECT` at the top of `build_assets.py`.

## Run it yourself
    python3 _source/build_assets.py            # offline fallback
    GITHUB_TOKEN=... python3 _source/build_assets.py --live
