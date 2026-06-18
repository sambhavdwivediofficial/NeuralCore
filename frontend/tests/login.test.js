// tests/login.test.js

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import LoginPage from '@/app/login/page';
import * as authService from '@/services/auth';

jest.mock('@/services/auth');
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
jest.mock('@/context/AuthContext', () => {
  const authService = require('@/services/auth');
  return {
    useAuthContext: () => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      signIn: async (credentials) => authService.login(credentials),
      signOut: jest.fn(),
      updateUser: jest.fn(),
      refresh: jest.fn(),
    }),
  };
});
jest.mock('@/components/common/Toast', () => ({
  toast: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders email and password fields', () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('shows validation errors when submitting empty form', async () => {
    render(<LoginPage />);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/email is required|invalid email/i)).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid email format', async () => {
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('calls login service with correct credentials on submit', async () => {
    authService.login.mockResolvedValue({
      user: { id: '1', email: 'user@example.com', name: 'Test User' },
      token: 'fake-jwt-token',
    });

    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith({
        email: 'user@example.com',
        password: 'password123',
        remember: true,
      });
    });
  });

  it('displays an error message when login fails', async () => {
    const { toast } = require('@/components/common/Toast');
    authService.login.mockRejectedValue({
      response: { data: { message: 'Invalid email or password' } },
    });

    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Invalid email or password');
    });
  });

  it('disables the submit button while a login request is in flight', async () => {
    let resolveLogin;
    authService.login.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve;
        })
    );

    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await userEvent.click(submitButton);

    expect(submitButton).toBeDisabled();

    resolveLogin({ user: { id: '1' }, token: 'token' });

    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
    });
  });
});
