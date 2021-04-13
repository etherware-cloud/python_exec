from .net import get_ip_address
from .topic_processor import WriteableTopicServer, ReadableTopicServer
from .moderator import Moderator
from .storage import IncrementalStorage
from .typing import Type, Optional, TracebackType, List


class NotTopicError(Exception):
    pass


class TopicNode:
    def __init__(self, moderator: Moderator, storage: Type[IncrementalStorage]):
        self._moderator = moderator
        self._storage = storage
        self._topics = {}
        self._topic_counter = {}
        self._stock_counter = 0

    async def loop(self, readable: ReadableTopicServer, writeable: WriteableTopicServer):
        while True:
            data = await readable.get()
            await writeable.put(data)
            self._stock_counter += 1

    def _get_topics(self, topic_name: Optional[str] = None) -> List[str]:
        return (topic_name and [topic_name]) or self._topics.keys()

    async def start(self, topic_name: Optional[str] = None):
        topic_names = self._get_topics(topic_name)

        for topic_name in topic_names:
            await self._topics[topic_name][0].start()
            await self._topics[topic_name][1].start()

    async def stop(self, topic_name: Optional[str] = None):
        topic_names = self._get_topics(topic_name)

        for topic_name in topic_names:
            await self._topics[topic_name][0].stop()
            await self._topics[topic_name][1].stop()

    def add_topic(self, topic_name: str, interface=None) -> bool:
        if topic_name in self._topics:
            self._topic_counter[topic_name] += 1
            return False

        address = f"http://{get_ip_address(interface or 'lo')}:0"
        storage = self._storage()
        readable = ReadableTopicServer(storage, topic_name, address)
        writeable = WriteableTopicServer(storage, topic_name, address)

        self._moderator.publish_topic(
            topic_name,
            readable.get_address(),
            properties={"role": "producer"},
        )
        self._moderator.publish_topic(
            topic_name,
            writeable.get_address(),
            properties={"role": "consumer"},
        )

        self._topics[topic_name] = (readable, writeable)
        self._topic_counter[topic_name] = 1
        return True

    def get_readable(self, topic_name: str) -> ReadableTopicServer:
        try:
            topic = self._topics[topic_name]
        except KeyError:
            raise NotTopicError
        else:
            return topic[0]

    def get_writeable(self, topic_name: str) -> WriteableTopicServer:
        try:
            topic = self._topics[topic_name]
        except KeyError:
            raise NotTopicError
        else:
            return topic[1]

    async def del_topic(self, topic_name: str) -> bool:
        counter = self._topic_counter.get(topic_name, 0)
        if counter > 1:
            self._topic_counter[topic_name] -= 1
            return True
        elif counter == 1:
            self._moderator.unpublish_topic(topic_name)
            await self.stop(topic_name)
            del self._topics[topic_name]
            self._topic_counter[topic_name] = 0
            return True
        else:
            return False

    def sync_topic(self, topic_name: str):
        raise NotImplementedError

    async def __aenter__(self) -> 'TopicNode':
        await self.start()
        return self

    async def __aexit__(self, exception_type: Optional[Type[BaseException]], exception_value: Optional[BaseException],
                        traceback: Optional[TracebackType]):
        await self.stop()
