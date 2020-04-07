import os
import oemof.solph as solph
from .component import Component
import oemof.thermal.compression_heatpumps_and_chillers as cmpr_hp_chiller
import smooth.framework.functions.functions as func
import pandas as pd

class AirSourceHeatPump(Component):
    """ An air source heat pump component is created through this class """

    def __init__(self, params):

        # Call the init function of the mother class.
        Component.__init__(self)

        """ PARAMETERS """
        self.name = 'Heat_pump_default_name'

        self.bus_el = None
        self.bus_th = None

        # Max. heating output [W]
        self.power_max = 1000e3

        self.csv_filename = None
        self.csv_separator = ','
        self.column_title = 0
        self.path = os.path.dirname(__file__)

        """ PARAMETERS BASED ON OEMOF THERMAL EXAMPLE """
        # Temperature below which icing occurs [deg C]
        self.temp_threshold_icing = 2
        # The output temperature from the heat pump [deg C]
        self.temp_high = [40]
        # The ambient temperature [deg C]
        self.temp_low = 10
        # Quality grade of heat pump [-]
        self.quality_grade = 0.4
        # Can be set to heat pump or chiller
        self.mode = 'heat_pump'
        # COP reduction caused by icing [-]
        self.factor_icing = 0.8
        # Ask Jann about this/look more into detail
        self.consider_icing = False

        """ UPDATE PARAMETER DEFAULT VALUES """
        self.set_parameters(params)

        if self.csv_filename is not None:
            # A csv file containing data for the ambient temperature is required [deg C]
            self.temp_low = func.read_data_file(self.path, self.csv_filename, self.csv_separator, self.column_title)
            self.temp_low_series = self.temp_low[self.column_title]
        else:
            self.temp_low_list = [self.temp_low] * self.sim_params.n_intervals
            self.temp_low_series = pd.Series(self.temp_low_list)

        # A function taken from oemof thermal that calculates the coefficient of performance (pre-calculated)
        self.cops = cmpr_hp_chiller.calc_cops(self.temp_high, self.temp_low_series, self.quality_grade,
                                              self.temp_threshold_icing,
                                              self.consider_icing, self.factor_icing, self.mode)

    def create_oemof_model(self, busses, _):
        air_source_heat_pump = solph.Transformer(
            label=self.name,
            inputs={busses[self.bus_el]: solph.Flow(variable_costs=0)},
            outputs={busses[self.bus_th]: solph.Flow(
                nominal_value=self.power_max,
                variable_costs=0)},
            conversion_factors={busses[self.bus_th]: self.cops[self.sim_params.i_interval]}
            )
        return air_source_heat_pump

