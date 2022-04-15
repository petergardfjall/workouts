#!/usr/bin/env python

import argparse
from datetime import datetime
import json
import logging
import math
from operator import methodcaller
import os
import re
import sys
from typing import Any, Mapping, Tuple
import xml.dom.minidom
import xml.dom.pulldom
import xml.etree.ElementTree

LOG_LEVEL = logging.INFO
if 'LOG_LEVEL' in os.environ:
    LOG_LEVEL = getattr(logging, os.environ['LOG_LEVEL'].upper())
LOG = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s [%(levelname)s] %(message)s', stream=sys.stdout)

DEFAULT_START_DATE = '2000-01-01'
DEFAULT_END_DATE = datetime.now().date().isoformat()

# 2020-06-04T05:11:37+00:00_5037219985_summary.json
activity_file_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2})_(\d{8,10})_summary.json$')

pace_pattern = re.compile(r'^(\d{2}):(\d{2})$')


class Pace:
    def __init__(self, distance_m: float, time_s: float) -> None:
        min_per_km = 1.0 / ((distance_m / time_s) * 60.0 / 1000.0)
        minutes_per_km = int(math.floor(min_per_km))
        seconds_per_km = int((min_per_km - minutes_per_km) * 60)
        self.pace = '{:02d}:{:02d}'.format(minutes_per_km, seconds_per_km)

    def __str__(self) -> str:
        return self.pace


class Lap:
    def __init__(self, distance, time, avg_hr, max_hr):
        self.distance = float(distance)
        self.time = float(time)
        self.avg_hr = int(avg_hr)
        self.max_hr = int(max_hr)

    @staticmethod
    def from_multiple(laps: list['Lap']) -> 'Lap':
        aggr = Lap(0,0,0,0)
        aggr.distance = sum([lap.distance for lap in laps])
        aggr.time = sum([lap.time for lap in laps])
        aggr.avg_hr = round(sum([lap._heartbeats() for lap in laps]) / (aggr.time / 60.0))
        aggr.max_hr = max([lap.max_hr for lap in laps])
        return aggr


    def pace(self) -> float:
        return self.distance / self.time

    def _heartbeats(self) -> int:
        return round(self.avg_hr * (self.time / 60.0))

    def __str__(self) -> str:
        return f'{{"distance": {self.distance}, "time": {self.time}, "avgHR": {self.avg_hr}, "maxHR": {self.max_hr}}}'


class IntervalLapMatcher:
    def __init__(self, interval_pace_mps, min_interval_distance) -> None:
        self.interval_pace_mps = interval_pace_mps
        self.min_interval_distance = min_interval_distance

    def interval_laps(self, laps: list[Lap]) -> list[Lap]:
        """Find consecutive laps from a sequence of Laps that count as interval
        laps (including intermixed recovery laps).  """
        start_idx = -1
        for i, lap in enumerate(laps):
            if self._is_interval_lap(lap):
                start_idx = i
                break
        if start_idx < 0:
            # no interval sequence at all found
            return []

        # note: also account for longer intervals (multi-km intervals)
        # - find start of interval sequence: first lap@interval-pace
        # - parse intervals: find next N consecutive laps@interval-pace
        #   - combine into one interval Lap
        #   - count following lap as recovery
        next_idx = start_idx
        intv_laps = []
        while next_idx < len(laps):
            interval, next_idx = self._next_interval(laps, next_idx)
            if not interval:
                break
            intv_laps.append(interval)
            if next_idx < len(laps):
                # add recovery lap
                intv_laps.append(laps[next_idx])
                next_idx += 1

        return intv_laps


    def _next_interval(self, laps: list[Lap], start_idx: int) -> Tuple[Lap, int]:
        """Finds next Lap as a combination of the consecutive Laps starting at
        start_idx that are @interval-pace. Returns the combined Lap together
        widh the end_idx of the interval """
        i = start_idx
        while i < len(laps) and self._is_interval_pace(laps[i]):
            i+=1
        if i == start_idx:
            return None, i
        return Lap.from_multiple(laps[start_idx:i]), i

    def _is_interval_pace(self, lap: Lap) -> bool:
        return (lap.pace() >= self.interval_pace_mps)


    def _is_interval_lap(self, lap: Lap) -> bool:
        return (lap.pace() >= self.interval_pace_mps and
                lap.distance >= self.min_interval_distance)


