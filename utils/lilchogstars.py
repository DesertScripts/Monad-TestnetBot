import asyncio
import random
from typing import Dict, List
from eth_account import Account
import aiohttp
from web3 import AsyncWeb3, Web3
from loguru import logger
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Constants
RPC_URL = "https://testnet-rpc.monad.xyz/"
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
NFT_CONTRACT_ADDRESS = "0xb33D7138c53e516871977094B249C8f2ab89a4F4"
BORDER_WIDTH = 80
ATTEMPTS = 3
PAUSE_BETWEEN_ACTIONS = [5, 15]
MAX_AMOUNT_FOR_EACH_ACCOUNT = [1, 3]

# ERC1155 ABI
ERC1155_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"},
            {"internalType": "uint256", "name": "id", "type": "uint256"},
        ],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "quantity", "type": "uint256"}],
        "name": "mint",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "mintedCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

def print_border(text: str, color=Fore.CYAN, width=BORDER_WIDTH):
    text = text.strip()
    if len(text) > width - 4:
        text = text[:width - 7] + "..."
    padded_text = f" {text} ".center(width - 2)
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

def print_step(step: str, message: str):
    steps = {
        'balance': 'BALANCE',
        'mint': 'MINT NFT'
    }
    step_text = steps[step]
    formatted_step = f"{Fore.YELLOW}🔸 {Fore.CYAN}{step_text:<15}{Style.RESET_ALL}"
    print(f"{formatted_step} | {message}")

def print_completion_message(accounts: int, success_count: int):
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print_border("LILCHOGSTARS MINT - MONAD TESTNET", Fore.GREEN)
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🎉 {'Completed NFT minting for ' + str(accounts) + ' accounts':^76}{Style.RESET_ALL}")
    completion_msg = f"ALL DONE - {accounts} ACCOUNTS"
    print_border(completion_msg, Fore.GREEN)
    success_msg = f"SUCCESSFUL NFT MINTS: {success_count}"
    print_border(success_msg, Fore.CYAN)
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")

class Lilchogstars:
    def __init__(self, account_index: int, private_key: str, session: aiohttp.ClientSession):
        self.account_index = account_index
        self.private_key = private_key
        self.session = session
        self.account = Account.from_key(private_key=private_key)
        self.web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))
        self.nft_contract = self.web3.eth.contract(address=NFT_CONTRACT_ADDRESS, abi=ERC1155_ABI)

    async def get_nft_balance(self) -> int:
        """Check NFT balance of the account."""
        for retry in range(ATTEMPTS):
            try:
                balance = await self.nft_contract.functions.mintedCount(self.account.address).call()
                logger.info(f"[{self.account_index}] NFT balance: {balance}")
                return balance
            except Exception as e:
                await self._handle_error("get_nft_balance", e)
        raise Exception("Failed to get NFT balance after retries")

    async def mint(self) -> bool:
        """Mint Lilchogstars NFT."""
        for retry in range(ATTEMPTS):
            try:
                balance = await self.get_nft_balance()
                random_amount = random.randint(MAX_AMOUNT_FOR_EACH_ACCOUNT[0], MAX_AMOUNT_FOR_EACH_ACCOUNT[1])
                
                print_step('balance', f"Current NFT balance: {Fore.CYAN}{balance} / Target: {random_amount}{Style.RESET_ALL}")
                
                if balance >= random_amount:
                    print_step('mint', f"{Fore.GREEN}✔ Already minted: {balance} NFTs{Style.RESET_ALL}")
                    return True

                print_step('mint', "Minting Lilchogstars NFT...")
                mint_txn = await self.nft_contract.functions.mint(1).build_transaction({
                    "from": self.account.address,
                    "value": 0,  # Free mint
                    "nonce": await self.web3.eth.get_transaction_count(self.account.address),
                    "type": 2,
                    "chainId": 10143,
                    **(await self._get_gas_params()),
                })
                signed_txn = self.web3.eth.account.sign_transaction(mint_txn, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt["status"] == 1:
                    print_step('mint', f"{Fore.GREEN}✔ Successfully minted! TX: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                    logger.success(f"[{self.account_index}] Successfully minted NFT. TX: {EXPLORER_URL}{tx_hash.hex()}")
                    return True
                else:
                    logger.error(f"[{self.account_index}] Mint failed. TX: {EXPLORER_URL}{tx_hash.hex()}")
                    print_step('mint', f"{Fore.RED}✘ Mint failed: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                    return False
            except Exception as e:
                await self._handle_error("mint", e)
        print_step('mint', f"{Fore.RED}✘ Failed to mint after {ATTEMPTS} attempts{Style.RESET_ALL}")
        return False

    async def _get_gas_params(self) -> Dict[str, int]:
        """Get gas parameters from the network."""
        latest_block = await self.web3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        max_priority_fee = await self.web3.eth.max_priority_fee
        return {
            "maxFeePerGas": base_fee + max_priority_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

    async def _handle_error(self, action: str, error: Exception) -> None:
        """Handle errors with random pause."""
        pause = random.uniform(*PAUSE_BETWEEN_ACTIONS)
        logger.error(f"[{self.account_index}] Error in {action}: {error}. Sleeping for {pause:.2f}s")
        print_step(action, f"{Fore.RED}✘ Error: {str(error)}. Retrying in {pause:.2f}s{Style.RESET_ALL}")
        await asyncio.sleep(pause)



async def run() -> None:
    """Run Lilchogstars script with multiple private keys from pvkey.txt."""
    try:
        with open("pvkey.txt", "r") as f:
            private_keys = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("File pvkey.txt not found!")
        print_border("ERROR: pvkey.txt not found!", Fore.RED)
        return

    if not private_keys:
        logger.error("No private keys found in pvkey.txt!")
        print_border("ERROR: No private keys found in pvkey.txt!", Fore.RED)
        return

    # Display initial title
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print_border("LILCHOGSTARS MINT - MONAD TESTNET", Fore.GREEN)
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}👥 {'Accounts'}: {len(private_keys):^76}{Style.RESET_ALL}")

    success_count = 0
    async with aiohttp.ClientSession() as session:
        for idx, private_key in enumerate(private_keys, start=1):
            wallet_short = Account.from_key(private_key).address[:8] + "..."
            account_msg = f"ACCOUNT {idx}/{len(private_keys)} - {wallet_short}"
            print_border(account_msg, Fore.BLUE)
            lilchogstars = Lilchogstars(idx, private_key, session)
            logger.info(f"Processing account {idx}/{len(private_keys)}: {lilchogstars.account.address}")

            # Perform mint
            if await lilchogstars.mint():
                success_count += 1

            # Pause between accounts
            if idx < len(private_keys):
                pause = random.uniform(10, 30)
                pause_msg = f"Waiting {pause:.2f}s before next account..."
                print(f"{Fore.YELLOW}⏳ {pause_msg:^76}{Style.RESET_ALL}")
                await asyncio.sleep(pause)

    # Display completion message
    print_completion_message(accounts=len(private_keys), success_count=success_count)

if __name__ == "__main__":
    asyncio.run(run())
