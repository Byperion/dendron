from .basic_types import NodeType, NodeStatus
from .tree_node import TreeNode
from .blackboard import Blackboard

import typing
from typing import List, Optional

import logging

BehaviorTree = typing.NewType("BehaviorTree", None)

class ControlNode(TreeNode):

    _used_names = set(["control"])

    """
    Base class for a control node.

    A control node maintains a list of children that it ticks under
    some conditions. The node tracks the state of its children as 
    they tick, and decides whether or not to continue based on its 
    internal logic.

    Args:
        name (`str`):
            The given name of this control node.
        children (`List[TreeNode]`):
            An optional initial list of children.
    """

    def __init__(self, children : List[TreeNode] = None, name : str = "control") -> None:
        super().__init__()
        self.children : List[TreeNode] = children if children is not None else []
        self._name = None
        self.name = name

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if self._name is not None:
            ControlNode._used_names.remove(self._name)

        if value in ControlNode._used_names:
            suffix = 0
            new_name = f"{value}_{suffix}"
            while new_name in ControlNode._used_names:
                suffix += 1
                new_name = f"{value}_{suffix}"
            value = new_name
        
        ControlNode._used_names.add(value)
        self._name = value

    def set_tree(self, tree : BehaviorTree) -> None:
        """
        Set the tree of this node, and then have each of the children
        set their tree similarly.

        Args:
            tree (`dendron.behavior_tree.BehaviorTree`):
                The tree that will contain this node.
        """
        self.tree = tree
        for c in self.children:
            c.set_tree(tree)

    def children(self) -> List[TreeNode]:
        return self.children

    def set_logger(self, new_logger) -> None:
        """
        Set the logger for this node, and then forward the logger to the
        children.

        Args:
            new_logger (`logging.Logger`):
                The Logger to use.
        """
        self.logger = new_logger
        for c in self.children:
            c.set_logger(new_logger)

    def set_log_level(self, new_level) -> None:
        """
        Set the log level for this node, then forward that level for the
        children to use.
        """
        self.log_level = new_level
        for c in self.children:
            c.set_log_level(new_level)

    def add_child(self, child : TreeNode) -> None:
        """
        Add a new child node to the end of the list.

        Args:
            child (`dendron.tree_node.TreeNode`):
                The new child node.
        """
        self.children.append(child)

    def add_children(self, children : List[TreeNode]) -> None:
        """
        Add a list of children to the end of the list.

        Args:
            children (`List[TreeNode]`):
                The list of `TreeNode`s to add. 
        """
        self.children.extend(children)

    def set_blackboard(self, bb : Blackboard) -> None:
        """
        Set the blackboard for this node, and then forward to the
        children.

        Args:
            bb (`dendron.blackboard.Blackboard`):
                The new blackboard to use.
        """
        self.blackboard = bb
        for child in self.children:
            child.set_blackboard(bb)

    def get_node_by_name(self, name : str) -> Optional[TreeNode]:
        """
        Search for a node by its name.

        Args:
            name (`str`):
                The name of the node we are looking for.

        Returns:
            `Optional[TreeNode]`: Either a node with the given name,
            or None.
        """
        if self.name == name:
            return self
        else:
            for child in self.children:
                node = child.get_node_by_name(name)
                if node != None:
                    return node
            return None

    def children_count(self) -> int:
        """
        Get the current number of children.

        Returns:
            `int`: The length of the children list.
        """
        return len(self.children)

    def children(self) -> List[TreeNode]:
        """
        Get the list of children.

        Returns:
            `List[TreeNode]`: The `self.children` list.
        """
        return self.children

    def child(self, index : int) -> TreeNode:
        """
        Get the child that is at position `index` in the list. Does
        not perform bounds checking.

        Args:
            index (`int`):
                The index of the child we want.

        Returns:
            `TreeNode`: The child at the desired index.
        """
        return self.children[index]

    def node_type(self) -> NodeType:
        """
        Return this node's `NodeType`.

        Returns:
            `NodeType`: The type (`CONTROL`).
        """
        return NodeType.CONTROL

    def halt_node(self) -> None:
        """
        Reset the children and then reset this node.
        """
        self.reset_children()
        self.reset_status()

    def reset(self) -> None:
        """
        Instruct each child to reset.
        """
        for child in self.children:
            child.reset()


