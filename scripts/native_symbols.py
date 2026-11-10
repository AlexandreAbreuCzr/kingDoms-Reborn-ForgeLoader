"""Read-only PE/PDB matching and local DbgHelp symbol queries; no target execution."""
from __future__ import annotations
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import struct
import uuid


def pe_identity(path):
    data = Path(path).read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    count = struct.unpack_from('<H', data, pe + 6)[0]
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    optional = pe + 24
    assert struct.unpack_from('<H', data, optional)[0] == 0x20b, 'PE32+ required'
    base = struct.unpack_from('<Q', data, optional + 24)[0]
    image_size = struct.unpack_from('<I', data, optional + 56)[0]
    sections = []
    for i in range(count):
        offset = optional + optional_size + i * 40
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from('<IIII', data, offset + 8)
        sections.append({'name': data[offset:offset+8].rstrip(b'\0').decode(), 'rva':rva,
                         'virtual_size':virtual_size, 'raw_size':raw_size, 'raw_offset':raw_offset})
    def file_offset(rva):
        for section in sections:
            delta = rva - section['rva']
            if 0 <= delta < section['raw_size']:
                return section['raw_offset'] + delta
        raise ValueError(f'RVA outside file-backed sections: {rva:#x}')
    debug_rva, debug_size = struct.unpack_from('<II', data, optional + 112 + 6*8)
    codeviews = []
    for i in range(debug_size // 28):
        offset = file_offset(debug_rva) + i * 28
        kind, size, _, pointer = struct.unpack_from('<IIII', data, offset + 12)
        if kind == 2 and data[pointer:pointer+4] == b'RSDS':
            codeviews.append({'guid':str(uuid.UUID(bytes_le=data[pointer+4:pointer+20])),
                              'age':struct.unpack_from('<I',data,pointer+20)[0],
                              'recorded_pdb_path':data[pointer+24:pointer+size].rstrip(b'\0').decode('utf-8','replace')})
    return {'image_base':base,'image_size':image_size,'sections':sections,'codeview':codeviews}


def pdb_identity(path):
    with Path(path).open('rb') as f:
        header = f.read(56)
        assert header.startswith(b'Microsoft C/C++ MSF 7.00'), 'MSF 7 required'
        block_size, _, _, directory_size, _, block_map = struct.unpack_from('<IIIIII',header,32)
        f.seek(block_map*block_size)
        directory_blocks=struct.unpack('<'+'I'*((directory_size+block_size-1)//block_size),
                                      f.read(4*((directory_size+block_size-1)//block_size)))
        directory=b''
        for block in directory_blocks:
            f.seek(block*block_size); directory+=f.read(block_size)
        count=struct.unpack_from('<I',directory)[0]
        lengths=struct.unpack_from('<'+'I'*count,directory,4)
        cursor=4+count*4
        for i,length in enumerate(lengths):
            blocks=0 if length==0xffffffff else (length+block_size-1)//block_size
            if i==1:
                stream=b''
                for block in struct.unpack_from('<'+'I'*blocks,directory,cursor):
                    f.seek(block*block_size); stream+=f.read(block_size)
                return {'guid':str(uuid.UUID(bytes_le=stream[12:28])),
                        'age':struct.unpack_from('<I',stream,8)[0], 'stream_count':count}
            cursor+=blocks*4
    raise ValueError('PDB info stream not found')


class SYMBOL_INFO(c.Structure):
    _fields_=[('SizeOfStruct',w.ULONG),('TypeIndex',w.ULONG),('Reserved',c.c_ulonglong*2),
              ('Index',w.ULONG),('Size',w.ULONG),('ModBase',c.c_ulonglong),('Flags',w.ULONG),
              ('Value',c.c_ulonglong),('Address',c.c_ulonglong),('Register',w.ULONG),
              ('Scope',w.ULONG),('Tag',w.ULONG),('NameLen',w.ULONG),('MaxNameLen',w.ULONG),('Name',c.c_char*1)]


def query_symbols(exe, pe, masks):
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=w.HANDLE
    handle=kernel.GetCurrentProcess()
    dbg=c.WinDLL('dbghelp',use_last_error=True)
    dbg.SymSetOptions.argtypes=[w.DWORD]; dbg.SymSetOptions.restype=w.DWORD
    # Fail-critical-errors, exact symbols, no network search path, undecorate.
    dbg.SymSetOptions(0x200 | 0x400 | 0x2)
    dbg.SymInitializeW.argtypes=[w.HANDLE,w.LPCWSTR,w.BOOL];dbg.SymInitializeW.restype=w.BOOL
    dbg.SymLoadModuleExW.argtypes=[w.HANDLE,w.HANDLE,w.LPCWSTR,w.LPCWSTR,c.c_ulonglong,w.DWORD,c.c_void_p,w.DWORD]
    dbg.SymLoadModuleExW.restype=c.c_ulonglong
    callback_type=c.WINFUNCTYPE(w.BOOL,c.POINTER(SYMBOL_INFO),w.ULONG,c.c_void_p)
    dbg.SymEnumSymbols.argtypes=[w.HANDLE,c.c_ulonglong,c.c_char_p,callback_type,c.c_void_p];dbg.SymEnumSymbols.restype=w.BOOL
    dbg.SymCleanup.argtypes=[w.HANDLE]; dbg.SymCleanup.restype=w.BOOL
    if not dbg.SymInitializeW(handle,str(exe.parent),False):raise c.WinError(c.get_last_error())
    try:
        base=dbg.SymLoadModuleExW(handle,None,str(exe),None,pe['image_base'],pe['image_size'],None,0)
        if not base:raise c.WinError(c.get_last_error())
        results=[]
        for mask in masks:
            rows=[]
            @callback_type
            def collect(ptr, size, context):
                symbol=ptr.contents
                name=c.string_at(c.addressof(symbol)+SYMBOL_INFO.Name.offset,symbol.NameLen).decode('utf-8','replace')
                rows.append({'name':name,'address':hex(symbol.Address),'rva':hex(symbol.Address-base),
                             'size':symbol.Size,'tag':symbol.Tag,'flags':hex(symbol.Flags)})
                return True
            if not dbg.SymEnumSymbols(handle,base,mask.encode(),collect,None):raise c.WinError(c.get_last_error())
            results.append({'mask':mask,'matches':rows})
        return results
    finally:dbg.SymCleanup(handle)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe',type=Path)
    parser.add_argument('--mask',action='append',default=[])
    parser.add_argument('--output',type=Path,default=Path('artifacts/native-symbols.json'))
    args=parser.parse_args()
    exe=args.exe.resolve();pdb=exe.with_suffix('.pdb')
    pe=pe_identity(exe);identity=pdb_identity(pdb)
    matched=any(all(record[k]==identity[k] for k in ('guid','age')) for record in pe['codeview'])
    if not matched:raise SystemExit('PDB GUID/age mismatch; symbol interpretation refused')
    result={'exe':str(exe),'pdb':str(pdb),'pdb_identity':identity,'pe_identity':pe,'matches':matched,
            'symbols':query_symbols(exe,pe,args.mask or ['*SafeCreateTexture2D*','*VerifyD3D11CreateTextureResult*',
              '*TerminateOnDeviceRemoved*','*CreateD3D11Texture2D*','*RHIInit*','*D3D11CreateDevice*',
              '*GameMoviePlayer*PlayMovie*','*InitD3DDevice*'])}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'matched':matched,'pdb':identity,'symbols':result['symbols']},indent=2))
