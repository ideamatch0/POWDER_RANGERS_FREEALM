# Powder Ranger — Windows edition

**Every layer under watch.**

Version 0.3.7 · English interface · Windows 10/11, 64-bit (x64)

## Start or install

1. Extract the complete ZIP to a local folder. Do not launch the executable from inside the ZIP and do not move it out of its extracted **Powder Ranger** folder.
2. Open the extracted **Powder Ranger** folder and double-click **Powder Ranger.exe**.
3. Powder Ranger opens in its own desktop window. If the embedded WebView engine is unavailable, the application falls back to the browser launcher.
4. To install it for your Windows account from the fallback launcher, click **Install on this computer**. This copies the executable and its bundled runtime into your local Programs folder and adds Desktop and Start menu shortcuts. Administrator rights are not required.

Python is included. The interface is displayed in a local desktop WebView and the analysis engine runs on a loopback address with an automatically selected port. Image analysis and reports do not require an internet connection. This prototype executable is not digitally signed; Windows or company policies may require approval to run it. No security settings need to be disabled.

## Import your first build

Choose **Single-job analysis**, then **Import folder**. Enter the full path to a folder on this computer and configure the filename pattern, stage aliases and layer thickness (for example, **60 µm**).

One image library represents one build. Images are read from their original folder; they are not copied into the application or modified. Keep that folder accessible. Public sample datasets are not included in the executable or ZIP.

Example names recognized by the default importer:

```
cam1_layer0001_spread.jpg
cam1_layer0001_fused.jpg
cam1_layer0002_spread.jpg
cam1_layer0002_fused.jpg
```

The configurable pattern must provide named `camera`, `layer` and `phase` groups. Check the recognized image count and layer range after importing, before starting analysis. The installed application begins with an empty library; your existing browser demonstration datasets and decisions are not copied automatically.

## Analyse and review

Run single-job analysis after checking the import. Initial gray-level calibration is calculated within that build. Post-spreading and post-melting images are analysed separately. Analysis is streamed from disk; processing speed depends on image dimensions, storage speed and image count. Progress and estimated remaining time are displayed.

Set the minimum consecutive persistence to reduce short-lived indications. Review in chronological or priority order; **Keep** and **Dismiss** save the decision and advance to the next indication. The before/peak/after crops use the same region and gray-level scale.

The priority score combines change intensity and persistence. It prioritises review; it is not a defect probability or a material-quality classification. Researcher annotations do not drive single-job detection. Reference-job comparison remains a planned mode in this version.

## Explore and export

The 3D viewer stacks photographs and colours indication markers by priority. When photographs are identified as post-melting, the cyan overlay estimates part sections from their appearance. This is an approximate photographic reconstruction, with uncalibrated X/Y coordinates. Unidentified acquisitions remain available as a photographic stack without an assigned physical height or post-melting shape.

After retaining indications, open **Create retained-indications report**. Enter the job name, reference, author, machine, material and conclusion. Choose a template:

| Template | Contents |
| --- | --- |
| Summary | Embedded 3D views, key figures, retained-indications register and comments. |
| Detailed review | Summary plus an overview and matching before/peak/after crops for every retained indication. |
| Presentation | Dark theme with larger 3D views and photographic review sheets. |

Reports contain only retained indications meeting the current persistence filter, across all stages and cameras. Each group receives separate 3D views. The views cover the complete available stack, not the viewer's current height cut. Cyan sections and score-coloured retained markers are embedded as fixed oblique and top views. Reports are self-contained HTML files: share them or open them offline without the original images. **Print / PDF** opens your browser's print dialog; choose Save as PDF and enable background graphics for full colour. Up to 500 retained indications per export are supported.

## Data, updates and removal

- Application settings, analysis caches, decisions, logs and generated reports: `%LOCALAPPDATA%\PowderRanger`.
- Installed executable: `%LOCALAPPDATA%\Programs\Powder Ranger\Powder Ranger.exe`.
- An update replaces the executable. Close the running launcher first. Your data folder is separate from the executable.
- To remove the app, close it, delete the installed executable folder and its two shortcuts. Keep the data folder to retain analyses and decisions, or remove it separately when no longer needed. Source images remain in the folders you imported.

## Rebuild from source

Install the dependencies in `requirements.txt` and PyInstaller, then run `python build_windows.py` on Windows. The output is `release/Powder Ranger/Powder Ranger.exe` and its supporting files. Development entry point: `python local_app.py --port 8765`. Build reference: [PyInstaller documentation](https://pyinstaller.org/en/stable/usage.html).
