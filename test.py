from abc import ABC, abstractmethod
import asyncio
import re
import time

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint
import uvicorn

from machine import Machine

m = Machine({
    '*': {
        'ERROR': 'fail'
    },
    'initial': {
        'START': 'name_input',
    },
    'name_input': {
        'NAME': 'validate_name',
    },
    'validate_name': {
        'VALID': 'phone_number_input',
        'INVALID': 'name_input',
    },
    'phone_number_input': {
        'PHONE_NUMBER': 'validate_phone_number',
    },
    'validate_phone_number': {
        'VALID': 'save_record',
        'INVALID': 'phone_number_input'
    },
    'save_record': {
        'SUCCESS': 'show_results',
    },
    'show_results': {
        'NEXT': 'initial',
        'DONE': 'end',
    },
    'end': None,
    'fail': None,
})


def update(thing, partial_update):
    try:
        thing.update(partial_update)
    except AttributeError:
        return partial_update
    else:
        return thing
    


@m.reducer('initial', 'START')
def start(context, action):
    return {
        'start_time': int(time.time())
    }

@m.reducer('name_input', 'NAME')
def name(context, action):
    return update(context, {
        'name': action.get('name')
    })

@m.reducer('phone_number_input', 'PHONE_NUMBER')
def phone_number(context, action):
    return update(context, {
        'phone_number': action.get('phone_number')
    })

@m.reducer('validate_name', 'VALID')
def name_valid(context, action):
    return update(context, {
        'is_name_valid': True
    })

@m.reducer('validate_name', 'INVALID')
def name_invalid(context, action):
    return update(context, {
        'is_name_valid': False
    })

@m.processor('validate_name')
async def validate_name(context, send):
    print('processing validate_name', context)
    # super-awesome validation
    if context.get('name') in ['John', 'Gus']:
        await send({'type': 'VALID'})
    else:
        await send({'type': 'INVALID'})


class Handler(ABC):
    @staticmethod
    @abstractmethod
    async def process(context, send):
        pass
    
    @staticmethod
    @abstractmethod
    def reduce(context, action):
        return context

@m.handler('validate_phone_number')
class ValidatePhoneNumberHandler(Handler):
    @staticmethod
    async def process(context, send):
        phone_number = context.get('phone_number')
        if re.search(r'[0-9]{3}-[0-9]{4}', phone_number):
            await send({'type': 'VALID'})
        else:
            await send({'type': 'INVALID'})
    @staticmethod
    def reduce(context, action):
        action_type = action['type']
        if action_type == 'VALID':
            return update(context, {'is_phone_number_valid': True})
        elif action_type == 'INVALID':
            return update(context, {'is_phone_number_valid': False})

@m.handler('save_record')
class SaveRecordHandler(Handler):
    @staticmethod
    async def process(context, send):
        print('pretending to save the record to a database or something...')
        await asyncio.sleep(2)
        print('fake record saved')
        await send({'type': 'SUCCESS'})


#-- WebSocket Server -----------------------------
#-------------------------------------------------
app = Starlette()

@app.websocket_route('/test')
class TestEndpoint(WebSocketEndpoint):

    encoding = 'json'

    async def on_connect(self, websocket):
        await websocket.accept()
        
        self._machine = m.realize()

        async def on_state_change(event):
            await websocket.send_json(event)

        self._machine.add_listener(on_state_change)
        await websocket.send_json({
            'state': self._machine.current_state,
            'context': self._machine.context
        })
    
    async def on_receive(self, websocket, data):
        await self._machine.invoke(data)
    
    async def on_disconnect(self, websocket, close_code):
        await self._machine.invoke({
            'type': 'ERROR',
            'error': 'Websocket disconnected',
        })


def main():
    uvicorn.run(app, host='0.0.0.0', port=4444)

if __name__ == '__main__':
    main()

