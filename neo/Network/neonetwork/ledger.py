import binascii
import asyncio
from typing import TYPE_CHECKING, List
from neo.Core.Blockchain import Blockchain
from neo.Core.Block import Block
from neo.IO.Helper import Helper as IOHelper
from neo.Network.neonetwork.core.uint256 import UInt256
from neo.logging import log_manager

logger = log_manager.getLogger('db')

if TYPE_CHECKING:
    from neo.Network.neonetwork.core.header import Header
    from neo.Network.neonetwork.network.payloads.block import Block as NetworkBlock
    from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import LevelDBBlockchain


class Ledger:
    def __init__(self, controller=None):
        self.controller = controller
        self.ledger = Blockchain.Default()  # type: LevelDBBlockchain

    async def cur_header_height(self) -> int:
        return self.ledger.HeaderHeight
        # return await self.controller.get_current_header_height()

    async def cur_block_height(self) -> int:
        # return await self.controller.get_current_block_height()
        return self.ledger.Height

    async def header_hash_by_height(self, height: int) -> 'UInt256':
        # return await self.controller.get_header_hash_by_height(height)
        header_hash = self.ledger.GetHeaderHash(height)
        if header_hash is None:
            data = bytearray(32)
        else:
            data = bytearray(binascii.unhexlify(header_hash))
            data.reverse()
        return UInt256(data=data)

    async def add_headers(self, network_headers: List['Header']) -> bool:
        """

        Args:
            headers:

        Returns: if successfully added

        """
        # return await self.controller.add_headers(headers)
        headers = []
        success = False
        for h in network_headers:
            header = IOHelper.AsSerializableWithType(h.to_array(), 'neo.Core.Header.Header')
            if header is None:
                break
            else:
                headers.append(header)
            # just making sure we don't block too long while converting
            await asyncio.sleep(0.001)
        else:
            success = self.ledger.AddHeaders(headers)

        return success

    async def add_block(self, raw_block: bytes) -> bool:
        # return await self.controller.add_block(block)
        block = IOHelper.AsSerializableWithType(raw_block, 'neo.Core.Block.Block')  # type: Block

        if block is None:
            return False
        else:
            header_success = self.ledger.AddHeader(block.Header)
            if not header_success:
                return False
            try:
                self.ledger.Persist(block)
            except Exception as e:
                logger.info(f"Could not persist block {block.Index} reason: {e}")
                return False

            try:
                self.ledger.OnPersistCompleted(block)
            except Exception as e:
                logger.debug(f"Failed to broadcast OnPersistCompleted event, reason: {e}")

        return True
