// lib/permissions.js

import { USER_ROLES } from '@/lib/constants';

const ROLE_HIERARCHY = {
  [USER_ROLES.SUPER_ADMIN]: 50,
  [USER_ROLES.OWNER]: 40,
  [USER_ROLES.ADMIN]: 30,
  [USER_ROLES.DEVELOPER]: 20,
  [USER_ROLES.VIEWER]: 10,
};

export const PERMISSIONS = {
  PROJECTS_CREATE: 'projects:create',
  PROJECTS_DELETE: 'projects:delete',
  PROJECTS_UPDATE: 'projects:update',
  PROJECTS_VIEW: 'projects:view',

  AGENTS_CREATE: 'agents:create',
  AGENTS_DELETE: 'agents:delete',
  AGENTS_RUN: 'agents:run',
  AGENTS_VIEW: 'agents:view',

  KNOWLEDGE_BASES_CREATE: 'knowledge_bases:create',
  KNOWLEDGE_BASES_DELETE: 'knowledge_bases:delete',
  KNOWLEDGE_BASES_UPDATE: 'knowledge_bases:update',
  KNOWLEDGE_BASES_VIEW: 'knowledge_bases:view',

  VECTOR_STORES_MANAGE: 'vector_stores:manage',
  VECTOR_STORES_VIEW: 'vector_stores:view',

  MONITORING_VIEW: 'monitoring:view',

  SETTINGS_MANAGE: 'settings:manage',
  SETTINGS_API_KEYS: 'settings:api_keys',
  SETTINGS_USERS: 'settings:users',
  SETTINGS_SECURITY: 'settings:security',

  BILLING_MANAGE: 'billing:manage',
};

const ROLE_PERMISSIONS = {
  [USER_ROLES.SUPER_ADMIN]: Object.values(PERMISSIONS),
  [USER_ROLES.OWNER]: Object.values(PERMISSIONS),
  [USER_ROLES.ADMIN]: [
    PERMISSIONS.PROJECTS_CREATE,
    PERMISSIONS.PROJECTS_UPDATE,
    PERMISSIONS.PROJECTS_VIEW,
    PERMISSIONS.AGENTS_CREATE,
    PERMISSIONS.AGENTS_DELETE,
    PERMISSIONS.AGENTS_RUN,
    PERMISSIONS.AGENTS_VIEW,
    PERMISSIONS.KNOWLEDGE_BASES_CREATE,
    PERMISSIONS.KNOWLEDGE_BASES_DELETE,
    PERMISSIONS.KNOWLEDGE_BASES_UPDATE,
    PERMISSIONS.KNOWLEDGE_BASES_VIEW,
    PERMISSIONS.VECTOR_STORES_MANAGE,
    PERMISSIONS.VECTOR_STORES_VIEW,
    PERMISSIONS.MONITORING_VIEW,
    PERMISSIONS.SETTINGS_API_KEYS,
    PERMISSIONS.SETTINGS_USERS,
  ],
  [USER_ROLES.DEVELOPER]: [
    PERMISSIONS.PROJECTS_VIEW,
    PERMISSIONS.AGENTS_CREATE,
    PERMISSIONS.AGENTS_RUN,
    PERMISSIONS.AGENTS_VIEW,
    PERMISSIONS.KNOWLEDGE_BASES_CREATE,
    PERMISSIONS.KNOWLEDGE_BASES_UPDATE,
    PERMISSIONS.KNOWLEDGE_BASES_VIEW,
    PERMISSIONS.VECTOR_STORES_VIEW,
    PERMISSIONS.MONITORING_VIEW,
    PERMISSIONS.SETTINGS_API_KEYS,
  ],
  [USER_ROLES.VIEWER]: [
    PERMISSIONS.PROJECTS_VIEW,
    PERMISSIONS.AGENTS_VIEW,
    PERMISSIONS.KNOWLEDGE_BASES_VIEW,
    PERMISSIONS.VECTOR_STORES_VIEW,
    PERMISSIONS.MONITORING_VIEW,
  ],
};

export function hasPermission(role, permission) {
  if (!role || !permission) return false;
  const permissions = ROLE_PERMISSIONS[role] || [];
  return permissions.includes(permission);
}

export function hasAnyPermission(role, permissionList = []) {
  return permissionList.some((permission) => hasPermission(role, permission));
}

export function hasAllPermissions(role, permissionList = []) {
  return permissionList.every((permission) => hasPermission(role, permission));
}

export function isRoleAtLeast(role, minimumRole) {
  const roleLevel = ROLE_HIERARCHY[role] ?? 0;
  const minimumLevel = ROLE_HIERARCHY[minimumRole] ?? 0;
  return roleLevel >= minimumLevel;
}

export function canManageWorkspace(role) {
  return isRoleAtLeast(role, USER_ROLES.ADMIN);
}

export function canManageBilling(role) {
  return isRoleAtLeast(role, USER_ROLES.OWNER);
}