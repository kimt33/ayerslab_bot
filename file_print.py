import os
import shutil
from subprocess import call
import urllib.request
from action import ActionInputError


def upload(msg):
    """Download the file provided in the Slack message data.

    Parameters
    ----------
    msg : dict
        Dictionary that contains the key 'download' and the url as the key.

    """
    try:
        url = msg['download']
    except KeyError:
        raise ActionInputError('You must upload the file and provide the command, `@bot upload`, as'
                               ' the comment to the uploaded file.')

    filename = url.split('/')[-1]
    # TODO: probably should put in some sort of limitation to the files that can be uploaded
    # if os.path.splitext(filename)[-1] != '.pdf':
    #     raise ActionInputError('You can only upload pdf files.')
    with urllib.request.urlopen(url) as response, open(os.path.join('/tmp', filename), 'wb') as fh:
        shutil.copyfileobj(response, fh)
    raise ActionInputError('Bleep bloop.')


def file_print(filename, sided='double', color='black', quality='economy', pages=''):
    """Print provided file in the tmp directory.

    Parameters
    ----------
    filename : str
        Name of the file stored in the tmp directory.
    sided : {'single', 'double'}
        Number of sides on the paper to print.
        Default is double sided printing.
    color : {'color', 'black'}
        Color used in the job.
        Default is black only printing.
    quality : {'high', 'economy'}
        Quality of the print.
        Default is economy printing.
    pages : str
        Pages that will be printed.
        Default is all pages.

    """
    filename = os.path.join('/tmp', filename)

    command = ['lpr', '-P', 'HP_LaserJet_400_color_M451dw']
    if sided == 'single':
        command += ['-o', 'sides=one-sided']
    elif sided == 'double':
        command += ['-o', 'sides=double-sided-long-edge']
    else:
        raise ActionInputError('The number of sides must be either `single` or `double`.')

    if color == 'color':
        command += ['-o', 'HPColorAsGray=false', '-o', 'HPEasyColor=true']
    elif color == 'black':
        command += ['-o', 'HPColorAsGray=true', '-o', 'HPEasyColor=false']
    else:
        raise ActionInputError('The colors used must be either `black` or `color`.')

    if quality == 'high':
        command += ['-o', 'HPEconoMode=false']
    elif quality == 'economy':
        command += ['-o', 'HPEconoMode=true']
    else:
        raise ActionInputError('The quality of the print job must be either `high` or `economy`.')

    if pages != '':
        command += ['-o', 'page-ranges={0}'.format(pages)]

    # fit to page
    command += ['-o', 'fit-to-page']
    # page size
    command += ['-o', 'media=Letter']
    # print file
    command.append(filename)

    call(command)
    raise ActionInputError('Bleep bloop.')
