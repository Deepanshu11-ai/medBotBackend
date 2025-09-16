import requests
from .config import GOOGLE_MAPS_API_KEY
from geopy.geocoders import Nominatim

def get_nearby_hospitals(location, radius=5000):
    """
    Search for nearby hospitals using Google Places API.
    Args:
        location (str): Location string (e.g., "New York, NY")
        radius (int): Search radius in meters (default 5km)
    Returns:
        list: List of nearby hospitals with their details
    """
    try:
        # First, get coordinates for the location
        geolocator = Nominatim(user_agent="medical_bot")
        location_data = geolocator.geocode(location)
        
        if not location_data:
            return []

        # Prepare the Places API request
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{location_data.latitude},{location_data.longitude}",
            "radius": radius,
            "type": "hospital",
            "key": GOOGLE_MAPS_API_KEY
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            hospitals = []
            for place in results[:5]:  # Limit to top 5 results
                hospitals.append({
                    "name": place.get("name"),
                    "address": place.get("vicinity"),
                    "rating": place.get("rating"),
                    "place_id": place.get("place_id"),
                    "lat": place["geometry"]["location"]["lat"],
                    "lng": place["geometry"]["location"]["lng"]
                })
            return hospitals
        return []
    except Exception as e:
        print(f"Error fetching nearby hospitals: {str(e)}")
        return []