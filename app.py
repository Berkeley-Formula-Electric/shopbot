import os
import re

import dotenv
from slack_bolt import App, Ack, Respond, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

import db


dotenv.load_dotenv()

CHANNEL_NAME = os.environ['CHANNEL_NAME']
CHANNEL_ID = os.environ['CHANNEL_ID']
APPROVAL_THRESHOLD = 1

_approve_reaction_matchers = [
    lambda event: event['reaction'] == 'white_check_mark',
    lambda event: event['item']['channel'] == CHANNEL_ID,
    lambda event: event['user'] in [approver.uid for approver in db.get_approvers()]
]

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

    success = db.add_part(cart, part, qty, user)
    if not success:
        respond(text=f'Addition of {qty} part(s) {part} to cart {cart} failed. Cart has not been created.')
        return
    text = f'{user.mention()} added {qty} of {part} to {cart}'
    say(channel=CHANNEL_NAME, text=text)


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
        respond(text=f'Removal of part {part} from cart {cart} did not succeed. '
                     'Cart does not exist or part was not found in cart.')
        return
    text = f'{user.mention()} removed {part} from {cart}'
    say(channel=CHANNEL_NAME, text=text)


@app.command('/sb-list')
def list_(ack: Ack, respond: Respond, say: Say, command: dict):
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

    text = _cart_content_fmtstr(cart_name, command["user_name"])
    if not text:
        respond(text=f'Listing of cart {cart_name} did not succeed. Cart does not exist.')
        return
    say(channel=CHANNEL_NAME, text=text) if send_public else respond(text=text)


