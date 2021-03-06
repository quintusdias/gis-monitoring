# Standard library imports
import argparse
import datetime
import pathlib

from .big_brother import BBFlagHistory
from .check_mk import CheckCheckMK
from .daily_log_merge import DailyApacheLogCount, DailyApacheLogCountPlot
from .daily_log import ApacheLogBinner

BB_SITE_MAP = {
    'bldr': {
        'nowcoast': ('http://bb-bldr.ncep.noaa.gov'
                     '/IDP-Applications/IDP-NOWCOAST-OPS'
                     '/IDP-NOWCOAST-OPS.html'),
        'idpgis': ('http://bb-bldr.ncep.noaa.gov'
                   '/IDP-Applications/IDP-GIS-ESRI/IDP-GIS-ESRI.html'),
    },
    'cprk': {
        # 'nowcoast': ('http://bb.ncep.noaa.gov'
        #              '/IDP-Applications/IDP-NOWCOAST-OPS'
        #              '/IDP-NOWCOAST-OPS.html'),
        'nowcoast': ('http://bb.ncep.noaa.gov'
                     '/IDP-Applications/IDP-NOWCOAST-NEW-Ops'
                     '/IDP-NOWCOAST-NEW-Ops.html'),
        'idpgis': ('http://bb.ncep.noaa.gov'
                   '/IDP-Applications/IDP-GIS-ESRI/IDP-GIS-ESRI.html'),
    },
}


def valid_date_time(s):
    """
    Performs type-checking for entry point.
    """
    format = '%Y-%m-%dT%H'
    try:
        return datetime.datetime.strptime(s, format)
    except ValueError:
        msg = f"Not a valid date: '{s}.  Expecting '{format}'"
        raise argparse.ArgumentTypeError(msg)


def valid_date(s):
    """
    Performs type-checking for collect_ags_stats entry point.
    """
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%d')
    except ValueError:
        msg = "Not a valid date: '{0}.".format(s)
        raise argparse.ArgumentTypeError(msg)


def bb_flag_history():
    """
    Entry point for command line script "bb_flag_hist"
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('site', choices=['cprk', 'bldr'])
    parser.add_argument('project', type=str)

    args = parser.parse_args()

    root = pathlib.Path.home()
    root = root / 'www' / 'bigbrother' / 'summary' / args.site / args.project
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'index.html'

    url = BB_SITE_MAP[args.site][args.project]
    obj = BBFlagHistory(url, output_file=str(path))
    obj.run()


def bin_daily_apache_log_file():
    """
    Console entry point for binning the daily apache log file by the minute.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('project',
                        choices=['idpgis', 'nowcoast'],
                        default='nowcoast')

    help = 'Path to input apache log file, hopefully you are just testing?'
    parser.add_argument('-i', '--input_file', type=str, help=help)

    help = 'Path to output HDF5 file, hopefully you are just testing?'
    parser.add_argument('-o', '--output_file', type=str, help=help)

    args = parser.parse_args()

    kwargs = {
        'project': args.project,
        'input_file': args.input_file,
        'output_file': args.output_file,
    }
    obj = ApacheLogBinner(**kwargs)
    obj.run()


def ccmk():
    """
    Query Check_MK for plots.
    """
    description = ("Command line utility for constructing a montage of plots "
                   "from Check_MK.")
    parser = argparse.ArgumentParser(description=description)

    help = "Project"
    choices = ['nowcoast', 'idpgis', 'ridge2']
    parser.add_argument('project', help=help, choices=choices)

    help = "Site"
    choices = ['cprk', 'bldr']
    parser.add_argument('site', help=help, choices=choices)

    help = "Tier"
    choices = ['dev', 'qa', 'op']
    parser.add_argument('tier', help=help, choices=choices)

    help = "VM type"
    choices = [
        'application-server', 'compute-farm', 'tomcat', 'db-reader',
        'db-master', 'geowebcache'
    ]
    parser.add_argument('vmtype', help=help, choices=choices)

    help = "Query this Check_MK metric."
    choices = [
        'CPU_load', 'CPU_utilization', 'Memory_used', 'fs__opt',
        'PostgreSQL_DB_postgres_Statistics:2', 'Uptime'
    ]
    parser.add_argument('metric', help=help, choices=choices)

    help = "Time range - YYYY-MM-DDTHH"
    parser.add_argument('--timerange', help=help, nargs=2,
                        type=valid_date_time,
                        required=True)

    help = "Output root."
    parser.add_argument('--output', help=help, type=str,
                        default=('/mnt/intra_wwwdev/ncep/ncepintradev/htdocs'
                                 '/ncep_common/nowcoast/check_mk'))

    args = parser.parse_args()

    obj = CheckCheckMK(args.project, args.site, args.tier, args.vmtype,
                       args.metric, args.timerange, args.output)
    obj.run()


def count_nco_log_items():
    """
    Count the number of hits in the apache logs.
    """
    description = "Command line utility for counting hits in apache logs."
    parser = argparse.ArgumentParser(description=description)

    choices = ['idpgis', 'nowcoast', 'nowcoastqa']
    help = 'Process this project''s logs.'
    parser.add_argument('project', choices=choices, help=help)

    args = parser.parse_args()

    dest = pathlib.Path.home()
    dest = dest / 'data' / 'logs' / 'nco' / args.project / 'hits.csv'

    today = datetime.date.today()

    obj = DailyApacheLogCount(args.project, today, dest)
    obj.run()


def plot_nco_hits():
    """
    Plot the number of hits in the apache logs.
    """
    description = "Command line utility for plotting hits in apache logs."
    parser = argparse.ArgumentParser(description=description)

    choices = ['idpgis', 'nowcoast', 'nowcoastqa']
    help = 'Process this project''s logs.'
    parser.add_argument('project', choices=choices, help=help)

    args = parser.parse_args()

    src = pathlib.Path.home()
    src = src / 'data' / 'logs' / 'nco' / args.project / 'hits.csv'

    obj = DailyApacheLogCountPlot(args.project, src)
    obj.run()
