import React from 'react';

const TugOfWar = () => {
  return (
    <div>
      <h2>줄다리기</h2>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>ChatGPT</span>
        <div style={{ border: '1px solid black', width: '200px', height: '20px' }}>
          <div style={{ width: '50%', height: '100%', backgroundColor: 'lightblue' }}></div>
        </div>
        <span>Gemini</span>
      </div>
    </div>
  );
};

export default TugOfWar;
