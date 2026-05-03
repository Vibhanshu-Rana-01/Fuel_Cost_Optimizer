import heapq
import numpy as np
from services.fuel_data_loader import FuelDataLoader

TANK_MILES = 500
MPG = 10
SEARCH_RADIUS_MILES = 30


def _cumulative_distances(coords):
    """Build cumulative mile markers for each coordinate point along the route."""
    cum = [0.0]
    R = 3958.8
    for i in range(1, len(coords)):
        lat1 = np.radians(coords[i-1][0])
        lon1 = np.radians(coords[i-1][1])
        lat2 = np.radians(coords[i][0])
        lon2 = np.radians(coords[i][1])
        dphi = lat2 - lat1
        dlambda = lon2 - lon1
        a = np.sin(dphi / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlambda / 2) ** 2
        cum.append(cum[-1] + R * 2 * np.arcsin(np.sqrt(a)))
    return cum


def _haversine_vectorised(slat, slon, lats, lons):
    """Compute distances from one point to an array of points."""
    R = 3958.8
    phi1 = np.radians(slat)
    phi2 = np.radians(lats)
    dphi = np.radians(lats - slat)
    dlambda = np.radians(lons - slon)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _stations_near_route(coords, cum_dist, fuel_df):
    """
    Vectorised haversine: find all stations within SEARCH_RADIUS_MILES of the route.
    Returns stations sorted by route_mile, each with detour_miles stored.
    """
    route_lats = np.array([c[0] for c in coords])
    route_lons = np.array([c[1] for c in coords])
    station_lats = fuel_df['lat'].values[:, np.newaxis]
    station_lons = fuel_df['lon'].values[:, np.newaxis]
    cum_arr = np.array(cum_dist)

    R = 3958.8
    phi1 = np.radians(station_lats)
    phi2 = np.radians(route_lats)
    dphi = np.radians(route_lats - station_lats)
    dlambda = np.radians(route_lons - station_lons)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    dist_matrix = R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    nearest_idxs = np.argmin(dist_matrix, axis=1)
    min_dists = dist_matrix[np.arange(len(fuel_df)), nearest_idxs]

    mask = min_dists <= SEARCH_RADIUS_MILES
    matched_df = fuel_df[mask].reset_index(drop=True)
    matched_idxs = nearest_idxs[mask]
    matched_dists = min_dists[mask]

    stations = [
        {
            'name': matched_df.iloc[i]['name'],
            'lat': matched_df.iloc[i]['lat'],
            'lon': matched_df.iloc[i]['lon'],
            'price': matched_df.iloc[i]['price'],
            'route_mile': float(cum_arr[matched_idxs[i]]),
            'detour_miles': float(matched_dists[i]),
        }
        for i in range(len(matched_df))
    ]

    return sorted(stations, key=lambda s: s['route_mile'])


def _starting_price(start_coord, fuel_df):
    """
    Average price of stations within SEARCH_RADIUS_MILES of trip origin.
    Uses coords[0] — no extra API call. Falls back to national average.
    """
    slat, slon = start_coord
    dists = _haversine_vectorised(slat, slon, fuel_df['lat'].values, fuel_df['lon'].values)
    nearby_prices = fuel_df['price'].values[dists <= SEARCH_RADIUS_MILES]
    if len(nearby_prices) > 0:
        return float(np.mean(nearby_prices))
    return float(fuel_df['price'].mean())


def _edge_cost(station_i, station_j):
    """
    Total cost of driving from station_i to station_j and refuelling.

    refil_cost  = gallons consumed on route leg × station_j price
    detour_cost = (detour_miles at j / MPG) × (price_i + price_j)
                  using average of both prices as you drive there at i's price
                  and back at j's price after refuelling.
    """
    leg_miles = station_j['route_mile'] - station_i['route_mile']
    gallons_consumed = leg_miles / MPG
    refil_cost = gallons_consumed * station_j['price']
    detour_cost = (station_j['detour_miles'] / MPG) * (station_i['price'] + station_j['price'])
    return refil_cost + detour_cost


class FuelOptimizer:
    def __init__(self):
        self._fuel_df = FuelDataLoader().get_data()

    def optimize(self, coords: list, total_miles: float) -> dict:
        cum_dist = _cumulative_distances(coords)
        stations = _stations_near_route(coords, cum_dist, self._fuel_df)

        starting_price = _starting_price(coords[0], self._fuel_df)

        # Virtual START node — mile 0, starting price, no detour
        start_node = {
            'name': 'START',
            'lat': coords[0][0],
            'lon': coords[0][1],
            'price': starting_price,
            'route_mile': 0.0,
            'detour_miles': 0.0,
        }

        # Virtual END node — destination, price 0, no detour
        end_node = {
            'name': 'END',
            'lat': coords[-1][0],
            'lon': coords[-1][1],
            'price': 0.0,
            'route_mile': total_miles,
            'detour_miles': 0.0,
        }

        # Full node list: START + route stations + END
        nodes = [start_node] + stations + [end_node]
        n = len(nodes)
        end_idx = n - 1

        # Build adjacency: for each node i find all reachable nodes j
        # j is reachable if route distance <= TANK_MILES
        adjacency = [[] for _ in range(n)]
        for i in range(n - 1):
            for j in range(i + 1, n):
                leg = nodes[j]['route_mile'] - nodes[i]['route_mile']
                if leg > TANK_MILES:
                    break  # nodes are sorted by route_mile so no point continuing
                cost = _edge_cost(nodes[i], nodes[j])
                adjacency[i].append((cost, j))

        # Dijkstra from node 0 (START) to end_idx (END)
        dist = [float('inf')] * n
        prev = [-1] * n
        dist[0] = 0.0
        heap = [(0.0, 0)]

        while heap:
            current_cost, u = heapq.heappop(heap)
            if current_cost > dist[u]:
                continue
            if u == end_idx:
                break
            for edge_cost, v in adjacency[u]:
                new_cost = dist[u] + edge_cost
                if new_cost < dist[v]:
                    dist[v] = new_cost
                    prev[v] = u
                    heapq.heappush(heap, (new_cost, v))

        if dist[end_idx] == float('inf'):
            raise ValueError(
                "No viable route found between the given locations. "
                "The route may pass through an area with no fuel stations within tank range."
            )

        # Reconstruct path
        path = []
        node = end_idx
        while node != -1:
            path.append(node)
            node = prev[node]
        path.reverse()

        # Extract actual fuel stops (exclude START and END virtual nodes)
        selected = [nodes[i] for i in path if nodes[i]['name'] not in ('START', 'END')]

        return {
            'fuel_stops': [
                {
                    'station_name': s['name'],
                    'location': [round(s['lat'], 6), round(s['lon'], 6)],
                    'price_per_gallon': round(s['price'], 3),
                }
                for s in selected
            ],
            'total_fuel_cost': round(dist[end_idx], 2),
        }
