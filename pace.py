#!/usr/bin/env python

import argparse
import logging
import re

log = logging.getLogger(__name__)
logging.basicConfig(format="%(message)s", level=logging.INFO)


def padzero(minute_or_second):
    """Pad a minute or second mark with leading zeroes.
    Fill with leading 0's if less than 10. For example: "7" becomes "07".

    :param minute_or_second: A number between 0 and 59, being
      a "minute of hour" or "second of minute" reading.
    :type minute_or_second: int
    
    :return: The (possibly) zero-padded string.
    :rtype: str
    """
    return str(minute_or_second).rjust(2, "0")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculates average pace from distance and time.")
    parser.add_argument(
        "time", metavar="<TIME>",
        help="A race time [HH:]<MM>:<SS>. For instance, 40:55.")
    parser.add_argument(
        "distance", metavar="<DISTANCE meters>", type=int,
        help="The distance in meters. For instance, 10000.")
    args = parser.parse_args()

    match = re.match(r'(\d{2}:)?(\d{2}):(\d{2})', args.time)
    if not match:
        raise ValueError("The specified time is not in form [HH:]<MM>:<SS>.")
    if match.group(1):
        time_hrs = int(match.group(1)[:2])
    else:
        time_hrs = 0    
    time_min = int(match.group(2))
    time_sec = int(match.group(3))
    # time in minutes
    total_time_min = time_hrs*60.0 + time_min + time_sec/60.0
    distance_km = args.distance / 1000.0

    # fractional pace in min/km
    pace_mpk = total_time_min / distance_km

    pace_mins = int(pace_mpk)
    pace_secs = int(round((pace_mpk - pace_mins) * 60.0))

    log.info("average pace:  %s:%s min/km", padzero(pace_mins), padzero(pace_secs))
