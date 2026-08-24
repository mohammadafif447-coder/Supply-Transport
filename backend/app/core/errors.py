from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from pydantic import ValidationError

UNIQUE_VIOLATION = "23505"

# Kode error kustom dari fungsi Postgres transition_order_status
# (lihat supabase/migrations/0002_order_transition_function.sql)
ORDER_INVALID_TRANSITION = "P0001"
ORDER_NOT_FOUND = "P0002"
ORDER_POD_REQUIRED = "P0003"
ORDER_DRIVER_VEHICLE_REQUIRED = "P0004"


def validation_error_to_http(exc: ValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=exc.errors(include_url=False, include_context=False),
    )


def db_error_to_http(exc: APIError) -> HTTPException:
    if exc.code == UNIQUE_VIOLATION:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Data sudah terdaftar sebelumnya ({exc.details or exc.message}).",
        )
    if exc.code == ORDER_NOT_FOUND:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order tidak ditemukan.")
    if exc.code == ORDER_INVALID_TRANSITION:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transisi status tidak diizinkan ({exc.message}).",
        )
    if exc.code == ORDER_POD_REQUIRED:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order ini mensyaratkan bukti serah terima (POD) sebelum bisa diselesaikan.",
        )
    if exc.code == ORDER_DRIVER_VEHICLE_REQUIRED:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="driver_id dan vehicle_id wajib diisi untuk assignment.",
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
