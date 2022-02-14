from typing import List
from gladier import GladierBaseTool, generate_flow_definition


def ssx_plot(**data):
    import numpy as np
    from matplotlib import pyplot as plt
    import os
    import json
    import re
    import glob 

    data_dir = data['data_dir']
    proc_dir = data['proc_dir']
    upload_dir = data['upload_dir']
    run_num = data['run_num']

    beamline_file_name = f'beamline_run{run_num}.json'
    beamline_file = os.path.join(data_dir, beamline_file_name)

    with open(beamline_file, 'r') as fp:
        beamline_metadata = json.load(fp)
        user_input = beamline_metadata.get('user_input', {})
    
    x_num_steps= user_input.get('x_num_steps')
    y_num_steps= user_input.get('y_num_steps')
    plot_filename=os.path.join(upload_dir, 'composite.png')

    int_indices=[]
    for int_file in glob.glob(os.path.join(proc_dir,'int-*.pickle')):
        int_match = re.match(r'int-\d+-\w+_\d+_(\d+).pickle', int_file)
        if int_match:
            int_index = int_match.groups()
            int_indices.append(int(int_index))    

    lattice_counts = np.zeros(x_num_steps*y_num_steps, dtype=np.dtype(int))

    for index in int_indices:
        lattice_counts[index] += 1
    lattice_counts = lattice_counts.reshape((y_num_steps, x_num_steps))
    # reverse the order of alternating rows
    lattice_counts[1::2, :] = lattice_counts[1::2, ::-1]

    # plot the lattice counts
    plt.figure(figsize=(x_num_steps/10., y_num_steps/10.))
    plt.axes([0, 0, 1, 1])  # Make the plot occupy the whole canvas
    plt.axis('off')
    plt.imshow(lattice_counts, cmap='hot', interpolation=None, vmax=4)
    plt.savefig(plot_filename)
    return plot_filename


@generate_flow_definition(modifiers={
    'ssx_plot': {'endpoint': 'funcx_endpoint_non_compute'}
})
class SSXPlot(GladierBaseTool):

    flow_input = {}

    required_input = [
        'funcx_endpoint_non_compute',
    ]

    funcx_functions = [
        ssx_plot,
    ]
