# Standard library imports
import datetime as dt
import importlib.resources as ir

# 3rd party library imports
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg2
import seaborn as sns

# Local imports
from .common import CommonProcessor
from . import sql

sns.set()


class UserAgentProcessor(CommonProcessor):
    """
    Attributes
    ----------
    conn : obj
        database connectivity
    database : path or str
        Path to database
    project : str
        Either nowcoast or idpgis
    time_series_sql : str
        SQL to collect a coherent timeseries of folder/service information.
    """
    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        """
        super().__init__(**kwargs)

        self.time_series_sql = """
            SELECT a.date, SUM(a.hits) as hits, SUM(a.errors) as errors,
                   SUM(a.nbytes) as nbytes, b.name as user_agent
            FROM user_agent_logs a
            INNER JOIN user_agent_lut b
            ON a.id = b.id
            GROUP BY a.date, user_agent
            ORDER BY a.date
            """

        self.data_retention_days = 7

    def verify_database_setup(self):
        """
        Verify that all the database tables are setup properly for managing
        the user_agents.
        """
        pass

    def process_raw_records(self, df):
        """
        We have reached a limit on how many records we accumulate before
        processing.  Turn what we have into a dataframe and aggregate it
        to the appropriate granularity.
        """
        self.logger.info(f"user agents:  processing {len(df)} raw records")

        columns = ['date', 'user_agent', 'hits', 'errors', 'nbytes']
        df = df[columns].copy()

        # Aggregate by the set frequency and user_agent, taking sums.
        groupers = [pd.Grouper(freq=self.frequency), 'user_agent']
        df = df.set_index('date').groupby(groupers).sum().reset_index()

        # Have to have the same column names as the database.
        df = self.replace_user_agents_with_ids(df)

        df = self.merge_with_database(df, 'user_agent_logs')

        self.to_table(df, 'user_agent_logs')

        # Reset for the next round of records.
        self.records = []

        self.logger.info("user agents:  done processing raw records")

    def replace_user_agents_with_ids(self, df):
        """
        Record any new user agents and get IDs for them.
        """
        self.logger.info('about to update the user agent LUT...')

        # Try upserting all the current referers.  If a user agent is already
        # known, then do nothing.
        sql = f"""
        insert into user_agent_lut (name) values %s
        on conflict on constraint user_agent_exists do nothing
        """
        args = ((x,) for x in df.user_agent.unique())
        psycopg2.extras.execute_values(self.cursor, sql, args, page_size=1000)

        # Get the all the IDs associated with the referers.  Fold then back
        # into our data frame, then drop the referers because we don't need
        # them anymore.
        sql = f"""
               SELECT id, name from user_agent_lut
               """
        known_referers = pd.read_sql(sql, self.conn)

        df = pd.merge(df, known_referers,
                      how='left', left_on='user_agent', right_on='name')

        df = df.drop(['user_agent', 'name'], axis='columns')
        self.logger.info('finished updating the user agent LUT...')
        return df

    def preprocess_database(self):
        """
        Clean out the user agent tables on mondays.
        """
        self.logger.info('preprocessing user agents ...')

        if dt.date.today().weekday() != 0:
            return

        query = ir.read_text(sql, 'prune_user_agents.sql') 
        self.logger.info(query)
        self.cursor.execute(query)

        self.conn.commit()

    def process_graphics(self, html_doc):
        self.get_timeseries()
        self.summarize_user_agents(html_doc)
        self.summarize_transactions(html_doc)
        self.summarize_bandwidth(html_doc)

    def get_top_user_agents(self):
        # who are the top user_agents for today?
        df = self.df_today.copy()

        df['valid_hits'] = df['hits'] - df['errors']
        top_user_agents = (df.groupby('user_agent')
                             .sum()
                             .sort_values(by='valid_hits', ascending=False)
                             .head(n=7)
                             .index)

        return top_user_agents

    def summarize_bandwidth(self, html_doc):
        """
        Create a PNG showing the top user_agents (bytes) over the last few
        days.
        """
        top_user_agents = self.get_top_user_agents()

        # Now restrict the hourly data over the last few days to those
        # user_agents.  Then restrict to valid hits.  And rename valid_hits to
        # hits.
        idx = self.df.user_agent.isin(top_user_agents)
        df = self.df[idx].sort_values(by='date')
        df = df[['date', 'user_agent', 'nbytes']]
        df['nbytes'] /= (1024 ** 3)

        df = df.pivot(index='date', columns='user_agent', values='nbytes')

        # Order them by max value.
        s = df.max().sort_values(ascending=False)
        df = df[s.index]

        fig, ax = plt.subplots(figsize=(15, 7))
        df.plot(ax=ax)

        kwargs = {
            'title': 'GBytes per Hour',
            'filename': f'{self.project}_user_agents_bytes.png',
        }
        self.write_html_and_image_output(df, html_doc, **kwargs)

    def summarize_transactions(self, html_doc):
        """
        Create a PNG showing the top user_agents over the last few days.
        """
        top_user_agents = self.get_top_user_agents()

        df = self.df.copy()

        # Now restrict the hourly data over the last few days to those
        # user_agents.  Then restrict to valid hits.  And rename valid_hits to
        # hits.
        idx = df.user_agent.isin(top_user_agents)
        df = df[idx].sort_values(by='date').copy()

        df['hits'] = df['hits'] - df['errors']
        df = df[['date', 'user_agent', 'hits']]

        # Rescale them from hits/hour to hits/second
        df['hits'] /= 3600

        df = df.pivot(index='date', columns='user_agent', values='hits')

        # Order them by max value.
        s = df.max().sort_values(ascending=False)
        df = df[s.index]

        fig, ax = plt.subplots(figsize=(15, 7))
        df.plot(ax=ax)

        kwargs = {
            'title': (
                'Hits per Second (averaged per hour, not including errors)'
            ),
            'filename': f'{self.project}_user_agents_hits.png',
        }
        self.write_html_and_image_output(df, html_doc, **kwargs)

    def summarize_user_agents(self, html_doc):
        """
        Calculate

              I) percentage of hits for each user_agent
             II) percentage of hits for each user_agent that are 403s
            III) percentage of total 403s for each user_agent

        Just for the latest day, though.
        """
        df = self.df_today.copy().groupby('user_agent').sum()

        total_hits = df['hits'].sum()
        total_bytes = df['nbytes'].sum()
        total_errors = df['errors'].sum()

        df = df[['hits', 'nbytes', 'errors']].copy()
        df['hits %'] = df['hits'] / total_hits * 100
        df['GBytes'] = df['nbytes'] / (1024 ** 3)  # GBytes
        df['GBytes %'] = df['nbytes'] / total_bytes * 100

        idx = df['errors'].isnull()
        df.loc[idx, ('errors')] = 0
        df['errors'] = df['errors'].astype(np.uint64)

        df['errors: % of all hits'] = df['errors'] / total_hits * 100
        df['errors: % of all errors'] = df['errors'] / total_errors * 100

        # Reorder the columns
        reordered_cols = [
            'hits',
            'hits %',
            'GBytes',
            'GBytes %',
            'errors',
            'errors: % of all hits',
            'errors: % of all errors'
        ]
        df = df[reordered_cols]
        df = df.sort_values(by='hits', ascending=False).head(15)

        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        kwargs = {
            'aname': 'user_agents',
            'atext': 'Top UserAgents',
            'h1text': f'Top UserAgents by Hits: {yesterday}'
        }
        self.create_html_table(df, html_doc, **kwargs)
