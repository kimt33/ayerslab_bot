from action import ActionInputError, speak
import members


def add_receipt(db_conn, lender, debtor, amount, description):
    """Add receipt to database.

    Parameters
    ----------
    db_conn : sqlite3.Connection
        Database connection object.
    lender : str
        Name of the user that is lending the money.
    debter : str
        Name of the user that is borrowing the money.
    amount : str
        Amount of the money being transferred.
    description : str
        Purpose of the transaction.

    """
    cursor = db_conn.cursor()
    # find lender id
    cursor.execute('SELECT userid FROM members WHERE name=? OR userid=? OR slack_id=? OR id=?',
                   (lender,)*4)
    rows = cursor.fetchall()
    if len(rows) > 1:
        raise ActionInputError('I found more than one person that goes by the identification, {0}'
                               ''.format(lender))
    elif len(rows) == 0:
        raise ActionInputError('I could not find anyone that goes by the identification, {0}'
                               ''.format(lender))
    # find debtor id
    cursor.execute('SELECT userid FROM members WHERE name=? OR userid=? OR slack_id=? OR id=?',
                   (debtor,)*4)
    rows = cursor.fetchall()
    if len(rows) > 1:
        raise ActionInputError('I found more than one person that goes by the identification, {0}'
                               ''.format(debtor))
    elif len(rows) == 0:
        raise ActionInputError('I could not find anyone that goes by the identification, {0}'
                               ''.format(debtor))
    # check amount
    try:
        amount = float(amount)
    except TypeError:
        raise ActionInputError('The amount of money given must be a number.')

    cursor.execute('INSERT INTO money (lender, debtor, amount, description, confirm_lender_receipt,'
                   ' confirm_debtor_receipt, confirm_lender_payment, confirm_debtor_payment) '
                   'VALUES (?,?,?,?,?,?,?,?)',
                   (lender, debtor, amount, description, 'no', 'no', 'no', 'no'))
    db_conn.commit()
    raise ActionInputError('Bleep bloop.')


def remove_receipt(db_conn, user, receipt_id):
    """Remove receipt from database.

    Parameters
    ----------
    db_conn : sqlite3.Connection
        Database connection object.
    user : str
        User that is removing the receipt from the database.
        Needs to be an administrator.
    receipt_id : str
        ID of the receipt being removed.

    """
    cursor = db_conn.cursor()
    if members.has_permission(cursor, user):
        # probably should confirm
        cursor.execute('DELETE FROM money WHERE id=?', (receipt_id, ))
        db_conn.commit()
        raise ActionInputError('Bleep bloop.')
    else:
        raise ActionInputError('You do not have the permission.')


def is_confirmed(db_conn, column, row_id):
    """Check if the given column has been confirmed.

    Parameters
    ----------
    db_conn : sqlite3.Connection
        Database connection object.
    column : {'confirm_lender_receipt', 'confirm_debtor_receipt', 'confirm_lender_payment',
              'confirm_debtor_payment'}
        Name of the column that will be checked.
    row_id : int
        Row ID of the receipt in the money database.

    Return
    ------
    confirmation : bool
        If the selected column has been confirmed.

    """
    if column not in ['confirm_lender_receipt', 'confirm_debtor_receipt TEXT',
                      'confirm_lender_payment', 'confirm_debtor_payment']:
        raise ValueError('Can only check one of `confirm_lender_receipt`, '
                         '`confirm_debtor_receipt`, `confirm_lender_payment`, '
                         '`confirm_debtor_payment` columns.')
    cursor = db_conn.cursor()
    cursor.execute('SELECT {0} from id=?'.format(column), (row_id,))
    return cursor.fetchone()[0][0] == 'yes'


def confirm(db_conn, user, row_id, confirm_type):
    """Confirm the given receipt.

    Parameters
    ----------
    db_conn : sqlite3.Connection
        Database connection object.
    user : str
        User ID of the person confirming.
    row_id : int
        Row ID of the receipt in the money database.
    confirm_type : {'receipt', 'payment'}
        Type of confirmation.

    """
    cursor = db_conn.cursor()
    match_row = False
    # check lender
    cursor.execute('SELECT confirm_lender_{0} FROM money WHERE id=? AND lender=?'
                   ''.format(confirm_type),
                   (row_id, user))
    try:
        confirm_lender = cursor.fetchone()[0]
    except (IndexError, TypeError):
        pass
    else:
        match_row = True
        if confirm_lender in ['no', '']:
            cursor.execute('UPDATE money SET confirm_lender_{0}=? WHERE id=?'.format(confirm_type),
                           ('yes', row_id))
            db_conn.commit()
        elif confirm_lender == 'yes':
            raise ActionInputError('You have already confirmed the {0} of receipt number {1}'
                                   ''.format(confirm_type, row_id))
        else:
            raise ValueError('Weird database entry, {0}, for {1} as receipt number {2}'
                             ''.format(confirm_lender, 'confirm_lender_{0}'.format(confirm_type),
                                       row_id))

    # check debtor
    cursor.execute('SELECT confirm_debtor_{0} FROM money WHERE id=? AND debtor=?'
                   ''.format(confirm_type),
                   (row_id, user))
    try:
        confirm_debtor = cursor.fetchone()[0]
    except (IndexError, TypeError):
        pass
    else:
        match_row = True
        if confirm_debtor == 'no':
            cursor.execute('UPDATE money SET confirm_debtor_{0}=? WHERE id=?'.format(confirm_type),
                           ('yes', row_id))
            db_conn.commit()
        elif confirm_debtor == 'yes':
            raise ActionInputError('You have already confirmed the {0} of receipt number {1}'
                                   ''.format(confirm_type, row_id))
        else:
            raise ValueError('Weird database entry, {0}, for {1} as receipt number {2}'
                             ''.format(confirm_debtor, 'confirm_lender_{0}'.format(confirm_type),
                                       row_id))

    # check if receipt is accessed
    if not match_row:
        raise ActionInputError('The receipt number {0} does not have you as a lender or a debtor.'
                               ''.format(row_id))

    raise ActionInputError('Bleep bloop.')


