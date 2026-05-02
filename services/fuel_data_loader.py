import os
import threading
import pandas as pd


class FuelDataLoader:
    _instance = None
    _data = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking — re-check after acquiring lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

                    fuel_path = os.path.join(base_dir, 'data', 'fuel-prices-for-be-assessment.csv')
                    cities_path = os.path.join(base_dir, 'data', 'uscities.csv')

                    if not os.path.exists(fuel_path):
                        raise RuntimeError(
                            f"Fuel prices CSV not found at: {fuel_path}. "
                            "Place 'fuel-prices-for-be-assessment.csv' in the data/ folder."
                        )
                    if not os.path.exists(cities_path):
                        raise RuntimeError(
                            f"US cities CSV not found at: {cities_path}. "
                            "Place 'uscities.csv' in the data/ folder."
                        )

                    fuel_df = pd.read_csv(fuel_path)
                    fuel_df.columns = fuel_df.columns.str.strip()
                    fuel_df = fuel_df.rename(columns={
                        'Truckstop Name': 'name',
                        'City': 'city',
                        'State': 'state',
                        'Retail Price': 'price',
                    })
                    fuel_df = fuel_df[['name', 'city', 'state', 'price']]

                    cities_df = pd.read_csv(cities_path, usecols=['city', 'state_id', 'lat', 'lng'])
                    cities_df = cities_df.rename(columns={'state_id': 'state', 'lng': 'lon'})
                    cities_df = cities_df.drop_duplicates(subset=['city', 'state'])

                    merged = fuel_df.merge(cities_df, on=['city', 'state'], how='inner')
                    merged = merged[['name', 'lat', 'lon', 'price']].dropna()

                    cls._data = merged.reset_index(drop=True)

        return cls._instance

    def get_data(self):
        return self._data
