"""Read selected native type layouts from the matching local PDB."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import sys
from native_symbols import SYMBOL_INFO, pe_identity, pdb_identity

exe = Path(sys.argv[1]).resolve()
pe = pe_identity(exe)
identity = pdb_identity(exe.with_suffix('.pdb'))
assert any(all(p[k] == identity[k] for k in ('guid','age')) for p in pe['codeview'])
k = c.WinDLL('kernel32', use_last_error=True)
k.GetCurrentProcess.restype = w.HANDLE
h = k.GetCurrentProcess()
d = c.WinDLL('dbghelp', use_last_error=True)
d.SymInitializeW.argtypes=[w.HANDLE,w.LPCWSTR,w.BOOL]
d.SymLoadModuleExW.argtypes=[w.HANDLE,w.HANDLE,w.LPCWSTR,w.LPCWSTR,c.c_ulonglong,w.DWORD,c.c_void_p,w.DWORD]
d.SymLoadModuleExW.restype=c.c_ulonglong
d.SymGetTypeFromName.argtypes=[w.HANDLE,c.c_ulonglong,c.c_char_p,c.POINTER(SYMBOL_INFO)]
d.SymGetTypeInfo.argtypes=[w.HANDLE,c.c_ulonglong,w.ULONG,c.c_int,c.c_void_p]
d.SymCleanup.argtypes=[w.HANDLE]
d.SymSetOptions(0x602)
assert d.SymInitializeW(h,str(exe.parent),False)
try:
    base=d.SymLoadModuleExW(h,None,str(exe),None,pe['image_base'],pe['image_size'],None,0)
    assert base
    rows=[]
    for name in sys.argv[2:]:
        buffer=c.create_string_buffer(c.sizeof(SYMBOL_INFO)+2048)
        symbol=c.cast(buffer,c.POINTER(SYMBOL_INFO))
        symbol.contents.SizeOfStruct=c.sizeof(SYMBOL_INFO);symbol.contents.MaxNameLen=2048
        if not d.SymGetTypeFromName(h,base,name.encode(),symbol):
            rows.append({'name':name,'error':c.get_last_error()});continue
        index=symbol.contents.TypeIndex
        length=c.c_ulonglong();d.SymGetTypeInfo(h,base,index,2,c.byref(length))
        count=w.ULONG();d.SymGetTypeInfo(h,base,index,13,c.byref(count))
        class Children(c.Structure):_fields_=[('Count',w.ULONG),('Start',w.ULONG),('ChildId',w.ULONG*count.value)]
        children=Children();children.Count=count.value
        d.SymGetTypeInfo(h,base,index,7,c.byref(children))
        members=[]
        for child in children.ChildId:
            ptr=c.c_void_p();offset=w.ULONG();tag=w.ULONG()
            d.SymGetTypeInfo(h,base,child,0,c.byref(tag))
            if not d.SymGetTypeInfo(h,base,child,1,c.byref(ptr)):continue
            text=c.wstring_at(ptr);k.LocalFree(c.c_void_p(ptr.value))
            has_offset=d.SymGetTypeInfo(h,base,child,10,c.byref(offset))
            if has_offset:members.append({'name':text,'offset':offset.value,'tag':tag.value})
        rows.append({'name':name,'size':length.value,'members':members})
    print(json.dumps(rows,indent=2))
finally:d.SymCleanup(h)
