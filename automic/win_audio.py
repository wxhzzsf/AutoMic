"""Windows 默认录音设备路由。

用未公开的 IPolicyConfig COM 接口, 把某个录音设备(默认 CABLE Output)设为系统
默认录音设备(eConsole + eMultimedia), 这样游戏/语音软件无需手动设置就会用上虚拟麦。
只动录音设备, 绝不改扬声器/渲染设备, 也不设"默认通信设备"(避免触发扬声器自动闪避)。
退出时自动恢复成原来的默认设备。无需管理员权限。
"""

from __future__ import annotations

import warnings
from ctypes import HRESULT
from ctypes.wintypes import DWORD, LPCWSTR

import comtypes
from comtypes import CLSCTX_ALL, COMMETHOD, GUID, CoCreateInstance, IUnknown
from pycaw.pycaw import DEVICE_STATE, AudioUtilities, EDataFlow, ERole


def _ensure_com() -> None:
    try:
        comtypes.CoInitialize()
    except Exception:
        pass

_CLSID_PolicyConfigClient = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")

# 设备角色: eConsole=0(默认), eMultimedia=1, eCommunications=2
#
# 只设 eConsole + eMultimedia(即系统"默认录音设备")。
# 故意**不**设 eCommunications: 把某设备设成"默认通信设备"会让 Windows 以为
# 正在通话, 触发"通信活动时降低其他声音"的自动闪避(ducking), 表现为扬声器变小声——
# 这正是用户不希望发生的"动了扬声器设置"。只设默认录音设备就不会影响扬声器。
_ROLE_CONSOLE = ERole.eConsole.value
_ROLE_MULTIMEDIA = ERole.eMultimedia.value
_ROLES = (_ROLE_CONSOLE, _ROLE_MULTIMEDIA)


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
    """按名字(子串)找**录音(采集)**设备的 endpoint id。

    只在采集设备(eCapture)里查找, 绝不会返回扬声器/渲染(eRender)设备的 id,
    这样路由默认麦克风时永远不会误改扬声器。
    """
    name_substr = name_substr.lower()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        devices = AudioUtilities.GetAllDevices(
            EDataFlow.eCapture.value, DEVICE_STATE.ACTIVE.value
        )
    for dev in devices:
        fname = (dev.FriendlyName or "") if hasattr(dev, "FriendlyName") else ""
        if name_substr in fname.lower() and dev.id:
            return dev.id
    return None


def is_capture_device(device_id: str) -> bool:
    """确认某 endpoint 是录音(采集)设备; 用作改默认设备前的安全闸门。"""
    try:
        return (
            AudioUtilities.GetEndpointDataFlow(device_id, 1)
            == EDataFlow.eCapture.value
        )
    except Exception:
        return False


def get_default_capture_id(role: int) -> str | None:
    """取当前默认录音设备(指定角色)的 endpoint id, 用于退出时恢复。"""
    try:
        enumerator = AudioUtilities.GetDeviceEnumerator()
        dev = enumerator.GetDefaultAudioEndpoint(EDataFlow.eCapture.value, role)
        return dev.GetId()
    except Exception:
        return None


def set_default_capture_by_id(device_id: str, roles=_ROLES) -> None:
    # 安全闸门: 只对录音设备改默认值, 绝不动扬声器(渲染设备)的默认输出。
    if not is_capture_device(device_id):
        raise ValueError("refusing to set default: not a capture device")
    pc = _policy_config()
    for role in roles:
        pc.SetDefaultEndpoint(device_id, role)


class DefaultMicRouter:
    """把目标录音设备设为系统默认录音设备(eConsole+eMultimedia), 退出时恢复原默认。

    只影响"默认录音设备", 不触碰扬声器, 也不设"默认通信设备"。
    """

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
