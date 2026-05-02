import bisect
import numpy as np
from services.fuel_data_loader import FuelDataLoader

TANK_MILES = 500
MPG = 10
SEARCH_RADIUS_MILES = 30
# Only consider stations at least MIN_LEG_MILES ahead to avoid tiny hops
MIN_LEG_MILES = 200


def _cumulative_distances(coords):
    """Build cumulative mile markers for each coordinate point along the route."""
    cum = [0.0]
    R = 3958.8
    for i in range(1, len(coords)):
        lat1, lon1 = np.radians(coords[i-1][0]), np.radians(coords[i-1][1])
        lat2, lon2 = np.radians(coords[i][0]), np.radians(coords[i][1])
        dphi = lat2 - lat1
        dlambda = lon2 - lon1
        a = np.sin(dphi / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlambda / 2) ** 2
        cum.append(cum[-1] + R * 2 * np.arcsin(np.sqrt(a)))
    return cum


def _stations_near_route(coords, cum_dist, fuel_df):
    """
    Vectorised haversine: compute distance from every station to every route
    coordinate in one numpy matrix operation. Returns stations within
    SEARCH_RADIUS_MILES of the route, sorted by route_mile.
    """
    route_lats = np.array([c[0] for c in coords])        # shape (R,)
    route_lons = np.array([c[1] for c in coords])        # shape (R,)
    station_lats = fuel_df['lat'].values[:, np.newaxis]  # shape (S, 1)
    station_lons = fuel_df['lon'].values[:, np.newaxis]  # shape (S, 1)
    cum_arr = np.array(cum_dist)                         # shape (R,)

    R = 3958.8
    phi1 = np.radians(station_lats)
    phi2 = np.radians(route_lats)
    dphi = np.radians(route_lats - station_lats)
    dlambda = np.radians(route_lons - station_lons)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    dist_matrix = R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))  # (S, R)

    nearest_idxs = np.argmin(dist_matrix, axis=1)
    min_dists = dist_matrix[np.arange(len(fuel_df)), nearest_idxs]

    mask = min_dists <= SEARCH_RADIUS_MILES
    matched_df = fuel_df[mask].reset_index(drop=True)
    matched_idxs = nearest_idxs[mask]

    stations = [
        {
            'name': matched_df.iloc[i]['name'],
            'lat': matched_df.iloc[i]['lat'],
            'lon': matched_df.iloc[i]['lon'],
            'price': matched_df.iloc[i]['price'],
            'route_mile': float(cum_arr[matched_idxs[i]]),
        }
        for i in range(len(matched_df))
    ]

    return sorted(stations, key=lambda s: s['route_mile'])


class FuelOptimizer:
    def __init__(self):
        self._fuel_df = FuelDataLoader().get_data()

    def optimize(self, coords: list, total_miles: float) -> dict:
        cum_dist = _cumulative_distances(coords)
        stations = _stations_near_route(coords, cum_dist, self._fuel_df)

        route_miles = [s['route_mile'] for s in stations]

        selected = []
        current_mile = 0.0

        while total_miles - current_mile > TANK_MILES:
            window_end = current_mile + TANK_MILES

            pref_start = bisect.bisect_right(route_miles, current_mile + MIN_LEG_MILES)
            window_start = bisect.bisect_right(route_miles, current_mile)
            window_end_idx = bisect.bisect_right(route_miles, window_end)

            preferred = stations[pref_start:window_end_idx]
            candidates = preferred if preferred else stations[window_start:window_end_idx]

            if not candidates:
                raise ValueError(
                    f"No fuel station within {TANK_MILES} miles of mile marker "
                    f"{current_mile:.1f}. Route may pass through uncovered area."
                )

            best = min(candidates, key=lambda s: s['price'])
            selected.append(best)
            current_mile = best['route_mile']

        # Cost model: each leg is charged at the price of the stop at the END
        # of that leg (i.e. the price you pay when you arrive and refuel).
        # The first leg (start → first stop) is charged at the first stop price.
        # The final leg (last stop → destination) is charged at the last stop price.
        total_cost = 0.0
        prev_mile = 0.0

        if not selected:
            # Route is under TANK_MILES — no stops needed.
            # Find the cheapest station on the route to estimate fuel cost.
            if stations:
                cheapest = min(stations, key=lambda s: s['price'])
                total_cost = (total_miles / MPG) * cheapest['price']
            else:
                # No stations found on route at all — cannot calculate cost.
                raise ValueError(
                    "No fuel stations found near this route. "
                    "Cannot calculate fuel cost."
                )
        else:
            for stop in selected:
                leg_miles = stop['route_mile'] - prev_mile
                total_cost += (leg_miles / MPG) * stop['price']
                prev_mile = stop['route_mile']

            # Final leg to destination
            final_leg = total_miles - prev_mile
            if final_leg > 0:
                total_cost += (final_leg / MPG) * selected[-1]['price']

        return {
            'fuel_stops': [
                {
                    'station_name': s['name'],
                    'location': [round(s['lat'], 6), round(s['lon'], 6)],
                    'price_per_gallon': round(s['price'], 3),
                }
                for s in selected
            ],
            'total_fuel_cost': round(total_cost, 2),
        }
