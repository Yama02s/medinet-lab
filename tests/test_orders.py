import pytest
from tests.conftest import create_test_token

@pytest.mark.asyncio
async def test_create_order_and_valid_state_transition(client, test_ids):
    doctor_token = create_test_token(test_ids["doctor_1"], "medico")
    lab_token = create_test_token(test_ids["lab_tech"], "laboratorista")

    # 1. Médico crea orden
    res = await client.post(
        "/api/lab/orders",
        json={
            "patient_id": str(test_ids["patient_1"]),
            "exam_type": "Hemograma Completo",
            "priority": "urgente",
            "clinical_notes": "Paciente presenta anemia aguda"
        },
        headers={"Authorization": f"Bearer {doctor_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    order_id = data["id"]
    assert data["status"] == "SOLICITADO"
    assert data["doctor_id"] == str(test_ids["doctor_1"])

    # 2. Laboratorista pasa a EN_PROCESO (Transición válida)
    res_patch = await client.patch(
        f"/api/lab/orders/{order_id}/status",
        json={"status": "EN_PROCESO"},
        headers={"Authorization": f"Bearer {lab_token}"}
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "EN_PROCESO"

@pytest.mark.asyncio
async def test_invalid_state_transition_rejected(client, test_ids):
    doctor_token = create_test_token(test_ids["doctor_1"], "medico")
    lab_token = create_test_token(test_ids["lab_tech"], "laboratorista")

    res = await client.post(
        "/api/lab/orders",
        json={
            "patient_id": str(test_ids["patient_1"]),
            "exam_type": "Perfil Lipídico",
            "priority": "normal"
        },
        headers={"Authorization": f"Bearer {doctor_token}"}
    )
    order_id = res.json()["id"]

    # Intentar pasar directo de SOLICITADO a ENTREGADO (Transición inválida)
    res_invalid = await client.patch(
        f"/api/lab/orders/{order_id}/status",
        json={"status": "ENTREGADO"},
        headers={"Authorization": f"Bearer {lab_token}"}
    )
    assert res_invalid.status_code == 400
    assert "Transición de estado inválida" in res_invalid.json()["detail"]
