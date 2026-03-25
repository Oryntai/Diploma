from .ip_camera import IPCameraDevice
from .smart_door_lock import SmartDoorLockDevice
from .smart_plug import SmartPlugDevice
from .temperature import TemperatureSensor

__all__ = [
    "TemperatureSensor",
    "SmartPlugDevice",
    "IPCameraDevice",
    "SmartDoorLockDevice",
]

DEVICE_CLASSES = {
    "temperature_sensor": TemperatureSensor,
    "smart_plug": SmartPlugDevice,
    "ip_camera": IPCameraDevice,
    "smart_door_lock": SmartDoorLockDevice,
}
