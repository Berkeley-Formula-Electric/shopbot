# shopbot

A slack bot that manages purchasing / shopping carts.

## Installation
Automatically: `./install.sh`

OR manually:
```bash
python3 -m venv venv
python3 -m pip install -r requirements.txt
```

## Usage
In the background: `./start.sh` 
- Equivalent to `nohup python3 app.py &`, requires `nohup`

In the foreground: `python3 app.py`

## Commands
- /sb-add: Add part link/num to a cart
- /sb-rm: Remove a part from a cart
- /sb-list: List parts in a cart
- /sb-list-carts: List all current carts
- /sb-create: Create a cart
- /sb-clear: Clear a cart (without buying)
- /sb-buy: Buy cart (+clear if approved)
- /sb-add-approver: Make a user an approver
- /sb-rm-approver: Remove an approver user
- /sb-help: Help with using shopbot

## Quickstart
1. Create a cart.
2. Add items to the cart.
3. Buy the cart. Approvers will react to the message to approve the purchase.
4. Once approved, the cart is cleared. Repeat from the beginning for another cart.
(note: approvers must be added before they can approve any purchases)

## Source Code
https://github.com/Berkeley-Formula-Electric/