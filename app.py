import os

import dotenv
from slack_bolt import App, Ack, Respond, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler

import db


CHANNEL = 'eecs-shopping-cart'

dotenv.load_dotenv()
app = App(token=os.environ['SLACK_BOT_TOKEN'])


@app.command('/sb-add')
def add(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    if _incorrect_channel(command, respond):
        return
    args = _parse_args(command)
    if len(args) not in (2, 3):
        _incorrect_num_args(respond, '2 or 3', len(args))
        return
    if len(args) == 2:
        # Default quantity for any item is 1
        args.append('1')
    cart, part, qty = args
    user = db.User(command['user_name'], command['user_id'])

    success = db.add_part(cart, part, user)
    if not success:
        respond(text=f'Addition of {qty} part(s) {part} to cart {cart} did not succeed.')
        return
    text = f'<@{user.name}> added {qty} of {part} to {cart}'
    say(channel=CHANNEL, text=text)


# TODO
@app.command('/sb-add-all')
def add_all(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()


@app.command('/sb-rm')
def rm(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    if _incorrect_channel(command, respond):
        return
    args = _parse_args(command)
    if len(args) != 2:
        _incorrect_num_args(respond, 2, len(args))
        return
    cart, part = args
    user = db.User(command['user_name'], command['user_id'])

    success = db.rm_part(cart, part, user)
    if not success:
        respond(text=f'Removal of part {part} from cart {cart} did not succeed.')
        return
    text = f'<@{user.name}> removed {part} from {cart}'
    say(channel=CHANNEL, text=text)


@app.command('/sb-list')
def lst(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    if _incorrect_channel(command, respond):
        return
    args = _parse_args(command)
    if len(args) not in (1, 2):
        _incorrect_num_args(respond, '1 or 2', len(args))
        return
    if len(args) == 1:
        args.append(False)
    cart_name, send_public = args

    cart_contents = db.list_cart(cart_name)
    cart_contents_fmt = '\n'.join([f'- {q} x {p}' for p, q in cart_contents])
    text = f'<@{command["user_name"]}> requested cart {cart_name}:\n{cart_contents_fmt}'
    say(channel=CHANNEL, text=text) if send_public else respond(text=text)

@app.command('/sb-create')
def create(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    cart, user = _cart_op_args(command, respond)

    success = db.create_cart(cart)
    if not success:
        respond(text=f'Creating cart {cart} did not succeed.')
        return
    text = f'<@{user.name}> created cart {cart}'
    say(channel=CHANNEL, text=text)


@app.command('/sb-clear')
def clear(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    cart, user = _cart_op_args(command, respond)

    success = db.clear_cart(cart, user)
    if not success:
        respond(text=f'Clearing cart {cart} did not succeed.')
        return
    text = f'<@{user.name}> cleared cart {cart}'
    say(channel=CHANNEL, text=text)


def _cart_op_args(command, respond):
    if _incorrect_channel(command, respond):
        return
    args = _parse_args(command)
    if len(args) != 1:
        _incorrect_num_args(respond, 1, len(args))
        return
    cart = args[0]
    user = db.User(command['user_name'], command['user_id'])
    return cart, user


@app.command('/sb-buy')
def buy(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()


@app.event('reaction_added')
def approve_reaction(ack: Ack, say: Say, respond: Respond, event: dict):
    ack()

    if _incorrect_channel(event, respond) or \
            event['reaction'] != 'white_check_mark' or \
            event['user'] not in [user.uid for user in db.get_approvers()]:
        return
    #TODO finish
    say(channel='eecs-shopping-cart', text='testing')


def _incorrect_channel(command, respond) -> bool:
    actual_channel = command['channel_name']
    is_incorrect = actual_channel != CHANNEL
    if is_incorrect:
        respond(text=f'Incorrect channel. Expected {CHANNEL}, got {actual_channel}.')
    return is_incorrect


def _incorrect_num_args(respond, expected, actual):
    respond(text=f'Incorrect number of arguments. Expected {expected}, got {actual}.')


def _parse_args(command):
    return [v for v in command['text'].split(' ') if v]


if __name__ == '__main__':
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
