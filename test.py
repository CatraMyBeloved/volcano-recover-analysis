import datetime
from src.helper import *
import pandas as pd
import matplotlib.pyplot as plt

dates_datetime = [datetime.datetime.strptime(string[4:], '%m%d') for string in
                  year2018]
dates_datetime2 = [datetime.datetime.strptime(string[4:], '%m%d') for string
                   in year2019]

date_series = pd.Series(pd.date_range(start=dates_datetime[0], end=dates_datetime[-1]))



fig, ax = plt.subplots()
ax.axhline(y=0.5, color='black')
ax.vlines(x=dates_datetime, ymin=0.5, ymax=1, color='red')
ax.axhline(y=0, color='black')
ax.vlines(x=dates_datetime2, ymin=0, ymax=0.5, color='blue')
plt.show()