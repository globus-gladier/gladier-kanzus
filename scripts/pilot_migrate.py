import json
import pathlib
import datetime
import globus_sdk
import click
import pprint
from importlib import import_module
from pilot.client import PilotClient
pilot_client = PilotClient()
search_client = pilot_client.get_search_client()


def get_document_name(base_name):
    index_info = search_client.get_index(pilot_client.get_index())
    date = datetime.datetime.now().isoformat()
    return f'{index_info["display_name"]}-{base_name}-{date}.json'


def build_content_map(short_path, content):
    for file_record in content['files']:
        file_record['url'] = pilot_client.get_globus_http_url(file_record['url'])
    return short_path, content



@click.group()
def cli():
    pass


@cli.command(help='Create a local backup of an index')
@click.argument('backup_doc', type=click.File('w+'), default=get_document_name('backup'))
def backup(backup_doc):
    """List all entries for a project, save them to the local directory"""
    backup_doc.write(json.dumps(pilot_client.list_entries(), indent=2))
    click.secho(f'Saved {backup_doc.name}', fg='green')


@cli.command(help='Create a migration using a backup')
@click.argument('backup_doc', type=click.File('r'))
@click.argument('migration_doc', type=click.File('w+'), default=get_document_name('migration'))
@click.option('--verbose', is_flag=True, help='Provide extra info')
def make_migration(backup_doc, migration_doc, verbose):
    content_map = {}
    click.secho(f'Creating migration from {backup_doc.name}...')
    try:
        for record in json.loads(backup_doc.read()):
            content = record['content'][0]
            for file_record in content['files']:
                file_record['url'] = pilot_client.get_short_path(file_record['url'])
            content_map[pilot_client.get_short_path(record['subject'])] = content
    except Exception:
        click.secho(f'Failed to read {backup_doc.name}, ensure it is a valid backup doc')
        if verbose:
            raise
    migration_doc.write(json.dumps(content_map, indent=2))
    click.secho(f'Saved {migration_doc.name}')


@cli.command(help='Ingest a migration document to an index')
@click.argument('migration_doc', type=click.File('r'))
@click.option('--custom-content-map', type=click.Path(exists=True, dir_okay=False))
@click.option('--preview-content', is_flag=True, help='Show json for one complete record')
@click.option('--preview-subjects', is_flag=True, help='Show the first 10 subjects')
@click.option('--force', is_flag=True, help='Make a mistake even though we warned you not to')
def migrate(migration_doc, custom_content_map, preview_content, preview_subjects, force):
    """Migrate accepts a migration doc, and uses the current pilot context/project to build
    a search ingest document. Migration docs have relative paths for subjects and files, and so
    pilot is used to build the new paths with the configured base_path"""
    content_map = json.loads(migration_doc.read())
    index_info = search_client.get_index(pilot_client.get_index())
    name = index_info["display_name"]
    click.secho(f'Preparing to ingest {len(content_map)} records into index '
                f'{name} ({index_info["id"]})')

    build_content_map_function = build_content_map
    if custom_content_map:
        try:
            mod = import_module(pathlib.Path(custom_content_map).stem)
            build_content_map_function = getattr(mod, 'build_content_map')
            click.secho(f'Using custom function: {custom_content_map}', fg='blue')
        except Exception:
            raise

    new_content_map = {}
    for sp, cnt in content_map.items():
        result = build_content_map_function(sp, cnt)
        if result is None:
            click.secho(f'WARNING: Skipping {sp}', fg='yellow')
            continue
        short_path, content = result
        new_content_map[short_path.lstrip('/')] = content

    click.secho('New search content built successfully', fg='green')

    if preview_content:
        subject, content = list(new_content_map.items())[-1]
        click.echo(f'Subject: {subject}\nContent: {json.dumps(content, indent=2)}\n')

    if preview_subjects:
        subjects = '\n'.join(list(new_content_map.keys())[:10])
        click.echo(f'Subjects: \n{subjects}')

    if index_info['num_subjects'] > 1 and not force:
        click.secho(f'WARNING: index {name} contains {index_info["num_subjects"]} subjects, '
                    f'suggest you wipe the index before proceeding', fg='red')
        return

    if click.confirm(f'Ingest {len(new_content_map)} into {name}?', abort=True):
        pilot_client.ingest_many(new_content_map)
        click.secho('Success', fg='green')
    else:
        click.secho('Aborted', fg='red')


@cli.command(help='Destroy all subjects within an index')
def wipe():
    """This will delete all search results, but preserve the project_metadata"""
    project = pilot_client.project.current
    results = pilot_client.search(project=project)
    index_info = search_client.get_index(pilot_client.get_index())
    search_query = {
        'q': '*',
        'filters': {
            'field_name': 'project_metadata.project-slug',
            'type': 'match_all',
            'values': [project or pilot_client.project.current]
        }
    }
    dz = '\n{}\nDANGER ZONE\n{}'.format('/' * 80, '/' * 80)
    click.secho(
        f'{dz}\n'
        f'This will delete all {results["total"]} search results in index {index_info["display_name"]}.'
        f'{dz}\n', bg='red')
    if click.confirm('Are you sure you wish to continue?'):
        search_client.delete_by_query(index_info['id'], search_query)


if __name__ == '__main__':
    cli()
