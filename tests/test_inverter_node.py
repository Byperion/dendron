from dendron.decorators import InverterNode
from dendron.actions import AlwaysSuccessNode, AlwaysFailureNode
from dendron.basic_types import NodeStatus

def test_failure_inversion():
    n1 = AlwaysSuccessNode("SuccessNode")

    inverter = InverterNode("Inverter", n1)

    result = inverter.execute_tick()

    assert result == NodeStatus.FAILURE

def test_success_inversion():

    n1 = AlwaysFailureNode("FailureNode")

    inverter = InverterNode("Inverter", n1)

    result = inverter.execute_tick()

    assert result == NodeStatus.SUCCESS