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
MAGMA_CONTRACT = "0x2c9C959516e9AAEdB2C748224a41249202ca8BE7"
GAS_LIMIT_STAKE = 500000
GAS_LIMIT_UNSTAKE = 800000

# Function to read private keys from pvkey.txt
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

# Function to display border
def print_border(text, color=Fore.CYAN, width=60):
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│ {text:^56} │{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

# Function to display step
def print_step(step, message):
    steps = {'stake': 'Stake MON', 'unstake': 'Unstake gMON'}
    step_text = steps[step]
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

# Stake MON
async def stake_mon(private_key, amount, cycle):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        
        print_border(f"[Cycle {cycle}] Staking {w3.from_wei(amount, 'ether')} MON | {wallet}")
        
        tx = {
            'to': MAGMA_CONTRACT,
            'data': '0xd5575982',
            'from': account.address,
            'value': amount,
            'gas': GAS_LIMIT_STAKE,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        }

        print_step('stake', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('stake', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(1)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('stake', f"{Fore.GREEN}Stake successful!{Style.RESET_ALL}")

        return amount

    except Exception as e:
        print_step('stake', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Unstake gMON
async def unstake_gmon(private_key, amount, cycle):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        
        print_border(f"[Cycle {cycle}] Unstaking {w3.from_wei(amount, 'ether')} gMON | {wallet}")
        
        data = "0x6fed1ea7" + w3.to_hex(amount)[2:].zfill(64)
        tx = {
            'to': MAGMA_CONTRACT,
            'data': data,
            'from': account.address,
            'gas': GAS_LIMIT_UNSTAKE,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        }

        print_step('unstake', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print_step('unstake', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(1)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('unstake', f"{Fore.GREEN}Unstake successful!{Style.RESET_ALL}")

    except Exception as e:
        print_step('unstake', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Run staking cycle for each private key
async def run_staking_cycle(cycles, private_keys):
    for account_idx, private_key in enumerate(private_keys, 1):
        wallet = w3.eth.account.from_key(private_key).address[:8] + "..."
        print_border(f"ACCOUNT {account_idx}/{len(private_keys)} | {wallet}", Fore.CYAN)

        for i in range(cycles):
            print_border(f"STAKING CYCLE {i + 1}/{cycles} | {wallet}")
            amount = get_random_amount()
            stake_amount = await stake_mon(private_key, amount, i + 1)
            delay = get_random_delay()
            print(f"\n{Fore.YELLOW}⏳ Waiting {delay / 60:.1f} minutes before unstaking...{Style.RESET_ALL}")
            await asyncio.sleep(delay)
            await unstake_gmon(private_key, stake_amount, i + 1)
            
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
    print(f"{Fore.GREEN}│ {'MAGMA STAKING - MONAD TESTNET':^56} │{Style.RESET_ALL}")
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

    print(f"{Fore.YELLOW}🚀 Running {cycles} staking cycles immediately for {len(private_keys)} accounts...{Style.RESET_ALL}")
    await run_staking_cycle(cycles, private_keys)

if __name__ == "__main__":
    asyncio.run(run())
