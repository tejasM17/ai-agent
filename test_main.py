import pytest
from fastapi.testclient import TestClient
from main import app, tasks_db
from unittest.mock import patch
from agents import TriageReport

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_db():
    tasks_db.clear()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_all_patients_empty():
    response = client.get("/api/incoming-patient")
    assert response.status_code == 200
    assert response.json()["total_tasks"] == 0
    assert response.json()["tasks"] == {}

@patch("main.process_patient_case")
def test_post_patient_success(mock_process):
    # Setup mock
    mock_report = TriageReport(
        urgency="High",
        symptoms_list=["chest pain", "shortness of breath"],
        medical_guidance="Seek immediate emergency care.",
        doctor_notes="High priority case."
    )
    mock_process.return_value = {
        "triage_report": mock_report,
        "research_facts": "Mocked research facts",
        "reflection": "Mocked reflection"
    }

    # Execute
    payload = {"email_body": "I have severe chest pain."}
    response = client.post("/api/incoming-patient", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["triage_report"]["urgency"] == "High"
    assert len(tasks_db) == 1
    
    # Test GET after POST
    get_response = client.get("/api/incoming-patient")
    assert get_response.status_code == 200
    assert get_response.json()["total_tasks"] == 1

def test_get_task_not_found():
    response = client.get("/tasks/nonexistent")
    assert response.status_code == 404
