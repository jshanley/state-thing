import React, { useEffect, useRef, useState } from 'react';


const WEBSOCKET_URL = process.env.REACT_APP_WEBSOCKET_URL;

const extractMessageText = (messageData) => new Promise((resolve, reject) => {
  if (typeof messageData === 'string') {
    resolve(messageData);
  } else if (messageData instanceof Blob) {
    const reader = new FileReader();
    reader.addEventListener('load', evt => resolve(evt.target.result));
    reader.addEventListener('error', evt => reject(evt.target.result));
    reader.readAsText(messageData);
  } else {
    reject()
  }
})

const connectToSocket = url => new Promise((resolve, reject) => {
  const socket = new WebSocket(url);
  socket.binaryType = 'blob';
  socket.addEventListener('open', () => {
    console.log('connection open')
    resolve(socket)
  })
  socket.addEventListener('error', (evt) => reject(evt))
})


function useWebSocketThing(url) {
  const [machineState, setMachineState] = useState({});
  const { state, context } = machineState;
  const [socket, setSocket] = useState(null);
  useEffect(() => {
    connectToSocket(url).then(sock => {
      setSocket(sock);
      const handleMessage = evt => {
        console.log('evt.data', evt.data)
        extractMessageText(evt.data)
          .then(text => JSON.parse(text))
          .then(data => setMachineState(data))
      }
      sock.addEventListener('message', handleMessage);
      return () => {
        sock.removeEventListener('message', handleMessage)
      }
    })
  }, [])

  // FIXME: this is probably not a good way to handle this...
  if (socket === null) {
    return [null, null, () => {}]
  }
  return [state, context, event => socket.send(JSON.stringify(event))]
  
}


function MainView({state, context, send}) {
  switch(state) {
    case null:
      return (
        <div>Connecting...</div>
      )
    case 'initial':
      return (
        <div>
          <button onClick={evt => send({type: 'START'})}>Start</button>
        </div>
      )
    case 'name_input':
      return (
        <NameInput
          context={context}
          onSubmit={name => send({type: 'NAME', name})}
        />
      )
    case 'phone_number_input':
      return (
        <PhoneNumberInput
          context={context}
          onSubmit={phone_number => send({type: 'PHONE_NUMBER', phone_number})}
        />
      )
    case 'save_record':
      return (
        <div>Saving record...</div>
      )
    case 'show_results':
      return (
        <div>
          <h3>Results</h3>
          <div>Name: {context.name}</div>
          <div>Phone No.: {context.phone_number}</div>
          <button onClick={evt => send({type: 'NEXT'})}>Next</button>
          <button onClick={evt => send({type: 'DONE'})}>Done</button>
        </div>
      )
    default:
      return <div>Catch-all for unhandled states</div>
  }
}

function DebugView({state, context, send}) {
  return <Status state={state} context={context} />
}

function WebSocketTest(props) {

  const [state, context, send] = useWebSocketThing(WEBSOCKET_URL)

  console.log(state)

  const childProps = {state, context, send};

  return (
    <div style={{
      height: '100vh',
      width: '100vw',
      padding: '1rem',
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between'
    }}>
      <MainView {...childProps} />
      <DebugView {...childProps} />
    </div>
  )
  
  
}

const useInputFocus = () =>  {
  const inputElement = useRef(null)
  useEffect(() => {
    inputElement.current.focus()
  }, [])
  return inputElement;
}

function NameInput(props) {
  const {context, onSubmit} = props;
  const [value, setValue] = useState('');

  const inputElement = useInputFocus()

  const handleSubmit = evt => {
    evt.preventDefault();
    onSubmit(value);
  }

  return (
    <form onSubmit={handleSubmit}>
      <input type="text"
        ref={inputElement}
        value={value}
        placeholder="Name"
        onChange={evt => setValue(evt.target.value)}
        style={{
          backgroundColor: context.is_name_valid === false ? 'red' : 'white'
        }}
      />
      {context.is_name_valid === false ? (
        <div style={{color: 'red'}}>Invalid name, try again.</div>
      ) : null}
      <button type="submit">Submit</button>
    </form>
    
  )
}

function PhoneNumberInput(props) {
  const {context, onSubmit} = props;
  const [value, setValue] = useState('');

  const inputElement = useInputFocus()

  const handleSubmit = evt => {
    evt.preventDefault();
    onSubmit(value);
  }

  return (
    <form onSubmit={handleSubmit}>
      <input type="tel"
        ref={inputElement}
        pattern="[0-9]{3}-[0-9]{4}"
        value={value}
        placeholder="Phone Number"
        onChange={evt => setValue(evt.target.value)}
        style={{
          backgroundColor: context.is_phone_number_valid === false ? 'red' : 'white'
        }}
      />
       {context.is_phone_number_valid === false ? (
        <div style={{color: 'red'}}>Invalid number, try again.</div>
      ) : null}
      <button type="submit">Submit</button>
    </form>
    
  )
}


function Status(props) {
  const { state, context } = props;

  return (
    <div>
      <div>State: {state}</div>
      <div>
        <span>Context: </span>
        <pre>
          <code>
            {JSON.stringify(context, null, 2)}
          </code>
        </pre>
      </div>
    </div>
  )
}

export default WebSocketTest;
