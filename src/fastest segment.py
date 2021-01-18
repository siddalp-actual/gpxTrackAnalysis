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

# # Distances along a Track
#
# For the Harrier's 2021 Scavenger Hunt I nned to pull out the distance
# travellled in the best 27:44 of a track.  So I dug into an old notebook where I'd started looking at the differences between gpx tracks from OSMAnd, routes built with OSMAnd, and track from my old Garmin GPS.

# +
# %matplotlib inline

import datetime
import unittest

import pandas as pd

import gpxpy


class TestStuff(unittest.TestCase):
    """
    Re-use the gpx file test cases to pull a gpx file into a Pandas dataframe
    """

    def set_up(self):
        """
        currently no set up needed
        """
        # pass

    def test_00(self):
        """
        this gpx was recorded on OSMAnd, has times, elevations and speeds
        """
        with open(
            "/home/siddalp/Dropbox/pgm/gpx/EA_5_mi_virtual_road_relay_entry.gpx", "r"
        ) as gpx_file:
            process(gpx_file)

    @unittest.skip("run the road relay stats")
    def test_01(self):
        """
        this gpx was recorded on OSMAnd, has times, elevations and speeds
        """
        with open(
            "/home/siddalp/Dropbox/pgm/gpx/Winnall_Moors_explore_and_bread_for_brekky.gpx",
            "r",
        ) as gpx_file:
            process(gpx_file)


def show_point_info(track_segment):
    """
    extract data from points in a segment and push it into a DataFrame
    """
    col_names = "No,Date_time,Latitude,Longitude,Altitude,GPS Speed,DOP,gpxpy_speed,seg_speed,delta_dist"
    print(col_names)
    cols = list(col_names.split(","))
    local_df = pd.DataFrame(columns=cols)
    for (point, point_no) in track_segment.walk():
        #    for pointno, point in enumerate(s.points[0:20]):
        if point.extensions:

            def get_speed(x):
                """
                parse the contents of the speed tag out of the xml
                """
                for xml_field in x:
                    if xml_field.tag == "speed":
                        return xml_field.text
                return 0

            speed = float(get_speed(point.extensions))
        else:
            speed = float(0)
        if point_no != 0:
            calc_speed = point.speed_between(track_segment.points[point_no - 1])
            #  distance = point.distance_3d(track_segment.points[point_no - 1])
            distance = point.distance_2d(track_segment.points[point_no - 1])
        else:
            # print( dir(point))
            calc_speed = float(0)
            distance = float(0)
        seg_speed = float(track_segment.get_speed(point_no))

        local_df.loc[point_no] = [
            point_no,
            point.time,
            point.latitude,
            point.longitude,
            point.elevation,
            speed,
            point.horizontal_dilution,
            calc_speed,
            seg_speed,
            distance,
        ]

    # although pandas appears to process the gpxpy time into a datetime, things go awry when trying to
    # plot with that as an index, so I've resorted to going via str() and strptime() to rid myself of
    # any dependency on gpxpy once I'm in the DataFrame
    # local_df["dt"] = pd.to_datetime(local_df["Date_time"])
    # Date_time looks like: 2021-01-12 07:47:39+00:00
    local_df["dt"] = local_df["Date_time"].apply(
        lambda x: datetime.datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S%z")
    )

    local_df.index = local_df["dt"]
    local_df["tdiff"] = (local_df["dt"].diff(1)).fillna(pd.Timedelta(seconds=0))

    display(local_df.head())
    # for field in df.columns:
    #    print(field, type(df[field][1]))
    # df[['Speed', 'gpxpy_speed', 'seg_speed']].plot()
    # plt.show()
    return local_df


def show_summary(moving_data):
    """
    display track summary information built from segments
    """
    print("Moving Distance", moving_data.sum()["moving_distance"])
    print(pd.Timedelta(seconds=moving_data.sum()["moving_time"]))


def process(input_file):
    """
    iterate over the tracks and their segments in the file,
     - output some summary info
     - use show_point_info to create a DataFrame which is then exposed
       at the global level for use in subsequent cells
    """
    global df

    gpx = gpxpy.parse(input_file)

    for track in gpx.tracks:
        all_data = pd.DataFrame()
        moving_data = pd.DataFrame()
        for segment in track.segments:
            if segment.has_elevations():
                (up_m, down_m) = segment.get_uphill_downhill()
            else:
                (up_m, down_m) = (0, 0)

            moving_data = moving_data.append(
                segment.get_moving_data(stopped_speed_threshold=1)._asdict(),
                ignore_index=True,
            )
            if segment.has_times():
                secs = segment.get_moving_data()[0]
                duration = pd.Timedelta(seconds=secs)
                # td = datetime.timedelta(,secs)
                print(f"duration: {duration}")
            else:
                print("duration: segment contains no time data")
            print(
                "2d length: {} 3d length: {}".format(
                    segment.length_2d(), segment.length_3d()
                )
            )
            print("climb: {}m descent: {}m".format(up_m, down_m))

            all_data = all_data.append(show_point_info(segment))
        show_summary(moving_data)
        df = all_data


