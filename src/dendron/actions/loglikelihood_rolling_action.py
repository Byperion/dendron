from dendron.action_node import ActionNode
from dendron.basic_types import NodeStatus
from dendron.configs.hflm_action_config import HFLMActionConfig
from dendron.behavior_tree import BehaviorTree

from typing import Callable

import types
from hflm.huggingface_model import HFLM
import traceback

class LogLikelihoodRollingAction(ActionNode):
    """
    An action node that uses a causal language model to calculate the log-likelihood
    of a given a prompt in the blackboard.

    This node is based on the HFLM library, and will
    download the model that you specify by name. This can take a long 
    time and/or use a lot of storage, depending on the model you name.

    There are enough configuration options for this type of node that
    the options have all been placed in a dataclass config object. See 
    the documentation for that object to learn about the many options
    available to you.

    Args:
        name (str):
            The given name of this node.
        cfg (CausalLMActionConfig):
            The configuration object for this model.
    """
    def __init__(self, name : str, cfg : HFLMActionConfig) -> None:
        super().__init__(name)

        self.input_key = cfg.input_key
        self.output_key = cfg.output_key
        self.device = cfg.device
        self.max_new_tokens = cfg.max_new_tokens
        self.torch_dtype = cfg.dtype
        self.temperature = cfg.temperature

        if self.temperature == 0.0: 
            self.do_sample = False
        else:
            self.do_sample = True

        self.input_processor = None
        self.output_processor = None
        self.config = cfg

    def set_model(self, new_model) -> None:
        """
        TODO: I'm not sure what type new_model should be
              if it is supposed to be an HFLM model, then we need to adjust this
        """
        self.model = new_model

    def set_input_processor(self, f : Callable) -> None:
        """
        Set the input processor to use during `tick()`s. 

        An input processor is applied to the prompt text stored in the 
        blackboard, and can be used to preprocess the prompt. The 
        processor function should be a map from `str` to `str`. During a 
        `tick()`, the output of this function will be what is tokenized 
        and sent to the model for generation.

        Args:
            f (Callable):
                The input processor function to use. Should be a callable
                object that maps (self, Any) to str.
        """
        self.input_processor = types.MethodType(f, self)

    def set_output_processor(self, f : Callable) -> None:
        """
        Set the output processor to use during `tick()`s.

        An output processor is applied to the text generated by the model,
        before that text is written to the output slot of the blackboard.
        The function should be a map from `str` to `str`.

        A typical example of an output processor would be a function that
        removes the prompt from the text returned by a model, so that only
        the newly generated text is written to the blackboard.

        Args:
            f (Callable):
                The output processor function. Should be a callable object
                that maps from (self, str) to Any.
        """
        self.output_processor = types.MethodType(f, self)

    def tick(self) -> NodeStatus:
        """
        Execute a tick, consisting of the following steps:

        - Retrieve a prompt from the node's blackboard, using the input_key.
        - Apply the input processor, if one exists.
        - Tokenize the prompt text.
        - Generate new tokens based on the prompt.
        - Decode the model output into a text string.
        - Apply the output processor, if one exists,
        - Write the result back to the blackboard, using the output_key.

        If any of the above fail, the exception text is printed and the node
        returns a status of `FAILURE`. Otherwise the node returns `SUCCESS`. If
        you want to use a language model to make decisions, consider looking at
        the `CompletionConditionNode`.
        """
        try:
            input_text = self.blackboard[self.input_key]

            if self.input_processor:
                input_text = self.input_processor(input_text)
            
            output_probs = self.tree.get_model(self.config.model).loglikelihood_rolling([input_text], disable_tqdm=True)[0]

            if self.output_processor:
                output_probs = self.output_processor(output_probs)

            self.blackboard[self.output_key] = output_probs

            return NodeStatus.SUCCESS
        except Exception as ex:
            print(f"Exception in node {self.name}:")
            print(traceback.format_exc())

            return NodeStatus.FAILURE

    def set_tree(self, tree : BehaviorTree) -> None:
        """
        Set the behavior tree for this node, which includes setting up the blackboard
        and registering the model configuration with the tree.

        Args:
            tree (BehaviorTree):
                The behavior tree this node belongs to.
        """
        self.tree = tree
        self.set_blackboard(tree.blackboard)
        tree.add_model(self.config)