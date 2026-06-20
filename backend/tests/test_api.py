# tests/test_api.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, api_client) -> None:
        response = await api_client.get("/health")
        assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_live_endpoint(self, api_client) -> None:
        response = await api_client.get("/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_success(self, api_client, test_user) -> None:
        response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "TestPassword123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert "nc_access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, api_client, test_user) -> None:
        response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "WrongPassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, api_client) -> None:
        response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@neuralcore.test", "password": "whatever"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_requires_auth(self, api_client) -> None:
        response = await api_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token(self, api_client, auth_headers, test_user) -> None:
        response = await api_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email


class TestProjectEndpoints:
    @pytest.mark.asyncio
    async def test_list_projects_requires_auth(self, api_client) -> None:
        response = await api_client.get("/api/v1/projects")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_project(self, api_client, auth_headers) -> None:
        response = await api_client.post(
            "/api/v1/projects",
            json={"name": "My Test Project", "description": "A project for testing"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Test Project"
        assert "slug" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, api_client, auth_headers) -> None:
        import uuid
        response = await api_client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404


class TestAgentEndpoints:
    @pytest.mark.asyncio
    async def test_list_agent_tools(self, api_client, auth_headers) -> None:
        response = await api_client.get("/api/v1/agents/tools", headers=auth_headers)
        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) > 0


class TestKnowledgeBaseEndpoints:
    @pytest.mark.asyncio
    async def test_list_chunking_strategies(self, api_client) -> None:
        response = await api_client.get("/api/v1/knowledge-bases/chunking-strategies")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 8

    @pytest.mark.asyncio
    async def test_list_ingestion_sources(self, api_client) -> None:
        response = await api_client.get("/api/v1/knowledge-bases/ingestion-sources")
        assert response.status_code == 200
        sources = response.json()
        assert len(sources) > 0