class WorkoutSummary:
    def __init__(self, laps: list[Lap], time: datetime):
        """Laps are assumed to include both intervals (even indices and
        recoveries (odd indicies)."""
        self.laps = laps
        self.time = time

    def interval_laps(self):
        return [lap for i, lap in enumerate(self.laps) if i % 2 == 0]

    def recovery_laps(self):
        return [lap for i, lap in enumerate(self.laps) if i % 2 == 1]

    @staticmethod
    def avg_time(laps: list[Lap]) -> float:
        if not laps:
            return 0.0
        return round(sum([lap.time for lap in laps]) / len(laps), 2)

    @staticmethod
    def max_time(laps: list[Lap]) -> float:
        if not laps:
            return 0.0
        return round(max([lap.time for lap in laps]), 2)

    @staticmethod
    def min_time(laps: list[Lap]) -> float:
        if not laps:
            return 0.0
        return round(min([lap.time for lap in laps]), 2)

    @staticmethod
    def avg_pace(laps: list[Lap]) -> Pace:
        if not laps:
            return None
        # assume all laps are of equal distace
        total_dist_m = sum([lap.distance for lap in laps])
        total_time_s = sum([lap.time for lap in laps])
        return Pace(total_dist_m, total_time_s)

    @staticmethod
    def slowest_pace(laps: list[Lap]) -> Pace:
        if not laps:
            return None
        slowest_lap = min(laps, key=methodcaller('pace'))
        return Pace(slowest_lap.distance, slowest_lap.time)

    @staticmethod
    def fastest_pace(laps: list[Lap]) -> Pace:
        if not laps:
            return None
        fastest_lap = max(laps, key=methodcaller('pace'))
        return Pace(fastest_lap.distance, fastest_lap.time)

    @staticmethod
    def avg_hr(laps: list[Lap]) -> int:
        if not laps:
            return 0
        return round(sum([lap.avg_hr for lap in laps]) / len(laps))

    @staticmethod
    def max_hr(laps: list[Lap]) -> int:
        if not laps:
            return 0
        return max([lap.max_hr for lap in laps])

    @staticmethod
    def avg_distance(laps: list[Lap]) -> float:
        if not laps:
            return 0.0
        return round(sum([lap.distance for lap in laps]) / len(laps), 2)

    @staticmethod
    def csv_headers() -> str:
        headers = [
            "Time",
            "I Dist", "I count", "I avg time", "I avg", "I max time", "I slow", "I min time", "I fast", "I avg HR", "I max HR",
            "R Dist", "R count", "R avg time", "R avg", "R max time", "R slow", "R min time", "R fast", "R avg HR", "R max HR"
        ]
        return ",".join(headers)

    def csv(self) -> str:
        intervals = self.interval_laps()
        recoveries = self.recovery_laps()
        values = [
            self.time,
            self.avg_distance(intervals), len(intervals), self.avg_time(intervals), self.avg_pace(intervals), self.max_time(intervals), self.slowest_pace(intervals), self.min_time(intervals), self.fastest_pace(intervals), self.avg_hr(intervals), self.max_hr(intervals),
            self.avg_distance(recoveries), len(recoveries), self.avg_time(recoveries), self.avg_pace(recoveries), self.max_time(recoveries), self.slowest_pace(recoveries), self.min_time(recoveries), self.fastest_pace(recoveries), self.avg_hr(recoveries), self.max_hr(recoveries),
        ]
        return ",".join([str(v) for v in values])

    def as_dict(self) -> Mapping[str, Any]:
        intervals = self.interval_laps()
        recoveries = self.recovery_laps()
        return {
            "time": self.time,
            "intervals": {
                "distance": self.avg_distance(intervals),
                "count": len(intervals),
                "avg_time": self.avg_time(intervals),
                "max_time": self.max_time(intervals),
                "min_time": self.min_time(intervals),
                "avg_pace": str(self.avg_pace(intervals)),
                "slow_pace": str(self.slowest_pace(intervals)),
                "fast_pace": str(self.fastest_pace(intervals)),
                "avg_hr":   self.avg_hr(intervals),
                "max_hr":   self.max_hr(intervals),
            },
            "recoveries": {
                "distance": self.avg_distance(recoveries),
                "count": len(recoveries),
                "avg_time": self.avg_time(recoveries),
                "max_time": self.max_time(recoveries),
                "min_time": self.min_time(recoveries),
                "avg_pace": str(self.avg_pace(recoveries)),
                "slow_pace": str(self.slowest_pace(recoveries)),
                "fast_pace": str(self.fastest_pace(recoveries)),
                "avg_hr":   self.avg_hr(recoveries),
                "max_hr":   self.max_hr(recoveries),
            }
        }

    def __str__(self) -> str:
        return json.dumps(self.as_dict(), indent=2)


