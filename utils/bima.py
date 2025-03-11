import asyncio
import random
from typing import Dict, List
from eth_account import Account
from eth_account.messages import encode_defunct
from loguru import logger
import aiohttp
from web3 import AsyncWeb3, Web3
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Define constants
RPC_URL = "https://testnet-rpc.monad.xyz/"
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
FAUCET_ADDRESS = "0xF2B87A9C773f468D4C9d1172b8b2C713f9481b80"
bmBTC = Web3.to_checksum_address("0x0bb0aa6aa3a3fd4f7a43fb5e3d90bf9e6b4ef799")
SPENDER_ADDRESS = Web3.to_checksum_address("0x07c4b0db9c020296275dceb6381397ac58bbf5c7")
ATTEMPTS = 3
PAUSE_BETWEEN_SWAPS = [5, 10]
RANDOM_PAUSE_BETWEEN_ACTIONS = [5, 15]
LEND = True
PERCENT_OF_BALANCE_TO_LEND = [20, 30]
BORDER_WIDTH = 80

# Define ABI directly in file
TOKEN_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

FAUCET_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_tokenAddress", "type": "address"}
        ],
        "name": "getTokens",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

MARKET_PARAMS = (
    Web3.to_checksum_address("0x01a4b3221e078106f9eb60c5303e3ba162f6a92e"),  # loanToken
    bmBTC,  # collateralToken
    Web3.to_checksum_address("0x7c47e0c69fb30fe451da48185c78f0c508b3e5b8"),  # oracle
    Web3.to_checksum_address("0xc2d07bd8df5f33453e9ad4e77436b3eb70a09616"),  # irm
    900000000000000000,  # lltv (0.9 в wei)
)

