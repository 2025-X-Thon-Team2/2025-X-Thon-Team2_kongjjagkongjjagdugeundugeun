import React from 'react';
import InputForm from './components/InputForm';
import TugOfWar from './components/TugOfWar';
import LogDisplay from './components/LogDisplay';

function App() {
  return (
    <div>
      <h1>교차검증AI - Cross-Verification AI</h1>
      <InputForm />
      <TugOfWar />
      <LogDisplay />
    </div>
  );
}

export default App;
