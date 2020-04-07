import importlib
from oemof import solph
from oemof.outputlib import processing
from smooth.framework.simulation_parameters import SimulationParameters as sp
from smooth.framework.functions.debug import get_df_debug, show_debug
from smooth.framework.exceptions import SolverNonOptimalError


def run_smooth(model):
    # Run the smooth simulation framework.
    # Parameters:
    #  model: smooth model object containing parameters for components, simulation and busses.

    """ INITIALIZATION """
    # legacy: components may be list. Convert to dict.
    if isinstance(model["components"], list):
        names = [c.pop("name") for c in model["components"]]
        model.update({'components': dict(zip(names, model["components"]))})

    # GET SIMULATION PARAMETERS
    # Create an object with the simulation parameters.
    sim_params = sp(model['sim_params'])

    # CREATE COMPONENT OBJECTS
    components = []
    for name, this_comp in model['components'].items():
        # Add simulation parameters to the components so they can be used
        this_comp['sim_params'] = sim_params
        # assign unique name
        this_comp['name'] = name
        # load the component class.
        this_comp_name = this_comp['component']
        # Import the module of the component.
        this_comp_module = importlib.import_module('smooth.components.component_' + this_comp_name)
        # While class name is camel case, underscores has to be removed and letters after underscores have to be capital
        class_name = ''
        if this_comp_name.isupper():
            class_name = this_comp_name
        else:
            this_comp_name_split = this_comp_name.split('_')
            for this_comp_name_part in this_comp_name_split:
                class_name += this_comp_name_part.capitalize()
        # Load the class (which by convention has a name with a capital first letter and camel case).
        this_comp_class = getattr(this_comp_module, class_name)
        # Initialize the component.
        this_comp_obj = this_comp_class(this_comp)
        # Check if this component is valid.
        this_comp_obj.check_validity()
        # Add this component to the list containing all components.
        components.append(this_comp_obj)

    # There are no results yet.
    df_results = None
    results_dict = None

    """ SIMULATION """
    for i_interval in range(sim_params.n_intervals):
        # Save the interval index of this run to the sim_params to make it usable later on.
        sim_params.i_interval = i_interval
        if sim_params.print_progress:
            print('Simulating interval {}/{}'.format(i_interval+1, sim_params.n_intervals))

        # Initialize the oemof energy system for this time step.
        this_time_index = sim_params.date_time_index[i_interval: (i_interval + 1)]
        oemof_model = solph.EnergySystem(timeindex=this_time_index, freq='{}min'.format(sim_params.interval_time))

        """ CREATE THE OEMOF MODEL FOR THIS INTERVAL """
        # Create all busses and save them to a dict for later use in the components.
        busses = {}

        for i_bus in model['busses']:
            # Create this bus and append it to the "busses" dict.
            busses[i_bus] = solph.Bus(label=i_bus)
            # Add the bus to the simulation model.
            oemof_model.add(busses[i_bus])

        # Prepare the simulation.
        for this_comp in components:
            # Execute the prepare simulation step (if this component has one).
            this_comp.prepare_simulation(components)
            # Get the oemof representation of this component.
            this_oemof_model = this_comp.create_oemof_model(busses, oemof_model)
            if this_oemof_model is not None:
                # Add the component to the oemof model.
                oemof_model.add(this_oemof_model)
            else:
                # If None is given back, no model is supposed to be added.
                pass

        """ RUN THE SIMULATION """
        # Do the simulation for this time step.
        model_to_solve = solph.Model(oemof_model)

        for this_comp in components:
            this_comp.update_constraints(busses, model_to_solve)

        if i_interval == 0:
            # Save the set of linear equations for the first interval.
            model_to_solve.write('./oemof_model.lp', io_options={'symbolic_solver_labels': True})

        oemof_results = model_to_solve.solve(solver='cbc', solve_kwargs={'tee': False})

        """ CHECK IF SOLVING WAS SUCCESSFUL """
        # If the status and temination condition is not ok/optimal, get and print the current flows and status
        status = oemof_results["Solver"][0]["Status"].key
        termination_condition = oemof_results["Solver"][0]["Termination condition"].key
        if status != "ok" and termination_condition != "optimal":
            new_df_results = processing.create_dataframe(model_to_solve)
            df_debug = get_df_debug(df_results, results_dict, new_df_results)
            show_debug(df_debug, components)
            raise SolverNonOptimalError('solver status: ' + status + " / termination condition: " + termination_condition)

        """ HANDLE RESULTS """
        # Get the results of this oemof run.
        results = processing.results(model_to_solve)
        results_dict = processing.parameter_as_dict(model_to_solve)
        df_results = processing.create_dataframe(model_to_solve)

        # Loop through every component and call the result handling functions
        for this_comp in components:
            # Update the flows
            this_comp.update_flows(results, sim_params)
            # Update the states.
            this_comp.update_states(results, sim_params)
            # Update the costs and artificial costs.
            this_comp.update_var_costs(results, sim_params)
            # Update the costs and artificial costs.
            this_comp.update_var_emissions(results, sim_params)

    # Calculate the annuity for each component.
    for this_comp in components:
        this_comp.generate_results()

    return components, status
