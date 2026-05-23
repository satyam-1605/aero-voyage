import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

BASE_URL = "https://serpapi.com/search"


def search_flights(
    origin,
    destination,
    outbound_date,
    return_date=None,
    trip_type="round_trip",
    currency="INR",
    max_results=3,
):

    params = {

        "engine":"google_flights",
        "departure_id":origin,
        "arrival_id": destination,
        "outbound_date": outbound_date,
        "currency":currency,
        "hl":"en",
        "gl":"in",
        "api_key": SERPAPI_KEY,
        "type":"1"
        if trip_type == "round_trip"
        else
        "2"
    }

    if (trip_type == "round_trip"and return_date ):
        params["return_date"] = return_date

    response = requests.get(BASE_URL,params=params,timeout=20)
    data = response.json()

    if "error" in data:
        raise ValueError(data["error"])

    raw_results = data.get("best_flights",[])

    flights = []

    for option in raw_results[:max_results]:

        legs = option.get( "flights", [] )
        if not legs:
            continue

        first_leg = legs[0]

        flights.append({"airline":first_leg.get( "airline" ),
                        "price":option.get("price" ), 
                        "departure_airport":first_leg.get("departure_airport", {} ).get("name"),
                        "arrival_airport":first_leg.get("arrival_airport", {} ).get("name" )})

    return {
        "flights": flights,
        "airports": data.get("airports", [])
    }


