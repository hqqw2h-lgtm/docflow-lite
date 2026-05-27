import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import 'antd/dist/reset.css';
import App from './v2/App';

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
