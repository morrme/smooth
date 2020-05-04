from smooth.components.component import Component
from smooth.framework.simulation_parameters import SimulationParameters as sp


class TestSimParam:
    @classmethod
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        sim_params = {
            'start_date': '1/1/2019',
            'n_intervals': 10,
            'interval_time': 60,
            'interest_rate': 0.03,
            'print_progress': True,
        }
        self.sim_params = sp(sim_params)

    def test_sim_params(self):
        assert self.sim_params.interest_rate is not None
        # TODO
