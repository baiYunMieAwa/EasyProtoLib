from easyprotolib.err import MCBlockNotFound
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gameobjects import MCBlock
    from .data_packet import MCPacket


class MCBlockEntitiesMap:
    __blocks: dict[int, type['MCBlock']] = {}

    @classmethod
    def set(cls, block_entity_id: int, block: type['MCBlock']) -> None:
        cls.__blocks[block_entity_id] = block

    @classmethod
    def get(cls, block_entity_id: int) -> type['MCBlock']:
        return cls.__blocks[block_entity_id]


class MCBlockMap:
    __blocks: list[type['MCBlock']] = []
    __air: list[int] = []

    @classmethod
    def set(cls, block: type['MCBlock']) -> None:
        cls.__blocks.append(block)
        if block.is_air():
            cls.__air.append(block.protocol_id)

    @classmethod
    def get_by_pid(cls, protocol_id: int) -> type['MCBlock']:
        for block in cls.__blocks:
            if protocol_id in block.protocol_ids:
                return block
        raise MCBlockNotFound()

    @classmethod
    def get_by_mcid(cls, mcid: str) -> type['MCBlock']:
        for block in cls.__blocks:
            if mcid == block.mcid:
                return block
        raise MCBlockNotFound()

    @classmethod
    def is_air(cls, protocol_id: int) -> bool:
        return protocol_id in cls.__air

    @classmethod
    def get_air_count(cls, protocol_id_list: list[int]) -> int:
        return sum(map(cls.__air.__contains__, protocol_id_list))


class MCPacketMap:
    __packets: dict[tuple[int, int, int], type['MCPacket'] | None] = {}

    @classmethod
    def set(cls, state: int, packet_id: int, direction: int, packet: type['MCPacket']) -> None:
        cls.__packets[(state, packet_id, direction)] = packet

    @classmethod
    def get(cls, state: int, packet_id: int, direction: int) -> type['MCPacket']:
        return cls.__packets[(state, packet_id, direction)]


class MCConnectMap:
    __id = -1

    @classmethod
    def get_new_id(cls):
        cls.__id += 1
        return cls.__id


__all__ = [
    "MCBlockEntitiesMap",
    "MCBlockMap",
    "MCPacketMap",
]
