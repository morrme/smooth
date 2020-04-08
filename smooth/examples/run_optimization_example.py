from smooth.examples.example_model import mymodel
from smooth import run_optimization
import smooth
from multiprocessing import freeze_support

import logging
logging.getLogger('pyomo.core').setLevel(logging.ERROR)

def main():
    # Define the optimization parameter. This dict needs the following information:
    #  ga_params: Genetic algorithm parameters [dict].
    #  attribute_variation: Information on the attributes to vary [list].
    opt_params = dict()
    # Define the variables for the genetic algorithm:
    #  pop_size: Number of individuals in the population [-].
    #  n_gen: Number of generations that will be evaluated [-].
    #  n_core: Number of cores used in the optimization ('max' will use all of them) [-].
    # generation: dictionary with relative number of individuals to select, crossover and mutate in each generation.
    # With a population_size of 30, a 2/3/5 generation:
    # - selects 6 best individuals without change
    # - generates at most 9 children through crossover of these 6 selected
    # - generates at least 15 children through mutation of the 6 selected
    # weights: tuple controlling fitness function of optimization.
    # negative numbers minimize, the absolute value describes relative importance.
    # First value is linked to cost, the second to emissions.
    # (-1, -1) means minimze costs and emissions, with equal importance.
    opt_params['ga_params'] = {
        'population_size': 30,
        'n_generation': 15,
        'n_core': 'max',
        'generation': {'select': 2, 'crossover': 3, 'mutate': 5},
        'weights': (-1, -1),
    }
    # Define the attribute variation information that will be used by the genetic algorithm.
    #  comp_name: Name of the component [string].
    #  comp_attribute: Name of the attribute to be varied [string].
    #  val_min: Min. value in variation process [int/float].
    #  val_max: Max. value in variation process [int/float].
    #  val_step: Step size in variation process [int/float].
    #
    # E.g. the combination val_min = 5, val_max = 60 and val_step = 10 lead to possible values 5, 15, 25, 35, 45 and 55.
    var_ely_power = {
        'comp_name': 'this_ely',
        'comp_attribute': 'power_max',
        'val_min': 100e3,
        'val_max': 2000e3,
        'val_step': 100e3
    }
    var_storage_capacity = {
        'comp_name': 'h2_storage',
        'comp_attribute': 'storage_capacity',
        'val_min': 50,
        'val_max': 2000,
        'val_step': 50
    }
    # Add the attribute variation info to the optimization parameters.
    opt_params['attribute_variation'] = [var_ely_power, var_storage_capacity]

    # Run an optimization example.
    return run_optimization(opt_params, mymodel)


if __name__ == '__main__':
    freeze_support()
    optimization_results = main()
    # smooth.save_results('optimization_result', optimization_results)
    smooth.plot_optimization_results(optimization_results)
