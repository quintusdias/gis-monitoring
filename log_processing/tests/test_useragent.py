# Standard libraary imports
import os
import pathlib
import tempfile
from unittest.mock import patch

# 3rd party library imports
import pandas as pd

# Local imports
from arcgis_apache_logs import UserAgentProcessor
from .test_core import TestCore


class TestSuite(TestCore):

    def setUp(self):
        """
        Create a temporary directory in which to create artifacts (often the
        current directory).
        """

        self.starting_dir = pathlib.Path.cwd()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        os.chdir(self.tempdir.name)

        fake_home_dir = tempfile.TemporaryDirectory()
        self.fake_home_dir = pathlib.Path(fake_home_dir.name)
        self.addCleanup(fake_home_dir.cleanup)

        patchee = 'arcgis_apache_logs.common.pathlib.Path.home'
        self.homedir_patcher = patch(patchee, return_value=self.fake_home_dir)
        self.homedir_patcher.start()

    def tearDown(self):
        """
        Change back to the starting directory and remove any artifacts created
        during a test.
        """
        os.chdir(self.starting_dir)

        self.homedir_patcher.stop()

    def test_user_agent_database_tables_not_initialized(self):
        """
        SCENARIO:  The database does not exist.

        EXPECTED RESULT:  The database is initialized.  There should be
        two tables.
        """
        r = UserAgentProcessor('idpgis')

        sql = """
              SELECT name
              FROM sqlite_master
              WHERE type='table' AND name NOT LIKE 'sqlite_%'
              ORDER BY name
              """
        actual = pd.read_sql(sql, r.conn)

        table_names = ['known_user_agents', 'user_agent_logs']
        expected = pd.Series(table_names, name='name')
        pd.testing.assert_series_equal(actual['name'], expected)
