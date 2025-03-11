import os
import asyncio
import random
from web3 import Web3
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Constants
RPC_URL = "https://testnet-rpc.monad.xyz"
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
CONTRACT_ADDRESS = "0xC995498c22a012353FAE7eCC701810D673E25794"

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

# Initialize web3 provider
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Check connection
if not w3.is_connected():
    print(f"{Fore.RED}❌ Could not connect to RPC{Style.RESET_ALL}")
    exit(1)

def print_border(text, color=Fore.CYAN, width=60):
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│ {text:^56} │{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

async def check_balance(wallet_address):
    print(f"{Fore.YELLOW}🔍 Checking balance...{Style.RESET_ALL}")
    balance = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_balance(wallet_address))
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"{Fore.CYAN}💰 Balance: {balance_eth} MONAD{Style.RESET_ALL}")

    if balance < w3.to_wei(0.1, 'ether') + w3.to_wei(0.01, 'ether'):  # 0.1 ETH + gas fee buffer
        print(f"{Fore.RED}❌ Insufficient balance for transaction!{Style.RESET_ALL}")
        return False
    return True


async def send_transaction(private_key):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet_address = account.address
        wallet_short = wallet_address[:8] + "..."

        print_border(f"Starting Monorail for {wallet_short}")
        if not await check_balance(wallet_address):
            return

        data = "0x96f25cbe0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e0590015a873bf326bd645c3e1266d4db41c4e6b000000000000000000000000000000000000000000000000016345785d8a0000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001a0000000000000000000000000" + wallet_address.replace('0x', '').lower() + "000000000000000000000000000000000000000000000000542f8f7c3d64ce470000000000000000000000000000000000000000000000000000002885eeed340000000000000000000000000000000000000000000000000000000000000004000000000000000000000000760afe86e5de5fa0ee542fc7b7b713e1c5425701000000000000000000000000760afe86e5de5fa0ee542fc7b7b713e1c5425701000000000000000000000000cba6b9a951749b8735c603e7ffc5151849248772000000000000000000000000760afe86e5de5fa0ee542fc7b7b713e1c54257010000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000014000000000000000000000000000000000000000000000000000000000000002800000000000000000000000000000000000000000000000000000000000000004d0e30db0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044095ea7b3000000000000000000000000cba6b9a951749b8735c603e7ffc5151849248772000000000000000000000000000000000000000000000000016345785d8a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010438ed1739000000000000000000000000000000000000000000000000016345785d8a0000000000000000000000000000000000000000000000000000542f8f7c3d64ce4700000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000c995498c22a012353fae7ecc701810d673e257940000000000000000000000000000000000000000000000000000002885eeed340000000000000000000000000000000000000000000000000000000000000002000000000000000000000000760afe86e5de5fa0ee542fc7b7b713e1c5425701000000000000000000000000e0590015a873bf326bd645c3e1266d4db41c4e6b000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044095ea7b3000000000000000000000000cba6b9a951749b8735c603e7ffc5151849248772000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        value = w3.to_wei(0.1, 'ether')

        try:
            gas_limit = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.estimate_gas({
                'from': wallet_address,
                'to': CONTRACT_ADDRESS,
                'value': value,
                'data': data
            }))
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Gas estimation failed. Using default gas limit. ({str(e)}){Style.RESET_ALL}")
            gas_limit = 500000

        tx = {
            'from': wallet_address,
            'to': CONTRACT_ADDRESS,
            'data': data,
            'value': value,
            'gas': gas_limit,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(wallet_address),
        }

        print(f"{Fore.BLUE}🚀 Sending transaction...{Style.RESET_ALL}")
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"{Fore.GREEN}✅ Transaction sent! Waiting for confirmation...{Style.RESET_ALL}")
        await asyncio.sleep(1)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"{Fore.GREEN}🎉 Transaction successful!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🔗 Explorer: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}❌ Error occurred: {str(e)}{Style.RESET_ALL}")

async def run():
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ {'MONORAIL - MONAD TESTNET':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

    private_keys = load_private_keys('pvkey.txt')
    if not private_keys:
        return

    print(f"{Fore.CYAN}👥 Accounts: {len(private_keys)}{Style.RESET_ALL}")

    for idx, private_key in enumerate(private_keys, 1):
        wallet_short = w3.eth.account.from_key(private_key).address[:8] + "..."
        print_border(f"ACCOUNT {idx}/{len(private_keys)} | {wallet_short}", Fore.CYAN)
        await send_transaction(private_key)
        if idx < len(private_keys):
            delay = random.randint(60, 180)  # Random delay 1-3 minutes
            print(f"\n{Fore.YELLOW}⏳ Waiting {delay / 60:.1f} minutes before next account...{Style.RESET_ALL}")
            await asyncio.sleep(delay)

    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ ALL DONE - {len(private_keys)} ACCOUNTS{' ' * (40 - len(str(len(private_keys))))}│{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(run())
