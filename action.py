"""Module for wrapping basic actions of the slack bot."""


def speak(client, channel, message, user=''):
    """Send message through Slack client.

    Parameters
    ----------
    client : SlackClient
        Slack client that will be used to send the message.
    channel : str
        Name of channel stored in Slack client
    message : str
        What bot will write
    user : str
        User to directly message

    """
    user = '<@{0}> '.format(user) if user != '' else ''
    message = '{0}{1}'.format(user, message)
    client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)


class ActionInputError(Exception):
    """Exception raised within the provided action for bad input."""
    pass


def act(arguments, actions):
    """Executes appropriate actions given the string arguments.

    Parameters
    ----------
    arguments : list of str
        Arguments provided by the user.
    actions : dict
        Actions that corresponds to the given arguments.
        Dictionary where the keys are the arguments provided by the user and the values are the
        actions that corresponds to the arguments.
        If multiple arguments are required to trigger an action, the dictionary can be nested for
        additional arguments.
        The values are the action that will be executed. It will be a function that requires no
        arguments (this function will be executed without arguments).
        Each level of action must contain an error key that handles the action upon bad input.

    Raises
    ------
    ValueError
        If the given actions does not contain the key 'error'.

    """
    try:
        contents = actions[arguments[0].lower()]
        # here, IndexError is raised if arguments is empty
        # then, KeyError is raised if given argument is not a key in actions
    except (KeyError, IndexError):
        if 'error' not in actions:
            raise ValueError('The provided set of actions must contain the key `error` to handle '
                             'behaviour when bad arguments are provided:\n{0}'.format(actions))
        raise ActionInputError(actions['error'])

    if isinstance(contents, (tuple, list)):
        doc, func = contents[:2]
        default_args = contents[2:]
        if not isinstance(doc, str):
            # FIXME: wording
            raise ValueError('First entry in the list of actions must be the documentation for '
                             'executing the function.')
        elif not hasattr(func, '__call__'):
            # FIXME: wording
            raise ValueError('Second entry in the list of actions must be the executed function.')
        try:
            args = default_args + arguments[1:]
            func(*args)
            # TypeError is raised if wrong number of arguments are provided to the method
        except TypeError:
            raise ActionInputError(doc)
    elif isinstance(contents, str):
        raise ActionInputError(contents)
    elif isinstance(contents, dict):
        act(arguments[1:], contents)
    else:
        # FIXME: wording
        raise ValueError('Cannot understand the given structure of actions.')
