#!/net/prog64/EMAN2/eman2.9/envs/gladier/bin/python

import time, argparse, os, re
from pprint import pprint
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from gladier import GladierBaseClient, generate_flow_definition
#import gladier.tests

class KanzusTriggers:
    def __init__(self, folder_path):
        self.observer = Observer()
        self.folder_path = folder_path

    def run(self,pattern=None):
        print("Kanzus Triggers Started")
        if not os.path.isdir(self.folder_path):
            print("Monitor dir does not exist.")
            print("Dir " + self.folder_path + " was created")
            os.mkdir(self.folder_path)
            
        print("Monitoring: " + self.folder_path)
        print('')

        event_handler = Handler()
        self.observer.schedule(event_handler, self.folder_path, recursive = True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except:
            self.observer.stop()
            print("Kanzus Triggers Stopped")

        self.observer.join()

class Handler(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None
        elif event.event_type == 'closed':
            KanzusLogic(event.src_path)
            return None
#https://stackoverflow.com/questions/58484940/process-multiple-oncreated-events-parallelly-in-python-watchdog

def KanzusLogic(event_file):

    cbf_num_pattern = r'(\w+_\d+_)(\d+).cbf'
    cbf_parse = re.match(cbf_num_pattern, os.path.basename(event_file))

    if cbf_parse is not None:

        cbf_base =cbf_parse.group(1)
        cbf_num =int(cbf_parse.group(2))

        rel_path = event_file.replace(base_input["input"]["base_local_dir"],'')
        names = rel_path.split('/')

        # ##LOCAL processing dirs
        local_dir = os.path.join(base_input["input"]["base_local_dir"], names[0], names[1])
        base_input["input"]["local_dir"] = local_dir
        base_input["input"]["local_proc_dir"] = local_dir + '_proc'
        base_input["input"]["local_upload_dir"] = local_dir + '_images'

        # ##REMOTE processing dirs
        data_dir = os.path.join(base_input["input"]["base_data_dir"], names[0], names[1])
        base_input["input"]["data_dir"] = data_dir
        base_input["input"]["proc_dir"] = data_dir + '_proc'
        base_input["input"]["upload_dir"] = data_dir + '_images' 
        
        base_input["input"]["trigger_name"] = os.path.join(data_dir,names[-1])

        n_batch_transfer = 32
        n_initial_transfer = 8
        n_batch_stills = 16
        n_batch_prime =  64

        if cbf_num%n_batch_transfer==0 or cbf_num==n_initial_transfer:
             
             label = f'SSX_Transfer_{names[0]}_{cbf_num}'
             flow = transfer_client.run_flow(flow_input=base_input,label=label)

             print('Transfer Flow')
             print("  Local Trigger : " + event_file)
             print("  UUID : " + flow['action_id'])
             print('')

        if cbf_num%n_batch_stills==0:
             subranges = create_ranges(cbf_num-n_batch_stills, cbf_num, n_batch_stills)
             new_range = subranges[0]
             base_input["input"]["input_files"]=f"{cbf_base}{new_range}.cbf"
             base_input["input"]["input_range"]=new_range[1:-1]
  
             label = f'SSX_Stills_{names[0]}_{new_range}'

             flow = stills_client.run_flow(flow_input=base_input, label=label)

             print('Stills Flow')
             print("  Local Trigger : " + event_file)
             print("  Range : " + base_input["input"]["input_range"])
             print("  UUID : " + flow['action_id'])
             print('')

@generate_flow_definition
class TransferClient(GladierBaseClient):
    gladier_tools = [
        'gladier_kanzus.tools.TransferOut',
    ]

@generate_flow_definition
class StillsClient(GladierBaseClient):
    gladier_tools = [
#        'gladier_kanzus.tools.TransferOut', #TransferData??
        'gladier_kanzus.tools.CreatePhil',
        'gladier_kanzus.tools.DialsStills',
        'gladier_kanzus.tools.SSXGatherData',
        'gladier_kanzus.tools.TransferProc',
        'gladier_kanzus.tools.SSXPlot',
        'gladier_kanzus.tools.SSXPublish',
        'gladier_kanzus.tools.TransferImage',
    ]

def create_ranges(start,end,delta):

    s_vec = np.arange(start,end,delta)
    proc_range = []
    for k in s_vec:
        k_start = k+1
        k_end = k_start + delta - 1
        if k_end > end:
            k_end = end
        proc_range.append(f'{{{str(k_start).zfill(5)}..{str(k_end).zfill(5)}}}')
    return proc_range

def register_container():
    ##hacking over container
    from funcx.sdk.client import FuncXClient
    fxc = FuncXClient()
    from gladier_kanzus.tools.dials_stills import funcx_stills_process as stills_cont
    cont_dir =  '/eagle/APSDataAnalysis/SSX/containers/'
    container_name = "dials_v1.simg"
    dials_cont_id = fxc.register_container(location=cont_dir+'/'+container_name,container_type='singularity')
    stills_cont_fxid = fxc.register_function(stills_cont, container_uuid=dials_cont_id)
    return stills_cont_fxid
    ##

##Arg Parsing
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('localdir', type=str, default='.')
    parser.add_argument('--datadir', type=str, 
        default='/APSDataAnalysis/SSX/random_start')
    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    ##parse dirs
    local_dir = args.localdir
    data_dir = args.datadir
    
    ##Process endpoints (theta - raf)
    head_funcx_ep      = 'e449e8b8-e114-4659-99af-a7de06feb847'
    queue_funcx_ep     = '4c676cea-8382-4d5d-bc63-d6342bdb00ca'
        

    ##Transfer endpoints
    beamline_globus_ep = 'ff32af54-ebe6-11eb-b467-eb47ba14b5cc'
    eagle_globus_ep    = '05d2c76a-e867-4f67-aa57-76edeb0beda0'
    theta_globus_ep    = '08925f04-569f-11e7-bef8-22000b9a448b'

    stills_cont_fxid = register_container() ##phase out with containers

    base_input = {
        "input": {
            #Processing variables
            "base_local_dir": local_dir,
            "base_data_dir": data_dir,

            "nproc": 64,
            "beamx": "-214.400",
            "beamy": "218.200",

            # funcX endpoints
            "funcx_endpoint_non_compute": head_funcx_ep,
            "funcx_endpoint_compute": queue_funcx_ep,

            # globus endpoints
            "globus_local_ep": beamline_globus_ep,
#           "globus_dest_ep": eagle_globus_ep, 
	    "globus_dest_ep": theta_globus_ep,

            # container hack for stills
            "stills_cont_fxid": stills_cont_fxid
        }
    }

    transfer_client = TransferClient()
    stills_client = StillsClient()
#    prime_client = PrimeClient()

    pprint(transfer_client.flow_definition)
    pprint(stills_client.flow_definition)
    exp = KanzusTriggers(local_dir)
    exp.run()


