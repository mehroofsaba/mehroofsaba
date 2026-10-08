# _source

`build_assets.py` generates every SVG in `../assets` and the root `../README.md`.

## How it stays live
`.github/workflows/update-profile.yml` runs `python3 _source/build_assets.py --live` every 3 hours
(and whenever you edit this folder, or press "Run workflow"). It reads your real GitHub data:
repos, descriptions, commit counts, stars, followers, the contribution calendar and your latest commits,
repaints them in the sakura palette, and commits the result.

## Controlling what shows up (all on GitHub, no code)
- **Which projects are featured:** pin repos on your profile ("Customize your pins"). Pinned repos come
  first, then the most recently pushed.
- **A project's text:** fill in the repo's "About" description on GitHub. Until you do, the hand-written
  fallback in `CURATED` is used.
- **Main spotlight project:** `MAIN_PROJECT` at the top of `build_assets.py`.

## Private contributions
The built-in token only sees public data. If your real profile graph is greener than the generated one
(because you have private repos), create a classic personal access token with `read:user` + `repo`
scopes and save it in this repo's Settings -> Secrets -> Actions as `PROFILE_TOKEN`.

## Run it yourself
    python3 _source/build_assets.py            # offline fallback
    GITHUB_TOKEN=... python3 _source/build_assets.py --live
