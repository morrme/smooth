from smooth.examples.example_dict_model import mymodel
from smooth import run_smooth
from smooth import print_smooth_results
from smooth import save_results
from smooth import plot_smooth_results

# Run an example.
smooth_result, status = run_smooth(mymodel)
plot_smooth_results(smooth_result)
