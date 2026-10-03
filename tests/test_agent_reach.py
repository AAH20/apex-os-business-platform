"""Tests for the Agent-Reach core module."""

import unittest

from apex_os_bp.agent_reach import (
    Agent,
    AgentStatus,
    Channel,
    ConsistentHashing,
    LeastConnections,
    Message,
    MessageBroker,
    MessageRouter,
    RoundRobin,
    Route,
)


class TestAgent(unittest.TestCase):
    def test_agent_creation_defaults(self):
        agent = Agent(name="test-agent")
        self.assertIsNotNone(agent.id)
        self.assertEqual(agent.name, "test-agent")
        self.assertEqual(agent.status, AgentStatus.IDLE)
        self.assertTrue(agent.is_available)

    def test_agent_assign_and_release(self):
        agent = Agent(capacity=2)
        agent.assign()
        self.assertEqual(agent.active_connections, 1)
        self.assertEqual(agent.status, AgentStatus.IDLE)
        agent.assign()
        self.assertEqual(agent.status, AgentStatus.BUSY)
        self.assertFalse(agent.is_available)
        agent.release()
        self.assertEqual(agent.status, AgentStatus.IDLE)
        self.assertTrue(agent.is_available)

    def test_agent_offline_not_available(self):
        agent = Agent(status=AgentStatus.OFFLINE)
        self.assertFalse(agent.is_available)


class TestMessage(unittest.TestCase):
    def test_message_creation(self):
        msg = Message(sender_id="a1", recipient_id="a2", payload={"key": "value"})
        self.assertIsNotNone(msg.id)
        self.assertEqual(msg.sender_id, "a1")
        self.assertEqual(msg.payload, {"key": "value"})

    def test_message_with_channel(self):
        msg = Message(channel_id="ch1", payload="hello")
        self.assertEqual(msg.channel_id, "ch1")


class TestChannel(unittest.TestCase):
    def test_subscribe_unsubscribe(self):
        ch = Channel(name="test")
        self.assertTrue(ch.subscribe("agent-1"))
        self.assertFalse(ch.subscribe("agent-1"))
        self.assertIn("agent-1", ch.subscribers)
        self.assertTrue(ch.unsubscribe("agent-1"))
        self.assertNotIn("agent-1", ch.subscribers)

    def test_unsubscribe_nonexistent(self):
        ch = Channel(name="test")
        self.assertFalse(ch.unsubscribe("ghost"))


class TestRoute(unittest.TestCase):
    def test_route_creation(self):
        route = Route(source_pattern="worker-*", target_agent_ids=["a1", "a2"])
        self.assertEqual(route.source_pattern, "worker-*")
        self.assertEqual(route.target_agent_ids, ["a1", "a2"])


class TestRoundRobin(unittest.TestCase):
    def test_select_cycles(self):
        agents = [Agent(name=f"a{i}") for i in range(3)]
        lb = RoundRobin(agents)
        seen = [lb.select() for _ in range(6)]
        self.assertEqual(seen[0].id, seen[3].id)
        self.assertEqual(seen[1].id, seen[4].id)

    def test_select_skips_unavailable(self):
        a1 = Agent(status=AgentStatus.OFFLINE)
        a2 = Agent()
        lb = RoundRobin([a1, a2])
        self.assertEqual(lb.select().id, a2.id)

    def test_add_remove_agent(self):
        lb = RoundRobin()
        agent = Agent()
        lb.add_agent(agent)
        self.assertEqual(lb.select().id, agent.id)
        self.assertTrue(lb.remove_agent(agent.id))
        self.assertIsNone(lb.select())


class TestLeastConnections(unittest.TestCase):
    def test_selects_least_connected(self):
        a1 = Agent()
        a1.assign()
        a1.assign()
        a2 = Agent()
        a2.assign()
        lb = LeastConnections([a1, a2])
        self.assertEqual(lb.select().id, a2.id)

    def test_all_busy_returns_none(self):
        a1 = Agent(capacity=1)
        a1.assign()
        lb = LeastConnections([a1])
        self.assertIsNone(lb.select())


