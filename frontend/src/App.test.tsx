import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { AuthProvider } from './contexts/AuthContext';
import App from './App';

describe('App Infrastructure', () => {
  it('should render without crashing', () => {
    // Render App with AuthProvider
    const { container } = render(
      <AuthProvider>
        <App />
      </AuthProvider>
    );
    
    // App should render successfully
    expect(container).toBeTruthy();
  });
});
