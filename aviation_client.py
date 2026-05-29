import os
import httpx

AVIATIONSTACK_URL = "http://api.aviationstack.com/v1/flights"


async def get_flight_status(flight_iata: str) -> dict:
    api_key = os.environ["AVIATIONSTACK_API_KEY"]
    params = {"access_key": api_key, "flight_iata": flight_iata.upper().strip(), "limit": 1}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(AVIATIONSTACK_URL, params=params)
        r.raise_for_status()
        data = r.json()

    items = data.get("data") or []
    if not items:
        return {"found": False, "flight": flight_iata}

    f = items[0]
    dep = f.get("departure") or {}
    arr = f.get("arrival") or {}
    airline = (f.get("airline") or {}).get("name")

    return {
        "found": True,
        "flight": flight_iata.upper(),
        "airline": airline,
        "status": f.get("flight_status"),
        "departure_airport": dep.get("airport"),
        "departure_terminal": dep.get("terminal"),
        "departure_gate": dep.get("gate"),
        "scheduled_departure": dep.get("scheduled"),
        "estimated_departure": dep.get("estimated"),
        "departure_delay_min": dep.get("delay"),
        "arrival_airport": arr.get("airport"),
        "arrival_terminal": arr.get("terminal"),
        "arrival_gate": arr.get("gate"),
        "scheduled_arrival": arr.get("scheduled"),
        "estimated_arrival": arr.get("estimated"),
        "arrival_delay_min": arr.get("delay"),
    }
