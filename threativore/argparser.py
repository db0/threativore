import argparse
from threativore.config import Config

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    "-v",
    "--verbosity",
    action="count",
    default=Config.threativore_verbosity,
    help="The default logging level is ERROR or higher. This value increases the amount of logging seen in your screen",
)
arg_parser.add_argument(
    "-q",
    "--quiet",
    action="count",
    default=Config.threativore_quiet,
    help="The default logging level is ERROR or higher. This value decreases the amount of logging seen in your screen",
)
arg_parser.add_argument(
    "--gc_days",
    action="store",
    default=7,
    required=False,
    type=int,
    help="For how many days to keep temporary rows in the DB",
)

arg_parser.add_argument("--allow_all_ips", action="store_true", help="If set, will consider all IPs safe")
arg_parser.add_argument("--test", action="store_true", help="Test")
arg_parser.add_argument("--color", default=False, action="store_true", help="Enabled colorized logs")
args = arg_parser.parse_args()