def parse_tcx_lap(lap_element: xml.dom.minidom.Element) -> Lap:
    node = lap_element
    total_s = node.getElementsByTagName('TotalTimeSeconds')[0].firstChild.nodeValue
    distance_m = node.getElementsByTagName('DistanceMeters')[0].firstChild.nodeValue
    avg_hr = node.getElementsByTagName('AverageHeartRateBpm')[0].getElementsByTagName('Value')[0].firstChild.nodeValue
    max_hr = node.getElementsByTagName('MaximumHeartRateBpm')[0].getElementsByTagName('Value')[0].firstChild.nodeValue

    return Lap(distance_m, total_s, avg_hr, max_hr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts interval sequences from garminexport activities.')
    parser.add_argument('--name', dest='name_pattern', default='.*', help='Only activities whose title matches this pattern will be considered.')
    parser.add_argument('--interval-pace', default='04:15', help='Minimum pace in min/km (MM:SS) for a lap to be considered an interval lap.')
    parser.add_argument('--min-interval-distance', default=150.0, type=float, help="Any lap shorter than this won't be considered an interval lap. This prevents counting strides as intervals.")
    parser.add_argument('--start-date', default=DEFAULT_START_DATE, help='Matched activities must be more recent than this datetime.')
    parser.add_argument('--end-date', default=DEFAULT_END_DATE, help='Matched activities must be older than this datetime.')
    parser.add_argument('dir', help='A directory holding activities backed-up by garminexport.')


    args = parser.parse_args()

    name_pattern = re.compile(args.name_pattern)
    start_date = datetime.fromisoformat(args.start_date).date()
    end_date = datetime.fromisoformat(args.end_date).date()
    m = pace_pattern.match(args.interval_pace)
    if not m:
        raise ValueError(f'invalid --interval-pace "{args.interval_pace}": must be of form MM:SS')
    mins = int(m.group(1))
    secs = int(m.group(2))
    # min pace in m/s for laps to count as interval laps
    interval_pace = 1000.0 / (60.0 * mins + secs)

    workouts = []
    LOG.debug("reading activities from %s to %s", {start_date}, {end_date})
    for fname in sorted(os.listdir(args.dir)):
        m = activity_file_pattern.match(fname)
        if not m:
            continue
        activity_time = datetime.fromisoformat(m.group(1))
        activity_id = m.group(2)

        if activity_time.date() < start_date:
            continue
        if activity_time.date() > end_date:
            # sorted list => we're done
            break

        with open(os.path.join(args.dir, fname), 'r') as summary_file:
            summary = json.load(summary_file)
            activity_name = summary.get('activityName', '')
            if not activity_name:
                continue

        if not name_pattern.search(activity_name):
            continue

        LOG.debug("%s: activity %s, name: %s",  activity_time, activity_id, {activity_name})

        #
        # read laps from .tcx file
        #
        laps = []
        tcx_file_name = fname.replace('_summary.json', '.tcx')
        tcx_path = os.path.join(args.dir, tcx_file_name)
        with open(tcx_path) as tcx_file:
            event_stream = xml.dom.pulldom.parse(tcx_file)
            for event, node in event_stream:
                if event == xml.dom.pulldom.START_ELEMENT and node.tagName == "Lap":
                    event_stream.expandNode(node)
                    # merge text nodes that are split into multiple child nodes
                    node.normalize()
                    laps.append(parse_tcx_lap(node))
        matcher = IntervalLapMatcher(interval_pace, args.min_interval_distance)
        interval_laps = matcher.interval_laps(laps)
        if not interval_laps:
            LOG.debug('  no interval laps found')
            continue

        for i, lap in enumerate(interval_laps):
            LOG.debug(f'  Lap {i+1}: {lap}')
        workout = WorkoutSummary(interval_laps, activity_time.strftime('%Y-%m-%d %H:%M:%S'))
        workouts.append(workout)

    LOG.debug(json.dumps([w.as_dict() for w in workouts], indent=2))

    #
    # output in CSV format
    #
    print(WorkoutSummary.csv_headers())
    for workout in workouts:
        print(workout.csv())
