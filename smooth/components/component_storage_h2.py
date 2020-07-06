import oemof.solph as solph
from .component import Component
from oemof.outputlib import views


class StorageH2 (Component):
    def __init__(self, params):

        # Call the init function of the mother class.
        Component.__init__(self)

        # ------------------- PARAMETERS -------------------
        self.name = 'Storage_default_name'

        # Define the hydrogen bus the storage is connected to.
        self.bus_in = None
        self.bus_out = None
        # Min. and max. pressure [bar].
        self.p_min = 0
        self.p_max = 450
        # Storage capacity at p_max (usable storage + min storage) [kg].
        self.storage_capacity = 500
        # Life time [a].
        self.life_time = 20
        # The initial storage level as a factor of the capacity [-]
        self.initial_storage_factor = 0.5
        # If balanced is True, the final storage level is force to be equal to the initial value,
        # by fixing the value
        # TODO: otherwise the cost of the initially stored hydrogen is incorporated into the final
        #  cost
        self.balanced = False
        self.fixed = False
        # Nb. of intervals to the end, where the balance ratio is applied for VAC calculation.
        self.balance_vac_interval = None
        # Difference to initial storage level in relation to the max. chargable H_2 until the end
        self.balance_ratio = 0
        # Max chargeable hydrogen in one time step in kg/h
        self.delta_max = None
        # Minimal flow needed in current timestep to attain the same storage level as at the start
        self.min_out = 0
        self.min_in = 0
        # The storage level wanted as a factor of the capacity
        self.slw_factor = None

        # ------------------- PARAMETERS (VARIABLE ARTIFICIAL COSTS - VAC) -------------------
        # Normal var. art. costs for charging (in) and discharging (out) the storage [EUR/kg].
        self.vac_in = 0
        self.vac_out = 0
        # Var. art. costs that apply if the storage level is below the wanted
        # storage level [EUR/kg].
        self.vac_low_in = 0
        self.vac_low_out = 0
        # Var. art. costs that apply as a scaling value if the storage level is set to be balanced
        # to the initial level by the end of simulation [EUR/kg].
        self.vac_bal_in = 0
        self.vac_bal_out = 0

        # ------------------- UPDATE PARAMETER DEFAULT VALUES -------------------
        self.set_parameters(params)
        # Initial storage level [kg].
        self.storage_level_init = self.initial_storage_factor * self.storage_capacity
        # If a storage level is set as wanted, the vac_low costs apply if the
        # storage is below that level [kg].
        if self.slw_factor is not None:
            self.storage_level_wanted = self.slw_factor * self.storage_capacity
        else:
            self.storage_level_wanted = None

        # max chargeable hydrogen in one time step in kg/h
        if self.delta_max is None:
            self.delta_max = self.storage_capacity

        # ------------------- CONSTANTS FOR REAL GAS EQUATION -------------------
        # Critical temperature [K] and pressure [Pa], molar mass of H2
        # [kg/mol], the gas constant [J/(K*mol)].
        self.T_crit = 33.19
        self.p_crit = 13.13 * 1e5
        self.Mr = 2.016 * 1e-3
        self.R = 8.314
        # Redlich Kwong EoS - Parameters
        self.rk_a = 0.1428
        self.rk_b = 1.8208e-5

        # ----- FURTHER STORAGE VALUES DEPENDANT ON THE PRESSURE/CAPACITY -----
        # Calculate the storage volume [m³].
        self.V = self.get_volume(self.p_max, self.storage_capacity)
        # Calculate the mass at p_min, which can't be used [kg].
        self.storage_level_min = self.get_mass(self.p_min)
        # Asserts that the initial storage level must be greater than the minimum storage
        # level
        assert self.storage_level_init >= self.storage_level_min

        # ------------------- STATES -------------------
        # Storage level [kg of h2]
        self.storage_level = min(self.storage_level_init, self.storage_capacity)
        # Storage pressure [bar].
        self.pressure = self.get_pressure(self.storage_level)

        # ------------------- VARIABLE ARTIFICIAL COSTS -------------------
        # Store the current artificial costs for input and output [EUR/kg].
        self.current_vac = [0, 0]

    def prepare_simulation(self, components):
        # Nb. or Intervals until end of simulation
        self.intervals_to_end = self.sim_params.n_intervals - self.sim_params.i_interval
        # Amount of hydrogen to charge to attain balance to initial storage level; can be negative
        self.charge_balance = self.storage_level_init - self.storage_level
        # Minimum flow is zero if the remaining timesteps are sufficient to balance the storage
        # level given the maximum flow constraint, otherwise it is equal to the flow needed.
        self.min_out = max(0,
                           - self.charge_balance - self.delta_max * (self.intervals_to_end - 1))
        self.min_in = max(0,
                          self.charge_balance - self.delta_max * (self.intervals_to_end - 1))

        # Absolute value of the balance_ratio rises towards end of simulation.
        # Given min_out/in the ratio cannot exceed [-1,1].
        self.balance_ratio = self.charge_balance / (self.delta_max * self.intervals_to_end)

        # Set the var. art. costs.
        vac_in = self.vac_in
        vac_out = self.vac_out
        if self.balanced and self.min_in != 0 or self.min_out != 0:
            # Initial and final storage levels should be balanced out
            # If there is a minimal flow needed, the flow value will be fixed to that value
            self.fixed = True

        # At an interval, if balance vac apply, storage_level_wanted is not considered
        if self.balance_vac_interval is not None \
                and self.intervals_to_end <= self.balance_vac_interval:
            # If a balance should be incentivized,
            # the balance VAC scaled balance_ratio value from above apply
            vac_in = -self.vac_bal_in * self.balance_ratio
            vac_out = self.vac_bal_in * self.balance_ratio
        else:
            if self.storage_level_wanted is not None \
                    and self.storage_level < self.storage_level_wanted:
                # If a wanted storage level is set and the storage level fell below
                # that wanted level, the low VAC apply.
                vac_in = self.vac_low_in
                vac_out = self.vac_low_out

        self.current_vac = [vac_in, vac_out]


    def create_oemof_model(self, busses, _):
        storage = solph.components.GenericStorage(
            label=self.name,
            outputs={busses[self.bus_out]: solph.Flow(
                nominal_value=self.delta_max, variable_costs=self.current_vac[1], max=1.0,
                actual_value=self.min_out/self.delta_max, fixed=self.fixed
            )},
            inputs={busses[self.bus_in]: solph.Flow(
                nominal_value=self.delta_max, variable_costs=self.current_vac[0], max=1.0,
                actual_value=self.min_in/self.delta_max, fixed=self.fixed
            )},
            initial_storage_level=self.storage_level / self.storage_capacity,
            nominal_storage_capacity=self.storage_capacity,
            min_storage_level=self.storage_level_min / self.storage_capacity,
            balanced=False)
        return storage

    def update_states(self, results, sim_params):
        data_storage = views.node(results, self.name)
        df_storage = data_storage['sequences']

        # Loop Through the data frame values and update states accordingly.
        for i_result in df_storage:
            if i_result[1] == 'capacity':
                if 'storage_level' not in self.states:
                    # Initialize an array that tracks the state stored mass.
                    self.states['storage_level'] = [None] * sim_params.n_intervals
                    self.states['vac'] = [None] * sim_params.n_intervals
                    self.states['pressure'] = [None] * sim_params.n_intervals
                # Check if this result is the storage capacity.
                self.storage_level = df_storage[i_result][0]
                self.states['storage_level'][sim_params.i_interval] = self.storage_level
                self.states['vac'][sim_params.i_interval] = self.current_vac
                # Get the storage pressure [bar].
                self.pressure = self.get_pressure(self.storage_level)
                self.states['pressure'][sim_params.i_interval] = self.pressure

    def get_mass(self, p, V=None):
        # Calculate the mass of the storage at a certain pressure.
        # Parameters:
        #  p: pressure [bar].
        #  V: storage volume [m³].

        if V is None:
            V = self.V

        # If p_min is set to 0, the whole capacity should be usable, thus m will be zero as well.
        if V > 0 and p == 0:
            return 0

        # Storage temperature [K].
        T = 273.15 + 25
        # Convert pressure form bar to Pa [Pa].
        p = p * 1e5
        # The mass has to be defined in an iterative process by changing the spec. volume [m³/mol].
        v_spec = 10
        for i in range(10):
            v_spec = (
                self.R * T / (p + (self.rk_a / (T**0.5 * v_spec * (v_spec + self.rk_b))))
            ) + self.rk_b

        # Calculate the mass [kg].
        m = V * self.Mr / v_spec
        return m

    def get_volume(self, p, m):
        # Calculate the volume needed to fit a certain mass at given pressure.
        # Parameters:
        #  p: pressure [bar].
        #  m: mass [kg].

        # Storage temperature [K].
        T = 273.15 + 25
        # Convert pressure form bar to Pa [Pa].
        p = p * 1e5
        # The mass has to be defined in an iterative process by changing the spec. volume [m³/mol].
        v_spec = 10
        for i in range(10):
            v_spec = (
                self.R * T / (p + (self.rk_a / (T**0.5 * v_spec * (v_spec + self.rk_b))))
            ) + self.rk_b

        # Calculate the volume [m3]
        V = m * v_spec / self.Mr
        return V

    def get_pressure(self, m):
        # Calculate the storage pressure for a given mass.
        # Parameters:
        #  m: mass [kg].

        # Storage volume [m³].
        V = self.V
        # Storage temperature [K].
        T = 273.15 + 25
        # Calculate the storage pressure [Pa].
        p = self.R * T / (V * self.Mr / m - self.rk_b) - \
            self.rk_a / (T**0.5 * V * self.Mr / m * (V * self.Mr / m + self.rk_b))
        # Return pressure in bar [bar].
        return p / 1e5
