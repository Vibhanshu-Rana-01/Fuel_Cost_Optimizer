# FuelSmart — Fuel-Efficient Route Optimizer API

A high-performance REST API that calculates the most cost-effective fueling strategy for long-distance road trips within the USA. Given a start and finish location, FuelSmart returns the optimal fuel stops along the route to minimize total fuel expenditure.

---

## How It Works

1. A POST request is sent with a start and finish city
2. The Google Maps Directions API fetches the route in a single API call
3. The route is cached — repeat requests for the same route make zero external API calls
4. A greedy algorithm cross-references the route against 6,000+ US fuel stations loaded in memory at startup
5. The cheapest fuel stops are selected ensuring the vehicle never exceeds its 500-mile range
6. Total fuel cost is calculated and returned with the route polyline and stop details

---

## Technical Constraints

| Parameter | Value |
|---|---|
| Vehicle range | 500 miles per full tank |
| Fuel efficiency | 10 MPG |
| Geography | United States only |
| External API calls | 1 per unique route (cached thereafter) |

---

## Tech Stack

- **Python 3.13**
- **Django 6** + **Django REST Framework**
- **Google Maps Directions API** — routing
- **NumPy / Pandas** — vectorised station matching
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
│   ├── fuel_optimizer.py   # Greedy algorithm for stop selection
│   └── routing_service.py  # Google Maps API + route caching
├── .env                    # Environment variables (not committed)
└── manage.py
```

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/fuelsmart.git
cd fuelsmart
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

Calculate the optimal fueling strategy for a trip.

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
| `400` | Invalid request body |
| `422` | Route not found or no stations available |
| `502` | Google Maps API unreachable |

---

## Data Attribution

City coordinate data provided by [Simplemaps US Cities Database](https://simplemaps.com/data/us-cities) (free tier).

---

## License

MIT
