import os
import random
import asyncio
from web3 import Web3
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Constants
RPC_URL = "https://testnet-rpc.monad.xyz/"
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
WMON_CONTRACT = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"

# Load private keys from pvkey.txt
def load_private_keys(file_path):
    try:
        with open(file_path, 'r') as file:
            keys = [line.strip() for line in file.readlines() if line.strip()]
            if not keys:
                raise ValueError("pvkey.txt is empty")
            return keys
    except FileNotFoundError:
        print(f"{Fore.RED}❌ pvkey.txt not found{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}❌ Error reading pvkey.txt: {str(e)}{Style.RESET_ALL}")
        return None

# Initialize web3 provider
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Check connection
if not w3.is_connected():
    print(f"{Fore.RED}❌ Could not connect to RPC{Style.RESET_ALL}")
    exit(1)

# Initialize contract
contract = w3.eth.contract(address=WMON_CONTRACT, abi=[
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "payable": False, "stateMutability": "nonpayable", "type": "function"},
])

# Print border function
def print_border(text, color=Fore.CYAN, width=60):
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│ {text:^56} │{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

# Print step function
def print_step(step, message):
    step_text = "Wrap MON" if step == 'wrap' else "Unwrap WMON"
    print(f"{Fore.YELLOW}➤ {Fore.CYAN}{step_text:<15}{Style.RESET_ALL} | {message}")

# Generate random amount (0.01 - 0.05 MON)
def get_random_amount():
    min_val = 0.01
    max_val = 0.05
    random_amount = random.uniform(min_val, max_val)
    return w3.to_wei(round(random_amount, 4), 'ether')

# Generate random delay (1-3 minutes)
def get_random_delay():
    return random.randint(60, 180)  # Returns seconds

# Wrap MON to WMON
async def wrap_mon(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."

        print_border(f"Wrapping {w3.from_wei(amount, 'ether')} MON → WMON | {wallet}")
        tx = contract.functions.deposit().build_transaction({
            'from': account.address,
            'value': amount,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })

        print_step('wrap', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('wrap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(1)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('wrap', f"{Fore.GREEN}Wrap successful!{Style.RESET_ALL}")

    except Exception as e:
        print_step('wrap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Unwrap WMON to MON
async def unwrap_mon(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."

        print_border(f"Unwrapping {w3.from_wei(amount, 'ether')} WMON → MON | {wallet}")
        tx = contract.functions.withdraw(amount).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })

        print_step('unwrap', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('unwrap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(1)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('unwrap', f"{Fore.GREEN}Unwrap successful!{Style.RESET_ALL}")

    except Exception as e:
        print_step('unwrap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Run swap cycle for each private key
async def run_swap_cycle(cycles, private_keys):
    for account_idx, private_key in enumerate(private_keys, 1):
        wallet = w3.eth.account.from_key(private_key).address[:8] + "..."
        print_border(f"ACCOUNT {account_idx}/{len(private_keys)} | {wallet}", Fore.CYAN)

        for i in range(cycles):
            print_border(f"SWAP CYCLE {i + 1}/{cycles} | {wallet}")
            amount = get_random_amount()
            await wrap_mon(private_key, amount)
            await unwrap_mon(private_key, amount)
            if i < cycles - 1:
                delay = get_random_delay()
                print(f"\n{Fore.YELLOW}⏳ Waiting {delay / 60:.1f} minutes before next cycle...{Style.RESET_ALL}")
                await asyncio.sleep(delay)

        if account_idx < len(private_keys):
            delay = get_random_delay()
            print(f"\n{Fore.YELLOW}⏳ Waiting {delay / 60:.1f} minutes before next account...{Style.RESET_ALL}")
            await asyncio.sleep(delay)

    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ ALL DONE: {cycles} CYCLES FOR {len(private_keys)} ACCOUNTS{' ' * (32 - len(str(cycles)) - len(str(len(private_keys))))}│{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

# Main function
async def run():
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ {'IZUMI SWAP - MONAD TESTNET':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

    private_keys = load_private_keys('pvkey.txt')
    if not private_keys:
        return

    print(f"{Fore.CYAN}👥 Accounts: {len(private_keys)}{Style.RESET_ALL}")

    while True:
        try:
            print_border("NUMBER OF CYCLES", Fore.YELLOW)
            cycles_input = input(f"{Fore.GREEN}➤ Enter number (default 1): {Style.RESET_ALL}")
            cycles = int(cycles_input) if cycles_input.strip() else 1
            if cycles <= 0:
                raise ValueError
            break
        except ValueError:
            print(f"{Fore.RED}❌ Please enter a valid number!{Style.RESET_ALL}")

    print(f"{Fore.YELLOW}🚀 Running {cycles} swap cycles immediately for {len(private_keys)} accounts...{Style.RESET_ALL}")
    await run_swap_cycle(cycles, private_keys)

if __name__ == "__main__":
    asyncio.run(run())
