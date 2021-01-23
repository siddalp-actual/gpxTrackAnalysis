#! /usr/bin/env python3
"""
    track_analyzer: find out stuff about runs and cycle rides
"""
__module__ = "track_analyzer"

import datetime
import sys
import unittest

import argparse
import pandas as pd

import gpxpy


class TrackData:
    """
    The track is held in this object as a pandas DataFrame
    """

    def __init__(self):
        """
        build the internal data structure
        """
        self.track_data = pd.DataFrame()
        self.duration = 0
        self.segment_data = 0

    def slurp(self, filename):
        """
        parse a gpx file into an object
        """
        with open(filename) as gpx_file:
            self.process(gpx_file)

    @staticmethod
    def isnotebook():
        """
        test the environment to see whether we're running under Jupyter
        """
        try:
            shell = get_ipython().__class__.__name__
            if shell == "ZMQInteractiveShell":
                return True  # Jupyter notebook or qtconsole
            if shell == "TerminalInteractiveShell":
                return False  # Terminal running IPython
            return False  # Other type (?)
        except NameError:
            return False  # Probably standard Python interpreter

    @staticmethod
    def get_point_info(segment_number, track_segment):
        """
        extract data from points in a segment and push it into a DataFrame
        """
        col_names = (
            "SegNo,PointNo,Date_time,Latitude,Longitude,Altitude,GPS Speed,DOP,"
            "gpxpy_speed,seg_speed,delta_dist"
        )
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
                calc_speed = point.speed_between(
                    track_segment.points[point_no - 1]
                )
                #  distance = point.distance_3d(track_segment.points[point_no - 1])
                distance = point.distance_2d(track_segment.points[point_no - 1])
            else:
                # print( dir(point))
                calc_speed = float(0)
                distance = float(0)
            seg_speed = float(track_segment.get_speed(point_no))

            local_df.loc[point_no] = [
                segment_number,
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

        # although pandas appears to process the gpxpy time into a datetime,
        # things go awry when trying to plot with that as an index, so I've
        # resorted to going via str() and strptime() to rid myself of
        # any dependency on gpxpy once I'm in the DataFrame
        # local_df["dt"] = pd.to_datetime(local_df["Date_time"])
        # Date_time looks like: 2021-01-12 07:47:39+00:00
        local_df["dt"] = local_df["Date_time"].apply(
            lambda x: datetime.datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S%z")
        )

        local_df.index = local_df["dt"]
        local_df["tdiff"] = (local_df["dt"].diff(1)).fillna(
            pd.Timedelta(seconds=0)
        )

        return local_df

    def process(self, input_file):
        """
        iterate over the tracks and their segments in the file,
         - output some summary info
         - use get_point_info to create a DataFrame which is then exposed
           at the global level for use in subsequent cells
        """

        gpx = gpxpy.parse(input_file)

        for track in gpx.tracks:
            all_data = pd.DataFrame()
            moving_data = pd.DataFrame()
            for seg_no, segment in enumerate(track.segments):
                if segment.has_elevations():
                    (up_m, down_m) = segment.get_uphill_downhill()
                else:
                    (up_m, down_m) = (0, 0)

                moving_data_dict = segment.get_moving_data(
                    stopped_speed_threshold=1
                )._asdict()

                moving_data_dict["ascent"] = up_m
                moving_data_dict["descent"] = down_m
                moving_data_dict["2d length"] = segment.length_2d()
                moving_data_dict["3d length"] = segment.length_3d()

                moving_data = moving_data.append(
                    moving_data_dict,
                    ignore_index=True,
                )
                if segment.has_times():
                    secs = segment.get_moving_data()[0]
                    self.duration = pd.Timedelta(seconds=secs)
                else:
                    self.duration = pd.Timedelta(seconds=0)

                all_data = all_data.append(self.get_point_info(seg_no, segment))
            self.track_data = all_data
            self.segment_data = moving_data

    def segment_summary(self):
        """
        display track summary information built from segments
        """
        print("Segment summary:")
        print(f"{self.segment_data['moving_distance'].count()} segments")
        print(
            "Total moving Distance", self.segment_data.sum()["moving_distance"]
        )
        print(
            "Total moving Time",
            pd.Timedelta(seconds=self.segment_data.sum()["moving_time"]),
        )
        if TrackData.isnotebook():
            display(self.segment_data)
        else:
            print(self.segment_data)

    def guess_activity_type(self):
        """
        guess what activity each segment corresponds with, can be one of
        'walk', 'run', 'cycle'
        we set a likelihood of activity type based on both the pace and distance
        """
        # speed in m/s
        self.segment_data["moving_speed"] = (
            self.segment_data["moving_distance"]
            / self.segment_data["moving_time"]
        )
        # pace is a Timedelta representing time for 1km,
        self.segment_data["pace"] = self.segment_data["moving_speed"].apply(
            lambda x: pd.Timedelta(seconds=1000 / x)
        )

        def walk_likelihood(speed):
            """
            rises from 0 at 0 m/s to 1 at 9:19 pace (4mph),
            then back down to 0 at 6:19 pace (10 min mile)
            In m/s these thresholds are 0, 1.788, 2.867
            """
            if speed < 1.788:
                return speed / 1.788
            if speed < 2.867:
                return (2.867 - speed) / (2.867 - 1.788)
            return 0

        def run_likelihood(speed):
            """
            rises from 0 at 9:19 pace to 1 at 6:19 pace
            1 from 6:19 thru 4:22
            falls to 0 from 4:22 thru 3:45
            in m/s these thresholds are 1.788, 2.867, 3.810, 4.444
            """
            if speed < 1.788:
                return 0
            if speed < 2.867:
                return (speed - 1.788) / (2.867 - 1.788)
            if speed < 3.810:
                return 1
            if speed < 4.444:
                return (4.444 - speed) / (4.444 - 3.810)
            return 0

        def cycle_likelihood(speed):
            """
            rises from 0 at slow-run pace to 1 at slow cycle pace
            stays at 1 from slow cycle to long distance cycle pace
            then drops back to 0 at twice that
            in m/s these thresholds are 2.687, 4.444, 5.010, 10
            """
            if speed < 2.687:
                return 0
            if speed < 4.444:
                return (speed - 2.687) / (4.444 - 2.687)
            if speed < 5.010:
                return 1
            if speed < 10:
                return (10 - speed) / (10 - 5.010)
            return 0

        def walking_distance(dist):
            """
            Very likely from 0-5k
            Then reduces, say, linearly to 20k
            """
            if dist < 5000:
                return 1
            if dist < 20000:
                return (dist - 5000) / (20000 - 5000)
            return 0

        def running_distance(dist):
            """
            Very likely from 3k - 20k
            Reducing down to 30k
            0 > 30k
            """
            if dist < 3000:
                return 0
            if dist < 5000:
                return (dist - 3000) / (5000 - 3000)
            if dist < 20000:
                return 1
            if dist < 30000:
                return (30000 - dist) / (30000 - 20000)
            return 0

        def cycling_distance(dist):
            """
            shopping trips tend to be ~ 3k
            20-50k almost certainly cylcling
            50-120k reducing likelihood
            """
            if dist < 20000:
                return dist / 20000
            if dist < 50000:
                return 1
            if dist < 120000:
                return (120000 - dist) / (120000 - 50000)
            return 0

        self.segment_data["P(walk) from speed"] = self.segment_data[
            "moving_speed"
        ].apply(walk_likelihood)
        self.segment_data["P(run) from speed"] = self.segment_data[
            "moving_speed"
        ].apply(run_likelihood)
        self.segment_data["P(cycle) from speed"] = self.segment_data[
            "moving_speed"
        ].apply(cycle_likelihood)
        self.segment_data["P(walk) from distance"] = self.segment_data[
            "moving_distance"
        ].apply(walking_distance)
        self.segment_data["P(run) from distance"] = self.segment_data[
            "moving_distance"
        ].apply(running_distance)
        self.segment_data["P(cycle) from distance"] = self.segment_data[
            "moving_distance"
        ].apply(cycling_distance)

        # Having calculated these likelihoods, now lets average them and use
        # the highest as our guess.

        walk_likelihood = (
            self.segment_data["P(walk) from distance"]
            + self.segment_data["P(walk) from speed"]
        )
        run_likelihood = (
            self.segment_data["P(run) from distance"]
            + self.segment_data["P(run) from speed"]
        )
        cycle_likelihood = (
            self.segment_data["P(cycle) from distance"]
            + self.segment_data["P(cycle) from speed"]
        )

        # however, the xxx_likelihood is a series across segments, just sum
        if walk_likelihood.sum() > run_likelihood.sum():
            if walk_likelihood.sum() > cycle_likelihood.sum():
                return "walk"

        if run_likelihood.sum() > cycle_likelihood.sum():
            if run_likelihood.sum() > walk_likelihood.sum():
                return "run"

        if cycle_likelihood.sum() > walk_likelihood.sum():
            if cycle_likelihood.sum() > run_likelihood.sum():
                return "cycle"

        return "undetermined"

    def show_point_info(self):
        """
        display the pandas DataFrame of point data
        """
        if TrackData.isnotebook():
            display(self.track_data)
        else:
            print(self.track_data)


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
        t_0 = TrackData()
        t_0.slurp(
            "/home/siddalp/Dropbox/pgm/gpx/EA_5_mi_virtual_road_relay_entry.gpx"
        )
        self.assertFalse(t_0.segment_data.empty)
        self.assertFalse(t_0.track_data.empty)
        t_0.segment_summary()

    # @unittest.skip("run the road relay stats")
    def test_01(self):
        """
        this gpx was recorded on OSMAnd, has times, elevations and speeds
        """
        t_1 = TrackData()
        t_1.slurp(
            "/home/siddalp/Dropbox/pgm/gpx/Winnall_Moors_explore_and_bread_for_brekky.gpx",
        )
        t_1.segment_summary()
        self.assertTrue(t_1)
        t_1.guess_activity_type()
        t_1.show_point_info()
        print(t_1.segment_data)

    def test_02(self):
        """
        this is a cycle ride
        """
        t_2 = TrackData()
        t_2.slurp("/home/siddalp/Dropbox/pgm/gpx/Wet_shopping_trip.gpx")
        self.assertEqual(t_2.guess_activity_type(), "cycle")
        print(t_2.segment_data)

    def test_03(self):
        """
        this is a run
        """
        t_3 = TrackData()
        t_3.slurp("/home/siddalp/Dropbox/pgm/gpx/_The_Everest_.gpx")
        self.assertEqual(t_3.guess_activity_type(), "run")
        print(t_3.segment_data)


def do_tests():
    """
    run some unit tests
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStuff)
    unittest.TextTestRunner(verbosity=2).run(suite)


def main():
    """
    called when not imported as a module
    will slurp in a file, or run unit tests
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test", help="run the unit tests", action="store_true"
    )
    parser.add_argument(
        "filename", help="track file to be read", type=str, nargs="?"
    )
    args = parser.parse_args()
    if args.test:
        print("running unit tests")
        do_tests()
    else:
        print(f"processing {args.filename}")


if __name__ == "__main__":
    main()
    sys.exit()
else:
    print(f"module {__module__} imported")
