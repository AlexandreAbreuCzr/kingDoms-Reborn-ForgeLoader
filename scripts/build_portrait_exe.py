"""Add an explicit import of the visible portrait runtime; preserve original imports."""
import hashlib
import json
from pathlib import Path
import struct
import argparse

ROOT=Path(__file__).resolve().parents[1]

def align(n,a):return (n+a-1)//a*a

def add_runtime(original):
    pe=struct.unpack_from('<I',original,0x3c)[0];opt=pe+24
    assert original[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',original,opt)[0]==0x20b
    count=struct.unpack_from('<H',original,pe+6)[0]
    optsize=struct.unpack_from('<H',original,pe+20)[0]
    section_align,file_align=struct.unpack_from('<II',original,opt+32)
    headers=struct.unpack_from('<I',original,opt+60)[0]
    start=opt+optsize
    assert start+(count+1)*40<=headers,'No free section header'
    sections=[]
    for i in range(count):
        vsize,rva,size,offset=struct.unpack_from('<IIII',original,start+40*i+8)
        sections.append((vsize,rva,size,offset))
    def offset_of(rva):
        for v,va,size,off in sections:
            if va<=rva<va+size:return off+rva-va
        raise ValueError('Import RVA outside file')
    directory=opt+112
    import_rva,_=struct.unpack_from('<II',original,directory+8)
    descriptors=bytearray();cursor=offset_of(import_rva)
    while original[cursor:cursor+20]!=b'\0'*20:
        descriptors.extend(original[cursor:cursor+20]);cursor+=20
        if len(descriptors)>4096:raise ValueError('Unexpected import count')
    new_rva=align(max(va+max(v,s) for v,va,s,_ in sections),section_align)
    raw_offset=align(len(original),file_align)
    data=bytearray(descriptors+b'\0'*40)
    def append(raw,alignment=1):
        data.extend(b'\0'*(align(len(data),alignment)-len(data)))
        position=len(data);data.extend(raw);return new_rva+position
    name=append(b'KingdomsPortraits.dll\0')
    function=append(b'\0\0KingdomsPortraitsMarker\0',2)
    ilt=append(struct.pack('<QQ',function,0),8)
    iat=append(struct.pack('<QQ',function,0),8)
    struct.pack_into('<IIIII',data,len(descriptors),ilt,0,0,name,iat)
    result=bytearray(original);result.extend(b'\0'*(raw_offset-len(result)))
    virtual_size=len(data);raw_size=align(virtual_size,file_align);data.extend(b'\0'*(raw_size-len(data)));result.extend(data)
    struct.pack_into('<H',result,pe+6,count+1)
    struct.pack_into('<I',result,opt+56,align(new_rva+virtual_size,section_align))
    struct.pack_into('<I',result,opt+64,0) # User-mode EXE checksum is optional; old value no longer applies.
    struct.pack_into('<II',result,directory+8,new_rva,len(descriptors)+40)
    # Bound imports, if present, would describe the old import layout.
    struct.pack_into('<II',result,directory+11*8,0,0)
    header=struct.pack('<8sIIIIIIHHI',b'.krphoto',virtual_size,new_rva,raw_size,raw_offset,0,0,0,0,0xc0000040)
    result[start+count*40:start+(count+1)*40]=header
    return bytes(result),{'new_section_rva':hex(new_rva),'import_descriptor_count':len(descriptors)//20+1,
                          'preserved_original_import_descriptors':len(descriptors)//20,'new_iat_rva':hex(iat)}

def build(source):
    spec=json.loads((ROOT/'profiles/player-patch.json').read_text())
    raw=Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=spec['source_sha256']:
        raise ValueError('Exact original KR214 executable required')
    modified,_=add_runtime(raw)
    if hashlib.sha256(modified).hexdigest()!=spec['target_sha256']:
        raise ValueError('Unexpected KR214 bootstrap result')
    output=ROOT/'.local/kr214-patched/PrototypeCity-Win64-Shipping.exe'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(modified)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    print(build(parser.parse_args().source))
