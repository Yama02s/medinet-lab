import pytest
from tests.conftest import create_test_token

@pytest.mark.asyncio
async def test_valid_pdf_upload_and_download(client, test_ids):
    doc_token = create_test_token(test_ids["doctor_1"], "medico")
    lab_token = create_test_token(test_ids["lab_tech"], "laboratorista")
    pat_token = create_test_token(test_ids["patient_1"], "paciente")

    res_order = await client.post(
        "/api/lab/orders",
        json={"patient_id": str(test_ids["patient_1"]), "exam_type": "Biopsia", "priority": "urgente"},
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    order_id = res_order.json()["id"]

    # Contenido con firma real %PDF-1.4
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    files = {"file": ("informe_biopsia.pdf", valid_pdf_content, "application/pdf")}

    res_upload = await client.post(
        f"/api/lab/orders/{order_id}/results",
        files=files,
        headers={"Authorization": f"Bearer {lab_token}"}
    )
    assert res_upload.status_code == 201
    result_data = res_upload.json()
    assert result_data["original_filename"] == "informe_biopsia.pdf"
    assert len(result_data["sha256_hash"]) == 64

    # Paciente dueño descarga el archivo y verifica cabeceras de seguridad
    res_dl = await client.get(
        f"/api/lab/results/{result_data['id']}/download",
        headers={"Authorization": f"Bearer {pat_token}"}
    )
    assert res_dl.status_code == 200
    assert res_dl.headers["x-content-type-options"] == "nosniff"
    assert 'attachment; filename="informe_biopsia.pdf"' in res_dl.headers["content-disposition"]

@pytest.mark.asyncio
async def test_disguised_executable_and_double_extension_rejected(client, test_ids):
    doc_token = create_test_token(test_ids["doctor_1"], "medico")
    lab_token = create_test_token(test_ids["lab_tech"], "laboratorista")

    res_order = await client.post(
        "/api/lab/orders",
        json={"patient_id": str(test_ids["patient_1"]), "exam_type": "Radiografía", "priority": "normal"},
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    order_id = res_order.json()["id"]

    # 1. Ejecutable Windows/Linux o script PHP disfrazado con extensión .pdf (Magic bytes falsos)
    fake_pdf_exe = b"MZ\x90\x00\x03\x00\x00\x00<?php system($_GET['cmd']); ?>"
    files_disguised = {"file": ("resultado_falso.pdf", fake_pdf_exe, "application/pdf")}

    res_fake = await client.post(
        f"/api/lab/orders/{order_id}/results",
        files=files_disguised,
        headers={"Authorization": f"Bearer {lab_token}"}
    )
    assert res_fake.status_code == 415

    # 2. Doble extensión maliciosa (shell.php.pdf) aún con cabecera PDF válida
    valid_pdf_bytes = b"%PDF-1.4\nContenido limpio"
    files_double = {"file": ("exploit.php.pdf", valid_pdf_bytes, "application/pdf")}

    res_double = await client.post(
        f"/api/lab/orders/{order_id}/results",
        files=files_double,
        headers={"Authorization": f"Bearer {lab_token}"}
    )
    assert res_double.status_code == 415

@pytest.mark.asyncio
async def test_oversized_file_rejected_with_413(client, test_ids):
    doc_token = create_test_token(test_ids["doctor_1"], "medico")
    lab_token = create_test_token(test_ids["lab_tech"], "laboratorista")

    res_order = await client.post(
        "/api/lab/orders",
        json={"patient_id": str(test_ids["patient_1"]), "exam_type": "Resonancia", "priority": "normal"},
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    order_id = res_order.json()["id"]

    # Archivo PDF que supera el límite de 1 MB configurado en conftest (1.5 MB)
    oversized_pdf = b"%PDF-1.4\n" + (b"A" * (1024 * 1024 + 500000))
    files = {"file": ("resonancia_pesada.pdf", oversized_pdf, "application/pdf")}

    res_large = await client.post(
        f"/api/lab/orders/{order_id}/results",
        files=files,
        headers={"Authorization": f"Bearer {lab_token}"}
    )
    assert res_large.status_code == 413
