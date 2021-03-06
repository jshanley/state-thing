import asyncio
import copy
import logging


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class Machine:
    def __init__(self, mapping):
        self.mapping = mapping
        self.state_handlers = {}

    def add_state_handler(self, fn, state_name):
        self.state_handlers[state_name] = fn

    def state_handler(self, state_name):
        def decorator(cls):
            self.add_state_handler(cls, state_name)
        return decorator

    def next_state(self, current_state, action_type):
        if not current_state in self.mapping:
            return None
        
        # Final states are explicitly NoneType by convention
        if self.mapping[current_state] is None:
            return None
        
        try:
            return self.mapping[current_state][action_type]
        except KeyError:
            try:
                return self.mapping['*'][action_type]
            except KeyError:
                return None

    def realize(self, *, initial_state='initial', initial_context=None):
        return MachineInstance(
            self,
            initial_state=initial_state,
            initial_context=initial_context,
        )


class MachineInstance:
    def __init__(self, machine, *, initial_state='initial', initial_context=None):
        print('MachineInstance.__init__')
        self.machine = machine
        self._context = copy.deepcopy(initial_context)
        self.current_state = initial_state
        self.listeners = []

    @property
    def context(self):
        return copy.deepcopy(self._context)

    @context.setter
    def context(self, value):
        self._context = value


    def get_state(self):
        return {
            'state': self.current_state,
            'context': self.context,
        }

    def _get_handler_instance(self, state_name):
        try:
            handler = self.machine.state_handlers[state_name]
        except KeyError:
            return None
        else:
            return handler()

    async def invoke(self, action):
        print('MachineInstance.invoke')

        try:
            action_type = action['type']
        except KeyError:
            raise ValueError('Action must have a "type" field')
        if not action_type:
            raise ValueError('Action "type" field must not be empty')

        print('action_type', action_type)

        next_state = self.machine.next_state(self.current_state, action_type)
        
        if next_state is None:
            return

        current_state_handler = self._get_handler_instance(self.current_state)
        next_state_handler = self._get_handler_instance(next_state)

        print('next_state', next_state)

        # update context
        if current_state_handler is not None:
            self.context = current_state_handler.reduce(self.context, action)

        print('context updated')
        
        # transition states
        self.current_state = next_state

        print('self.current_state', self.current_state)

        # notify listeners
        await self._emit(self.get_state())

        # process new state
        if next_state_handler is not None:
            await next_state_handler.process(self.context, self.invoke)

    async def _emit(self, event):
        for listener in self.listeners:
            if asyncio.iscoroutinefunction(listener):
                await listener(event)
            else:
                listener(event)

    def add_listener(self, fn):
        self.listeners.append(fn)
    
    def listener(self, fn):
        self.add_listener(fn)
        return fn

class StateHandler(object):
    async def process(self, context, send):
        pass
    
    def reduce(self, context, action):
        return context


def update(context, partial_update):
    """
    Helper function for applying partial updates to a context
    """
    try:
        context.update(partial_update)
    except AttributeError:
        return partial_update
    else:
        return context


