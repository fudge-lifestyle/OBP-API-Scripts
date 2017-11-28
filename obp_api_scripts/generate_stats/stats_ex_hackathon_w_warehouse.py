# -*- coding: utf-8 -*-

# Answer a few questions about statistics not easily possible using SQL only


import datetime
import psycopg2
import statistics

from .stats import pretty_decoration, DATE_FORMAT, SQL_DATE_RANGE_FORMAT

from settings import (
    DATABASE,
    DATE_START, DATE_END, DATE_BEFORE, DATE_AFTER,
)


class Stats(object):
    """
    Calculate statistics about the usage of a sandbox
    """

    def __init__(self):
        connstring = "host='{}' dbname='{}' user='{}' password='{}'"
        self.connection = psycopg2.connect(connstring.format(
            DATABASE['host'],
            DATABASE['name'],
            DATABASE['user'],
            DATABASE['password']))
        self.sql  = {
            'date_range': "((createdat >= to_timestamp('{}', 'yyyy-mm-dd hh24:mi:ss') AND createdat <= to_timestamp('{}', 'yyyy-mm-dd hh24:mi:ss')) OR (createdat >= to_timestamp('{}', 'yyyy-mm-dd hh24:mi:ss') AND createdat <= to_timestamp('{}', 'yyyy-mm-dd hh24:mi:ss')))".format(DATE_START, DATE_BEFORE, DATE_AFTER, DATE_END)  # noqa
        }
        self.cursor = self.connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Properly clean up connection resources
        """
        self.cursor.close()
        self.connection.close()

    @pretty_decoration
    def apps(self):
        """
        Gets apps which have been used before DATE_BEFORE and after DATE_AFTER,
        TODO: Filter apps used between DATE_BEFORE and DATE_AFTER
        """
        query = "SELECT resourceuser.email, consumer.name, consumer.description FROM resourceuser, consumer WHERE resourceuser.userid_ = consumer.createdbyuserid AND name <> '' AND {};".format(self.sql['date_range'])  # noqa
        self.cursor.execute(query)
        apps = self.cursor.fetchall()

        query = "SELECT DISTINCT resourceuser.email FROM resourceuser, mappedentitlement WHERE mappedentitlement.mrolename = 'CanSearchWarehouse' AND mappedentitlement.muserid = resourceuser.userid_ ORDER BY resourceuser.email"  # noqa
        self.cursor.execute(query)
        warehouse_users = self.cursor.fetchall()
        # Remove tuple:
        warehouse_users = list(map(lambda x: x[0], warehouse_users))

        users = {}
        print('Used apps between {} and {} or between {} and {}:'.format(DATE_START, DATE_BEFORE, DATE_AFTER, DATE_END))
        print('User email address,App name,App description,User CanSearchWarehouse')  # noqa
        print('/' * 78)
        for a in apps:
            users[a[0]] = True
            can_search_warehouse = True if a[0] in warehouse_users else False
            print('{},{},{},{}'.format(
                a[0],
                a[1].replace(',', '\\,'),
                a[2].replace(',', '\\,'),
                can_search_warehouse)
            )
        print('/' * 78)
        print('Total number of apps: {}'.format(len(apps)))
        print('Total number of users: {}'.format(len(users)))
        names = list(map(lambda x: x[1], apps))
        return names


    def calls_date_range(self, query_fmt, date_start, date_end):
        """
        Prints a distribution of API calls by day
        Called by method calls
        """
        date_range_fmt = "date_c >= to_timestamp('{}', 'yyyy-mm-dd hh24:mi:ss') AND date_c <= to_timestamp('{}', 'yyyy-mm-dd hh24:mi:ss')"
        d_start = datetime.datetime.strptime(date_start, DATE_FORMAT)
        d_end = datetime.datetime.strptime(date_end, DATE_FORMAT)
        d_from = d_start
        d_to = d_start + datetime.timedelta(days=1)
        sum = 0
        while d_to <= d_end:
            date_range = date_range_fmt.format(d_from, d_to)
            query = query_fmt.format(date_range)
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            print('{} - {} # {}'.format(d_from, d_to, result[0]))
            sum += result[0]
            d_from = d_to
            d_to = d_to + datetime.timedelta(days=1)
        return sum

    @pretty_decoration
    def calls(self, app_names):
        """
        Prints how many calls were made in total with given app names
        """
        wrapped_app_names = ', '.join(
            map(lambda x: "'{}'".format(x.replace("'", "''")), app_names))
        query_app_names = "SELECT COUNT(*) FROM mappedmetric WHERE appname IN ({})".format(wrapped_app_names)  # noqa
        query_fmt = query_app_names + " AND {}"
        date_range = self.sql['date_range'].replace('createdat', 'date_c')
        query = query_fmt.format(date_range)
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        print('Total calls: {}'.format(result[0]))

        sum0 = self.calls_date_range(query_fmt, DATE_START, DATE_BEFORE)
        print('-' * 10)
        sum1 = self.calls_date_range(query_fmt, DATE_AFTER, DATE_END)
        print('Sanity check: {} calls'.format(sum0+sum1))

    def run_all(self):
        app_names = self.apps()
        self.calls(app_names)
