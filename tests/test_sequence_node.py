from dendron.actions import AlwaysSuccessNode
from dendron.controls import SequenceNode
from dendron.basic_types import NodeStatus

def test_successful_sequence():
    n1 = AlwaysSuccessNode("Success1")
    n2 = AlwaysSuccessNode("Success2")

    seq = SequenceNode("Sequence")

    seq.add_child(n1)
    seq.add_child(n2)

    result = seq.execute_tick()

    assert result == NodeStatus.SUCCESS