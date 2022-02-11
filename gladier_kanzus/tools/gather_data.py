from gladier import GladierBaseTool, generate_flow_definition


def ssx_gather_data(**data):
    import re
    import os
    import json
    import shutil
    trigger_name = data['trigger_name']
    data_dir = data['data_dir']
    processing_dir = data['proc_dir']
    upload_dir = data['upload_dir']
    tar_input = data['tar_input']

    sample_metadata = trigger_name.split('/')[-4:]
    assert len(sample_metadata) == 4 and trigger_name.endswith('cbf'), (
        'Invalid sample path, must run with end path resembling: "S9/nsp10nsp16/K/Kaleidoscope_15_22016.cbf"'
        f'Got: {trigger_name}'
    )

    # Gather metadata from path names
    run_name, protein, _, trigger_file = sample_metadata
    match = re.match(r'(\w+)_(\d+)_\d+.cbf', trigger_file)
    if not match:
        raise ValueError(f'Invalid trigger file: {trigger_file}, must match "Kaleidoscope_15_22016.cbf"')
    exp_name, exp_number = match.groups()


    
    if not os.path.exists(upload_dir):
        os.mkdir(upload_dir)
    
    beamline_file = os.path.join(data_dir, f'beamline_run{exp_number}.json')
    shutil.copyfile(beamline_file, os.path.join(upload_dir, os.path.basename(beamline_file)))

    # Fetch the list of ints that 'hit'.
    int_indices = []
    int_filenames = []
    cbf_indices = []
    for filename in os.listdir(processing_dir):
        # match int-0-Kaleidoscope_15_05189.pickle
        int_match = re.match(r'int-(\d+)-(\w+)_(\d+)_(\d+).pickle', filename)
        if int_match:
            int_filenames.append(filename)
            int_number, exp_name, beamline_run, int_index = int_match.groups()
            int_indices.append(int(int_index))
     
        if '.txt' in filename:
            fpath = os.path.join(processing_dir,filename)
            with open(fpath,'r') as f:
                for line in f.readlines():
                    match = re.findall(r"(\d+).cbf", line)
                    if match:
                        cbf_index = int(match[0])
                        cbf_indices.append(cbf_index)
    
    if len(cbf_indices) == 0:
        cbf_indices.append(0)
   
    proc_cbf_file = os.path.join(processing_dir,'proc_cbf.txt')
    
    if os.path.exists(proc_cbf_file):
        os.remove(proc_cbf_file)

    with open(proc_cbf_file,'w+') as f:
        for cbf in sorted(cbf_indices):
            f.write(str(cbf) + "\n")

    proc_ints_file = os.path.join(processing_dir,'proc_ints.txt')
    
    if os.path.exists(proc_ints_file):
        os.remove(proc_ints_file)

    with open(proc_ints_file,'w+') as f:
        for intfile in sorted(int_filenames):
            f.write(str(intfile) + "\n")
            
    batch_info = {
        'cbf_files': len(cbf_indices),
        'cbf_file_range': {'from': min(cbf_indices), 'to': max(cbf_indices)},
        'total_number_of_int_files': len(int_indices)
    }

    # Move int files to the upload dir.
    os.makedirs(tar_input, mode=0o775, exist_ok=True)
    for int_filename in int_filenames:
        shutil.copyfile(os.path.join(processing_dir, int_filename),
                        os.path.join(tar_input, int_filename))

    # Fetch beamline metadata
    with open(beamline_file, 'r') as fp:
        beamline_metadata = json.load(fp)
    user_input = beamline_metadata.get('user_input', {})
    protein = user_input.get('protein_name', protein)

    # Update any metadata in the pilot 'metadata' key
    metadata = data['pilot'].get('metadata', {})
    metadata.update(beamline_metadata)
    metadata.update({
        'chip': exp_name,
        'experiment_number': exp_number,
        'run_name': run_name,
        'protein': protein,
        'trigger_name': trigger_name,
        'batch_info': batch_info,
    })
    data['pilot']['metadata'] = metadata

    return {
        'pilot': data['pilot'],
        'plot': {
            'plot_filename': os.path.join(upload_dir, 'composite.png'),
            'int_indices': sorted(int_indices),
            'x_num_steps': user_input.get('x_num_steps', 0),
            'y_num_steps': user_input.get('y_num_steps', 0),
        }
    }


@generate_flow_definition(modifiers={
    'ssx_gather_data': {'endpoint': 'funcx_endpoint_non_compute'}
})

class SSXGatherData(GladierBaseTool):
    flow_input = {
        'metadata': {
            "description": "Automated data processing.",
            "creators": [{"creatorName": "Kanzus"}],
            "publisher": "Automate",
            "subjects": [{"subject": "SSX"}],
            "publicationYear": '2021',
        }
    }

    required_input = [
        'trigger_name',
        'tar_input',
        'proc_dir',
        'upload_dir',
        'funcx_endpoint_non_compute',
    ]

    funcx_functions = [
        ssx_gather_data
    ]
