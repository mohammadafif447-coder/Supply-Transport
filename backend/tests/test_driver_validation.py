import pytest
from pydantic import ValidationError

from app.models.driver import DriverCreate
from app.models.vehicle import VehicleCreate


def _valid_vehicle_kwargs(**overrides) -> dict:
    kwargs = {"plate_number": "B1234FT", "vehicle_type": "pickup", "max_weight_kg": 1000}
    kwargs.update(overrides)
    return kwargs


def _valid_driver_kwargs(**overrides) -> dict:
    kwargs = {
        "full_name": "Budi Santoso",
        "phone_number": "081234567890",
        "ktp_number": "3171234567890001",
        "sim_number": "SIM-001",
        "bank_name": "BCA",
        "bank_account_number": "1234567890",
        "vehicle": VehicleCreate(**_valid_vehicle_kwargs()),
    }
    kwargs.update(overrides)
    return kwargs


def test_driver_create_accepts_valid_payload():
    driver = DriverCreate(**_valid_driver_kwargs())
    assert driver.full_name == "Budi Santoso"


@pytest.mark.parametrize(
    "phone_number",
    ["081234567890", "6281234567890", "+6281234567890"],
)
def test_driver_create_accepts_valid_indonesian_phone_formats(phone_number):
    driver = DriverCreate(**_valid_driver_kwargs(phone_number=phone_number))
    assert driver.phone_number == phone_number


@pytest.mark.parametrize(
    "phone_number",
    [
        "12345",
        "0812345",  # too short
        "081234567890123456",  # too long
        "0912345678901",  # doesn't start with 8 after prefix
        "abcdefghij",
        "+1234567890",
    ],
)
def test_driver_create_rejects_invalid_phone_formats(phone_number):
    with pytest.raises(ValidationError):
        DriverCreate(**_valid_driver_kwargs(phone_number=phone_number))


@pytest.mark.parametrize(
    "ktp_number",
    ["123", "12345678901234567", "not-numeric-16char", "317123456789000A"],
)
def test_driver_create_rejects_invalid_ktp_number(ktp_number):
    with pytest.raises(ValidationError):
        DriverCreate(**_valid_driver_kwargs(ktp_number=ktp_number))


def test_driver_create_rejects_full_name_too_short():
    with pytest.raises(ValidationError):
        DriverCreate(**_valid_driver_kwargs(full_name="ab"))


@pytest.mark.parametrize("bank_account_number", ["123", "abc123456", "1" * 21])
def test_driver_create_rejects_invalid_bank_account_number(bank_account_number):
    with pytest.raises(ValidationError):
        DriverCreate(**_valid_driver_kwargs(bank_account_number=bank_account_number))


def test_vehicle_create_accepts_valid_payload():
    vehicle = VehicleCreate(**_valid_vehicle_kwargs())
    assert vehicle.vehicle_type.value == "pickup"


@pytest.mark.parametrize("plate_number", ["B1", "b1234ft", "B1234@FT"])
def test_vehicle_create_rejects_invalid_plate_number(plate_number):
    with pytest.raises(ValidationError):
        VehicleCreate(**_valid_vehicle_kwargs(plate_number=plate_number))


@pytest.mark.parametrize("max_weight_kg", [0, -1, 50001])
def test_vehicle_create_rejects_invalid_max_weight(max_weight_kg):
    with pytest.raises(ValidationError):
        VehicleCreate(**_valid_vehicle_kwargs(max_weight_kg=max_weight_kg))


def test_vehicle_create_rejects_unknown_vehicle_type():
    with pytest.raises(ValidationError):
        VehicleCreate(**_valid_vehicle_kwargs(vehicle_type="spaceship"))
