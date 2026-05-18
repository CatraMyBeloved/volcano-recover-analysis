"""Plot acquisition date availability for 2018 and 2019."""
import datetime
import matplotlib.pyplot as plt
import pandas as pd

from src.helper import year2018, year2019

dates_2018 = [datetime.datetime.strptime(d[4:], '%m%d') for d in year2018]
dates_2019 = [datetime.datetime.strptime(d[4:], '%m%d') for d in year2019]

fig, ax = plt.subplots()
ax.axhline(y=0.5, color='black')
ax.vlines(x=dates_2018, ymin=0.5, ymax=1, color='red', label='2018')
ax.axhline(y=0, color='black')
ax.vlines(x=dates_2019, ymin=0, ymax=0.5, color='blue', label='2019')
ax.legend()
ax.set_title('Sentinel-2 acquisition dates')
ax.set_yticks([])
plt.tight_layout()
plt.show()
