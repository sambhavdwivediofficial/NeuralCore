// tests/retrieval.test.js

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import RetrievalDebuggerPage from '@/app/retrieval-debugger/page';
import { SearchResults } from '@/components/retrieval/SearchResults';
import { ScoreCard } from '@/components/retrieval/ScoreCard';
import * as kbHook from '@/hooks/useKnowledgeBases';
import * as projectContext from '@/context/ProjectContext';
import * as retrievalHook from '@/hooks/useRetrieval';

jest.mock('@/hooks/useKnowledgeBases');
jest.mock('@/context/ProjectContext');
jest.mock('@/hooks/useRetrieval');
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

const mockKnowledgeBases = [
  { id: 'kb_1', name: 'Product Documentation' },
  { id: 'kb_2', name: 'Support Tickets' },
];

const mockResults = [
  {
    chunk_id: 'chunk_1',
    document_name: 'pricing.md',
    content: 'NeuralCore offers tiered pricing based on monthly query volume.',
    score: 0.92,
  },
  {
    chunk_id: 'chunk_2',
    document_name: 'faq.md',
    content: 'You can upgrade or downgrade your plan at any time.',
    score: 0.81,
  },
];

describe('RetrievalDebuggerPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    projectContext.useProjectContext.mockReturnValue({ activeProjectId: 'proj_1' });
    kbHook.useKnowledgeBases.mockReturnValue({ knowledgeBases: mockKnowledgeBases });
    retrievalHook.useRetrievalQuery.mockReturnValue({
      result: null,
      isLoading: false,
      runQuery: jest.fn().mockResolvedValue({ results: mockResults, latency_ms: 145 }),
    });
  });

  it('renders quick links to chunk inspector, metrics, and reranking', () => {
    render(<RetrievalDebuggerPage />);
    expect(screen.getByText('Chunk inspector')).toBeInTheDocument();
    expect(screen.getByText('Metrics')).toBeInTheDocument();
    expect(screen.getByText('Reranking')).toBeInTheDocument();
  });

  it('disables run query button until a knowledge base and query are provided', () => {
    render(<RetrievalDebuggerPage />);
    expect(screen.getByRole('button', { name: /run query/i })).toBeDisabled();
  });

  it('enables the run query button once query and knowledge base are set', async () => {
    render(<RetrievalDebuggerPage />);
    await userEvent.type(
      screen.getByPlaceholderText(/enter a query to test retrieval/i),
      'How does pricing work?'
    );

    const kbTrigger = screen.getByText(/select knowledge base/i);
    await userEvent.click(kbTrigger);
    await userEvent.click(await screen.findByText('Product Documentation'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /run query/i })).not.toBeDisabled();
    });
  });

  it('shows an empty state in SearchResults when no results have been returned yet', () => {
    render(<RetrievalDebuggerPage />);
    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });
});

describe('SearchResults', () => {
  it('renders an empty state when results are empty', () => {
    render(<SearchResults results={[]} isLoading={false} />);
    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });

  it('renders a result card for each retrieved chunk', () => {
    render(<SearchResults results={mockResults} isLoading={false} />);
    expect(
      screen.getByText(/tiered pricing based on monthly query volume/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/upgrade or downgrade your plan/i)).toBeInTheDocument();
  });

  it('shows a skeleton loader while loading', () => {
    render(<SearchResults results={null} isLoading />);
    expect(screen.getByTestId('skeleton-text')).toBeInTheDocument();
  });
});

describe('ScoreCard', () => {
  it('renders the formatted score value', () => {
    render(<ScoreCard rank={1} score={0.8765} />);
    expect(screen.getByText('0.8765')).toBeInTheDocument();
  });

  it('renders the provided rank', () => {
    render(<ScoreCard rank={3} score={0.5} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});
