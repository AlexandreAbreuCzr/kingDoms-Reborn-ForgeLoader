// Exercise the real importer without starting the game, hooks, or any UI.
#include "portraits.cpp"
#include <cassert>
#include <iostream>
int main(){
    Gdiplus::GdiplusStartupInput input;ULONG_PTR token=0;
    assert(Gdiplus::GdiplusStartup(&token,&input,nullptr)==Gdiplus::Ok);
    wchar_t temp[MAX_PATH],filename[MAX_PATH];assert(GetTempPathW(MAX_PATH,temp));
    assert(GetTempFileNameW(temp,L"KRP",0,filename));
    {
        Gdiplus::Bitmap source(256,128,PixelFormat24bppRGB);
        Gdiplus::Graphics graphics(&source);graphics.Clear(Gdiplus::Color(255,45,100,180));
        UINT count=0,size=0;Gdiplus::GetImageEncodersSize(&count,&size);Bytes storage(size);
        auto* codecs=reinterpret_cast<Gdiplus::ImageCodecInfo*>(storage.data());
        assert(Gdiplus::GetImageEncoders(count,size,codecs)==Gdiplus::Ok);
        bool saved=false;
        for(UINT i=0;i<count;++i)if(wcscmp(codecs[i].MimeType,L"image/png")==0){
            assert(source.Save(filename,&codecs[i].Clsid,nullptr)==Gdiplus::Ok);saved=true;break;
        }
        assert(saved);
    }
    auto image=convert(filename);assert(dimensions(image)&&image.size()<=krphoto::MaxJpeg);
    auto received=krphoto::decode(krphoto::encode(L"Portrait_01",image));
    assert(received.valid&&dimensions(received.jpeg));
    assert(!dimensions(Bytes{255,216,255,217}));
    assert(DeleteFileW(filename));
    bool refused=false;try{convert(filename);}catch(...){refused=true;}assert(refused);
    Gdiplus::GdiplusShutdown(token);
    std::cout<<"Real PNG import, JPEG normalization, receive decode and invalid-file rejection passed\n";
}
