import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from shapely.geometry import shape
import pandas as pd
import requests
import math
from streamlit_searchbox import st_searchbox

st.set_page_config(
    page_title="Rooftop Mapping & Analysis",
    layout="wide",
    page_icon="map"
)

# Default to SBU if the user hasn't searched for a location yet
if 'start_coords' not in st.session_state:
    st.session_state['start_coords'] = [23.3475, 85.4173]


def get_location_suggestions(searchterm: str):
    """Returns address suggestions from ArcGIS as the user types."""
    if not searchterm or len(searchterm) < 3:
        return []
    try:
        url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/suggest"
        params = {
            "f": "json",
            "text": searchterm,
            "maxSuggestions": 6,
            "categories": "Address,Landmark,City"
        }
        response = requests.get(url, params=params, timeout=5).json()
        return [s["text"] for s in response.get("suggestions", [])]
    except Exception:
        return []


def get_exact_coordinates(address):
    """Turns a selected address string into [lat, lon]. Returns None on failure."""
    try:
        url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
        params = {"f": "json", "singleLine": address, "maxLocations": 1}
        response = requests.get(url, params=params, timeout=5).json()
        if response.get("candidates"):
            loc = response["candidates"][0]["location"]
            return [loc["y"], loc["x"]]
    except Exception:
        pass
    return None


with st.sidebar:
    st.subheader("Global Search")
    selected_address = st_searchbox(
        get_location_suggestions,
        placeholder="Enter address or landmark...",
        key="address_search_box",
        edit_after_submit="current",
        rerun_on_update=True
    )

    if selected_address:
        new_coords = get_exact_coordinates(selected_address)
        if new_coords and new_coords != st.session_state['start_coords']:
            st.session_state['start_coords'] = new_coords
            st.rerun()


st.title("Rooftop Mapping & Site Analysis")
st.caption("Locate your facility and use the polygon tool to delineate roof segments.")

# Changing the key forces Folium to re-render when the location changes
map_session_key = f"tracer_{st.session_state['start_coords'][0]}_{st.session_state['start_coords'][1]}"

m = folium.Map(
    location=st.session_state['start_coords'],
    zoom_start=19,
    max_zoom=22,
    control_scale=True
)

folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google Hybrid',
    name='Satellite View',
    max_zoom=22,
    max_native_zoom=18
).add_to(m)

folium.Marker(
    st.session_state['start_coords'],
    tooltip="Active Search Site",
    icon=folium.Icon(color='blue', icon='info-sign')
).add_to(m)

# Only polygon and rectangle tools are relevant for rooftop tracing
Draw(
    export=False,
    draw_options={
        'polyline': False,
        'circle': False,
        'marker': False,
        'circlemarker': False,
        'rectangle': True,
        'polygon': True
    },
    edit_options={'poly': {'allowIntersection': False}}
).add_to(m)


layout_map, layout_data = st.columns([3, 1])

with layout_map:
    drawing_output = st_folium(
        m,
        width="100%",
        height=650,
        key=map_session_key,
        returned_objects=["all_drawings"]
    )

with layout_data:
    st.subheader("Inventory Metrics")

    if drawing_output and drawing_output.get("all_drawings"):
        inventory = []
        for index, feature in enumerate(drawing_output["all_drawings"]):
            if feature['geometry']['type'] in ['Polygon', 'MultiPolygon']:
                geom = shape(feature["geometry"])
                lat_radians = math.radians(st.session_state['start_coords'][0])
                # Convert from geographic degrees² to m², correcting for latitude
                area_m2 = geom.area * (111319 ** 2) * math.cos(lat_radians)

                inventory.append({
                    "Component": f"Section {index + 1}",
                    "Area": round(area_m2, 2)
                })

        if inventory:
            trace_df = pd.DataFrame(inventory)
            st.dataframe(trace_df, hide_index=True, use_container_width=True)

            total_area = trace_df['Area'].sum()
            st.metric("Total Delineated Area", f"{total_area:,.2f} m²")

            if st.button("Sync with Dashboard", use_container_width=True):
                export_df = trace_df.rename(columns={"Component": "Building"})
                st.session_state['manual_df'] = export_df
                st.toast("✅ Data synced! Navigate to the Dashboard page.")
        else:
            st.info("Awaiting delineation. Please trace roof sections on the map.")
    else:
        st.info("Select a tracing tool on the map to begin measuring infrastructure.")