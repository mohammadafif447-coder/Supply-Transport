from enum import Enum


class VehicleType(str, Enum):
    motor = "motor"
    pickup = "pickup"
    box_small = "box_small"
    box_medium = "box_medium"
    truck_cdd = "truck_cdd"
    truck_cdd_long = "truck_cdd_long"
    truck_fuso = "truck_fuso"
    truck_trailer = "truck_trailer"


class DriverStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"


class CargoType(str, Enum):
    general = "general"
    fragile = "fragile"
    frozen = "frozen"
    hazardous = "hazardous"
    document = "document"


class OrderStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    picked_up = "picked_up"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"
