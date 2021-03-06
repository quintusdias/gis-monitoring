from setuptools import setup

scripts = [
    'bb_flag_history',
    'bin_daily_apache_log_file',
    'ccmk',
    'collect_arcsoc_counts',
    'count_nco_log_items',
    'plot_nco_hits',
]
console_scripts = [f"{item}=gis_utilities.commandline:{item}"
                   for item in scripts]

kwargs = {
    'name': 'gis_utilities',
    'author': 'John Evans',
    'author_email': 'john.g.evans@noaa.gov',
    'url': 'https://vlab.ncep.noaa.gov/redmine/projects/gis-monitoring',
    'description': 'Tools for detecting abusive users',
    'entry_points': {
        'console_scripts': console_scripts,
    },
    'packages': ['gis_utilities'],
    'package_data': {
        'gis_utilities': ['etc/webalizer.conf']
    },
    'install_requires': [
        'apache_log_parser',
        'openpyxl>=2.4.0',
        'pandas',
        'tables>=3.3.0',
        'scikit-image',
    ],
    'version': '0.0.6',
}

setup(**kwargs)
