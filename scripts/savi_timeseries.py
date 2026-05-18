"""Plot mean SAVI over the lava flow extent for the 2018 acquisition series."""
import matplotlib.pyplot as plt
import numpy as np

from src.data_processing import RasterCalculator

DATES = [
    '20180104', '20180119', '20180305', '20180320', '20180608',
    '20180708', '20180713', '20180807', '20180812', '20180901',
    '20181001', '20181130', '20181220',
]

calculator = RasterCalculator('data/processed', 'rasters')
calculator.set_borders('lavaflow_lapalma')

means = []
for date in DATES:
    savi = calculator.calculate_savi('T28RBS', capture_date=date, save_file=False, use_bounds=True)
    relevant = savi.data[savi.data > 0]
    means.append(np.mean(relevant).item())

plt.plot(DATES, means, marker='o')
plt.xticks(rotation=45, ha='right')
plt.ylabel('Mean SAVI (vegetated pixels)')
plt.title('SAVI timeseries over lava flow extent, 2018')
plt.tight_layout()
plt.show()
