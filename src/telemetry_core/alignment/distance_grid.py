import numpy as np
import pandas as pd

SMOOTH = ["time_s", "speed_kph", "throttle_pct", "rpm"]     # in between values make sense 
STEPS = ["gear", "brake", "drs"]                # no in-between: take the last sample before

def add_distance(tel:pd.DataFrame) -> pd.DataFrame:
    