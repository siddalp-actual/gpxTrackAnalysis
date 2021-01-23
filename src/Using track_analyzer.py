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

# +
import sys
sys.path.append("..")
import track_analyzer

t_1 = track_analyzer.TrackData()
t_1.slurp(
    "/home/siddalp/Dropbox/pgm/gpx/Winnall_Moors_explore_and_bread_for_brekky.gpx",
)
t_1.guess_activity_type()
t_1.segment_summary()
t_1.show_point_info()

# -

# %tb