class ParallelNode(ControlNode):
    """
    A Parallel node is a control node that ticks all its children concurrently.
    
    The node's policy parameter determines how the node reports its status:
    - 'success_on_all': Only succeeds when all children succeed, fails if any child fails
    - 'success_on_one': Succeeds when at least one child succeeds, fails if all children fail
    - 'success_on_all_or_one_failure': Succeeds only when all children succeed,
                                       fails if any child fails
    
    Example:
        # Create the AsyncAction nodes
        async_node_1 = AsyncAction("AsyncTask1", async_task_1)
        async_node_2 = AsyncAction("AsyncTask2", async_task_2)

        # Create a Parallel node with the AsyncAction nodes as children
        # Using "success_on_all" policy (tree succeeds only if both tasks succeed)
        parallel_node = Parallel([async_node_1, async_node_2], name="ParallelTasks", policy="success_on_all")

        # Create the behavior tree with the Parallel node as the root
        tree = BehaviorTree("AsyncConcurrentExample", parallel_node)
    
    Args:
        children (`List[TreeNode]`):
            The list of children to execute in parallel.
        name (`str`):
            The name of this node.
        policy (`str`):
            The policy to use for determining success/failure.
    """
    
    def __init__(self, 
                children: List[TreeNode] = [], 
                name: str = "parallel",
                policy: str = "success_on_all") -> None:
        super().__init__(children, name)
        
        self.policy = policy
        # Dictionary to track child nodes that are running
        self.running_children = {}
        # Dictionary to store the status of completed child nodes
        self.completed_children = {}
        
    def reset(self) -> None:
        """
        Reset this node and all its children.
        """
        self.running_children = {}
        self.completed_children = {}
        super().reset()
        
    def tick(self) -> NodeStatus:
        """
        Tick all children and update their statuses.
        
        The return status depends on the node's policy and the current status
        of all children.
        
        Returns:
            `NodeStatus`: The status of this node based on its children's statuses.
        """
        n_children = self.children_count()
        self.set_status(NodeStatus.RUNNING)
        
        # First pass: Tick all children that are not completed
        for i, child in enumerate(self.children):
            if i not in self.completed_children:
                if i not in self.running_children:
                    self.running_children[i] = True
                
                # Execute the child
                child_status = child.execute_tick()
                
                # If the child is done, move it to completed
                if child_status != NodeStatus.RUNNING:
                    self.completed_children[i] = child_status
                    self.running_children.pop(i, None)
        
        # Count success and failure children
        success_count = sum(1 for status in self.completed_children.values() 
                           if status == NodeStatus.SUCCESS)
        failure_count = sum(1 for status in self.completed_children.values() 
                           if status == NodeStatus.FAILURE)
        completed_count = len(self.completed_children)
        
        # Apply the policy
        if self.policy == "success_on_all":
            # Return SUCCESS only if all children succeeded
            if completed_count == n_children:
                if success_count == n_children:
                    self.reset()
                    return NodeStatus.SUCCESS
                else:
                    self.reset()
                    return NodeStatus.FAILURE
        elif self.policy == "success_on_one":
            # Return SUCCESS if at least one child succeeded
            if success_count > 0:
                self.reset()
                return NodeStatus.SUCCESS
            # Return FAILURE if all children failed
            elif completed_count == n_children:
                self.reset()
                return NodeStatus.FAILURE
        elif self.policy == "success_on_all_or_one_failure":
            # Return FAILURE as soon as a child fails
            if failure_count > 0:
                self.reset()
                return NodeStatus.FAILURE
            # Return SUCCESS if all children succeeded
            elif completed_count == n_children:
                self.reset()
                return NodeStatus.SUCCESS
        
        # If we get here, some children are still running
        return NodeStatus.RUNNING
    