df = pd.DataFrame()
suite = unittest.TestLoader().loadTestsFromTestCase(TestStuff)
unittest.TextTestRunner(verbosity=2).run(suite)
# print('locals: ',[name for (name, thing) in locals().items() if callable(thing)])
# print('globals:',[name for (name, thing) in globals().items() if isinstance(thing,types.Function_type)])

df[["GPS Speed", "gpxpy_speed", "seg_speed"]].plot()


# -

# At this point, I have a Data_frame with distance and time deltas between
# each consecutive point. Now we have to perform an n-squared iteration
# such that for every start point, we add points to meet a criteria
# (within 'Mo time', greater than 5k etc). Then maximise or minimize over
# that.
#
# The $O(n^2)$ algorithm is held in `build_distance_list()` below.
# Subsequently I made this go nearly 30x faster by taking the first
# solution, then removing the first point and adding subsequent points to
# match the required criteria. See `faster_distance_list()`. I think this
# is now closer to $O(n)$.

MO = datetime.timedelta(seconds=27 * 60 + 44)  # Mo's WR 10k 27:44
print(MO)
display(df)


# +
def find_mo_dist(start_at):
    """
    first function designed to work out maximum distance travelled in
    27:44 (Mo Farah's WR 10k time)
    """
    global df, MO
    cum_time = pd.Timedelta(seconds=0)
    cum_dist = 0
    # print(f"mo dist: {start_at}")
    for i in range(start_at + 1, df.shape[0]):
        if cum_time + df.iloc[i]["tdiff"] >= MO:
            return i - 1, cum_dist, cum_time
        cum_time += df.iloc[i]["tdiff"]
        cum_dist += df.iloc[i]["delta_dist"]

    # if we've looped over the entire frame and time total is short
    # return and end row of 0
    return 0, 0, 0


def meets_criteria(in_df, start_at, test_after_adding_point=None):
    """
    Lots of tests follow the same pattern, refactor using a testing function
    """
    cum_time = pd.Timedelta(seconds=0)
    cum_dist = 0
    # print(f"mo dist: {start_at}")
    for i in range(start_at + 1, in_df.shape[0]):
        # print(f"{cum_dist}")
        cum_time += in_df.iloc[i]["tdiff"]
        cum_dist += in_df.iloc[i]["delta_dist"]
        if test_after_adding_point is not None and test_after_adding_point(
            cum_dist, cum_time
        ):
            return i, cum_dist, cum_time
    return 0, 0, 0


def fastest5k(dist_so_far, ignored_time_so_far):
    """
    testing function to find fastest 5k
    """
    return dist_so_far >= 5000


def greater_than5mi(dist_so_far, ignored_time_so_far):  # cum_dist, cum_time
    """
    testing function to find fastest 5mi
    """
    return dist_so_far >= 1609.3 * 5


def build_distance_list(in_df):
    """
    this function tries to meet the criteria starting from the first point,
    then the second etc, creating an entry in a DataFrame for each start point
    for which there is a solution.
    """
    distance_list = []
    for start_row in range(in_df.shape[0]):  # number rows
        # (end_row, cum_dist, cum_time) = find_mo_dist(start_row)
        # (end_row, cum_dist, cum_time) = meets_creiteria(start_row, test_after_adding_point=fastest5k)
        (end_row, total_dist, total_time) = meets_criteria(
            in_df, start_row, test_after_adding_point=fastest5k
        )
        # print(f"result: {end_row}, {total_dist}")
        if end_row == 0:
            break
        item = {
            "start_row": start_row,
            "end_row": end_row,
            "start_time": in_df.iloc[start_row]["dt"],
            "cum_dist": total_dist,
            "cum_time": total_time,
            "end_time": in_df.iloc[end_row]["dt"],
        }
        distance_list.append(item.copy())

    return pd.DataFrame(distance_list)


