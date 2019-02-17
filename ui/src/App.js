import React, { Component } from 'react';

import WebSocketTest from './components/websocket-test';
import './App.css';

class App extends Component {
  render() {
    return (
      <div className="App">
        <WebSocketTest />
      </div>
    );
  }
}

export default App;
