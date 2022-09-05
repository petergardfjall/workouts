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
        description="Calculates target paces as one or more percentages of a given pace.")
    parser.add_argument(
        "pace", metavar="<PACE>",
        help="A pace in <MM:SS> per km. For instance, 03:55.")
    parser.add_argument(
        "target_percentages", nargs="+", metavar="<TARGET %>", type=int,
        help="The target percentages of <PACE> to calculate. For instance, 94.")
    args = parser.parse_args()

    match = re.match(r'(\d{2}):(\d{2})', args.pace)
    if not match:
        raise ValueError("The specified pace is not in form <MM:SS>.")
    pace_min = int(match.group(1))
    pace_sec = int(match.group(2))
    # pace in min/km
    pace_mpk = pace_min + (pace_sec / 60.0)
    # convert pace to speed in km/h
    # min/km => km/min
    speed_kpm = 1 / pace_mpk
    # km/min => km/h
    speed_kph = speed_kpm * 60

    log.info("source pace:  %s min/km", args.pace)
    log.info("source speed: %f km/h", speed_kph)
    log.info("")
    log.info("target speeds")
    log.info("=============")
    for target_percentage in args.target_percentages:
        target_speed_kph = speed_kph * (target_percentage / 100.0)
        target_pace_mpk = 60.0 / target_speed_kph
        target_pace_min = int(target_pace_mpk)
        target_pace_sec = int((target_pace_mpk - target_pace_min) * 60)
        target_pace_str = "%s:%s" % (padzero(target_pace_min), padzero(target_pace_sec))
        log.info("%3d%%: pace: %s min/km, speed: %f km/h", target_percentage, target_pace_str, target_speed_kph)
