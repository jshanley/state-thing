import asyncio
import copy
import logging


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class Machine:
    def __init__(self, mapping):
        self.mapping = mapping
        self.reducers = {}
        self.processors = {}
        self.handlers = {}

    def add_reducer(self, fn, state_name, action_type):
        self.reducers[(state_name, action_type)] = fn

    def reducer(self, state_name, action_type):
        def decorator(fn):
            self.add_reducer(fn, state_name, action_type)
        return decorator

    def add_processor(self, fn, state_name):
        self.processors[state_name] = fn

    def processor(self, state_name):
        def decorator(fn):
            self.add_processor(fn, state_name)
        return decorator

    def add_handler(self, fn, state_name):
        self.handlers[state_name] = fn

    def handler(self, state_name):
        def decorator(cls):
            self.add_handler(cls, state_name)
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

        print('next_state', next_state)

        # update context
        try:
            reducer = self.machine.reducers[(self.current_state, action_type)]
        except KeyError:
            print(f'key not found: self.machine.reducers[({self.current_state}, {action_type})]')
            try:
                handler = self.machine.handlers[self.current_state]
            except KeyError:
                pass
            else:
                self.context = handler.reduce(self.context, action)
        else:
            self.context = reducer(self.context, action)

        print('context updated')
        
        # transition states
        self.current_state = next_state

        print('self.current_state', self.current_state)

        # notify listeners
        await self._emit(self.get_state())

        # process new state
        try:
            processor = self.machine.processors[self.current_state]
        except KeyError:
            try:
                processor = self.machine.handlers[self.current_state].process
            except (KeyError, AttributeError):
                pass
            else:
                await processor(self.context, self.invoke)
        else:
            await processor(self.context, self.invoke)

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


