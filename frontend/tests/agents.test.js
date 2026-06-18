// tests/agents.test.js

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import AgentsPage from '@/app/agents/page';
import { AgentRunner } from '@/components/agents/AgentRunner';
import * as agentsHook from '@/hooks/useAgents';
import * as projectContext from '@/context/ProjectContext';
import * as agentContext from '@/context/AgentContext';

jest.mock('@/hooks/useAgents');
jest.mock('@/context/ProjectContext');
jest.mock('@/context/SettingsContext', () => ({
  useSettingsContext: () => ({
    theme: 'dark',
    setTheme: jest.fn(),
    sidebarCollapsed: false,
    toggleSidebar: jest.fn(),
    mounted: true,
  }),
}));
jest.mock('@/context/AgentContext');
jest.mock('@/services/agents');
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => '/agents',
}));
jest.mock('@/context/AuthContext', () => ({
  useAuthContext: () => ({
    user: { id: 'user_1', name: 'Test User', email: 'test@example.com', role: 'admin' },
    isAuthenticated: true,
    isLoading: false,
    error: null,
    signIn: jest.fn(),
    signOut: jest.fn(),
    updateUser: jest.fn(),
    refresh: jest.fn(),
  }),
}));

const mockAgents = [
  {
    id: 'agent_1',
    name: 'Research Assistant',
    type: 'research',
    status: 'idle',
    description: 'Performs multi-step web research',
    updated_at: '2026-06-16T10:00:00Z',
  },
  {
    id: 'agent_2',
    name: 'SQL Analyst',
    type: 'coding',
    status: 'running',
    description: 'Writes and validates SQL queries',
    updated_at: '2026-06-17T03:30:00Z',
  },
];

describe('AgentsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    projectContext.useProjectContext.mockReturnValue({
      projects: [],
      activeProjectId: 'proj_1',
      activeProject: { id: 'proj_1', name: 'Test Project' },
      setActiveProject: jest.fn(),
      isLoading: false,
    });
    agentsHook.useAgents.mockReturnValue({
      agents: mockAgents,
      isLoading: false,
      refresh: jest.fn(),
    });
  });

  it('renders a list of agent cards', () => {
    render(<AgentsPage />);
    expect(screen.getByText('Research Assistant')).toBeInTheDocument();
    expect(screen.getByText('SQL Analyst')).toBeInTheDocument();
  });

  it('shows an empty state when there are no agents', () => {
    agentsHook.useAgents.mockReturnValue({ agents: [], isLoading: false, refresh: jest.fn() });
    render(<AgentsPage />);
    expect(screen.getByText(/no agents yet/i)).toBeInTheDocument();
  });

  it('filters agents by search input', async () => {
    render(<AgentsPage />);
    const searchInput = screen.getByPlaceholderText(/search agents/i);
    await userEvent.type(searchInput, 'SQL');
    expect(agentsHook.useAgents).toHaveBeenCalled();
  });

  it('shows loading skeletons while agents are loading', () => {
    agentsHook.useAgents.mockReturnValue({ agents: [], isLoading: true, refresh: jest.fn() });
    render(<AgentsPage />);
    expect(screen.getAllByTestId('skeleton-card').length).toBeGreaterThan(0);
  });
});

describe('AgentRunner', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders an empty state when there is no active run', () => {
    agentContext.useAgentContext.mockReturnValue({
      startRun: jest.fn(),
      stopRun: jest.fn(),
      getRun: () => null,
    });

    render(<AgentRunner agentId="agent_1" />);
    expect(screen.getByText(/no active run/i)).toBeInTheDocument();
  });

  it('disables the run button when input is empty', () => {
    agentContext.useAgentContext.mockReturnValue({
      startRun: jest.fn(),
      stopRun: jest.fn(),
      getRun: () => null,
    });

    render(<AgentRunner agentId="agent_1" />);
    expect(screen.getByRole('button', { name: /run agent/i })).toBeDisabled();
  });

  it('calls startRun with the provided input when submitted', async () => {
    const startRun = jest.fn().mockResolvedValue('run_123');
    agentContext.useAgentContext.mockReturnValue({
      startRun,
      stopRun: jest.fn(),
      getRun: () => null,
    });

    render(<AgentRunner agentId="agent_1" />);
    const textarea = screen.getByPlaceholderText(/describe the task/i);
    await userEvent.type(textarea, 'Summarize the latest quarterly report');
    await userEvent.click(screen.getByRole('button', { name: /run agent/i }));

    await waitFor(() => {
      expect(startRun).toHaveBeenCalledWith('agent_1', {
        input: 'Summarize the latest quarterly report',
      });
    });
  });

  it('renders execution timeline steps when a run is active', async () => {
    const startRun = jest.fn().mockResolvedValue('run_123');
    agentContext.useAgentContext.mockReturnValue({
      startRun,
      stopRun: jest.fn(),
      getRun: (runId) =>
        runId === 'run_123'
          ? {
              status: 'running',
              output: 'Partial output so far...',
              steps: [
                {
                  id: 'step_1',
                  title: 'Planning',
                  state: 'complete',
                  detail: 'Created plan',
                  duration_ms: 320,
                },
                { id: 'step_2', title: 'Retrieving context', state: 'running', detail: null },
              ],
            }
          : null,
    });

    render(<AgentRunner agentId="agent_1" />);
    const textarea = screen.getByPlaceholderText(/describe the task/i);
    await userEvent.type(textarea, 'Summarize the latest quarterly report');
    await userEvent.click(screen.getByRole('button', { name: /run agent/i }));

    await waitFor(() => {
      expect(screen.getByText('Planning')).toBeInTheDocument();
    });
    expect(screen.getByText('Retrieving context')).toBeInTheDocument();
    expect(screen.getByText(/partial output so far/i)).toBeInTheDocument();
  });
});
