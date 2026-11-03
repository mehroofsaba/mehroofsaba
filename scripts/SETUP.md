# Setup

## 1. Berghan (headings on all generated pages)

Berghan is a licensed font, so it must not be committed to this public repo.
Instead the workflow reads it from a private GitHub secret and draws the headings as
vector outlines inside the images.

1. `pip install fonttools`
2. `python scripts/prepare_font.py path/to/Berghan.otf` (creates `Berghan-subset.b64.txt`)
3. Repo → Settings → Secrets and variables → Actions → New repository secret
   - Name: `BERGHAN_FONT_B64`
   - Value: the full contents of `Berghan-subset.b64.txt`
4. Actions → "Update Projects & Activity" → Run workflow.

Check Craft Supply Co's licence allows turning the font into images (outlined text).
Until the secret exists, headings fall back to Jost (open licence) and the log shows a warning.

## 2. LinkedIn link

The LinkedIn profile URL is configured directly in `scripts/update_profile.py`.
Update the `LINKEDIN_URL` constant there if the profile URL changes.

## 3. Optional knobs (environment variables in the workflow)

`MAX_REPOS` (cap the number of cards, default all) · `EXCLUDE_REPOS` (comma-separated names).
