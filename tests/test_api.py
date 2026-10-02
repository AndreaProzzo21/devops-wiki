import pytest
from fastapi.testclient import TestClient
from app.main import app 

# Creiamo il client di test
client = TestClient(app)

def test_get_tools_returns_200():
    response = client.get("/api/tools")
    assert response.status_code == 200
    # Assumiamo ritorni una lista o un dizionario, dipendentemente dal tuo DB
    assert isinstance(response.json(), (dict, list))

def test_list_commands_pagination():
    response = client.get("/api/commands?page=1&limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert data["limit"] == 5
    assert isinstance(data["items"], list)

def test_list_commands_validation_error():
    # Il limite massimo impostato nell'OpenAPI è 100
    response = client.get("/api/commands?limit=150")
    assert response.status_code == 422
    assert "detail" in response.json()

def test_search_commands_success():
    # 'q' è required (min_length=1)
    response = client.get("/api/search?q=test")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_search_commands_missing_query():
    # Chiamata senza il parametro 'q' obbligatorio
    response = client.get("/api/search")
    assert response.status_code == 422

def test_get_command_not_found():
    # ID inesistente per triggerare l'eccezione 404
    response = client.get("/api/commands/id-inventato-che-non-esiste-123")
    assert response.status_code == 404
    assert response.json() == {"detail": "Command not found"}

import time

def test_search_rate_limiting():
    # Usiamo un IP completamente casuale o unico per evitare conflitti con altri test
    headers = {"X-Forwarded-For": "192.168.100.55"}
    
    # Eseguiamo 9 chiamate consentite (stiamo leggermente sotto il tetto massimo di 10 per sicurezza)
    for _ in range(9):
        res = client.get("/api/search?q=docker", headers=headers)
        assert res.status_code == 200
        # Una micro-pausa per distribuire le chiamate nel tempo del singolo secondo
        time.sleep(0.05)
        
    # La chiamata che supera il limite (la 10ª o 11ª nello stesso secondo) deve restituire 429
    res_blocked = client.get("/api/search?q=docker", headers=headers)
    assert res_blocked.status_code == 429
    assert "Retry-After" in res_blocked.headers