import RPi.GPIO as GPIO
from threading import Timer
import datetime
from action import ActionInputError
import members


def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.OUT)


def set_on():
    GPIO.output(4, GPIO.HIGH)


def set_off():
    GPIO.output(4, GPIO.LOW)


def set_open():
    setup()
    set_on()
    Timer(3.0, set_off).start()


def has_permission(cursor, user):
    """Checks if user has permission to open door.

    Parameters
    ----------
    cursor : sqlite3.Cursor
        Cursor object used to retrieve infromation from the database.
    user : str
        Identification of the user.
        Can be name, userid, slack id or id.

    """
    cursor.execute('SELECT door_permission FROM members WHERE name=? OR userid=? OR slack_id=? OR '
                   'id=?', (user,)*4)
    rows = cursor.fetchall()

    if len(rows) > 1:
        raise ActionInputError('I found more than one person that goes by the identification, {0}'
                               ''.format(user))
    else:
        return len(rows) == 1 and rows[0][0] == 'yesdoor'


def add(db_conn, user, user_to_add):
    """Give user permission to open door and add to the database if not already added.

    Parameters
    ----------
    db_conn : sqlite3.Connection
        Database connection object.
    user : str
        User that wants to change the permission of another user.
    user_to_add : str
        User to add to the database.

    """
    cursor = db_conn.cursor()
    cursor.execute('SELECT id FROM members WHERE name=? OR userid=? OR slack_id=? OR '
                   'id=?', (user_to_add,)*4)
    rows = cursor.fetchall()
    if len(rows) > 1:
        raise ActionInputError('I found more than one person that goes by {0}'.format(user_to_add))
    elif len(rows) == 0:
        raise ActionInputError('I could not find anyone that goes by {0}'.format(user_to_add))
    else:
        members.modify(db_conn, user, 'door_permission', 'yesdoor', 'id', rows[0][0])


def open_door(db_conn, user):
    """Open the door.

    Parameters
    ----------
    db_conn : sqlite3.Connection
        Database connection object.
    user : str
        Person who wants to open the door.

    """
    cursor = db_conn.cursor()
    if has_permission(cursor, user):
        set_open()
        cursor.execute("INSERT INTO doorlog (time, userid) VALUES (?,?)",
                       (str(datetime.datetime.now()), user),)
        db_conn.commit()
        raise ActionInputError('Bleep bloop')
    else:
        raise ActionInputError("I'm sorry, {0}, but I'm afraid I can't do that.".format(user))
