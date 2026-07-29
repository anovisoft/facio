"""Client beacon events (UI-only types from docs/mvp/04-metrics.md)."""


async def test_accept_client_beacons(client, auth_headers, enqueue_path):
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project_id = created.json()["project"]["id"]

    for event_type in (
        "app_opened",
        "accept_viewed",
        "action_shown",
        "path_opened",
        "project_switched",
    ):
        response = await client.post(
            "/api/v1/events",
            headers=auth_headers,
            json={
                "type": event_type,
                "project_id": project_id,
                "payload": {"source": "test"},
            },
        )
        assert response.status_code == 201, event_type
        body = response.json()
        assert body["type"] == event_type
        assert body["project_id"] == project_id


async def test_reject_server_mutation_event_types(
    client, auth_headers, enqueue_path
):
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project_id = created.json()["project"]["id"]

    response = await client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={"type": "committed", "project_id": project_id},
    )
    assert response.status_code == 422
    assert "Allowed" in response.json()["detail"]


async def test_app_opened_without_project(client, auth_headers):
    response = await client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={"type": "app_opened", "payload": {}},
    )
    assert response.status_code == 201
    assert response.json()["project_id"] is None


async def test_event_for_foreign_project_not_found(client, auth_headers):
    response = await client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={
            "type": "path_opened",
            "project_id": "00000000-0000-0000-0000-000000000099",
        },
    )
    assert response.status_code == 404
