# ☀️ Solar Rooftop Analyzer

A Streamlit application that helps estimate rooftop solar potential — combining
satellite-based rooftop tracing with energy, carbon, and financial projections.

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

Specify a license for this project (e.g. MIT) to let others know how they can use it.
