"""Windows 默认录音设备路由。

用未公开的 IPolicyConfig COM 接口, 把某个录音设备(默认 CABLE Output)设为系统
默认的"通信"和"控制台"录音设备, 这样游戏/语音软件无需手动设置就会用上虚拟麦。
退出时自动恢复成原来的默认设备。无需管理员权限。
"""

from __future__ import annotations

import warnings
from ctypes import HRESULT
from ctypes.wintypes import DWORD, LPCWSTR

import comtypes
from comtypes import CLSCTX_ALL, COMMETHOD, GUID, CoCreateInstance, IUnknown
from pycaw.pycaw import AudioUtilities, EDataFlow, ERole


def _ensure_com() -> None:
    try:
        comtypes.CoInitialize()
    except Exception:
        pass

_CLSID_PolicyConfigClient = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")

# 设备角色: eConsole=0(默认), eMultimedia=1, eCommunications=2
_ROLE_CONSOLE = ERole.eConsole.value
_ROLE_COMMUNICATIONS = ERole.eCommunications.value
_ROLES = (_ROLE_CONSOLE, _ROLE_COMMUNICATIONS)


class IPolicyConfig(IUnknown):
    """只声明到 SetDefaultEndpoint 为止; 前面的方法用占位以对齐 vtable 槽位。"""

    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_ = (
        COMMETHOD([], HRESULT, "GetMixFormat"),
        COMMETHOD([], HRESULT, "GetDeviceFormat"),
        COMMETHOD([], HRESULT, "ResetDeviceFormat"),
        COMMETHOD([], HRESULT, "SetDeviceFormat"),
        COMMETHOD([], HRESULT, "GetProcessingPeriod"),
        COMMETHOD([], HRESULT, "SetProcessingPeriod"),
        COMMETHOD([], HRESULT, "GetShareMode"),
        COMMETHOD([], HRESULT, "SetShareMode"),
        COMMETHOD([], HRESULT, "GetPropertyValue"),
        COMMETHOD([], HRESULT, "SetPropertyValue"),
        COMMETHOD(
            [],
            HRESULT,
            "SetDefaultEndpoint",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], DWORD, "eRole"),
        ),
        COMMETHOD([], HRESULT, "SetEndpointVisibility"),
    )


def _policy_config() -> "IPolicyConfig":
    return CoCreateInstance(
        _CLSID_PolicyConfigClient, IPolicyConfig, CLSCTX_ALL
    )


def find_capture_device_id(name_substr: str) -> str | None:
    """按名字(子串)找录音设备的 endpoint id。"""
    name_substr = name_substr.lower()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        devices = AudioUtilities.GetAllDevices()
    for dev in devices:
        fname = (dev.FriendlyName or "") if hasattr(dev, "FriendlyName") else ""
        if name_substr in fname.lower() and dev.id:
            return dev.id
    return None


def get_default_capture_id(role: int) -> str | None:
    """取当前默认录音设备(指定角色)的 endpoint id, 用于退出时恢复。"""
    try:
        enumerator = AudioUtilities.GetDeviceEnumerator()
        dev = enumerator.GetDefaultAudioEndpoint(EDataFlow.eCapture.value, role)
        return dev.GetId()
    except Exception:
        return None


def set_default_capture_by_id(device_id: str, roles=_ROLES) -> None:
    pc = _policy_config()
    for role in roles:
        pc.SetDefaultEndpoint(device_id, role)


class DefaultMicRouter:
    """把目标录音设备设为默认(通信+控制台), 退出时恢复原默认。"""

    def __init__(self, target_name: str = "CABLE Output"):
        self._target = target_name
        self._saved: dict[int, str] = {}
        self._applied = False

    def apply(self) -> bool:
        """成功返回 True; 找不到目标设备或出错返回 False。"""
        _ensure_com()
        target_id = find_capture_device_id(self._target)
        if not target_id:
            return False
        try:
            for role in _ROLES:
                cur = get_default_capture_id(role)
                if cur:
                    self._saved[role] = cur
            set_default_capture_by_id(target_id, _ROLES)
            self._applied = True
            return True
        except Exception:
            return False

    def restore(self) -> None:
        if not self._applied:
            return
        _ensure_com()
        try:
            pc = _policy_config()
            for role, dev_id in self._saved.items():
                try:
                    pc.SetDefaultEndpoint(dev_id, role)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._applied = False
            self._saved.clear()
