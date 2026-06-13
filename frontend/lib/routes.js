// lib/routes.js

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',

  PROJECTS: '/projects',
  PROJECT_CREATE: '/projects/create',
  PROJECT_DETAIL: (projectId) => `/projects/${projectId}`,
  PROJECT_ANALYTICS: (projectId) => `/projects/${projectId}/analytics`,
  PROJECT_SETTINGS: (projectId) => `/projects/${projectId}/settings`,

  AGENTS: '/agents',
  AGENT_CREATE: '/agents/create',
  AGENT_DETAIL: (agentId) => `/agents/${agentId}`,
  AGENT_SETTINGS: (agentId) => `/agents/${agentId}/settings`,

  KNOWLEDGE_BASES: '/knowledge-bases',
  KNOWLEDGE_BASE_CREATE: '/knowledge-bases/create',
  KNOWLEDGE_BASE_DETAIL: (kbId) => `/knowledge-bases/${kbId}`,
  KNOWLEDGE_BASE_CHUNKS: (kbId) => `/knowledge-bases/${kbId}/chunks`,
  KNOWLEDGE_BASE_EMBEDDINGS: (kbId) => `/knowledge-bases/${kbId}/embeddings`,
  KNOWLEDGE_BASE_RETRIEVAL: (kbId) => `/knowledge-bases/${kbId}/retrieval`,

  RETRIEVAL_DEBUGGER: '/retrieval-debugger',

  VECTOR_STORES: '/vector-stores',
  VECTOR_STORE_QDRANT: '/vector-stores/qdrant',
  VECTOR_STORE_MILVUS: '/vector-stores/milvus',
  VECTOR_STORE_PGVECTOR: '/vector-stores/pgvector',

  MONITORING: '/monitoring',
  MONITORING_LOGS: '/monitoring/logs',
  MONITORING_TRACES: '/monitoring/traces',
  MONITORING_ALERTS: '/monitoring/alerts',

  SETTINGS: '/settings',
  SETTINGS_API_KEYS: '/settings/api-keys',
  SETTINGS_SECURITY: '/settings/security',
  SETTINGS_USERS: '/settings/users',
};

export const NAV_SECTIONS = [
  {
    label: 'General',
    items: [
      { label: 'Dashboard', href: ROUTES.DASHBOARD, icon: 'LayoutDashboard' },
      { label: 'Projects', href: ROUTES.PROJECTS, icon: 'FolderKanban' },
    ],
  },
  {
    label: 'Build',
    items: [
      { label: 'Knowledge Bases', href: ROUTES.KNOWLEDGE_BASES, icon: 'Database' },
      { label: 'Agents', href: ROUTES.AGENTS, icon: 'Bot' },
      { label: 'Vector Stores', href: ROUTES.VECTOR_STORES, icon: 'Boxes' },
    ],
  },
  {
    label: 'Diagnostics',
    items: [
      { label: 'Retrieval Debugger', href: ROUTES.RETRIEVAL_DEBUGGER, icon: 'SearchCode' },
      { label: 'Monitoring', href: ROUTES.MONITORING, icon: 'Activity' },
    ],
  },
  {
    label: 'Workspace',
    items: [
      { label: 'Settings', href: ROUTES.SETTINGS, icon: 'Settings' },
    ],
  },
];

export const PUBLIC_ROUTES = [ROUTES.LOGIN];