import tinydb


database = tinydb.TinyDB('db.json', indent=4)


class User:
    def __init__(self, name: str, uid: str):
        self.name = name
        self.uid = uid

    @classmethod
    def from_str(cls, escaped_str: str):
        parts = escaped_str[2:-1].split('|')
        return cls(name=parts[1], uid=parts[0])

    @classmethod
    def from_dict(cls, mapping: dict):
        return cls(name=mapping['name'], uid=mapping['uid'])

    def to_dict(self):
        return {
            'name': self.name,
            'uid': self.uid
        }

    def mention(self) -> str:
        return f'<@{self.name}>'

    def __eq__(self, other):
        return self.name == other.name and \
               self.uid == other.uid

    def __str__(self):
        return f'User(name={self.name}, id={self.uid})'

    def __repr__(self):
        return self.__str__()


def add_part(cart_name: str, part: str, qty: str, user: User) -> bool:
    if cart_name not in database.tables():
        return False
    cart = database.table(cart_name)
    cart.insert({
        'part': part,
        'qty': qty,
        'user': user.to_dict()
    })
    return True


def rm_part(cart_name: str, part, user: User) -> bool:
    if cart_name not in database.tables():
        return False
    # TODO keep track of who removed things
    cart = database.table(cart_name)
    ids = cart.remove(tinydb.Query().part == part)
    return len(ids) != 0


def list_cart(cart_name: str) -> list[tuple]:
    cart = database.table(cart_name)
    parts = cart.all()
    return [(part['part'], part['qty'], User.from_dict(part['user'])) for part in parts if part]


def create_cart(cart_name: str) -> bool:
    if cart_name in database.tables():
        return False
    # On the backend, this creates a table if none existed before
    table = database.table(cart_name)
    # This is required, otherwise the table is not serialized
    table.insert({})
    return True


def clear_cart(cart_name: str, user: User) -> bool:
    if cart_name not in database.tables():
        return False
    # Drop and re-create is the easiest way to clear
    # Makes a new table ID, but this is OK since
    # nothing depends on/uses the table ID
    database.drop_table(cart_name)
    database.table(cart_name)
    return True


def add_approver(approver: User, user: User) -> bool:
    approvers = database.table('approvers')
    approvers.insert({
        'approver': approver.to_dict(),
        'user': user.to_dict()
    })
    return True


def rm_approver(approver: User) -> bool:
    approvers = database.table('approvers')
    matches = approvers.search(tinydb.Query().approver == approver.to_dict())
    if len(matches) != 1:
        return False
    approvers.remove(doc_ids=[matches[0].doc_id])
    return True


def get_approvers() -> list[User]:
    table = database.table('approvers')
    approvers = table.all()
    return [User.from_dict(approver['approver']) for approver in approvers]


def begin_approval(cart_name: str, ts: str) -> bool:
    if cart_name not in database.tables():
        return False
    approvals = database.table('approvals')
    approvals.insert({
        'cart': cart_name,
        'ts': ts,
        'approvals': []
    })
    return True


def get_approvals(cart_name: str):
    if cart_name not in database.tables():
        return None
    approval_table = database.table('approvals')
    matches = approval_table.search(tinydb.Query().cart == cart_name)
    if len(matches) != 1:
        return None
    return matches[0]['approvals'], matches[0].doc_id


def add_approval(cart_name: str, user: User, ts: str) -> bool:
    cart_approvals, doc_id = get_approvals(cart_name)
    # OK for approvals to be empty, but not None
    if cart_approvals is None:
        return False
    approval = {
        'user': user.to_dict(),
        'ts': ts
    }
    cart_approvals.append(approval)
    approval_table = database.table('approvals')
    approval_table.update(doc_ids=[doc_id], fields={'approvals': cart_approvals})
    return True


def rm_approval(cart_name: str, user: User) -> bool:
    approvals, doc_id = get_approvals(cart_name)
    for approval in approvals[:]:
        if approval['user'] == user.to_dict():
            approvals.remove(approval)
            approval_table = database.table('approvals')
            approval_table.update(doc_ids=[doc_id], fields={'approvals': approvals})
            return True
    return False


def clear_approvals(cart_name: str, user: User) -> bool:
    approval_table = database.table('approvals')
    matches = approval_table.search(tinydb.Query().cart == cart_name)
    approval_table.remove(doc_ids=[match.doc_id for match in matches])
    return True


if __name__ == '__main__':
    raise NotImplementedError('Not an entrypoint')
