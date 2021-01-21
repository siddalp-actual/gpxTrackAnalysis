# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# # Working out the track type

# +
import IPython.core.display

IPython.core.display.HTML("<img src='./untitled.svg'/>")
# -

# As the velocity, or pace, increases the most likely activity type changes.  Let's try to establish some key velocities and their equivalent paces.  
#
# | Speed km/h | Speed m/s | Pace min/km | Comment |
# | ---:| ---: | ---: | --- |
# | 1    | 0.278 | 60:00   | segment cut-off |
# | 3    | 0.833 | 20:00   | strava run cut-off |
# | 6.4  | 1.788 |  9:19   | 4mph walking |
# | 9.6  | 2.667 |  6:15   | slow run  |
# | 13.7 | 3.810 |  4:23   | fast run  |
# | 16.0 | 4.444 |  3:45   | slow cycle |
# | 20.9 | 5.010 |  2:52   | long distance cycle |
#

metres_per_sec = 1609*4/3600
print(metres_per_sec)
print(metres_per_sec*3.6)

import pandas as pd
print(pd.Timedelta(seconds=1000/metres_per_sec))


