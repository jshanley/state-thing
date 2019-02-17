from abc import ABC, abstractmethod
import asyncio
import re
import time

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint
import uvicorn

from machine import Machine, StateHandler, update

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

@m.state_handler('initial')
class InitialStateHandler(StateHandler):
    def reduce(self, context, action):
        if action['type'] == 'START':
            return {
                'start_time': int(time.time())
            }
        else:
            return context

@m.state_handler('name_input')
class NameInputStateHandler(StateHandler):
    def reduce(self, context, action):
        if action['type'] == 'NAME':
            return update(context, {
                'name': action.get('name')
            })
        else:
            return context

@m.state_handler('phone_number_input')
class PhoneNumberInputStateHandler(StateHandler):
    def reduce(self, context, action):
        if action['type'] == 'PHONE_NUMBER':
            return update(context, {
                'phone_number': action.get('phone_number')
            })
        else:
            return context


@m.state_handler('validate_name')
class ValidateNameStateHandler(StateHandler):
    async def process(self, context, send):
        # super-awesome validation
        if context.get('name') in ['John', 'Gus']:
            await send({'type': 'VALID'})
        else:
            await send({'type': 'INVALID'})

    def reduce(self, context, action):
        action_type = action['type']
        if action_type == 'VALID':
            return update(context, {
                'is_name_valid': True
            })
        elif action_type == 'INVALID':
            return update(context, {
                'is_name_valid': False
            })
        else:
            return context


@m.state_handler('validate_phone_number')
class ValidatePhoneNumberStateHandler(StateHandler):
    async def process(self, context, send):
        phone_number = context.get('phone_number')
        if re.search(r'[0-9]{3}-[0-9]{4}', phone_number):
            await send({'type': 'VALID'})
        else:
            await send({'type': 'INVALID'})

    def reduce(self, context, action):
        action_type = action['type']
        if action_type == 'VALID':
            return update(context, {'is_phone_number_valid': True})
        elif action_type == 'INVALID':
            return update(context, {'is_phone_number_valid': False})
        else:
            return context

@m.state_handler('save_record')
class SaveRecordHandler(StateHandler):
    async def process(self, context, send):
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

