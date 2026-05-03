# FuelSmart — Fuel-Efficient Route Optimizer API

A high-performance REST API that calculates the **globally optimal** fueling strategy for long-distance road trips within the USA. Given a start and finish location, FuelSmart finds the sequence of fuel stops that minimizes your total trip cost — accounting for both fuel price per gallon and the real cost of driving off the highway to reach each station.

---

## How It Works

1. A POST request is sent with a start and finish city
2. The Google Maps Directions API fetches the route in a single API call
3. The route is cached — repeat requests for the same route make zero external API calls
4. 6,000+ US fuel stations are loaded into RAM at startup and matched against the route using vectorised NumPy operations
5. The average fuel price near the trip origin is calculated to estimate the starting tank price
6. Every station on the route becomes a node in a weighted graph
7. Dijkstra's shortest path algorithm finds the globally cheapest sequence of stops
8. Total fuel cost — including detour costs — is returned with the route polyline and stop details

---

## Why Dijkstra and Not Greedy

A greedy algorithm picks the cheapest station in the current window at each step. This can lead to locally good but globally bad decisions — a cheap stop now might force an expensive stop later.

Dijkstra evaluates every possible combination of stops across the entire route and finds the path with the minimum total cost. It is mathematically guaranteed to find the optimal solution.

---

## How Detour Cost Is Calculated

Every fuel station is not sitting on the highway. Some are 1 mile off the road, some are 15 miles off. Driving off the highway and back costs real fuel.

For each edge in the graph (driving from station i to station j):

```
refil_cost  = (route_miles_i_to_j / MPG) × price_at_j
detour_cost = (detour_miles_at_j / MPG) × (price_at_i + price_at_j)
edge_cost   = refil_cost + detour_cost
```

The detour cost uses the sum of both prices because you drive to the station burning fuel at the price you last paid (price i) and drive back after refuelling at the new price (price j).

---

## Technical Constraints

| Parameter | Value |
|---|---|
| Vehicle range | 500 miles per full tank |
| Fuel efficiency | 10 MPG |
| Station search radius | 30 miles from route |
| Geography | United States only |
| External API calls | 1 per unique route (cached thereafter) |

---

## Tech Stack

- **Python 3.13**
- **Django 6** + **Django REST Framework**
- **Google Maps Directions API** — single call routing with plain city name support
- **NumPy / Pandas** — vectorised station matching
- **Dijkstra's Algorithm** — globally optimal stop selection
- **Simplemaps US Cities** — city coordinate data

---

## Project Structure

```
greedy_route_optimiser/
├── api/                    # DRF views, serializers, URLs
├── core/                   # Django settings, WSGI, root URLs
├── data/                   # Fuel prices CSV + US cities CSV
├── services/
│   ├── fuel_data_loader.py # Singleton — loads CSVs into RAM at startup
│   ├── fuel_optimizer.py   # Dijkstra algorithm for globally optimal stop selection
│   └── routing_service.py  # Google Maps API + route caching
├── .env                    # Environment variables (not committed)
└── manage.py
```

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Vibhanshu-Rana-01/Fuel_Cost_Optimizer.git
cd Fuel_Cost_Optimizer
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add required data files

Place the following files in the `data/` folder:

- `fuel-prices-for-be-assessment.csv` — fuel station prices
- `uscities.csv` — US city coordinates from [simplemaps.com/data/us-cities](https://simplemaps.com/data/us-cities)

### 5. Configure environment variables

Create a `.env` file in the project root:

```
DJANGO_SECRET_KEY=your-secret-key-here
GOOGLE_MAPS_API_KEY=your-google-maps-api-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

To generate a Django secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Run the server

```bash
python manage.py runserver
```

---

## API Reference

### `POST /api/v1/route-plan/`

Calculate the globally optimal fueling strategy for a trip.

**Request Body**

```json
{
  "start": "Los Angeles, CA",
  "finish": "New York, NY"
}
```

**Successful Response `200 OK`**

```json
{
  "total_distance_miles": 2791.5,
  "total_fuel_cost": 854.10,
  "route_polyline": "encoded_polyline_string",
  "fuel_stops": [
    {
      "station_name": "HOPI TRAVEL PLAZA",
      "location": [36.2883, -115.0888],
      "price_per_gallon": 3.139
    }
  ]
}
```

**Error Responses**

| Status | Meaning |
|---|---|
| `400` | Invalid request body — missing or malformed start/finish |
| `422` | Route not found, no stations available, or gap in coverage |
| `502` | Google Maps API unreachable or timed out |

---

## Algorithm Overview

```
1. Decode Google Maps polyline → list of (lat, lon) coordinates
2. Build cumulative mile markers using Haversine formula
3. Match 6,007 stations to route via vectorised NumPy distance matrix
4. Store route_mile and detour_miles per station
5. Calculate starting price from stations near trip origin
6. Build weighted graph: START + stations + END as nodes
7. Draw edges between all nodes reachable within 500 miles
8. Calculate edge cost = refil_cost + detour_cost
9. Run Dijkstra's shortest path from START to END
10. Return optimal path and total cost
```

---

## Data Attribution

City coordinate data provided by [Simplemaps US Cities Database](https://simplemaps.com/data/us-cities) (free tier).

---

## License

MIT
