import numpy as np
import matplotlib.pyplot as plt
from src.data_processing import RasterCalculator

calculator = RasterCalculator('data/processed', 'rasters')

dates_to_process = ['20180104', '20180119', '20180305', '20180320', '20180608', '20180708', '20180713', '20180807', '20180812', '20180901', '20181001', '20181130', '20181220']

calculator.set_borders('lavaflow_lapalma')
means = []
for date in dates_to_process:
    print(date)
    savi = calculator.calculate_savi('T28RBS', capture_date = date, save_file = True, use_bounds = True)
    relevant_points = savi[np.where(savi > 0)]
    means.append(np.mean(relevant_points).item())

dates_int = [int(date) for date in dates_to_process]
plt.plot(dates_int, means)
plt.show()