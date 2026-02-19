import jwt

from app.services.google_oauth_service import GOOGLE_ID_TOKEN_ALGORITHM

GOOGLE_SAMPLE_JWK = {
    "kty": "RSA",
    "kid": "c816d337b8365a06a851ad80016c171099492609",
    "alg": "RS256",
    "use": "sig",
    "n": (
        "upqfXMzThiSPdQfFN2--TPprv6IAPDAHoSA7S2fCr5DYJbG-CRomlIvtblCq_3_AU_Fk-BREd3"
        "yQtMBrT5w60bAmwYThBu0gdKCB0ApAXkHbVpmUvtTC6zBVcmentXkYN0TXME6RyDNPFXO6G28CU"
        "OenyLfQp9hmqF_lyfvRNpsptH_4uK70tZ6BSkobeBp3QrIYJs_qjhHfeSw9oisYFgz-w4yxfDrs"
        "ezPmhuDd_VpmHZqEOkIE1OP0gOMz99e7e-bIiHHcGUQ19L0LSxirqht0z00dXFUFwBSeOOfrUJf"
        "A8n4o2IoFYPwNibOCK1FMl1ThfUVcZHpHEiC5yfPBfQ"
    ),
    "e": "AQAB",
}


def test_pyjwt_rs256_validation_backend_is_available() -> None:
    key = jwt.PyJWK.from_dict(
        GOOGLE_SAMPLE_JWK,
        algorithm=GOOGLE_ID_TOKEN_ALGORITHM,
    ).key

    assert key is not None
