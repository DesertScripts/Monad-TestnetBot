import os
import random
import asyncio
import time
from web3 import Web3
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Constants
RPC_URLS = [
    "https://testnet-rpc.monorail.xyz",
    "https://testnet-rpc.monad.xyz",
    "https://monad-testnet.drpc.org"
]
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
UNISWAP_V2_ROUTER_ADDRESS = "0xCa810D095e90Daae6e867c19DF6D9A8C56db2c89"
WETH_ADDRESS = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"

# List of supported tokens
TOKEN_ADDRESSES = {
    "DAC": "0x0f0bdebf0f83cd1ee3974779bcb7315f9808c714",
    "USDT": "0x88b8e2161dedc77ef4ab7585569d2415a1c1055d",
    "WETH": "0x836047a99e11f376522b447bffb6e3495dd0637c",
    "MUK": "0x989d38aeed8408452f0273c7d4a17fef20878e62",
    "USDC": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",
    "CHOG": "0xE0590015A873bF326bd645c3E1266d4db41C4E6B"
}

# ABI for ERC20 token
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

# ABI for Uniswap V2 Router
ROUTER_ABI = [
    {
        "name": "swapExactETHForTokens",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]
    },
    {
        "name": "swapExactTokensForETH",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]
    }
]

# Function to read private keys from pvkey.txt
def load_private_keys(file_path='pvkey.txt'):
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

# Function to connect to RPC
def connect_to_rpc():
    for url in RPC_URLS:
        w3 = Web3(Web3.HTTPProvider(url))
        if w3.is_connected():
            print(f"{Fore.BLUE}🪫 Connected to RPC: {url}{Style.RESET_ALL}")
            return w3
        print(f"{Fore.YELLOW}Failed to connect to {url}, trying next RPC...{Style.RESET_ALL}")
    raise Exception(f"{Fore.RED}❌ Could not connect to any RPC{Style.RESET_ALL}")

# Initialize web3 provider
w3 = connect_to_rpc()
UNISWAP_V2_ROUTER_ADDRESS = w3.to_checksum_address(UNISWAP_V2_ROUTER_ADDRESS)
WETH_ADDRESS = w3.to_checksum_address(WETH_ADDRESS)
TOKEN_ADDRESSES = {key: w3.to_checksum_address(value) for key, value in TOKEN_ADDRESSES.items()}

# Function to display pretty border
def print_border(text, color=Fore.MAGENTA, width=60):
    print(f"{color}╔{'═' * (width - 2)}╗{Style.RESET_ALL}")
    print(f"{color}║ {text:^56} ║{Style.RESET_ALL}")
    print(f"{color}╚{'═' * (width - 2)}╝{Style.RESET_ALL}")

# Function to display step
def print_step(step, message):
    steps = {'approve': 'Approve', 'swap': 'Swap', 'balance': 'Balance'}
    step_text = steps[step]
    print(f"{Fore.YELLOW}🔸 {Fore.CYAN}{step_text:<15}{Style.RESET_ALL} | {message}")

# Generate random ETH amount (0.0001 - 0.01)
def get_random_eth_amount():
    return w3.to_wei(round(random.uniform(0.0001, 0.01), 6), 'ether')

# Generate random delay (1-3 minutes)
def get_random_delay():
    return random.randint(60, 180)  # Returns seconds

# Retry function for 429 errors
async def retry_on_429(operation, max_retries=3, base_delay=2):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if "429 Client Error" in str(e) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                print(f"{Fore.YELLOW}⚠ Too many requests, retrying in {delay} seconds...{Style.RESET_ALL}")
                await asyncio.sleep(delay)
            else:
                raise e

