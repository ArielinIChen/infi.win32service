import ctypes
from collections import namedtuple

from .utils import enum
from .service import Service

OpenSCManager      = ctypes.windll.advapi32.OpenSCManagerW
CloseServiceHandle = ctypes.windll.advapi32.CloseServiceHandle
CreateService      = ctypes.windll.advapi32.CreateServiceW

# From http://msdn.microsoft.com/en-us/library/windows/desktop/ms685981%28v=vs.85%29.aspx
ServiceManagerAccess = enum(
    ALL                = 0xF003F,
    CONNECT            = 0x0001,
    CREATE_SERVICE     = 0x0002,
    ENUMERATE_SERVICE  = 0x0004,
    LOCK               = 0x0008,
    QUERY_LOCK_STATUS  = 0x0010,
    MODIFY_BOOT_CONFIG = 0x0020)

# From http://msdn.microsoft.com/en-us/library/windows/desktop/ms684323%28v=vs.85%29.aspx
SC_ACTIVE_DATABASE = u"SERVICES_ACTIVE_DATABASE"

# From http://msdn.microsoft.com/en-us/library/windows/desktop/ms682450%28v=vs.85%29.aspx

# -- CreateService.dwServiceType:
ServiceType = enum(
    KERNEL_DRIVER         = 0x00000001,
    FILE_SYSTEM_DRIVER    = 0x00000002,
    ADAPTER               = 0x00000004,
    RECOGNIZER_DRIVER     = 0x00000008,
    WIN32_OWN_PROCESS     = 0x00000010,
    WIN32_SHARE_PROCESS   = 0x00000020,
    INTERACTIVE_PROCESS   = 0x00000100)

# -- CreateService.dwStartType:
ServiceStartType = enum(
    BOOT     = 0x00000000,
    SYSTEM   = 0x00000001,
    AUTO     = 0x00000002,
    DEMAND   = 0x00000003,
    DISABLED = 0x00000004)

# -- CreateService.dwErrorControl:
ServiceErrorControl = enum(
    IGNORE   = 0x00000000, 
    NORMAL   = 0x00000001,
    SEVERE   = 0x00000002,
    CRITICAL = 0x00000003)

# -- CreateService.dwDesiredAccess:
ServiceAccess = enum(ALL                  = 0xF01FF,
                     QUERY_CONFIG         = 0x0001,
                     CHANGE_CONFIG        = 0x0002,
                     QUERY_STATUS         = 0x0004,
                     ENUMERATE_DEPENDENTS = 0x0008,
                     START                = 0x0010,
                     STOP                 = 0x0020,
                     PAUSE_CONTINUE       = 0x0040,
                     INTERROGATE          = 0x0080,
                     USER_DEFINED_CONTROL = 0x0100)

class ServiceControlManagerContext(object):
    def __init__(self, machine=None, database=None, access=ServiceManagerAccess.ALL):
        super(ServiceControlManagerContext, self).__init__()
        self.machine = unicode(machine) if machine is not None else 0
        self.database = unicode(database) if machine is not None else 0
        self.access = access
        self.scm = None
        
    def __enter__(self):
        scm_handle = OpenSCManager(self.machine, self.database, self.access)
        if scm_handle == 0:
            raise ctypes.WinError()
        self.scm = ServiceControlManager(scm_handle)
        return self.scm

    def __exit__(self, type, value, traceback):
        if self.scm is not None:
            self.scm.close()

class ServiceControlManager(object):
    def __init__(self, handle):
        super(ServiceControlManager, self).__init__()
        self.handle = handle

    def create_service(self, name, display_name, type, start_type, path,
                       load_order_group=None, dependencies=None, error_control=ServiceErrorControl.NORMAL,
                       account=None, account_password=None, access=ServiceAccess.ALL):
        # http://msdn.microsoft.com/en-us/library/windows/desktop/ms682450%28v=vs.85%29.aspx
        # SC_HANDLE WINAPI CreateService(
        #   __in       SC_HANDLE hSCManager,
        #   __in       LPCTSTR lpServiceName,
        #   __in_opt   LPCTSTR lpDisplayName,
        #   __in       DWORD dwDesiredAccess,
        #   __in       DWORD dwServiceType,
        #   __in       DWORD dwStartType,
        #   __in       DWORD dwErrorControl,
        #   __in_opt   LPCTSTR lpBinaryPathName,
        #   __in_opt   LPCTSTR lpLoadOrderGroup,
        #   __out_opt  LPDWORD lpdwTagId,
        #   __in_opt   LPCTSTR lpDependencies,
        #   __in_opt   LPCTSTR lpServiceStartName,
        #   __in_opt   LPCTSTR lpPassword
        #);
        lpServiceName = unicode(name)
        lpDisplayName = unicode(display_name)
        dwDesiredAccess = access
        dwServiceType = type
        dwStartType = start_type
        dwErrorControl = error_control
        lpBinaryPathName = unicode(path) 
        lpLoadOrderGroup = unicode(load_order_group) if load_order_group is not None else 0

        tag_id = ctypes.c_ulong()
        lpdwTagId = ctypes.byref(tag_id)

        lpDependencies = unicode(dependencies) if dependencies is not None else 0
        lpServiceStartName = unicode(account) if account is not None else 0
        lpPassword = unicode(account_password) if account_password is not None else 0
        
        service_h = CreateService(self.handle, lpServiceName, lpDisplayName, dwDesiredAccess, dwServiceType,
                                  dwStartType, dwErrorControl, lpBinaryPathName, lpLoadOrderGroup, lpdwTagId,
                                  lpDependencies, lpServiceStartName, lpPassword)
        if service_h == 0:
            raise ctypes.WinError()
        return Service(service_h, tag_id.value)

    def open_service(self, name, access=ServiceAccess.ALL):
        service_h = OpenService(self.handle, unicode(name), access)
        if service_h == 0:
            raise ctypes.WinError()
        return Service(service_h)

    def close(self):
        if self.handle != 0:
            if not CloseServiceHandle(self.handle):
                raise ctypes.WinError()
            self.handle = 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()