@app.command('/sb-create')
def create(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    cart, user = _single_arg(command, respond)
    if not cart and not user:
        return

    success = db.create_cart(cart)
    if not success:
        respond(text=f'Creating cart {cart} did not succeed. Cart already exists.')
        return
    text = f'{user.mention()} created cart {cart}'
    say(channel=CHANNEL_NAME, text=text)


@app.command('/sb-clear')
def clear(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    cart, user = _single_arg(command, respond)

    success = db.clear_cart(cart, user)
    if not success:
        respond(text=f'Clearing cart {cart} did not succeed.')
        return
    text = f'{user.mention()} cleared cart {cart}'
    say(channel=CHANNEL_NAME, text=text)


@app.command('/sb-buy')
def buy(ack: Ack, respond: Respond, say: Say, command: dict, client: WebClient):
    ack()

    cart, user = _single_arg(command, respond)
    if db.get_approvals(cart) is not None:
        respond(text=f'Approval workflow already exists for cart {cart}.')
        return
    approvers = ' '.join([approver.mention() for approver in db.get_approvers()])

    cart_content = _cart_content_fmtstr(cart, user.name)
    if not cart_content:
        respond(text=f'Approval workflow for {cart} did not succeed. Cart does not exist.')
        return
    text = '*BEGIN PURCHASE REQUEST*\n\n' \
           f'{cart_content}\n\n' \
           f'Approvers (required): {approvers}\n' \
           'Please react :white_check_mark: to approve this purchase request'
    resp = say(channel=CHANNEL_NAME, text=text)
    ts = resp.data['ts']
    success = db.begin_approval(cart, ts)
    if not success:
        client.chat_delete(channel=CHANNEL_ID, ts=ts)
        respond(text='Approval workflow did not succeed.')
        return


@app.event(event='reaction_added', matchers=_approve_reaction_matchers)
def add_approve_reaction(ack: Ack, say: Say, event: dict, client: WebClient):
    ack()

    reaction = client.reactions_get(channel=CHANNEL_ID, timestamp=event['item']['ts'])
    if not reaction or not reaction.data['ok']:
        _client_post_ephemeral(client, event,
                               'Failed getting message which reaction was applied to.')
        return
    message = reaction.data['message']
    cart_matches = re.findall(r'> requested cart (.+):', message['text'])
    if len(cart_matches) != 1:
        # This should be silent; unrelated message
        return
    cart = cart_matches[0]
    if cart not in db.database.tables():
        _client_post_ephemeral(client, event,
                               f'Approval failed. Cart {cart} does not exist.')
        return

    user = None
    all_approvers = db.get_approvers()
    for approver in all_approvers:
        if approver.uid == event['user']:
            user = approver
            break
    if not user:
        _client_post_ephemeral(client, event,
                               f'Approval failed. User {user.name} is not in the approvers list.')
        return

    success = db.add_approval(cart, user, event['event_ts'])
    if not success:
        _client_post_ephemeral(client, event,
                               f'Approval failed. Approval for cart {cart} has not been started.')
        return
    text = f'{user.mention()} approved cart {cart}'
    say(channel=CHANNEL_NAME, text=text)

    approvals = db.get_approvals(cart)
    if len(approvals) == APPROVAL_THRESHOLD:
        cart_content = _cart_content_fmtstr(cart, user.name)
        approvals_repr = ' '.join([db.User.from_dict(approval['user']).mention() for approval in approvals])
        text = '*PURCHASE REQUEST APPROVED*\n\n' \
               f'{cart_content}\n\n' \
               f'Approved by: {approvals_repr}\n' \
               f'Cart {cart} will be cleared.'
        if not db.clear_cart(cart, user):
            _client_post_ephemeral(client, event,
                                   f'Cart {cart} could not be cleared after approval. Exiting.')
            return
        if not db.clear_approvals(cart, user):
            _client_post_ephemeral(client, event,
                                   f'Approvals list for cart {cart} could not be cleared after approval. Exiting.')
            return
        say(channel=CHANNEL_NAME, text=text)


@app.event('reaction_added')
def ignore_reaction_add(body, logger):
    # All reaction additions need to be handled
    pass


@app.event(event='reaction_removed', matchers=_approve_reaction_matchers)
def rm_approve_reaction(ack: Ack, say: Say, respond: Respond, event: dict, client: WebClient):
    ack()
    # TODO finish


@app.event('reaction_removed')
def ignore_reaction_rm(body, logger):
    # All reaction removals need to be handled
    pass


@app.command('/sb-add-approver')
def add_approver(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    approver_str, user = _single_arg(command, respond)
    approver = db.User.from_str(approver_str)

    #TODO uncomment after testing
    # if approver == user:
    #     respond(text='Approver cannot be yourself. Ask someone else to add you.')
    #     return

    success = db.add_approver(approver, user)
    if not success:
        respond(text=f'Addition of approver user {approver.name} did not succeed')
        return
    text = f'{user.mention()} added {approver.mention()} to the approver list'
    say(channel=CHANNEL_NAME, text=text)


@app.command('/sb-rm-approver')
def rm_approver(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()

    approver_str, user = _single_arg(command, respond)
    approver = db.User.from_str(approver_str)

    if approver not in db.get_approvers():
        respond(text=f'User {approver.name} is not in the approver list.')
        return

    success = db.rm_approver(approver)
    if not success:
        respond(text=f'Removing {approver.name} from approvers list failed. Approver not found in list.')
        return
    text = f'{user.mention()} removed {approver.mention()} from the approvers list'
    say(channel=CHANNEL_NAME, text=text)


@app.command('/sb-help')
def help_(ack: Ack, respond: Respond, say: Say, command: dict):
    ack()
    # TODO finish


def _client_post_ephemeral(client, event, text):
    client.chat_postEphemeral(channel=CHANNEL_ID, user=event['user'], text=text)

def _single_arg(command, respond):
    if _incorrect_channel(command, respond):
        return None, None
    args = _parse_args(command)
    if len(args) != 1:
        _incorrect_num_args(respond, 1, len(args))
        return None, None
    user = db.User(command['user_name'], command['user_id'])
    return args[0], user


def _cart_content_fmtstr(cart_name, user_name):
    if cart_name not in db.database.tables():
        return None
    cart_contents = db.list_cart(cart_name)
    cart_contents_fmt = '\n'.join([f'- {q} x {p} ({u.name})' for p, q, u in cart_contents])
    return f'<@{user_name}> requested cart {cart_name}:\n{cart_contents_fmt}'


def _incorrect_channel(command, respond) -> bool:
    actual_channel = command['channel_name']
    is_incorrect = actual_channel != CHANNEL_NAME
    if is_incorrect:
        respond(text=f'Incorrect channel. Expected {CHANNEL_NAME}, got {actual_channel}.')
    return is_incorrect


def _incorrect_num_args(respond, expected, actual):
    respond(text=f'Incorrect number of arguments. Expected {expected}, got {actual}.')


def _parse_args(command):
    return [v for v in command['text'].split(' ') if v]


if __name__ == '__main__':
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
