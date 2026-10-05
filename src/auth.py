"""Kimlik doğrulama.

Her istek "Authorization: Bearer <token>" başlığı taşır; çalışan kimliği
token'dan çıkarılır. İstemci kim olduğunu kendisi SÖYLEYEMEZ.

NOT: Bu bir demo. Gerçek bir şirkette token'lar kurumsal kimlik sağlayıcısından
(Azure AD, Okta, Keycloak gibi) gelen ve imzası doğrulanan JWT'ler olurdu.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.database import get_employee

DEMO_TOKENS = {
    "demo-token-e001": "E001",
    "demo-token-e002": "E002",
    "demo-token-e003": "E003",
    "demo-token-e004": "E004",
    "demo-token-e005": "E005",
    "demo-token-e006": "E006",
}

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_employee(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or credentials.credentials not in DEMO_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya eksik token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    employee = get_employee(DEMO_TOKENS[credentials.credentials])
    if employee is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Çalışan bulunamadı.")
    return dict(employee)