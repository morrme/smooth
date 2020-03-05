from smooth.framework.functions.functions import read_data_file, get_date_time_index, get_sim_time_span, interval_time_index
import pandas as pd


def test_get_date_time_index():
    # Function defining the parameters for perfect/myopic foresight:
    # Parameters:
    #  start_date: the first evaluated time period (e.g. '1/1/2019') [string].
    #  n_intervals: number of times the 'for' loop should run [-].
    #  step_size: Size of one time step [min].

    date_time_index = get_date_time_index('1/1/2020', 3, 60)
    assert date_time_index.equals(pd.DatetimeIndex(['2020-01-01 00:00:00',
                                                    '2020-01-01 01:00:00',
                                                    '2020-01-01 02:00:00']))


def test_interval_time_index():
    # Function to divide the set date time index into hourly intervals.
    # Parameters:
    #  date_time_index: chosen date range for the model
    #  this_time_index: the time at each 'for' loop

    date_time_index = get_date_time_index('1/1/2020', 3, 60)
    this_time_index = interval_time_index(date_time_index, 1)
    assert (this_time_index == '2020-01-01 01:00:00').all()


def test_get_sim_time_span():
    # Calculate the time span of the simulation.
    # Return the time delta in minutes [min].
    # Parameters:
    #  n_interval: number of intervals [-].
    #  step_size: Size of one time step [min].

    assert get_sim_time_span(3, 15) == 3 * 15


