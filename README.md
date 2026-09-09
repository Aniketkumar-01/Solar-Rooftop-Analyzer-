# ☀️ Solar Rooftop Analyzer

A Streamlit application that helps estimate rooftop solar potential — combining
satellite-based rooftop tracing with energy, carbon, and financial projections.

🔗 **Live app:** https://solar-rooftop-analyzer.streamlit.app/
💻 **Repo:** https://github.com/Aniketkumar-01/Solar-Rooftop-Analyzer-

## Features

**🗺️ Satellite Mapping (`sattelite_mapping.py`)**
- Search for any address or landmark and jump to it on a satellite map
- Trace rooftop polygons directly on high-resolution satellite imagery
- Automatically computes delineated roof area (m²), corrected for latitude
- Sync traced building data straight into the dashboard with one click

**📊 Solar Insights Dashboard (`dashboard.py`)**
- Upload rooftop area data via CSV, or sync it from the mapping page
- Auto-geocodes your project location and pulls real annual solar irradiance
  (NASA POWER API), with a sensible fallback if the lookup fails
- Configurable panel efficiency, system losses, and rooftop utilisation
- Calculates, per building and in total:
  - System capacity (kWp)
  - Estimated annual energy generation (kWh)
  - CO₂ emissions offset (tCO₂e)
  - Estimated annual financial savings (₹)
- Interactive charts and a downloadable full analysis CSV

## Project Structure

```
.
├── dashboard.py              # Main analysis dashboard (Streamlit page)
├── pages/
│   └── sattelite_mapping.py  # Rooftop tracing on satellite imagery
├── requirements.txt
└── README.md
```

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-org-or-user>/solar-rooftop-analyzer.git
cd solar-rooftop-analyzer
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run dashboard.py
```

Then navigate to the **Satellite Mapping** page from the sidebar to trace rooftops,
or upload a CSV with `Building` and `Area` columns directly on the Dashboard page.

## CSV Format

If uploading data manually, your CSV should contain at minimum:

| Column   | Description                     |
|----------|----------------------------------|
| Building | Name/label of the building       |
| Area     | Rooftop area in square metres (m²) |

**Example:**

```csv
Building,Area
Block A,823
Block B,1139
Library,450
lab,300
```

A ready-to-use sample file, [`sample-data.csv`](sample-data.csv), is included in this
repo — download it and upload it directly on the [live app](https://solar-rooftop-analyzer.streamlit.app/)
to try the full analysis without needing your own data.

## Data Sources

- **Geocoding:** [Nominatim (OpenStreetMap)](https://nominatim.org/) and [ArcGIS World Geocoding Service](https://developers.arcgis.com/rest/geocode/)
- **Solar Irradiance:** [NASA POWER API](https://power.larc.nasa.gov/)
- **Satellite Imagery:** Google Hybrid tiles via Folium

## Assumptions & Constants

| Constant | Value | Notes |
|---|---|---|
| Grid carbon factor | 0.82 kg CO₂/kWh | India grid average (CEA 2023) |
| Panel power density | 0.20 kW/m² | Standard installer basis |
| O&M cost | ₹500/kWp/year | |
| Default irradiance fallback | 4.8 kWh/m²/day | Used if location/API lookup fails |

## Collaborators

- [saurav2003kujur](https://github.com/saurav2003kujur)
- [Shivam99864246](https://github.com/Shivam99864246)

## License

This project is licensed under the [MIT License](LICENSE) — see the `LICENSE` file
for the full text. Copyright (c) 2026 Aniket kumar, with contributions from the
collaborators listed above.
