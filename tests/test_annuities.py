import pytest
from smooth.framework.functions.update_annuities import update_annuities, calc_annuity, calc_annual_emissions
from smooth.components.component import Component
from smooth.framework.simulation_parameters import SimulationParameters as sp


class TestAnnuities:
    @classmethod
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        capex = {
            'key': ['free', 'spec'],
            'fitting_value': [[193, -0.366], 'cost'],
            'dependant_value': ['power_max', 'power_max']
        }

        sim_params = {
            'start_date': '1/1/2019',
            'n_intervals': 10,
            'interval_time': 60,
            'interest_rate': 0.03,
            'print_progress': True,
        }
        self.component = Component()
        self.component.life_time = 20
        self.component.capex = capex
        self.component.sim_params = sp(sim_params)
        self.target = {'cost': 10}

    def test_calc_annuities(self):
        assert (round(calc_annuity(self.component, None)) == 0)
        assert (round(calc_annuity(self.component, {})) == 0)

    def test_update_annuities_error(self):
        self.component.life_time = None
        with pytest.raises(ValueError):
            self.component.check_validity()
        self.component.life_time = 0
        with pytest.raises(ValueError):
            self.component.check_validity()

    # def test_update_annuities_results(self):
    #     with pytest.raises(Exception):
    #         update_annuities(self.component)
    #     # assert self.component.results is not None
    #     # TODO change test values
    #     # capex_annuity = 1
    #     # opex = 2
    #     # variable_cost_annuity = 3
    #     # assert self.component.results['annuity_capex'] == capex_annuity
    #     # assert self.component.results['annuity_opex'] == opex
    #     # assert self.component.results['annuity_variable_costs'] == variable_cost_annuity
    #     # assert self.component.results['annuity_total'] == capex_annuity + opex + variable_cost_annuity

    def test_calc_annuities_emissions(self):
        assert calc_annual_emissions(self.component, None) == 0
        assert calc_annual_emissions(self.component, 0) == 0
        assert calc_annual_emissions(
            self.component, self.target) == self.target['cost'] / self.component.life_time
