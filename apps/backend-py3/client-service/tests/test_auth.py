async def test_missing_device_id_returns_401(client):
    response = await client.get("/api/v1/projects")
    assert response.status_code == 401
    assert "X-Device-Id" in response.json()["detail"]


async def test_blank_device_id_returns_401(client):
    response = await client.get(
        "/api/v1/projects", headers={"X-Device-Id": "   "}
    )
    assert response.status_code == 401


async def test_device_id_creates_user(client, auth_headers, db_session):
    from sqlalchemy import select

    from app.models import User

    response = await client.get("/api/v1/projects", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

    device_id = auth_headers["X-Device-Id"]
    result = await db_session.execute(
        select(User).where(User.device_id == device_id)
    )
    assert result.scalar_one_or_none() is not None