def faster_distance_list(in_df, test_after_adding_point=greater_than5mi):
    """
    try to go faster than the n-squared method
    """
    start_row = 0
    distance_list = []
    (end_row, total_dist, total_time) = meets_criteria(
        in_df, start_row, test_after_adding_point=test_after_adding_point
    )
    last_row = in_df.shape[0] - 1
    while end_row < last_row and start_row < last_row:
        item = {
            "start_row": start_row,
            "end_row": end_row,
            "start_time": in_df.iloc[start_row]["dt"],
            "cum_dist": total_dist,
            "cum_time": total_time,
            "end_time": in_df.iloc[end_row]["dt"],
        }
        distance_list.append(item.copy())

        start_row += 1  # start at the next point

        # which means removing the delta time and distance of that point
        total_dist -= in_df.iloc[start_row]["delta_dist"]
        total_time -= in_df.iloc[start_row]["tdiff"]

        # then adding points at the end until the criteria is met again
        while end_row < last_row:
            end_row += 1
            total_dist += in_df.iloc[end_row]["delta_dist"]
            total_time += in_df.iloc[end_row]["tdiff"]
            if test_after_adding_point(total_dist, total_time):
                break

    return pd.DataFrame(distance_list)


# #%timeit dl = build_distance_list()  # 4.72s
dl = faster_distance_list(df, greater_than5mi)  # 170ms
dl.index = dl["start_time"]
display(dl)

# -

# The `dl`, distances_list, Data_frame has the set of points and the time
# & distance they encompass for each sub-range that meets the criteria

# At this point, I started to realise that my calculated best time and
# pace where a bit different from those which Strava had found, so I
# embarked on a side mission to try to bring the two sets of results into
# agreement. See [Removing Stops](#Removing-Stops), below.

# dl.index = dl['start_time']
dl["secs_per_km"] = (
    dl["cum_time"].apply(lambda x: x.total_seconds()) / dl["cum_dist"] * 1000
)  # in s/km
dl["pace"] = dl["secs_per_km"].apply(lambda x: pd.Timedelta(seconds=x))
dl["pace"].plot()
display(
    dl.iloc[dl["cum_time"].argmin()]
    # the row corresponding to the minimum cumulative time for the distance
)


# ## Removing Stops
#
# Now I want to pull the stopped time out of my track. For this morning's
# 'Winnall Moors explore', I stopped for some time in Hoxton's buying
# bread. Strava stats are:
#
# -   distance 7.42km
# -   moving time 36:44
# -   elapsed time 44:03
# -   pace 4:57/km
# -   climb 38m
#
# I've also just read an article about Pandas Pipes so let's make one to
# pull some points out.
#
# > first issue I've come across is that the track is split across 2
# > segments, presumably by the long gap at the bread shop. I need to add
# > these together.
#
# It looks as though I get the Strava moving time by using the points
# where the point speed is \> 3km/h

# +
def remove_slow_point(in_df):
    """
    time is correct, but 2d distance too short
    """
    df = pd.DataFrame()
    df = in_df.copy()  # don't modify original
    return df[
        df["delta_dist"] / df["tdiff"].apply(lambda x: x.total_seconds()) > 3000 / 3600
    ]


def zero_tdiff_of_slow_point(in_df):
    """
    time is correct, but 2d distance is still a little short
    """
    df = pd.DataFrame()
    df = in_df.copy()  # don't modify original
    df.loc[
        df["delta_dist"] / df["tdiff"].apply(lambda x: x.total_seconds())
        <= 3000 / 3600,
        "tdiff",
    ] = pd.Timedelta(seconds=0)
    return df


dj = df.pipe(remove_slow_point)
dk = df.pipe(zero_tdiff_of_slow_point)


# +
# the 2d-distance looks closer to the Strava one


def strava_stat(in_df):
    """
    print the stats I'm trying to match with Strava
    """
    print(in_df["delta_dist"].sum())
    print(in_df["tdiff"].sum())


strava_stat(df)
strava_stat(dj)
strava_stat(dk)
# -

# There's much better agreement with the Strava data once I've removed the
# 'tdiff' associated with the points where the average speed moving here
# from the previous point is less than the threshold 3km/h. However, It
# looks as though I do need to keep the distance.

dl = faster_distance_list(dk, greater_than5mi)  # 170ms
dl.index = dl["start_time"]
# dl.index = dl['start_time']
dl["secs_per_km"] = (
    dl["cum_time"].apply(lambda x: x.total_seconds()) / dl["cum_dist"] * 1000
)  # in s/km
dl["pace"] = dl["secs_per_km"].apply(lambda x: pd.Timedelta(seconds=x))
dl["pace"].plot()
display(
    dl.iloc[dl["cum_time"].argmin()]
    # the row corresponding to the minimum cumulative time for the distance
)
fastest_row = dl["cum_time"].argmin()
print(
    "activetime:", dl.iloc[fastest_row]["end_time"] - dl.iloc[fastest_row]["start_time"]
)
display(dl)
