import pathlib
import pprint
from pilot.client import PilotClient

pilot_client = PilotClient()


def build_content_map(short_path, content):
    try:
        run_name = content['project_metadata'].get('run_name')
        if not run_name and content['project_metadata'].get('user_input'):
            run_name = pathlib.Path(content['project_metadata']['user_input']['directory']).name
        else:
            print(f'skipping {short_path}')

        prot_name = content['project_metadata']['user_input']['prot_name']
        short_path = pathlib.Path('/') / run_name / prot_name / pathlib.Path(short_path)

        for file_record in content['files']:
            filename = pathlib.Path(file_record['url']).name
            file_record['url'] = pilot_client.get_globus_http_url(str(short_path / filename))
        return str(short_path), content

    except Exception as e:
        print(f'Failed on {short_path}')
        # pprint.pprint(content)
        return