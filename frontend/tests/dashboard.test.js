// tests/dashboard.test.js

import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DashboardPage from '@/app/dashboard/page';
import * as projectsHook from '@/hooks/useProjects';
import * as projectContext from '@/context/ProjectContext';

jest.mock('@/hooks/useProjects');
jest.mock('@/context/ProjectContext');
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

const mockAnalytics = {
  total_requests: 18234,
  requests_change: 0.12,
  active_agents: 6,
  agents_change: 0.02,
  documents_indexed: 982,
  documents_change: 0.05,
  total_cost: 142.32,
  cost_change: -0.08,
  usage_series: [
    { date: '2026-06-10', value: 1200 },
    { date: '2026-06-11', value: 1450 },
  ],
  cost_by_model: [{ name: 'gpt-4o', value: 80.5 }],
  recent_activity: [
    {
      id: 'evt_1',
      type: 'agent_run',
      description: 'Research Assistant completed a run',
      actor: 'Jane Doe',
      created_at: '2026-06-17T05:00:00Z',
    },
  ],
  avg_latency_ms: 420,
  p95_latency_ms: 980,
  retrieval_hit_rate: 0.91,
  cache_hit_rate: 0.67,
};

describe('DashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    projectContext.useProjectContext.mockReturnValue({
      activeProject: { id: 'proj_1', name: 'Customer Support Assistant' },
      activeProjectId: 'proj_1',
      isLoading: false,
    });

    projectsHook.useProjectAnalytics.mockReturnValue({
      analytics: mockAnalytics,
      isLoading: false,
    });
  });

  it('renders the active project name as the page title', () => {
    render(<DashboardPage />);
    expect(screen.getByText('Customer Support Assistant')).toBeInTheDocument();
  });

  it('renders stat cards with formatted values', async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Total requests')).toBeInTheDocument();
      expect(screen.getByText('Active agents')).toBeInTheDocument();
      expect(screen.getByText('Documents indexed')).toBeInTheDocument();
      expect(screen.getByText('Estimated cost')).toBeInTheDocument();
    });
  });

  it('shows a loading state while analytics are loading', () => {
    projectsHook.useProjectAnalytics.mockReturnValue({
      analytics: null,
      isLoading: true,
    });

    render(<DashboardPage />);
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  it('renders recent activity items', () => {
    render(<DashboardPage />);
    expect(screen.getByText(/Research Assistant completed a run/i)).toBeInTheDocument();
  });

  it('falls back to a generic title when no active project is set', () => {
    projectContext.useProjectContext.mockReturnValue({
      activeProject: null,
      activeProjectId: null,
      isLoading: false,
    });

    render(<DashboardPage />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});
