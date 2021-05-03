import time, argparse, os, re
from pprint import pprint
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from gladier.client import GladierClient as GladierBaseClient

class KanzusTriggers:
    def __init__(self, folder_path):
        self.observer = Observer()
        self.folder_path = folder_path

    def run(self,pattern=None):
        print("Kanzus Triggers Started")
        print("Monitoring: " + self.folder_path)


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
        elif event.event_type == 'created':
            #event.src_path is the file watchdog found
            # Event is created, you can process it now
            KanzusLogic(event.src_path,f_pattern=None,f_ext=None, n_batch=256)


def KanzusLogic(event_file,f_pattern=None,f_ext=None, n_batch=256):
    if not f_pattern:
        f_pattern = r'(\w+_\d+_)(\d+).cbf'
    cbf_path = os.path.dirname(event_file)
    cbf_file = os.path.basename(event_file)
    cbf_parse = re.match(f_pattern, cbf_file)
    cbf_base =cbf_parse.group(1)
    cbf_num =int(cbf_parse.group(2))

    file_delta = 20
    range_delta = file_delta

    if cbf_num%file_delta==0:
        subranges = create_ranges(cbf_num-file_delta, cbf_num, range_delta)
        new_range = subranges[0]
        print(cbf_file)
        print(cbf_base)
        print(cbf_num)
        print(new_range)
        print(base_input)



from gladier_kanzus.flows.tutorial_flow import flow_definition as kanzus_flow


class KanzusSSXGladier(GladierBaseClient):
    client_id = 'e6c75d97-532a-4c88-b031-8584a319fa3e'
    gladier_tools = [
        'gladier_kanzus.tools.CreatePhil',
        'gladier_kanzus.tools.DialsStills',
        'gladier_kanzus.tools.SSXGatherData',
        'gladier_kanzus.tools.SSXPlot',
        'gladier_kanzus.tools.SSXPublish',
    ]
    flow_definition = kanzus_flow

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
    cont_dir =  '/home/rvescovi/.funcx/containers/'
    container_name = "dials_v1.simg"
    dials_cont_id = fxc.register_container(location=cont_dir+'/'+container_name,container_type='singularity')
    stills_cont_fxid = fxc.register_function(stills_cont, container_uuid=dials_cont_id)
    return stills_cont_fxid
    ##

##Arg Parsing
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('workdir', type=str, default='.')
    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    workdir = args.workdir
    print(workdir)
    os.chdir(workdir)

    ##theta
    conf = {'local_endpoint': '8f2f2eab-90d2-45ba-a771-b96e6d530cad',
            'queue_endpoint': '23519765-ef2e-4df2-b125-e99de9154611',
            }

    ##theta dirs
    data_dir = '/eagle/APSDataAnalysis/SSX/S12/StTrpAB/B'
    proc_dir = data_dir
    
    
    stills_cont_fxid = register_container()

    @global
    base_input = {
        "input": {
            #Processing variables
            "proc_dir": proc_dir,
            "data_dir": data_dir,

            "nproc": 16,
            "beamx": "-214.400",
            "beamy": "218.200",

            # funcX endpoints
            "funcx_local_ep": conf['local_endpoint'],
            "funcx_queue_ep": conf['queue_endpoint'],

            # container hack for stills
            "stills_cont_fxid": stills_cont_fxid
        }





    # pprint(flow_input['input'])
    # phils_flow = phils_client.start_flow(flow_input=flow_input)


    exp = KanzusTriggers(workdir)
    exp.run()



