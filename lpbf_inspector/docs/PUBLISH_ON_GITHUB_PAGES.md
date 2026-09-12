# Publish the Powder Ranger landing page on GitHub Pages

## 1) Add your repo links in the site

Open `docs/index.html` and replace:

- `https://github.com/YOUR_ORG/YOUR_REPO/releases/latest`
- `https://github.com/YOUR_ORG/YOUR_REPO`

with your real repository URLs.

## 2) Commit the docs folder

1. Add and commit the files:

```bash
git add docs
git commit -m "Add GitHub Pages landing site for Powder Ranger"
```

2. Push to GitHub.

## 3) Enable GitHub Pages

- In your GitHub repository: **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: your main branch (for example `main`)
- Folder: `/docs`
- Save

GitHub will publish a URL like:

- `https://<your-org>.github.io/<repo>/`

## 4) Link download button

In GitHub, create a release with `.exe` artifacts attached (from `build_windows.py` package).

Example release name:
- `Powder Ranger v0.3.1`

Attach:
- `PowderRanger-Setup.exe` (or your executable name)
- optional installer logs / changelog

Then the homepage button will point to `Releases` and keep working automatically if you keep the release URL format.

## 5) Keep the demo page aligned with releases

For every new release:
- update `docs/index.html` with the same repo links if the repo URL changed.
- update the version text in README and optionally add a version badge in `docs/index.html`.