def list(db_conn, last=0):
    """List the receipt database.

    Parameters
    ----------
    db_conn : sqlite3.Connection
        Database connection object.
    last : int
        Number of entries (counting backwards) to print.

    """
    col_names = ['Database ID',
                 'Lender',
                 'Debtor',
                 'Amount',
                 'Description',
                 'Receipt Confirmed (L)',
                 'Receipt Confirmed (D)',
                 'Payment Confirmed (L)',
                 'Payment Confirmed (D)']

    cursor = db_conn.cursor()

    message = '{:<12}{:<30}{:<30}{:<8}{:<50}{:<23}{:<23}{:<23}{:<23}\n'.format(*col_names)
    cursor.execute('SELECT * FROM money')
    rows = cursor.fetchall()
    for row in rows[-last:]:
        # construct message
        message += '{:<12}{:<30}{:<30}{:<8.2f}{:<50}{:<23}{:<23}{:<23}{:<23}\n'.format(*row)

    raise ActionInputError('\n' + message)


def remind(client, db_conn, user, *remindees):
    """Send out reminders to others.

    Parameters
    ----------
    client : SlackClient
        Slack client.
    db_conn : sqlite3.Connection
        Database connection object.
    user : str
        Name of the user sending out reminders.
    remindees : list of str
        Names of the users being reminded.

    """
    cursor = db_conn.cursor()
    if len(remindees) == 1 and remindees[0] == 'everyone':
        cursor.execute('SELECT * FROM money WHERE lender=? OR debtor=?', (user, user))
        receipts = [i for i in cursor.fetchall() if 'no' in i[5:]]
    else:
        receipts = []
        for remindee in remindees:
            cursor.execute('SELECT * FROM money WHERE (lender=? AND debtor=?) OR '
                           '(debtor=? AND lender=?)', (user, remindee)*2)
            receipts.append(cursor.fetchone())

    for receipt_id, lender, debtor, amount, desc, conf_rl, conf_rd, conf_pl, conf_pd in receipts:
        if lender == user:
            user_is_lender = True
            user_conf = (conf_rl, conf_pl)
            other = debtor
            other_conf = (conf_rd, conf_pd)
        elif debtor == user:
            user_is_lender = False
            user_conf = (conf_rd, conf_pd)
            other = lender
            other_conf = (conf_rl, conf_pl)

        msg_format = ("I am reminding you about receipt number {0} where it says {1} "
                      "${2:.2f} with the following description: '{3}'.\n")
        if user_is_lender:
            msg = msg_format.format(receipt_id, 'you owe ' + user, amount, desc)
            user_msg = msg_format.format(receipt_id, user + ' owes you', amount, desc)

        else:
            msg = msg_format.format(receipt_id, user + ' owes you', amount, desc)
            user_msg = msg_format.format(receipt_id, 'you owe ' + user, amount, desc)

        receipt_confirm = ("Please confirm receipt number {0}.\nThe payment can be confirmed with "
                           "`money confirm {0} receipt`.".format(receipt_id))
        payment_confirm = ("Please pay for and confirm the receipt number {0}.\nThe payment can be "
                           "confirmed with `money confirm {0} payment`.".format(receipt_id))
        all_confirmed = ("You have confirmed everything and are waiting for {0} to confirm. You may"
                         " need to talk to {0} in person.")
        if user_conf[0] == 'no':
            user_msg += receipt_confirm
        elif user_conf[0] == 'yes' and user_conf[1] == 'no':
            user_msg += payment_confirm
        else:
            user_msg += all_confirmed.format(other)

        if other_conf[0] == 'no':
            msg += receipt_confirm
        elif other_conf[0] == 'yes' and other_conf[1] == 'no':
            msg += payment_confirm
        else:
            user_msg += all_confirmed.format(user)

        # find other user id
        cursor.execute('SELECT slack_id FROM members WHERE name=? OR userid=? OR slack_id=? OR '
                       'id=?', (other,)*4)
        rows = cursor.fetchall()
        if len(rows) != 1:
            raise ValueError('Something went wrong in the members database.')

        im_channel = client.api_call("im.open", user=rows[0][0])['channel']['id']
        speak(client, im_channel, msg)

        raise ActionInputError(user_msg)
