import json

import click

from workona import yaml_load, make_bookmarks

@click.command(help="Generate a Chrome-compatible bookmarks.html file from a Workona export.")
@click.argument('inputfile', type=click.Path(exists=True))
@click.option('-w', '--workspaces', multiple=True)
@click.option('-o', '--outputfile', default='bookmarks.html')
def generate_bookmarks(inputfile, workspaces, outputfile):
    """Operate on INPUTFILE, optionally filtering for WORKSPACES."""
    with open(inputfile, 'rb') as fh:
        rawdata = fh.read()

    if inputfile.endswith('.json'):
        data = json.loads(rawdata)
    elif inputfile.endswith('.txt'):
        data = yaml_load(rawdata)
    else:
        raise Exception("Expecting yaml or json Workona export files")
    
    output = make_bookmarks(data, workspaces=workspaces)
    
    with open(outputfile, 'w') as fh:
        fh.write(output)

if __name__ == '__main__':
    try:
        generate_bookmarks()
    except SystemExit:
        # this one's for VSCode, it breakpoints on all unhandled exceptions
        # including the one emitted by `Click` on a cli failure.
        pass