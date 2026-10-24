import pytest
from tests.conftest import create_test_token

@pytest.mark.asyncio
async def test_idor_blocked_between_patients_and_doctors(client, test_ids):
    doc1_token = create_test_token(test_ids["doctor_1"], "medico")
    doc2_token = create_test_token(test_ids["doctor_2"], "medico")
    pat1_token = create_test_token(test_ids["patient_1"], "paciente")
    pat2_token = create_test_token(test_ids["patient_2"], "paciente")

    # Doctor 1 crea orden para Paciente 1
    res = await client.post(
        "/api/lab/orders",
        json={
            "patient_id": str(test_ids["patient_1"]),
            "exam_type": "PCR Covid-19",
            "priority": "urgente"
        },
        headers={"Authorization": f"Bearer {doc1_token}"}
    )
    order_id = res.json()["id"]

    # Caso 1: Paciente 2 intenta leer la orden del Paciente 1 (Ataque IDOR) -> Debe dar 403
    res_idor_pat = await client.get(
        f"/api/lab/orders/{order_id}",
        headers={"Authorization": f"Bearer {pat2_token}"}
    )
    assert res_idor_pat.status_code == 403

    # Caso 2: Médico 2 intenta leer orden creada por Médico 1 (Ataque IDOR) -> Debe dar 403
    res_idor_doc = await client.get(
        f"/api/lab/orders/{order_id}",
        headers={"Authorization": f"Bearer {doc2_token}"}
    )
    assert res_idor_doc.status_code == 403

    # Caso 3: Paciente 2 intenta listar historial de resultados del Paciente 1 -> Debe dar 403
    res_idor_results = await client.get(
        f"/api/lab/patients/{test_ids['patient_1']}/results",
        headers={"Authorization": f"Bearer {pat2_token}"}
    )
    assert res_idor_results.status_code == 403

    # Caso 4: Paciente 1 accede a su propia orden -> Debe dar 200 OK
    res_legit = await client.get(
        f"/api/lab/orders/{order_id}",
        headers={"Authorization": f"Bearer {pat1_token}"}
    )
    assert res_legit.status_code == 200
