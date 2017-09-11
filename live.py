import os
import shlex
import sqlite3
import time
from slackclient import SlackClient
import action
import utils
import door
import members
import quiet
import file_print
from bot_info import SLACK_BOT_TOKEN, BOT_ID

# instantiate Slack clients
slack_client = SlackClient(SLACK_BOT_TOKEN)

# read in database
db_conn = sqlite3.connect('ayerslab.db')
cursor = db_conn.cursor()
# initiate database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
if u'members' not in (j for i in cursor.fetchall() for j in i):
    cursor.execute('CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT, userid TEXT NOT NULL, '
                   'slack_id TEXT, email TEXT, role TEXT, permission TEXT, door_permission TEXT)')
    db_conn.commit()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
if u'doorlog' not in (j for i in cursor.fetchall() for j in i):
    cursor.execute('''CREATE TABLE doorlog
    (id INTEGER PRIMARY KEY,
        time TEXT NOT NULL,
        userid TEXT NOT NULL)''')
    db_conn.commit()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
if u'quietlog' not in (j for i in cursor.fetchall() for j in i):
    cursor.execute('''CREATE TABLE quietlog
    (id INTEGER PRIMARY KEY,
        time TEXT NOT NULL,
        userid TEXT NOT NULL)''')
    db_conn.commit()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
if u'group_meetings' not in (j for i in cursor.fetchall() for j in i):
    cursor.execute('CREATE TABLE group_meetings (id INTEGER PRIMARY KEY, date TEXT NOT NULL, '
                   'presenter INTEGER, chair INTEGER, title TEXT)')
    db_conn.commit()

if __name__ == "__main__":
    if slack_client.rtm_connect():
        print("ayerslab_bot connected and running!")
        host = "<@{0}>".format(BOT_ID)

        dict_channels = {i['name']: i['id']
                         for i in slack_client.api_call("channels.list")['channels']}
        while True:
            raw_info = slack_client.rtm_read()

            # parse messages (if info is a message that has been directly messaged to bot)
            def msgs():
                """Generate messages."""
                for msg in raw_info:
                    parsed_msg = {}

                    if not msg['type'].startswith('message'):
                        continue

                    try:
                        subtype = msg['subtype']
                    except KeyError:
                        if msg['user'] == BOT_ID:
                            continue
                        parsed_msg['message'] = msg['text'].strip()
                    else:
                        if subtype != 'file_share':
                            continue
                        parsed_msg['download'] = msg['file']['url_private_download']
                        if 'initial_comment' in msg['file']:
                            parsed_msg['message'] = msg['file']['initial_comment']['comment']
                        else:
                            parsed_msg['message'] = ''

                    parsed_msg['user'] = msg['user']
                    parsed_msg['channel'] = msg['channel']
                    parsed_msg['time'] = msg['ts']
                    yield parsed_msg

            # process messages
            for msg in msgs():
                if msg['message'].startswith(host):
                    args = msg['message'].replace(host, '')
                else:
                    args = msg['message']

                # parse the arguments
                args = shlex.split(args)

                # configure speak
                def speak(message):
                    """Respond to the message."""
                    action.speak(slack_client, msg['channel'], message, msg['user'])

                # configure act
                def act(arguments, actions):
                    """Act according to the message.

                    Parameters
                    ----------
                    arguments : arguments for the
                    """
                    utils.make_errors(actions, speak)
                    try:
                        action.act(arguments, actions)
                    except action.ActionInputError as error:
                        speak(str(error))
                    except Exception as error:
                        speak('I ENCOUNTERED AN UNEXPECTED ERROR. DEBUG ME HUMAN!')
                        raise error

                cursor.execute("SELECT userid FROM members WHERE slack_id = ?", (msg['user'],))
                try:
                    readable_user = cursor.fetchone()[0]
                except (IndexError, TypeError):
                    readable_user = msg['user']

                if msg['channel'] == dict_channels['1door'] and args[0] != 'door':
                    args = ['door'] + args

                actions = {
                    'door': {
                        'open': ['', door.open_door, db_conn, readable_user],
                        '@': ['', door.open_door, db_conn, readable_user],
                        '#': ['', door.open_door, db_conn, readable_user],
                        'i': ['', door.open_door, db_conn, readable_user],
                        'abre': ['', door.open_door, db_conn, readable_user],
                        'ouvre': ['', door.open_door, db_conn, readable_user],
                        u'\u5f00\u95e8': ['', door.open_door, db_conn, readable_user],
                        'add': ['To add a user to access the door, you must provide an '
                                'identification of the user, like their name or Slack id.',
                                door.add, db_conn, readable_user],
                    },
                    'members': {
                        'add': ['To add a member to the Ayer\'s lab group member database, you must'
                                ' provide the name, userid, slack id, email, position of the '
                                'new member, permission to the bot, and permission to the door in '
                                'the given order. The entries are space delimited, which means that'
                                ' you must encase multiword entries within quotes. '
                                'If you are missing any of these information, just leave the '
                                'information blank, i.e. \'\'.',
                                members.add, db_conn, readable_user],
                        'modify': ["To modify a member's information in the database, you must "
                                   "provide the column that you'd like to modify, the new value, "
                                   "and identifiers of the members (alternating between the column "
                                   "and its value).",
                                   members.modify, db_conn, readable_user],
                        'list': ["To list the members' information in the database, you must "
                                 "provide the columns that you'd like to see.",
                                 members.list, db_conn],
                        'import_from_slack': ['', members.import_from_slack, slack_client, db_conn]
                    },
                    'quiet': ['', quiet.shush, slack_client, db_conn, readable_user,
                              dict_channels['shush']],
                    'upload': ['', file_print.upload, msg],
                    'print': ["To print a file, you must provide the filename of the file that "
                              "you've uploaded. Then, you can provided print options in the "
                              "following order: number of sides, which must be one of `single` or "
                              "`double` (default is `double`); color, which must be one of `color` "
                              "or `black` (default is `black`); quality, which must be one of "
                              "`high` or `economy` (default is `economy`); and page numbers, which "
                              "uses dashes to include multiple pages in an interval and commas to "
                              "include separated pages (default is all pages). Since keyword "
                              "arguments are not supported you must supply all arguments up until "
                              "desired arugment to modify. For example, to specify print quality, "
                              "you must provide the number of sides and color.",
                              file_print.file_print],
                    # 'meetings': {
                    # },
                    # 'money': {
                    # },
                    # 'random': {
                    # },
                }
                act(args, actions)

            # 1 second delay between reading from firehose
            time.sleep(1)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