LENDING_ABI = [
    {
        "type": "function",
        "name": "supplyCollateral",
        "inputs": [
            {
                "name": "marketParams",
                "type": "tuple",
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"},
                ],
            },
            {"name": "assets", "type": "uint256"},
            {"name": "onBehalf", "type": "address"},
            {"name": "data", "type": "bytes"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    }
]

# Function to display a centered border with text
def print_border(text: str, color=Fore.CYAN, width=BORDER_WIDTH):
    text = text.strip()
    if len(text) > width - 4:  # -4 for the "│" characters and spaces
        text = text[:width - 7] + "..."  # Truncate and add ...
    padded_text = f" {text} ".center(width - 2)
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

# Function to display step with wide format, no TX hash truncation
def print_step(step: str, message: str):
    steps = {
        'login': 'LOGIN',
        'faucet': 'GET TOKENS',
        'approve': 'APPROVE',
        'lend': 'LEND',
        'balance': 'BALANCE'
    }
    step_text = steps[step]
    formatted_step = f"{Fore.YELLOW}🔸 {Fore.CYAN}{step_text:<15}{Style.RESET_ALL}"
    print(f"{formatted_step} | {message}")

# Function to display completion message
def print_completion_message(accounts: int, success_count: int):
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print_border("BIMA DEPOSIT - MONAD TESTNET", Fore.GREEN)
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🎉 {'Completed deposit for ' + str(accounts) + ' accounts':^76}{Style.RESET_ALL}")
    completion_msg = f"ALL DONE - {accounts} ACCOUNTS"
    print_border(completion_msg, Fore.GREEN)
    success_msg = f"SUCCESSFUL TRANSACTIONS: {success_count}"
    print_border(success_msg, Fore.CYAN)
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")


class Bima:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        private_key: str,
        session: aiohttp.ClientSession
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.session = session
        self.account = Account.from_key(private_key=private_key)
        self.web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))

    async def login(self) -> bool:
        """Login to Bima."""
        for retry in range(ATTEMPTS):
            try:
                message_to_sign, timestamp = await self._get_nonce()
                if not message_to_sign:
                    raise ValueError("Message to sign is empty")

                signature = "0x" + self._get_signature(message_to_sign)
                headers = self._get_headers()
                json_data = {"signature": signature, "timestamp": int(timestamp)}

                print_step('login', "Attempting to log in...")
                async with self.session.post(
                    "https://mainnet-api-v1.bima.money/bima/wallet/connect",
                    headers=headers,
                    json=json_data,
                ) as response:
                    response.raise_for_status()
                    logger.success(f"[{self.account_index}] Successfully logged in to Bima")
                    print_step('login', f"{Fore.GREEN}✔ Login successful!{Style.RESET_ALL}")
                    return True

            except Exception as e:
                await self._handle_error("login", e)
        print_step('login', f"{Fore.RED}✘ Login failed after {ATTEMPTS} attempts{Style.RESET_ALL}")
        return False

    async def lend(self) -> bool:
        """Perform lending on Bima."""
        if not LEND:
            print_step('lend', f"{Fore.YELLOW}⚠ Lending is disabled{Style.RESET_ALL}")
            return False

        for retry in range(ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Lending on Bima...")
                print_border(f"LENDING OPERATION - {self.account.address[:8]}", Fore.MAGENTA)
                token_contract = self.web3.eth.contract(address=bmBTC, abi=TOKEN_ABI)
                balance = await token_contract.functions.balanceOf(self.account.address).call()

                if balance == 0:
                    raise ValueError("Token balance is 0")

                logger.info(f"[{self.account_index}] Token balance: {Web3.from_wei(balance, 'ether')} bmBTC")
                print_step('lend', f"Balance: {Fore.CYAN}{Web3.from_wei(balance, 'ether')} bmBTC{Style.RESET_ALL}")
                amount_to_lend = self._calculate_lend_amount(balance)

                print_step('approve', f"Approving {amount_to_lend / 10**18:.4f} bmBTC for lending")
                await self._approve_token(amount_to_lend)
                await asyncio.sleep(random.uniform(*PAUSE_BETWEEN_SWAPS))

                print_step('lend', "Supplying collateral...")
                tx_hash = await self._supply_collateral(amount_to_lend)
                logger.success(f"[{self.account_index}] Successfully supplied collateral. TX: {EXPLORER_URL}{tx_hash.hex()}")
                print_step('lend', f"{Fore.GREEN}✔ Successfully supplied! TX: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                return True

            except Exception as e:
                await self._handle_error("lend", e)
        print_step('lend', f"{Fore.RED}✘ Lending failed after {ATTEMPTS} attempts{Style.RESET_ALL}")
        return False

    async def get_faucet_tokens(self) -> bool:
        """Get tokens from Bima faucet."""
        for retry in range(ATTEMPTS):
            try:
                if not await self.login():
                    raise ValueError("Failed to login to Bima")

                logger.info(f"[{self.account_index}] Getting tokens from Bima faucet...")
                print_border(f"FAUCET OPERATION - {self.account.address[:8]}", Fore.MAGENTA)
                print_step('faucet', "Requesting tokens from faucet...")

                # Check faucet bmBTC balance
                token_contract = self.web3.eth.contract(address=bmBTC, abi=TOKEN_ABI)
                faucet_balance = await token_contract.functions.balanceOf(FAUCET_ADDRESS).call()
                if faucet_balance == 0:
                    logger.warning(f"[{self.account_index}] Faucet has no bmBTC balance")
                    print_step('faucet', f"{Fore.RED}✘ Faucet is empty (0 bmBTC){Style.RESET_ALL}")
                    return False

                logger.info(f"[{self.account_index}] Faucet balance: {Web3.from_wei(faucet_balance, 'ether')} bmBTC")
                print_step('faucet', f"Faucet balance: {Fore.CYAN}{Web3.from_wei(faucet_balance, 'ether')} bmBTC{Style.RESET_ALL}")

                # Check wallet MON balance
                mon_balance = await self.web3.eth.get_balance(self.account.address)
                if mon_balance < Web3.to_wei(0.01, 'ether'):
                    logger.warning(f"[{self.account_index}] Insufficient MON balance: {Web3.from_wei(mon_balance, 'ether')} MON")
                    print_step('faucet', f"{Fore.RED}✘ Insufficient MON: {Web3.from_wei(mon_balance, 'ether')} MON{Style.RESET_ALL}")
                    return False

                print_step('faucet', f"Wallet MON: {Fore.CYAN}{Web3.from_wei(mon_balance, 'ether')} MON{Style.RESET_ALL}")

                # Try to build transaction
                contract = Web3().eth.contract(address=FAUCET_ADDRESS, abi=FAUCET_ABI)
                transaction = await self._build_transaction(
                    contract.functions.getTokens(bmBTC),
                    FAUCET_ADDRESS,
                )

                # Try to call transaction to check for detailed errors
                try:
                    await self.web3.eth.call(transaction)
                except Exception as call_error:
                    error_str = str(call_error).lower()
                    if "execution reverted" in error_str:
                        logger.warning(f"[{self.account_index}] Faucet call failed: Daily limit reached")
                        print_step('faucet', f"{Fore.YELLOW}⚠ Daily limit reached, try again in 24 hours{Style.RESET_ALL}")
                        return False
                    else:
                        raise call_error

                gas_params = await self._get_gas_params()
                transaction.update({"gas": await self._estimate_gas(transaction), **gas_params})

                tx_hash = await self._send_transaction(transaction)
                logger.success(f"[{self.account_index}] Successfully got tokens from Bima faucet. TX: {EXPLORER_URL}{tx_hash.hex()}")
                print_step('faucet', f"{Fore.GREEN}✔ Tokens received! TX: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
                return True

            except Exception as e:
                await self._handle_error("get_faucet_tokens", e)
        print_step('faucet', f"{Fore.RED}✘ Failed after {ATTEMPTS} attempts{Style.RESET_ALL}")
        return False

    async def _approve_token(self, amount: int) -> None:
        """Phê duyệt token để chi tiêu."""
        contract = Web3().eth.contract(address=bmBTC, abi=TOKEN_ABI)
        gas_params = await self._get_gas_params()

        transaction = await self._build_transaction(
            contract.functions.approve(SPENDER_ADDRESS, amount),
            bmBTC,
        )
        transaction.update({"gas": await self._estimate_gas(transaction), **gas_params})

        tx_hash = await self._send_transaction(transaction)
        logger.success(f"[{self.account_index}] Successfully approved bmBTC. TX: {EXPLORER_URL}{tx_hash.hex()}")
        print_step('approve', f"{Fore.GREEN}✔ Approved! TX: {EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")

    async def _supply_collateral(self, amount: int) -> bytes:
        """Cung cấp collateral cho lending."""
        contract = Web3().eth.contract(address=SPENDER_ADDRESS, abi=LENDING_ABI)
        gas_params = await self._get_gas_params()

        transaction = await self._build_transaction(
            contract.functions.supplyCollateral(
                MARKET_PARAMS,
                amount,
                self.account.address,
                "0x",
            ),
            SPENDER_ADDRESS,
        )
        transaction.update({"gas": await self._estimate_gas(transaction), **gas_params})

        return await self._send_transaction(transaction)

    async def _get_nonce(self) -> tuple[str, str]:
        """Lấy nonce để đăng nhập."""
        for retry in range(ATTEMPTS):
            try:
                async with self.session.get(
                    "https://mainnet-api-v1.bima.money/bima/wallet/tip_info",
                    headers=self._get_headers(),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data["data"]["tip_info"], data["data"]["timestamp"]
            except Exception as e:
                await self._handle_error("_get_nonce", e)
        return "", ""

    def _get_headers(self) -> Dict[str, str]:
        """Trả về headers mặc định."""
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-CH,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://bima.money",
            "Referer": "https://bima.money/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "address": self.account.address,
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

    def _calculate_lend_amount(self, balance: int) -> int:
        """Tính toán số lượng token để lend."""
        percent = random.uniform(*PERCENT_OF_BALANCE_TO_LEND)
        return int(balance * percent / 100)

    async def _get_gas_params(self) -> Dict[str, int]:
        """Lấy thông số gas từ mạng."""
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await self.web3.eth.max_priority_fee
        return {
            "maxFeePerGas": base_fee + max_priority_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

    async def _estimate_gas(self, transaction: dict) -> int:
        """Ước lượng gas cho giao dịch."""
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            return int(estimated * 1.1)  # Buffer 10%
        except Exception as e:
            logger.warning(f"[{self.account_index}] Gas estimation failed: {e}. Using default.")
            raise

    async def _build_transaction(self, function, to_address: str) -> Dict:
        """Xây dựng giao dịch cơ bản bất đồng bộ."""
        nonce = await self.web3.eth.get_transaction_count(self.account.address, "latest")
        return {
            "from": self.account.address,
            "to": to_address,
            "data": function._encode_transaction_data(),
            "chainId": 10143,
            "type": 2,
            "value": 0,
            "nonce": nonce,
        }

    async def _send_transaction(self, transaction: Dict) -> bytes:
        """Gửi giao dịch đã ký."""
        signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.info(f"[{self.account_index}] Waiting for transaction confirmation...")
        await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash

    def _get_signature(self, message: str) -> str:
        """Tạo chữ ký cho message."""
        encoded_msg = encode_defunct(text=message)
        signed_msg = Web3().eth.account.sign_message(encoded_msg, private_key=self.private_key)
        return signed_msg.signature.hex()

    async def _handle_error(self, action: str, error: Exception) -> None:
        """Xử lý lỗi với pause ngẫu nhiên."""
        pause = random.uniform(*RANDOM_PAUSE_BETWEEN_ACTIONS)
        logger.error(f"[{self.account_index}] Error in {action}: {error}. Sleeping for {pause:.2f}s")
        print_step(action, f"{Fore.RED}✘ Error: {str(error)}. Retrying in {pause:.2f}s{Style.RESET_ALL}")
        await asyncio.sleep(pause)


async def run() -> None:
    """Run Bima script with multiple private keys from pvkey.txt."""
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

    # Display opening title
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print_border("BIMA DEPOSIT - MONAD TESTNET", Fore.GREEN)
    print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}👥 {'Accounts'}: {len(private_keys):^76}{Style.RESET_ALL}")

    success_count = 0
    async with aiohttp.ClientSession() as session:
        for idx, private_key in enumerate(private_keys, start=1):
            wallet_short = Account.from_key(private_key).address[:8] + "..."
            account_msg = f"ACCOUNT {idx}/{len(private_keys)} - {wallet_short}"
            print_border(account_msg, Fore.BLUE)
            bima = Bima(idx, proxy="", private_key=private_key, session=session)
            logger.info(f"Processing account {idx}/{len(private_keys)}: {bima.account.address}")

            # Check wallet bmBTC balance
            token_contract = bima.web3.eth.contract(address=bmBTC, abi=TOKEN_ABI)
            wallet_balance = await token_contract.functions.balanceOf(bima.account.address).call()
            print_step('balance', f"Balance: {Fore.CYAN}{Web3.from_wei(wallet_balance, 'ether')} bmBTC{Style.RESET_ALL}")

            # Perform tasks in order
            if wallet_balance == 0:
                faucet_success = await bima.get_faucet_tokens()
                if not faucet_success:
                    continue  # Skip if faucet fails (out of tokens or daily limit)
            else:
                logger.info(f"[{bima.account_index}] Wallet already has bmBTC, skipping faucet")
                print_step('faucet', f"{Fore.YELLOW}⚠ Wallet has {Web3.from_wei(wallet_balance, 'ether')} bmBTC, skipping faucet{Style.RESET_ALL}")

            # Continue with lending if wallet has tokens or faucet was successful
            if await bima.lend():
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
    asyncio.run(run())  # Run with English by default
