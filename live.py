import shlex
import sqlite3
import datetime
import time
from slackclient import SlackClient
import action
import utils
import door
import members
import quiet
import file_print
import money
from bot_info import SLACK_BOT_TOKEN, BOT_ID

# this is a monday at 2PM
ref_date = datetime.datetime(2017, 9, 11, 14)
# number of weeks since (plus one)
week_counter = (datetime.datetime.now() - ref_date).days // 7 + 1

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
if u'money' not in (j for i in cursor.fetchall() for j in i):
    cursor.execute('CREATE TABLE money (id INTEGER PRIMARY KEY, lender TEXT NOT NULL, '
                   'debtor TEXT NOT NULL, amount REAL NOT NULL, description TEXT, '
                   'confirm_lender_receipt TEXT, confirm_debtor_receipt TEXT, '
                   'confirm_lender_payment TEXT, confirm_debtor_payment TEXT)')
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
                def speak(message, user=msg['user']):
                    """Respond to the message."""
                    action.speak(slack_client, msg['channel'], message, user)

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
                    'money': {
                        'remind': ['To remind people about money related things, you need to '
                                   'provide their user names (space separated). If you want to find'
                                   ' everyone related to you, write `everyone` instead.',
                                   money.remind, slack_client, db_conn, readable_user],
                        'remove': ['To remove a receipt, you need to provide the receipt ID.',
                                   money.remove_receipt, db_conn, readable_user],
                        'add': ["To add a receipt, you need to provide the lender, the borrower, "
                                "the amount, and the description of the transaction, in the given "
                                "order.",
                                money.add_receipt, db_conn],
                        'list': ['', money.list, db_conn],
                        'confirm': ['To confirm a transaction, you need to provide the ID of the '
                                    'receipt and the type of confirmation (one of `receipt` or '
                                    '`payment`).', money.confirm, db_conn, readable_user]
                    },
                    # 'meetings': {
                    # },
                    # 'random': {
                    # },
                }
                act(args, actions)

            # time since reference
            delta_time = (datetime.datetime.now() - ref_date).days
            # On every monday near 2 PM
            if delta_time % 7 == 0 and delta_time // 7 == week_counter:
                cursor.execute('SELECT * FROM money WHERE confirm_lender_receipt=? OR '
                               'confirm_lender_payment=? OR confirm_debtor_receipt=? OR '
                               'confirm_debtor_payment=?', ('no',)*4)
                receipts = cursor.fetchall()
                for receipt in receipts:
                    try:
                        money.remind(slack_client, db_conn, receipt[1], receipt[2])
                    except action.ActionInputError as error:
                        cursor.execute('SELECT slack_id FROM members WHERE name=? OR userid=? OR '
                                       'slack_id=? OR id=?', (receipt[1],)*4)
                        im_channel = slack_client.api_call("im.open", user=cursor.fetchone()[0])['channel']['id']
                        action.speak(slack_client, im_channel, str(error))
                week_counter += 1

            # 1 second delay between reading from firehose
            time.sleep(1)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
