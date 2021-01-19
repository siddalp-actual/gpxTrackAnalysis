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
    def get_point_info(track_segment):
        """
        extract data from points in a segment and push it into a DataFrame
        """
        col_names = (
            "No,Date_time,Latitude,Longitude,Altitude,GPS Speed,DOP,"
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
         - use show_point_info to create a DataFrame which is then exposed
           at the global level for use in subsequent cells
        """

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
                    segment.get_moving_data(
                        stopped_speed_threshold=1
                    )._asdict(),
                    ignore_index=True,
                )
                if segment.has_times():
                    secs = segment.get_moving_data()[0]
                    self.duration = pd.Timedelta(seconds=secs)
                else:
                    self.duration = pd.Timedelta(seconds=0)
                print(
                    "2d length: {} 3d length: {}".format(
                        segment.length_2d(), segment.length_3d()
                    )
                )
                print("climb: {}m descent: {}m".format(up_m, down_m))

                all_data = all_data.append(self.get_point_info(segment))
            self.track_data = all_data
            print(self.track_data)
            self.segment_data = moving_data

    def segment_summary(self):
        """
        display track summary information built from segments
        """
        print("Moving Distance", self.segment_data.sum()["moving_distance"])
        print(pd.Timedelta(seconds=self.segment_data.sum()["moving_time"]))


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

    @unittest.skip("run the road relay stats")
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
else:
    print(f"module {__module__} imported")

sys.exit()
