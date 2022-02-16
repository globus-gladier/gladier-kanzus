#!/local/data/idsbc/idstaff/gladier/miniconda3/envs/gladier/bin/python

import time, argparse, os
from watchdog.observers import Observer
#from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import gladier_kanzus.logging  # noqa

class KanzusTriggers:
    def __init__(self, folder_path):
        self.observer = Observer()
        self.folder_path = folder_path

    def run(self):
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

#https://stackoverflow.com/questions/58484940/process-multiple-oncreated-events-parallelly-in-python-watchdog
class Handler(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
#        print(event)
        if event.is_directory:
            return None
        elif event.event_type == 'created':
            #KanzusLogic(event.src_path)
            return None
        elif event.event_type == 'modified':
            KanzusLogic(event.src_path)
            return None

def parse_cbf_event(event_file):
    event = {}
    event['exp'] = event_file.split('/')[-4]
    event['sample'] = event_file.split('/')[-3]
    event['chip_letter'] = event_file.split('/')[-2]
    event['filename'] = event_file.split('/')[-1]
    event['chip_name'] = event['filename'].split('_')[0]
    event['run_num'] = int(event['filename'].split('_')[1])
    try:
        event['cbf_num'] = int(event['filename'].split('_')[2].replace('.cbf',''))
    except:
        event['cbf_num'] = None
    return event

def parse_int_event(event_file):
    event = {}
    return event

def KanzusLogic(event_file):

    if '.cbf' in event_file:
        event = parse_cbf_event(event_file)

        # LOCAL processing dirs
        exp_path = base_input["input"]["base_local_dir"]
        local_dir = os.path.join(exp_path, event['sample'], event['chip_letter'])
        base_input["input"]["local_dir"] = local_dir
        base_input["input"]["local_proc_dir"] = local_dir + '_proc'
        base_input["input"]["local_prime_dir"] = local_dir + '_prime'
        base_input["input"]["local_images_dir"] = os.path.join(exp_path, event['sample'], event['chip_name']) + '_images'

        # REMOTE processing dirs
        data_dir = os.path.join(base_input["input"]["base_data_dir"], event['sample'], event['chip_letter'])
        base_input["input"]["data_dir"] = data_dir
        base_input["input"]["proc_dir"] = data_dir + '_proc'
        base_input["input"]["prime_dir"] = data_dir + '_prime'
        base_input["input"]["upload_dir"] = os.path.join(base_input["input"]["base_data_dir"],  event['sample'], event['chip_name']) + '_images' 
        base_input["input"]["trigger_name"] = event_file
        base_input["input"]['exp'] = event['exp']
        base_input["input"]['sample'] = event['sample']
        base_input["input"]['chip_letter'] = event['chip_letter']
        base_input["input"]['filename'] = event['filename']
        base_input["input"]['chip_name'] = event['chip_name']
        base_input["input"]['cbf_num'] = event['cbf_num']
        base_input["input"]['run_num'] = event['run_num']
        base_input["input"]['stills_batch_size'] = n_batch_stills
        base_input['input']['tar_input'] = base_input["input"]["proc_dir"] ##Something funky here 
        base_input['input']['tar_output'] = os.path.join(base_input["input"]["upload_dir"],'ints.tar.gz')


        if event['cbf_num'] % n_batch_transfer == 0 or event['cbf_num'] == n_initial_transfer:
            start_transfer_flow(event)

        if event['cbf_num'] % n_batch_stills == 0:
            start_stills_flow(event)

        if event['cbf_num'] % n_batch_publish == 0:
            start_publish_flow(event)

        if event['cbf_num'] % n_batch_prime == 0:
            start_prime_flow(event)

    if 'int_list.txt' in event_file:
       event = parse_int_event(event_file)
       
       if event['total_ints'] % n_batch_prime == 0:
           start_prime_flow(event)


def start_transfer_flow(event):
    ###RunFlow
    label = 'SSX_Transfer_{}_{}'.format(event['chip_name'],event['cbf_num'])
    flow = data_transfer_flow.run_flow(flow_input=base_input,label=label)
    print(label)
    print("URL : https://app.globus.org/runs/" + flow['action_id'] + "\n")
    ###

def start_stills_flow(event):
    ###RunFlow
    label = 'SSX_Stills_{}_{}'.format(event['chip_name'],event['cbf_num'])
    flow = stills_flow.run_flow(flow_input=flow_input, label=label)
    print(label)
    print("URL : https://app.globus.org/runs/" + flow['action_id'] + "\n")
    ###


def start_publish_flow(event):
    ###RunFlow
    label = f'SSX_Plot_{}_{}'.format(event['chip_name'],event['cbf_num'])
    flow = publish_flow.run_flow(flow_input=base_input,label=label)
    print(label)
    print("URL : https://app.globus.org/runs/" + flow['action_id'] + "\n")
    ###

def start_prime_flow(event):                                   
    ###RunFlow
    label = 'SSX_Prime_{}_{}'.format(event['chip_name'],event['cbf_num'])                                                                                                                                    
    flow = prime_flow.run_flow(flow_input=base_input, label=label)
    print(label)
    print("URL : https://app.globus.org/runs/" + flow['action_id'] + "\n")
    ###

# Arg Parsing
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('localdir', type=str, default='.')
    parser.add_argument('--datadir', type=str, 
        default='/eagle/APSDataAnalysis/SSX/random_start')
    parser.add_argument('--deployment','-d', default='raf-prod', help=f'Deployment configs. Available: {list(deployment_map.keys())}')
    return parser.parse_args()

##Gather deployment specific variables
from gladier_kanzus.deployments import deployment_map

##Import relevant flows
from gladier_kanzus.flows import TransferFlow
from gladier_kanzus.flows import StillsFlow
from gladier_kanzus.flows import PublishFlow
from gladier_kanzus.flows import PrimeFlow



if __name__ == '__main__':

    args = parse_args()

    local_dir = args.localdir
    data_dir = args.datadir

    n_initial_transfer = 512
    n_batch_transfer = 2048
    n_batch_stills = 512
    n_batch_publish =  2048
    n_batch_prime =  2000

    depl = deployment_map.get(args.deployment)
    if not depl:
        raise ValueError(f'Invalid Deployment, deployments available: {list(deployment_map.keys())}')

    depl_input = depl.get_input()

    base_input = {
        "input": {
            #Processing variables
            "base_local_dir": local_dir,
            "base_data_dir": data_dir,
            # funcX endpoints
            'funcx_endpoint_non_compute': depl_input['input']['funcx_endpoint_non_compute'],
            'funcx_endpoint_compute': depl_input['input']['funcx_endpoint_compute'],
            # globus endpoints
            "globus_local_ep": depl_input['input']['beamline_globus_ep'],
            "globus_dest_ep": depl_input['input']['theta_globus_ep'], 
    	    "globus_dest_mount" : depl_input['input']['ssx_eagle_mount'],
        }
    }

    data_transfer_flow = TransferFlow()
    stills_flow = StillsFlow()
    prime_flow = PrimeFlow()
    publish_flow = PublishFlow()

    os.chdir(local_dir)

    exp = KanzusTriggers(local_dir)
    exp.run()


