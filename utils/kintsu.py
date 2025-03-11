import os
import random
import asyncio
from web3 import Web3
from web3.exceptions import ContractLogicError
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Constants
RPC_URL = "https://testnet-rpc.monad.xyz/"
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
KITSU_STAKING_CONTRACT = "0x07AabD925866E8353407E67C1D157836f7Ad923e"

# Function to read multiple private keys from pvkey.txt
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

# ABI for staking contract
staking_abi = [
    {"name": "stake", "type": "function", "stateMutability": "payable", "inputs": [], "outputs": []},
    {"name": "withdraw", "type": "function", "stateMutability": "nonpayable", "inputs": [{"name": "amount", "type": "uint256"}], "outputs": [{"type": "bool"}]},
    {"name": "withdrawWithSelector", "type": "function", "stateMutability": "nonpayable", "inputs": [{"name": "amount", "type": "uint256"}], "outputs": [{"type": "bool"}], "selector": "0x30af6b2e"}
]

# Initialize contract
contract = w3.eth.contract(address=KITSU_STAKING_CONTRACT, abi=staking_abi)

# Function to display pretty border
def print_border(text, color=Fore.MAGENTA, width=60):
    print(f"{color}╔{'═' * (width - 2)}╗{Style.RESET_ALL}")
    print(f"{color}║ {text:^56} ║{Style.RESET_ALL}")
    print(f"{color}╚{'═' * (width - 2)}╝{Style.RESET_ALL}")

# Function to display step with prettier interface
def print_step(step, message):
    steps = {'stake': 'Stake MON', 'unstake': 'Unstake sMON'}
    step_text = steps[step]
    print(f"{Fore.YELLOW}🔸 {Fore.CYAN}{step_text:<15}{Style.RESET_ALL} | {message}")

# Generate random amount (0.01 - 0.05 MON)
def get_random_amount():
    min_val = 0.01
    max_val = 0.05
    random_amount = random.uniform(min_val, max_val)
    return w3.to_wei(round(random_amount, 4), 'ether')

# Generate random delay (1-3 minutes)
def get_random_delay():
    return random.randint(60, 180)  # Returns seconds

# Stake MON function
async def stake_mon(private_key, amount, cycle):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        
        print_border(f"[Cycle {cycle}] Staking {w3.from_wei(amount, 'ether')} MON | {wallet}", Fore.MAGENTA)
        
        balance = w3.eth.get_balance(account.address)
        print_step('stake', f"Balance: {Fore.CYAN}{w3.from_wei(balance, 'ether')} MON{Style.RESET_ALL}")
        if balance < amount:
            raise ValueError(f"Insufficient balance: {w3.from_wei(balance, 'ether')} MON < {w3.from_wei(amount, 'ether')} MON")

        tx = contract.functions.stake().build_transaction({
            'from': account.address,
            'value': amount,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })

        print_step('stake', "Sending stake transaction...")
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('stake', f"Tx Hash: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(2)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if receipt.status == 1:
            print_step('stake', f"{Fore.GREEN}✔ Stake successful!{Style.RESET_ALL}")
            return amount
        else:
            raise Exception(f"Transaction failed: Status {receipt.status}, Data: {receipt.get('data', 'N/A')}")

    except ContractLogicError as cle:
        print_step('stake', f"{Fore.RED}✘ Failed: Contract reverted - {str(cle)}{Style.RESET_ALL}")
        raise
    except Exception as e:
        print_step('stake', f"{Fore.RED}✘ Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Unstake sMON function
async def unstake_mon(private_key, amount, cycle):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        
        print_border(f"[Cycle {cycle}] Unstaking {w3.from_wei(amount, 'ether')} sMON | {wallet}", Fore.MAGENTA)
        
        tx = {
            'to': KITSU_STAKING_CONTRACT,
            'from': account.address,
            'data': "0x30af6b2e" + w3.to_hex(amount)[2:].zfill(64),
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        }

        print_step('unstake', "Sending unstake transaction...")
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('unstake', f"Tx Hash: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(2)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if receipt.status == 1:
            print_step('unstake', f"{Fore.GREEN}✔ Unstake successful!{Style.RESET_ALL}")
        else:
            raise Exception(f"Transaction failed: Status {receipt.status}, Data: {receipt.get('data', 'N/A')}")

    except ContractLogicError as cle:
        print_step('unstake', f"{Fore.RED}✘ Failed: Contract reverted - {str(cle)}{Style.RESET_ALL}")
        raise
    except Exception as e:
        print_step('unstake', f"{Fore.RED}✘ Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Run staking cycle for each private key
async def run_staking_cycle(cycles, private_keys):
    for account_idx, private_key in enumerate(private_keys, 1):
        wallet = w3.eth.account.from_key(private_key).address[:8] + "..."
        print_border(f"🏦 ACCOUNT {account_idx}/{len(private_keys)} | {wallet}", Fore.BLUE)

        for i in range(cycles):
            print_border(f"🔄 KITSU STAKING CYCLE {i + 1}/{cycles} | {wallet}", Fore.CYAN)
            amount = get_random_amount()
            try:
                stake_amount = await stake_mon(private_key, amount, i + 1)
                delay = get_random_delay()
                print(f"\n{Fore.YELLOW}⏳ Waiting {delay / 60:.1f} minutes before unstaking...{Style.RESET_ALL}")
                await asyncio.sleep(delay)
                await unstake_mon(private_key, stake_amount, i + 1)
            except Exception as e:
                print(f"{Fore.RED}❌ Error in cycle {i + 1}: {str(e)}{Style.RESET_ALL}")
                continue
            
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
    print(f"{Fore.GREEN}│ {'KITSU STAKING - MONAD TESTNET':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

    private_keys = load_private_keys('pvkey.txt')
    if not private_keys:
        return

    print(f"{Fore.CYAN}👥 Accounts: {len(private_keys)}{Style.RESET_ALL}")

    while True:
        try:
            print_border("🔢 NUMBER OF CYCLES", Fore.YELLOW)
            cycles_input = input(f"{Fore.GREEN}➤ Enter number (default 1): {Style.RESET_ALL}")
            cycles = int(cycles_input) if cycles_input.strip() else 1
            if cycles <= 0:
                raise ValueError
            break
        except ValueError:
            print(f"{Fore.RED}❌ Please enter a valid number!{Style.RESET_ALL}")

    print(f"{Fore.YELLOW}🚀 Running {cycles} Kitsu staking cycles for {len(private_keys)} accounts...{Style.RESET_ALL}")
    await run_staking_cycle(cycles, private_keys)

if __name__ == "__main__":
    asyncio.run(run())
