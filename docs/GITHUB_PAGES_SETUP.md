# Quick setup to publish the landing page on GitHub Pages

### 1) Create the GitHub repository
Use your GitHub account and create a repository, for example: `powder-ranger`.

### 2) Initialize / connect the local repository

```bash
cd "C:\Users\gogov\Documents\ChatGPT\ALM"
git init
git add .github docs lpbf_inspector/docs lpbf_inspector/README.md
git commit -m "Initial landing page for Powder Ranger"
git branch -M main
git remote add origin https://github.com/<OWNER>/<REPO>.git
git push -u origin main
```

### 3) Enable GitHub Pages

In GitHub → Settings → Pages:
- Source: `GitHub Actions`
- The workflow in `.github/workflows/pages.yml` will publish `docs/`.

### 4) Upload the Windows executable

In GitHub → Releases → New release:
- Tag it (ex. `v0.3.1`)
- Attach your installer/executable
- Copy the release URL
- Replace the placeholder in `docs/index.html`:
  - `https://github.com/YOUR_ORG/YOUR_REPO/releases/latest`

### 5) Optional custom domain

If you own a domain:
- Add a `CNAME` file with your domain
- In GitHub Pages settings, set the custom domain

### 6) Update repo links in the landing page

Edit:

- `docs/index.html`

Replace both placeholders:

- `https://github.com/YOUR_ORG/YOUR_REPO/releases/latest`
- `https://github.com/YOUR_ORG/YOUR_REPO`

with your real repository URLs.