# Function to approve token
async def approve_token(private_key, token_address, amount, token_symbol):
    account = w3.eth.account.from_key(private_key)
    wallet = account.address[:8] + "..."

    async def do_approve():
        token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        balance = token_contract.functions.balanceOf(account.address).call()
        if balance < amount:
            raise ValueError(f"Insufficient {token_symbol} balance: {balance / 10**18} < {amount / 10**18}")

        print_step('approve', f'Approving {token_symbol}')
        tx = token_contract.functions.approve(UNISWAP_V2_ROUTER_ADDRESS, amount).build_transaction({
            'from': account.address,
            'gas': 150000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print_step('approve', f"Tx Hash: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(2)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise Exception(f"Approval failed: Status {receipt.status}")
        print_step('approve', f"{Fore.GREEN}✔ {token_symbol} approved{Style.RESET_ALL}")

    try:
        await retry_on_429(do_approve)
    except Exception as e:
        print_step('approve', f"{Fore.RED}✘ Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Function to swap MON to token
async def swap_eth_for_tokens(private_key, token_address, amount_in_wei, token_symbol):
    account = w3.eth.account.from_key(private_key)
    wallet = account.address[:8] + "..."

    async def do_swap():
        print_border(f"Swapping {w3.from_wei(amount_in_wei, 'ether')} MON to {token_symbol} | {wallet}", Fore.MAGENTA)
        
        mon_balance = w3.eth.get_balance(account.address)
        if mon_balance < amount_in_wei:
            raise ValueError(f"Insufficient MON balance: {w3.from_wei(mon_balance, 'ether')} < {w3.from_wei(amount_in_wei, 'ether')}")

        router = w3.eth.contract(address=UNISWAP_V2_ROUTER_ADDRESS, abi=ROUTER_ABI)
        tx = router.functions.swapExactETHForTokens(
            0, [WETH_ADDRESS, token_address], account.address, int(time.time()) + 600
        ).build_transaction({
            'from': account.address,
            'value': amount_in_wei,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })

        print_step('swap', 'Sending...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print_step('swap', f"Tx Hash: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(2)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if receipt.status == 1:
            print_step('swap', f"{Fore.GREEN}✔ Swap successful!{Style.RESET_ALL}")
            return True
        raise Exception(f"Transaction failed: Status {receipt.status}")

    try:
        return await retry_on_429(do_swap)
    except Exception as e:
        print_step('swap', f"{Fore.RED}✘ Failed: {str(e)}{Style.RESET_ALL}")
        return False

# Function to swap token to MON
async def swap_tokens_for_eth(private_key, token_address, token_symbol):
    account = w3.eth.account.from_key(private_key)
    wallet = account.address[:8] + "..."

    async def do_swap():
        print_border(f"Swapping {token_symbol} to MON | {wallet}", Fore.MAGENTA)
        
        token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        balance = token_contract.functions.balanceOf(account.address).call()
        if balance == 0:
            print_step('swap', f"{Fore.BLACK}⚠ No {token_symbol}, skipping{Style.RESET_ALL}")
            return False

        await approve_token(private_key, token_address, balance, token_symbol)
        
        router = w3.eth.contract(address=UNISWAP_V2_ROUTER_ADDRESS, abi=ROUTER_ABI)
        tx = router.functions.swapExactTokensForETH(
            balance, 0, [token_address, WETH_ADDRESS], account.address, int(time.time()) + 600
        ).build_transaction({
            'from': account.address,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })

        print_step('swap', 'Sending...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print_step('swap', f"Tx Hash: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        await asyncio.sleep(2)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if receipt.status == 1:
            print_step('swap', f"{Fore.GREEN}✔ Swap successful!{Style.RESET_ALL}")
            return True
        raise Exception(f"Transaction failed: Status {receipt.status}")

    try:
        return await retry_on_429(do_swap)
    except Exception as e:
        print_step('swap', f"{Fore.RED}✘ Failed: {str(e)}{Style.RESET_ALL}")
        return False

# Function to check balance
async def check_balance(private_key):
    account = w3.eth.account.from_key(private_key)
    wallet = account.address[:8] + "..."
    print_border(f"💰 Balance | {wallet}", Fore.CYAN)

    async def get_mon_balance():
        balance = w3.eth.get_balance(account.address)
        print_step('balance', f"MON: {Fore.CYAN}{w3.from_wei(balance, 'ether')}{Style.RESET_ALL}")

    async def get_token_balance(symbol, address):
        token_contract = w3.eth.contract(address=address, abi=ERC20_ABI)
        balance = token_contract.functions.balanceOf(account.address).call()
        print_step('balance', f"{symbol}: {Fore.CYAN}{balance / 10**18}{Style.RESET_ALL}")

    try:
        await retry_on_429(get_mon_balance)
        for symbol, addr in TOKEN_ADDRESSES.items():
            await retry_on_429(lambda: get_token_balance(symbol, addr))
    except Exception as e:
        print_step('balance', f"{Fore.RED}✘ Error reading balance: {str(e)}{Style.RESET_ALL}")

# Run swap cycle for each private key
async def run_swap_cycle(cycles, private_keys):
    for account_idx, private_key in enumerate(private_keys, 1):
        wallet = w3.eth.account.from_key(private_key).address[:8] + "..."
        print_border(f"🏦 ACCOUNT {account_idx}/{len(private_keys)} | {wallet}", Fore.BLUE)
        await check_balance(private_key)

        for i in range(cycles):
            print_border(f"🔄 UNISWAP SWAP CYCLE {i + 1}/{cycles} | {wallet}", Fore.CYAN)
            
            # Swap MON to tokens
            for token_symbol, token_address in TOKEN_ADDRESSES.items():
                eth_amount = get_random_eth_amount()
                await swap_eth_for_tokens(private_key, token_address, eth_amount, token_symbol)
                await asyncio.sleep(5)  # 5 seconds delay between swaps

            # Swap tokens back to MON
            print_border(f"🔄 SWAP ALL TOKENS BACK TO MON | {wallet}", Fore.CYAN)
            for token_symbol, token_address in TOKEN_ADDRESSES.items():
                await swap_tokens_for_eth(private_key, token_address, token_symbol)
                await asyncio.sleep(5)  # 5 seconds delay between swaps

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
    print(f"{Fore.GREEN}│ {'UNISWAP - MONAD TESTNET':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

    private_keys = load_private_keys('pvkey.txt')
    if not private_keys:
        return

    print(f"{Fore.CYAN}👥 Accounts: {len(private_keys)}{Style.RESET_ALL}")

    while True:
        try:
            print_border("🔢 NUMBER OF CYCLES", Fore.YELLOW)
            cycles_input = input(f"{Fore.GREEN}➤ Enter number of cycles (default 5): {Style.RESET_ALL}")
            cycles = int(cycles_input) if cycles_input.strip() else 5
            if cycles <= 0:
                raise ValueError
            break
        except ValueError:
            print(f"{Fore.RED}❌ Please enter a valid number!{Style.RESET_ALL}")

    print(f"{Fore.YELLOW}🚀 Running {cycles} Uniswap swap cycles with random 1-3 minute delay for {len(private_keys)} accounts...{Style.RESET_ALL}")
    await run_swap_cycle(cycles, private_keys)

if __name__ == "__main__":
    asyncio.run(run())
