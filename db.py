import os


class User:
    def __init__(self, name, uid):
        self.name = name
        self.uid = uid


def add_part(cart, part, user: User) -> bool:
    pass


def rm_part(cart, part, user: User) -> bool:
    pass


def list_cart(cart) -> list:
    # TODO replace with actual
    return [["link1", 100], ["link2", 200], ["link3", 300]]


def create_cart(cart) -> bool:
    pass


def clear_cart(cart, user: User) -> bool:
    pass


def add_approver(user: User) -> bool:
    pass


def rm_approver(user: User) -> bool:
    pass


def get_approvers() -> list[User]:
    # TODO change after testing
    return [User(os.environ['TESTING_USER_NAME'], os.environ['TESTING_USER_ID'])]


def add_approval(cart, user: User) -> bool:
    pass


def clear_approvals(cart, user: User) -> bool:
    pass


if __name__ == '__main__':
    raise NotImplementedError('Not an entrypoint')