class TestConsistentHashing(unittest.TestCase):
    def test_select_returns_agent(self):
        agents = [Agent(name=f"a{i}") for i in range(3)]
        lb = ConsistentHashing(agents)
        agent = lb.select("some-key")
        self.assertIsNotNone(agent)
        self.assertIn(agent.id, [a.id for a in agents])

    def test_consistent_mapping(self):
        agents = [Agent(name=f"a{i}") for i in range(3)]
        lb = ConsistentHashing(agents)
        first = lb.select("stable-key").id
        second = lb.select("stable-key").id
        self.assertEqual(first, second)

    def test_remove_agent(self):
        agents = [Agent(name=f"a{i}") for i in range(3)]
        lb = ConsistentHashing(agents)
        lb.remove_agent(agents[0].id)
        agent = lb.select("key")
        self.assertIsNotNone(agent)
        self.assertNotEqual(agent.id, agents[0].id)


class TestMessageRouter(unittest.TestCase):
    def test_register_and_route(self):
        router = MessageRouter()
        agent = Agent()
        router.register_agent(agent)
        msg = Message(sender_id="test")
        result = router.route(msg)
        self.assertEqual(result.id, agent.id)

    def test_route_with_rule(self):
        router = MessageRouter()
        a1 = Agent()
        a2 = Agent()
        router.register_agent(a1)
        router.register_agent(a2)
        route = Route(source_pattern="worker-*", target_agent_ids=[a2.id])
        router.add_route(route)
        msg = Message(sender_id="worker-1")
        result = router.route(msg)
        self.assertEqual(result.id, a2.id)

    def test_unregister_agent(self):
        router = MessageRouter()
        agent = Agent()
        router.register_agent(agent)
        self.assertTrue(router.unregister_agent(agent.id))
        self.assertEqual(router.agent_count, 0)

    def test_release_agent(self):
        router = MessageRouter()
        agent = Agent()
        router.register_agent(agent)
        msg = Message()
        router.route(msg)
        self.assertEqual(agent.active_connections, 1)
        router.release(agent.id)
        self.assertEqual(agent.active_connections, 0)

    def test_no_available_agents(self):
        router = MessageRouter()
        msg = Message()
        self.assertIsNone(router.route(msg))


class TestMessageBroker(unittest.TestCase):
    def test_create_and_delete_channel(self):
        broker = MessageBroker()
        ch = broker.create_channel("test")
        self.assertEqual(broker.channel_count, 1)
        self.assertTrue(broker.delete_channel(ch.id))
        self.assertEqual(broker.channel_count, 0)

    def test_subscribe_and_publish(self):
        broker = MessageBroker()
        broker.create_channel("news")
        broker.subscribe("news", "agent-1")
        msg = Message(channel_id="news", payload="hello")
        delivered = broker.publish(msg)
        self.assertEqual(delivered, 1)

    def test_consume_message(self):
        broker = MessageBroker()
        broker.create_channel("news")
        broker.subscribe("news", "agent-1")
        msg = Message(channel_id="news", payload="data")
        broker.publish(msg)
        consumed = broker.consume("agent-1")
        self.assertIsNotNone(consumed)
        self.assertEqual(consumed.payload, "data")

    def test_queue_size(self):
        broker = MessageBroker()
        broker.create_channel("news")
        broker.subscribe("news", "agent-1")
        broker.publish(Message(channel_id="news"))
        broker.publish(Message(channel_id="news"))
        self.assertEqual(broker.queue_size("agent-1"), 2)

    def test_handler_invoked(self):
        broker = MessageBroker()
        broker.create_channel("events")
        received = []
        broker.register_handler("events", received.append)
        msg = Message(channel_id="events", payload="x")
        broker.publish(msg)
        self.assertEqual(len(received), 1)

    def test_unsubscribe(self):
        broker = MessageBroker()
        broker.create_channel("news")
        broker.subscribe("news", "agent-1")
        self.assertTrue(broker.unsubscribe("news", "agent-1"))
        msg = Message(channel_id="news")
        self.assertEqual(broker.publish(msg), 0)

    def test_publish_to_nonexistent_channel(self):
        broker = MessageBroker()
        msg = Message(channel_id="ghost")
        self.assertEqual(broker.publish(msg), 0)


if __name__ == "__main__":
    unittest.main()
