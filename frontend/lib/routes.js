// frontend/lib/routes.js

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  LOGIN_MFA: '/login/mfa',
  SIGNUP: '/signup',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: (token) => `/reset-password/${token}`,
  VERIFY_EMAIL: '/verify-email',
  ACCEPT_INVITE: (token) => `/accept-invite/${token}`,
  AUTH_CALLBACK: '/auth/callback',
  ONBOARDING: '/onboarding',

  DASHBOARD: '/dashboard',

  PROJECTS: '/projects',
  PROJECT_CREATE: '/projects/create',
  PROJECT: (id) => `/projects/${id}`,
  PROJECT_ANALYTICS: (id) => `/projects/${id}/analytics`,
  PROJECT_SETTINGS: (id) => `/projects/${id}/settings`,

  AGENTS: '/agents',
  AGENT_CREATE: '/agents/create',
  AGENT: (id) => `/agents/${id}`,
  AGENT_DETAIL: (id) => `/agents/${id}`,
  AGENT_SETTINGS: (id) => `/agents/${id}/settings`,

  KNOWLEDGE_BASES: '/knowledge-bases',
  KNOWLEDGE_BASE_CREATE: '/knowledge-bases/create',
  KNOWLEDGE_BASE: (id) => `/knowledge-bases/${id}`,
  KNOWLEDGE_BASE_CHUNKS: (id) => `/knowledge-bases/${id}/chunks`,
  KNOWLEDGE_BASE_EMBEDDINGS: (id) => `/knowledge-bases/${id}/embeddings`,
  KNOWLEDGE_BASE_RETRIEVAL: (id) => `/knowledge-bases/${id}/retrieval`,

  CHAT: '/chat',

  RETRIEVAL_DEBUGGER: '/retrieval-debugger',
  RETRIEVAL_DEBUGGER_QUERY: '/retrieval-debugger/query',
  RETRIEVAL_DEBUGGER_CHUNKS: '/retrieval-debugger/chunks',
  RETRIEVAL_DEBUGGER_RERANKING: '/retrieval-debugger/reranking',
  RETRIEVAL_DEBUGGER_METRICS: '/retrieval-debugger/metrics',

  VECTOR_STORES: '/vector-stores',
  VECTOR_STORE_QDRANT: '/vector-stores/qdrant',
  VECTOR_STORE_MILVUS: '/vector-stores/milvus',
  VECTOR_STORE_PGVECTOR: '/vector-stores/pgvector',

  MONITORING: '/monitoring',
  MONITORING_LOGS: '/monitoring/logs',
  MONITORING_TRACES: '/monitoring/traces',
  MONITORING_ALERTS: '/monitoring/alerts',

  WORKFLOWS: '/workflows',
  WORKFLOW_CREATE: '/workflows/create',
  WORKFLOW: (id) => `/workflows/${id}`,

  PROMPTS: '/prompts',

  DATASETS: '/datasets',
  DATASET_CREATE: '/datasets/create',

  PLUGINS: '/plugins',

  ORGANIZATIONS: '/organizations',
  ORGANIZATION_CREATE: '/organizations/create',
  ORGANIZATION: (id) => `/organizations/${id}`,
  ORGANIZATION_SETTINGS: (id) => `/organizations/${id}/settings`,

  SETTINGS: '/settings',
  SETTINGS_SECURITY: '/settings/security',
  SETTINGS_API_KEYS: '/settings/api-keys',
  SETTINGS_USERS: '/settings/users',

  ADMIN: '/admin',
  ADMIN_ORGANIZATIONS: '/admin/organizations',
};

export const PUBLIC_ROUTES = [
  '/',
  '/login',
  '/login/mfa',
  '/signup',
  '/forgot-password',
  '/verify-email',
  '/auth/callback',
  '/terms',
  '/privacy',
  '/security',
  '/changelog',
  '/architecture',
];

export const PUBLIC_ROUTE_PREFIXES = [
  '/reset-password/',
  '/accept-invite/',
];

export const NAV_SECTIONS = [
  {
    id: 'main',
    label: null,
    items: [
      { id: 'dashboard', label: 'Dashboard', href: ROUTES.DASHBOARD, icon: 'LayoutDashboard' },
      { id: 'chat', label: 'Chat', href: ROUTES.CHAT, icon: 'MessageSquare' },
    ],
  },
  {
    id: 'build',
    label: 'Build',
    items: [
      { id: 'projects', label: 'Projects', href: ROUTES.PROJECTS, icon: 'FolderKanban' },
      { id: 'agents', label: 'Agents', href: ROUTES.AGENTS, icon: 'Bot' },
      { id: 'knowledge-bases', label: 'Knowledge Bases', href: ROUTES.KNOWLEDGE_BASES, icon: 'BookOpen' },
      { id: 'workflows', label: 'Workflows', href: ROUTES.WORKFLOWS, icon: 'Workflow' },
      { id: 'datasets', label: 'Datasets', href: ROUTES.DATASETS, icon: 'Database' },
      { id: 'prompts', label: 'Prompts', href: ROUTES.PROMPTS, icon: 'FileText' },
    ],
  },
  {
    id: 'debug',
    label: 'Debug',
    items: [
      { id: 'retrieval-debugger', label: 'Retrieval Debugger', href: ROUTES.RETRIEVAL_DEBUGGER, icon: 'Search' },
      { id: 'vector-stores', label: 'Vector Stores', href: ROUTES.VECTOR_STORES, icon: 'Layers' },
    ],
  },
  {
    id: 'ops',
    label: 'Operations',
    items: [
      { id: 'monitoring', label: 'Monitoring', href: ROUTES.MONITORING, icon: 'Activity' },
      { id: 'plugins', label: 'Plugins', href: ROUTES.PLUGINS, icon: 'Puzzle' },
    ],
  },
  {
    id: 'account',
    label: 'Account',
    items: [
      { id: 'organizations', label: 'Organizations', href: ROUTES.ORGANIZATIONS, icon: 'Building2' },
      { id: 'settings', label: 'Settings', href: ROUTES.SETTINGS, icon: 'Settings' },
    ],
  },
];
