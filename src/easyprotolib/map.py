from easyprotolib.err import MCBlockNotFound
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gameobjects import MCBlock
    from .data_packet import MCDataPacket


class MCBlockEntitiesMap:
    __blocks: dict[int, type['MCBlock']] = {}

    @classmethod
    def set(cls, block_entity_id: int, block: type['MCBlock']) -> None:
        cls.__blocks[block_entity_id] = block

    @classmethod
    def get(cls, block_entity_id: int) -> type['MCBlock']:
        return cls.__blocks[block_entity_id]


class MCBlockMap:
    __blocks: list[tuple[int, list[dict], type['MCBlock']]] = []
    __air: list[int] = []

    @classmethod
    def set(cls, protocol_id: int, protocol_data: list[dict], block: type['MCBlock']) -> None:
        cls.__blocks.append((protocol_id, protocol_data, block))
        if block.is_air():
            cls.__air.append(protocol_id)

    @classmethod
    def get(cls, protocol_id: int) -> type['MCBlock']:
        for id, data, block in cls.__blocks:
            if id == protocol_id:
                return block
        for id, data, block in cls.__blocks:
            if id < 0:
                for i in data:
                    if i["id"] == protocol_id:
                        return block
        raise MCBlockNotFound()

    @classmethod
    def is_air(cls, protocol_id: int) -> bool:
        return protocol_id in cls.__air

    @classmethod
    def get_air_count(cls, protocol_id_list: list[int]) -> int:
        return sum(map(cls.__air.__contains__, protocol_id_list))


class MCDataPacketMap:
    __packets: dict[tuple[int, int, int], type['MCDataPacket'] | None] = {}

    @classmethod
    def set(cls, state: int, packet_id: int, direction: int, packet: type['MCDataPacket']) -> None:
        cls.__packets[(state, packet_id, direction)] = packet

    @classmethod
    def get(cls, state: int, packet_id: int, direction: int) -> type['MCDataPacket']:
        return cls.__packets[(state, packet_id, direction)]


__all__ = [
    "MCBlockEntitiesMap",
    "MCBlockMap",
    "MCDataPacketMap",
]
