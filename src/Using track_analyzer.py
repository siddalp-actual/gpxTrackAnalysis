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
#    "/home/siddalp/Dropbox/pgm/gpx/Winnall_Moors_explore_and_bread_for_brekky.gpx",
#    "/home/siddalp/Dropbox/pgm/gpx/_The_ABBA_.gpx",
#    "/home/siddalp/Dropbox/pgm/gpx/Would_yew_forest.gpx",
#    "/home/siddalp/Dropbox/pgm/gpx/EA_5_mi_virtual_road_relay_entry.gpx"
#    "/home/siddalp/Dropbox/pgm/gpx/Final_family_walk_before_Lent_term_starts.gpx"
#    "/home/siddalp/Dropbox/pgm/gpx/When_the_route_ends_before_your_planned_distance.gpx"
    "/home/siddalp/Dropbox/pgm/gpx/Nearly_dry_and_warm_enough_to_enjoy_cycling.gpx"
)
#t_1.guess_activity_type()
seg_data = t_1.segment_summary()
t_1.show_point_info()


# +
def best_10mi(dist_so_far, time_so_far):
    if dist_so_far >= 10000:
        return True
    return False

#dl = t_1.build_distance_list()
dl = t_1.build_distance_list()  #test_after_adding_point = best_10mi)

best_time = dl['cum_time'].min()
pos_best_time = dl['cum_time'].idxmin()
print(f"Best time of {best_time} in interval starting at {pos_best_time}")

display(dl)
# -

import matplotlib
ax = dl["pace"].plot()
ax.set_ylabel("Pace")
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(
    # the *divmod lets the tuple result be passed as parms to format
    lambda x, p: "{:d}:{:02}".format(*divmod(int(x/1e9),60))
))

t_1.show_strava_stats()

help(track_analyzer.TrackData.build_distance_list)
