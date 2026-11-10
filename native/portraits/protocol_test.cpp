#include "protocol.hpp"
#include "panel_state.hpp"
#include <cassert>
#include <iostream>
int main(){
    assert(krphoto::settings_visible(0)&&krphoto::settings_visible(3)&&krphoto::settings_visible(4));
    assert(!krphoto::settings_visible(1)&&!krphoto::settings_visible(2)&&!krphoto::settings_visible(255));
    // Visibility follows a continuing lobby tick, even long after the last portrait change.
    assert(krphoto::panel_visible(60000,59900,true,true,true,false));
    assert(!krphoto::panel_visible(60000,59000,false,true,true,false));
    assert(!krphoto::panel_visible(60000,58000,true,true,true,false));
    assert(!krphoto::panel_visible(60000,59900,true,true,false,false));
    assert(!krphoto::panel_visible(60000,59900,true,true,true,true));
    assert(!krphoto::panel_visible(60000,59900,true,false,true,false));
    for(size_t n=0;n<256;++n){std::vector<uint8_t> bytes(n);for(size_t i=0;i<n;++i)bytes[i]=uint8_t(i);
        auto encoded=krphoto::base64(bytes);std::vector<uint8_t> decoded;std::wstring wide(encoded.begin(),encoded.end());
        if(n){assert(krphoto::unbase64(wide,decoded,n));assert(decoded==bytes);}
    }
    std::vector<uint8_t> jpeg{255,216,255,217};
    for(auto name:{L"Portrait_01",L"Imperador",L"Retrato \u00e7\u00e3o"}){
        auto wire=krphoto::encode(name,jpeg);auto received=krphoto::decode(wire);assert(received.valid&&received.fallback==name&&received.jpeg==jpeg);
    }
    assert(!krphoto::decode(L"regular_portrait").marked);
    assert(krphoto::decode(L"KRPM1|invalid|bad").marked&&!krphoto::decode(L"KRPM1|invalid|bad").valid);
    for(auto malformed:{L"====",L"AA=A",L"AB==",L"AAA=AAAA",L"AA A",L"++++!"}){std::vector<uint8_t> data;assert(!krphoto::unbase64(malformed,data,64));}
    auto huge=std::wstring(krphoto::MaxToken+1,L'A');assert(!krphoto::decode(L"KRPM1|"+huge).valid);
    bool refused=false;try{krphoto::encode(L"",jpeg);}catch(...){refused=true;}assert(refused);
    // Network-sized payload survives without depending on an original file path.
    std::vector<uint8_t> largest(krphoto::MaxJpeg,123);largest[0]=255;largest[1]=216;
    auto packet=krphoto::encode(std::wstring(krphoto::MaxFallback,L'P'),largest);
    assert(packet.size()<=krphoto::MaxToken);
    auto peer=krphoto::decode(packet);assert(peer.valid&&peer.jpeg==largest&&peer.fallback.size()==krphoto::MaxFallback);
    refused=false;try{largest.push_back(0);krphoto::encode(L"Portrait_01",largest);}catch(...){refused=true;}assert(refused);
    assert(!krphoto::valid_name(std::wstring(1,wchar_t(0xd800))));
    assert(!krphoto::valid_name(L"a\nb"));
    auto corrupt=krphoto::decode(krphoto::encode(L"Portrait_01",jpeg)+L"!");
    assert(corrupt.marked&&!corrupt.valid&&corrupt.fallback==L"Portrait_01");
    std::cout<<"protocol roundtrips, unicode fallback, malformed and size boundaries passed\n";
}
