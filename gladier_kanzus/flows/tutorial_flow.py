  flow_definition = {
    "Comment": "Kanzus Phils Flow",
    "StartAt": "Dials Create Phil",
    "States": {
      "Dials Create Phil": {
        "Comment": "Create Dials Phil",
        "Type": "Action",
        "ActionUrl": "https://api.funcx.org/automate",
        "ActionScope": "https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all",
        "Parameters": {
            "tasks": [{
              "endpoint.$": "$.input.funcx_local_ep",
              "func.$": "$.input.funcx_create_phil_funcx_id",
              "payload.$": "$.input"
          }]
        },
        "ResultPath": "$.DialsCreatePhil",
        "WaitTime": 600,
        "Next": "Dials Stills"
      },
      "Dials Stills": {
        "Comment": "Dials Stills Function",
        "Type": "Action",
        "ActionUrl": "https://api.funcx.org/automate",
        "ActionScope": "https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all",
        "Parameters": {
            "tasks": [{
              "endpoint.$": "$.input.funcx_queue_ep",
              "func.$": "$.input.stills_cont_fxid",
              "payload.$": "$.input"
          }]
        },
        "ResultPath": "$.DialsStills",
        "WaitTime": 7200,
        "Next": 'SSXGatherData'
      },
      'SSXGatherData': {
            'Comment': 'Gather port-dials data for plot generation and upload',
            'Type': 'Action',
            'ActionUrl': 'https://api.funcx.org/automate',
            'ActionScope': 'https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/automate2',
            'ExceptionOnActionFailure': False,
            'Parameters': {
                'tasks': [{
                  'endpoint.$': '$.input.funcx_endpoint_non_compute',
                  'func.$': '$.input.ssx_gather_data_funcx_id',
                  'payload.$': '$.input',
              }]
            },
            'ResultPath': '$.SSXGatherData',
            'WaitTime': 600,
            'Next': 'SSXPlot',
          },
          'SSXPlot': {
            'Comment': 'Plot the pack-man image',
            'Type': 'Action',
            'ActionUrl': 'https://api.funcx.org/automate',
            'ActionScope': 'https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/automate2',
            'ExceptionOnActionFailure': False,
            'Parameters': {
                'tasks': [{
                  'endpoint.$': '$.input.funcx_endpoint_non_compute',
                  'func.$': '$.input.ssx_plot_funcx_id',
                  'payload': {
                      'xdim.$': '$.SSXGatherData.details.result.metadata.user_input.x_num_steps',
                      'ydim.$': '$.SSXGatherData.details.result.metadata.user_input.y_num_steps',
                      'int_indices.$': '$.SSXGatherData.details.result.int_indices',
                      'plot_filename.$': '$.SSXGatherData.details.result.plot_filename',
                  }
              }]
            },
            'ResultPath': '$.SSXPlot',
            'WaitTime': 600,
            'Next': 'SSXPublish',
          },
          'SSXPublish': {
                'Comment': 'Publish data on petrel and globus search',
                'Type': 'Action',
                'ActionUrl': 'https://api.funcx.org/automate',
                'ActionScope': 'https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/automate2',
                'ExceptionOnActionFailure': False,
                'Parameters': {
                    'tasks': [{
                        'endpoint.$': '$.input.funcx_endpoint_non_compute',
                        'func.$': '$.input.ssx_publish_funcx_id',
                        'payload': {
                            'metadata.$': '$.SSXGatherData.details.result.metadata',
                            'upload_dir.$': '$.SSXGatherData.details.result.upload_dir',
                        }
                    }]
                },
                'ResultPath': '$.SSXPublish',
                'WaitTime': 600,
                'End': True
            }
        }
      }